#!/usr/bin/env python3
"""Verify and exclusively copy only the complete pinned Qwen generated frontend."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/hbm_qwen_cxx_r10_20261002'
EXPECTED_ROOT=Path('/home/ubuntu/OpenTallas-hbm-qwen-cxx-r10')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def entries():return [json.loads(x)for x in(OUT/'frontend_inventory.jsonl').read_text().splitlines()]
def verify(require_root=True):
 m=load(OUT/'frontend_manifest.json');prior=Path(m['original_output']);old=OUT/'parent_checkpoint'
 if require_root and ROOT!=EXPECTED_ROOT:raise ValueError('qualified Qwen CXX source root changed')
 for name,pin in m['parent_checkpoint_pins'].items():
  if sha(old/name)!=pin:raise ValueError('parent checkpoint changed: '+name)
  record=m['parent_checkpoint_path']+'/'+name
  if subprocess.check_output(['git','show',m['parent_checkpoint_commit']+':'+record],cwd=ROOT)!=(old/name).read_bytes():raise ValueError('committed parent checkpoint mismatch')
 oldroot=Path(m['original_source_root'])
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=oldroot,text=True).strip()!=m['original_source_commit'] or subprocess.check_output(['git','status','--porcelain'],cwd=oldroot,text=True):raise ValueError('original source worker must remain clean and frozen')
 go=load(old/'GO.json');p=load(old/'proposal.json');v=load(old/'verdict.json');end=load(old/'Qwen-frontend-end.json')
 if go['source_commit']!=m['original_source_commit'] or v['source_commit']!=m['original_source_commit'] or sha(old/'proposal.json')!=m['original_proposal_sha256'] or go['proposal_sha256']!=m['original_proposal_sha256'] or p['source_sha256']!=m['source_sha256'] or p['gate_tool_sha256']!=m['gate_tool_sha256'] or p['verified_toolchain']!=m['verified_toolchain']:raise ValueError('qualified source/tool/frame provenance mismatch')
 if v['source_sha256']!=m['source_sha256'] or v['proposal_sha256']!=m['original_proposal_sha256'] or v['GO_sha256']!=sha(old/'GO.json') or go['runner_caps']!=p['runner_caps']:raise ValueError('original verdict/GO caps provenance mismatch')
 expected=[x.replace('<fresh-output>',m['original_output'])for x in p['commands']['Qwen'][0]['argv']]
 if expected!=m['frontend_argv']:raise ValueError('original frontend frame argv changed')
 if subprocess.check_output(['git','show',m['original_GO_commit']+':'+m['original_GO_record_path']],cwd=ROOT)!=(old/'GO.json').read_bytes():raise ValueError('original committed GO mismatch')
 for name in ['GO.json','proposal.json','verdict.json','Qwen-frontend-end.json']:
  if(prior/name).read_bytes()!=(old/name).read_bytes():raise ValueError('original failure/frontend receipt changed')
 if end['exit_code']!=0 or end['termination_reason']is not None or end['argv']!=m['frontend_argv']:raise ValueError('successful complete frontend required')
 for bundle in ('source_sha256','gate_tool_sha256'):
  for name,pin in m[bundle].items():
   if sha(ROOT/name)!=pin or sha(oldroot/name)!=pin:raise ValueError('source/tool changed: '+name)
 for name,pin in m['verified_toolchain']['files_sha256'].items():
  if sha(name)!=pin:raise ValueError('compiler changed: '+name)
 if sha(OUT/'frontend_inventory.jsonl')!=m['frontend_inventory_sha256'] or sha(OUT/'expected_archive_objects.json')!=m['expected_archive_objects_sha256']:raise ValueError('complete inventory changed')
 kit=entries();allowed={'.cpp','.h','.mk','.dat'};source=prior/'Qwen/obj'
 if len(kit)!=m['frontend_files'] or sum(x['bytes']for x in kit)!=m['frontend_bytes'] or len({x['path']for x in kit})!=len(kit):raise ValueError('inventory census changed')
 wanted={Path(x['path']).name for x in kit}
 if {p.name for p in source.iterdir()if p.suffix in allowed}!=wanted:raise ValueError('frontend inventory incomplete or changed')
 for x in kit:
  path=Path(x['path'])
  if path.parent!=Path('Qwen/obj')or path.suffix not in allowed:raise ValueError('partial object/PCH/archive or invalid path in frontend inventory')
  f=prior/path
  if f.is_symlink()or not f.is_file()or f.stat().st_size!=x['bytes']or sha(f)!=x['sha256']:raise ValueError('generated frontend changed: '+str(path))
 return m

def copy_kit(prior,kit,destination):
 destination=Path(destination)
 if destination.exists()or destination.is_symlink():raise ValueError('exclusive fresh object directory required')
 destination.mkdir(parents=True)
 total=0
 for x in kit:
  path=Path(x['path'])
  if path.parent!=Path('Qwen/obj')or path.suffix not in {'.cpp','.h','.mk','.dat'}:raise ValueError('forbidden reused artifact')
  src=Path(prior)/path;dst=destination/path.name;h=hashlib.sha256();count=0
  with os.fdopen(os.open(src,os.O_RDONLY|os.O_NOFOLLOW),'rb')as f,dst.open('xb')as g:
   before=os.fstat(f.fileno())
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block);count+=len(block);g.write(block)
   after=os.fstat(f.fileno())
  if(before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns)or count!=x['bytes']or h.hexdigest()!=x['sha256']or sha(dst)!=x['sha256']or sha(src)!=x['sha256']:raise ValueError('frontend changed during exclusive copy')
  total+=count
 return dict(verdict='PASS_EXCLUSIVE_COMPLETE_QWEN_FRONTEND_ONLY',files=len(kit),bytes=total,objects_PCH_archive_binary_reused=False,old_frontend_unchanged=True,hardlinks=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);parser.add_argument('--proposal',type=Path,required=True);parser.add_argument('--go',type=Path,required=True);parser.add_argument('--go-commit',required=True);a=parser.parse_args()
 import run_hbm_qwen_cxx_r10 as R
 go=load(a.go);p=load(a.proposal);R.validate_go(go,a.proposal,R.G.git('rev-parse','HEAD'));R.validate_cgroup(go)
 if R.G.git('status','--porcelain'):raise ValueError('clean pinned worker required')
 if subprocess.check_output(['git','show',a.go_commit+':'+go['admission_record_path']],cwd=ROOT)!=a.go.read_bytes():raise ValueError('fresh committed GO required')
 if sha(OUT/'frontend_manifest.json')!=p['frontend_manifest_sha256']or a.destination!=Path(go['output_path'])/'Qwen/obj':raise ValueError('GO manifest/output mismatch')
 m=verify();receipt=copy_kit(m['original_output'],entries(),a.destination);verify()
 with(a.destination.parent/'reuse_frontend_receipt.json').open('x')as f:f.write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps(receipt,sort_keys=True))
