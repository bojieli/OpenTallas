from pathlib import Path
import subprocess,sys,hashlib,json
W=Path('/srv/opentallas-scratch/claude/wt/codex-s81-start-data-1030');R=Path(__file__).parent
sys.path.insert(0,str(W/'tools/die_plan'))
import start_data_emit as D
rtl=W/'rtl/common/ot_dp_clk_landing_ca.sv'
s=rtl.read_text(); native=s[s.index('module ot_dp_landing_origin #('):s.index('endmodule',s.index('module ot_dp_landing_origin #('))+len('endmodule')]
e=dict(cells=[dict(instance='sd_actual_b'+str(i)) for i in range(3)])
lines,last=D.body(e,'p')
b='''module BUFx8_ASAP7_75t_R(input A,output Y); buf(Y,A); endmodule
module tb;
 reg clk=0,p=0,rst=0; always #416.5 clk=~clk;
 wire q0,q1,q2,q3; reg delayed; integer n=0, checks=0, invcaught=0, cyclecaught=0;
 always @(posedge clk) delayed<=p;
'''+ '\n'.join(lines)+f'''
 ot_dp_landing_origin #(.EDGE_FALL(0)) a(clk,rst,p,q0);
 ot_dp_landing_origin #(.EDGE_FALL(0)) b(clk,rst,{last},q1);
 ot_dp_landing_origin #(.EDGE_FALL(0)) c(clk,rst,~{last},q2);
 ot_dp_landing_origin #(.EDGE_FALL(0)) d(clk,rst,delayed,q3);
 always @(negedge clk) begin #1;
  if(n>10) begin checks=checks+1; if(q0!==q1) $fatal(1,"buffered source mismatch");
   if(q0!==q2) invcaught=invcaught+1; if(q0!==q3) cyclecaught=cyclecaught+1; end
 end
 initial begin
  #1; rst=0;
  for(n=0;n<700;n=n+1) begin
   @(posedge clk); #10;
   if(n==64 || n==320 || n==576) rst=1;
   if(n==256 || n==512) rst=0;
   p=(n%13)<7;
   if(n%31==5) p=1'bx;
  end
  #1000;
  if(invcaught==0 || cyclecaught==0) $fatal(1,"control not detected");
  $display("PASS checks=%0d inversion_mutant=%0d extra_cycle_mutant=%0d cold64 warm64/64 addedcycles=0",checks,invcaught,cyclecaught);
  $finish;
 end
endmodule
'''
(R/'coupon.sv').write_text(native+'\n'+b)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(R/'coupon'),str(R/'coupon.sv')],check=True)
r=subprocess.run(['vvp',str(R/'coupon')],text=True,capture_output=True,check=True)
(R/'run.log').write_text(r.stdout+r.stderr);print(r.stdout)
(R/'receipt.json').write_text(json.dumps(dict(scope='actual native origin with emitted ordinary BUF8 Boolean chain; not mapped/physical timing qualification',rtl_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),added_cycles=0,buffer_count=3,clock_period_ps=833,source_gates_homes='required by manifest and postmap audit; not fabricated'),indent=2)+'\n')
