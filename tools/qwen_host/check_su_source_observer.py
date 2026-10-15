#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
SRC='rtl/qwen_sys/static_schedule_20261014/ot_qfd_seq_su_bi_static.sv';TB='rtl/qwen_sys/static_schedule_20261014/tb_qwen_su_source_observer.sv'
OUT=ROOT/'results/rtl/qwen_production_stage_1015/su_source_observer'
def main():
 OUT.mkdir(parents=True,exist_ok=True);text=(ROOT/SRC).read_text();cases=[]
 variants=[('normal',text,True),('candidate_gates_event_mutant',text.replace("observe<={issue,candidate_v,unit,12'(program_base+candidate_pc)};","observe<={issue&&candidate_v,candidate_v,unit,12'(program_base+candidate_pc)};"),False),('omit_segment_base_mutant',text.replace("12'(program_base+candidate_pc)","candidate_pc"),False)]
 with tempfile.TemporaryDirectory(prefix='q-su-source-')as td:
  for name,source,success in variants:
   src=Path(td)/'source.sv';src.write_text(source);exe=Path(td)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_qwen_su_source_observer','-o',str(exe),str(src),TB],cwd=ROOT,check=True,capture_output=True)
   r=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True);(OUT/(name+'.log')).write_text(r.stdout+r.stderr)
   if(r.returncode==0)!=success:raise RuntimeError(name+': '+r.stdout+r.stderr)
   cases.append(dict(case=name,exit_code=r.returncode,status='PASS'if success else'REJECTED'))
 (OUT/'source.json').write_text(json.dumps(dict(status='PASS_SOURCE_OBSERVER_COMPONENT',clock='actual SU parent clk',register_edges=1,bits=16,format='issue,candidate_v,unit2,program_base+candidate_pc12',tests=cases,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in[SRC,TB,'rtl/qwen_split/qfd_seq_su_static.sv']}),indent=2)+'\n')
 print('PASS actual source observer, pin edge, candidate fault observation and two RTL mutants')
if __name__=='__main__':main()
