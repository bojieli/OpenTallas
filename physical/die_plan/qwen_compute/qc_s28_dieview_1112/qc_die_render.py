#!/usr/bin/env python3
"""QC-S28-DIEVIEW (11-12): whole-die QC overlay render from qc_die_audit.py's audit.json.

    python3 -I qc_die_render.py AUDIT.json OUT_DIR [--tag before] [--title TEXT]

Draws every partition slot in die coordinates:
  fill colour  = soft-cell fill (cell area / soft area; cb*/su cores: total fill incl. macros, hatched '//'),
  thick red edge = route_supply p99 > 1.0 (orange 0.8-1.0),  label = type / fill % / aspect / p99 / max sinks per tap,
  grey = hard cores (orient applied), magenta = macro streets < 20 um, cyan = landing ring bands,
  dots = clock taps (size ~ sinks; red = over the cap), red lines = station / ft hops > 405 um,
  orange x = station ends off their core / face (stale-site candidates > 60 um).
Writes <tag>_die.png (full die) and zoom PNGs (family windows)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib import cm, colors  # noqa: E402

ZOOMS = {
    "w5_column": (1500, 0, 4200, 25700),
    "sl_strip_W": (1500, 9900, 9300, 15500),
    "sl_strip_E": (16900, 9900, 24700, 15500),
    "west_io_coll": (0, 3000, 1650, 16000),
    "cb_pair_bottom": (1500, 0, 4200, 7700),
    "cb_pair_top": (1500, 17900, 4200, 25700),
}


def tf(p, pt, W, H):
    x, y = pt
    o = p["orient"]
    X, Y = {"R0": (x, y), "MX": (x, H - y), "MY": (W - x, y), "R180": (W - x, H - y)}[o]
    return p["origin"][0] + X, p["origin"][1] + Y


def trect(p, r, W, H):
    a = tf(p, (r[0], r[1]), W, H)
    b = tf(p, (r[2], r[3]), W, H)
    return min(a[0], b[0]), min(a[1], b[1]), abs(a[0] - b[0]), abs(a[1] - b[1])


def short(tn):
    return tn.split("__")[0]


def draw(doc, ax, box=None, labels=True, fs=3.0, tapscale=1.0):
    rows, geom = doc["rows"], doc["geom"]
    cmap = matplotlib.colormaps["viridis"]
    norm = colors.Normalize(0, 0.7)
    for c in doc.get("die_channels", []):
        r = c["rect_um"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#222", ec="#555", lw=0.3, hatch="..", zorder=0))
    for p in doc["parts"]:
        tn = p["type"]
        r, g = rows[tn], geom[tn]
        W, H = r["W"], r["H"]
        x0, y0 = p["origin"]
        if box and (x0 > box[2] or x0 + W < box[0] or y0 > box[3] or y0 + H < box[1]):
            continue
        macro = r["macro_frac"] > 0.2
        f = r["total_fill"] if macro else (r["soft_fill"] or 0)
        if r.get("fill_est") is not None:
            f = r["fill_est_total"] if macro else r["fill_est"]
        known = (r["cells"] or 0) > 0 or macro or r.get("fill_est")
        fc = cmap(norm(f)) if known else (0.35, 0.35, 0.35, 1)
        p99 = r.get("route_p99")
        try:
            p99v = float(p99)
        except (TypeError, ValueError):
            p99v = 0
        ec, lw = ("#ff2020", 1.6) if p99v > 1.0 else (("#ff9a1a", 1.1) if p99v > 0.8 else ("#101010", 0.4))
        ax.add_patch(Rectangle((x0, y0), W, H, fc=fc, ec=ec, lw=lw, hatch="//" if macro else None, zorder=1))
        for c in g["cores"]:
            x, y, w, h = trect(p, c["r"], W, H)
            ax.add_patch(Rectangle((x, y), w, h, fc="#9a9a9a", ec="#333", lw=0.25, alpha=0.85, zorder=2))
        for b in g["bands"]:
            x, y, w, h = trect(p, b["r"], W, H)
            ax.add_patch(Rectangle((x, y), w, h, fc="#00e5ff", ec="none", alpha=0.55, zorder=3))
        for s in g["streets"]:
            if s["g"] < 20:
                x, y, w, h = trect(p, s["r"], W, H)
                ax.add_patch(Rectangle((x, y), max(w, 6), max(h, 6), fc="#ff00ff", ec="none", alpha=0.9, zorder=4))
        cap = r.get("tap_cap") or 1200
        if g["taps"]:
            P = [tf(p, (t["x"], t["y"]), W, H) for t in g["taps"]]
            S = [t["sinks"] or 0 for t in g["taps"]]
            ax.scatter([q[0] for q in P], [q[1] for q in P], s=[(0.4 + 2.5 * v / cap) * tapscale for v in S],
                       c=["#ff1010" if v > cap else "#ffffff" for v in S], linewidths=0, zorder=6)
        for o in g["over"]:
            A = tf(p, o["a"], W, H)
            B = tf(p, o["b"], W, H)
            ax.plot([A[0], B[0]], [A[1], B[1]], color="#ff0000", lw=1.8, zorder=7)
        if labels:
            txt = f"{short(tn)}\nf{100 * f:.0f}% a{r['aspect']} p{p99v:.2f}\nt{r['taps']}/{r['max_sinks_tap']}"
            if r.get("hops_gt405"):
                txt += f" H{r['hops_gt405']}"
            ax.text(x0 + W / 2, y0 + H / 2, txt, ha="center", va="center", fontsize=fs, color="white", zorder=8,
                    bbox=dict(fc="black", alpha=0.45, lw=0, pad=0.4))
    for p in doc["parts"]:
        tn = p["type"]
        for st in doc["geom"][tn].get("stale", []):
            X, Y = tf(p, st["at"], doc["rows"][tn]["W"], doc["rows"][tn]["H"])
            ax.scatter([X], [Y], marker="x", s=14, c="#ffa500", lw=0.8, zorder=9)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    return sm


def main():
    a = sys.argv[1:]
    doc = json.loads(Path(a[0]).read_text())
    out = Path(a[1])
    out.mkdir(parents=True, exist_ok=True)
    tag = a[a.index("--tag") + 1] if "--tag" in a else "before"
    title = a[a.index("--title") + 1] if "--title" in a else doc["plan"]
    DW, DH = doc["die"]
    fig, ax = plt.subplots(figsize=(36, 30), dpi=110)
    fig.patch.set_facecolor("#0b0d12")
    ax.set_facecolor("#0b0d12")
    sm = draw(doc, ax, fs=2.6)
    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect("equal")
    ax.tick_params(colors="#bbb")
    ax.set_title(f"QC die overlay [{tag}] {title}\nfill (soft; hatched = macro types, total) | edge red p99>1, orange 0.8-1 "
                 f"| grey hard cores | cyan landing rings | magenta streets<20um | dots taps (red > cap) | red lines hops>405 "
                 f"| x stale station ends", color="white", fontsize=16)
    cb = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.01)
    cb.set_label("fill", color="white")
    cb.ax.yaxis.set_tick_params(color="white", labelcolor="white")
    fig.savefig(out / f"{tag}_die.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    for name, box in ZOOMS.items():
        w, h = box[2] - box[0], box[3] - box[1]
        sc = 14.0 / max(w, h) * 1000
        fig, ax = plt.subplots(figsize=(max(4, w / 1000 * sc), max(4, h / 1000 * sc)), dpi=130)
        fig.patch.set_facecolor("#0b0d12")
        ax.set_facecolor("#0b0d12")
        draw(doc, ax, box=box, fs=6.5, tapscale=5)
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
        ax.set_aspect("equal")
        ax.tick_params(colors="#bbb")
        ax.set_title(f"[{tag}] {name}", color="white")
        fig.savefig(out / f"{tag}_{name}.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
