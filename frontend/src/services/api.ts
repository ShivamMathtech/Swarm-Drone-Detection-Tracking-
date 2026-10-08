export async function api(path:string,body?:unknown):Promise<any>{
 const response=await fetch('/api'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json();
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));
 return data;
}
export async function upload(file:File){const body=new FormData();body.append('file',file);const r=await fetch('/api/upload-video',{method:'POST',body});const d=await r.json();if(!r.ok)throw new Error(d.detail);return d;}
