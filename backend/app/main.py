import asyncio
import csv
import io
import json
import multiprocessing as mp
import os
import queue
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import cv2
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv
from app.config import Config, StartRequest, DATA, ROOT
from app.models.schemas import EvaluationReport
from app.utils.database import Database
from app.video.pipeline import run_pipeline

load_dotenv(ROOT/'.env')
ORIGINS={x.strip() for x in os.getenv('ALLOWED_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080').split(',')}

class Engine:
    def __init__(self):
        db=Database(); self.config=Config(**db.load_config()); db.close()
        self.proc=None;self.output=None;self.stop_event=None;self.pause_event=None
        self.latest=None;self.meta=None;self.version=0;self.status='STOPPED';self.message='Ready. Start DEMO or configure trusted drone weights.'
        self.sid=None;self.lock=asyncio.Lock();self.evaluation=None
    async def stop(self):
        if self.proc:
            self.stop_event.set()
            await asyncio.to_thread(self.proc.join,2)
            if self.proc.is_alive():
                self.proc.terminate(); await asyncio.to_thread(self.proc.join,2)
            self.proc.close();self.proc=None
            self.output.close();self.output=None
            db=Database();db.end(self.sid,time.time());db.close()
        self.status='STOPPED';self.message='Stream stopped';self.latest=None;self.meta=None;self.version+=1
    async def start(self, req):
        if self.proc and self.proc.is_alive(): raise HTTPException(409,'Stop the current stream first')
        source=None
        if req.source=='webcam': source=req.camera_index
        if req.source=='rtsp':
            if not req.rtsp_alias.startswith('CAM_') or not req.rtsp_alias.replace('_','').isalnum():
                raise HTTPException(422,'Use a CAM_ environment variable alias')
            source=os.getenv(req.rtsp_alias)
            if not source or not source.lower().startswith(('rtsp://','rtsps://')):
                raise HTTPException(422,'RTSP alias missing or invalid in server environment')
        if req.source=='video':
            try: uid=str(uuid.UUID(req.upload_id or ''))
            except ValueError: raise HTTPException(422,'Upload a video first')
            matches=list((DATA/'uploads').glob(uid+'.*'))
            if not matches: raise HTTPException(404,'Uploaded video not found')
            source=str(matches[0])
        await self.stop()
        self.sid=str(uuid.uuid4());ctx=mp.get_context('spawn')
        self.output=ctx.Queue(maxsize=2);self.stop_event=ctx.Event();self.pause_event=ctx.Event()
        self.proc=ctx.Process(target=run_pipeline,args=(self.config.model_dump(),req.source,source,self.sid,self.output,self.stop_event,self.pause_event),daemon=True)
        self.status='STARTING';self.message='Opening source and loading tracker/model';self.proc.start()
    async def pump(self):
        while True:
            if self.output:
                try:
                    while True:
                        item=self.output.get_nowait()
                        if item['type']=='frame':
                            self.latest=item['packet'];self.meta=item['meta'];self.version+=1
                            if not self.pause_event.is_set(): self.status='RUNNING';self.message='Tracking active'
                        else: self.status=item['status'];self.message=item['message'];self.version+=1
                except queue.Empty: pass
                if self.proc and not self.proc.is_alive() and self.status in ('STARTING','RUNNING','PAUSED'):
                    self.status='ERROR';self.message='Worker exited; verify dependencies and input';self.version+=1
            await asyncio.sleep(.01)
    def state(self): return {'status':self.status,'message':self.message,'session_id':self.sid}

@asynccontextmanager
async def lifespan(app):
    app.state.engine=Engine();task=asyncio.create_task(app.state.engine.pump())
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
    await app.state.engine.stop()

