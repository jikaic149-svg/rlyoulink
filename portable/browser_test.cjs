const fs=require('fs');
(async()=>{
 const root=process.argv[2], info=JSON.parse(fs.readFileSync(root+'/data/runtime.json','utf8'));
 const target=await (await fetch('http://127.0.0.1:9229/json/new?'+encodeURIComponent(info.url),{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl), pending=new Map(),errors=[];let id=0;
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
 function call(method,params={}){return new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});}
 await call('Runtime.enable');await call('Page.enable');await call('Page.reload');
 await new Promise(r=>setTimeout(r,6500));
 const r=await call('Runtime.evaluate',{expression:"JSON.stringify({title:document.title,service:document.getElementById('monitor-service').textContent,probe:document.getElementById('probe-select').textContent,token:!!serviceToken})",returnByValue:true});
 console.log(r.result.value);console.log(JSON.stringify({javascriptErrors:errors}));
 const shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync('portable_rlyoulink/browser-check.png',Buffer.from(shot.data,'base64'));
 ws.close();await fetch('http://127.0.0.1:9229/json/close/'+target.id);
 if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
