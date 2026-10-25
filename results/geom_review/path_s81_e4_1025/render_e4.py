"""PATH-S81/E4 renders.  usage: render_e4.py placed.csv f6.tsv OUTDIR TITLE [taps_tt.tsv taps_ff.tsv]
  e4_place.png  : full core; ROM capture flops coloured by bank, line to their ROM pin; reset pin regs; other flops
  e4_romcid.png : zoom on the ROM stack
  e4_cts_<c>.png: register sinks coloured by CK arrival at TT / FF, tap buffers marked, macros drawn"""
import csv, os, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
rows = list(csv.DictReader(open(sys.argv[1])))
f6 = list(csv.DictReader(open(sys.argv[2]), delimiter="\t"))
out, title = sys.argv[3], sys.argv[4]
W, H = 410.4, 466.56
cols = plt.cm.tab10.colors
mac = [r for r in rows if r["kind"] == "macro"]
def macros(ax, label=True):
    for r in mac:
        x, y, w, h = (float(r[c]) for c in "xywh"); n = r["name"].replace("\\", "")
        m = re.search(r"m\[(\d)\]\.rom", n)
        ax.add_patch(Rectangle((x, y), w, h, fc=cols[int(m.group(1))] if m else "#e2e8f0", alpha=0.25 if m else 0.6, ec="#4a5568", lw=0.8))
        if label:
            ax.text(x + w / 2, y + h / 2, f"ROM m[{m.group(1)}]" if m else n.split(".")[-2][-14:] if "." in n else n[-14:], ha="center", va="center", fontsize=6)
def bank(r):
    m = re.search(r"m\\?\[(\d)\\?\]", r["rom"]); return int(m.group(1)) if m else -1
for zoom in (False, True):
    fig, ax = plt.subplots(figsize=(11, 12.5) if not zoom else (11, 12), dpi=110)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="k"))
    macros(ax)
    oth = [(float(r["x"]) + float(r["w"]) / 2, float(r["y"]) + float(r["h"]) / 2) for r in rows if r["kind"] in ("std", "buf", "ff")
           and "bank_words" not in r["name"]]
    ax.scatter(*zip(*oth), s=0.3, c="#cbd5e0", lw=0, rasterized=True, label=f"other cells ({len(oth)})")
    rst = [(float(r["x"]), float(r["y"])) for r in rows if r["kind"] == "ff" and re.match(r"u_r\.(early_n|root)", r["name"].replace("\\", ""))]
    if rst: ax.scatter(*zip(*rst), s=40, c="k", marker="*", label=f"rst_n pin regs ({len(rst)})")
    segs = []
    for b in range(8):
        pts = [r for r in f6 if bank(r) == b]
        if not pts: continue
        d = sorted(float(r["dist_um"]) for r in pts)
        ax.scatter([float(r["fx"]) for r in pts], [float(r["fy"]) for r in pts], s=8, c=[cols[b]], lw=0,
                   label=f"bank {b} capture ({len(pts)}) med {d[len(d)//2]:.1f} max {d[-1]:.1f} um")
        segs += [((float(r["fx"]), float(r["fy"])), (float(r["px"]), float(r["py"]))) for r in pts]
    ax.add_collection(LineCollection(segs, lw=0.3, colors="#2d3748", alpha=0.6))
    if zoom:
        rx = [float(r["x"]) for r in mac if ".rom" in r["name"]] + [float(r["x"]) + float(r["w"]) for r in mac if ".rom" in r["name"]]
        ry = [float(r["y"]) for r in mac if ".rom" in r["name"]] + [float(r["y"]) + float(r["h"]) for r in mac if ".rom" in r["name"]]
        ax.set_xlim(min(rx) - 15, max(rx) + 15); ax.set_ylim(min(ry) - 15, max(ry) + 15)
    else:
        ax.set_xlim(-5, W + 5); ax.set_ylim(-5, H + 5)
    ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7, markerscale=2)
    ax.set_title(title + (" -- ROM stack zoom: capture flop -> own ROM rd pin" if zoom else " -- placement"), fontsize=10)
    plt.tight_layout(); fn = os.path.join(out, "e4_romcid.png" if zoom else "e4_place.png"); plt.savefig(fn); plt.close(fig); print("ok", fn)
for tf in sys.argv[5:]:
    c = "ff" if "_ff" in tf else "tt"
    t = [r for r in csv.DictReader(open(tf), delimiter="\t") if float(r["arr_ps"]) > 0]
    fig, ax = plt.subplots(figsize=(11, 12.5), dpi=110)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="k")); macros(ax, False)
    a = [float(r["arr_ps"]) for r in t]
    sc = ax.scatter([float(r["x"]) for r in t], [float(r["y"]) for r in t], c=a, s=1.5, cmap="viridis", lw=0, rasterized=True)
    plt.colorbar(sc, ax=ax, shrink=0.6, label=f"CK arrival {c.upper()} (ps)")
    taps = {}
    for r in t: taps.setdefault(r["tap"], []).append((float(r["x"]), float(r["y"]), float(r["arr_ps"])))
    for k, v in taps.items():
        mx = sum(p[0] for p in v) / len(v); my = sum(p[1] for p in v) / len(v)
        ax.text(mx, my, k, fontsize=5, color="r", ha="center")
    ax.set_xlim(-5, W + 5); ax.set_ylim(-5, H + 5); ax.set_aspect("equal")
    ax.set_title(f"{title} -- 4_cts sinks by CK arrival {c.upper()}: {len(taps)} density taps, {len(t)} sinks, "
                 f"{min(a):.0f}-{max(a):.0f} ps", fontsize=10)
    plt.tight_layout(); fn = os.path.join(out, f"e4_cts_{c}.png"); plt.savefig(fn); plt.close(fig); print("ok", fn)
