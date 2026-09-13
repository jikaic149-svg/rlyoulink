from pathlib import Path
import os, subprocess, sys, time, urllib.request, json, webbrowser
root=Path(__file__).resolve().parent
url='http://127.0.0.1:8765'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def ready():
    try:
        with opener.open(url+'/api/health',timeout=1) as response:
            return json.load(response).get('service')=='amphilink-local'
    except Exception:return False
if not ready():
    with (root/'server.log').open('a',encoding='utf-8') as log:
        subprocess.Popen([sys.executable,str(root/'server.py')],cwd=root,
            stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(30):
        if ready():break
        time.sleep(.2)
    else:
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'启动失败，请查看 AmphiLink_UI/server.log','AmphiLink',0)
        raise SystemExit(1)
webbrowser.open(url)
