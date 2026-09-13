"""Assemble redistributable licenses and project sources; never print keys."""
from pathlib import Path
import importlib.metadata as metadata
import shutil, tarfile, json
root=Path(__file__).resolve().parent
payload=root/'payload'
licenses=payload/'licenses'
versions={}
for dist in metadata.distributions():
    name=dist.metadata['Name']; versions[name]=dist.version
    for file in dist.files or []:
        if any(word in file.name.lower() for word in ('license','copying','notice')):
            path=Path(dist.locate_file(file))
            if path.is_file():
                target=licenses/'python-packages'/name/str(file).replace('..','_').replace(':','_')
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,target)
(licenses/'python-packages.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
import sys
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists(): shutil.copy2(python_license,licenses/'PYTHON-LICENSE.txt')
for archive in licenses.glob('*.tar.gz'):
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            if member.isfile() and ('/LICENSES/' in member.name or member.name.count('/')==1 and member.name.split('/')[-1].lower() in ('license','copying','license.terms')):
                relative=Path(member.name)
                if '..' in relative.parts: continue
                target=licenses/'openocd-licenses'/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(tf.extractfile(member).read())
source=payload/'source'
shutil.copytree(root/'src',source/'src',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('rlyoulink.spec','requirements-build.txt','BUILD.md','prepare_payload.py'):
    shutil.copy2(root/name,source/name)
