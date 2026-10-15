#!/usr/bin/env python3
"""Source-bound real VM macro control proof; arithmetic/collective are fixtures."""
import hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/rtl/qwen_production_stage_1015/segment_calendar'
RTL='rtl/qwen_sys/static_schedule_20261014/ot_qwen_tp_seq_calendar.sv'
TB='rtl/qwen_sys/static_schedule_20261014/tb_qwen_tp_seq_calendar.sv'
SOURCES=[RTL,TB,'rtl/hdc/ot_hdc_delay.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
DESC='results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/layer_candidate_segments.hex'
def main():
 OUT.mkdir(parents=True,exist_ok=True);results=[]
 original=(ROOT/RTL).read_text()
 variants=[('normal',original,0,True),('missing_return',original,1,True),
  ('stop_wait_mutant',original.replace('if(cycle==stop_q)begin','if(cycle==stop_q&&r_valid)begin'),0,False),
  ('token_truncation_mutant',original.replace('assign c_tag={tok_q,pos_q[7:0],6\'(seg)};',"assign c_tag={tok_q[15:0],pos_q[7:0],8'(seg)};"),0,False)]
 with tempfile.TemporaryDirectory(prefix='q-production-segment-')as td:
  for name,source,mut,expect_pass in variants:
   p=pathlib.Path(td)/f'{name}.sv';p.write_text(source);exe=pathlib.Path(td)/name
   compiled=subprocess.run(['iverilog','-g2012','-s','tb_qwen_tp_seq_calendar',f'-Ptb_qwen_tp_seq_calendar.MUT={mut}','-o',str(exe),str(p)]+SOURCES[1:],cwd=ROOT,text=True,capture_output=True)
   if compiled.returncode:raise RuntimeError(compiled.stderr)
   run=subprocess.run(['vvp',str(exe),f'+DESCRIPTORS={DESC}'],cwd=ROOT,text=True,capture_output=True)
   (OUT/f'{name}.log').write_text(run.stdout+run.stderr)
   passed=run.returncode==0 and 'PASS actual2xAR256'in run.stdout
   if passed!=expect_pass:raise RuntimeError(f'{name}: unexpected result\n{run.stdout}{run.stderr}')
   results.append(dict(case=name,exit_code=run.returncode,expected_pass=expect_pass,status='PASS'if expect_pass else 'REJECTED'))
 status=dict(schema='opentallas.qwen-segment-controller-proof.v1',status='PASS_COMPONENT_ONLY',
  scope='Actual released DW and four real SRAM models; core completion and collective loopback are explicit interface fixtures. No whole-layer arithmetic, eight-rank collective, or physical timing qualification.',
  tests=results,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SOURCES+[DESC]})
 (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status['tests']))
if __name__=='__main__':main()
