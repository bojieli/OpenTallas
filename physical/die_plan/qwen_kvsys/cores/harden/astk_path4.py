#!/usr/bin/env python3
"""PATH-KV-ASTK4 10-25: ASTK master successor structure (kit-copy RTL transform).  Applied after astk_write_decode.

CTS1 diagnosis (PATH-KV-ASTK3 14:48, GEOM-REVIEW-2 14:46, COORD rulings (a)/(b)):
  * zn_0 (chain head, qkd_astk_zn_head_p): zi lands on core PINS, one landing flop per pin (face_guard), so the store
    read address / slot select zq[6:2] (one flop each) drove the whole 128-b oa/ob read select (up to 2073 loads; no
    same-edge replicas possible without duplicating pin flops).  Fix (COORD ruling (a), +1 cycle on zn_0, priced by
    KV-TOK): the pin flops become a pure landing stage zl/tl; the zone's old registers zq/tq load from them one edge
    later, and NSPLIT = 16 kept qkd_astk_rep5 read-address replicas (g_rd[*].u_rc, d = zl[6:2]) are same-edge copies of
    zq[6:2], one per 8-b slice of oa/ob (as zn_1..3).  The whole zone is then EXACTLY its old function on inputs
    delayed by one edge (tc, zi only; rst_n not delayed), so zo/fo are +1 cycle (checked by tb_zn0 lockstep).
  * ctl: start (aq_q[0]) -> zst_n/sa_n select -> 16-b subtract -> 17 g_zk zk_r copies (TT -44.68, 19 EP): the
    start-dependent arithmetic is precomputed on both sides of start (zk_st from cal_q, zk_cn from schedule_age/cal_r,
    neither depends on start) and each of the 17 slices registers start ? zk_st : zk_cn in its own kept qkd_astk_zks
    (same value as the old zk_r on every edge, 0 cycles; start then drives only 17 slice selects).
`mut` (tb only): zn_0 -> one replica slice reads the un-delayed zq (latency error); ctl -> zk_st off by one.
"""
import sys
from pathlib import Path

import astk_timing_regs

ZKS_MOD = """
// PATH-KV-ASTK4 10-25: per-slice z_k register with the start select inside the slice (keep_hierarchy, fixed width).
(* keep_hierarchy *) module qkd_astk_zks (input wire ck, input wire st, input wire [3:0] a, input wire [3:0] b, output reg [3:0] q);
    always @(posedge ck) q <= st ? a : b;
endmodule
"""


