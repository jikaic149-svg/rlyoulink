from pathlib import Path
import sys

FROZEN=bool(getattr(sys,'frozen',False))
BASE=Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent/'payload'
RESOURCES=Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent
UI=RESOURCES/'ui'
MAINTENANCE=RESOURCES/'maintenance'
OPENOCD=BASE/'tools/openocd'
PUBLIC=BASE/'publisher/keys/release_public.pem'
PRIVATE=BASE/'publisher/keys/rlyoulink-private.pem'

def worker(task,*args,serial=None):
    command=[str(BASE/'rlyoulink-worker.exe')] if FROZEN else [sys.executable,str(RESOURCES/'worker.py')]
    command+=['--task',task]
    if serial:command+=['--serial',serial]
    return command+list(map(str,args))
