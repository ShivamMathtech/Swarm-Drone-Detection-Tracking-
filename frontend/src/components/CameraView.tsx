import {useEffect,useRef} from 'react';
import {useStore} from '../store';
import {getImage} from '../services/stream';
import {drawHud,cropRect} from '../hud/draw';
export function CameraView(){
 const ref=useRef<HTMLCanvasElement>(null);const frame=useStore(s=>s.frame);const status=useStore(s=>s.status);
 useEffect(()=>{let raf=0,lastFrame="";const render=()=>{const begin=performance.now();
  const c=ref.current,entry=getImage(),state=useStore.getState();
  if(c&&entry&&state.config){const f=entry.meta;
   if(c.width!==f.width||c.height!==f.height){c.width=f.width;c.height=f.height;}
   const ctx=c.getContext('2d')!;ctx.filter='grayscale(1) contrast(0.85) brightness(0.82)';ctx.drawImage(entry.image,0,0);ctx.filter='none';
   drawHud(ctx,f,state.config,state.selected,performance.now());
   const key=f.session_id+':'+f.frame_id;
   if(key!==lastFrame){lastFrame=key;state.set({renderMs:performance.now()-begin,displayLatencyMs:Math.max(0,Date.now()-f.captured_at*1000)});}
  }raf=requestAnimationFrame(render);
 };raf=requestAnimationFrame(render);return()=>cancelAnimationFrame(raf);},[]);
 return <div className="camera-shell">
  <canvas ref={ref} width={1280} height={720} aria-label="Live camera with tracking HUD" onClick={e=>{
    const f=getImage()?.meta;if(!f)return;const r=e.currentTarget.getBoundingClientRect(),x=(e.clientX-r.left)*f.width/r.width,y=(e.clientY-r.top)*f.height/r.height;
    const hit=f.targets.filter(t=>x>=t.bbox[0]-15&&x<=t.bbox[2]+15&&y>=t.bbox[1]-15&&y<=t.bbox[3]+15).sort((a,b)=>(a.bbox[2]-a.bbox[0])-(b.bbox[2]-b.bbox[0]))[0];
    if(hit)useStore.getState().set({selected:hit.track_id});
  }}/>
  <div className="feed-tag">{frame?.demo?'DEMO MODE · SYNTHETIC SCENE':'EO / VIS · OBSERVATION ONLY'}</div>
  {(!frame||status!=='RUNNING')&&<div className="feed-state"><b>{status}</b><span>{status==='STOPPED'?'Choose DEMO to verify the complete pipeline':useStore.getState().message}</span></div>}
  <div className="scanlines"/>
 </div>;
}
export function SeekerView(){
 const ref=useRef<HTMLCanvasElement>(null);const selected=useStore(s=>s.selected),cfg=useStore(s=>s.config);
 useEffect(()=>{let raf=0;const draw=()=>{
  const canvas=ref.current,entry=getImage(),s=useStore.getState();
  if(canvas){const c=canvas.getContext('2d')!;c.fillStyle='#050906';c.fillRect(0,0,320,180);
   const t=entry?.meta.targets.find(x=>x.track_id===s.selected);
   if(entry&&t&&s.config&&t.status!=='LOST'){
    const [x,y,w,h]=cropRect(t,entry.meta.width,entry.meta.height,s.config.zoom);
    c.filter='grayscale(1)';c.drawImage(entry.image,x,y,w,h,0,0,320,180);c.filter='none';
    c.strokeStyle='#00ff40';c.lineWidth=1;const sx=320/w,sy=180/h;
    c.strokeRect((t.bbox[0]-x)*sx,(t.bbox[1]-y)*sy,(t.bbox[2]-t.bbox[0])*sx,(t.bbox[3]-t.bbox[1])*sy);
   }else{c.fillStyle='#4a8659';c.font='12px monospace';c.fillText(t?'TRACK LOST · NO CURRENT CROP':'SELECT A VISIBLE TRACK',25,93);}
  }raf=requestAnimationFrame(draw);
 };raf=requestAnimationFrame(draw);return()=>cancelAnimationFrame(raf);},[]);
 if(!cfg?.show_seeker)return null;
 return <section><h2>SEEKER VIEW <span>{cfg.zoom}.0X</span></h2><canvas ref={ref} width={320} height={180} className="seeker" aria-label="Selected target crop"/><div className="section-foot">{selected?`DR-${String(selected).padStart(2,'0')}`:'NO SELECTION'}<span>DIGITAL CROP</span></div></section>;
}