def _mod(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j


def zn0(text, mut=False):
    name = "qkd_astk_zn_head_p"
    i, j = _mod(text, name)
    s = text[i:j]
    subs = [
        ("    always @(posedge ck) begin zc_q <= ZC; tq[14:1] <= tc[14:1]; zq[137:1] <= zi[137:1]; end\n",
         "    // PATH-KV-ASTK4 (COORD ruling (a), +1 cycle): zl/tl = the pin landing registers; zq/tq one edge later\n"
         "    (* keep *) reg [14:0]  tl;\n"
         "    (* keep *) reg [137:0] zl;\n"
         "    always @(posedge ck) begin zc_q <= ZC; tl[14:1] <= tc[14:1]; zl[137:1] <= zi[137:1];"
         " tq[14:1] <= tl[14:1]; zq[137:1] <= zl[137:1]; end\n"),
        ("        if (!rn_q) begin tq[0] <= 1'b0; zq[0] <= 1'b0; fi_q <= 1'b0; end\n"
         "        else begin tq[0] <= tc[0]; zq[0] <= zi[0]; fi_q <= fi; end\n",
         "        if (!rn_q) begin tl[0] <= 1'b0; zl[0] <= 1'b0; tq[0] <= 1'b0; zq[0] <= 1'b0; fi_q <= 1'b0; end\n"
         "        else begin tl[0] <= tc[0]; zl[0] <= zi[0]; tq[0] <= tl[0]; zq[0] <= zl[0]; fi_q <= fi; end\n"),
        (".tcn(tc[14:1])", ".tcn(tl[14:1])"),
    ]
    for a, b in subs:
        assert s.count(a) == 1, (name, a)
        s = s.replace(a, b)
    text = text[:i] + s + text[j:]
    text = astk_timing_regs.zn(text, name, split=True)
    i, j = _mod(text, name)
    s = text[i:j]
    a = "qkd_astk_rep5 u_rc (.ck(ck), .d(zi[6:2]), .q(rc));"
    assert s.count(a) == 1
    s = s.replace(a, "qkd_astk_rep5 u_rc (.ck(ck), .d(zl[6:2]), .q(rc));")
    if mut:   # slice 0 reads the store with the un-delayed address (zl) -> a wrong-latency read select
        a = f"        wire [3:0] rk = rc[3:0];\n"
        assert s.count(a) == 1
        s = s.replace(a, "        wire [3:0] rk = (rg == 0) ? zl[5:2] : rc[3:0];\n")
    return text[:i] + s + text[j:]


def ctl(text, mut=False):
    name = "qkd_astk_ctl_s"
    i, j = _mod(text, name)
    s = text[i:j]
    a = "        (* keep *) qkd_astk_rep4 u_zk (.ck(ck), .d(4'(z_age_rn / Z_STRIDE)), .q(zk_r));\n"
    assert s.count(a) == 1, a
    s = s.replace(a, "        (* keep *) qkd_astk_zks u_zk (.ck(ck), .st(start), .a(zk_st), .b(zk_cn), .q(zk_r));\n")
    anchor = "    genvar zg;\n"
    assert s.count(anchor) == 1
    off = " + 16'd4" if mut else ""
    add = ("    // PATH-KV-ASTK4 10-25: start-independent next-state terms of z_k (start = 1: sa_n = 0, zst_n = cal_q[31:16];\n"
           "    // start = 0: sa_n = the running age, zst_n = cal_r[31:16]); each slice selects with start (0 cycles)\n"
           "    wire [15:0] sa_cn = (schedule_active && schedule_age != 16'hffff) ? schedule_age + 16'd1 : schedule_age;\n"
           f"    wire [15:0] z_age_st = 16'd0 - (cal_q[31:16] - 16'd1){off};\n"
           "    wire [15:0] z_age_cn = (rn_q ? sa_cn : 16'd0) - (cal_r[31:16] - 16'd1);\n"
           "    wire [3:0]  zk_st = 4'(z_age_st / Z_STRIDE), zk_cn = 4'(z_age_cn / Z_STRIDE);\n")
    s = s.replace(anchor, add + anchor)
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mut_zn=False, mut_ctl=False):
    d = Path(rtl_dir)
    p = d / "qkd_astk_zn_head_p.sv"
    p.write_text(zn0(p.read_text(), mut_zn))
    p = d / "qkd_astk_static_leaves.sv"
    p.write_text(ctl(p.read_text(), mut_ctl) + ZKS_MOD)


def replica_expect(exp):
    """astk_replica_expect.json for the successor: zn_0 read-address replicas 0,0..0,15 + ctl zk slices in qkd_astk_zks."""
    for r in exp["rules"]:
        if r["name"] == "zn_read_addr_replicas":
            r["groups"] = [f"{z},{k}" for z in range(4) for k in range(16)]
        if r["name"] == "ctl_zk_copies":
            r["module"] = "qkd_astk_zks"
    exp["note"] += "; PATH-KV-ASTK4: zn_0 read-address replicas (+1 cycle landing stage) + ctl zk slices qkd_astk_zks (start select per slice)"
    return exp


if __name__ == "__main__":
    apply_kit(sys.argv[1], "mut_zn" in sys.argv[2:], "mut_ctl" in sys.argv[2:])
