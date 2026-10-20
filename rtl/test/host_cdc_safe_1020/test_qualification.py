#!/usr/bin/env python3
"""Causal negative checks of actual elaborated source, no reset/initial-state assumption."""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'tools/ref_tile'))
import gray_fifo_cdc_constraints as G
spec=json.loads((root/'rtl/test/host_cdc_safe_1020/host_sram1.json').read_text())
source='rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_visibility_fence_sram.sv'
original=(root/source).read_text()
mutations={
 'publication':('req_next!=req&&!fc_copy[k]','!fc_copy[k]'),
 'capture':('rc2!=ack_host && rc2!=ack_copy[k]','rc2!=ack_copy[k]'),
 'high_payload_hold':('else if(req_next!=req)snapshot_hi','else snapshot_hi'),
}
results={}
for name,(old,new) in mutations.items():
 assert original.count(old)==1,(name,original.count(old))
 with tempfile.TemporaryDirectory(prefix='host-cdc-'+name+'-') as temp:
  r=Path(temp)
  for rel in spec['sources']+['physical/common_flow/ot_keep_regs.tcl']:
   target=r/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,target)
  for macro in spec['macros']:
   rel=macro['view'];shutil.copytree(root/rel,r/rel,dirs_exist_ok=True)
  (r/source).write_text(original.replace(old,new))
  try:G.lint(spec,r)
  except G.GrayFifoError as e:
   message=str(e)
   expected='capture' if name=='capture' else 'changes while the Gray count holds'
   assert expected in message,(name,message)
   results[name]={'verdict':'REFUSED','message':message,'source_sha256':hashlib.sha256((r/source).read_bytes()).hexdigest()}
  else:raise AssertionError('mutant admitted: '+name)
  print(name,results[name]['message'],flush=True)
Path('qualification_mutants.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS 3 causal CDC source qualification negatives')
