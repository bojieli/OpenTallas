#!/usr/bin/env python3
"""PATH-KV-ASTK 10-25: ASTK master write-decode / sideband-select structure (kit-copy RTL transform; ports, module
names and cycles unchanged).  Applied after astk_timing_regs (--astk-timing-regs --astk-rep-split).

Failing-path classification of the master kv3_astk__190.08x181.44 CTS probe (Codex astkff, TT 833 ps, 228 EP, -61.24):
  * zn  (197 EP, zn_0 75 / zn_1 25 / zn_3 98): tq/zq -> pb = ({k,S,sgam,000} < T) 15-b compare (~300 ps of MAJ chain)
        -> put & (k == r) -> 128-load row write enable of sd[r] (~300 ps BUFx2 fanout tree) -> sd[r][*] D.
  * ctl (30 EP, 322 paths): zh[1:0] -> 4:1 select of z_s over z_hd (128 loads + 2nd broadcast) -> ap[42:1]; 7 paths
        from the 5 g_zk zk_r copies (32-b x 16-entry zf_m read each).
Fix (industry practice: next-state precompute registers + register duplication per consumer slice, 0 added cycles):
  * zn  : pb = kt_r[k] | (ke_r[k] & lo_r[slot[3:1]]) where lo_r[j] = ({S, sgam(L, j), 000} < T[8:0]),
          kt_r[i] = ({0,i} < T[13:9]), ke_r[i] = ({0,i} == T[13:9]) are registered from the NEXT state of zc_q / tq
          (zc, tc; neither has a reset), so they equal the combinational terms on every edge.  The 15-b compare and
          T (tq) leave the write cycle: pb = two 16:1 + one 8:1 selects by the zq k/slot fields (40 regs/zone).
          tc is internal (ctl tc face copies) in every zn incl. the chain head, so no logic is added on a core pin.
  * ctl : zh gets 4 kept same-edge replicas (keep_hierarchy counter module, identical next state:
          start ? 0 : (!l_pend && z_emit) ? +1 : hold, async reset rn_q), one per 8-b slice of z_s; the zk_r copies go
          from 5 (32-b chunks) to 17 (8-b z_hd slices + tag) so each drives 8 b x 16 entries.
`mut` (tb only) corrupts lo_r[0] (zn) / one zh replica (ctl) so the miter proves it observes the new registers.
"""
import re
import sys

ZH_MOD = """
// PATH-KV-ASTK 10-25: zh replica (same next state as ctl.zh; a user-module instance is never merged by opt_merge)
(* keep_hierarchy *) module qkd_astk_zhrep (input wire ck, input wire rn, input wire clr, input wire inc, output reg [1:0] q);
    always @(posedge ck or negedge rn)
        if (!rn) q <= 2'd0;
        else if (clr) q <= 2'd0;
        else if (inc) q <= q + 2'd1;
endmodule
"""


