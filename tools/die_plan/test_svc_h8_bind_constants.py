"""Physical H8 interfaces preserve the behavior of the original tied forms."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEMORY = "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv"
MEMORY_MODEL = "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v"


def _run(tmp_path, bench, sources):
    compiler = shutil.which("iverilog")
    runner = shutil.which("vvp")
    if not compiler or not runner:
        pytest.skip("Icarus Verilog is required for the source witness")
    tb = tmp_path / "tb.sv"
    tb.write_text(bench)
    out = tmp_path / "tb.vvp"
    compile_run = subprocess.run(
        [compiler, "-g2012", "-s", "tb", "-o", str(out), str(tb), *(str(ROOT / source) for source in sources)],
        capture_output=True, text=True,
    )
    assert compile_run.returncode == 0, compile_run.stdout + compile_run.stderr
    bench_run = subprocess.run([runner, str(out)], capture_output=True, text=True)
    assert bench_run.returncode == 0, bench_run.stdout + bench_run.stderr


def test_h8_qmem_preserves_invalid_read_address_and_write_cycles(tmp_path):
    """Compare both read modes while exercising all encodings of the original four-bit read address."""
    _run(tmp_path, """
module tb;
  reg clk=0;
  always #5 clk=~clk;
  reg [3:0] ra=0;
  reg [2:0] wa=0;
  reg we=0;
  reg [511:0] wd=0;
  wire [511:0] full[2], narrow[2];
  for (genvar sync=0; sync<2; sync=sync+1) begin : mode
    dsdv_svc_mem_ar #(.W(512),.DEPTH(8),.AW(4),.SYNC(sync)) control
      (.clk(clk),.ra_n(ra),.we(we),.wa({1'b0,wa}),.wd(wd),.rd(full[sync]));
    dsdv_svc_mem_ar #(.W(512),.DEPTH(8),.AW(4),.SYNC(sync),.WAW(3)) physical_form
      (.clk(clk),.ra_n(ra),.we(we),.wa(wa),.wd(wd),.rd(narrow[sync]));
  end
  task step(input [3:0] r, input bit en, input [2:0] a, input [511:0] word_data);
    @(negedge clk); ra=r; we=en; wa=a; wd=word_data;
    @(posedge clk); #1;
    for (int mode=0; mode<2; mode=mode+1) begin
      if ((^full[mode] === 1'bx) || narrow[mode] !== full[mode])
        $fatal(1,"QMEM divergence mode=%0d ra=%0d",mode,r);
      if (r>=8 && narrow[mode] !== 0) $fatal(1,"Invalid QMEM read aliases a real row");
    end
  endtask
  initial begin
    for (int row=0; row<8; row=row+1) step(4'(row),1,3'(row),512'(row+1));
    for (int row=0; row<16; row=row+1) step(4'(row),0,0,0);
    for (int row=0; row<8; row=row+1) begin
      step(4'(row),1,3'(row),512'(row+17));
      step(4'(row+8),0,0,0);
      step(4'(row),0,0,0);
    end
    $finish;
  end
endmodule
""", [MEMORY, MEMORY_MODEL])
