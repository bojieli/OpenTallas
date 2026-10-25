"""CLOCK-RESET/relay2 10-25: the production S81 relay stations dsfd_rstg / ot_s81_sstn_payload536 (2-flop since
S81-KITS-RTLC dc23a738f) equal the retired one-flop stations (reference copies below, from bf48820fa / 2091acfaf)
delayed by exactly one edge, on every one of the 602 public output bits, including column-reset (rs) pulses on the
valid bits.  Both faces are registered: input pin -> capture flop, launch flop -> output pin, no shared flop.
Mutants that must be caught: one-flop depth (output from the capture stage), payload data bit flip, the master's own
OT_SSTN_PAYLOAD_1FLOP_MUT, and a reset-less valid bit (OT_SSTN_PAYLOAD_RESET_MUT)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl/dsrom_sys/s81_static_net"

REF_1STAGE = r'''
module ref1_rstg (input wire [0:0] ck, input wire [65:0] i, output wire [65:0] o, input wire [0:0] rs);
    reg [65:1] r; always @(posedge ck[0]) r <= i[65:1];
    reg v; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) v <= 1'b0; else v <= i[0];
    assign o = {r, v};
endmodule
module ref1_payload536 (input wire ck, rs, input wire [535:0] i, output wire [535:0] o);
    reg [530:0] hi; reg [2:0] lo; reg [1:0] valid;
    always @(posedge ck) begin hi <= i[535:5]; lo <= i[3:1]; end
    always @(posedge ck or negedge rs) if (!rs) valid <= 2'b00; else valid <= {i[4], i[0]};
    assign o = {hi, valid[1], lo, valid[0]};
endmodule
'''

BENCH = r'''
module tb;
reg ck=0; always #5 ck=~ck;
reg rs=0; reg [65:0] ri=0; reg [535:0] pi=0;
wire [65:0] rold, rnew; wire [535:0] pold, pnew;
reg [65:1] rdata; reg rv; reg [530:0] phi; reg [2:0] plo; reg [1:0] pv;
ref1_rstg oldr(ck, ri, rold, rs);
dsfd_rstg newr(ck, ri, rnew, rs);
ref1_payload536 oldp(ck, rs, pi, pold);
ot_s81_sstn_payload536 newp(ck, rs, pi, pnew);
// one extra edge on the reference output; the valid bits keep their column-reset class
always @(posedge ck) begin rdata <= rold[65:1]; phi <= pold[535:5]; plo <= pold[3:1]; end
always @(posedge ck or negedge rs) if (!rs) begin rv <= 0; pv <= 0; end else begin rv <= rold[0]; pv <= {pold[4], pold[0]}; end
integer j, k, nres; reg [31:0] x = 32'h01234567;
initial begin
  nres = 0;
  repeat (6) @(negedge ck);
  for (k = 0; k < 12000; k = k + 1) begin
    x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5);
    rs = (k % 137 != 0 && k % 137 != 1);
    if (!rs) nres = nres + 1;
    for (j = 0; j < 66; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); ri[j] = x[0]; end
    for (j = 0; j < 536; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); pi[j] = x[0]; end
    #1;  // async column reset: the valid bits clear at once, not at the next edge
    if (k > 1 && (rnew !== {rdata, rv} || pnew !== {phi, pv[1], plo, pv[0]})) $fatal(1, "RESET_ASYNC_LOCKSTEP_FAIL cycle%0d", k);
    @(negedge ck);
    if (k > 1 && rnew !== {rdata, rv}) $fatal(1, "RSTG_LATENCY_LOCKSTEP_FAIL cycle%0d", k);
    if (k > 1 && pnew !== {phi, pv[1], plo, pv[0]}) $fatal(1, "PAYLOAD_LATENCY_LOCKSTEP_FAIL cycle%0d", k);
  end
  $display("RELAY2_LOCKSTEP_PASS words12000 bits602 cycles_added1 reset_cycles%0d", nres);
  $finish;
end
endmodule
'''

ANCHOR_R = "assign o = {r, v};"


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog")
@pytest.mark.parametrize("mutant", ["none", "rstg_one_flop", "payload_bit", "payload_1flop", "payload_reset"])
def test_relay2_one_edge_lockstep(tmp_path, mutant):
    rstg = (RTL / "gen/dsfd_rstg.sv").read_text()
    assert rstg.count(ANCHOR_R) == 1
    if mutant == "rstg_one_flop":
        rstg = rstg.replace(ANCHOR_R, "assign o = {l, lv};")
    defines = {"payload_bit": "OT_SSTN_PAYLOAD_BIT_MUT", "payload_1flop": "OT_SSTN_PAYLOAD_1FLOP_MUT",
               "payload_reset": "OT_SSTN_PAYLOAD_RESET_MUT"}
    (tmp_path / "rstg.sv").write_text(rstg)
    (tmp_path / "ref.sv").write_text(REF_1STAGE)
    (tmp_path / "bench.sv").write_text(BENCH)
    exe = tmp_path / "sim"
    cmd = ["iverilog", "-g2012", "-s", "tb", "-o", str(exe)]
    if mutant in defines:
        cmd.append("-D" + defines[mutant])
    cmd += [str(tmp_path / "rstg.sv"), str(RTL / "ot_s81_sstn_payload536.sv"), str(tmp_path / "ref.sv"),
            str(tmp_path / "bench.sv")]
    subprocess.run(cmd, check=True, capture_output=True)
    p = subprocess.run(["vvp", str(exe)], text=True, capture_output=True)
    if mutant == "none":
        assert p.returncode == 0 and "RELAY2_LOCKSTEP_PASS" in p.stdout, p.stdout + p.stderr
    else:
        assert "LOCKSTEP_FAIL" in p.stdout, p.stdout + p.stderr
