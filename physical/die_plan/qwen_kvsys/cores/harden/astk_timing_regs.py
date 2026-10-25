#!/usr/bin/env python3
"""KV-CORES 10-25 ASTK timing structure (kit-copy RTL transform, module names / ports / cycles unchanged).

Failing-path classification of the four old ASTK routes (Codex corner recoveries, TT 833 ps):
  * zn  : zq[k] (16-entry x 128-b flop store read address, one flop) -> ~1000 mux loads -> oa[*]   WN -80.6, ES -7
  * ctl : cal_r (calendar ages) -> 16-b compares (l_slot / z_slot) -> ap[42:1] select (+ z_k -> 16x133-b z_hd mux)
          WS -47.6, ES -34.1, EN -9.0
Fix (industry practice: register duplication + next-state decode registers, zero added cycles):
  * zn  : (non-head zn only: zn_0 zi are core pins) the store read address / slot select is captured into NGRP same-edge kept replicas (one per 128/NGRP-bit
          slice of oa/ob), each driving only its slice (extends Codex's verified r4 4-replica candidate).
  * ctl : l_slot / z_slot and z_k are computed from the NEXT-state of schedule_age / schedule_active / cal_r / nblk and
          registered (l_slot_r, z_slot_r, 5 slice copies of z_k_r); those registers equal the combinational originals
          on every edge (async-reset regs reset to the original's reset value), so ap / f / z queue behave identically.
`MUT` (tb only) injects a one-off error into one replica so the miter proves it observes the replicas.

split=True (gen --astk-rep-split, KV-CORE-RTL 10-25, GEOM-REVIEW-3 06:37): the kept `reg` replicas above were merged back
by yosys opt_merge (keep marks the wire, not the $dff cell): ASTK B ES g_zn_1.g_rd[7].rc[0] drove 2048 mux loads.  With
split the zn read-address/slot replicas become NSPLIT = 16 instances of a (* keep_hierarchy *) register module (user
module instances are never merged), one per 8-b slice of oa/ob (rk[0] -> 8 b x 8 mux2 = 64 loads), and the ctl z_k slice
copies use the same kind of module.  Same edges, same values: 0 cycles.
"""
import re
import sys

NGRP = 8
NSPLIT = 16
REP_MODS = """
// KV-CORE-RTL 10-25 (--astk-rep-split): register replicas that synthesis must keep distinct (opt_merge never merges user
// module instances; a kept reg alone is merged back).  Fixed widths, no parameters (paramod renaming defeats keep lists).
(* keep_hierarchy *) module qkd_astk_rep5 (input wire ck, input wire [4:0] d, output reg [4:0] q);
    always @(posedge ck) q <= d;
endmodule
(* keep_hierarchy *) module qkd_astk_rep4 (input wire ck, input wire [3:0] d, output reg [3:0] q);
    always @(posedge ck) q <= d;
endmodule
"""


def zn(text, name, mut=False, split=False):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    s = text[i:j]
    old_a = "        oa <= slot[0] ? sd[k] : d;\n"
    old_b = "        ob <= slot[0] ? d : 128'd0;\n"
    assert s.count(old_a) == 1 and s.count(old_b) == 1, name
    s = s.replace(old_a, "").replace(old_b, "")
    ng = NSPLIT if split else NGRP
    w = 128 // ng
    anchor = "    always @(posedge ck) begin\n        if (put)"
    assert s.count(anchor) == 1, name
    xor = " ^ ((rg == 0) ? 4'd1 : 4'd0)" if mut else ""
    rcff = ("        wire [4:0] rc;\n        (* keep *) qkd_astk_rep5 u_rc (.ck(ck), .d(zi[6:2]), .q(rc));\n" if split else
            "        (* keep *) reg [4:0] rc;\n        always @(posedge ck) rc <= zi[6:2];\n")
    rep = (f"    // KV-CORES 10-25: {ng} same-edge read-address/slot replicas (zi[6:2] = zq[6:2]), one per {w}-b slice\n"
           f"    genvar rg;\n    generate for (rg = 0; rg < {ng}; rg = rg + 1) begin : g_rd\n"
           + rcff +
           f"        wire [3:0] rk = rc[3:0]{xor};\n"
           f"        always @(posedge ck) begin\n"
           f"            oa[{w}*rg +: {w}] <= rc[4] ? sd[rk][{w}*rg +: {w}] : d[{w}*rg +: {w}];\n"
           f"            ob[{w}*rg +: {w}] <= rc[4] ? d[{w}*rg +: {w}] : {w}'d0;\n"
           f"        end\n    end endgenerate\n")
    s = s.replace(anchor, rep + anchor)
    return text[:i] + s + text[j:]


