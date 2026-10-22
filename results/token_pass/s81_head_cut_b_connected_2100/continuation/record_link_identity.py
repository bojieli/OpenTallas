from pathlib import Path
import subprocess,hashlib,json,sys
n=sys.argv[1] if len(sys.argv)>1 else 'b'
r=Path.cwd()/'out'/('obj_'+n)
files={}
for p in sorted(r.iterdir()):
 if p.suffix in ('.o','.a') or p.name in ('Vtb_s81hd_diecut','Vtb_s81hd_diecut.mk','Vtb_s81hd_diecut__verFiles.dat'):
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
  files[p.name]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
archive=r/'Vtb_s81hd_diecut__ALL.a'
members=subprocess.run(['ar','t',str(archive)],text=True,capture_output=True,check=True).stdout.splitlines()
assert members and len(members)==len(set(members))
proc=subprocess.Popen(['ar','p',str(archive)],stdout=subprocess.PIPE)
verified=[]
for name in members:
 expected=files[name];remaining=expected['bytes'];h=hashlib.sha256()
 while remaining:
  block=proc.stdout.read(min(8*1024*1024,remaining))
  assert block,('short archive member',name)
  h.update(block);remaining-=len(block)
 assert h.hexdigest()==expected['sha256'],('archive/object mismatch',name)
 verified.append(name)
assert not proc.stdout.read(1) and proc.wait()==0
old=json.loads((Path.cwd()/'retained_build_manifest.json').read_text())
retained={}
if n=='b':
 for path,e in old['files'].items():
  if path.endswith('.o'):
   name=Path(path).name
   assert files[name]==e,('retained object changed',name)
   retained[name]=e
print(json.dumps(dict(phase=n,files=files,archive_members=members,archive_members_exact=verified,retained_objects_unchanged=len(retained)),indent=1))
