#!/usr/bin/env python3
"""Preserve the seven h1v source archives on measured EPYC3 storage."""
import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
HOST='ot-epyc3'; DEST='/srv/opentallas-scratch/codex-takeover-20261010/local-archive-preserve/h1v'
FILES=sorted(p for p in Path('/tmp/h1v').glob('*.tar') if p.stat().st_size>2**30)
assert len(FILES)==7
NAMES=[str(p) for p in FILES]
def invoke(args,**kw):
    r=subprocess.run(args,check=True,text=True,capture_output=True,**kw)
    return r.stdout
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*2**20): h.update(b)
    return h.hexdigest()
def signature(p):
    s=p.stat();return (s.st_ino,s.st_size,s.st_mtime_ns)
def dependencies():
    # Query running processes as root, retaining cwd/fd/argv/environment privacy.
    code='''import json,os,sys
paths=json.loads(sys.argv[1]); blocked=[]
for pid in os.listdir('/proc'):
 if not pid.isdigit():continue
 pp='/proc/'+pid
 try:
  cwd=os.readlink(pp+'/cwd');cmd=open(pp+'/cmdline','rb').read().decode(errors='replace');env=open(pp+'/environ','rb').read().decode(errors='replace')
  fds=[]
  for fd in os.listdir(pp+'/fd'):
   try:fds.append(os.readlink(pp+'/fd/'+fd))
   except OSError:pass
  if cwd=='/tmp/h1v' or cwd.startswith('/tmp/h1v/') or any(p in cmd+' '+env or p in fds for p in paths):blocked.append(pid)
 except FileNotFoundError:pass
 except PermissionError:blocked.append(pid)
 except OSError:pass
print(json.dumps(blocked))
'''
    # Do not put the archive list in argv: it would self-match the process probe.
    code=code.replace('paths=json.loads(sys.argv[1]);','paths='+repr(NAMES)+';')
    blocked=json.loads(invoke(['sudo','-n','python3','-'],input=code))
    if blocked:raise RuntimeError('live archive dependencies: '+','.join(blocked))
    for base in (Path('/home/ubuntu/.local/state/closure_loop/jobs'),Path('/home/ubuntu/OpenTallas/tools/closure_loop/jobs'),Path('/home/ubuntu/wt-codex-closure-daemon-20261007l/tools/closure_loop/jobs')):
        for f in base.glob('*.json'):
            raw=f.read_text(errors='replace')
            # Any specification reference is retained, even if terminal, because
            # retry may use the original source archive again.
            if any(p in raw or Path(p).name in raw for p in NAMES):raise RuntimeError('queued/retry archive reference: '+str(f))
    if any(Path('/tmp/h1v').rglob('.keep')):raise RuntimeError('.keep')

dependencies()
required=sum(p.stat().st_size for p in FILES)
capacity=invoke(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',HOST,'python3 -'],input="import shutil,json\nprint(json.dumps(shutil.disk_usage('/srv/opentallas-scratch')._asdict()))\n")
assert json.loads(capacity)['free']>required
invoke(['ssh','-o','BatchMode=yes',HOST,'mkdir -p '+shlex.quote(DEST)+' && touch '+shlex.quote(DEST+'/.keep')])
receipt={'schema':'opentallas.source_archive_preserve.v1','host':HOST,'destination':DEST,'measured_capacity_before':json.loads(capacity),'files':[]}
receipt_path=HERE/'h1v_archive_preservation.json'
local_manifest=Path('/tmp/h1v/PRESERVED_ARCHIVES_20261010.json')
def record():
    text=json.dumps(receipt,indent=2)+'\n';receipt_path.write_text(text);local_manifest.write_text(text)
    invoke(['ssh','-o','BatchMode=yes',HOST,'cat > '+shlex.quote(DEST+'/PRESERVED_ARCHIVES_20261010.json')],input=text)
for p in FILES:
    sig=signature(p);digest=sha(p)
    row={'original':str(p),'bytes':sig[1],'sha256':digest,'new_home':HOST+':'+DEST+'/'+p.name,'verified':False,'local_removed':False,'restore_command':'rsync -a -- '+HOST+':'+DEST+'/'+p.name+' '+str(p)}
    receipt['files'].append(row);record()
    print('COPY '+p.name+' '+str(sig[1])+' bytes',flush=True)
    invoke(['rsync','-a','--partial','--',str(p),HOST+':'+DEST+'/'])
    remote_code='import hashlib\nh=hashlib.sha256()\nwith open('+repr(DEST+'/'+p.name)+",'rb') as f:\n while b:=f.read(8*2**20): h.update(b)\nprint(h.hexdigest())\n"
    remote_hash=invoke(['ssh','-o','BatchMode=yes',HOST,'python3 -'],input=remote_code).strip()
    assert remote_hash==digest and signature(p)==sig,'archive copy changed'
    row['verified']=True;record()
    dependencies()
    # Re-read the exact local source hash before unlinking. The durable receipts
    # and remote .keep preserve restoration even if later work needs this path.
    assert sha(p)==digest and signature(p)==sig
    p.unlink();row['local_removed']=True;record()
    print('PRESERVED_AND_RECLAIMED '+p.name,flush=True)
receipt['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());record()
print('RECLAIMED_BYTES '+str(required),flush=True)
