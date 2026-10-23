#!/usr/bin/env python3
"""A0-REPACK (10-23): re-packed A0 ROM-leaf parents qfd_tile_n{k,l}_romleaf (owner order, industry practice).

Same RTL / children / clocks / REGROOT 9 crossings as the rc15a kits (Codex QW-A0-2000 local request decode, census
clean); only the floorplan, the pin plan and the soft-root fences change.

Top-down budget (tools/qwen_cluster/qc_gen.py CB16 slot 2445.096 x 5227.176): x = corridors L 86.4 + A/T/B 3 x 146.88 +
R 86.4 = 613.44 + 4 A0 => A0 width <= 457.92; y = strips 2 x 86.4 + 3 row gaps x 129.6 = 561.6 + 4 A0 => A0 height
<= 1166.4.  Both variants below are 457.92 x 1157.76 (0.530 mm2, -28.8 % vs 820.8 x 907.2) and leave every corridor of
the slot as qc_gen derived it, plus 4 x 8.64 um of y.

MAIN 'm' (ROM pairs back to back): ROM block (bottom) = 5 rows of [col 0 R0 pins W | col 1 MY pins E], the two bare
faces abutted (abutted_row), pins open into one 54-um W and one 54-um E operand channel that hold the bank OR trees /
L1 landing rings (rsw/rnw, rse/rne) and the operand readers (dw/de) of their own column.  LSL block (top) = 3 rows of
[NK node (R0, pins W at the n_* face) | 30.7-um TX channel | LSL A MY pins W + LSL B R0 pins E back to back | 35.4-um
TX channel | LSL C R0 pins E | E band]; A = g0..2, B = g4..6, C = g3 / g7 (rows 1, 2), C row 0 = issue-engine pocket
beside the tap pins.  ROM row channels 20.0 um, LSL row channels 20.1 um, ROM-LSL band 20.9 um.
FALLBACK 'f' (ROM pairs face to face): the same LSL block; ROM rows [col 0 MY pins E | 67.4-um central operand spine |
col 1 R0 pins W]; RW / D of both columns in the spine (shortest ROM->ring, one shared spine; 20-um edge bands).
"""
import copy, json, math, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROM_W, ROM_H, LSL_W, LSL_H, NODE_W, NODE_H = 172.8, 110.16, 99.792, 140.4, 47.52, 432.0
CM, PE, CH = 2.16, 20.0, 20.0
W = 457.92
ME = "u_g.u_tile.u_tile.u_logic"
VIEWS = {"ROM": "physical/ref_tile/ot_qwen_tile_romleaf/views/ot_qwen_tile_romleaf",
         "LSL": "physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1",
         "NODE": "physical/ref_tile/qw_a0_rc14_children/node_nb1/ot_qwen_tile_node"}

def up(v, q):
    return round(math.ceil(round(v / q, 6) - 1e-9) * q, 4)

def dn(v, q):
    return round(math.floor(round(v / q, 6) + 1e-9) * q, 4)

# ---- geometry ------------------------------------------------------------------------------------------------------
Y_ROM = [up(CM + CH, 0.048) + i * up(ROM_H + CH, 0.048) for i in range(5)]       # 22.176 + i * 130.176
Y_ROM = [round(v, 4) for v in Y_ROM]
ROM_ROW_OF_BANK = {0: 0, 1: 1, 2: 2, 4: 3, 3: 4}      # S group 0..2 at the bottom, N group 4, 3 (bank 3 at the band)
ROM_TOP = Y_ROM[-1] + ROM_H
Y_LSL0 = up(ROM_TOP + CH, 8.64)
LSL_PITCH = up(LSL_H + CH, 0.192)
Y_LSL = [round(Y_LSL0 + i * LSL_PITCH, 4) for i in range(3)]
LSL_TOP = Y_LSL[-1] + LSL_H
H = up(LSL_TOP + CH + CM, 8.64)
X_NODE = up(CM + PE, 0.432)
X_C = dn(W - CM - PE - LSL_W, 0.432)
X_A = 100.656                                  # node E face 69.984 + 30.672 TX channel (chW)
X_B = round(X_A + LSL_W, 4)
CH_W = round(X_A - (X_NODE + NODE_W), 4)
CH_2 = round(X_C - (X_B + LSL_W), 4)
Y_NODE = up((Y_LSL[0] + LSL_TOP) / 2 - NODE_H / 2, 0.048)
LSL_AT = {0: (X_A, 0, "MY"), 1: (X_A, 1, "MY"), 2: (X_A, 2, "MY"), 4: (X_B, 1, "R0"), 5: (X_B, 2, "R0"),
          3: (X_C, 0, "R0"), 6: (X_C, 1, "R0"), 7: (X_C, 2, "R0")}   # B row 0 = the issue-engine pocket (tile centre)

