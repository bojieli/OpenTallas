#!/usr/bin/env python3
"""OUTL zoom render, type frame: before | after panels per crop window.
usage: rgz.py PLAN_BEFORE_DIR PLAN_AFTER_DIR OUTDIR TYPE:NAME:x0,y0,x1,y1 ..."""
import json, sys, re
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

MODS = tuple(__import__("os").environ.get("MODS", "").split(","))


def opt(o, W, H, x, y):
    return {"R0": (x, y), "MY": (W - x, y), "MX": (x, H - y), "R180": (W - x, H - y)}[o]


def load(pd):
    pd = Path(pd)
    return pd, json.loads((pd / "die_plan.json").read_text()), json.loads((pd / "clock_entries.json").read_text())


def panel(ax, pd, d, ce, tn, win, title):
    t = d["partition_types"][tn]; x0, y0, x1, y1 = win
    chg = []
    for h in t["hard_cores"]:
        ox, oy = h["origin_um"]; w, hh = h["outline_um"]
        if ox > x1 or oy > y1 or ox + w < x0 or oy + hh < y0:
            continue
        hot = any(m and m in h["module"] for m in MODS)
        ax.add_patch(Rectangle((ox, oy), w, hh, fc="tomato" if hot else "dimgrey", alpha=0.35 if hot else 0.5,
                               ec="black", lw=0.8, zorder=3))
        ax.text(ox + w / 2, oy + hh / 2, f"{h['inst']}\n{w:g}x{hh:g} {h.get('orient', 'R0')}", fontsize=6,
                ha="center", va="center", zorder=9, clip_on=True)
        if hot:
            chg.append(h)
            pins = json.loads((pd / h["pins_file"]).read_text())
            xs, ys, cs = [], [], []
            for p in pins:
                px, py = opt(h.get("orient", "R0"), w, hh, p["x"], p["y"])
                xs.append(ox + px); ys.append(oy + py); cs.append("blue" if p["layer"] == "M4" else "purple")
            ax.scatter(xs, ys, s=0.4, c=cs, lw=0, zorder=6)
            key = [k for k in ce.get(tn, {}) if k == h["inst"] or h["inst"].startswith(k + "_")]
            if key:
                e = ce[tn][key[0]]; ix0, iy0, ix1, iy1 = e["island_um"]
                a = opt(h.get("orient", "R0"), w, hh, ix0, iy0); b = opt(h.get("orient", "R0"), w, hh, ix1, iy1)
                ax.add_patch(Rectangle((ox + min(a[0], b[0]), oy + min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]),
                                       fc="orange", ec="darkorange", lw=0.8, zorder=7))
    for c in t.get("contents", []):
        if "origin_um" in c and "outline_um" in c:
            ox, oy = c["origin_um"]; w, hh = c["outline_um"]
            if ox > x1 or oy > y1 or ox + w < x0 or oy + hh < y0:
                continue
            ax.add_patch(Rectangle((ox, oy), w, hh, fc="none", ec="green", lw=0.5, ls="--", zorder=4))
    names = {h["inst"] for h in chg} | {re.sub(r"__q\d+$", "", h["inst"]) for h in chg}
    for e in t.get("internal_stations", []):
        ends = {str(e.get("launch", "")).split(".")[0], str(e.get("capture", "")).split(".")[0]}
        pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
        if not any(x0 - 50 <= p[0] <= x1 + 50 and y0 - 50 <= p[1] <= y1 + 50 for p in pts):
            continue
        hot = bool(ends & names)
        if hot:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=0.25, c="teal", alpha=0.5, zorder=5)
            ax.scatter([e["to_um"][0], e["from_um"][0]], [e["to_um"][1], e["from_um"][1]], s=3, c="red", lw=0, zorder=8)
        ax.scatter([p[0] for p in e["regs_um"]], [p[1] for p in e["regs_um"]], s=2 if hot else 0.8,
                   c="teal" if hot else "grey", lw=0, zorder=8)
    for tp in t.get("clock", {}).get("taps", []):
        if x0 <= tp["xy"][0] <= x1 and y0 <= tp["xy"][1] <= y1:
            ax.plot([tp["xy"][0]], [tp["xy"][1]], "*", ms=6, c="darkorange", zorder=10)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_title(title, fontsize=8)


def main():
    pb, pa, out = sys.argv[1:4]
    B = load(pb); A = load(pa); Path(out).mkdir(parents=True, exist_ok=True)
    for spec in sys.argv[4:]:
        tn, nm, w = spec.split(":"); win = [float(v) for v in w.split(",")]
        asp = (win[2] - win[0]) / (win[3] - win[1])
        fig, axs = plt.subplots(1, 2, figsize=(min(26, 2 * 9 * max(asp, 0.6)), 9 / max(asp, 0.6) * 0.9 + 1), dpi=120)
        panel(axs[0], *B, tn, win, f"BEFORE {Path(pb).name} {tn} {nm}")
        panel(axs[1], *A, tn, win, f"AFTER {Path(pa).name} {tn} {nm}  (red=changed core, blue/purple=M4/M5 pins, "
                                   "orange=clock entry island + tap, teal=stations of changed cores, red dot=endpoint)")
        fig.tight_layout(); fn = Path(out) / f"z_{tn}_{nm}.png"; fig.savefig(fn); plt.close(fig); print(fn)


if __name__ == "__main__":
    main()
