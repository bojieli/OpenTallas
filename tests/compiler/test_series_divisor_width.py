"""The narrowed Taylor divisor must preserve non-default series lengths."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("terms,steps", [(56, 10), (64, 10), (254, 10), (56, 4)])
@pytest.mark.parametrize("positive", [False, True])
def test_series_divisor_preserves_supported_lengths(tmp_path, terms, steps, positive):
    name = (
        "ot_a3_fp32_exp_pos_cr_rne" if positive else "ot_a3_fp32_transcendental_cr_rne"
    )
    source = ROOT / "rtl/abi3" / f"{name}.sv"
    # Retain the previous nine-bit divider as a differential authority. This
    # compares the full transaction, including certification and cycle count.
    wide = source.read_text().replace(f"module {name}", f"module {name}_wide")
    wide = wide.replace(
        "SERIES_DIVISOR_BITS = $clog2(SERIES_TERMS + 2)", "SERIES_DIVISOR_BITS = 9"
    )
    (tmp_path / "wide.sv").write_text(wide)
    operation = "" if positive else ".operation(1'b0),"
    sign = "0" if positive else "8"
    expected = "402df854" if positive else "3ebc5ab2"
    bench = f"""
module tb;
  reg clk=0, rst_n=0, in_valid=0;
  reg [31:0] argument_code;
  wire ready, wide_ready, valid, wide_valid;
  wire [31:0] result, wide_result;
  wire [1:0] error, wide_error;
  integer cycles=0, c;
  always #1 clk=~clk;
  {name} #(.SERIES_TERMS({terms}), .DIV_BITS_PER_STEP({steps})) dut (
    .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(ready),
    {operation} .argument_code(argument_code), .out_ready(1'b1),
    .out_valid(valid), .result_code(result), .result_error(error));
  {name}_wide #(.SERIES_TERMS({terms}), .DIV_BITS_PER_STEP({steps})) reference (
    .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(wide_ready),
    {operation} .argument_code(argument_code), .out_ready(1'b1),
    .out_valid(wide_valid), .result_code(wide_result), .result_error(wide_error));
  always @(negedge clk) begin
    cycles=cycles+1;
    if (cycles>200000) $fatal(1, "timeout");
    if (rst_n) begin
      if (ready !== wide_ready || valid !== wide_valid)
        $fatal(1, "handshake differs");
      if (valid && (result !== wide_result || error !== wide_error))
        $fatal(1, "narrow divider changed result or certification");
    end
  end
  initial begin
    repeat(3) @(negedge clk);
    rst_n=1;
    for (c=0; c<4; c=c+1) begin
      wait(ready);
      @(negedge clk);
      case(c)
        0: argument_code=32'h{"3f800000" if positive else "bf800000"};
        1: argument_code=32'h{"42a00000" if positive else "c2a00000"};
        2: argument_code=32'h{sign}0000001;
        3: argument_code=32'h00000000;
      endcase
      in_valid=1;
      @(negedge clk); in_valid=0;
      wait(valid); @(negedge clk);
      if (error !== ((c==3 && {int(positive)}) ? 2'd1 : 2'd0)) $fatal(1, "unexpected certification failure case=%0d error=%0d", c, error);
      if (c==0 && result !== 32'h{expected}) $fatal(1, "exp(1) oracle mismatch");
      @(negedge clk);
    end
    $display("PASS terms={terms} positive={positive} steps={steps}");
    $finish;
  end
endmodule
"""
    (tmp_path / "tb.sv").write_text(bench)
    executable = tmp_path / "sim.vvp"
    sources = [
        ROOT / "rtl/lib" / f"{n}.sv"
        for n in ("ot_wide_mul_seq", "ot_wide_div_small_seq", "ot_wide_div_seq")
    ]
    compile_result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(executable),
            *map(str, sources),
            str(source),
            str(tmp_path / "wide.sv"),
            str(tmp_path / "tb.sv"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    result = subprocess.run(
        ["vvp", str(executable)], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
