"""Loopback-only AmphiLink UI and one owned OpenOCD session."""
import atexit
import base64
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import mimetypes
import re
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit, parse_qs
from links import ProbeMonitor
import probe_upgrade
from progress import PROGRESS
from targets import identify, flash_ranges, contains_image

from runtime import UI as ROOT, OPENOCD as OCD
from probe_device import list_probes
TOKEN = secrets.token_hex(24)
INSTANCE = secrets.token_hex(16)
PORT = 8765
LOCK = threading.Lock()
PROBES = ProbeMonitor()

def number(value, maximum=0xffffffff):
    n = int(str(value), 0)
    if not 0 <= n <= maximum: raise ValueError('地址或参数超出范围')
    return n

class Debugger:
    def __init__(self):
        self.process = None
        self.rpc = None
        self.logs = deque(maxlen=200)
        self.identity = {}
        self.breakpoints = {}
        self.transport = None
        self.host = None
        self.target = "rlyou_detect.mem"
        self.profile = None
        self.flash_ranges = []

    def command(self, command, timeout=5):
        if not self.rpc or not self.process or self.process.poll() is not None:
            raise RuntimeError('OpenOCD 未连接，请重新连接目标')
        self.rpc.settimeout(timeout)
        wire = f'set ui_code [catch {{{command}}} ui_result]; format "%d\\n%s" $ui_code $ui_result'
        try:
            self.rpc.sendall(wire.encode()+b'\x1a')
            data = bytearray()
            while not data.endswith(b'\x1a'):
                part = self.rpc.recv(4096)
                if not part: raise ConnectionError('OpenOCD 连接已关闭')
                data.extend(part)
                if len(data)>1024*1024: raise RuntimeError('OpenOCD 响应过大')
        except (OSError, ConnectionError):
            self.close()
            raise RuntimeError('调试通信中断；目标状态未知，请重新连接')
        code, _, result = data[:-1].decode(errors='replace').partition('\n')
        if code != '0': raise RuntimeError(result or 'OpenOCD 命令失败')
        return result

    def read(self, address, width, count):
        raw = self.command(f'{self.target} read_memory {address} {width} {count}')
        return [int(v,0) for v in raw.split()]

    def output_reader(self, process, ready=None):
        for line in process.stdout:
            if ready and 'Listening on port' in line and 'tcl connections' in line:
                ready.set()
            if re.match(r'^\s*#\s*\d+:\s*0x[0-9a-fA-F]+\s*\(0x', line):
                continue  # Keep the full RPC sector map, but avoid flooding UI logs.
            self.logs.append(line.rstrip())

    def connect(self, options):
        if self.process: raise RuntimeError('已有调试会话，请先断开')
        transport = options.get('transport','usb')
        if transport not in ('usb','wifi'): raise ValueError('未知连接方式')
        speed = number(options.get('speed',100),1000)
        if speed not in (100,500,1000): raise ValueError('不支持的 SWD 速率')
        config = ['bindto 127.0.0.1','gdb port disabled','telnet port disabled',
                  'adapter driver cmsis-dap']
        if transport == 'wifi':
            host = str(ipaddress.IPv4Address(options.get('host','')))
            port = number(options.get('port',4441),65535)
            if not port: raise ValueError('无效端口')
            config += ['cmsis-dap backend tcp',f'cmsis-dap tcp host {host}',f'cmsis-dap tcp port {port}']
        else:
            candidates=list_probes()
            selected=str(options.get('serial') or '')
            if not selected and len(candidates)==1:selected=candidates[0]
            if selected not in candidates:raise ValueError('Select one connected USB probe')
            config += ['cmsis-dap backend usb_bulk','cmsis-dap vid_pid 0x303a 0x83b3','adapter serial '+selected]
        config += ['transport select swd', f'adapter speed {speed}', 'cmsis-dap quirk disable']
        self.logs.clear()
        try:
            self.target = 'rlyou_detect.core'
            self.start_session(config + [
                'source [find target/swj-dp.tcl]',
                'swj_newdap rlyou_detect cpu -irlen 4 -ircapture 0x1 -irmask 0xf',
                'dap create rlyou_detect.dap -chain-position rlyou_detect.cpu',
                'target create rlyou_detect.core cortex_m -dap rlyou_detect.dap -ap-num 0 -endian little',
                'reset_config none'])
            detection_state = self.command(f'{self.target} curstate')
            try:
                self.command('halt 2000')
                profile, identity = identify(self.read)
            finally:
                if detection_state == 'running':
                    self.command('resume')
            self.logs.append('Auto-detected ' + identity['name'] + ' / ' + identity['config'])
            self.close()
            self.profile = profile
            self.target = profile.cpu
            self.start_session(config + ['source [find target/' + profile.config + ']',
                                         f'adapter speed {speed}', 'reset_config none'])
            original_state = self.command(f'{self.target} curstate')
            try:
                self.command('halt 2000')
                code = self.read(identity['id_address'], 32, 1)[0]
                if code != int(identity['id'], 0):
                    raise RuntimeError('Target identity changed during connection')
                # Probe all configured banks while halted. Unknown/protected flash
                # must fail here instead of enabling a guessed programming layout.
                banks = int(self.command('llength [flash list]'))
                bank_info = []
                for index in range(banks):
                    base = int(self.command(f'dict get [lindex [flash list] {index}] base'), 0)
                    if not 0x08000000 <= base < 0x08400000:
                        # The vendor scripts also register OTP banks. They are
                        # not application flash and must never enter this map.
                        continue
                    bank_info.append(self.command(f'flash info {index} sectors', timeout=5))
                self.flash_ranges = flash_ranges(bank_info, identity['flash_kib'])
                identity['flash_ranges'] = [{'start':a, 'end':b} for a,b in self.flash_ranges]
                self.identity = identity
            finally:
                if original_state == 'running':
                    self.command('resume')
            self.transport = transport
            self.host = host if transport == 'wifi' else None
            return self.status()
        except Exception:
            self.close()
            raise

    def start_session(self, config):
        config = list(config)
        # Select a free loopback port; never attach to an unrelated OpenOCD.
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0)); rpc_port=listener.getsockname()[1]
        config += [f'tcl port {rpc_port}','init']
        args=[str(OCD/'bin/openocd.exe'),'-s',str(OCD/'share/openocd/scripts')]
        for line in config: args += ['-c',line]
        self.process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        ready=threading.Event()
        threading.Thread(target=self.output_reader,args=(self.process,ready),daemon=True).start()
        try:
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if self.process.poll() is not None: raise RuntimeError('\n'.join(self.logs)[-2500:])
                if ready.wait(.05):
                    self.rpc=socket.create_connection(('127.0.0.1',rpc_port),timeout=2)
                    break
            if not self.rpc: raise RuntimeError('OpenOCD 启动超时\n'+'\n'.join(self.logs)[-1500:])
            self.rpc.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            self.close();raise

    def status(self):
        if not self.process or self.process.poll() is not None:
            if self.process:self.close()
            return {'connected':False,'session_active':False,'target_state':'unknown',
                    'target_link':'unverified','checked_at':time.time(),'logs':list(self.logs)}
        started=time.monotonic()
        try:
            self.command(f'{self.target} arp_poll', timeout=2)
            target=self.command(f'{self.target} curstate', timeout=2)
            healthy=target in ('running','halted')
            error='' if healthy else '目标状态：'+target
        except Exception as exc:
            target='unknown';healthy=False;error=str(exc)
        return {'connected':healthy,'session_active':bool(self.process),'target_state':target,
                'target_link':'online' if healthy else 'error','target_error':error,
                'checked_at':time.time(),'latency_ms':round((time.monotonic()-started)*1000),
                'identity':self.identity,'host':self.host,
                'transport':self.transport,'breakpoints':list(self.breakpoints.values()),'logs':list(self.logs)}

    def registers(self):
        if self.command(f'{self.target} curstate')!='halted':raise RuntimeError('请先暂停目标，再读取内核寄存器')
        # Cortex-M invalidates its register cache on resume/step and refreshes
        # context on debug entry. Do not read every register a second time.
        raw=self.command('get_reg {r0 r1 r2 r3 r4 r5 r6 r7 r8 r9 r10 r11 r12 sp lr pc xpsr}')
        values=raw.split()
        return {values[i]:values[i+1] for i in range(0,len(values),2)}

    def close(self):
        if self.rpc:
            try:self.rpc.sendall(b'shutdown\x1a')
            except OSError:pass
            self.rpc.close();self.rpc=None
        if self.process:
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate();self.process.wait(timeout=3)
            self.process=None
        self.identity={};self.breakpoints={}
        self.profile=None;self.flash_ranges=[]

    def action(self, name, body):
        if name=='probe-package':return probe_upgrade.inspect(body)
        if name=='probe-upgrade':
            if self.process:raise RuntimeError('升级前请先结束 STM32 调试会话')
            enabled=PROBES.enabled
            PROBES.set_enabled(False)
            try:return probe_upgrade.install(body,self.logs.append,PROGRESS.stage)
            finally:PROBES.set_enabled(enabled)
        if name=='probe-disconnect':
            result=self.action('disconnect', {})
            PROBES.set_enabled(False)
            return dict(result, probe_enabled=False)
        if name=='probe-reconnect':
            PROBES.set_enabled(True)
            return dict(self.status(), probe_enabled=True)
        if name=='connect' and not PROBES.enabled:
            raise RuntimeError('探针已手动断开，请先点击重新连接')
        if name=='connect':return self.connect(body)
        if name=='disconnect':
            # Remove only breakpoints owned by this service, then resume on explicit disconnect.
            if self.process:
                for bp in list(self.breakpoints.values()):self.remove_breakpoint(bp['address'])
                if self.command(f'{self.target} curstate')=='halted':self.command('resume')
            self.close();return self.status()
        if name=='registers':return {'registers':self.registers()}
        if name=='memory':
            if self.command(f'{self.target} curstate')!='halted':raise RuntimeError('请先暂停目标，避免运行态内存读取返回无效值')
            address=number(body['address'])
            if address>0xffffffe0 or address%4:raise ValueError('请使用可容纳 32 字节的四字节对齐地址')
            return {'address':address,'words':self.read(address,32,8)}
        if name in ('halt','resume','step','reset'):
            if name=='resume' and self.command(f'{self.target} curstate')=='running':return self.status()
            if name=='step' and self.command(f'{self.target} curstate')!='halted':raise RuntimeError('请先暂停目标')
            self.command({'halt':'halt 2000','resume':'resume','step':'step','reset':'reset run'}[name])
            result=self.status()
            if result['target_state']=='halted':result['registers']=self.registers()
            return result
        if name=='breakpoint':
            address=number(body['address'])
            if address%2:raise ValueError('断点地址必须半字对齐')
            if address in self.breakpoints:raise ValueError('该地址已有断点')
            if self.command(f'{self.target} curstate')!='halted':raise RuntimeError('请先暂停目标再添加断点')
            kind=body.get('kind','hardware')
            if kind=='write':
                if address%4:raise ValueError('写观察点需要四字节对齐')
                self.command(f'wp {address} 4 w')
            elif kind=='hardware':self.command(f'bp {address} 2 hw')
            else:raise ValueError('不支持的断点类型')
            self.breakpoints[address]={'address':address,'kind':kind}
            return self.status()
        if name=='remove-breakpoint':self.remove_breakpoint(number(body['address']));return self.status()
        if name=='erase':
            if not self.identity:raise RuntimeError('请先识别目标')
            if self.breakpoints:raise RuntimeError('请先移除断点再整片擦除')
            self.command('reset init',timeout=15)
            self.erase_main_flash()
            result=self.status()
            if not result.get('connected') or result.get('target_state')!='halted':
                raise RuntimeError('擦除命令已结束，但无法确认目标暂停状态')
            return result
        if name=='flash':return self.flash(body)
        raise ValueError('不支持的操作')

    def remove_breakpoint(self,address):
        bp=self.breakpoints[address]
        self.command(f'{"rwp" if bp["kind"]=="write" else "rbp"} {address}')
        del self.breakpoints[address]

    def erase_main_flash(self):
        main_banks=[];info=[]
        for index in range(int(self.command('llength [flash list]'))):
            base=int(self.command(f'dict get [lindex [flash list] {index}] base'),0)
            if not 0x08000000<=base<0x08400000:continue
            info.append(self.command(f'flash info {index} sectors',timeout=5))
            main_banks.append(index)
        actual=flash_ranges(info,self.identity['flash_kib'])
        if actual!=self.flash_ranges:raise RuntimeError('Flash 布局已变化，请重新连接识别')
        for position,index in enumerate(main_banks,1):
            PROGRESS.stage(f'整片擦除主 Flash · Bank {position}/{len(main_banks)}')
            self.command(f'flash erase_sector {index} 0 last',timeout=120)

    def flash(self,body):
        if not self.identity:raise RuntimeError('请先识别目标')
        erase=body.get('erase')
        if erase not in ('covered','all'):raise ValueError('不支持的擦除范围')
        suffix=Path(body.get('name','')).suffix.lower()
        if suffix not in ('.bin','.hex','.elf'):raise ValueError('固件格式不支持')
        data=base64.b64decode(body['data'],validate=True)
        if not data or len(data)>4*1024*1024:raise ValueError('镜像必须为 1 字节至 4 MiB')
        address=''
        if suffix=='.bin':
            offset=number(body['address'])
            if not contains_image(self.flash_ranges, offset, len(data)):raise ValueError('BIN 超出目标 Flash 范围')
            address=f' {offset}'
        elif suffix=='.elf' and not data.startswith(b'\x7fELF'):raise ValueError('ELF 文件头无效')
        elif suffix=='.hex' and not data.lstrip().startswith(b':'):raise ValueError('HEX 文件头无效')
        if self.breakpoints:raise RuntimeError('请先移除本服务设置的断点再烧录')
        with tempfile.TemporaryDirectory(prefix='amphilink-image-') as directory:
            path=Path(directory)/('image'+suffix);path.write_bytes(data)
            # Parse the complete image before any destructive operation.
            self.command(f'test_image {{{path.as_posix()}}}{address}',timeout=15)
            PROGRESS.stage('1/4 复位并准备烧录')
            self.command('reset init',timeout=15)
            if erase=='all':
                self.erase_main_flash()
            write_mode=' erase' if erase=='covered' else ''
            PROGRESS.stage('2/4 写入 STM32' if erase=='all' else '2/4 擦除并写入 STM32')
            self.command(f'flash write_image{write_mode} {{{path.as_posix()}}}{address}',timeout=90)
            if body.get('verify',True):
                PROGRESS.stage('3/4 校验 STM32 镜像')
                self.command(f'verify_image {{{path.as_posix()}}}{address}',timeout=90)
            if body.get('run',True):
                PROGRESS.stage('4/4 复位并运行 STM32')
                self.command('reset run',timeout=15)
        result=self.status()
        if not result.get('connected'):
            raise RuntimeError('写入操作已结束，但目标连接状态未确认，请检查目标')
        if body.get('run',True) and result.get('target_state')!='running':
            raise RuntimeError('写入操作已结束，但目标运行状态未确认')
        return result

