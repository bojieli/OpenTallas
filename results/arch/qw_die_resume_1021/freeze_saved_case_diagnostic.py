"""Freeze exact already-captured physical/source inputs, never regenerate GEN."""
from pathlib import Path
import argparse, hashlib, json
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('root',type=Path)
a=ap.parse_args();root=a.root.resolve()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
files=[]
# All emitted case inputs plus actual RTL/tool code and physical native sources,
# abstract geometry, parameter/spec/closure metadata. Include selection decisions.
for directory in ('out','src/rtl','src/tools','src/physical'):
 for p in (root/directory).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and (directory=='out' or p.suffix in ('.v','.sv','.svh','.py','.sh','.tcl','.lef','.lib','.json','.gz')):
   files.append(p)
for p in ('out.log','src/SOURCE_COMMIT','src/results/arch/qwen_split_compute_1014/bind_view_select.json',
          'src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json',
          'pre_bind/port_bind.json','pre_bind/lane_latency_audit.txt','pre_bind/record_bundle_audit.txt',
          'pre_bind/die_param_audit.txt','pre_bind/hr_contract.txt','reset_sync_audit.txt','hier_check.line',
          'diagnostic_compiler_failure.json','diagnostic_open_classification.json',
          'reset_projection_diag1340/verdict.json','reset_release_prior_g4try3.json'):
 files.append(root/p)
manifest=dict(schema='opentallas.saved_case_physical_diagnostic.v1',original_gen_exit=1,compiler_verdict='FAIL',
 qualification_eligible=False,compiler_scope='retained r6b legacy L1 diagnostic failure; no selected coherent73 compile result',
 sha256={str(p.relative_to(root)):sha(p)for p in sorted(set(files))})
(root/'saved_case_diagnostic_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('FROZEN_DIAGNOSTIC_INPUTS',len(manifest['sha256']))
