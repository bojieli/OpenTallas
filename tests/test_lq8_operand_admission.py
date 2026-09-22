"""Admission captures geometry and rejects invalid scale/divisibility contracts."""

from pathlib import Path
import random
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_operand_admission(tmp_path):
    rng = random.Random(20260922)
    cases = [
        (2, 24, k, g, sa, sb, ba, bb, 2)
        for k, g, sa, sb, ba, bb in [
            (65535, 2, 0, 0, 0, 0),
            (65535, 4, 0, 0, 0, 0),
            (65532, 4, 1, 1, 12, 4),
            (24, 2, 1, 1, 6, 8),
            (25, 2, 1, 0, 6, 0),
            (24, 4, 1, 0, 6, 0),
            (24, 1, 1, 0, 0, 0),
            (0, 1, 0, 0, 0, 0),
            (24, 3, 0, 0, 0, 0),
        ]
    ]
    cases += [(0, 8, 8, 1, 0, 0, 0, 0, 0), (1, 9, 8, 1, 0, 0, 0, 0, 0)]
    for _ in range(80):
        g = rng.choice([1, 2, 4])
        k = rng.randint(1, 16383) * g
        ba = g * rng.choice([1, 2, 3, 4, 8])
        bb = g * rng.choice([1, 2, 3, 4, 8])
        cases.append(
            (
                rng.randint(1, 65535),
                8 * rng.randint(1, 8191),
                k,
                g,
                rng.randrange(2),
                rng.randrange(2),
                ba,
                bb,
                rng.randrange(5),
            )
        )
    vectors = []
    for i, (rows, cols, k, g, sa, sb, ba, bb, rpb) in enumerate(cases):
        bad = not rows or not cols or cols % 8 or not k or g not in (1, 2, 4)
        bad = bool(
            bad
            or (sa and (not ba or ba % g or k % ba))
            or (sb and (not bb or bb % g or k % bb))
        )
        # group=3 is refused; its don't-care output follows the fallback shift.
        effective_g = g if g in (1, 2, 4) else 1
        vectors.append(
            f"""check_case(16'd{rows},16'd{cols},16'd{k},8'd{g},1'b{sa},1'b{sb},16'd{ba},16'd{bb},16'd{rpb},1'b{int(bad)},16'd{(k + effective_g - 1) // effective_g},16'd{k // ba if sa and ba else 0},16'd{k // bb if sb and bb else 0});"""
        )
    bench = tmp_path / "tb.sv"
    bench.write_text(
        """module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,record_ready=0;
wire command_ready,record_valid,geometry_error;
reg [31:0] cfg_generation=0,cfg_a_base=0,cfg_s_base=0,cfg_ws_base=0,cfg_w_base=0;
reg [15:0] cfg_rows=0,cfg_cols=0,cfg_depth=0,cfg_block_a=0,cfg_block_b=0,cfg_block_rows_a=0;
reg [7:0] cfg_group=0;reg cfg_scale_a=0,cfg_scale_b=0;
wire [31:0] generation,a_base,s_base,ws_base,w_base;
wire [15:0] rows,local_cols,depth_words,rows_per_scale_a,scale_stride_a,scale_stride_b,groups_per_scale_a,groups_per_scale_b;
ot_a3_lq8_operand_admission dut(.*);
integer checks=0;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task check_case(input [15:0] nr,nc,nk,input [7:0] ng,input sa,sb,input [15:0] ba,bb,rpb,input bad,input [15:0] words,cpa,cpb);
integer cycles;
begin
 cfg_generation=32'h123;cfg_a_base=100;cfg_s_base=200;cfg_ws_base=300;cfg_w_base=400;
 cfg_rows=nr;cfg_cols=nc;cfg_depth=nk;cfg_group=ng;cfg_scale_a=sa;cfg_scale_b=sb;
 cfg_block_a=ba;cfg_block_b=bb;cfg_block_rows_a=rpb;command_valid=1;
 #1;if(!command_ready)$fatal(1,"command not ready");tick();command_valid=0;
 // Mutate every external field immediately after handshake.
 cfg_generation=0;cfg_a_base=0;cfg_s_base=0;cfg_ws_base=0;cfg_w_base=0;
 cfg_rows=0;cfg_cols=0;cfg_depth=0;cfg_group=0;cfg_scale_a=0;cfg_scale_b=0;
 cfg_block_a=0;cfg_block_b=0;cfg_block_rows_a=0;
 cycles=0;while(!record_valid)begin tick();cycles=cycles+1;if(cycles>18)$fatal(1,"admission timeout");end
 if(cycles!=17 || geometry_error!==bad)$fatal(1,"admission verdict case %0d",checks);
 repeat(4)begin
  if(command_ready || !record_valid || generation!=32'h123 || a_base!=100 || s_base!=200 || ws_base!=300 || w_base!=400 ||
     rows!=nr || local_cols!=nc/8 || depth_words!=words || rows_per_scale_a!=(rpb==0?16'd1:rpb))$fatal(1,"captured record changed");
  if(!bad && (scale_stride_a!=cpa || scale_stride_b!=cpb || groups_per_scale_a!=(sa?ba/ng:0) || groups_per_scale_b!=(sb?bb/ng:0)))$fatal(1,"wrong scale geometry");
  tick();
 end
 record_ready=1;tick();record_ready=0;if(record_valid)$fatal(1,"record not consumed");checks=checks+1;
end endtask
initial begin
tick();rst_n=1;
"""
        + "\n".join(vectors)
        + """
command_valid=1;tick();command_valid=0;repeat(5)tick();clear=1;tick();clear=0;
repeat(20)tick();if(record_valid || !command_ready)$fatal(1,"clear left divider active");
$display("PASS admission cases=%0d capture, hold, overflow boundary and abort",checks);$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
"""
    )
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_lq8_operand_admission.sv"),
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"PASS admission cases={len(cases)}" in run.stdout
