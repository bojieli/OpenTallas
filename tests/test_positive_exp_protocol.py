"""Positive exponential retains/reset-invalidates results across primitive stages."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('source', ['rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv', 'results/rtl/positive_range_pipeline/candidate.sv'])
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
def test_reset_restart_and_output_stalls(tmp_path, simulator, source):
    bench = tmp_path/'tb.sv'
    bench.write_text(r'''
module tb;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,in_valid=0,out_ready=0;
reg [31:0] argument_code=32'h3f800000;
wire in_ready,out_valid;wire [31:0] result_code;wire [1:0] result_error;
ot_a3_fp32_exp_pos_cr_rne dut(.*);
integer phase,n,checks=0;
task issue;begin
 wait(in_ready);@(negedge clk);in_valid=1;argument_code=32'h3f800000;
 @(negedge clk);in_valid=0;
end endtask
task check_result;begin
 wait(out_valid);@(negedge clk);
 if(result_code!==32'h402df854 || result_error!==0)$fatal(1,"exp(1)");
 // Upstream offers another request while output is blocked; it must not enter.
 in_valid=1;argument_code=32'h40000000;
 repeat(9)begin
  @(negedge clk);
  if(!out_valid || in_ready || result_code!==32'h402df854 || result_error!==0)
   $fatal(1,"unstable stalled result");
 end
 in_valid=0;out_ready=1;@(negedge clk);out_ready=0;
 repeat(3)@(negedge clk);
 if(out_valid || !in_ready)$fatal(1,"retire handshake");
 checks=checks+1;
end endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(phase=0;phase<6;phase=phase+1)begin
  issue();
  case(phase)
   0: wait(dut.reduce_mul_busy);
   1: wait(dut.mul_lower_busy);
   2: wait(dut.div_lower_busy);
   3: wait(out_valid);
   4: wait(dut.state == RANGE_PRODUCT);
   5: wait(dut.state == RANGE_DIFF);
  endcase
  @(negedge clk);#0.25;rst_n=0;#0.25;
  if(out_valid || result_code!==0 || result_error!==0)$fatal(1,"reset publication");
  repeat(2)@(negedge clk);rst_n=1;
  repeat(4000)begin
   @(negedge clk);if(out_valid)$fatal(1,"stale post-reset result");
  end
  issue();check_result();
 end
 $display("PASS positive exp protocol reset_stages=6 stalled_restarts=%0d",checks);
 $finish;
end
initial begin #200000;$fatal(1,"timeout");end
endmodule
'''.replace('RANGE_PRODUCT', '11' if 'candidate' in source else '2').replace('RANGE_DIFF', '12' if 'candidate' in source else '3'))
    sources = [ROOT/'rtl/lib/ot_wide_mul_seq.sv', ROOT/'rtl/lib/ot_wide_div_small_seq.sv',
               ROOT/source, bench]
    if simulator == 'iverilog':
        cmd = ['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),*map(str,sources)]
        run = ['vvp',str(tmp_path/'sim')]
    else:
        cmd = [str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),
               '--binary','--timing','-j','2','-Wno-fatal','--top-module','tb',
               '--Mdir',str(tmp_path/'obj'),*map(str,sources)]
        run = [str(tmp_path/'obj/Vtb')]
    result = subprocess.run(cmd,capture_output=True,text=True,timeout=240)
    assert result.returncode == 0,result.stdout+result.stderr
    result = subprocess.run(run,capture_output=True,text=True,timeout=180)
    assert result.returncode == 0,result.stdout+result.stderr
    assert 'PASS positive exp protocol reset_stages=6 stalled_restarts=6' in result.stdout
