import pathlib as P,json,os,subprocess as S,time,hashlib,tarfile,re
paths=['/home/ubuntu/w19-production-recovery','/home/ubuntu/w19-production-protocol.vvp','/home/ubuntu/w19-vvp11','/home/ubuntu/w19-ivl11'];out=P.Path('/tmp/opentallas-maintenance-remote-20261001');out.mkdir(exist_ok=True);records=[]
# All process cwd/cmd/fd/maps must be readable; do not stop any process.
def live(path):
 hits=[];errors=[]
 for d in P.Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   cmd=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');links=[]
   for n in ['cwd','exe','root']:
    try:links.append(os.readlink(d/n))
    except FileNotFoundError:pass
   for f in (d/'fd').iterdir():
    try:links.append(os.readlink(f))
    except FileNotFoundError:pass
   maps=(d/'maps').read_text(errors='replace')
   if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(x==path or x.startswith(path+'/') for x in links) or path+'/' in maps:hits.append(int(d.name))
  except FileNotFoundError:pass
  except PermissionError:errors.append(str(d))
 ps=S.run(['docker','ps','-aq'],capture_output=True,text=True);assert ps.returncode==0,ps.stderr
 if ps.stdout.split():
  ins=S.run(['docker','inspect',*ps.stdout.split()],capture_output=True,text=True);assert ins.returncode==0,ins.stderr
  for c in json.loads(ins.stdout):
   if not c['State'].get('Running'):continue
   cfg=c['Config'];cwd=cfg.get('WorkingDir','');cmd=' '.join(cfg.get('Cmd') or [])
   if cwd==path or cwd.startswith(path+'/') or re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(m.get('Source','')==path or m.get('Source','').startswith(path+'/') for m in c.get('Mounts',[])):hits.append('docker:'+c['Id'])
 assert not errors,errors;return hits

import shutil
receipts=json.load(open(out/'w19_archive_receipt.json'));actions=[]
for r in receipts:
 path=r['path'];p=P.Path(path);action={'path':path,'timestamp':time.time()};actions.append(action)
 try:
  assert 'archive' in r,'not archived'
  assert hashlib.sha256(P.Path(r['archive']).read_bytes()).hexdigest()==r['archive_sha256'],'archive mismatch'
  assert p.exists() and not p.is_symlink(),'absent/symlink'
  action['live_refs']=live(path);assert not action['live_refs'],'live references'
  for f in r['files']:
   target=p/f['relative'] if p.is_dir() else p
   assert hashlib.sha256(target.read_bytes()).hexdigest()==f['sha256'],'source changed after archival'
  before=os.statvfs('/home/ubuntu');action['free_before']=before.f_bavail*before.f_frsize;action['archive_sha256']=r['archive_sha256'];action['allocated_bytes']=r['allocated_bytes']
  with open(out/(p.name+'_retirement_before.json'),'x') as stream:json.dump(action,stream,indent=2)
  if p.is_dir():shutil.rmtree(p)
  else:p.unlink()
  after=os.statvfs('/home/ubuntu');action['free_after']=after.f_bavail*after.f_frsize;action['filesystem_free_delta']=action['free_after']-action['free_before'];action['removed']=not p.exists()
 except Exception as e:action['skip_reason']=str(e)
with open(out/'w19_retirement_after.json','x') as stream:json.dump(actions,stream,indent=2)
print(json.dumps(actions))
