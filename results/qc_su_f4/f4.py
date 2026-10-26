#!/usr/bin/env python3
"""QC-SU-F4 re-floorplans for vmr / rp1 (COORD 13:25 ruling 3: no SRAM rotation; MIF0 canonical).

F4A = the F3 structure (MASTER-PLAN-R4 refloor.py: two SRAM columns either side of a 21.6-um centre gap, entry island at
the die centre in the gap, N strip = read-end (L) flops, S strip = S-face pin registers + write-end (R) flops, W read face
kept in the top 54 um) built from the NATIVE column view ot_sram_1r1w_1024x256_m1b2_r2c2_ns (96.552 x 140.424, mux 1 x
2 banks, pins = the m2 "split" halves on its TOP (L half) and BOTTOM (R half) edges, M5).  Orientations are legal for
SYMMETRY X Y: west column MY (pins at its east end, beside the gap), east column R0.  No rotation anywhere.
Sinks: the MIF0 placement (synth+place of the current kit floorplan, RTL origin/main, MIF 0) grouped by refloor.group
(W-face, S-face, L/R end of SRAM k) and re-sited into that group's F4A region (refloor.spread, order kept).  PLAN sink
model, not a placement.
usage: f4.py MIF0.geo OUT.geo"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "results/master_plan_r4/qc_su_refloor"))
from refloor import L, group, read, spread, write_geo  # noqa: E402

COL = "ot_sram_1r1w_1024x256_m1b2_r2c2_ns"
CW, CH = 96.552, 140.424            # column view R0 size (physical/asap7_memory_macros_v2_col)
PIN_LO, PIN_HI = 0.768, 40.608      # pin segment along each pin (top/bottom) edge, R0 x
CK_OFF = 0.78


def f4a(g, gap=21.6, side=11.52, s_strip=34.56, n_strip=30.24, halo=4.32):
    # halo = the kit MACRO_ROWS_HALO 4.32 (F3 used the 2.2 wire halo, which put N-band flops and leaf drivers inside the
    # macro row halo, where no std-cell row exists: rp1 F4A G3 FAIL 3 leaf sites at y 183.6 < 179.304 + 4.32)
    m, grp = group(g)
    width = 2 * L + side + CW + gap + CW + side
    height = 2 * L + s_strip + CH + n_strip
    W = round(-(-width // L) * L, 3)
    H = round(-(-height // L) * L, 3)
    cx = round(round(W / 2 / L * 2) * L / 2, 3)
    cy = round(H / 2, 3)
    ys0 = L + s_strip
    ys1 = ys0 + CH
    gx0, gx1 = cx - gap / 2, cx + gap / 2
    mw = [gx0 - CW, ys0, gx0, ys1]          # west column (bank0), MY: pin segments at its EAST end (gap side)
    me = [gx1, ys0, gx1 + CW, ys1]          # east column (bank1), R0: pin segments at its WEST end (gap side)
    segw = (gx0 - PIN_HI, gx0 - PIN_LO)
    sege = (gx1 + PIN_LO, gx1 + PIN_HI)
    macros = [(m[0][0], COL, mw, "MY", (round(gx0 - CK_OFF, 3), round(ys1, 3))),
              (m[1][0], COL, me, "R0", (round(gx1 + CK_OFF, 3), round(ys1, 3)))]
    core = [L, L, W - L, H - L]
    sinks = []
    nb0, nb1 = ys1 + halo, ys1 + halo + min(n_strip - 2 * halo, 16.2)
    sinks += spread(grp["L0"], lambda s: s[1], [segw[0], nb0, segw[1], nb1])
    sinks += spread(grp["L1"], lambda s: s[1], [sege[0], nb0, sege[1], nb1])
    sb1, sb0 = ys0 - halo, ys0 - halo - 10.8
    sinks += spread(grp["R0"], lambda s: s[1], [segw[0], sb0, segw[1], sb1])
    sinks += spread(grp["R1"], lambda s: s[1], [sege[0], sb0, sege[1], sb1])
    sinks += spread(grp["S"], lambda s: (s[0], s[1]), [core[0] + 1.0, core[1] + 0.5, core[2] - 1.0, sb0 - 0.5])
    wy1 = core[3] - 1.0
    sinks += spread(grp["W"], lambda s: s[1], [core[0] + 0.5, wy1 - 54.0, core[0] + side - halo - 0.5, wy1])
    return dict(die=[0, 0, W, H], core=core, entry=(cx, cy), macros=macros, sinks=sinks,
                groups={k: len(v) for k, v in grp.items()}, gap=[gx0, gx1], strips=dict(S=[core[1], ys0], N=[ys1, core[3]]),
                pin_faces=dict(S=[core[0], core[2]], W=[wy1 - 54.0, wy1]), orientations={m[0][0]: "MY", m[1][0]: "R0"})


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    r = f4a(read(src))
    write_geo(r, out)
    meta = {k: v for k, v in r.items() if k != "sinks"}
    meta["n_sinks"] = len(r["sinks"])
    Path(out + ".json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta))
