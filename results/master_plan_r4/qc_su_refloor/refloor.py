#!/usr/bin/env python3
"""MASTER-PLAN-R4 QC SU vmr/rp1 core RE-FLOORPLAN (12.8b order: internal H-tree first, split last; COORD 11:56 ruling).

Plan-only geometry. Content of qfd_dv_s8x_vmr / qfd_dv_s8_crh_rp1 = 2 x ot_sram_1r1w_1024x256 (174.744 x 70.488, pins on both
SHORT edges: L = clk/rd_out/raddr/waddr/wd[0:135], R = w_mask/wd[136:255]/repair) + 2.1k / 1.2k um2 std cells (synth area) +
1509 / 998 face pins (S write face, W read face).  Old floorplan: SRAMs stacked full-width in the middle, entry in the SRAM
channel, ~60 % of the sinks are S-face pin registers BEHIND the south SRAM -> entry->sink maze floor 343 / 277 um.

New floorplan F3 ("SRAM columns + centre gap"): both SRAMs rotated to columns (R270, west one mirrored) side by side, pin edges
at the N (L = read side) and S (R = write side) ends, a 21.6-um centre gap (clock trunk channel, entry island at the die
centre), N strip (read logic + L-end flops) and S strip (S-face pin regs + R-end flops), W read face pins kept on the W face
(top 54 um, next to the N strip).  Faces unchanged (S write, W read); only pin positions along each face move (top-down pin
assignment, unclosed tiles).  Outline from content: width = 2 SRAM columns + gap + 2 margin columns, height = SRAM + strips.

Sinks: every placed sink of the R4b geo is assigned to its functional group by its old position (W-face reg, S-face reg,
L-/R-end flop of SRAM k) and re-sited into that group's region of F3, preserving its order along the face/edge.  This is a
PLAN sink model (the placer will choose exact sites inside the regions); it is not a placement.
"""
import json
import sys
from pathlib import Path

SW, SH = 174.744, 70.488          # SRAM R0 size
PIN_LO, PIN_HI = 0.768, 40.512     # pin segment on each short edge (R0 y)
CK_OFF = 0.78
L = 4.32


def read(path):
    g = dict(sinks=[], macros=[], pins=[])
    for line in open(path):
        f = line.split()
        if not f:
            continue
        if f[0] == "CORE":
            g["core"] = list(map(float, f[1:5]))
        elif f[0] == "DIE":
            g["die"] = list(map(float, f[1:5]))
        elif f[0] == "SINK":
            g["sinks"].append((float(f[1]), float(f[2]), f[3], f[4], f[5]))
        elif f[0] == "MACRO":
            g["macros"].append((f[1], f[2], list(map(float, f[3:7]))))
        elif f[0] == "PIN":
            g["pins"].append((f[1], float(f[2]), float(f[3])))
    return g


def group(g):
    m = sorted(g["macros"], key=lambda t: t[2][1])        # m[0] south SRAM (bank0), m[1] north (bank1)
    x0, x1 = m[0][2][0], m[0][2][2]
    out = {k: [] for k in ("W", "S", "L0", "L1", "R0", "R1")}
    for s in g["sinks"]:
        x, y = s[0], s[1]
        k = 0 if abs(y - (m[0][2][1] + m[0][2][3]) / 2) < abs(y - (m[1][2][1] + m[1][2][3]) / 2) else 1
        if x < 25.0:
            out["W"].append(s)
        elif x < x0 and y > m[0][2][1] - 15:
            out[f"L{k}"].append(s)
        elif x > x1 and y > m[0][2][1] - 15:
            out[f"R{k}"].append(s)
        else:
            out["S"].append(s)
    return m, out