def rom_x(var):
    if var == "m":
        x0 = up((W - 2 * ROM_W) / 2, 0.432)
        return {0: (x0, "R0"), 1: (round(x0 + ROM_W, 4), "MY")}
    x1 = dn(W - CM - PE - ROM_W, 0.432)
    return {0: (up(CM + PE, 0.432), "MY"), 1: (x1, "R0")}

def plan(nk, var):
    ch = {}
    rx = rom_x(var)
    for p in (0, 1):
        for b in range(5):
            ch[f"ROM{p}{b}"] = [rx[p][0], Y_ROM[ROM_ROW_OF_BANK[b]], rx[p][1]]
    for gg, (x, r, o) in LSL_AT.items():
        ch[f"LSL{gg}"] = [x, Y_LSL[r], o]
    if nk:
        ch["NODE"] = [X_NODE, Y_NODE, "R0"]
    return ch

def children(nk, var):
    out = []
    for k, (x, y, o) in plan(nk, var).items():
        if k == "NODE":
            inst = f"{ME}.genblk5.g_ndh.u_node"
        elif k.startswith("LSL"):
            inst = f"{ME}.u_me.g_hier.g_sl[{k[3:]}].g_hd.u_lh"
        else:
            inst = f"{ME}.g_rom_pipe.g_rph.g_rb[{k[4]}].g_single.g_col[{k[3]}].u_leaf"
        out.append(dict(view=VIEWS[re.sub(r"\d", "", k)], count=1, inst=inst, at=[x, y], orient=o, at_exact=True))
    return out

# ---- pins ----------------------------------------------------------------------------------------------------------
def snap(y):
    return round(0.012 + 0.096 * round((y - 0.012) / 0.096), 3)

ROM_CLK_LOCAL = 21.76        # ROM clk pin (LEF y); MX not used
LSL_CLK_LOCAL = 62.99

