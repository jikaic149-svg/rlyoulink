"""Console worker: also the publisher CLI, hidden when invoked by the GUI."""
import argparse,os,sys,runpy,json
from runtime import MAINTENANCE,OPENOCD,UI,BASE
sys.path[:0]=[str(MAINTENANCE),str(UI)]
TASKS={'release':'rlyou_release.py','usb-info':'rlyou_usb_info.py',
       'usb-enter':'upgrade_usb.py','usb-upgrade':'rlyou_usb_upgrade.py','usb-restart':'restart-v2-rom.py'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',required=True,choices=[*TASKS,'esptool','self-test'])
    parser.add_argument('--serial')
    args,remaining=parser.parse_known_args()
    if args.serial:os.environ['RLYOULINK_SERIAL']=args.serial.upper()
    if args.task=='esptool':
        import esptool
        esptool.main(remaining);return
    if args.task=='self-test':
        import cryptography,serial,usb,PIL,pystray,esptool,gen_esp32part
        from rlyou_release import verify
        packages=list((BASE/'firmware').glob('*.amphipkg'))
        assert packages,'Firmware package missing'
        manifest=verify(packages[0])[0]
        import subprocess
        result=subprocess.run([str(OPENOCD/'bin/openocd.exe'),'--version'],capture_output=True,timeout=10)
        assert result.returncode==0,'OpenOCD failed'
        assert (BASE/'publisher/keys/rlyoulink-private.pem').is_file()
        print(json.dumps({'self_test':'passed','firmware':manifest['version'],'runtime':sys.version.split()[0]}));return
    sys.argv=[str(MAINTENANCE/TASKS[args.task]),*remaining]
    runpy.run_path(sys.argv[0],run_name='__main__')

if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if stream is not None:stream.reconfigure(encoding='utf-8',errors='replace',line_buffering=True)
    try:main()
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
