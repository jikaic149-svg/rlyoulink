import os,re
import usb.core,usb.util,usb.backend.libusb1
from runtime import OPENOCD

def backend():
    result=usb.backend.libusb1.get_backend(find_library=lambda _:str(OPENOCD/'bin/libusb-1.0.dll'))
    if result is None:raise RuntimeError('缺少随包 libusb，检查 tools/openocd/bin')
    return result

def list_probes():
    items=[]
    for dev in usb.core.find(find_all=True,idVendor=0x303A,idProduct=0x83B3,backend=backend()):
        try:
            serial=usb.util.get_string(dev,dev.iSerialNumber).upper()
            if re.fullmatch(r'[0-9A-F]{12}',serial):items.append(serial)
        finally:usb.util.dispose_resources(dev)
    return sorted(set(items))

def device():
    requested=os.environ.get('RLYOULINK_SERIAL','').upper()
    serials=list_probes()
    if not requested:
        if len(serials)!=1:raise RuntimeError('请连接一台探针，或在上位机选择具体 USB 设备')
        requested=serials[0]
    if requested not in serials:raise RuntimeError('所选 USB 探针未连接，请检查数据线和 WinUSB 驱动')
    for dev in usb.core.find(find_all=True,idVendor=0x303A,idProduct=0x83B3,backend=backend()):
        if usb.util.get_string(dev,dev.iSerialNumber).upper()==requested:return dev
        usb.util.dispose_resources(dev)
    raise RuntimeError('USB 探针已断开')
