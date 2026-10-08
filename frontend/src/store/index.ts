import {create} from 'zustand';
import type {Config,Frame,Evaluation} from '../types';
type State={config:Config|null;frame:Frame|null;selected:number|null;status:string;message:string;connected:boolean;renderMs:number|null;displayLatencyMs:number|null;events:{timestamp:number;message:string}[];evaluation:Evaluation|null;set:(s:Partial<State>)=>void};
export const useStore=create<State>(set=>({config:null,frame:null,selected:null,status:'STOPPED',message:'Connecting to sensor service…',connected:false,renderMs:null,displayLatencyMs:null,events:[],evaluation:null,set:s=>set(s)}));
