"""Fixed six-edge G0..5 acceptance and real off-by-one DUT mutant."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
def test_mtp_accept_static():
 with tempfile.TemporaryDirectory(prefix='mtp-accept-static-')as d:
  p=Path(d);tb=p/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,accept_slot=0;reg[2:0]draft_count=0;reg[84:0]draft_tokens=0;reg[101:0]target_tokens=0;
 reg[20:0]base_position=100;reg[3:0]epoch=4;reg[59:0]identity=7;
 wire result_valid,rejected,fault;wire[2:0]accepted,squashed;wire[16:0]bonus_token;wire[20:0]commit_position,next_base;wire[3:0]next_epoch;wire[59:0]result_identity;
 ot_s81_mtp_accept_static dut(.*);
 integer g,a,k,t;
 task step;begin @(negedge clk);#1;end endtask
 initial begin
  repeat(3)step();rst_n=1;step();
  for(g=0;g<=5;g=g+1)for(a=0;a<=g;a=a+1)begin
   draft_count=3'(g);for(k=0;k<5;k=k+1)draft_tokens[17*k+:17]=17'(20+k);
   for(k=0;k<6;k=k+1)target_tokens[17*k+:17]=17'(k<a?20+k:90+k);
   accept_slot=1;step();accept_slot=0;
   for(t=1;t<6;t=t+1)begin step();if(result_valid)$fatal(1,"early result");end
   step();
   if(!result_valid||accepted!=a||squashed!=g-a||bonus_token!=90+a||commit_position!=100+a||next_base!=101+a||rejected!=(a<g)||next_epoch!=4+(a<g)||result_identity!=7||fault)$fatal(1,"accept mismatch g%0d a%0d got%0d bonus%0d",g,a,accepted,bonus_token);
   step();if(result_valid)$fatal(1,"stretched result");
  end
  $display("MTP_ACCEPT_STATIC PASS all21 G0to5 prefixpatterns fixedR6 commit_rollback_epoch");$finish;
 end
endmodule
''')
  src=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_s81_mtp_accept_static.sv'
  for mutant in(0,1):
   actual=p/f'dut{mutant}.sv';text=src.read_text()
   if mutant:text=text.replace('==draft_q[17*i+:17]','==draft_q[17*((i+1)%5)+:17]')
   actual.write_text(text);exe=p/f'run{mutant}'
   subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(actual),str(tb)],check=True,capture_output=True)
   r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
   if mutant:assert r.returncode!=0 and'accept mismatch'in r.stdout,r.stdout
   else:assert r.returncode==0 and'MTP_ACCEPT_STATIC PASS'in r.stdout,r.stdout
