#!/usr/bin/env python3
"""Complete read-only frontend inventory; GO-guarded exclusive verified copy only."""
import argparse,hashlib,json,os,stat,time,subprocess
from pathlib import Path
PRIOR=Path('/tmp/hbm-native-connected-parent-20261002-r1')
GO_COMMIT='858f084a5caaed97f24046e58187d8eee7514adb'
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def files(root):
 if root.is_symlink() or not root.is_dir():raise ValueError('regular inventory root required')
 entries=[]
 for p in sorted(root.iterdir()):
  if p.is_symlink() or not stat.S_ISREG(p.lstat().st_mode):raise ValueError('nonregular generated entry: '+p.name)
  if p.suffix not in ('.cpp','.h','.mk','.d','.dat'):raise ValueError('stale/unexpected build entry: '+p.name)
  if p.suffix=='.d' and p.name!='Vconnected__ver.d':raise ValueError('compiled dependency file present')
  if p.suffix=='.dat' and p.name!='Vconnected__verFiles.dat':raise ValueError('unexpected metadata')
  entries.append(p)
 return entries

def generate():
 go=json.loads((PRIOR/'GO.json').read_text());proposal=json.loads((PRIOR/'proposal.json').read_text());end=json.loads((PRIOR/'DS-frontend-end.json').read_text())
 committed=subprocess.check_output(['git','show',GO_COMMIT+':'+go['admission_record_path']],cwd=ROOT)
 if committed!=(PRIOR/'GO.json').read_bytes():raise ValueError('prior committed GO mismatch')
 if digest(PRIOR/'proposal.json')!=go['proposal_sha256']:raise ValueError('prior proposal mismatch')
 if end['name']!='frontend' or end['target']!='DS' or end['exit_code']!=0 or end['termination_reason'] is not None:raise ValueError('successful DS frontend required')
 expected=proposal['commands']['DS'][0]['argv'];expected=[x.replace('<fresh-output>',str(PRIOR))for x in expected]
 if end['argv']!=expected:raise ValueError('prior actual frontend argv mismatch')
 for p,h in proposal['source_sha256'].items():
  if digest(ROOT/p)!=h:raise ValueError('actual source changed: '+p)
 for p,h in proposal['verified_toolchain']['files_sha256'].items():
  if digest(p)!=h:raise ValueError('tool changed: '+p)
 obj=PRIOR/'DS/obj';inventory=[];oldprefix=str(obj).encode();outrefs=[];sourcerefs=[]
 for p in files(obj):
  before=p.stat();h=hashlib.sha256();tail=b'';output=False;source=False
  with p.open('rb')as f:
   for b in iter(lambda:f.read(1024*1024),b''):
    h.update(b);probe=tail+b;output|=oldprefix in probe;source|=str(ROOT).encode() in probe;tail=probe[-4096:]
  after=p.stat()
  if(before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('generated file changed while hashing')
  if output:outrefs.append(p.name)
  if source:sourcerefs.append(p.name)
  inventory.append({'path':p.name,'bytes':before.st_size,'sha256':h.hexdigest()})
 if outrefs!=['Vconnected__ver.d','Vconnected__verFiles.dat']:raise ValueError('unexpected baked output path in compile inputs: '+str(outrefs))
 mk=(obj/'Vconnected.mk').read_text()
 if 'VERILATOR_ROOT = /home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator' not in mk or '  -O0 \\' not in mk or '  -DVL_TIME_CONTEXT \\' not in mk:raise ValueError('generated kit/flags changed')
 if 'VM_USER_CLASSES = \\\n\n' not in mk:raise ValueError('unreviewed external user C++ inputs')
 return {'schema':'opentallas.DS-successful-frontend.inventory.v1','prior_output':str(PRIOR),'object_root':str(obj),'source_root':str(ROOT),'prior_GO_commit':GO_COMMIT,'prior_source_commit':go['source_commit'],'prior_GO_sha256':digest(PRIOR/'GO.json'),'prior_proposal_sha256':digest(PRIOR/'proposal.json'),'frontend_end_sha256':digest(PRIOR/'DS-frontend-end.json'),'frontend_argv':end['argv'],'frontend_argv_sha256':hashlib.sha256(json.dumps(end['argv'],separators=(',',':')).encode()).hexdigest(),'frontend_wall_s':end['wall_s'],'source_sha256':proposal['source_sha256'],'tool_files_sha256':proposal['verified_toolchain']['files_sha256'],'prior_receipt_pins':{p:digest(PRIOR/p)for p in ['GO.json','proposal.json','run_start.json','DS-frontend-start.json','DS-frontend-end.json','verdict.json','DS/frontend.log']},'files':inventory,'file_count':len(inventory),'total_bytes':sum(x['bytes']for x in inventory),'baked_path_audit':{'old_output_references':outrefs,'absolute_source_root_references':sourcerefs,'generated_mk_sha256':digest(obj/'Vconnected.mk'),'policy':'Copy ALL files unchanged; DEPS= prevents inclusion of original absolute __ver.d; VM_USER_DIR= and explicit VPATH exclude original relative source root. VM_USER_CLASSES empty. -B and fresh empty object directory prohibit stale objects. Compiler flags remain-O0/-DVL_TIME_CONTEXT. Original metadata retained as provenance, unused by make.'}}

def verify_inputs(m):
 for p,h in m['prior_receipt_pins'].items():
  if digest(Path(m['prior_output'])/p)!=h:raise ValueError('prior receipt changed: '+p)
 for p,h in m['source_sha256'].items():
  if digest(ROOT/p)!=h:raise ValueError('source changed: '+p)
 for p,h in m['tool_files_sha256'].items():
  if digest(p)!=h:raise ValueError('tool changed: '+p)
 if Path(m['source_root'])!=ROOT:raise ValueError('source root changed')

def copy_inventory(m,destination,limit_s=300):
 root=Path(m['object_root']);dest=Path(destination);started=time.monotonic()
 want={x['path']:x for x in m['files']}
 if len(want)!=m['file_count'] or len(want)!=len(m['files']) or any(Path(x).name!=x for x in want):raise ValueError('unsafe/duplicate inventory path')
 if {p.name for p in files(root)}!=set(want):raise ValueError('complete inventory changed')
 if dest.exists() or dest.is_symlink() or dest.resolve().is_relative_to(root.resolve()):raise ValueError('exclusive new destination required')
 dest.mkdir(parents=True,exist_ok=False);copied=0
 for name,item in want.items():
  if time.monotonic()-started>=limit_s:raise TimeoutError('reuse copy budget exceeded')
  src=root/name;h=hashlib.sha256();count=0
  fd=os.open(src,os.O_RDONLY|os.O_NOFOLLOW)
  with os.fdopen(fd,'rb')as f,(dest/name).open('xb')as g:
   before=os.fstat(f.fileno())
   if not stat.S_ISREG(before.st_mode):raise ValueError('nonregular input')
   for b in iter(lambda:f.read(1024*1024),b''):
    if time.monotonic()-started>=limit_s:raise TimeoutError('reuse copy budget exceeded')
    h.update(b);count+=len(b);g.write(b)
   after=os.fstat(f.fileno())
  if(before.st_ino,before.st_mtime_ns,before.st_size)!=(after.st_ino,after.st_mtime_ns,after.st_size):raise ValueError('input changed during copy')
  if count!=item['bytes'] or h.hexdigest()!=item['sha256'] or digest(dest/name)!=item['sha256']:raise ValueError('generated content mismatch: '+name)
  copied+=count
 if {p.name for p in files(root)}!=set(want):raise ValueError('inventory changed during copy')
 for name,item in want.items():
  if time.monotonic()-started>=limit_s:raise TimeoutError('reuse post-copy verification budget exceeded')
  if digest(root/name)!=item['sha256']:raise ValueError('old generated content changed after copy: '+name)
 return {'verdict':'PASS_EXCLUSIVE_COMPLETE_FRONTEND_COPY_ONLY','files':len(want),'bytes':copied,'wall_s':time.monotonic()-started,'source_unchanged':True,'compiled_objects_reused':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory-out',type=Path);p.add_argument('--copy',action='store_true');p.add_argument('--manifest',type=Path);p.add_argument('--destination',type=Path);p.add_argument('--proposal',type=Path);p.add_argument('--go',type=Path);p.add_argument('--go-commit');a=p.parse_args()
 if a.inventory_out and not a.copy:
  data=generate()
  with a.inventory_out.open('x')as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
  print('INVENTORIED_READ_ONLY',data['file_count'],data['total_bytes'])
 elif a.copy and all([a.manifest,a.destination,a.proposal,a.go,a.go_commit]):
  import run_hbm_rf_connected_reuse_r5 as R
  go=json.loads(a.go.read_text());R.validate_go(go,a.proposal,R.G.git('rev-parse','HEAD'))
  if subprocess.check_output(['git','show',a.go_commit+':'+go['admission_record_path']],cwd=ROOT)!=a.go.read_bytes():raise ValueError('uncommitted reuse GO')
  if R.G.git('status','--porcelain','--untracked-files=normal'):raise ValueError('clean worktree required')
  R.validate_cgroup(go)
  if digest(a.manifest)!=go['reuse_inventory_sha256']:raise ValueError('GO inventory pin mismatch')
  if a.destination!=Path(go['output_path'])/'DS/obj':raise ValueError('copy destination differs from GO output binding')
  m=json.loads(a.manifest.read_text());verify_inputs(m);v=copy_inventory(m,a.destination);verify_inputs(m);v.update(inventory_sha256=digest(a.manifest),prior_frontend_GO_commit=m['prior_GO_commit'],frontend_end_sha256=m['frontend_end_sha256'],frontend_argv_sha256=m['frontend_argv_sha256'])
  with(a.destination.parent/'reuse_receipt.json').open('x')as f:json.dump(v,f,indent=2)
  print(json.dumps(v))
 else:p.error('read-only inventory mode or GO-bound exclusive copy mode required')
