from pathlib import Path
import json, urllib.request, subprocess, tempfile, zipfile, os, sys
base=Path(sys.argv[1]).resolve()
info=json.loads((base/'data/runtime.json').read_text())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
    with op.open(info['url']+path,timeout=10) as response:return json.load(response)
health=get('api/health')
assert health['instance']==info['instance'] and health['distribution']=='rlyoulink-portable'
state=get('api/state'); assert not state['session_active']
assert get('api/progress')['state']=='idle'
for name in ('','style.css','app.js','network.js','backend.js','links.js','upgrade.js','progress.js'):
    assert op.open(info['url']+name,timeout=10).status==200
package=next((base/'firmware').glob('*.amphipkg'))
import base64
body=json.dumps({'name':package.name,'data':base64.b64encode(package.read_bytes()).decode()}).encode()
request=urllib.request.Request(info['url']+'api/probe-package',data=body,headers={
    'Origin':info['url'].rstrip('/'),'X-AmphiLink-Token':state['token'],'Content-Type':'application/json'})
inspection=json.load(op.open(request,timeout=30))
assert inspection['manifest']['version']=='3.0.0'
worker=base/'rlyoulink-worker.exe'
env={**os.environ,'PATH':os.environ['SystemRoot']+'\\System32','PYTHONPATH':'','PYTHONHOME':''}
def run(*args,success=True):
    result=subprocess.run([str(worker),'--task',*map(str,args)],env=env,cwd=tempfile.gettempdir(),capture_output=True,timeout=30)
    assert (result.returncode==0)==success,(args,result.stdout,result.stderr)
    return result
run('self-test');run('esptool','version')
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    with zipfile.ZipFile(package) as z:
        entries={name:z.read(name) for name in z.namelist()}
    (tmp/'app.bin').write_bytes(entries['application.bin'])
    run('release','pack',tmp/'app.bin','--version','3.0.0','--output',tmp/'new.amphipkg')
    run('release','verify',tmp/'new.amphipkg')
    image=bytearray(entries['application.bin']); image[-1]^=1
    entries['application.bin']=bytes(image)
    with zipfile.ZipFile(tmp/'bad.amphipkg','w') as z:
        for name,data in entries.items():z.writestr(name,data)
    run('release','verify',tmp/'bad.amphipkg',success=False)
    entries['application.bin']=(tmp/'app.bin').read_bytes()
    entries['manifest.sig']=b'\x00'*len(entries['manifest.sig'])
    with zipfile.ZipFile(tmp/'badsig.amphipkg','w') as z:
        for name,data in entries.items():z.writestr(name,data)
    run('release','verify',tmp/'badsig.amphipkg',success=False)
second=subprocess.run([str(base/'rlyoulink.exe'),'--no-browser'],timeout=12,env=env)
assert second.returncode==0
assert json.loads((base/'data/runtime.json').read_text())==info
print(json.dumps({'portable_smoke':'passed','url':info['url'],'signing':'passed',
                  'tampered_image':'rejected','bad_signature':'rejected','single_instance':'passed',
                  'external_python_path':'disabled','hardware_writes':False}))
