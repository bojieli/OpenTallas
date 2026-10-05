import pathlib as P,json,os,subprocess as S,time,hashlib,tarfile,re
paths=['/home/ubuntu/w19-production-recovery','/home/ubuntu/w19-production-protocol.vvp','/home/ubuntu/w19-vvp11','/home/ubuntu/w19-ivl11'];out=P.Path('/tmp/opentallas-maintenance-remote-20261001');records=[]
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

candidates=['/home/ubuntu/qwen-integration-20261001', '/home/ubuntu/qwen-terminal-capture-20261001']

checks={'paths':{path:live(path) for path in candidates},'queue_manifests':[]}
for root in ['/tmp/claude-1000/queue','/home/ubuntu/queue']:
 for p in P.Path(root).glob('*.manifest'):
  b=p.read_bytes();s=b.decode(errors='replace');checks['queue_manifests'].append({'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'candidate_mentions':[path for path in candidates if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',s)]})
print(json.dumps(checks))
