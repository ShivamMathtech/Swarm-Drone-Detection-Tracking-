import type {Frame} from '../types';
import {useStore} from '../store';
export type ImageFrame={meta:Frame;image:ImageBitmap;received:number};
let current:ImageFrame|null=null;
export const getImage=()=>current;
export function connectStream(){
 let closed=false,socket:WebSocket|null=null,retry:ReturnType<typeof setTimeout>,busy=false;
 let pending:ArrayBuffer|null=null;
 async function decode(buffer:ArrayBuffer){
   busy=true;
   try{
     const n=new DataView(buffer).getUint32(0,false);
     if(n<2||n>buffer.byteLength-4)throw new Error('Invalid video packet');
     const meta=JSON.parse(new TextDecoder().decode(buffer.slice(4,4+n))) as Frame;
     const received=performance.now();
     const image=await createImageBitmap(new Blob([buffer.slice(4+n)],{type:'image/jpeg'}));
     if(closed){image.close();return;}
     current?.image.close();current={meta,image,received};
     const state=useStore.getState();
     const changed=state.frame?.session_id!==meta.session_id;
     const selected=!changed&&meta.targets.some(t=>t.track_id===state.selected)?state.selected:meta.targets.find(t=>t.status!=='LOST')?.track_id??null;
     state.set({frame:meta,selected});
   }catch(e){useStore.getState().set({message:String(e)});}
   finally{busy=false;if(pending&&!closed){const next=pending;pending=null;void decode(next);}}
 }
 function open(){
   socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/tracking`);socket.binaryType='arraybuffer';
   socket.onopen=()=>useStore.getState().set({connected:true});
   socket.onmessage=event=>{
     if(typeof event.data==='string'){
       const s=JSON.parse(event.data);
       if(s.type==='status')useStore.getState().set({status:s.status,message:s.message});
     }else if(busy)pending=event.data;else void decode(event.data);
   };
   socket.onclose=()=>{useStore.getState().set({connected:false,message:'Video connection lost; reconnecting…'});if(!closed)retry=setTimeout(open,1500);};
   socket.onerror=()=>socket?.close();
 }
 open();
 return ()=>{closed=true;clearTimeout(retry);socket?.close();current?.image.close();current=null;};
}