def pin_plan(nk, var):
    """face -> [(pin, y)]; buses at 0.192 (5.2 pins/um) aligned with their consumer, singles beside their root's mass"""
    yr = {b: Y_ROM[ROM_ROW_OF_BANK[b]] for b in range(5)}
    yl = {gg: Y_LSL[r] for gg, (_x, r, _o) in LSL_AT.items()}
    ntop = Y_NODE
    W_bus = [("t_out", 514, ntop + 211.98)]
    if nk:
        W_bus = [("n_a", 514, ntop + 10.91), ("n_b", 514, ntop + 111.52), ("t_out", 514, ntop + 211.98),
                 ("n_y", 514, ntop + 312.49)]
    E_bus = [("tap", 508, ROM_TOP - 92.0), ("tile_id", 16, ROM_TOP + 12.0)]
    W_single = {**{f"ck_rp{b}": yr[b] + ROM_CLK_LOCAL for b in range(5)},
                "ck_rsw": yr[1] + 60.0, "ck_rnw": yr[4] + 60.0, "ck_dw": ROM_TOP - 30.0,
                **{f"ck_lsl{g}": yl[g] + LSL_CLK_LOCAL for g in (0, 1, 2)},
                **{f"ck_tx{g}": yl[g] + LSL_CLK_LOCAL + 12.0 for g in (0, 1, 2)},
                "ck_fa2": ntop + 211.98 + 104.0}
    E_single = {**{f"ck_rp{b + 5}": yr[b] + ROM_CLK_LOCAL for b in range(5)},
                "ck_rs": yr[1] + 60.0, "ck_rn": yr[4] + 60.0, "ck_de": ROM_TOP - 30.0,
                **{f"ck_lsl{g}": yl[g] + LSL_CLK_LOCAL for g in (3, 4, 5, 6, 7)},
                **{f"ck_tx{g}": yl[g] + LSL_CLK_LOCAL + 12.0 for g in (3, 4, 5, 6, 7)},
                "ck_fa4": ROM_TOP - 95.0, "rst_n": ROM_TOP + 17.0, "tie_hi": ROM_TOP + 19.0,
                "tie_lo": ROM_TOP + 21.0, "ck": ROM_TOP + 15.0}
    if nk:
        W_single.update({"ck_fa0": ntop + 6.0, "ck_fa1": ntop + 111.0, "ck_fa3": ntop + 312.0 - 3.0,
                         "ck_node": ntop + 204.0})
    out = {}
    for face, buses, singles in (("W", W_bus, W_single), ("E", E_bus, E_single)):
        # singles first, each at its root's mass (>= 0.96 apart); buses then run at 0.192 and step over every single
        # (a 0.96-um hole), each bus starting no lower than the end of the previous one
        rows, used = [], []
        for name, y0 in sorted(singles.items(), key=lambda kv: kv[1]):
            y = snap(y0); k = 0
            while any(abs(y - u) < 0.95 for u in used):
                k += 1; y = snap(y0 + (k // 2 + 1) * 0.96 * (1 if k % 2 else -1))
            assert 3.0 < y < H - 3.0 and abs(y - y0) < 10, (name, y0, y)
            used.append(y); rows.append((name, y))
        last = -1.0
        for name, n, y0 in sorted(buses, key=lambda t: t[2]):
            y = snap(max(y0, last + 0.192))
            for i in range(n):
                while any(abs(y - u) < 0.45 for u in used):
                    y = round(y + 0.192, 3)
                rows.append((f"{name}[{i}]", y)); y = round(y + 0.192, 3)
            last = y - 0.192
            assert last < H - 3.0, (name, last)
        ys = sorted(v for _n, v in rows)
        assert all(b - a > 0.15 for a, b in zip(ys, ys[1:])), face
        out[face] = rows
    return out

def pins_tcl(kit, nk, var):
    p = pin_plan(nk, var)
    o = [f"# {kit}: generated by tools/qwen_romleaf/repack/gen_repack.py (A0-REPACK 10-23, {W} x {H} um).",
         "# W/E faces, M4, 0.192 um bus pitch (5.2 pins/um); every bus aligned with its consumer, every clock entry at its",
         "# root's mass (ROM rows, LSL rows, operand channels, issue pocket).  Same ports and faces as the rc14 rc2 plan",
         "# except ck_lsl3 / ck_tx3 (LSL 3 now sits in the E column: W -> E face)."]
    for face, rows in p.items():
        x = 0.096 if face == "W" else round(W - 0.096, 3)
        for name, y in sorted(rows, key=lambda r: r[1]):
            o.append(f"place_pin -pin_name {{{name}}} -layer M4 -location {{{x:.3f} {y:.3f}}}")
    return "\n".join(o) + "\n", {f: sorted({re.sub(r"\[.*", "", n) for n, _ in rows}) for f, rows in p.items()}

# ---- soft-root fences (same groups / regexes as rc13 nk_rc13_regions.tcl; new boxes; L9 writers FREE) ---------------
LO = "([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])"
def tx_box(gg):
    x, r, o = LSL_AT[gg]
    y0 = Y_LSL[r]
    if o == "MY":          # pins W: fence in the chW lane at the pin face
        return (round(x - 14.0, 3), y0, round(x - 0.5, 3), round(y0 + LSL_H, 3))
    xe = x + LSL_W
    return (round(xe + 0.5, 3), y0, round(xe + (14.0 if x == X_B else 12.0), 3), round(y0 + LSL_H, 3))

def chan_boxes(var):
    """x-ranges (rw_w, d_w, rw_e, d_e): the L1 ring writer lane on each ROM column's pin face, the operand-reader /
    L9-writer lane beside it (MAIN: the rest of the 54-um channel; FALLBACK: the two middle lanes of the spine)"""
    rx = rom_x(var)
    if var == "m":
        w_pin = rx[0][0]; e_pin = rx[1][0] + ROM_W
        return (w_pin - 15.6, w_pin - 0.4), (CM + 0.4, w_pin - 16.4), (e_pin + 0.4, e_pin + 15.6), (e_pin + 16.4, W - CM - 0.4)
    w_pin = rx[0][0] + ROM_W; e_pin = rx[1][0]
    mid = (w_pin + e_pin) / 2
    return (w_pin + 0.4, w_pin + 15.6), (w_pin + 16.4, mid - 0.4), (e_pin - 15.6, e_pin - 0.4), (mid + 0.4, e_pin - 16.4)

def regions_tcl(kit, nk, var):
    (rw0, rw1), (dw0, dw1), (re0, re1), (de0, de1) = chan_boxes(var)
    s_lo, s_hi = Y_ROM[0] + 10.0, Y_ROM[2] + ROM_H - 10.0
    n_lo, n_hi = Y_ROM[3] + 10.0, Y_ROM[4] + ROM_H - 10.0
    d_lo, d_hi = Y_ROM[2] + 20.0, Y_ROM[3] + ROM_H     # operand readers between the S and N ring writers
    l9_lo, l9_hi = Y_ROM[4] + 20.0, ROM_TOP + 8.0      # L9 ring writers at the band (one compact block per operand root)
    hub = (X_B + 10.0, Y_LSL[0] + 10.0, X_B + LSL_W - 10.0, Y_LSL[0] + LSL_H - 40.0)
    f = lambda b: "{{" + " ".join(f"{v:.3f}" for v in b) + "}}"
    tx = []
    for gg in range(8):
        tx.append(f"  [dict create name tx{gg} type EXCLUSIVE regex {{(g_sl\\[{gg}\\]\\.g_hd\\.(g_tx9\\.(u_qlr2[cwe]\\.|g_r\\[1\\]\\.u_tx/)|g_out9\\.u_qlw3\\.)|g_sl\\[{gg}\\]\\.g_hd\\.(g_tx\\.g_r\\[[01]\\]\\.u_tx/|g_lrr\\.rq|g_outland\\.q))}} boxes {f(tx_box(gg))} min 1 max 100000] \\")
    g = [
      "  [dict create name land_rq type FREE regex {g_rom_pipe\\.rq_(ce|ad)_[sn]\\[1\\]\\[} boxes {} min 1 max 100000] \\",
      "  [dict create name land_fault type FREE regex {u_me\\.(fault_q\\[|g_hier\\.g_sl\\[[0-7]\\]\\.g_hd\\.g_fl\\.q)} boxes {} min 0 max 200] \\",
      *tx,
      f"  [dict create name rsw type EXCLUSIVE regex {{(g_col_land\\.u_qlw1sw\\.|(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gs|gs_q)\\[{LO}\\]|g_rph\\.g_rb\\[[0-2]\\]\\.g_single\\.g_col\\[0\\]\\.g_lrr\\.rq))}} boxes {f((rw0, s_lo, rw1, s_hi))} min 1 max 100000] \\",
      f"  [dict create name rnw type EXCLUSIVE regex {{(g_col_land\\.u_qlw1nw\\.|(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gn|gn_q)\\[{LO}\\]|g_rph\\.g_rb\\[[34]\\]\\.g_single\\.g_col\\[0\\]\\.g_lrr\\.rq))}} boxes {f((rw0, n_lo, rw1, n_hi))} min 1 max 100000] \\",
      f"  [dict create name rse type EXCLUSIVE regex {{(g_col_land\\.u_qlw1se\\.|(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gs|gs_q)\\[|g_rph\\.g_rb\\[[0-2]\\]\\.g_single\\.g_col\\[1\\]\\.g_lrr\\.rq))}} boxes {f((re0, s_lo, re1, s_hi))} min 1 max 100000] \\",
      f"  [dict create name rne type EXCLUSIVE regex {{(g_col_land\\.u_qlw1ne\\.|(g_rqr\\.(genblk[0-9]+\\.g_col_roots\\.gn|gn_q)\\[|g_rph\\.g_rb\\[[34]\\]\\.g_single\\.g_col\\[1\\]\\.g_lrr\\.rq))}} boxes {f((re0, n_lo, re1, n_hi))} min 1 max 100000] \\",
      f"  [dict create name dw type EXCLUSIVE regex {{(g_col_land\\.u_qlr1[sn]w\\.|u_me\\.s2_w\\[([0-9]|[1-9][0-9]|[1-9][0-9][0-9]|10[01][0-9]|102[0-3])\\]|(g_hd\\.g_tx\\.g_r\\[0\\]\\.di\\[(16[0-9]|17[0-5]|19[2-9]|20[0-7]|22[4-9]|23[0-9]|25[6-9]|26[0-9]|27[01])\\]|u_me\\.g_operand_rr\\.g_lsel\\.s1b_(wsrc_w|gm_w\\[)|u_me\\.g_operand_rr\\.g_csel\\.(wsrc_q|gm_q)\\[([0-9]|1[0-5])\\]|u_me\\.mq_wrom\\[{LO}\\]|g_hd\\.g_tx\\.tc\\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\\]))}} boxes {f((dw0, d_lo, dw1, d_hi))} min 1 max 100000] \\",
      f"  [dict create name de type EXCLUSIVE regex {{(g_col_land\\.u_qlr1[sn]e\\.|u_me\\.s2_w\\[|(g_hd\\.g_tx\\.g_r\\[0\\]\\.di\\[(28[89]|29[0-9]|30[0-3]|32[0-9]|33[0-5]|35[2-9]|36[0-7]|38[4-9]|39[0-9])\\]|u_me\\.g_operand_rr\\.g_lsel\\.s1b_(wsrc_e|gm_e\\[)|u_me\\.g_operand_rr\\.g_csel\\.(wsrc_q|gm_q)\\[|u_me\\.mq_wrom\\[|g_hd\\.g_tx\\.tc\\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\\]))}} boxes {f((de0, d_lo, de1, d_hi))} min 1 max 100000] \\",
      f"  [dict create name dwr type EXCLUSIVE regex {{\\.g_tx9\\.u_qlw2w\\.}} boxes {f((dw0, l9_lo, dw1, l9_hi))} min 1 max 100000] \\",
      f"  [dict create name der type EXCLUSIVE regex {{\\.g_tx9\\.u_qlw2e\\.}} boxes {f((de0, l9_lo, de1, l9_hi))} min 1 max 100000] \\",
      "  [dict create name land_top type FREE regex {^(u_ot_pr_core\\.)?u_g\\.u_tile\\.(n_va|fault_q)$} boxes {} min 0 max 4] \\",
      "  [dict create name land_rings type FREE regex {\\.(g_l2c\\.u_qlw2c|g_xm9\\.u_xr|g_out9\\.u_qlr3)\\.} boxes {} min 1 max 100000] \\",
      f"  [dict create name hub type EXCLUSIVE regex {{^(u_ot_pr_core\\.)?u_g\\.u_tile\\.}} boxes {f(hub)} min 1 max 100000] \\",
    ]
    hdr = [f"# {kit}: generated by tools/qwen_romleaf/repack/gen_repack.py (A0-REPACK 10-23, variant {var}).",
           "# Same groups / regexes / order as rc13 nk_rc13_regions.tcl (rc14/rc15 baseline); boxes moved to the re-packed",
           "# consumers: TX rungs + out landings at each LSL's pin face, ROM L1 rings (rsw/rnw, rse/rne) on the pin lane of",
           "# their column's operand channel, operand readers dw/de above them at the ROM-LSL band, issue engine in the E pocket",
           "# beside the tap pins.  As rc13, the L9 ring writers (u_qlw2w/e) sit in one compact block per operand root (dwr/der,",
           "# top of the operand lane at the band, <= ~250 um from the readers on the same root); only the landed 4-slot ring",
           "# (K=2: >= 1 cycle of wire) crosses to the LSL block.  L1 rings: S writers (rows 0-2) and N writers (rows 3-4) land",
           "# in the reader lane between them (~200 um each).",
           "set qrl_groups [list \\"]
    return "\n".join(hdr + g + ["]", "source /src/tools/qwen_romleaf/rc14_2000/baseline/parent_regions.tcl", ""])

def request_decode_tcl(var):
    """rc15 local request decoder fence, re-pointed at the re-packed ROM pin lanes (same checks, same 5.4 x 5.4 box)."""
    src = (ROOT / "tools/qwen_romleaf/rc15_2000/local_request_decode.tcl").read_text()
    rx = rom_x(var)
    if var == "m":
        w_pin = rx[0][0]; e_pin = rx[1][0] + ROM_W
        x0w, x1w, x0e, x1e = w_pin - 6.0, w_pin - 0.6, e_pin + 0.6, e_pin + 6.0
    else:
        w_pin = rx[0][0] + ROM_W; e_pin = rx[1][0]
        x0w, x1w, x0e, x1e = w_pin + 0.6, w_pin + 6.0, e_pin - 6.0, e_pin - 0.6
    old = " if {$col==0} {set x0 232.2;set x1 237.6} else {set x0 583.2;set x1 588.6}"
    assert old in src
    new = f" if {{$col==0}} {{set x0 {x0w:.3f};set x1 {x1w:.3f}}} else {{set x0 {x0e:.3f};set x1 {x1e:.3f}}}"
    return ("# A0-REPACK 10-23 (gen_repack.py): tools/qwen_romleaf/rc15_2000/local_request_decode.tcl with the decoder boxes\n"
            "# on the re-packed ROM pin lanes; nothing else changed.\n" + src.replace(old, new))

# ---- spec ----------------------------------------------------------------------------------------------------------
def spec(nk, var):
    k = "nk" if nk else "nl"
    base = json.load(open(ROOT / f"physical/ref_tile/qfd_tile_{k}_romleaf_rc15a/spec.json"))
    kit = f"qfd_tile_{k}_romleaf_rp{var}"
    s = copy.deepcopy(base)
    s["name"] = kit
    s["outline"] = {"w": W, "h": H, "exact": True}
    s["children"] = children(nk, var)
    ptcl, faces = pins_tcl(kit, nk, var)
    s["pins"] = {"W": faces["W"], "E": faces["E"]}
    d = "tools/qwen_romleaf/repack"
    s["io_tcl"] = f"{d}/{kit}_pins.tcl"
    s["pin_hook_before_flops"] = [f"{d}/{kit}_regions.tcl", f"{d}/{kit}_request_decode.tcl"]
    s["child_lattice_um"] = 0.048
    lab = {"m": "MAIN: ROM pairs back to back (abutted_row), pins into W/E operand channels",
           "f": "FALLBACK: ROM pairs face to face across one central operand spine"}[var]
    s["structural_change"] = (f"A0-REPACK 10-23 ({lab}): re-pack of rc15a (same RTL, children, clocks, REGROOT 9, 0 cycles) "
        f"into {W} x {H} um (0.530 mm2, was 820.8 x 907.2 = 0.745), two tiers: ROM block (5 rows x 2) below an LSL block "
        "(3 rows: [node | TX | LSL MY|R0 back to back | TX | LSL]); 20-um channels, no slivers; buses aligned with their "
        "consumers; fences moved with their consumers, L9 ring writers FREE.  Plan: tools/qwen_romleaf/repack/gen_repack.py.")
    s["slot_change_request"] = (f"A0-REPACK 10-23: A0 {W} x {H} um fits the CB16 slot cell 457.92 x 1166.4 that qc_gen.py "
        "derives (corridors unchanged); vs the 820.8 x 907.2 rc14/rc15 kits: W/E faces kept, ck_lsl3 / ck_tx3 move W -> E, "
        "bus y positions change (cluster stand-in tools/qwen_cluster/a0_standin.py reads this pin Tcl).")
    s["reroute_reason"] = "A0-REPACK owner order 10-23: industry-practice re-pack, visual + first-principles review."
    j = s["job"]
    j["owner"] = "Claude:A0-REPACK"; j["branch"] = "claude/a0-repack-1023"; j["tag"] = f"rp{var}"
    j["purpose"] = s["structural_change"]
    j["views_to"] = f"physical/ref_tile/{kit}/views"; j["record_to"] = f"results/rtl/ref_tile/{kit}"
    return kit, s, ptcl, regions_tcl(kit, nk, var), request_decode_tcl(var)

def flyline_plan(nk, var):
    ch = plan(nk, var)
    pp = pin_plan(nk, var)
    ports = {}
    for face, rows in pp.items():
        acc = {}
        for n, y in rows:
            acc.setdefault("P_" + re.sub(r"\[.*", "", n), []).append(y)
        for b, ys in acc.items():
            ports[b] = [0.0 if face == "W" else W, sum(ys) / len(ys)]
    return {"name": f"rp{var}_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports}

if __name__ == "__main__":
    print(f"OUTLINE {W} x {H} = {W * H / 1e6:.4f} mm2  Y_ROM {Y_ROM} ROM_TOP {ROM_TOP:.3f}  Y_LSL {Y_LSL} LSL_TOP "
          f"{LSL_TOP:.3f}  X_A {X_A} X_B {X_B} X_C {X_C} chW {CH_W} ch2 {CH_2}  node {X_NODE},{Y_NODE}")
    if "--write" in sys.argv:
        for nk in (True, False):
            for var in ("m", "f"):
                kit, s, ptcl, rtcl, qtcl = spec(nk, var)
                d = ROOT / "tools/qwen_romleaf/repack"
                (d / f"{kit}_pins.tcl").write_text(ptcl)
                (d / f"{kit}_regions.tcl").write_text(rtcl)
                (d / f"{kit}_request_decode.tcl").write_text(qtcl)
                kd = ROOT / f"tools/qwen_romleaf/repack/specs"; kd.mkdir(exist_ok=True)
                (kd / f"{kit}.json").write_text(json.dumps(s, indent=1) + "\n")
                print("WROTE", kit, len(ptcl.splitlines()) - 4, "pins")
    if len(sys.argv) > 2 and sys.argv[1] == "--fly":
        sys.path.insert(0, str(HERE)); import flyline_model as FM, plans as PL
        cen = {"nl": json.load(open(sys.argv[2])), "nk": json.load(open(sys.argv[3]))}
        for nk in (False, True):
            k = "nk" if nk else "nl"
            o = PL.old(nk); o["fixed"] = FM.fences(ROOT / "tools/qwen_romleaf/rc14_2000/baseline/nk_rc13_regions.tcl")
            if not nk:
                o["fixed"] = {g: v for g, v in o["fixed"].items()}
            ps = [o]
            for var in ("m", "f"):
                q = flyline_plan(nk, var); kit = f"qfd_tile_{k}_romleaf_rp{var}"
                tf = pathlib.Path("/tmp") / f"{kit}_regions.tcl"; tf.write_text(regions_tcl(kit, nk, var))
                q["fixed"] = FM.fences(tf); ps.append(q)
            for p in ps:
                r = FM.solve(cen[k], p)
                json.dump(r, open(f"/home/ubuntu/scratch/a0-repack/fly_{p['name']}.json", "w"), indent=1)
                print(p["name"], "bit-mm", r["bit_mm"], {c: (v["bit_mm"], v["max_um"]) for c, v in list(r["classes"].items())[:8]})
