import type {Config,Frame,Target} from '../types';
const G='#00ff40';
function bracket(c:CanvasRenderingContext2D,b:number[],pad=0){
 const [x1,y1,x2,y2]=[b[0]-pad,b[1]-pad,b[2]+pad,b[3]+pad],l=Math.min(17,(x2-x1)/3);
 c.beginPath();for(const [x,y,sx,sy] of [[x1,y1,1,1],[x2,y1,-1,1],[x1,y2,1,-1],[x2,y2,-1,-1]]){c.moveTo(x+sx*l,y);c.lineTo(x,y);c.lineTo(x,y+sy*l);}c.stroke();
}
export function drawHud(c:CanvasRenderingContext2D,f:Frame,cfg:Config,selected:number|null,animationTime:number){
 const {width:w,height:h}=f,scale=w/1280,fs=Math.max(12,13*scale);
 c.save();c.strokeStyle=G;c.fillStyle=G;c.lineWidth=1*scale;c.font=`${fs}px monospace`;
 c.shadowColor='#00ff4033';c.shadowBlur=3;
 const text=(s:string,x:number,y:number)=>c.fillText(s,x,y);
 // Pixel scales, deliberately not headings, altitude tapes, or fabricated range.
 c.globalAlpha=.65;c.beginPath();
 for(let i=0;i<=10;i++){const x=w*.3+i*w*.04;c.moveTo(x,50*scale);c.lineTo(x,(i%5?56:62)*scale);}
 c.moveTo(w*.3,56*scale);c.lineTo(w*.7,56*scale);c.stroke();text('IMAGE COORDINATES / PX',w*.41,35*scale);
 c.globalAlpha=1;
 if(cfg.show_crosshair){
  const x=w/2,y=h/2,l=60*scale,g=16*scale;c.beginPath();
  c.moveTo(x-l,y);c.lineTo(x-g,y);c.moveTo(x+g,y);c.lineTo(x+l,y);
  c.moveTo(x,y-l);c.lineTo(x,y-g);c.moveTo(x,y+g);c.lineTo(x,y+l);
  c.moveTo(x-3,y);c.lineTo(x+3,y);c.moveTo(x,y-3);c.lineTo(x,y+3);c.stroke();
  c.globalAlpha=.18;c.beginPath();c.arc(x,y,42*scale,animationTime*.0001,animationTime*.0001+.8);c.stroke();c.globalAlpha=1;
 }
 for(const t of f.targets){
  const color=t.status==='LOST'?'#ff6666':t.confidence<cfg.confidence_threshold?'#d8da65':G;
  c.strokeStyle=color;c.fillStyle=color;c.lineWidth=cfg.line_thickness*scale;
  if(cfg.show_trajectory){
   c.setLineDash([4*scale,5*scale]);
   for(let i=1;i<t.trajectory.length;i++){
    c.globalAlpha=cfg.fade_points?.12+.65*i/t.trajectory.length:.7;
    c.beginPath();c.moveTo(...t.trajectory[i-1] as [number,number]);c.lineTo(...t.trajectory[i] as [number,number]);c.stroke();
   }c.setLineDash([]);c.globalAlpha=1;
  }
  if(cfg.show_boxes){bracket(c,t.bbox,5*scale);if(t.track_id===selected){c.lineWidth=1;bracket(c,t.bbox,12*scale);}}
  const x=Math.max(5,Math.min(w-170*scale,t.bbox[0])),y=Math.max(86*scale,t.bbox[1]-15*scale);
  if(cfg.show_ids)text(`${t.id}  ${t.class_name.toUpperCase()}`,x,y);
  if(cfg.show_confidence)text(`${Math.round(t.confidence*100)}%  ${t.status}`,x,t.bbox[3]+23*scale);
  if(cfg.debug)text(`X ${t.center[0].toFixed(0)} Y ${t.center[1].toFixed(0)}`,x,t.bbox[3]+40*scale);
 }
 if(cfg.debug){c.strokeStyle='#ffffff88';c.setLineDash([2,3]);for(const b of f.raw_detections)c.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);c.setLineDash([]);}
 c.fillStyle=G;c.globalAlpha=.75;
 text('EO / VIS · GRAYSCALE DISPLAY',24*scale,h-44*scale);
 text(`FRAME ${String(f.source_frame).padStart(6,'0')}  ·  T+${f.source_time.toFixed(1)}s`,24*scale,h-23*scale);
 c.textAlign='right';text('RNG N/A   ALT N/A   SPD N/A',w-24*scale,h-23*scale);
 c.restore();
}
export function cropRect(t:Target,w:number,h:number,zoom:number){
 const bw=t.bbox[2]-t.bbox[0],bh=t.bbox[3]-t.bbox[1];
 // Magnification relative to a contextual crop, increasing with the zoom setting.
 let cw=Math.min(w,Math.max(bw*1.5,Math.max(bw*12,160)/zoom)),ch=cw*9/16;
 if(ch>h){ch=h;cw=ch*16/9;}
 if(ch<bh*1.5){ch=Math.min(h,bh*1.5);cw=Math.min(w,ch*16/9);}
 return [Math.min(Math.max(0,t.center[0]-cw/2),w-cw),Math.min(Math.max(0,t.center[1]-ch/2),h-ch),cw,ch];
}
