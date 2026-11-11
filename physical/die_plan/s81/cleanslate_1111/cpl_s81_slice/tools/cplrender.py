#!/usr/bin/env python3
"""CPL-S81-SLICE render: one type, one placement -> PNG (plan view + cut profile table)."""
import math
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle, Circle  # noqa: E402

import cpl  # noqa: E402

FCOL = {"N": "#d62728", "S": "#1f77b4", "E": "#2ca02c", "W": "#9467bd"}


def render(M, pl, out, title, scores=None, ref=None):
    W, H = M.W, M.H
    fig = plt.figure(figsize=(19, 10.5), dpi=110)
    ax = fig.add_axes([0.03, 0.05, 0.60, 0.88])
    ax.set_xlim(-60, W + 60)
    ax.set_ylim(-60, H + 60)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    # fixed macros
    for fx in M.fixed:
        ax.add_patch(Rectangle((fx[0], fx[1]), fx[2] - fx[0], fx[3] - fx[1], fc="#dddddd", ec="#999999", lw=0.4,
                               hatch="///"))
    # bands
    for (r, k, w) in M.bands:
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#9be29b", ec="g", lw=0.6, alpha=0.7))
        ax.text(r[0], r[3] + 3, "band %s" % k, fontsize=5, color="g")
    # windows
    for b in M.buses.values():
        lo, hi = b["window_um"][:2]
        lw = 2 + min(6, b.get("width", 1) / 200)
        c = "#ff7f0e" if b.get("dir") == "in" else "#8c564b"
        if b["face"] in ("N", "S"):
            y = H if b["face"] == "N" else 0
            ax.plot([lo, hi], [y, y], color=c, lw=lw, solid_capstyle="butt")
            ax.text((lo + hi) / 2, y + (12 if b["face"] == "N" else -26), "%s %db" % (b["name"], b["width"]),
                    fontsize=5, ha="center", color=c, rotation=0)
        else:
            x = W if b["face"] == "E" else 0
            ax.plot([x, x], [lo, hi], color=c, lw=lw, solid_capstyle="butt")
            ax.text(x + (8 if b["face"] == "E" else -8), (lo + hi) / 2, "%s %db" % (b["name"], b["width"]),
                    fontsize=5, va="center", ha="left" if b["face"] == "E" else "right", color=c, rotation=90)
    # ft slots
    for (a, c, bits) in M.fixed_segments():
        ax.plot([a[0], c[0]], [a[1], c[1]], color="#17becf", lw=0.6 + min(4, bits / 250), ls="--", alpha=0.8)
    for f in M.ft:
        for r in f.get("regs_um") or []:
            ax.plot(r[0], r[1], "s", color="#003f5c", ms=2.5)
    # clock tap
    ax.plot(*M.tap, marker="*", color="red", ms=12)
    # cores
    R = [M.rect(i, pl) for i in range(len(M.cores))]
    for i, h in enumerate(M.cores):
        r = R[i]
        moved = ref is not None and tuple(ref[i]) != tuple(pl[i])
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#fff3c4" if not moved else "#ffd6e7",
                               ec="#444", lw=0.9))
        lab = h["inst"].split(".")[-1] if not h["inst"].endswith(".u_l") else h["inst"].split(".")[-2]
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, "%s\n%s %s\n%s" % (lab, h["module"].replace("ot_", "")[:18],
                pl[i][2], h.get("obs_max", "")), fontsize=5.5, ha="center", va="center")
        # pin groups per face
        w, hh = h["outline_um"]
        cnt = Counter()
        for bus, pts in M.pins[h["module"]].items():
            for (px, py) in pts:
                X, Y = cpl.opt(w, hh, pl[i][2], px, py)
                cnt[cpl.face_of(w, hh, X, Y)] += 1
        for f, n in cnt.items():
            if n < 2:
                continue
            fx, fy = dict(N=((r[0] + r[2]) / 2, r[3] - 7), S=((r[0] + r[2]) / 2, r[1] + 3),
                          E=(r[2] - 3, (r[1] + r[3]) / 2), W=(r[0] + 3, (r[1] + r[3]) / 2))[f]
            ax.text(fx, fy, "%s%d" % (f, n), fontsize=4.5, color=FCOL[f], ha="center" if f in "NS" else
                    ("right" if f == "E" else "left"), va="center", fontweight="bold")
            th = 4
            if f in "NS":
                y = r[3] if f == "N" else r[1]
                ax.plot([r[0] + 2, r[2] - 2], [y, y], color=FCOL[f], lw=min(3.5, 0.5 + n / 400))
            else:
                x = r[2] if f == "E" else r[0]
                ax.plot([x, x], [r[1] + 2, r[3] - 2], color=FCOL[f], lw=min(3.5, 0.5 + n / 400))
    # flylines
    links = sorted(M.links, key=lambda l: -l["bits"])
    top = set(id(l) for l in links[:20])
    for l in links:
        a, c = M.link_pts(l, pl)
        b = l["bits"]
        ax.plot([a[0], c[0]], [a[1], c[1]], color="#e377c2" if l["b"][0] == "core" else "#7f7f7f",
                lw=0.3 + min(3.5, b / 300) * (1.6 if id(l) in top else 1), alpha=0.75 if id(l) in top else 0.35)
    # reach circles on station links (core end, radius 405)
    for s in M.st[:60]:
        if s["face"] and s["pins"]:
            i, bus = s["pins"][0]
            c = M.bus_cen(i, bus, pl)
            ax.add_patch(Circle(c, 405, fill=False, ls=":", lw=0.3, ec="#bcbd22"))
    for s, e in enumerate(M.t.get("internal_stations") or []):
        pass
    ax.set_title(title, fontsize=10)
    # cut profiles
    ct = M.cut_table(pl)
    ax2 = fig.add_axes([0.67, 0.56, 0.31, 0.36])
    ax2.plot([r[0] for r in ct["V"]], [r[3] for r in ct["V"]], label="V cut x (bits W<->E / H tracks)")
    ax2.plot([r[0] for r in ct["H"]], [r[3] for r in ct["H"]], label="H cut y (bits S<->N / V tracks)")
    ax2.axhline(0.8, color="r", ls="--", lw=0.8)
    ax2.set_ylim(0, max(1.0, max([r[3] for r in ct["V"] + ct["H"]] + [0]) * 1.1))
    ax2.set_xlabel("cut position um")
    ax2.set_ylabel("demand / supply")
    ax2.legend(fontsize=7)
    ax2.set_title("full-outline cut profile (macros M6-only H, halved; streets M2/M4/M6)", fontsize=8)
    ax3 = fig.add_axes([0.67, 0.05, 0.31, 0.44])
    ax3.axis("off")
    wv = max(ct["V"], key=lambda r: r[3]) if ct["V"] else (0, 0, 0, 0)
    wh = max(ct["H"], key=lambda r: r[3]) if ct["H"] else (0, 0, 0, 0)
    lines = ["worst V cut x=%.0f: %d bits / %d H tracks = %.2f" % wv,
             "worst H cut y=%.0f: %d bits / %d V tracks = %.2f" % wh]
    # per-cut table, coarse (every ~100 um)
    lines.append("")
    lines.append("V cuts (x um: bits / H tracks)")
    stepV = max(1, len(ct["V"]) // 12)
    lines += ["  x=%6.0f  %6d / %6d  %.2f" % r for r in ct["V"][::stepV]]
    lines.append("H cuts (y um: bits / V tracks)")
    stepH = max(1, len(ct["H"]) // 10)
    lines += ["  y=%6.0f  %6d / %6d  %.2f" % r for r in ct["H"][::stepH]]
    if scores:
        lines.append("")
        lines += ["%s: %s" % (k, v) for k, v in scores.items()]
    ax3.text(0, 1, "\n".join(lines), fontsize=6.5, family="monospace", va="top")
    fig.savefig(out)
    plt.close(fig)
