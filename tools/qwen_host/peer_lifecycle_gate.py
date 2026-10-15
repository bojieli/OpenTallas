#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,json
r=Path(__file__).resolve().parents[2];b='rtl/qwen_sys/host_integrated_20261014/'
paths=['rtl/test/qwen_host/tb_qkd_host_peer_lifecycle.sv']+[b+x+'.sv' for x in ['qkd_host_tp8_coordinator','qkd_host_peer_coordinator_codec','qkd_host_peer_rank_codec','qkd_host_coordinator_services','qkd_host_lifecycle_collected','qkd_host_post_collector','qkd_host_native_token_endpoint_cancel']]+['rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv','rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_cohort.sv']
out={}
for mutant in [False,True]:
 with tempfile.TemporaryDirectory() as d:
  files=[]
  for p in paths:
   s=(r/p).read_text()
   if mutant and p.endswith('qkd_host_post_collector.sv'):s=s.replace('!cq_needed||cq_seen||MUT==1',"!cq_needed||1'b1||MUT==1")
   q=Path(d)/Path(p).name;q.write_text(s);files.append(str(q))
  p=subprocess.run(['iverilog','-g2012','-s','tb_qkd_host_peer_lifecycle','-o',d+'/sim',*files],capture_output=True,text=True);assert p.returncode==0,p.stderr
  p=subprocess.run(['vvp',d+'/sim'],capture_output=True,text=True,timeout=60)
  assert (p.returncode==0)==(not mutant),(mutant,p.stdout,p.stderr)
  out['skip_cq_mutant' if mutant else 'positive']={'returncode':p.returncode,'stdout':p.stdout}
print(json.dumps(out,indent=2))
