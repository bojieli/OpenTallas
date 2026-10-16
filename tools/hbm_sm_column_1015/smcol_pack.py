#!/usr/bin/env python3
"""H-SM 2026-10-15 (OWNER 22:30 v8 SM column trial): pack one SM (or an SM pair) into a column over its PC box(es).

Unit = one leaf-half of an SM tile (32 per SM): xs on top; below it the tcl pair over tct (tcl sum_o S -> tct sum_i N)
beside bdc.  Rows of leaf-halves either side of an N-S transport/BE spine (x-write beat 2,069 b + rows: 3,705 crossing
bits per tile, ~200 um of M5/M7 at cut 0.56; transport stations live in the spine; the 8 BE 319.68 x 77.76 join the front band).
Static front (fc_xl, fc_t x2, fc_xr x2, fc_b x2 + ~50k um2 cells ~ 0.43 mm2) is a band on the S face over the PC box.
Leaf sizes: 'closed' = today's closed views; 'd62' = density re-harden kits (xs is pin/macro bound: S face 2,900 pins
need its 302.4 um, so xs stays 302.4 x 155.544).  Planning geometry only -- no route.
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

G = 21.6
LEAF = {"closed": {"xs": (302.4, 155.544), "tcl": (86.4, 120.024), "tct": (194.4, 69.144), "bdc": (112.32, 142.56)},
        "d62": {"xs": (302.4, 155.544), "tcl": (86.4, 108.0), "tct": (194.4, 56.16), "bdc": (112.32, 116.64)}}
FRONT_MM2 = 0.43
BE_MM2 = 8 * 319.68 * 77.76 / 1e6
CONTENT_MM2 = 2.21


def half(L):
    tw = max(2 * L["tcl"][0] + G, L["tct"][0])
    th = L["tcl"][1] + G + L["tct"][1]
    w = max(L["xs"][0], tw + G + L["bdc"][0])
    h = L["xs"][1] + G + max(th, L["bdc"][1])
    kids = [("xs", 0, h - L["xs"][1], *L["xs"]), ("tct", 0, 0, *L["tct"]), ("tcl", 0, L["tct"][1] + G, *L["tcl"]),
            ("tcl", L["tcl"][0] + G, L["tct"][1] + G, *L["tcl"]), ("bdc", tw + G, 0, *L["bdc"])]
    return round(w, 3), round(h, 3), kids


def plan(width, n_sm, leaves, spine=345.6):
    w, h, kids = half(LEAF[leaves])
    per_row = int((width - spine - G) // (w + G))
    halves = 32 * n_sm
    rows = -(-halves // per_row)
    front_h = round((FRONT_MM2 + BE_MM2) * n_sm * 1e6 / width / 0.85, 1)   # front + 8 BE band on the S face
    H = round(front_h + G + rows * (h + G), 1)
    return dict(width_um=width, sms=n_sm, leaves=leaves, half_um=[w, h], halves_per_row=per_row, rows=rows,
                spine_um=spine, front_band_um=front_h, height_um=H, area_per_sm_mm2=round(width * H / 1e6 / n_sm, 3),
                sm32_mm2=round(32 * width * H / 1e6 / n_sm, 1), content_fill=round(CONTENT_MM2 * n_sm / (width * H / 1e6), 3),
                leaf_outline_fill=round(halves * sum(a * b for k, x, y, a, b in kids) / (width * H), 3)), kids


def draw(p, kids, out):
    W, H = p["width_um"], p["height_um"]
    fig, ax = plt.subplots(figsize=(4, 4 * H / W if H / W < 4 else 16))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    ax.add_patch(Rectangle((0, 0), W, p["front_band_um"], color="#c9a0dc", alpha=.6)); ax.text(10, 10, "static front (S, over PC box)", fontsize=6)
    hw, hh = p["half_um"]; per = p["halves_per_row"]; sx = per // 2 * (hw + G)
    ax.add_patch(Rectangle((sx, p["front_band_um"] + G), p["spine_um"], H - p["front_band_um"] - G, color="#f6e7b0"))
    ax.text(sx + 5, H - 60, "spine: transport + BE", fontsize=5, rotation=90)
    col = {"xs": "#6a8fb5", "tcl": "#8cc1b8", "tct": "#74b06a", "bdc": "#f0a050"}
    n = 0
    for r in range(p["rows"]):
        y0 = p["front_band_um"] + G + r * (hh + G)
        for c in range(per):
            if n >= 32 * p["sms"]: break
            x0 = c * (hw + G) + (p["spine_um"] + G if c >= per // 2 else 0)
            for k, x, y, a, b in kids:
                ax.add_patch(Rectangle((x0 + x, y0 + y), a, b, color=col[k], ec="k", lw=.2))
            n += 1
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
    ax.set_title(f"{p['sms']} SM column {W} x {H} um, {p['leaves']} leaves, fill {p['content_fill']}", fontsize=7)
    ax.text(10, H - 30, "N: SM_X / SM_OUT / KV_DESC (band)", fontsize=6)
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "results/arch/hbm_sm_column_1015"); out.mkdir(parents=True, exist_ok=True)
    rec = []
    for width, n, spine in ((1036.8, 1, 216.0), (2073.6, 2, 216.0)):
        for lv in ("closed", "d62"):
            p, kids = plan(width, n, lv, spine)
            rec.append(p)
            draw(p, kids, out / f"smcol_{int(width)}_{lv}.png")
            print(json.dumps(p))
    (out / "smcol_pack.json").write_text(json.dumps({"schema": "opentallas.hbm.sm_column_pack.v1", "agent": "Claude H-SM",
                                                     "date": "2026-10-15", "plans": rec}, indent=1) + "\n")


if __name__ == "__main__":
    main()
