#!/usr/bin/env python3
"""MASTER-PLAN-R4 generalisation of refloor.py F3 to n stacked SRAMs (btab 4 x 128x256, prog 4 x 256x256; COORD
spot-check 10-26: btab/prog variant so QC-SU-LAT-R6 can switch if its model predicts TT > 270).
Same rule: every SRAM rotated to a column (pin ends N = L side, S = R side), n/2 columns W and n/2 E of a 21.6-um centre
gap holding the entry at the die centre, S strip = S-face pin regs + R-end flops, N strip = L-end flops, the side face
(W or E, as in the kit) keeps its pins in the top 54 um next to the N strip.  Faces unchanged.  PLAN sink model."""
import json, sys
from pathlib import Path
from refloor import read, spread, write_geo, L

def f3n(g, gap=21.6, side=11.52, s_strip=34.56, n_strip=30.24, halo=2.2, col_sp=4.32):
    m = sorted(g["macros"], key=lambda t: t[2][1])
    n = len(m)
    SWm, SHm = m[0][2][2] - m[0][2][0], m[0][2][3] - m[0][2][1]
    x0, x1 = m[0][2][0], m[0][2][2]
    core0 = g["core"]
    face = "E" if any(s[0] > core0[2] - 25 for s in g["sinks"]) and not any(s[0] < 25 for s in g["sinks"]) else "W"
    grp = {"F": [], "S": []}
    for k in range(n):
        grp[f"L{k}"], grp[f"R{k}"] = [], []
    for s in g["sinks"]:
        x, y = s[0], s[1]
        k = min(range(n), key=lambda i: abs(y - (m[i][2][1] + m[i][2][3]) / 2))
        if (face == "W" and x < 25) or (face == "E" and x > core0[2] - 25):
            grp["F"].append(s)
        elif x < x0 and y > m[0][2][1] - 15:
            grp[f"L{k}"].append(s)
        elif x > x1 and y > m[0][2][1] - 15:
            grp[f"R{k}"].append(s)
        else:
            grp["S"].append(s)
    h = n // 2
    width = 2 * L + 2 * side + gap + n * SHm + (n - 2) * col_sp
    height = 2 * L + s_strip + SWm + n_strip
    W = round(-(-width // L) * L, 3); H = round(-(-height // L) * L, 3)
    cx, cy = round(round(W / 2 / L * 2) * L / 2, 3), round(H / 2, 3)
    ys0, ys1 = L + s_strip, L + s_strip + SWm
    cols = [cx - gap / 2 - (h - i) * SHm - (h - 1 - i) * col_sp for i in range(h)] + \
           [cx + gap / 2 + i * (SHm + col_sp) for i in range(h)]
    macros, sinks = [], []
    core = [L, L, W - L, H - L]
    for k, (name, master, r) in enumerate(m):
        c0 = cols[k]
        rect = [c0, ys0, c0 + SHm, ys1]
        seg = (c0 + 0.77, c0 + min(SHm, 40.5)) if k >= h else (c0 + SHm - min(SHm, 40.5), c0 + SHm - 0.77)
        ck = (round(seg[0] if k >= h else seg[1], 3), round(ys1, 3))
        macros.append((name, master, rect, "R270" if k >= h else "MY_R270", ck))
        sinks += spread(grp[f"L{k}"], lambda s: s[1], [seg[0], ys1 + halo, seg[1], ys1 + halo + min(n_strip - 2 * halo, 16.2)])
        sinks += spread(grp[f"R{k}"], lambda s: s[1], [seg[0], ys0 - halo - 10.8, seg[1], ys0 - halo])
    sinks += spread(grp["S"], lambda s: (s[0], s[1]), [core[0] + 1.0, core[1] + 0.5, core[2] - 1.0, ys0 - halo - 11.3])
    wy1 = core[3] - 1.0
    fx = [core[0] + 0.5, core[0] + side - halo - 0.5] if face == "W" else [core[2] - side + halo + 0.5, core[2] - 0.5]
    sinks += spread(grp["F"], lambda s: s[1], [fx[0], wy1 - 54.0, fx[1], wy1])
    return dict(die=[0, 0, W, H], core=core, entry=(cx, cy), macros=macros, sinks=sinks, side_face=face,
                groups={k: len(v) for k, v in grp.items()}, gap=[cx - gap / 2, cx + gap / 2])

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    r = f3n(read(src)); write_geo(r, out)
    meta = {k: v for k, v in r.items() if k != "sinks"}; meta["n_sinks"] = len(r["sinks"])
    Path(out + ".json").write_text(json.dumps(meta, indent=1) + "\n"); print(json.dumps(meta)[:600])
