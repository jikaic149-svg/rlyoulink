from pathlib import Path
import shutil, os
src=Path(__file__).resolve().parent/'firmware-v2'
dst=Path(os.environ['TEMP'])/'rlyoulink-build'
for p in src.rglob('*'):
    if p.is_file():
        q=dst/p.relative_to(src)
        if not q.exists() or p.read_bytes()!=q.read_bytes():
            q.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,q)
print('Build source synchronized')
