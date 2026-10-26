"""S81/IDXNET 10-25: die render with the 6 IDXNET lanes highlighted (port windows joined in order) + crops.
usage: python3 render_idxnet.py die_plan.json OUTDIR"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
T = d["partition_types"]
W, H = d["die"]["outline_um"]
def rect(p):
    t = T[p["type"]]; w, h = t["outline_um"]
    x, y = p["origin_um"]
    if p.get("orient") in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
    return x, y, w, h
parts = {p["name"]: rect(p) for p in d["partitions"]}
NEW = ["tp__bk_sel__s_7N_LP", "tp__s_7N_LP__bk_sel", "tp__bk_sel__s_7S_LP", "tp__s_0S_LP__s_0N_LP", "ql__s_0N_LP__iqf",
       "qc__iqf__s_0N_LP"]
OLD = ["tl__bk_sel__s_0N_LP", "ca__s_0N_LP__bk_sel", "cb__s_0N_LP__bk_sel"]
col = dict(zip(NEW + OLD, ["#d62728", "#ff7f0e", "#9467bd", "#2ca02c", "#1f77b4", "#17becf", "#999999", "#bbbbbb", "#cccccc"]))
ports = [p for p in d["ports"] if "__".join(p["id"].split("__")[:-1]) in col]
def ctr(pn):
    x, y, w, h = parts[pn]; return x + w / 2, y + h / 2
def face_pt(p):
    x, y, w, h = parts[p["src"]["part"]]
    a, b = p["window_um"]; m = (a + b) / 2
    f = p["face"]
    return {"N": (m, y + h), "S": (m, y), "E": (x + w, m), "W": (x, m)}[f]
hot = set()
for p in ports: hot.add(p["src"]["part"]); hot.add(p["dst"]["part"])
def draw(ax, lim=None):
    for n, (x, y, w, h) in parts.items():
        fc = "#fde9b7" if n in ("bk_sel", "iqf") or n.endswith("_LP") and n in hot else ("#eef3f8" if n in hot else "#f4f4f4")
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#888888", lw=0.3))
        if (n in hot or n in ("bk_sel", "iqf")) and (lim is not None or n in ("bk_sel", "iqf") or n.endswith("_LP")):
            ax.text(x + w / 2, y + h / 2, n, fontsize=4 if lim is None else 6, ha="center", va="center", clip_on=True)
    for lane in OLD + NEW:
        seq = [p for p in ports if "__".join(p["id"].split("__")[:-1]) == lane]
        seq.sort(key=lambda p: int(p["id"].split("__")[-1]))
        if not seq: continue
        pts = [ctr(seq[0]["src"]["part"])]
        for p in seq: pts += [face_pt(p), ctr(p["dst"]["part"])]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, "-", color=col[lane], lw=1.6 if lane in NEW else 0.8, label=lane, alpha=0.9)
        ax.plot(xs[1:-1:2], ys[1:-1:2], "o", color=col[lane], ms=2)
    ax.set_aspect("equal")
    if lim: ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
    else: ax.set_xlim(0, W); ax.set_ylim(0, H)
fig, ax = plt.subplots(figsize=(16, 12.5), dpi=130); draw(ax); ax.legend(fontsize=6, loc="upper right")
ax.set_title("S81 v4.8 + IDXNET 10-25: topk_final TP4 lanes + rank-tree query lanes (grey = H4 tree lanes)")
fig.savefig(out / "idxnet_die.png", bbox_inches="tight"); plt.close(fig)
cw, ch = 1442.88, 1226.88
for nm, (c0, c1, r0, r1) in {"col6_iqf_s0": (4, 10, -0.2, 15.5), "bksel_col15": (10, 17, 7, 20.2)}.items():
    fig, ax = plt.subplots(figsize=(12, 12), dpi=130); draw(ax, (c0 * cw, c1 * cw, r0 * ch, r1 * ch))
    ax.legend(fontsize=7, loc="lower right"); ax.set_title(nm)
    fig.savefig(out / f"idxnet_{nm}.png", bbox_inches="tight"); plt.close(fig)
print("ok", len(ports), "port segments")
