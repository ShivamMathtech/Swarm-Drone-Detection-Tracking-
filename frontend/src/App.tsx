import {useEffect,useState} from 'react';
import {useStore} from './store';
import {api} from './services/api';
import {connectStream} from './services/stream';
import {CameraView,SeekerView} from './components/CameraView';
import {TopStatus,TargetManager,TargetInfo,SystemStats,EventLog,ResearchPanel} from './components/Telemetry';
import {ControlPanel} from './components/ControlPanel';
import {Settings} from './components/Settings';
export default function App(){
 const [settings,setSettings]=useState(false);const ready=useStore(s=>!!s.config);
 useEffect(()=>{let stopped=false;const disconnect=connectStream();
 const refresh=async()=>{try{
  if(!useStore.getState().config){const config=await api('/config');if(!stopped)useStore.getState().set({config});}
  const [events,stats]=await Promise.all([api('/events'),api('/stats')]);
  if(!stopped)useStore.getState().set({events,evaluation:stats.evaluation});
 }catch(e){if(!stopped)useStore.getState().set({message:`Backend unavailable: ${String(e)}`});}};
 void refresh();const timer=setInterval(refresh,1500);return()=>{stopped=true;clearInterval(timer);disconnect();};},[]);
 return <main><header><div className="brand"><span className="brand-mark">⊕</span><div><h1>SWARM DRONE TRACKING</h1><p>COMPUTER VISION / OBSERVATION & RESEARCH</p></div></div><div className="header-right">EO / VIS <span>LOCAL CONSOLE</span></div></header><TopStatus/><div className="workspace"><div className="main-column"><CameraView/><ControlPanel openSettings={()=>setSettings(true)}/><ResearchPanel/><EventLog/></div><aside><TargetManager/><SeekerView/><TargetInfo/><SystemStats/></aside></div><footer><span>MONITOR · CLASSIFY · TRACK</span><div><a href="/api/reports/csv" download>EXPORT CSV ↓</a><a href="/api/reports/json" download>EXPORT JSON ↓</a><label className="report-import">IMPORT EVALUATION<input type="file" accept=".json" onChange={async e=>{const f=e.target.files?.[0];if(!f)return;try{const evaluation=await api('/research/report',JSON.parse(await f.text()));useStore.getState().set({evaluation});}catch(err){useStore.getState().set({message:`Report rejected: ${String(err)}`});}}}/></label></div></footer>{settings&&ready&&<Settings close={()=>setSettings(false)}/>}</main>;
}
