from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parent
build=Path(os.environ['TEMP'])/'rlyoulink-build/build'
out=root/'rlyoulink-release';out.mkdir(exist_ok=True)
for source,name in [('rlyoulink.bin','application.bin'),('bootloader/bootloader.bin','bootloader.bin'),('partition_table/partition-table.bin','partition-table.bin')]:
    shutil.copyfile(build/source,out/name)
subprocess.run([sys.executable,str(root/'rlyou_release.py'),'pack',str(out/'application.bin'),
                '--output',str(out/'rlyoulink-xiaos3-d2-3.0.0.amphipkg')],check=True)
(out/'bootstrap-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.iterdir() if p.suffix in ('.bin','.amphipkg')},indent=2),encoding='utf-8')
print(out)
