#!/usr/bin/env python3
"""TOK-QK/C 2026-10-24: apply KV boot fixes C1 + C2 to a COPY of a staged KV die-slice vehicle tree (stage_src.sh layout).

    apply_C.py STAGED_TREE BO1_HUBWI REPO_ROOT      (called by apply_C.sh; idempotent; prints every file it changes)

C2 (clocking): the host SerDes x6 halves (sys_SW / sys_SE, ot_qfd_serdes_112g_x6_phy) run on their own clock clk_phy behind
    ONE crossing per direction at the PHY (rtl/physical/ot_fdi_phy_cdc.sv: Gray-pointer async FIFOs, valid + data written
    together); every lane and the whole hub_Wi host (link adapter, pad, its CDC channels) run on the core clock -- the
    unsynchronised core-lane -> clk_phy adapter crossing is removed, not stacked.  The adapter's transmit slots are paced
    below the PHY rate (rtl/physical/ot_fdi_tx_pace.sv, 19/24 of 1.2 GHz = 0.950 GHz < 0.959 GHz).
C1 (bind): the FDI rx valid was rebuilt in hub_Wi as AND(W.rx_v, E.rx_v) + a kept as-built 4-stage ot_dp_dly that its data
    did not get (valid 4 flits late), and the W / E halves land 30 / 36 cycles (R8 grouped them per source partition).
    Now each half's valid rides in its own lane word with its data and the halves are paired BY ORDER
    (rtl/physical/ot_fdi_join2.sv): no AND, no kept delay, no cycle-alignment assumption between the halves.
Files changed in the tree: src/bind__rtl/{kv3_sys_SD_part,kv3_sys_SD_v1_part,kv3_hub_Wi_part,qwen_kvsys_bound_top}.sv;
    new src/c1c2__rtl/ot_fdi_{phy_cdc,join2,tx_pace}.sv (+ files.f); hub_Wi first replaced by the BO1 candidate (with
    qkd_host_root_admission_obsx_bo1.sv + qkd_d2d_boot_event_bridge.sv staged from the repo if missing).
"""
import hashlib
import os
import re
import shutil
import sys

MARK = "TOK-QK/C 10-24"
BO1_MD5 = "70e99cebd5972994b55a1b6a89b46407"     # epyc2 scratch2/claude/codex-qwen/boot_bo1_bound_candidate/kv3_hub_Wi_part.sv
changed = []


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def sub1(s, old, new, what):
    n = s.count(old)
    if n != 1:
        sys.exit(f"apply_C: {what}: expected exactly 1 match, found {n}")
    return s.replace(old, new)


def put(p, s):
    if open(p).read() != s:
        open(p, "w").write(s)
        changed.append(p)


def sys_sd(p, W, side):
    s = open(p).read()
    if MARK in s:
        return
    s = sub1(s, "    input  wire arst_n,\n", "    input  wire arst_n,\n    input  wire clk_clk_phy,   // " + MARK +
             " (C2): the PHY's own clock (ot_fdi_phy_cdc)\n", f"{p} port")
    i0 = s.index(f"    // as-built serdes_host.u_sub.u_{side}\n")
    i1 = s.index("    );\n", i0) + len("    );\n")
    old = s[i0:i1]
    assert f"ot_qfd_serdes_112g_x6_phy #(.W({W})) u_core" in old and f".tx_v(i_host_fdi_q[{W}])" in old, old
    new = (f"    // {MARK} (C2): the host SerDes half runs on its own clock clk_phy; ot_fdi_phy_cdc is the ONE clock crossing of\n"
           f"    // each direction (Gray-pointer async FIFOs at the PHY, valid + data written together); lanes stay on core.\n"
           f"    wire w_phy_rst_n, w_phy_tx_v, w_phy_rx_v, w_phy_tx_up;\n"
           f"    wire [{W - 1}:0] w_phy_tx_flit, w_phy_rx_flit;\n"
           f"    ot_fdi_phy_cdc #(.W({W}), .DEPTH(8)) u_fdi_cdc (.clk(clk), .link_rst_n(i_host_link_rst_n_q[0]),\n"
           f"        .c_tx_v(i_host_fdi_q[{W}]), .c_tx_d(i_host_fdi_q[{W - 1}:0]), .c_rx_v(w_core_rx_v[0]), .c_rx_d(w_core_rx_flit),\n"
           f"        .c_tx_up(w_core_tx_up[0]), .clk_phy(clk_clk_phy), .p_rst_n(w_phy_rst_n), .p_tx_v(w_phy_tx_v),\n"
           f"        .p_tx_d(w_phy_tx_flit), .p_rx_v(w_phy_rx_v), .p_rx_d(w_phy_rx_flit), .p_tx_up(w_phy_tx_up));\n"
           f"    // as-built serdes_host.u_sub.u_{side} (on clk_phy)\n"
           f"    ot_qfd_serdes_112g_x6_phy #(.W({W})) u_core (\n"
           f"        .clk(clk_clk_phy),\n        .rst_n(w_phy_rst_n),\n        .rx_flit(w_phy_rx_flit),\n        .rx_v(w_phy_rx_v),\n"
           f"        .tx_flit(w_phy_tx_flit),\n        .tx_up(w_phy_tx_up),\n        .tx_v(w_phy_tx_v)\n    );\n")
    s = s.replace(old, new)
    s = s.replace("// every crossing registered on both sides (ot_dp_st, data + epoch); one clock, one reset synchroniser.",
                  "// every crossing registered on both sides (ot_dp_st, data + epoch); core clock + clk_phy (" + MARK +
                  ": the PHY half behind ot_fdi_phy_cdc).")
    put(p, s)


