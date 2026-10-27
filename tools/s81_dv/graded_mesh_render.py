#!/usr/bin/env python3
"""Full-metal render of a graded_mesh_encode.py output: die-wide + true-geometry zoom windows (PG, rails, rail
shields, bank collectors/risers, stub drops, tree wires + shields, VIA89 pads, pin stacks, census findings)."""
import argparse, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.patches import Rectangle

COL = {"pg_VDD": "#d62728", "pg_VDDPHY": "#e377c2", "pg_VSS": "#1f77b4", "mesh": "#ff7f0e", "rail_shield": "#17becf", "tree": "#2ca02c",
       "shield": "#9edae5", "bank": "#9467bd", "bank_riser": "#9467bd", "stub_drop": "#8c564b", "via": "#000000"}


def xyrect(s):
    lay, net, kind, plo, phi, alo, ahi = s[:7]
    return (alo, plo, ahi - alo, phi - plo) if lay == "M8" else (plo, alo, phi - plo, ahi - alo)


def key(s):
    k = s[2]
    return k if k in COL else ("shield" if s[1] == "VSS" else "tree")


def window(ax, E, box, title, findings):
    x0, y0, x1, y1 = box
    groups = {}
    pg = [("M8" if r[1] == "M8" else "M9", r[0], "pg", r) for r in E["pg_rects"]]
    for lay, net, _, r in pg:
        _, _, rx0, ry0, rx1, ry1 = r
        if rx1 < x0 or rx0 > x1 or ry1 < y0 or ry0 > y1:
            continue
        groups.setdefault(f"pg_{net if net in ('VDD','VSS','VDDPHY') else 'VDD'}", []).append((rx0, ry0, rx1 - rx0, ry1 - ry0))
    for s in E["shapes"]:
        rx, ry, w, h = xyrect(s)
        if rx + w < x0 or rx > x1 or ry + h < y0 or ry > y1:
            continue
        groups.setdefault(key(s), []).append((rx, ry, w, h))
    order = ["pg_VDD", "pg_VDDPHY", "pg_VSS", "rail_shield", "shield", "tree", "mesh", "bank", "bank_riser", "stub_drop"]
    for k in order:
        if k in groups:
            ax.add_collection(PatchCollection([Rectangle((a, b), c, d) for a, b, c, d in groups[k]], facecolor=COL[k],
                                              edgecolor="none", alpha=.35 if k.startswith("pg") else .85, label=f"{k} ({len(groups[k])})"))
    vs = [v for v in E["vias"] if x0 <= v["x_um"] <= x1 and y0 <= v["y_um"] <= y1]
    ax.add_collection(PatchCollection([Rectangle((v["x_um"] - v["pad_um"] / 2, v["y_um"] - v["pad_um"] / 2), v["pad_um"], v["pad_um"]) for v in vs],
                                      facecolor="none", edgecolor="k", linewidth=.6, label=f"VIA89 pad ({len(vs)})"))
    st = [s for s in E["stacks"] if x0 <= s["xy_um"][0] <= x1 and y0 <= s["xy_um"][1] <= y1]
    if st:
        ax.plot([s["xy_um"][0] for s in st], [s["xy_um"][1] for s in st], "m.", ms=3, label=f"pin stack ({len(st)})")
    fx = [f for f in findings if x0 <= f[0] <= x1 and y0 <= f[1] <= y1]
    if fx:
        ax.plot([f[0] for f in fx], [f[1] for f in fx], "rx", ms=10, mew=2, label=f"census finding ({len(fx)})")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_title(title, fontsize=8)
    ax.legend(fontsize=5, loc="upper right")


def main(a):
    d = Path(a.dir)
    E = json.loads((d / "encoded_metal.json").read_text())
    R = json.loads((d / "ENCODE.json").read_text())
    F = json.loads((d / "findings.json").read_text())
    fpts = []
    for r in F["census_rows"]:
        s = r["a"]; rx, ry, w, h = xyrect(s); fpts.append((rx + w / 2, ry + h / 2))
    for r in F["via"]:
        fpts.append(tuple(r["via"]))
    # die-wide
    fig, ax = plt.subplots(figsize=(16, 12.4), dpi=110)
    lines = {}
    for s in E["shapes"]:
        k = key(s)
        if k in ("rail_shield", "shield"):
            continue
        lay, _, _, plo, phi, alo, ahi = s[:7]
        c = (plo + phi) / 2
        seg = [(alo, c), (ahi, c)] if lay == "M8" else [(c, alo), (c, ahi)]
        lines.setdefault(k, ([], []))[0].append(seg); lines[k][1].append(.2 + 1.2 * (phi - plo))
    for k, (segs, lw) in lines.items():
        ax.add_collection(LineCollection(segs, colors=COL[k], linewidths=lw if k == "mesh" else .15, label=f"{k} ({len(segs)})"))
    if fpts:
        ax.plot([p[0] for p in fpts], [p[1] for p in fpts], "rx", ms=6, label=f"census findings ({len(fpts)} shown)")
    W = max(v["x_um"] for v in E["vias"]) + 500; H = max(v["y_um"] for v in E["vias"]) + 300
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"S81 graded mesh ENCODED die-wide: {R['status']} | rails M8 {R['rails']['M8']} M9 {R['rails']['M9']} | "
                 f"shorts {R['metal_shorts']} spacing {R['metal_spacing']} | via-out {R['via_outside_incident']} | fails {R['fails']}", fontsize=9)
    fig.savefig(d / "die_full_metal.png", bbox_inches="tight"); plt.close(fig)
    # zoom windows
    vias = E["vias"]
    widest = max(vias, key=lambda v: v["pad_um"])
    corner = min(vias, key=lambda v: v["x_um"] + v["y_um"])
    banks = [a for a in E["attachments"] if a["role"] == "driver"]
    big = max(banks, key=lambda a: len(a["units"]))
    stubs = [a for a in E["attachments"] if a["role"] != "driver"]
    stub = stubs[len(stubs) // 2]
    wins = [("root / widest crossing", widest["x_um"], widest["y_um"], 30), ("die-edge rail end (SW corner)", corner["x_um"], corner["y_um"], 30),
            (f"largest driver bank ({len(big['units'])} BUFx24)", big["xy_um"][0], big["xy_um"][1], 25),
            ("stub drop / pin stack", stub["xy_um"][0], stub["xy_um"][1], 15)]
    ce = E.get("phy_clip_ends") or []
    for j, t in ((0, "first"), (len(ce) // 2, "middle"), (len(ce) - 1, "last")):
        if ce:
            wins.append((f"PHY-band rail end ({t} of {len(ce)})", ce[j][0], ce[j][1], 14))
    if fpts:
        wins.append(("first census finding", fpts[0][0], fpts[0][1], 12))
    if len(fpts) > 1:
        wins.append(("middle census finding", fpts[len(fpts) // 2][0], fpts[len(fpts) // 2][1], 12))
    for i, (t, x, y, r) in enumerate(wins):
        fig, ax = plt.subplots(figsize=(9, 9), dpi=120)
        window(ax, E, (x - r, y - r, x + r, y + r), f"{t} @ ({x:.2f},{y:.2f}) +-{r} um", fpts)
        fig.savefig(d / f"zoom_{i}.png", bbox_inches="tight"); plt.close(fig)
    print("rendered", d)


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("dir"); main(p.parse_args())
