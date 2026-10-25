"""Nearest equal-depth reset terminals preserve epoch and explicit START cycles."""
import copy
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reset_tree as RT
import gen_rtl


@pytest.mark.parametrize('start', [False, True])
def test_leaf_reassignment_epoch_lockstep_and_mutants(tmp_path, start):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog unavailable')
    tree=RT.build([('old',100,100),('nearest',700,100)],(10,10))
    tree.update(entry='relayed',sync_stages=2,start=start,n_clock_taps=2,outs=[])
    assert RT.verify(tree)==[]
    # Both physical candidates have the same registered depth. The real emitter
    # supplies reset AND START for consumer taps when START is enabled.
    body='\n'.join(RT.rtl_lines(tree))
    # Consumer epoch and state use the same reset signal after physical net
    # reassignment. A delayed terminal and omission of START must both be caught.
    gate='start_i' if start else 'arst_n'
    tb=f'''module tb;
reg clk=0,arst_n=0,start_i=0; always #5 clk=~clk;
{body}
reg delayed=0; always @(posedge clk) delayed<=rst_n_t1;
reg [7:0] old_state=0,new_state=0,delay_state=0,raw_state=0;
reg old_epoch=0,new_epoch=0,delay_epoch=0,raw_epoch=0;
always @(posedge clk or negedge rst_n_t0) if(!rst_n_t0) begin old_state<=0;old_epoch<=0;end else begin old_state<=old_state+1;old_epoch<=1;end
always @(posedge clk or negedge rst_n_t1) if(!rst_n_t1) begin new_state<=0;new_epoch<=0;end else begin new_state<=new_state+1;new_epoch<=1;end
always @(posedge clk or negedge delayed) if(!delayed) begin delay_state<=0;delay_epoch<=0;end else begin delay_state<=delay_state+1;delay_epoch<=1;end
always @(posedge clk or negedge {gate}) if(!{gate}) begin raw_state<=0;raw_epoch<=0;end else begin raw_state<=raw_state+1;raw_epoch<=1;end
integer i,checks=0,wrong_depth=0,wrong_gate=0;
initial begin
  for(i=0;i<192;i=i+1) begin
    @(negedge clk);
    arst_n=(i>=16 && i%47>3);
    start_i=(i>=28 && i%61>7);
    @(posedge clk); #1;
    if(i>12) begin
      checks=checks+1;
      if({{old_state,old_epoch}} !== {{new_state,new_epoch}}) $fatal(1,"leaf reassignment mismatch cycle%0d",i);
      if({{old_state,old_epoch}} !== {{delay_state,delay_epoch}}) wrong_depth=wrong_depth+1;
      if({{old_state,old_epoch}} !== {{raw_state,raw_epoch}}) wrong_gate=wrong_gate+1;
    end
  end
  if(wrong_depth==0 || wrong_gate==0) $fatal(1,"mutant escaped");
  $display("PASS checks=%0d wrong_depth=%0d wrong_gate=%0d",checks,wrong_depth,wrong_gate); $finish;
end
endmodule
'''
    cells=tmp_path/'cells.sv';cells.write_text(gen_rtl.CELLS)
    bench=tmp_path/'tb.sv';bench.write_text(tb)
    exe=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(cells),str(bench)],check=True,capture_output=True,text=True)
    p=subprocess.run(['vvp',str(exe)],check=True,capture_output=True,text=True)
    assert 'PASS checks=179' in p.stdout,p.stdout
