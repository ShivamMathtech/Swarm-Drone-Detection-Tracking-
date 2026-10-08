import {useState} from 'react';
import {useStore} from '../store';
import {api,upload} from '../services/api';
export function ControlPanel({openSettings}:{openSettings:()=>void}){
 const status=useStore(s=>s.status),message=useStore(s=>s.message);const [source,setSource]=useState('demo'),[camera,setCamera]=useState(0),[alias,setAlias]=useState('CAM_RTSP_URL'),[uploadId,setUploadId]=useState(''),[filename,setFilename]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const running=['STARTING','RUNNING','PAUSED'].includes(status);
 async function action(path:string,body:unknown={}){setBusy(true);setError('');try{const r=await api(path,body);useStore.getState().set({status:r.status,message:r.message});}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <section className="control"><h2>SOURCE / SESSION <button onClick={openSettings}>SETTINGS ↗</button></h2><div className="controls-row"><label>SOURCE<select disabled={running||busy} value={source} onChange={e=>setSource(e.target.value)}><option value="demo">DEMO · SYNTHETIC</option><option value="video">VIDEO FILE</option><option value="webcam">WEBCAM</option><option value="rtsp">RTSP / IP CAMERA</option></select></label>
 {source==='webcam'&&<label>CAMERA INDEX<input aria-label="Camera index" type="number" min={0} max={10} value={camera} onChange={e=>setCamera(+e.target.value)}/></label>}
 {source==='rtsp'&&<label>SERVER ENV ALIAS<input value={alias} onChange={e=>setAlias(e.target.value)}/></label>}
 {source==='video'&&<label className="file-label">{filename||'UPLOAD VIDEO'}<input disabled={running||busy} type="file" accept=".mp4,.avi,.mov,.mkv,.webm" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;setBusy(true);setError('');setUploadId('');try{const d=await upload(file);setUploadId(d.upload_id);setFilename(file.name);}catch(err){setError(String(err));}finally{setBusy(false);}}}/></label>}
 <div className="session-buttons"><button className="primary" disabled={running||busy||(source==='video'&&!uploadId)} onClick={()=>action('/stream/start',{source,camera_index:camera,upload_id:uploadId||null,rtsp_alias:alias})}>{busy?'WAIT…':'START'}</button><button disabled={!running||busy} onClick={()=>action('/stream/stop')}>STOP</button><button disabled={!['RUNNING','PAUSED'].includes(status)||busy} onClick={()=>action(status==='PAUSED'?'/stream/resume':'/stream/pause')}>{status==='PAUSED'?'RESUME':'PAUSE'}</button></div></div><div role="status" className={error||status==='ERROR'?'message error':'message'}>{error||message}</div></section>;
}
