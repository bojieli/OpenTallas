"""Grouped depth rounding must retain the carry at the 16-bit shape limit."""

from pathlib import Path
import shutil
import subprocess
import pytest
from tools.rtl_abi3_lq8_campaign import RTL_SOURCES

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_grouped_depth_boundary(tmp_path):
    bench = tmp_path / "tb.sv"
    bench.write_text("""module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0;reg [15:0] cfg_depth=0;reg [7:0] cfg_group=1;
wire operand_request;
ot_a3_lane_pipelined #(.OPERAND_CREDITS(1)) dut(
.clk(clk),.rst_n(rst_n),.start(start),.operand_credit(1'b0),.operand_request(operand_request),
.cfg_rows(16'd1),.cfg_cols(16'd3),.cfg_depth(cfg_depth),
.cfg_dtype_a(ot_a3_lane_pkg::FMT_MXFP4_E2M1),.cfg_dtype_b(ot_a3_lane_pkg::FMT_MXFP4_E2M1),.cfg_group(cfg_group),
.cfg_a_base(32'd0),.cfg_b_base(32'd0),.cfg_scale_a(1'b0),.cfg_scale_b(1'b0),
.cfg_block_a(16'd0),.cfg_block_b(16'd0),.cfg_block_rows_a(16'd0),.cfg_block_rows_b(16'd0),
.cfg_scale_a_base(32'd0),.cfg_scale_b_base(32'd0),.cfg_out_base(32'd0),.cfg_out_fp32(1'b1),
.a_rd_data(64'd0),.b_rd_data(64'd0),.s_rd_data(32'd0),.t_rd_data(32'd0));
integer g,k,expected;
initial begin
for(g=1;g<=4;g=g*2)begin
 for(k=65531;k<=65535;k=k+1)begin
  @(negedge clk);rst_n=0;start=0;
  @(negedge clk);rst_n=1;cfg_depth=16'(k);cfg_group=8'(g);start=1;
  @(negedge clk);start=0;
  wait(operand_request);@(negedge clk);
  expected=(k+g-1)/g;
  if(dut.depth_words!=16'(expected) || dut.kg_count_m1!=16'(expected-1))
   $fatal(1,"depth=%0d group=%0d got words=%0d expected=%0d",k,g,dut.depth_words,expected);
 end
end
$display("PASS lane grouped depth boundary cases=15");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
""")
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            *[str(ROOT / p) for p in RTL_SOURCES],
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS lane grouped depth boundary cases=15" in run.stdout
