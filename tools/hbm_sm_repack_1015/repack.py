#!/usr/bin/env python3
"""H-SM-REPACK 2026-10-15: SM frame re-pack analysis + renders.
usage: repack.py COMPLETE35.json COMPLETE16.json OUTDIR
COMPLETE35/16 = the compact660_v5 SM frame / tile geometry (codex/sm-dense-pack-1015 62f2a4a7b, read-only input).
Writes OUTDIR/repack.json and PNGs (v5 frame, v5 tile, rp1 tile, rp1 frame)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom as T

CONTENT_PER_SM_MM2 = 2.21          # TILE-FILL 354b5bb2e: macro + std-cell content of one SM (closed views)
COL = {"xs": "#4e79a7", "bdc": "#f28e2b", "tct": "#59a14f", "tcl": "#76b7b2", "beat": "#e15759", "tile": "#bab0ac",
       "be": "#9c755f", "front": "#b07aa1", "soft": "#edc948", "row": "#ff9da7", "land": "#ff9da7"}


def kind_of(cell):
    for k in ("xs", "bdc", "tct", "tcl", "beat", "be", "land", "row"):
        if f"_{k}" in cell:
            return k
    if "tile" in cell:
        return "tile"
    return "front"


def draw(path, w, h, boxes, title, notes=(), bands=()):
    s = 9.0 / max(w, h)
    fig, ax = plt.subplots(figsize=(max(3.0, w * s) + 1.5, max(3.0, h * s) + 1.0), dpi=110)
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5, ec="k"))
    for (x0, y0, x1, y1, c, lab) in bands:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=c, ec="none", alpha=0.25))
        ax.text(x0 + 3, y0 + 3, lab, fontsize=6)
    for b in boxes:
        k, name, x, y, bw, bh = b[:6]
        ax.add_patch(Rectangle((x, y), bw, bh, fc=COL.get(k, "#cccccc"), ec="k", lw=0.4, alpha=0.85))
        if bw * s > 0.25:
            ax.text(x + bw / 2, y + bh / 2, name, fontsize=5, ha="center", va="center")
    for (x, y, t) in notes:
        ax.text(x, y, t, fontsize=6, color="darkred")
    ax.set_xlim(-0.02 * w, 1.02 * w); ax.set_ylim(-0.02 * h, 1.02 * h); ax.set_aspect("equal")
    ax.set_title(title, fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def stats(w, h, boxes):
    hard = sum(b[4] * b[5] for b in boxes)
    g = T.gaps([(b[0], b[1], b[2], b[3], b[4], b[5]) for b in boxes])
    sl = sorted({x[0] for x in g if 0 < x[0] < 20})
    return {"outline_um": [round(w, 3), round(h, 3)], "area_mm2": round(w * h / 1e6, 4),
            "child_outline_mm2": round(hard / 1e6, 4), "child_coverage": round(hard / (w * h), 3),
            "overlaps": sum(1 for x in g if x[0] < 0), "slivers_um": sl[:10],
            "min_gap_um": min((x[0] for x in g if x[0] >= 0), default=None)}


def front_block():
    """static SM front (ot_smh_static_front, main): the closed fc children it instantiates + its tile-parent cells.
    LEF outlines from complete35 (closed views); the feed / bundle registers are soft (budget 50k um2 at 0.5 util)."""
    kids = [("front", "fc_xl", 302.4, 298.08), ("front", "fc_tw", 218.16, 216.0), ("front", "fc_te", 218.16, 216.0),
            ("front", "fc_rw", 218.16, 151.2), ("front", "fc_re", 218.16, 151.2), ("front", "fc_bw", 218.16, 302.4),
            ("front", "fc_be", 218.16, 302.4)]
    return kids, 50000.0


def frame_rp1():
    """rp1 frame: 8 columns (W 4 = tile MY, E 4 = tile R0) of 2 tiles + BE, the static front column in the middle.
    Column pitch = tile + 21.6 (die / relay channel); tiles of a column 21.6 apart (gout -> gin straight seam)."""
    tw, th = T.W, T.H
    gap = 21.6
    be_w, be_h = 319.68, 77.76
    kids, soft = front_block()
    fw = 345.6                                      # front column: widest child 302.4 + 2 x 21.6
    colh = be_h + gap + th + gap + th
    boxes = []
    x = 0.0
    for c in range(8):
        if c == 4:
            fx = x
            y = 0.0
            for k, n, w, h in kids:                 # stacked, 21.6 apart, centred
                boxes.append((k, n, round(fx + (fw - w) / 2, 3), round(y, 3), w, h))
                y += h + gap
            soft_h = soft / 0.5 / fw * 0 + soft / (fw * 0.5)
            boxes.append(("soft", "front cells (feed, bundle regs)", fx, round(y, 3), fw, round(min(soft_h, colh - y), 3)))
            x += fw + gap
        side = "wg" if c < 4 else "eg"
        boxes.append(("be", f"be_{side}{c}", round(x + (tw - be_w) / 2, 3), 0.0, be_w, be_h))
        boxes.append(("tile", f"tile{c}p1 ({'MY' if c < 4 else 'R0'})", round(x, 3), round(be_h + gap, 3), tw, th))
        boxes.append(("tile", f"tile{c}p0", round(x, 3), round(be_h + 2 * gap + th, 3), tw, th))
        x += tw + gap
    return round(x - gap, 3), round(colh, 3), boxes


def main():
    c35 = json.loads(Path(sys.argv[1]).read_text())
    c16 = json.loads(Path(sys.argv[2]).read_text())
    out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    rec = {"schema": "opentallas.hbm.sm_repack.v1", "agent": "Claude H-SM-REPACK", "date": "2026-10-15",
           "content_per_sm_mm2": CONTENT_PER_SM_MM2, "inputs": {"v5_frame": "codex/sm-dense-pack-1015 complete35.json",
           "v5_tile": "codex/sm-dense-pack-1015 complete16.json"}}
    # current v5 frame / tile
    fw, fh = c35["frame_outline_um"]
    b35 = [(kind_of(c["cell"]), c["cell"].replace("ot_hbm_accel_smh_", ""), c["x"], c["y"], *c["outline_um"]) for c in c35["children"]]
    rec["v5_frame"] = stats(fw, fh, b35)
    draw(out / "v5_frame.png", fw, fh, b35, f"v5 SM frame {fw} x {fh} (compact660_v5 slot, 35 children)")
    b16 = [(c["kind"].replace("_w", "").replace("_e", "") if c["kind"].startswith(("row", "beat")) else c["kind"],
            c["name"], c["x"], c["y"], c["w"], c["h"]) for c in c16["children"]]
    rec["v5_tile"] = stats(c16["width_um"], c16["height_um"], b16)
    rec["v5_tile"]["note"] = ("UNBUILT: 6 new transport masters (rowW/beatW/beatE/rowE0/rowE1) + the 3,705-bit E-W bus "
                              "on M8 over the leaves; the cluster contract caps signals at M7 unless H-DIE issues a "
                              "cluster_layer_grant (die M8/M9 then PG-only over every tile)")
    draw(out / "v5_tile.png", c16["width_um"], c16["height_um"], b16, "v5 tile 693.44 x 609.92 (needs M8 + 6 new masters)")
    # rp1 tile
    tb = [(k, inst.split(".")[-1].replace("*g_lf?", "L").replace("?", ""), x, y, w, h)
          for k, inst, x, y, w, h, o in T.children()]
    tb = [(k, (("L0 " if y > T.Y_CH0 else "L1 ") + n) if k != "beat" else n, x, y, w, h) for k, n, x, y, w, h in tb]
    rec["rp1_tile"] = stats(T.W, T.H, tb)
    rec["rp1_tile"].update({"channel_um": [T.Y_CH0, T.Y_XS0], "transport": "beat_e x2 hard (W transit + E beat), rows / "
                            "landings / pin registers = tile cells", "parent_sinks_est": 22862 - 2 * 2 * 2069})
    bands = [(0, T.Y_CH0, T.W, T.Y_XS0, "#edc948", "transport channel: pin regs, row_w/row_e + N/S landing cells"),
             (0, T.Y_CH0 + 8, 6, T.Y_XS0 - 8, "#e15759", "")]
    notes = [(2, T.Y_XS0 - 20, "rin/bin W (M4+M6)"), (T.W - 90, T.Y_XS0 - 20, "rout/bout E"),
             (T.W / 2 - 40, T.H - 12, "gin, straps, clk N"), (T.W / 2 - 30, 4, "gout S")]
    draw(out / "rp1_tile.png", T.W, T.H, tb, f"rp1 tile {T.W} x {T.H} (12 closed children)", notes, bands)
    # rp1 frame
    w, h, fb = frame_rp1()
    rec["rp1_frame"] = stats(w, h, fb)
    for k in ("v5_frame", "rp1_frame"):
        a = rec[k]["area_mm2"]
        rec[k]["sm32_mm2"] = round(32 * a, 1)
        rec[k]["fill_content"] = round(CONTENT_PER_SM_MM2 / a, 3)
    rec["rp1_frame"]["saving_32sm_mm2"] = round(rec["v5_frame"]["sm32_mm2"] - rec["rp1_frame"]["sm32_mm2"], 1)
    draw(out / "rp1_frame.png", w, h, fb, f"rp1 SM frame {w} x {h}")
    (out / "repack.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
