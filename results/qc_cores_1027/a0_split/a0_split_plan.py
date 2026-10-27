#!/usr/bin/env python3
"""QC-CORES-1 (10-27): A0 NK/NL core = parent + hardened-once sub-cores; centre clock entry + in-core islands (12.2a1/12.3/12.8a,b).
Input: Codex parent floorplan (codex/qc-a0-2157@b7da9afaa results/qc_a0_2157/rawfault_cut/parent_floorplan.json), unchanged child placements.
Output: a0_split_plan.json + a0_split_plan_{nk,nl}.png. Planning only: no P&R, no latency claim (numbers here are geometry)."""
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
H = os.path.dirname(os.path.abspath(__file__))
fp = json.load(open(os.path.join(H, "input_parent_floorplan_codex_b7da9afaa.json")))
# child clock pins in child frame (from views / kit pins): romleaf LEF clk W edge (0,21.756); node LEF clk E edge (47.52,204.012);
# rawleaf kit pins.json clk E face (115.248,62.988).  All are EDGE pins -> 12.8a requires centre entry on re-kit (see plan).
PIN = {"ot_qwen_tile_romleaf": (0.0, 21.756), "ot_qwen_tile_node": (47.52, 204.012), "rawleaf": (115.248, 62.988)}
def kind(v): return "rawleaf" if v.startswith("PENDING") else v.split("/")[-1]
def place_pin(c):
    k = kind(c["view"]); px, py = PIN[k]; w, h = c["size_um"]; x, y = c["at"]
    if c["orient"] == "MY": px = w - px
    return (x + px, y + py)
W, Hh = fp["nk"]["outline_um"]; cx, cy = W / 2, Hh / 2
# Balanced 3-level in-core tree from the geometric-centre entry (all legs equal per level):
D1, D2 = 245.0, 130.0
E0 = (cx, cy)
L1 = {"S": (cx, cy - D1), "N": (cx, cy + D1)}
L2 = {"S0": (cx, cy - D1 - D2), "S1": (cx, cy - D1 + D2), "N0": (cx - D2, cy + D1), "N1": (cx + D2, cy + D1)}
PARENT = {"S0": "S", "S1": "S", "N0": "N", "N1": "N"}
def inside(p, c, halo=0.0):
    x, y = c["at"]; w, h = c["size_um"]
    return x - halo <= p[0] <= x + w + halo and y - halo <= p[1] <= y + h + halo
out = {"schema": "qc_cores_1027.a0_split.v1", "source": "codex/qc-a0-2157@b7da9afaa parent_floorplan.json (children unchanged)",
       "outline_um": [W, Hh], "entry": {"xy": E0, "rule": "12.8a geometric centre, M9->M5 stack, one entry (replaces 42/41 external taps)"},
       "tree": {"D1_um": D1, "D2_um": D2, "L1": L1, "L2": L2}, "cores": {}}
for core in ("nk", "nl"):
    ch = fp[core]["hard_children"]
    rec = {"children": [], "island_violations": [], "leaf_load": {k: [] for k in L2}}
    for c in ch:
        p = place_pin(c); k = kind(c["view"])
        best = min(L2, key=lambda n: abs(L2[n][0] - p[0]) + abs(L2[n][1] - p[1]))
        leg = abs(L2[best][0] - p[0]) + abs(L2[best][1] - p[1])
        rec["children"].append({"type": k, "inst": c["inst"], "clk_pin": [round(p[0], 3), round(p[1], 3)], "leaf_island": best, "leg_um": round(leg, 2),
                                "entry_to_pin_um": round(D1 + D2 + leg, 2)})
        rec["leaf_load"][best].append(k)
    for n, p in list(L1.items()) + list(L2.items()) + [("E0", E0)]:
        for c in ch:
            if inside(p, c, 5.4): rec["island_violations"].append([n, c["inst"]])
    rec["max_entry_to_child_pin_um"] = max(x["entry_to_pin_um"] for x in rec["children"])
    out["cores"][core] = rec
    # render
    fig, ax = plt.subplots(figsize=(6.2, 14))
    ax.add_patch(Rectangle((0, 0), W, Hh, fill=False, lw=2, ec="k"))
    corr = (200.664, 16.776, 257.256 - 200.664, 658.44 - 16.776)
    ax.add_patch(Rectangle(corr[:2], corr[2], corr[3], fc="#fff3c4", ec="#d9b300", lw=0.8, ls="--"))
    ax.text(229, 30, "bus corridor\n(Codex budget)", ha="center", fontsize=6, color="#8a7000")
    col = {"ot_qwen_tile_romleaf": "#9ecae1", "rawleaf": "#a1d99b", "ot_qwen_tile_node": "#fdae6b"}
    lab = {"ot_qwen_tile_romleaf": "ROM leaf", "rawleaf": "LSL rawleaf", "ot_qwen_tile_node": "node"}
    for c in ch:
        k = kind(c["view"]); x, y = c["at"]; w, h = c["size_um"]
        ax.add_patch(Rectangle((x, y), w, h, fc=col[k], ec="#333", lw=0.8))
        ax.text(x + w / 2, y + h / 2, f"{lab[k]}\n{c['orient']}", ha="center", va="center", fontsize=6)
    seg = [(E0, L1["S"]), (E0, L1["N"])] + [(L1[PARENT[n]], L2[n]) for n in L2]
    for a, b in seg: ax.plot([a[0], b[0]], [a[1], b[1]], color="#c00", lw=2.2)
    for x in rec["children"]:
        a = L2[x["leaf_island"]]; b = x["clk_pin"]
        ax.plot([a[0], a[0], b[0]], [a[1], b[1], b[1]], color="#c00", lw=0.7, ls=":")
        ax.plot(*b, marker="s", ms=3, color="#600")
    ax.plot(*E0, marker="*", ms=16, color="#c00", mec="k"); ax.text(E0[0] + 6, E0[1], "E0 centre entry\nM9->M5 island", fontsize=7)
    for n, p in L1.items(): ax.plot(*p, marker="D", ms=8, color="#c00", mec="k"); ax.text(p[0] + 6, p[1] + 4, f"L1 {n}", fontsize=7)
    for n, p in L2.items(): ax.plot(*p, marker="o", ms=8, color="#f60", mec="k"); ax.text(p[0] + 6, p[1] - 12, f"L2 {n}", fontsize=7)
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, Hh + 10); ax.set_aspect("equal")
    ax.set_title(f"qfd_tile_{core}_a0c split plan (QC-CORES-1 10-27)\n{W}x{Hh} um, {len(ch)} hard sub-cores; "
                 f"tree D1={D1} D2={D2} um; max E0->child pin {rec['max_entry_to_child_pin_um']} um\n"
                 f"island-in-child-halo violations: {len(rec['island_violations'])}  (square = child clk pin, EDGE pins today)", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(H, f"a0_split_plan_{core}.png"), dpi=110); plt.close(fig)
json.dump(out, open(os.path.join(H, "a0_split_plan.json"), "w"), indent=1)
for core, r in out["cores"].items():
    print(core, "children", len(r["children"]), "viol", r["island_violations"], "max_entry_to_pin", r["max_entry_to_child_pin_um"],
          {k: len(v) for k, v in r["leaf_load"].items()})
