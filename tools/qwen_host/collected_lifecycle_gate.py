#!/usr/bin/env python3
"""Component protocol regression; no native engine/die qualification claim."""
from pathlib import Path
import json,subprocess,tempfile,os
r=Path(__file__).resolve().parents[2]
leaf='rtl/qwen_sys/host_integrated_20261014/qkd_host_lifecycle_collected.sv'
paths=['rtl/test/qwen_host/tb_qkd_host_lifecycle_collected.sv',leaf,'rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv','rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_cohort.sv']
out={}
for mutant in [False,True]:
 with tempfile.TemporaryDirectory() as d:
  files=[]
  for p in paths:
   s=(r/p).read_text()
   if mutant and p==leaf:s=s.replace('(post_pending && cancel_tag','(1\'b0 && post_pending && cancel_tag')
   q=Path(d)/Path(p).name;q.write_text(s);files.append(str(q))
  subprocess.run(['iverilog','-g2012','-s','tb_qkd_host_lifecycle_collected','-o',d+'/sim',*files],check=True,capture_output=True)
  p=subprocess.run(['vvp',d+'/sim'],capture_output=True,text=True,timeout=30)
  assert (p.returncode==0)==(not mutant),(mutant,p.stdout,p.stderr)
  out['late_ack_mutant' if mutant else 'positive']={'returncode':p.returncode,'stdout':p.stdout}
print(json.dumps(out,indent=2))
