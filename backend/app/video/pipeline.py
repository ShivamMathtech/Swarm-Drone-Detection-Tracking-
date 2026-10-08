import json
import queue
import struct
import time
from pathlib import Path
import cv2
from app.config import Config
from app.detection.yolo_detector import YoloDetector
from app.tracking.tracker import MultiTracker, TrackHistory
from app.video.stream import DemoSource, DemoDetector, VideoSource, LatestLiveSource
from app.analytics.metrics import summarize
from app.utils.database import Database
from app.models.schemas import TrackingMessage

def pack_frame(meta, jpeg):
    raw=json.dumps(meta,separators=(',',':'),allow_nan=False).encode()
    return struct.pack('!I',len(raw))+raw+jpeg

def publish(output, item):
    try: output.put_nowait(item)
    except queue.Full:
        try: output.get_nowait()
        except queue.Empty: pass
        try: output.put_nowait(item)
        except queue.Full: pass

def run_pipeline(config_dict, kind, source, sid, output, stop, paused):
    # Separate process bounds blocked native camera calls; parent can terminate.
    cv2.setLogLevel(0)  # Native decoder diagnostics may contain camera credentials.
    config=Config(**config_dict); cap=None; db=None
    try:
        cap=DemoSource() if kind=='demo' else (LatestLiveSource(source,kind) if kind in ('webcam','rtsp') else VideoSource(source,kind))
        detector=DemoDetector() if kind=='demo' else YoloDetector(config)
        tracker=MultiTracker(config); history=TrackHistory(config)
        db=Database();db.start(sid,kind,time.time())
        frame_id=0;source_frame=0;rate_start=time.monotonic();rate_count=0;fps=0
        clock=time.monotonic(); pause_start=None
        while not stop.is_set():
            if paused.is_set():
                if pause_start is None: pause_start=time.monotonic()
                stop.wait(.05);continue
            if pause_start is not None:
                clock+=time.monotonic()-pause_start;pause_start=None
            started=time.monotonic()
            ok,frame=cap.read();source_frame+=1;captured_at=time.time()
            if not ok or frame is None or frame.size==0:
                publish(output,{'type':'status','status':'ENDED' if kind=='video' else 'ERROR',
                    'message':'Video finished (or decoder reached an unreadable frame).' if kind=='video' else 'CAMERA ERROR: empty frame / disconnected source'})
                break
            source_time=(source_frame-1)/cap.fps
            if kind in ('video','demo'):
                # Follow the recording clock; fast processing never fast-forwards a file.
                stop.wait(max(0,clock+source_time-time.monotonic()))
            if (source_frame-1)%(config.frame_skip+1): continue
            if frame.shape[1]>config.max_frame_width:
                frame=cv2.resize(frame,(config.max_frame_width,round(frame.shape[0]*config.max_frame_width/frame.shape[1])))
            t=time.monotonic();rows=detector.detect(frame);inference_ms=(time.monotonic()-t)*1000
            t=time.monotonic();active=tracker.update(rows,frame)
            # File track age uses video time. Live inputs use elapsed acquisition time.
            track_time=source_time if kind in ('demo','video') else time.monotonic()-clock
            targets,events=history.update(active,track_time,detector.names)
            tracker_ms=(time.monotonic()-t)*1000;frame_id+=1
            now=time.time(); db.record(sid,frame_id,source_frame,track_time,now,targets,events)
            ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,config.jpeg_quality])
            if not ok: raise ValueError('FRAME ERROR: JPEG encoding failed')
            rate_count+=1;elapsed=time.monotonic()-rate_start
            if elapsed>=.5: fps=rate_count/elapsed;rate_count=0;rate_start=time.monotonic()
            msg=TrackingMessage(timestamp=now,captured_at=captured_at,session_id=sid,frame_id=frame_id,source_frame=source_frame,
                source_time=track_time,width=frame.shape[1],height=frame.shape[0],fps=round(fps,1),
                inference_ms=round(inference_ms,2),tracker_ms=round(tracker_ms,2),
                pipeline_ms=round((time.monotonic()-started)*1000,2),demo=kind=='demo',
                model='SYNTHETIC / CONTOUR DETECTOR' if kind=='demo' else Path(config.model_path).name,
                targets=targets,raw_detections=rows.tolist() if config.debug else [],
                stats=summarize(targets,history.detection_count,history.total_tracks),
                events=[{'timestamp':now,'message':e} for e in events]).model_dump()
            publish(output,{'type':'frame','meta':msg,'packet':pack_frame(msg,encoded.tobytes())})
            stop.wait(max(0,1/config.target_fps-(time.monotonic()-started)))
    except Exception as exc:
        # Known messages omit sources; raw third-party exceptions can contain secrets.
        safe=str(exc) if isinstance(exc,ValueError) and str(exc).startswith(('MODEL UNAVAILABLE','CUDA UNAVAILABLE','CAMERA ERROR','FRAME ERROR')) else f'PIPELINE ERROR ({type(exc).__name__}): verify trusted weights, dependencies and input codec; try CPU / demo'
        publish(output,{'type':'status','status':'ERROR','message':safe})
    finally:
        if cap: cap.release()
        if db: db.end(sid,time.time());db.close()