DEBUG=Debugger()
atexit.register(DEBUG.close)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,body):
        data=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(data)
    def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{PORT}'
    def do_GET(self):
        if not self.valid_host():return self.reply(403,{'error':'仅允许本机访问'})
        path=urlsplit(self.path).path
        if path=='/api/health':return self.reply(200,{'service':'amphilink-local','distribution':'rlyoulink-portable','version':'3.0.1','instance':INSTANCE})
        if path=='/api/progress':return self.reply(200,PROGRESS.snapshot())
        if path=='/api/logs':return self.reply(200,{'logs':list(DEBUG.logs)})
        if path=='/api/links':
            try:return self.reply(200,PROBES.snapshot(parse_qs(urlsplit(self.path).query).get('host',[None])[0]))
            except ValueError as exc:return self.reply(400,{'error':str(exc)})
        if path=='/api/state':
            if not LOCK.acquire(blocking=False):return self.reply(409,{'error':'设备操作进行中'})
            try:self.reply(200,dict(DEBUG.status(),token=TOKEN,probe_enabled=PROBES.enabled))
            except Exception as e:self.reply(503,{'error':str(e)})
            finally:LOCK.release()
            return
        name='index.html' if path=='/' else path.lstrip('/')
        if name not in ('index.html','style.css','app.js','network.js','backend.js','links.js','upgrade.js','progress.js'):return self.reply(404,{'error':'not found'})
        data=(ROOT/name).read_bytes()
        self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin')!=f'http://127.0.0.1:{PORT}' or self.headers.get('X-AmphiLink-Token')!=TOKEN:
            return self.reply(403,{'error':'请从本地上位机页面发起操作'})
        # Brief state reads from other windows must not reject a user's command.
        # A long operation still returns Busy after a bounded wait.
        if not LOCK.acquire(timeout=3):return self.reply(409,{'error':'设备操作进行中'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<6*1024*1024:raise ValueError('请求大小无效')
            self.connection.settimeout(10)
            body=json.loads(self.rfile.read(length))
            action=urlsplit(self.path).path.removeprefix('/api/')
            tracked = action in ('flash','erase','probe-upgrade')
            if tracked: PROGRESS.begin('stm32' if action in ('flash','erase') else 'esp32')
            try:
                result=DEBUG.action(action,body)
            except Exception as exc:
                if tracked: PROGRESS.finish(exc)
                raise
            if tracked:
                PROGRESS.finish()
                if action=='erase': PROGRESS.update(detail='主 Flash 已擦除，目标保持暂停；尚未写入程序')
                if action=='flash' and not body.get('verify',True):
                    PROGRESS.update(detail='写入完成，用户未启用镜像校验')
            self.reply(200,result)
        except Exception as e:self.reply(400,{'error':str(e),'logs':list(DEBUG.logs)})
        finally:LOCK.release()

if __name__=='__main__':
    PROBES.start()
    print(f'AmphiLink UI: http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
