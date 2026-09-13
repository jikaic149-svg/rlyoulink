from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
root = Path(SPECPATH)
src = root/'src'
hidden = ['server','links','probe_upgrade','progress','targets','probe_device','runtime']
for package in ('esptool','cryptography','usb','serial','pystray'):
    hidden += collect_submodules(package)
datas = [(str(p), str(p.parent.relative_to(src)))
         for folder in ('ui','maintenance') for p in (src/folder).rglob('*')
         if p.is_file() and '__pycache__' not in p.parts and 'tests' not in p.parts
         and p.suffix != '.pyc']
datas += collect_data_files('esptool')
a = Analysis([str(src/'launcher.py'), str(src/'worker.py')],
    pathex=[str(src),str(src/'ui'),str(src/'maintenance')],
    datas=datas, hiddenimports=hidden, excludes=['tkinter'], noarchive=False)
pyz = PYZ(a.pure)
gui_scripts = [entry for entry in a.scripts if entry[0] != 'worker']
worker_scripts = [entry for entry in a.scripts if entry[0] != 'launcher']
gui = EXE(pyz, gui_scripts, [], exclude_binaries=True, name='rlyoulink',
    console=False, icon=str(root/'payload/assets/rlyoulink.ico'))
worker = EXE(pyz, worker_scripts, [], exclude_binaries=True, name='rlyoulink-worker',
    console=True, icon=str(root/'payload/assets/rlyoulink.ico'))
coll = COLLECT(gui, worker, a.binaries, a.datas, strip=False, upx=False, name='rlyoulink-portable-win64')
