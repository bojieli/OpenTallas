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


def test_h8_header_only_ingress_retains_tied_behavior_and_default_fault(tmp_path):
    ingress = "rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress_h8.sv"
    model = "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v"
    _run(tmp_path, """
module tb;
  reg clk=0;
  always #5 clk=~clk;
  reg rst_n=1, cfg=0, den=0, param_valid=0, launch=0;
  wire [2:0] qv, ready, done, fault;
  wire [511:0] data[3];
  wire [11:0] code[3];
  for (genvar m=0; m<3; m=m+1) begin : cases
    wire den_input = m==0 ? 1'b0 : den;
    dsdv_pv_so_ingress_h8 #(.ENABLE(1),.HEADER_DEN(1),.EXTERNAL_DEN_EVENT(m!=1)) ingress
      (.clk(clk),.rst_n(rst_n),.cfg_v(cfg),.cfg_owner(20'd3),.cfg_position(21'd5),
       .cfg_se_jid(8'd7),.cfg_so_jid(8'd9),.pv_v(1'b0),.pv_quarter(2'd0),.pv_d(513'd0),
       .param_v(param_valid),.param_row(3'd0),.param_owner(20'd3),.param_position(21'd5),.param_d(512'd0),
       .den_v(den_input),.den_mask(16'hffff),.den_owner(20'd3),.den_jid(8'd7),.launch(launch),
       .q_v(qv[m]),.q_d(data[m]),.ready(ready[m]),.done(done[m]),.fault(fault[m]),.fault_code(code[m]));
  end
  always @(posedge clk) if (rst_n) begin
    #1;
    if ({qv[0],ready[0],done[0],fault[0],code[0]} !== {qv[1],ready[1],done[1],fault[1],code[1]})
      $fatal(1,"Physical ingress changed the original tied behavior");
    if (qv[0] && data[0] !== data[1]) $fatal(1,"Physical ingress data divergence");
  end
  initial begin
    #1 rst_n=0;
    repeat (3) @(negedge clk);
    rst_n=1;
    repeat (4) @(negedge clk);
    cfg=1; den=1;
    @(negedge clk); cfg=0; den=0;
    repeat (3) @(negedge clk);
    if (fault !== 3'b100 || code[2] !== 12'h001)
      $fatal(1,"Full ingress lost external-den collision detection");
    param_valid=1; den=1;
    @(negedge clk); param_valid=0; den=0;
    repeat (3) @(negedge clk);
    if (fault[1:0] !== 2'b00) $fatal(1,"Physical ingress unexpectedly faulted");
    launch=1; den=1;
    @(negedge clk); launch=0; den=0;
    repeat (3) @(negedge clk);
    if (code[0] !== 12'h080 || code[1] !== 12'h080) $fatal(1,"Launch guard was removed");
    $finish;
  end
endmodule
""", [ingress, model])
