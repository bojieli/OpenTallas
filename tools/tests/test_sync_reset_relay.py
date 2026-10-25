"""One die-root CDC: delivered resets use ordinary synchronous shifts, preserving the priced release depth."""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_release_lockstep_and_wrong_depth_mutant(tmp_path):
    source=ROOT/'rtl/lib/ot_rst_relay.sv'
    bench='''
module tb;
reg clk=0;always #5 clk=~clk;
reg rn=0;wire[3:0] a,b;wire[3:0] bad;reg[2:0] expected=0;
ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1),.SYNC_INPUT(0)) legacy(clk,rn,a);
ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1),.SYNC_INPUT(1)) dut(clk,rn,b);
ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(2),.SYNC_INPUT(1)) mutant(clk,rn,bad);
always @(posedge clk) expected<={expected[1:0],rn};
integer k;integer caught=0;
initial begin
 repeat(6) @(negedge clk);
 rn=1;
 for(k=0;k<7;k=k+1) begin
  @(negedge clk);
  if(a!==b || b!=={4{expected[2]}}) $fatal(1,"RELEASE_DEPTH_MISMATCH");
  if(bad!==b) caught=1;
 end
 if(!caught) $fatal(1,"MUTANT_ESCAPED");
 // Assertion is synchronous and travels the same three edges; the first falling edge cannot clear the output.
 #1 rn=0;#1;
 if(b!==4'hf) $fatal(1,"ASYNC_ASSERT_REMAINED");
 for(k=0;k<5;k=k+1) begin
  @(negedge clk);
  if(b!=={4{expected[2]}}) $fatal(1,"ASSERT_SHIFT_MISMATCH");
 end
 $display("SYNC_RESET_LOCKSTEP_PASS MUTANT_CAUGHT");$finish;
end
endmodule
'''
    p=tmp_path/'bench.sv';p.write_text(bench);exe=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(source),str(p)],check=True,capture_output=True)
    r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
    assert r.returncode==0 and 'SYNC_RESET_LOCKSTEP_PASS MUTANT_CAUGHT' in r.stdout,r.stdout+r.stderr
