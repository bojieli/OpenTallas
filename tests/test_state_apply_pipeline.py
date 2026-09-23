"""Apply pipeline preserves transaction results while separating byte accounting."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('variant',['state_apply_pipeline','state_apply_overlap'])
@pytest.mark.parametrize('simulator',['iverilog','verilator'])
def test_apply_pipeline(tmp_path,simulator,variant):
    old=tmp_path/'old.sv';old.write_text((ROOT/'results/rtl/state_apply_pipeline/before.sv').read_text().replace('module ot_a3_state_controller','module old_state'))
    ports=".clk(clk),.rst_n(rst_n),.clear(clear),.op_valid(valid),.op_sub(sub),.op_descriptor_id(id),.op_rows(rows),.op_rows_bound(1'b1),.op_payload(payload),.commit_all(commit_all),.discard_all(discard_all),.session_state_count(32'd3)"
    fields=['count_prepares','count_commits','count_discards','count_reads','count_commits_applied','count_rows_committed','count_bytes_written','pending_count','slot_open','slot_used','apply_overflow']
    compare='\n'.join(f'if(dut.{f}!==ref_dut.{f})$fatal(1,"{f} mismatch round %0d",t);' for f in fields)
    bench=tmp_path/'tb.sv';bench.write_text(r'''
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,valid=0,commit_all=0,discard_all=0;
reg [7:0] sub=0;reg [31:0] id=0,rows=0;reg [511:0] payload=0;
ot_a3_state_controller #(.SLOTS(3)) dut(PORTS);
old_state #(.SLOTS(3)) ref_dut(PORTS);
integer t,i,waits,dut_cycles,ref_cycles,transactions=0,cancellations=0;
reg [63:0] expected_bytes;
reg [31:0] rb,span,cap,policy;
task command(input [7:0] op);begin
 sub=op;valid=1;@(negedge clk);valid=0;
 if(dut.op_done!==ref_dut.op_done || dut.op_ok!==ref_dut.op_ok || dut.op_trap_class!==ref_dut.op_trap_class)$fatal(1,"admission");
 if(!dut.op_ok)$fatal(1,"unexpected refusal");
 @(negedge clk);
end endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(t=0;t<90;t=t+1)begin
  clear=1;@(negedge clk);clear=0;expected_bytes=0;
  for(i=0;i<3;i=i+1)begin
   id=i+1;policy=t%3;cap=(t%2)?127:128;span=(t*17+i*13)%200+1;
   if(policy==0)cap=1000;
   rb=32'hfffffff0+t+i;rows=span;
   payload=0;payload[8+:8]=policy;payload[128+:32]=rb;
   payload[192+:32]=cap;payload[256+:32]=policy==2 ? cap-1 : 0;
   command(1);command(2);
   expected_bytes=expected_bytes+64'(rb)*64'(policy==1 ? 0 : (policy==2 && span>cap ? cap : span));
  end
  commit_all=1;@(negedge clk);commit_all=0;waits=0;dut_cycles=0;ref_cycles=0;
  while(dut.apply_busy || ref_dut.apply_busy)begin
   if(dut.apply_busy)dut_cycles=dut_cycles+1;
   if(ref_dut.apply_busy)ref_cycles=ref_cycles+1;
   @(negedge clk);waits=waits+1;if(waits>200)$fatal(1,"timeout");
  end
  if(dut_cycles-ref_cycles != ((OVERLAP && policy==2 && cap==127)?0:6))
   $fatal(1,"latency dut=%0d ref=%0d policy=%0d cap=%0d",dut_cycles,ref_cycles,policy,cap);
  COMPARE
  if(dut.count_bytes_written!==expected_bytes)$fatal(1,"independent byte total");
  for(i=0;i<3;i=i+1)begin
   if(dut.slot_cursor[i]!==ref_dut.slot_cursor[i] || dut.slot_generation[i]!==ref_dut.slot_generation[i])$fatal(1,"committed state");
  end
  transactions=transactions+1;
 end
 // Cancel each new pipeline stage before its first retirement; no stale result.
 for(t=0;t<7;t=t+1)begin
  clear=1;@(negedge clk);clear=0;id=1;rows=7;payload=0;
  payload[128+:32]=32'hffffffff;payload[192+:32]=100;
  if(t>=2)begin payload[8+:8]=2;payload[192+:32]=127;end
  command(1);command(2);commit_all=1;@(negedge clk);commit_all=0;
  // Cover capture/product and early/middle/final remainder iterations.
  waits=t<2?t:(t==2?0:(t==3?1:(t==4?2:(t==5?16:33))));
  repeat(waits)@(negedge clk);
  discard_all=1;@(negedge clk);discard_all=0;
  repeat(5)@(negedge clk);
  if(dut.count_bytes_written!=0 || dut.count_commits_applied!=0 || dut.pending_count!=0 || dut.apply_busy)$fatal(1,"cancelled payload retired");
  cancellations=cancellations+1;
 end
 $display("PASS apply pipeline transactions=%0d cancellations=%0d",transactions,cancellations);$finish;
end
initial begin #1000000;$fatal(1,"global timeout");end
endmodule
'''.replace('PORTS',ports).replace('COMPARE',compare).replace('OVERLAP', '1' if variant=='state_apply_overlap' else '0'))
    sources=[str(ROOT/'rtl/abi3/ot_a3_pkg.sv'),str(ROOT/f'results/rtl/{variant}/candidate.sv'),str(old),str(bench)]
    if simulator=='iverilog':
        cmd=['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),*sources];run=['vvp',str(tmp_path/'sim')]
    else:
        cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb','--Mdir',str(tmp_path/'obj'),*sources];run=[str(tmp_path/'obj/Vtb')]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=240);assert p.returncode==0,p.stdout+p.stderr
    p=subprocess.run(run,capture_output=True,text=True,timeout=60);assert p.returncode==0,p.stdout+p.stderr
    assert 'PASS apply pipeline transactions=90 cancellations=7' in p.stdout