def hub_wi(p):
    s = open(p).read()
    if MARK in s:
        return
    s = sub1(s, "    input  wire clk_clk_phy,\n", "", "hub_Wi clk_clk_phy port")
    s = sub1(s, "    wire [0:0] w_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y;\n", "", "AND wire")
    s = sub1(s, "    wire [0:0] d4_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y;\n", "", "d4 wire")
    s, n = re.subn(r"    ot_dp_dly #\(\.W\(1\), \.D\(4\)\) u_d4_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y [^\n]*\n", "", s)
    assert n == 1, "d4 instance"
    s, n = re.subn(r"    assign w_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y = [^\n]*\n", "", s)
    assert n == 1, "AND assign"
    assert "kv_phy_slices_sv_197" not in s
    s = sub1(s, "        .ck_pad(clk_clk_phy),\n", "        .ck_pad(clk),\n", "ck_pad")
    s = sub1(s, "        .ck_phy({clk_clk_phy, clk_clk_phy, clk_clk_phy, clk_clk_phy, clk_clk_phy, clk_clk_phy, clk_clk_phy, clk_clk_phy}),\n",
             "        .ck_phy({clk, clk, clk, clk, clk, clk, clk, clk}),\n", "ck_phy")
    s = sub1(s, "        .ck_phy_rx_w(clk_clk_phy),\n", "        .ck_phy_rx_w(clk),\n", "ck_phy_rx_w")
    s = sub1(s, "        .ck_phy_tx_r(clk_clk_phy),\n", "        .ck_phy_tx_r(clk),\n", "ck_phy_tx_r")
    assert "clk_clk_phy" not in s
    s = sub1(s, "        .phy_rx_flit({i_serdes_E_rx_flit_q[520:0], i_serdes_W_rx_flit_q[521:0]}),\n",
             "        .phy_rx_flit(w_fdi_rx_flit),\n", "phy_rx_flit")
    s = sub1(s, "        .phy_rx_v(d4_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y[0]),\n", "        .phy_rx_v(w_fdi_rx_v),\n", "phy_rx_v")
    s = sub1(s, "        .phy_up(and_0),\n", "        .phy_up(w_fdi_phy_up),\n", "phy_up")
    blk = ("    // " + MARK + " (C1 + C2): host SerDes FDI face.  Each x6 half arrives from its own ot_fdi_phy_cdc (sys_SW / sys_SE: the\n"
           "    // ONE clock crossing) with its valid in the same lane word as its data; the halves are paired by order\n"
           "    // (ot_fdi_join2), replacing AND(W.rx_v, E.rx_v) + the kept as-built ot_dp_dly D=4 the data never got (C1: valid 4\n"
           "    // flits late; halves 30 / 36 cycles).  Adapter, pad and its CDC channels run on the core clock (no second\n"
           "    // crossing); the adapter's transmit slots (tx_up = link up AND slot) are paced below the PHY flit rate.\n"
           "    wire w_fdi_rx_v, w_fdi_slot, w_fdi_phy_up;\n"
           "    wire [1042:0] w_fdi_rx_flit;\n"
           "    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_fdi_join (.clk(clk), .rst_n(w_host_link_rst_n[0]),\n"
           "        .a_v(i_serdes_W_rx_flit_q[522]), .a_d(i_serdes_W_rx_flit_q[521:0]), .b_v(i_serdes_E_rx_flit_q[521]),\n"
           "        .b_d(i_serdes_E_rx_flit_q[520:0]), .o_v(w_fdi_rx_v), .o_d(w_fdi_rx_flit));\n"
           "    ot_fdi_tx_pace #(.NUM(19), .DEN(24)) u_fdi_pace (.clk(clk), .rst_n(w_host_link_rst_n[0]), .slot(w_fdi_slot));\n"
           "    assign w_fdi_phy_up = and_0 & w_fdi_slot;\n")
    anchor = "    qkd_host_root_admission_obsx_bo1 #("
    s = sub1(s, anchor, blk + anchor, "u_host anchor")
    put(p, s)


