#!/usr/bin/env python3
"""GO-bound complete linked ELF copy; never reuse partial build products."""
import argparse,hashlib,json,os,stat,subprocess,time
from pathlib import Path
import hbm_ds_frontend_reuse as I
ROOT=Path(__file__).resolve().parents[1]
def verify(m,require_root=True):
 if require_root and ROOT!=Path(m['source_root']):raise ValueError('source root changed')
 prior=Path(m['original_output'])
 for f,h in m['prior_receipt_sha256'].items():
  if I.digest(prior/f)!=h:raise ValueError('qualified build receipt changed: '+f)
 for bundle in ('source_sha256','gate_tool_sha256'):
  for f,h in m[bundle].items():
   if I.digest(ROOT/f)!=h:raise ValueError('qualified source/tool changed: '+f)
 for bundle in ('verified_tool_files_sha256','runtime_libraries_sha256'):
  for f,h in m[bundle].items():
   if I.digest(f)!=h:raise ValueError('qualified compiler/runtime changed: '+f)
 committed=subprocess.check_output(['git','show',m['GO_commit']+':'+m['GO_record_path']],cwd=ROOT)
 if committed!=(prior/'GO.json').read_bytes():raise ValueError('original committed build GO mismatch')
 oldgo=json.loads(committed);oldp=json.loads((prior/'proposal.json').read_text());oldv=json.loads((prior/'verdict.json').read_text())
 if oldgo['source_commit']!=m['source_commit'] or oldv['source_commit']!=m['source_commit'] or oldp['source_sha256']!=m['source_sha256'] or oldp['gate_tool_sha256']!=m['gate_tool_sha256'] or oldp['verified_toolchain']['files_sha256']!=m['verified_tool_files_sha256'] or oldv['binary_sha256'].get('DS/obj/Vconnected')!=m['binary']['sha256']:raise ValueError('qualified source/tool/frame provenance mismatch')
 c=json.loads((prior/'DS-CXX-end.json').read_text());a=json.loads((prior/'DS/CXX_archive_receipt.json').read_text())
 if c['exit_code']!=0 or c['termination_reason'] is not None or a!=m['actual_archive_receipt'] or a['archive_members']!=a['generated_objects'] or a['binary_sha256']!=m['binary']['sha256']:raise ValueError('qualified complete CXX/archive required')
 if c['argv']!=m['CXX_argv']:raise ValueError('qualified frame argv changed')
 b=Path(m['binary']['path'])
 if b.is_symlink() or b.stat().st_size!=m['binary']['bytes'] or I.digest(b)!=m['binary']['sha256']:raise ValueError('qualified ELF changed')

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
 if count!=want['bytes'] or h.hexdigest()!=want['sha256'] or I.digest(dest)!=want['sha256'] or I.digest(src)!=want['sha256']:raise ValueError('qualified ELF copy hash mismatch')
 os.chmod(dest,want['mode'])
 with dest.open('rb')as f:
  if f.read(4)!=b'\x7fELF':raise ValueError('ELF magic required')
 return dict(verdict='PASS_EXCLUSIVE_QUALIFIED_COMPLETE_DS_ELF_COPY',binary_sha256=want['sha256'],bytes=count,old_binary_unchanged=True,objects_PCH_archive_reused=False)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--go',type=Path,required=True);p.add_argument('--go-commit',required=True);a=p.parse_args()
 import run_hbm_runtime_calibration_r8 as R
 go=json.loads(a.go.read_text());proposal=json.loads(a.proposal.read_text());R.CAPS=R.P.caps_for(proposal['target'])
 R.validate_go(go,a.proposal,R.G.git('rev-parse','HEAD'));R.validate_cgroup(go)
 if subprocess.check_output(['git','show',a.go_commit+':'+go['admission_record_path']],cwd=ROOT)!=a.go.read_bytes():raise ValueError('fresh committed GO required')
 if R.G.git('status','--porcelain','--untracked-files=normal'):raise ValueError('clean worker required')
 if I.digest(a.manifest)!=proposal['qualified_binary_manifest_sha256'] or a.destination!=Path(go['output_path'])/'DS/obj/Vconnected':raise ValueError('GO manifest/output binding mismatch')
 m=json.loads(a.manifest.read_text());verify(m);v=copy_binary(m,a.destination);verify(m)
 with(a.destination.parent.parent/'reuse_binary_receipt.json').open('x')as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(v))
