"""Read maintenance identity or enter ROM on the selected probe."""
import argparse,time
import usb.core,usb.util
from serial.tools import list_ports
from probe_device import device

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--enter',action='store_true');args=parser.parse_args()
    dev=device()
    try:
        serial=usb.util.get_string(dev,dev.iSerialNumber).upper()
        data=bytes(dev.ctrl_transfer(0xC0,0x42,0,0xA11F,8,timeout=2000))
        if data!=b'ALUP\x01\x01\x00\x00':raise RuntimeError('USB maintenance protocol unsupported')
        print('USB maintenance supported')
        if not args.enter:return
        dev.ctrl_transfer(0x40,0x42,0xB007,0xA11F,b'',timeout=2000)
    finally:usb.util.dispose_resources(dev)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        for port in list_ports.comports():
            if port.vid==0x303A and (port.serial_number or '').replace(':','').upper()==serial:
                print('Download port: '+port.device);return
        time.sleep(.25)
    raise RuntimeError('下载串口未出现，请检查驱动或进入 BOOT 模式')

if __name__=='__main__':main()