def spread(items, key, box, rows=None):
    """re-site items (order by key) uniformly over box [x0,y0,x1,y1], row-major along x."""
    items = sorted(items, key=key)
    n = len(items)
    if not n:
        return []
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rows = rows or max(1, round((n * h / w) ** 0.5))
    per = -(-n // rows)
    out = []
    for i, s in enumerate(items):
        r, c = divmod(i, per)
        out.append((round(x0 + (c + 0.5) * w / per, 3), round(y0 + (r + 0.5) * h / rows, 3)) + tuple(s[2:]))
    return out


def f3(g, gap=21.6, side=11.52, s_strip=34.56, n_strip=30.24, halo=2.2):
    m, grp = group(g)
    width = 2 * L + side + SH + gap + SH + side
    height = 2 * L + s_strip + SW + n_strip
    W = round(-(-width // L) * L, 3)
    H = round(-(-height // L) * L, 3)
    cx = round(round(W / 2 / L * 2) * L / 2, 3)
    cy = round(H / 2, 3)
    ys0 = L + s_strip
    ys1 = ys0 + SW
    gx0, gx1 = cx - gap / 2, cx + gap / 2
    mw = [gx0 - SH, ys0, gx0, ys1]                       # west column (bank0), R270 + MY: pins on its gap side
    me = [gx1, ys0, gx1 + SH, ys1]                       # east column (bank1), R270: pins on its gap side
    segw = (gx0 - PIN_HI, gx0 - PIN_LO)
    sege = (gx1 + PIN_LO, gx1 + PIN_HI)
    macros = [(m[0][0], m[0][1], mw, "MY_R270", (round(gx0 - CK_OFF, 3), round(ys1, 3))),
              (m[1][0], m[1][1], me, "R270", (round(gx1 + CK_OFF, 3), round(ys1, 3)))]
    core = [L, L, W - L, H - L]
    rowh = 0.27 * 4
    sinks = []
    # L ends (read side) at the N end of each column, just above its pin segment
    nb0, nb1 = ys1 + halo, ys1 + halo + min(n_strip - 2 * halo, 16.2)
    sinks += spread(grp["L0"], lambda s: s[1], [segw[0], nb0, segw[1], nb1])
    sinks += spread(grp["L1"], lambda s: s[1], [sege[0], nb0, sege[1], nb1])
    # R ends (write side) at the S end, just below the pin segment
    sb1, sb0 = ys0 - halo, ys0 - halo - 10.8
    sinks += spread(grp["R0"], lambda s: s[1], [segw[0], sb0, segw[1], sb1])
    sinks += spread(grp["R1"], lambda s: s[1], [sege[0], sb0, sege[1], sb1])
    # S-face pin registers: S strip below the band, ordered along the face as before
    sinks += spread(grp["S"], lambda s: (s[0], s[1]), [core[0] + 1.0, core[1] + 0.5, core[2] - 1.0, sb0 - 0.5])
    # W read-face registers: W face top 54 um (beside the column top + N strip), ordered by old y
    wy1 = core[3] - 1.0
    sinks += spread(grp["W"], lambda s: s[1], [core[0] + 0.5, wy1 - 54.0, core[0] + side - halo - 0.5, wy1])
    return dict(die=[0, 0, W, H], core=core, entry=(cx, cy), macros=macros, sinks=sinks,
                groups={k: len(v) for k, v in grp.items()}, gap=[gx0, gx1], strips=dict(S=[core[1], ys0], N=[ys1, core[3]]),
                pin_faces=dict(S=[core[0], core[2]], W=[wy1 - 54.0, wy1]))


def write_geo(r, path):
    with open(path, "w") as fh:
        fh.write("DIE %.3f %.3f %.3f %.3f\n" % tuple(r["die"]))
        fh.write("CORE %.3f %.3f %.3f %.3f\n" % tuple(r["core"]))
        fh.write("PIN ck %.3f %.3f\n" % r["entry"])
        for n, master, rect, orient, ck in r["macros"]:
            fh.write("MACRO %s %s %.3f %.3f %.3f %.3f CK %.3f %.3f\n" % ((n, master) + tuple(rect) + ck))
        fh.write("ISLCOUNT 0\n")
        for s in r["sinks"]:
            fh.write("SINK %.3f %.3f %s %s %s\n" % s)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    r = f3(read(src))
    write_geo(r, out)
    meta = {k: v for k, v in r.items() if k != "sinks"}
    meta["n_sinks"] = len(r["sinks"])
    Path(out + ".json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta))