def ctl(text, mut=False, split=False):
    name = "qkd_astk_ctl_s"
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    s = text[i:j]
    subs = [
        ("    assign z_hd = zf_m[STATIC_SCHEDULE ? z_k : zfr[3:0]];\n", ""),
        ("    wire l_pend = STATIC_SCHEDULE ? l_slot : legacy_l_pend;\n",
         "    wire l_pend = STATIC_SCHEDULE ? l_slot_r : legacy_l_pend;\n"),
        ("    wire z_emit = STATIC_SCHEDULE ? z_slot : z_ne;\n",
         "    wire z_emit = STATIC_SCHEDULE ? z_slot_r : z_ne;\n"),
    ]
    for a, b in subs:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    anchor = "    wire zd0 = STATIC_SCHEDULE ? z_done_slot : legacy_zd0;\n"
    assert s.count(anchor) == 1
    lm = "16'd4" if mut else "16'd3"
    add = (
        "    // KV-CORES 10-25: next-state decode registers (same values as l_slot / z_slot / z_k on every edge, 0 cycles)\n"
        "    wire        sa_act_n = start ? 1'b1 : schedule_active;\n"
        "    wire [15:0] sa_n = start ? 16'd0 : (schedule_active && schedule_age != 16'hffff) ? schedule_age + 16'd1 : schedule_age;\n"
        "    wire [15:0] lmax_n = start ? cal_q[15:0] : cal_r[15:0];\n"
        "    wire [15:0] zst_n = start ? cal_q[31:16] : cal_r[31:16];\n"
        "    wire [15:0] z_age_n = sa_n - (zst_n - 16'd1);\n"
        "    wire [15:0] z_age_rn = (rn_q ? sa_n : 16'd0) - (zst_n - 16'd1);\n"
        "    (* keep *) reg l_slot_r, z_slot_r;\n"
        "    always @(posedge ck or negedge rn_q)\n"
        "        if (!rn_q) begin l_slot_r <= 1'b0; z_slot_r <= 1'b0; end\n"
        "        else begin\n"
        f"            l_slot_r <= sa_act_n && sa_n >= lmax_n - 16'd1 && sa_n < lmax_n + {lm};\n"
        "            z_slot_r <= sa_act_n && sa_n >= zst_n - 16'd1 && (z_age_n / Z_STRIDE < nblk_c) && (z_age_n % Z_STRIDE < 4);\n"
        "        end\n"
        "    genvar zg;\n"
        "    generate for (zg = 0; zg < 5; zg = zg + 1) begin : g_zk\n"
        + ("        wire [3:0] zk_r;\n        (* keep *) qkd_astk_rep4 u_zk (.ck(ck), .d(4'(z_age_rn / Z_STRIDE)), .q(zk_r));\n"
           if split else
           "        (* keep *) reg [3:0] zk_r;\n"
           "        always @(posedge ck) zk_r <= 4'(z_age_rn / Z_STRIDE);\n") +
        "        if (zg < 4) begin : g_s\n"
        "            assign z_hd[5 + 32*zg +: 32] = zf_m[zk_r][5 + 32*zg +: 32];\n"
        "        end else begin : g_t\n"
        "            assign z_hd[4:0] = zf_m[zk_r][4:0];\n"
        "        end\n"
        "    end endgenerate\n")
    s = s.replace(anchor, add + anchor)
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mut=False, split=False):
    from pathlib import Path
    d = Path(rtl_dir)
    p = d / "qkd_astk_leaves.sv"
    p.write_text(zn(p.read_text(), "qkd_astk_zn", mut, split) + (REP_MODS if split else ""))
    # the chain-head zn (zn_0) lands its zi on core PINS: one landing flop per pin (face_guard), so no same-edge
    # replicas there; its read-address fanout is left to the default recipe (fanout-24 post-route repair).
    p = d / "qkd_astk_static_leaves.sv"
    p.write_text(ctl(p.read_text(), mut, split))


if __name__ == "__main__":
    apply_kit(sys.argv[1], "mut" in sys.argv[2:], "split" in sys.argv[2:])
