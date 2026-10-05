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
for path in paths:
 p=P.Path(path);r={'path':path,'timestamp':time.time()};records.append(r)
 try:
  assert p.exists() and not p.is_symlink(),'absent or symlink';assert p.parent==P.Path('/home/ubuntu');assert not (p/'.git').exists(),'source worktree unexpected'
  r['live_refs']=live(path);assert not r['live_refs'],'live'
  files=sorted(f for f in p.rglob('*') if f.is_file()) if p.is_dir() else [p];items=[];keep=[]
  for f in files:
   assert not f.is_symlink(),'symlink file';b=f.read_bytes();omit=f.suffix=='.vvp';items.append({'relative':str(f.relative_to(p)) if p.is_dir() else f.name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'preserved':not omit})
   if not omit:keep.append(f)
  assert sum(x['bytes'] for x in items if x['preserved'])<20_000_000,'metadata archive too large'
  tar=out/(p.name+'.tar.gz')
  with open(tar,'xb') as stream:
   with tarfile.open(fileobj=stream,mode='w:gz') as t:
    for f in keep:t.add(f,arcname=str(f.relative_to(p)) if p.is_dir() else f.name,recursive=False)
  r.update(files=items,archive=str(tar),archive_sha256=hashlib.sha256(tar.read_bytes()).hexdigest(),allocated_bytes=int(S.check_output(['du','-s','-B1',path],text=True).split()[0]))
 except Exception as e:r['skip_reason']=str(e)
with open(out/'w19_archive_receipt.json','x') as f:json.dump(records,f,indent=2)
print(json.dumps(records))