app=FastAPI(title='Swarm Drone Tracking Research Console',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=list(ORIGINS),allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.middleware('http')
async def origin_guard(request:Request,call_next):
    if request.headers.get('origin') and request.headers['origin'] not in ORIGINS:
        return Response('Origin denied',status_code=403)
    return await call_next(request)

def engine(request): return request.app.state.engine

@app.get('/health')
async def health(request:Request):
    e=engine(request);return {'ok':True,**e.state()}

@app.get('/config')
async def get_config(request:Request): return engine(request).config.model_dump()

@app.post('/config')
async def set_config(config:Config,request:Request):
    e=engine(request)
    async with e.lock:
        if e.proc and e.proc.is_alive(): raise HTTPException(409,'Stop stream before applying settings')
        db=Database();db.save_config(config);db.close();e.config=config
    return config.model_dump()

@app.post('/stream/start')
async def start(req:StartRequest,request:Request):
    e=engine(request)
    async with e.lock: await e.start(req)
    return e.state()

@app.post('/stream/stop')
async def stop(request:Request):
    e=engine(request)
    async with e.lock: await e.stop()
    return e.state()

@app.post('/stream/pause')
async def pause(request:Request):
    e=engine(request)
    async with e.lock:
        if e.status!='RUNNING': raise HTTPException(409,'Stream is not running')
        e.pause_event.set();e.status='PAUSED';e.message='Paused';e.version+=1
    return e.state()

@app.post('/stream/resume')
async def resume(request:Request):
    e=engine(request)
    async with e.lock:
        if e.status!='PAUSED': raise HTTPException(409,'Stream is not paused')
        e.pause_event.clear();e.status='RUNNING';e.message='Tracking active';e.version+=1
    return e.state()

@app.post('/upload-video')
async def upload_video(file:UploadFile=File(...)):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in {'.mp4','.avi','.mov','.mkv','.webm'}: raise HTTPException(422,'Supported: MP4 AVI MOV MKV WebM')
    uid=str(uuid.uuid4());path=DATA/'uploads'/(uid+ext);size=0
    try:
        with path.open('wb') as target:
            while block:=await file.read(1024*1024):
                size+=len(block)
                if size>1024**3: raise HTTPException(413,'Maximum video size is 1 GiB')
                target.write(block)
        def verify():
            cap=cv2.VideoCapture(str(path));ok,frame=cap.read();cap.release()
            return ok and frame is not None and frame.size>0
        if not await asyncio.to_thread(verify): raise HTTPException(422,'Video cannot be decoded; convert to H.264 MP4 or MJPEG AVI')
    except BaseException:
        path.unlink(missing_ok=True);raise
    finally: await file.close()
    return {'upload_id':uid,'bytes':size}

@app.get('/tracks')
async def tracks(request:Request): return (engine(request).meta or {}).get('targets',[])

@app.get('/stats')
async def stats(request:Request):
    e=engine(request);return {**e.state(),**(e.meta or {}).get('stats',{}),'evaluation':e.evaluation}

@app.get('/events')
async def events(request:Request):
    db=Database()
    rows=[dict(r) for r in db.db.execute('SELECT timestamp,message FROM events WHERE session_id=? ORDER BY id DESC LIMIT 100',(engine(request).sid,))];db.close()
    return rows

@app.post('/research/report')
async def report(report:EvaluationReport,request:Request):
    e=engine(request);e.evaluation=report.model_dump();return e.evaluation

@app.get('/reports/{kind}')
async def export(kind:str,request:Request):
    if kind not in ('json','csv'): raise HTTPException(404,'Use json or csv')
    e=engine(request);db=Database()
    detections=[dict(r) for r in db.db.execute('SELECT d.*,t.class_name FROM detections d LEFT JOIN tracks t ON d.session_id=t.session_id AND d.track_id=t.track_id WHERE d.session_id=? ORDER BY d.id',(e.sid,))]
    tracks=[dict(r) for r in db.db.execute('SELECT * FROM tracks WHERE session_id=?',(e.sid,))];db.close()
    if kind=='json':
        body=json.dumps({'session_id':e.sid,'config':e.config.model_dump(),'evaluation':e.evaluation,'stats':(e.meta or {}).get('stats',{}),'tracks':tracks,'detections':detections},indent=2)
    else:
        output=io.StringIO();fields=list(detections[0]) if detections else ['session_id','track_id','timestamp','frame_id','x1','y1','x2','y2','confidence','class_name']
        writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader();writer.writerows(detections);body=output.getvalue()
    return Response(body,media_type='application/json' if kind=='json' else 'text/csv',headers={'Content-Disposition':f'attachment; filename="swarm-session.{kind}"'})

@app.websocket('/ws/tracking')
async def tracking(ws:WebSocket):
    if ws.headers.get('origin') not in ORIGINS and ws.headers.get('origin') is not None:
        await ws.close(code=1008);return
    await ws.accept();e=ws.app.state.engine;last=-1;last_state=None
    receiver=asyncio.create_task(ws.receive())
    try:
        while True:
            if receiver.done():
                if receiver.result()['type']=='websocket.disconnect': break
                receiver=asyncio.create_task(ws.receive())
            state=e.state()
            if state!=last_state:
                await asyncio.wait_for(ws.send_json({'type':'status',**state}),5);last_state=state
            if e.version!=last and e.latest and e.status in ('RUNNING','PAUSED','ENDED'):
                # JPEG and metadata share a packet, so overlays cannot drift to another frame.
                await asyncio.wait_for(ws.send_bytes(e.latest),5);last=e.version
            await asyncio.sleep(.02)
    except (WebSocketDisconnect,RuntimeError,asyncio.TimeoutError): pass
    finally:
        receiver.cancel()
        try: await receiver
        except (asyncio.CancelledError,WebSocketDisconnect,RuntimeError): pass
