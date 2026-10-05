#!/usr/bin/env python3
"""Qualify and exclusively copy a completed Qwen ELF, never partial objects."""
import argparse,hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED_ROOT=Path('/home/ubuntu/OpenTallas-hbm-qwen-runtime-r11')
OUT=ROOT/'results/uarch/hbm_qwen_runtime_r11_20261002'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def verify(require_root=True):
 if require_root and ROOT!=EXPECTED_ROOT:raise ValueError('qualified runtime source root changed')
 m=load(OUT/'qualified_binary.json');prior=Path(m['original_output']);oldroot=Path(m['source_root'])
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=oldroot,text=True).strip()!=m['source_commit'] or subprocess.check_output(['git','status','--porcelain'],cwd=oldroot,text=True):raise ValueError('qualified original build worker must remain clean and frozen')
 for f,h in m['prior_receipt_sha256'].items():
  if sha(prior/f)!=h or sha(OUT/'qualified_build'/f)!=h:raise ValueError('qualified build receipt changed: '+f)
 for f,h in m['prior_logs_sha256'].items():
  if sha(prior/f)!=h:raise ValueError('qualified build log changed: '+f)
 for bundle in ('source_sha256','gate_tool_sha256'):
  for f,h in m[bundle].items():
   if sha(ROOT/f)!=h or sha(oldroot/f)!=h:raise ValueError('qualified source/tool changed: '+f)
 for bundle in (m['verified_toolchain']['files_sha256'],m['runtime_libraries_sha256']):
  for f,h in bundle.items():
   if sha(f)!=h:raise ValueError('qualified compiler/runtime changed: '+f)
 go=subprocess.check_output(['git','show',m['GO_commit']+':'+m['GO_record_path']],cwd=ROOT)
 if go!=(prior/'GO.json').read_bytes():raise ValueError('original committed build GO mismatch')
 oldgo=json.loads(go);p=load(prior/'proposal.json');v=load(prior/'verdict.json');c=load(prior/'Qwen-CXX-end.json');a=load(prior/'Qwen/CXX_archive_receipt.json')
 if oldgo['source_commit']!=m['source_commit'] or v['source_commit']!=m['source_commit'] or p['source_sha256']!=m['source_sha256'] or p['gate_tool_sha256']!=m['gate_tool_sha256'] or p['verified_toolchain']!=m['verified_toolchain']:raise ValueError('qualified source/tool/frame provenance mismatch')
 if oldgo['proposal_sha256']!=sha(prior/'proposal.json') or v['proposal_sha256']!=oldgo['proposal_sha256'] or v['GO_sha256']!=sha(prior/'GO.json') or oldgo['runner_caps']!=p['runner_caps']:raise ValueError('original verdict/GO/caps provenance mismatch')
 if v['verdict']!='PASS_NATIVE_QWEN_BUILD_ONLY' or c['exit_code']!=0 or c['termination_reason'] is not None or c['argv']!=m['CXX_argv'] or a['archive_members']!=a['generated_objects'] or a['archive_members']!=m['archive']['exact_members'] or a['binary_sha256']!=m['binary']['sha256'] or v['binary_sha256'].get('Qwen/obj/Vconnected')!=m['binary']['sha256']:raise ValueError('qualified complete cold build required')
 review=subprocess.check_output(['git','show',m['parent_review_commit']+':'+m['parent_review_record_path']],cwd=ROOT)
 if hashlib.sha256(review).hexdigest()!=m['parent_review_sha256'] or review!=(OUT/'qualified_build/parent_review.json').read_bytes():raise ValueError('independent committed review changed')
 r=json.loads(review)
 if r['verdict']!='PASS_BUILD_ONLY' or r['source_commit']!=m['source_commit'] or r['binary_sha256']!=m['binary']['sha256'] or r['archive_sha256']!=m['archive']['sha256'] or r['raw_verdict_sha256']!=sha(prior/'verdict.json') or not all(r['checks'].values()):raise ValueError('independent build review required')
 for kind in ('binary','archive'):
  x=m[kind];f=Path(x['path'])
  if f.is_symlink() or not f.is_file() or f.stat().st_size!=x['bytes'] or sha(f)!=x['sha256']:raise ValueError('qualified '+kind+' changed')
 return m

def copy_binary(m,dest):
 src=Path(m['binary']['path']);want=m['binary'];dest=Path(dest)
 if dest.exists() or dest.is_symlink() or dest.resolve()==src.resolve():raise ValueError('exclusive fresh binary destination required')
 dest.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();count=0
 with os.fdopen(os.open(src,os.O_RDONLY|os.O_NOFOLLOW),'rb')as f,dest.open('xb')as g:
  before=os.fstat(f.fileno())
  if not stat.S_ISREG(before.st_mode):raise ValueError('regular qualified ELF required')
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block);count+=len(block);g.write(block)
  after=os.fstat(f.fileno())
 if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('qualified ELF changed during copy')
 if count!=want['bytes'] or h.hexdigest()!=want['sha256'] or sha(dest)!=want['sha256'] or sha(src)!=want['sha256']:raise ValueError('qualified ELF copy hash mismatch')
 os.chmod(dest,want['mode'])
 with dest.open('rb')as f:
  if f.read(4)!=b'\x7fELF':raise ValueError('ELF magic required')
 return dict(verdict='PASS_EXCLUSIVE_QUALIFIED_COMPLETE_QWEN_ELF_COPY',binary_sha256=want['sha256'],bytes=count,old_binary_unchanged=True,objects_PCH_archive_reused=False)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--go',type=Path,required=True);p.add_argument('--go-commit',required=True);a=p.parse_args()
 import run_hbm_qwen_runtime_r11 as R
 go=load(a.go);proposal=load(a.proposal)
 R.validate_go(go,a.proposal,R.G.git('rev-parse','HEAD'));R.validate_cgroup(go)
 if subprocess.check_output(['git','show',a.go_commit+':'+go['admission_record_path']],cwd=ROOT)!=a.go.read_bytes():raise ValueError('fresh committed GO required')
 if R.G.git('status','--porcelain','--untracked-files=normal'):raise ValueError('clean worker required')
 if a.manifest.resolve()!=(OUT/'qualified_binary.json').resolve() or sha(a.manifest)!=proposal['qualified_binary_manifest_sha256'] or a.destination!=Path(go['output_path'])/'Qwen/obj/Vconnected':raise ValueError('GO manifest/output binding mismatch')
 m=verify();v=copy_binary(m,a.destination);verify()
 with(a.destination.parent.parent/'reuse_binary_receipt.json').open('x')as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(v))
