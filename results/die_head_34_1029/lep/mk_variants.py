#!/usr/bin/env python3
"""DIE-HEAD-34 (2026-10-29): lep_pair 777.6x492.48 variants from the DIE-HEAD-33 V1 inputs (results/die_head_33_1029/lep).
VA: the 1114 S-face K pins (M5 k_lo_*, M7 k_li_*/k_flt/k_rxv), packed in x 2.0..395.4 for the old 388.8 width, are re-spread
    uniformly over x 2.04..775.0 in the same order per layer, snapped to the layer's existing track grid
    (M5 0.024 + 0.048 k, M7 0.032 + 0.064 k).  W coll pins, centre rst_n and the kit clk entry are unchanged.
VB: VA pins + the 36 u_ep fifo/rb 256x64 SRAMs spread in x per row: x' = x + 4.32*round((x - 155.52)*(F-1)/4.32), F maps
    the row span 155.52..410.4 onto 155.52..700 (rows, orient, the 4.32 lattice residual kept); the 19 32x64 SRAMs unchanged.
    usage: mk_variants.py SRCDIR OUTDIR
"""
import json, sys, copy
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
pins = json.loads((src / "lep_pair_pins_777.json").read_text())
child = json.loads((src / "lep_pair_child_v5.json").read_text())
GRID = {"M5": (0.024, 0.048), "M7": (0.032, 0.064)}
X0, X1 = 2.04, 775.0
rep = {"pins": {}}
pv = copy.deepcopy(pins)
for L, (o, g) in GRID.items():
    S = sorted([p for p in pv["pins"] if p["y"] < 1 and p["layer"] == L], key=lambda p: p["x"])
    n = len(S); used = set()
    for i, p in enumerate(S):
        x = X0 + (X1 - X0) * i / (n - 1)
        k = round((x - o) / g)
        while k in used: k += 1
        used.add(k); p["x"] = round(o + g * k, 4)
    xs = [p["x"] for p in S]
    rep["pins"][L] = {"n": n, "x_min": xs[0], "x_max": xs[-1], "pitch_min": round(min(b - a for a, b in zip(xs, xs[1:])), 4),
                      "tracks_used_pct": round(100.0 * n * g / (X1 - X0), 2)}
pv["faces"]["S"] = "K-side in M5 / out M7, full S face x2.04..775 (DIE-HEAD-34 VA re-spread)"
pv["source"] += "; DIE-HEAD-34 mk_variants.py VA: S-face K pins re-spread over the full 777.6 width"
(out / "lep_pair_pins_777_va.json").write_text(json.dumps(pv, indent=1) + "\n")

W256, H256, HALO = 34.584, 41.352, 4.32
CORE_X1 = 773.28
CLK = (388.92, 246.24)
F = (700.0 - 155.52) / (410.4 - 155.52)
cb = copy.deepcopy(child); moved = []
for c in cb["child_type"]["contents"]:
    if c.get("kind") != "sram" or ".u_ep." not in c["inst"]: continue
    x, y = c["origin_um"]
    nx = round(x + 4.32 * round((x - 155.52) * (F - 1) / 4.32), 4)
    # keep the plan clk/rst entry (388.92, 246.24) off macro+halo (clock_on_macro): step left on the 4.32 lattice
    while nx - HALO <= CLK[0] <= nx + W256 + HALO and y - HALO <= CLK[1] <= y + H256 + HALO:
        nx = round(nx - 4.32, 4)
    c["origin_um"] = [nx, y]; moved.append((c["inst"], x, nx, y))
# legality: in core with halo, no overlap (incl. halos) between any two SRAMs, clk/rst entry not on a macro+halo
def box(c):
    w, h = (W256, H256) if "256x64" in c["module"] else (31.992, 17.304)
    x, y = c["origin_um"]; return (x, y, x + w, y + h)
S = [c for c in cb["child_type"]["contents"] if c.get("kind") == "sram"]
bad = []
for i, a in enumerate(S):
    ax0, ay0, ax1, ay1 = box(a)
    if ax0 - HALO < 4.32 - 1e-6 or ax1 + HALO > CORE_X1 + 1e-6: bad.append(("core", a["inst"]))
    for b in S[i + 1:]:
        bx0, by0, bx1, by1 = box(b)
        if ax0 < bx1 + HALO and bx0 < ax1 + HALO and ay0 < by1 + HALO and by0 < ay1 + HALO: bad.append(("overlap", a["inst"], b["inst"]))
    if ax0 - HALO <= CLK[0] <= ax1 + HALO and ay0 - HALO <= CLK[1] <= ay1 + HALO: bad.append(("clk_on_macro", a["inst"]))
rep["vb"] = {"F": round(F, 4), "moved": len(moved), "x_max_after": max(m[2] for m in moved) + W256,
             "illegal": bad, "rows": sorted({m[3] for m in moved})}
(out / "lep_pair_child_v5_vb.json").write_text(json.dumps(cb, indent=1) + "\n")
(out / "variants_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep, indent=1)); sys.exit(1 if bad else 0)
