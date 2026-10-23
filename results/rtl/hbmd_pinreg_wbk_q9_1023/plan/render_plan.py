#!/usr/bin/env python3
"""floorplan-only render of a q9 spec: outline, SRAM macros + halos (read side marked), std bands, pin segments per face"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
spec, out = sys.argv[1], sys.argv[2]
s = json.load(open(spec)); W, H = s["outline"]["w"], s["outline"]["h"]
MW, MH = 94.824, 41.04
fig, ax = plt.subplots(figsize=(10, 10 * H / W + 0.6))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
xs, ys = [], []
for m in s["macros"]:
    x, y = m["at"]; xs += [x, x + MW]; ys += [y, y + MH]
    ax.add_patch(Rectangle((x - 10.8, y - 5.4), MW + 21.6, MH + 10.8, color="#f3d9a4", lw=0))
for m in s["macros"]:
    x, y = m["at"]
    ax.add_patch(Rectangle((x, y), MW, MH, fc="#c98a2b", ec="k", lw=0.4))
    rx = x + MW - 3 if m["orient"] in ("MY", "R180") else x
    ax.add_patch(Rectangle((rx, y + 1.6), 3, 24.5, color="#1f5fbf", lw=0))   # rd_out pins edge
    ax.text(x + MW / 2, y + MH / 2, m["inst"].split("?")[1], ha="center", va="center", fontsize=6)
x1, y1, y0 = max(xs) + 10.8, max(ys) + 5.4, min(ys) - 5.4
ax.add_patch(Rectangle((0, y1), W, H - y1, color="#bfe3c0", alpha=0.5, lw=0))
ax.add_patch(Rectangle((x1, 0), W - x1, y1, color="#bfe3c0", alpha=0.5, lw=0))
ax.add_patch(Rectangle((0, 0), W, y0, color="#d6e4f5", alpha=0.6, lw=0))
ax.text(W / 2, (y1 + H) / 2, f"N K band {H - y1:.1f} um (PC0-7 heads/rings/FIFOs)", ha="center", fontsize=9)
ax.text((x1 + W) / 2, y1 / 2, f"E K band\n{W - x1:.1f} um\n(PC8-15)", ha="center", fontsize=9)
ax.text(W / 2, y0 / 2, f"S wd landing band {y0:.1f} um", ha="center", va="center", fontsize=8)
cols = plt.cm.tab20.colors
for i, g in enumerate(s.get("pin_bit_groups", [])):
    lo, hi = g["range"]; pc = g["bits"]["w_k_v"][0]; c = cols[pc % 20]
    if g["face"] == "N":
        ax.add_patch(Rectangle((lo, H - 6), hi - lo, 6, color=c)); ax.text((lo + hi) / 2, H + 4, f"PC{pc}", ha="center", fontsize=7)
    else:
        ax.add_patch(Rectangle((W - 6, lo), 6, hi - lo, color=c)); ax.text(W + 4, (lo + hi) / 2, f"PC{pc}", va="center", fontsize=7)
for n, (lo, hi) in (s.get("pin_ranges") or {}).items():
    ax.add_patch(Rectangle((lo, H - 10), hi - lo, 10, color="red")); ax.text(lo, H - 18, n, fontsize=6, color="red")
ax.add_patch(Rectangle((0, 0), W, 4, color="#1f5fbf")); ax.text(4, 6, "S: stream ctl + wd[2311:0] (2,452 pins)", fontsize=7)
npin = sum(sum(b[1] - b[0] + 1 for b in g["bits"].values()) for g in s.get("pin_bit_groups", []) if g["face"] == "N")
epin = sum(sum(b[1] - b[0] + 1 for b in g["bits"].values()) for g in s.get("pin_bit_groups", []) if g["face"] == "E")
sram = len(s["macros"]) * (MW + 21.6) * (MH + 10.8)
ax.set_title(f"{s['name']} PLAN {W} x {H} ({W*H/1e3:.0f}k um2): N {npin} pins {npin/W:.2f}/um, E {epin} pins {epin/H:.2f}/um, "
             f"S 2452 {2452/W:.2f}/um\nSRAM+halo {sram/1e3:.0f}k, free {(W*H-sram)/1e3:.0f}k um2 -> std 229.5k (nd placed) = "
             f"{229.5e3/(W*H-sram):.0%}; blue = SRAM read side (rd_out)", fontsize=9)
ax.set_xlim(-10, W + 40); ax.set_ylim(-10, H + 20); ax.set_aspect("equal")
fig.savefig(out, dpi=130, bbox_inches="tight"); print(out)
st = {"element": s["top"], "kit": s["name"], "kind": "PLAN (floorplan-only, from spec.json; no placement yet)",
      "outline_um": [W, H], "area_um2": round(W * H), "macros": len(s["macros"]), "macro_halo_area_um2": round(sram),
      "free_um2": round(W * H - sram), "std_nd_placed_um2": 229460, "std_nd_synth_um2": 106600,
      "std_fill_of_free_est_pct": round(100 * 229.5e3 / (W * H - sram), 1),
      "std_fill_of_free_est_synth_only_pct": round(100 * 106.6e3 / (W * H - sram), 1),
      "bands_um": {"N": round(H - y1, 1), "E": round(W - x1, 1), "S": round(y0, 1)},
      "pins_per_face": {"N": npin + 2, "E": epin, "S": 2452, "W": 0},
      "pins_per_um": {"N": round((npin + 2) / W, 2), "E": round(epin / H, 2), "S": round(2452 / W, 2)},
      "unregistered_pins_rtl": {"w_k_rdy": 16, "why": "named exception: K valid/ready handshake ready input"},
      "nd_long_wire_buffers": {"wire_BUFx16f": 186884, "wire_BUFx12f": 107180, "share_of_nd_cells_pct": 23.3,
                               "q10_trigger": "> 15% of cells at 3_4 -> per-PC FIFO + K ring hierarchy (q10)"}}
json.dump(st, open(out.replace(".png", "_stats.json"), "w"), indent=1)
