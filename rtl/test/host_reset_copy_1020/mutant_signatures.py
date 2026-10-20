#!/usr/bin/env python3
from pathlib import Path
import sys,shutil,tempfile,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
import actual_signature as A
r=Path.cwd();s=json.loads((r/'rtl/test/host_cdc_safe_1020/host_sram1.json').read_text())
files=set(s['sources'])|{'physical/common_flow/ot_keep_regs.tcl','rtl/test/host_cdc_safe_1020/host_sram1.json'}
for m in s['macros']:
 files.update(str(p.relative_to(r)) for p in (r/m['view']).iterdir())
results={}
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 for f in files:
  p=root/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/f,p)
 p=root/'rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_visibility_fence_sram.sv'
 baseline=p.read_text()
 target='''always @(posedge ck or negedge rst_n)
    if(!rst_n)req_copy[k]<=0;
    else req_copy[k]<=req_next;'''
 assert baseline.count(target)==1
 mutants=dict(wrong_D=target.replace('<=req_next;','<=~req_next;'),wrong_clock=target.replace('posedge ck','posedge clk_h'),missing_reset='always @(posedge ck)req_copy[k]<=req_next;',wrong_value=target.replace('req_copy[k]<=0','req_copy[k]<=1'))
 A.verify(root);results['exact']='PASS'
 for name,wrong in mutants.items():
  p.write_text(baseline.replace(target,wrong))
  try:A.verify(root)
  except (ValueError,AssertionError) as e:results[name]='REFUSED '+str(e)
  else:raise AssertionError('mutation not caught '+name)
 out=r/'reset_copy_proof/actual_mutants.json';out.write_text(json.dumps(results,indent=2)+'\n');print(out)
