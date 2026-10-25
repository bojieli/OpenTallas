"""Zoom on the ROM columns: CPRE capture flops coloured by ROM bank, tag flops, u_map select logic, cid outputs.
usage: render_romcid.py placed.csv out.png title"""
import csv, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
rows = list(csv.DictReader(open(sys.argv[1])))
cols = plt.cm.tab10.colors
fig, ax = plt.subplots(figsize=(11, 12), dpi=110)
rom = {}
for r in rows:
    if r["kind"] != "macro": continue
    x, y, w, h = (float(r[c]) for c in "xywh"); n = r["name"].replace("\\", "")
    m = re.search(r"m\[(\d)\]", n)
    fc = cols[int(m.group(1))] if m else "#e2e8f0"
    if m: rom[int(m.group(1))] = (x, y, w, h)
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, alpha=0.25 if m else 0.6, ec="#4a5568", lw=0.8))
    ax.text(x + w / 2, y + h / 2, (f"ROM m[{m.group(1)}]" if m else n.split(".")[-1])[-20:], ha="center", va="center", fontsize=8)
pts = {"bank": [[] for _ in range(8)], "tag": [], "map": [], "cid": [], "other": []}
for r in rows:
    if r["kind"] in ("macro", "tap", "pin"): continue
    n = r["name"].replace("\\", ""); cx = float(r["x"]) + float(r["w"]) / 2; cy = float(r["y"]) + float(r["h"]) / 2
    if not (0 <= cx <= 200 and 60 <= cy <= 360): continue
    m = re.search(r"g_capture_first\.bank_words\[(\d+)\]", n)
    if m: pts["bank"][int(m.group(1)) // 4].append((cx, cy)); continue
    if "g_capture_first.bank_word_tag" in n: pts["tag"].append((cx, cy)); continue
    if "u_map" in n and r["kind"] == "ff": pts["cid"].append((cx, cy)); continue
    if "u_map" in n: pts["map"].append((cx, cy)); continue
    pts["other"].append((cx, cy))
def sc(p, **k):
    if p: ax.scatter(*zip(*p), lw=0, rasterized=True, **k)
sc(pts["other"], s=0.4, c="#cbd5e0", label=f"other cells ({len(pts['other'])})")
sc(pts["map"], s=2, c="#718096", label=f"u_map comb ({len(pts['map'])})")
sc(pts["cid"], s=6, c="k", marker="x", label=f"u_map other ff ({len(pts['cid'])})")
sc(pts["tag"], s=10, c="m", marker="^", label=f"tag ff ({len(pts['tag'])})")
for b in range(8):
    sc(pts["bank"][b], s=9, c=[cols[b]], label=f"capture ff bank {b} ({len(pts['bank'][b])})")
ax.set_xlim(0, 200); ax.set_ylim(60, 360); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=7, markerscale=2)
ax.set_title(sys.argv[3], fontsize=10)
plt.tight_layout(); plt.savefig(sys.argv[2]); print("ok", sys.argv[2])
