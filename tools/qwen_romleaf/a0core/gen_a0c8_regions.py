#!/usr/bin/env python3
r"""QC-A0 10-24 A0 v8 regions (F1, structural): each LSL head's rung-0 landed crossing is co-located at the hub.

    gen_a0c8_regions.py nk|nl OUT.tcl [--e-orient MY|R0] [--qlr3 hub|face]

v7 -> v8 (same outline, pins, RTL body, cycles):
  * per head g, ONE hub sub-box hd<g> holds the head's ring WRITERS (u_qlw2w/e) AND its READERS (u_qlr2c/w/e,
    including the reader output flops that Yosys names g_tx9.tc[..]): the 4-slot banks (2 x 512 b + the shared 600-b
    l2c bank) never leave the hub.  Only the rung-1 word (XW = 390 b, reader q -> leaf round/mask -> g_r[1].u_tx at
    the head's pin face) crosses to the face, register -> wire -> register.
  * hub sub-boxes are a 3 x 3 array that mirrors the LSL array (head column / row -> sub-box column / row); the empty
    slot's own position (middle column, row 0) holds the shared l2c writer u_qlw2c.
  * each head's face box f<g> holds its rung-1 register, its result-ring writer u_qlw3 (captures the leaf pins) and
    the leaf reset relay g_lrr.rq; --qlr3 face also puts the result-ring reader u_qlr3 there (only the 73-b result
    word leaves the face), --qlr3 hub puts it into hd<g> for the heads whose face is not on the W side.
  * regex fix: v7 matched only '/'-separated names (g_r\[1\]\.u_tx/) and missed the flattened reader flops
    g_tx9.tc[..] (1,024 / tile), which fell into the catch-all 'hub' box; v8 matches the flattened names.
  * the catch-all EXCLUSIVE 'hub' box (and its 4-um seam to the writer boxes) is gone: the remaining control
    registers (u_me issue / operand control, ib_i, ...) are FREE (claimed, not boxed: GPL places them between their
    drivers and loads), as are the x-operand landing ring g_xm9 and the request / fault landings (as in v7).
  * all top-zone groups are INCLUSIVE (members fenced in, their combinational cones may share the box; v7's
    EXCLUSIVE boxes pushed the reader muxes / enables out into the seams).
  * ROM-zone groups (L1 rings rsw/rnw/rse/rne, readers lsw..lne, operand dw/de) are v7 unchanged.
--e-orient MY (default): the E LSL column (sl3/6/7) is mirrored so its pin face looks W into the 35-um channel at
x 300.24-335.66 (beside the hub) instead of the 20-um E die margin: no head word crosses the E column.
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

LW, LH = 99.792, 140.4
HALO = 5.4
X_W, X_M, X_E = 100.656, 200.448, 335.664
Y_R = (673.92, 834.432, 994.944)
HEADS = {0: ("W", 0), 1: ("W", 1), 2: ("W", 2), 4: ("M", 1), 5: ("M", 2), 3: ("E", 0), 6: ("E", 1), 7: ("E", 2)}
ROM_TOP = 542.88 + 110.16  # 653.04


def head_box(g, e_orient):
    col, row = HEADS[g]
    x = dict(W=X_W, M=X_M, E=X_E)[col]
    return x, Y_R[row]


def face(g, e_orient):
    col, row = HEADS[g]
    if col == "W":
        return "W", X_W
    if col == "M":
        return "E", X_M + LW
    return ("W", X_E) if e_orient == "MY" else ("E", X_E + LW)


def face_box(g, e_orient):
    side, fx = face(g, e_orient)
    _, y0 = head_box(g, e_orient)
    y1 = y0 + LH
    col, _ = HEADS[g]
    if col == "W":                       # W channel between the node (x <= 69.984) and the W LSL column (v7 box)
        return (79.656, y0, 95.056, y1)
    if col == "M":                       # E face of sl4/5 into the 35-um channel: its W half
        return (305.84, y0, 316.84, y1)
    if e_orient == "MY":                 # W face of sl3/6/7 into the same channel: its E half
        return (319.24, y0, 330.064, y1)
    return (441.056, y0, 455.256, y1)    # v7: E die margin


# hub: x from the W LSL column's halo to the face boxes of the channel, y from the ROM top halo to the row-1 halo
HUB = (X_M + HALO, 660.64, 316.84, Y_R[1] - HALO)  # y0 = v7 dwr/der bottom, clear of the ROM-zone EXCLUSIVE boxes (<= 659.04)
SUBCOL = dict(W=0, M=1, E=2)
# where each head's result-ring READER u_qlr3 sits (the result word then hops to the t_out pin flops at the W edge):
#   face: beside its writer u_qlw3 at the head's pin face (only the 73-b result word leaves the face);
#   hd<g>: in hub sub-box g (the 4-slot bank crosses to it).  'mix' (v8): face for every head whose face -> t_out
#   leg is <= ~330 um; sl3 (row 0, face at x 335.66, t_out bits 192-255 at y ~938-950 on the W edge: face -> pin
#   ~440-480 um) lands in the NW hub sub-box hd2 (face -> hd2 ~100-160 um, hd2 -> t_out ~360 um).
QLR3 = dict(face={g: "face" for g in range(8)},
            hub={g: ("face" if HEADS[g][0] == "W" else f"hd{g}") for g in range(8)},
            mix={g: ("hd2" if g == 3 else "face") for g in range(8)})


def sub_box(col, row):
    x0, y0, x1, y1 = HUB
    dx, dy = (x1 - x0) / 3, (y1 - y0) / 3
    return (round(x0 + col * dx, 3), round(y0 + row * dy, 3), round(x0 + (col + 1) * dx, 3), round(y0 + (row + 1) * dy, 3))


def gen(k, e_orient, qlr3):
    P = r"g_sl\[%d\]\.g_hd\."
    lines = []

    def grp(name, typ, rx, boxes, mn=1, mx=100000):
        b = " ".join("{%s}" % " ".join(f"{v:.3f}" for v in bx) for bx in boxes)
        lines.append(f"  [dict create name {name} type {typ} regex {{{rx}}} boxes {{{b}}} min {mn} max {mx}] \\")

    grp("land_rq", "FREE", r"g_rom_pipe\.rq_(ce|ad)_[sn]\[1\]\[", [], 1)
    grp("land_fault", "FREE", r"u_me\.(fault_q\[|g_hier\.g_sl\[[0-7]\]\.g_hd\.g_fl\.q)", [], 0, 200)
    # head face boxes: rung 1 (kept u_tx, '/' hierarchy), result-ring writer, leaf reset relay (+ result reader)
    for g in range(8):
        col, row = HEADS[g]
        fr = (P % g) + r"(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq"
        if QLR3[qlr3][g] == "face":
            fr += r"|g_out9\.u_qlr3\."
        fr += ")"
        grp(f"f{g}", "INCLUSIVE", fr, [face_box(g, e_orient)])
    # hub sub-boxes: writers + readers (+ result reader of the non-W heads when --qlr3 hub)
    for g in range(8):
        col, row = HEADS[g]
        hr = (P % g) + r"g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)"
        rq = [h for h in range(8) if QLR3[qlr3][h] == f"hd{g}"]
        if rq:
            hr = "(" + hr + "|" + r"g_sl\[[%s]\]\.g_hd\.g_out9\.u_qlr3\." % "".join(map(str, rq)) + ")"
        grp(f"hd{g}", "INCLUSIVE", hr, [sub_box(SUBCOL[col], row)])
    grp("l2c", "INCLUSIVE", r"\.g_l2c\.u_qlw2c\.", [sub_box(1, 0)])
    # ROM zone (v7 unchanged)
    v7 = ROOT / f"tools/qwen_romleaf/repack/qfd_tile_{k}_a0v3_regions.tcl"
    rom = [l for l in v7.read_text().splitlines()
           if re.match(r"\s*\[dict create name (rsw|rnw|rse|rne|lsw|lse|lnw|lne|dw|de) ", l)]
    assert len(rom) == 10, len(rom)
    lines.extend(rom)
    grp("land_xm9", "FREE", r"\.g_xm9\.u_xr\.", [], 1)
    grp("land_top", "FREE", r"^(u_ot_pr_core\.)?u_g\.u_tile\.(n_va|fault_q)$", [], 0, 4)
    grp("ctl", "FREE", r"^(u_ot_pr_core\.)?u_g\.u_tile\.", [], 1)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("k"); ap.add_argument("out")
    ap.add_argument("--e-orient", default="MY"); ap.add_argument("--qlr3", default="mix")
    a = ap.parse_args()
    body = gen(a.k, a.e_orient, a.qlr3)
    hdr = (__doc__.strip().splitlines())
    txt = "".join("# " + l + "\n" if l else "#\n" for l in hdr[3:])
    txt += f"# generated: gen_a0c8_regions.py {a.k} --e-orient {a.e_orient} --qlr3 {a.qlr3}\n"
    txt += "set qrl_groups [list \\\n" + "\n".join(body) + "\n]\n"
    txt += "source /src/tools/qwen_romleaf/rc14_2000/baseline/parent_regions.tcl\n"
    Path(a.out).write_text(txt)
    print(a.out, len(body), "groups; hub", HUB, "sub", [sub_box(c, r) for r in range(3) for c in range(3)])


if __name__ == "__main__":
    main()