def zn(text, name, mut=False):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    s = text[i:j]
    old = "    wire        pb = (cb < {1'b0, T}) && (`KVD_AKMUT != 3);\n"
    assert s.count(old) == 1, name
    m = re.findall(r"zc_q <= (\w+);", s)
    assert len(m) == 1, (name, m)
    zc_n = m[0]
    assert s.count("tq[14:1] <= tc[14:1];") == 1, name
    xor = " ^ 8'd1" if mut else ""
    new = (
        "    // PATH-KV-ASTK 10-25: write-decode next-state threshold registers (0 cycles).  lo_r[j] equals\n"
        "    // ({S, sgam(L, slot[3:1] = j), 3'b000} < T[8:0]) on every edge: registered from the next state of zc_q / tq.\n"
        f"    wire [3:0]  zc_n = {zc_n};\n"
        "    reg  [7:0]  lo_n, lo_r;\n"
        "    reg  [3:0]  sib_n, sg_n, jj_;\n"
        "    integer     j_;\n"
        "    always @* for (j_ = 0; j_ < 8; j_ = j_ + 1) begin\n"
        "        jj_ = j_;\n"
        "        sib_n = {jj_[2:0], 1'b1};\n"
        "        sg_n = (zc_n[3:2] == 2'd0) ? sib_n : (zc_n[3:2] == 2'd1) ? {sib_n[2:0], 1'b0} :\n"
        "               (zc_n[3:2] == 2'd2) ? {sib_n[1:0], 2'b00} : {sib_n[0], 3'b000};\n"
        "        lo_n[j_] = {zc_n[1:0], sg_n, 3'b000} < tc[9:1];\n"
        "    end\n"
        f"    always @(posedge ck) lo_r <= lo_n{xor};\n"
        "    // kt_r[i] = ({0,i} < T[13:9]), ke_r[i] = ({0,i} == T[13:9]), registered from tc[14:10]: T leaves the write cycle\n"
        "    reg  [15:0] kt_n, ke_n, kt_r, ke_r;\n"
        "    reg  [4:0]  ki_;\n"
        "    integer     i_;\n"
        "    always @* for (i_ = 0; i_ < 16; i_ = i_ + 1) begin\n"
        "        ki_ = i_;\n"
        "        kt_n[i_] = ki_ < tc[14:10];\n"
        "        ke_n[i_] = ki_ == tc[14:10];\n"
        "    end\n"
        "    always @(posedge ck) begin kt_r <= kt_n; ke_r <= ke_n; end\n"
        "    wire        pb = (kt_r[k] || (ke_r[k] && lo_r[slot[3:1]])) && (`KVD_AKMUT != 3);\n")
    s = s.replace(old, new)
    return text[:i] + s + text[j:]


def ctl(text, mut=False):
    name = "qkd_astk_ctl_s"
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    s = text[i:j]
    old_sel = "        for (m_ = 0; m_ < 4; m_ = m_ + 1) if (zh == m_) z_s = z_hd[5 + 32*m_ +: 32];\n"
    assert s.count(old_sel) == 1
    s = s.replace(old_sel, "        z_s = z_s_w;   // PATH-KV-ASTK 10-25: 4 zh replicas, one per 8-b slice\n")
    anchor = "    reg  [31:0]  lm_s, z_s;\n"
    assert s.count(anchor) == 1
    inc = "!l_pend && z_emit"
    rep = (
        "    // PATH-KV-ASTK 10-25: zh replicas (same next state as zh: start -> 0, l_pend holds, z_emit +1 mod 4)\n"
        "    wire [31:0]  z_s_w;\n"
        "    genvar zs;\n"
        "    generate for (zs = 0; zs < 4; zs = zs + 1) begin : g_zh\n"
        "        wire [1:0] zr;\n"
        f"        (* keep *) qkd_astk_zhrep u_zh (.ck(ck), .rn(rn_q), .clr(start), .inc({inc}{' ^ (zs == 0)' if mut else ''}), .q(zr));\n"
        "        assign z_s_w[8*zs +: 8] = z_hd[5 + 32*zr + 8*zs +: 8];\n"
        "    end endgenerate\n")
    s = s.replace(anchor, anchor + rep)
    old_zk = ("    generate for (zg = 0; zg < 5; zg = zg + 1) begin : g_zk\n")
    assert s.count(old_zk) == 1
    s = s.replace(old_zk, "    generate for (zg = 0; zg < 17; zg = zg + 1) begin : g_zk   // PATH-KV-ASTK: 8-b z_hd slices\n")
    old_s = ("        if (zg < 4) begin : g_s\n"
             "            assign z_hd[5 + 32*zg +: 32] = zf_m[zk_r][5 + 32*zg +: 32];\n")
    assert s.count(old_s) == 1
    s = s.replace(old_s, ("        if (zg < 16) begin : g_s\n"
                          "            assign z_hd[5 + 8*zg +: 8] = zf_m[zk_r][5 + 8*zg +: 8];\n"))
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mut=False):
    from pathlib import Path
    d = Path(rtl_dir)
    p = d / "qkd_astk_leaves.sv"
    p.write_text(zn(p.read_text(), "qkd_astk_zn", mut))
    p = d / "qkd_astk_zn_head_p.sv"
    p.write_text(zn(p.read_text(), "qkd_astk_zn_head_p", mut))
    p = d / "qkd_astk_static_leaves.sv"
    p.write_text(ctl(p.read_text(), mut) + ZH_MOD)


if __name__ == "__main__":
    apply_kit(sys.argv[1], "mut" in sys.argv[2:])