def top(p):
    s = open(p).read()
    if MARK in s:
        return
    for inst, mod in (("sys_SE", "kv3_sys_SD_v1_part"), ("sys_SW", "kv3_sys_SD_part")):
        s = sub1(s, f"    {mod} {inst} (\n        .clk(clk_core),\n        .arst_n(rst_n),\n",
                 f"    {mod} {inst} (\n        .clk(clk_core),\n        .arst_n(rst_n),\n        .clk_clk_phy(clk_clk_phy),   // {MARK} (C2)\n",
                 f"top {inst}")
    i0 = s.index("    kv3_hub_Wi_part hub_Wi (\n")
    i1 = s.index("    );\n", i0)
    seg = s[i0:i1]
    assert seg.count("        .clk_clk_phy(clk_clk_phy),\n") == 1, "top hub_Wi clk_clk_phy"
    s = s[:i0] + seg.replace("        .clk_clk_phy(clk_clk_phy),\n", "") + s[i1:]
    s = s.replace("module qwen_kvsys_bound_top (", f"// {MARK}: C1+C2 vehicle edit (clk_phy -> sys_SW / sys_SE PHY halves, not hub_Wi)\nmodule qwen_kvsys_bound_top (", 1)
    put(p, s)


def main():
    V, bo1, repo = (os.path.abspath(x) for x in sys.argv[1:4])
    R = f"{V}/src/bind__rtl"
    # files.f carries the staging host's absolute prefix (build.sh re-roots it): match entries by suffix
    ff = f"{V}/files.f"
    lines = open(ff).read().splitlines()
    P0 = re.sub(r"/src/.*", "", lines[0])
    # hub_Wi: the BO1 candidate (+ its two host sources) unless already C-edited
    hw = f"{R}/kv3_hub_Wi_part.sv"
    if MARK not in open(hw).read():
        if md5(hw) != BO1_MD5:
            if md5(bo1) != BO1_MD5:
                sys.exit(f"apply_C: BO1 candidate {bo1} md5 {md5(bo1)} != {BO1_MD5}")
            shutil.copyfile(bo1, hw)
            changed.append(hw + " (<- BO1 candidate)")
    for f in ("qkd_host_root_admission_obsx_bo1.sv", "qkd_d2d_boot_event_bridge.sv"):
        if not any(l.endswith("/" + f) for l in lines):
            shutil.copyfile(f"{repo}/rtl/qwen_sys/kv_host_obs_20261019/{f}", f"{R}/{f}")
            lines.append(f"{P0}/src/bind__rtl/{f}")
            changed.append(f"{R}/{f} (+files.f)")
    # new RTL: own tagged dir, listed in files.f
    C = f"{V}/src/c1c2__rtl"
    os.makedirs(C, exist_ok=True)
    for f in ("ot_fdi_phy_cdc.sv", "ot_fdi_join2.sv", "ot_fdi_tx_pace.sv"):
        src, dst = f"{repo}/rtl/physical/{f}", f"{C}/{f}"
        if not os.path.exists(dst) or open(src).read() != open(dst).read():
            shutil.copyfile(src, dst)
            changed.append(dst)
        if not any(l.endswith("/c1c2__rtl/" + f) for l in lines):
            lines.append(f"{P0}/src/c1c2__rtl/{f}")
            changed.append(ff + f" (+{f})")
    new = "\n".join(lines) + "\n"
    if open(ff).read() != new:
        open(ff, "w").write(new)
    sys_sd(f"{R}/kv3_sys_SD_part.sv", 522, "W")
    sys_sd(f"{R}/kv3_sys_SD_v1_part.sv", 521, "E")
    hub_wi(hw)
    top(f"{R}/qwen_kvsys_bound_top.sv")
    # bound top sha record (stage_src.sh convention)
    open(f"{V}/bound_top.sha256", "w").write(hashlib.sha256(open(f"{R}/qwen_kvsys_bound_top.sv", "rb").read()).hexdigest() + "\n")
    print(f"apply_C: {len(changed)} change(s)")
    for c in changed:
        print(f"  changed {c}")
    if not changed:
        print("  (already applied: nothing to do)")


if __name__ == "__main__":
    main()
