"""Portable loopback UI with a per-folder single instance and tray lifecycle."""
import sys, os, json, time, threading, webbrowser, msvcrt, ctypes, traceback, socket
from urllib.request import build_opener, ProxyHandler
from runtime import BASE, UI, MAINTENANCE
sys.path[:0] = [str(UI), str(MAINTENANCE)]

def message(text):
    ctypes.windll.user32.MessageBoxW(0, text, 'rlyoulink', 0x40)

def main():
    for name in ('data', 'logs'):
        (BASE/name).mkdir(exist_ok=True)
    log = open(BASE/'logs/application.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    lock = open(BASE/'data/app.lock', 'a+b')
    lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
    state = BASE/'data/runtime.json'
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        for _ in range(30):
            try:
                info = json.loads(state.read_text(encoding='utf-8'))
                with build_opener(ProxyHandler({})).open(info['url']+'api/health', timeout=1) as response:
                    health = json.load(response)
                if health.get('instance') == info.get('instance'):
                    if '--no-browser' not in sys.argv: webbrowser.open(info['url'])
                    return
            except Exception: pass
            time.sleep(.2)
        raise RuntimeError('已有实例正在启动或未响应，请检查托盘和 logs 目录。')
    import server
    from http.server import ThreadingHTTPServer
    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address = False
        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()
    for port in range(8765, 8796):
        try:
            http = LocalServer(('127.0.0.1', port), server.Handler)
            break
        except OSError: continue
    else: raise RuntimeError('8765–8795 端口均不可用。')
    server.PORT = port
    url = f'http://127.0.0.1:{port}/'
    state.write_text(json.dumps({'url':url, 'pid':os.getpid(), 'instance':server.INSTANCE}), encoding='utf-8')
    server.PROBES.start()
    threading.Thread(target=http.serve_forever, daemon=True).start()
    print(time.strftime('%Y-%m-%d %H:%M:%S'), url, flush=True)
    if '--no-browser' not in sys.argv: webbrowser.open(url)
    import pystray
    from PIL import Image
    def stop(icon, item):
        if not server.LOCK.acquire(blocking=False):
            message('设备操作正在进行，请完成后再退出。'); return
        try:
            if server.PROGRESS.snapshot()['state']=='active':
                message('烧录或升级正在进行，请完成后再退出。'); return
            server.DEBUG.action('disconnect', {})
            http.shutdown(); http.server_close()
            state.unlink(missing_ok=True)
            icon.stop()
        except Exception:
            traceback.print_exc(); message('退出时遇到问题，请查看 logs/application.log。')
        finally: server.LOCK.release()
    icon = pystray.Icon('rlyoulink', Image.open(BASE/'assets/rlyoulink.png'), 'rlyoulink', pystray.Menu(
        pystray.MenuItem('打开上位机', lambda: webbrowser.open(url), default=True),
        pystray.MenuItem('打开日志文件夹', lambda: os.startfile(BASE/'logs')),
        pystray.MenuItem('退出', stop)))
    icon.run()
    lock.close()

if __name__=='__main__':
    try: main()
    except Exception as exc:
        traceback.print_exc()
        message(f'启动失败：{exc}\n请将整个文件夹解压到可写目录，并查看 logs/application.log。')
        sys.exit(1)
