#!/usr/bin/env python3
"""CE foundation only: all-state freeze and old logical-cycle behavior."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
R=Path(__file__).resolve().parents[1]
RTL=R/'rtl/hbm_accel/control_20261007/protected_registered/ot_hbm_regcheck_ce_hierarchy.sv'
TB=R/'rtl/hbm_accel/control_20261007/tb_sm_serial_owner.sv'
FIX=R/'results/rtl/hbm_sm_command_20261007/stress_seq.hex'
def run(args):
 p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return dict(returncode=p.returncode,output=p.stdout)
def main():
 bench=TB.read_text().replace('ot_hbm_sm_serial_owner #(.ENABLE(1)) dut(.*);','ot_hbm_regcheck_sm_serial_owner #(.ENABLE(1)) dut(.clk(fast_clk),.step_en(step_en),.state_observe(observed),.*);')
 bench=bench.replace('always #5 clk=~clk;', '''always #40 clk=~clk;
 reg fast_clk=1;always #5 fast_clk=~fast_clk;
 integer fast_phase=0;always @(negedge fast_clk)fast_phase=(fast_phase+1)%8;
 wire step_en=fast_phase==4;
 wire[2672:0] observed;
 reg[2672:0] saved_observation;
 always @(posedge fast_clk)if(rst_n&&!step_en)begin
  saved_observation=observed;#1;
  if(observed!==saved_observation)$fatal(1,"CE state changed while paused");
 end''')
 with tempfile.TemporaryDirectory(prefix='hbm-ce-gate-') as tmp:
  p=Path(tmp);b=p/'tb.sv';b.write_text(bench);exe=p/'sim'
  build=run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(RTL),str(b)]);assert build['returncode']==0,build
  result=run(['vvp',str(exe),'+SEQ='+str(FIX)])
  changed=p/'mutant.sv';text=RTL.read_text();assert 'else if(step_en) cred <=' in text
  changed.write_text(text.replace('else if(step_en) cred <=','else cred <='))
  build=run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(changed),str(b)]);assert build['returncode']==0,build
  mutant=run(['vvp',str(exe),'+SEQ='+str(FIX)])
 files=[RTL,TB,FIX,Path(__file__),R/'tools/hbm_sm_protected_registered_build.py',R/'tools/hbm_sm_protected_registered_model.py']
 verdict=dict(status='PASS' if result['returncode']==0 and 'full_shape_X_captures=6448 cycles=8638' in result['output'] and mutant['returncode']!=0 and 'CE state changed while paused' in mutant['output'] else 'FAIL',
 scope='complete synchronous-CE core/ingress/channel foundation only; peers intentionally execute on logical clock. No production transaction wrapper, registered verdict, or safe external commit claimed.',
 enabled_ratio='1/8',observed_state_bits=2673,normal=result,missing_channel_CE_mutant=mutant,
 source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},physical_admitted=False)
 out=R/'results/rtl/hbm_sm_protected_registered_20261007/ce_component.json'
 if out.exists():raise RuntimeError('immutable receipt exists')
 out.write_text(json.dumps(verdict,indent=2)+'\n');print(verdict['status']);print(result['output']);print(mutant['output'])
 if verdict['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
