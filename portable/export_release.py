"""Copy a clean tested distribution and create a checked ZIP."""
from pathlib import Path
import shutil,sys,hashlib,json,zipfile
root=Path(__file__).resolve().parent
source=root/'dist/rlyoulink-portable-win64'
shutil.copytree(root/'payload',source,dirs_exist_ok=True)
destination=Path(sys.argv[1]).resolve()
archive=destination.with_suffix('.zip')
if destination.exists() or archive.exists(): raise SystemExit('Output already exists; refusing to replace it')
shutil.copytree(source,destination,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.log','app.lock','runtime.json'))
files={p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(destination.rglob('*')) if p.is_file()}
assert 'publisher/keys/rlyoulink-private.pem' in files
assert '.agents/skills/rlyoulink/SKILL.md' in files
assert not any('/.agents/.agents/' in name for name in files)
(destination/'SHA256SUMS.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(destination.rglob('*')):
        if p.is_file():z.write(p,destination.name+'/'+p.relative_to(destination).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in files.items():
        assert hashlib.sha256(z.read(destination.name+'/'+name)).hexdigest()==digest
archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='ascii')
print(json.dumps({'files':len(files),'zip_bytes':archive.stat().st_size,'zip_integrity':'passed','folder':str(destination)},ensure_ascii=False))
