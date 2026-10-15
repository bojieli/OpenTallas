#!/usr/bin/env python3
"""Actual stage-launch fact checks plus real RTL mutants, no readiness schedule."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
SRC='rtl/qwen_sys/static_schedule_20261014/ot_qfd_seq_su_bi_static.sv'
TB='rtl/qwen_sys/static_schedule_20261014/tb_qwen_stage_resource_gate.sv'
OUT=ROOT/'results/rtl/qwen_production_stage_1015/cbuf_requirement'
def main():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/SRC).read_text();cases=[]
 variants=[('embedding_cold',original,0,True),('requires_cold_fault',original,1,True),
  ('unconditional_fault_mutant',original.replace('if(requires_cbuf&&(!st_rdy||st_rdy_stage!=cur_stage))','if(!st_rdy||st_rdy_stage!=cur_stage)'),0,False),
  ('ready_gates_start_mutant',original.replace('assign go=pend&&!h_start;','assign go=pend&&!h_start&&st_rdy;'),0,False)]
 with tempfile.TemporaryDirectory(prefix='q-stage-resource-')as td:
  for name,source,required,success in variants:
   src=Path(td)/'parent.sv';src.write_text(source);exe=Path(td)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_qwen_stage_resource_gate',f'-Ptb_qwen_stage_resource_gate.REQUIRES={required}','-o',str(exe),str(src),TB],cwd=ROOT,check=True,capture_output=True)
   r=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True);(OUT/(name+'.log')).write_text(r.stdout+r.stderr)
   if(r.returncode==0)!=success:raise RuntimeError(name+': '+r.stdout+r.stderr)
   cases.append(dict(case=name,exit_code=r.returncode,status='PASS'if success else'REJECTED'))
 (OUT/'source.json').write_text(json.dumps(dict(status='PASS_COMPONENT_ONLY',scope='Real static launch gate; source-derived CROM requirement only affects fault, never launch. No physical/profile qualification.',tests=cases,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in[SRC,TB,'tools/qwen_static_schedule/segments.py']}),indent=2)+'\n')
 print('PASS source resource requirement, fixed launch, cold CBUF fault and two rejected RTL mutants')
if __name__=='__main__':main()
