#!/usr/bin/env python3
"""QC-NLNK-RF2 11-06 vR form (OWNER 21:5x conservative form + COORD brief): pipelined reset tree, default-off RSTP.

Measured cause (qfd_tile_nl_a0c vB2, TT -96.8): the one native reset sample u_g.g_rst_native.q (ungated face clock, latency
829 ps through 27 delaybufs) drives 279 async-reset sinks over ~1.1 mm through 51 repeaters; the recovery check is captured on
gated ck_de (latency 745).  Smells 4 + 5.

RSTP = 0 (default): unchanged.  RSTP = 3: q (the same port sample on the face clock) -> s1 (4 copies) -> s2 (32 copies) -> s3
(256 copies: the pass balances coarse loads, ~1925 of them before synthesis drops dead constant flops, and <= 8 needs ~241; copies
left without a load after synthesis stay as kept idle flops because the LEC family check needs every bit), every stage a synchronous kept register with no reset, on the body clock `ck`, so the same (gated) tree as the
sinks.  Reset assert AND release at the sinks arrive exactly +3 clk edges later (PIN CYCLES: reset only; rst_n is held >= 64 clk,
owner 10-29; the ICG stays open: rst_e is released 3 edges after the port and dr then holds it for ICG_DRAIN = 64 more).
No data path changes a cycle.

In the RTL every copy's D comes from copy 0 of the stage before and every sink hangs on s3[0]: the copies are identical
registers, which is what physical/common_flow/ot_rst_copies.py proves before it re-points the loads over the copies (name-sorted
cut, so s3 group k, s2 group k/8 and s1 group k/64 serve the same region; OT_RST_COPIES_MAX = 8 is the fanout bound; wire names
end in __ot_rl<k>v, the pass's default family regex).  The kit LEC and its RRS copy families are the proof of that step.

Bench-only `OT_RSTP_MUT (must FAIL): 1 = s3 never released, 2 = one stage short (bypass s3), 3 = re-assert lost (only the first
reset reaches the sinks), 4 = s3 copy 0 fed from a stuck s2 copy.
DIE-QC-87 11-07 vR3: third arg "wide" = 8/64/512 copies (4/32/256 left NL s3 at 12 and NK at 10 loads against the 8 target).
usage: rstp_patch.py RTL_DIR nl|nk [wide]
"""
import sys
from pathlib import Path

R = Path(sys.argv[1]); T = sys.argv[2]; WIDE = len(sys.argv) > 3 and sys.argv[3] == "wide"
assert T in ("nl", "nk")

def sub(path, old, new, count=1):
    p = R / path; s = p.read_text(); n = s.count(old)
    if n != count:
        sys.exit(f"rstp_patch: {path}: expected {count} x {old!r}, found {n}")
    p.write_text(s.replace(old, new))

BODY = f"qfd_tile_{T}_rp2_45.sv"; TOP = f"qfd_tile_{T}_a0c.sv"
# RSTP (QC-NLNK-RF2 vR, opt-in, default 0 = unchanged): see tools/qwen_romleaf/a0core/lqr/rstp_patch.py
PDECL = "parameter integer RSTP = 0, parameter integer LQR = 0"
sub(BODY, "parameter integer LQR = 0", PDECL)
TREE = """        (* keep *) reg q;
        always @(posedge ck_fa4) q <= rst_n;
        if (RSTP == 0) begin : g_rp0
            assign reset_q = q;
        end else begin : g_rp
            //: vR tree: identical kept copies per stage on the body clock (same gated tree as the sinks); no reset on any stage
            (* keep *) reg [3:0] s1__ot_rl1v;
            (* keep *) reg [31:0] s2__ot_rl2v;
            (* keep *) reg [255:0] s3__ot_rl3v;
`ifdef OT_RSTP_MUT
            localparam integer RMUT = `OT_RSTP_MUT;
`else
            localparam integer RMUT = 0;
`endif
            always @(posedge ck) begin
                s1__ot_rl1v <= {4{q}};
                s2__ot_rl2v <= {32{s1__ot_rl1v[0]}};
                s3__ot_rl3v <= {256{(RMUT == 4) ? 1'b1 : s2__ot_rl2v[0]}};
            end
`ifdef OT_RSTP_MUT
            reg seen = 1'b0;
            always @(posedge ck) if (s3__ot_rl3v[0] === 1'b1) seen <= 1'b1;
            assign reset_q = (RMUT == 1) ? 1'b0 : (RMUT == 2) ? s2__ot_rl2v[0] : (RMUT == 3) ? (s3__ot_rl3v[0] | seen) : s3__ot_rl3v[0];
`else
            assign reset_q = s3__ot_rl3v[0];
`endif
            initial if (RSTP != 3) $fatal(1, "RSTP form: RSTP must be 0 or 3");
        end
"""
if WIDE:
    for o, n in (("reg [3:0] s1", "reg [7:0] s1"), ("reg [31:0] s2", "reg [63:0] s2"), ("reg [255:0] s3", "reg [511:0] s3"),
                 ("{4{q}}", "{8{q}}"), ("{32{s1", "{64{s1"), ("{256{(RMUT", "{512{(RMUT")):
        assert TREE.count(o) == 1, o
        TREE = TREE.replace(o, n)
sub(BODY, "        (* keep *) reg q;\n        always @(posedge ck_fa4) q <= rst_n;\n        assign reset_q = q;\n", TREE)
sub(TOP, "parameter integer LQR = 0", PDECL)
s = (R / TOP).read_text()
n = s.count(".LQR(LQR)) u_g (")
if n != 2:
    sys.exit(f"rstp_patch: {TOP}: u_g instantiations {n} != 2")
(R / TOP).write_text(s.replace(".LQR(LQR)) u_g (", ".LQR(LQR), .RSTP(RSTP)) u_g ("))
print(f"rstp_patch {T}: OK {R}")
