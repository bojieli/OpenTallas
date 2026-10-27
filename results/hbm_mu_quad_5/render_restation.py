#!/usr/bin/env python3
"""HBM-MU-QUAD-5 restation before/after zooms. Usage: render_rst.py BEFORE_PLAN AFTER_PLAN REPORT OUTDIR"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B = json.load(open(sys.argv[1]))["partition_types"]; A = json.load(open(sys.argv[2]))["partition_types"]
rep = json.load(open(sys.argv[3])); out = Path(sys.argv[4])
views = [("q_su11", "B1", None, (900, 450, 1350, 900)), ("q_hub_nw", "B1", "bus:L28_o", None),
         ("root", "B1", "bus:L74m_i", None), ("q_b000", "B2", None, None), ("q_su31", "B2", "L35x1", None)]
def chains(t, kind, conn):
    if kind == "B1":
        return [(e.get("conn"), [e.get("from_um")] + e["regs_um"] + [e.get("to_um")]) for e in t.get("internal_stations", []) if e.get("regs_um")]
    return [(s["name"], s["regs_um"]) for s in t.get("ft_slots", []) if s.get("regs_um")]
for tn, kind, conn, win in views:
    moved = {(r["conn"]) for r in rep["rows"] if r["type"] == tn and r["kind"] == kind}
    if conn: moved &= {conn}
    fig, axs = plt.subplots(1, 2, figsize=(16, 8))
    for ax, T, ttl, col in ((axs[0], B, "planU4f (before)", "red"), (axs[1], A, "restation (after)", "green")):
        t = T[tn]; W, H = t["outline_um"]
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1))
        for c in t.get("hard_cores", []):
            x, y = c["origin_um"]; w, h = c["outline_um"]; dx, dy = c.get("track_offset_um", [0, 0])
            ax.add_patch(Rectangle((x + dx, y + dy), w, h, fc="#bbbbbb", ec="#555555", lw=0.5))
            ax.text(x + dx + w / 2, y + dy + h / 2, c["inst"], fontsize=5, ha="center", va="center")
        xs_all = []; ys_all = []
        for nm, pts in chains(t, kind, conn):
            if nm not in moved: continue
            pts = [p for p in pts if p]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=col, lw=0.8, alpha=0.7)
            regs = pts[1:-1] if kind == "B1" else pts
            ax.plot([p[0] for p in regs], [p[1] for p in regs], "o", color=col, ms=3)
            xs_all += [p[0] for p in pts]; ys_all += [p[1] for p in pts]
        if win: ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3])
        elif xs_all:
            m = 150; ax.set_xlim(max(-10, min(xs_all) - m), min(W + 10, max(xs_all) + m)); ax.set_ylim(max(-10, min(ys_all) - m), min(H + 10, max(ys_all) + m))
        ax.set_aspect("equal"); ax.set_title(f"{tn} {kind} {conn or 'all moved'} - {ttl} ({len(moved)} chains)", fontsize=9)
    fig.tight_layout(); p = out / f"restation_{tn}_{kind}.png"; fig.savefig(p, dpi=110); plt.close(fig); print(p)
