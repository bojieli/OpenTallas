"""render a placed kit dump (dump_place.tcl) for GEOM review: outline, flops (face regs green / ft stations orange /
reset relays red / other seq grey), buffers black, pins blue; prints pin->reg and reg->reg hop stats."""
import sys, re, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src, png, title = sys.argv[1], sys.argv[2], sys.argv[3]
W = H = 0; I = []; P = []
for ln in open(src):
    p = ln.rstrip("\n").split("\t")
    if p[0] == "DIE": W, H = float(p[1]), float(p[2])
    elif p[0] == "I": I.append((p[1], p[2], *map(float, p[3:7])))
    elif p[0] == "P": P.append((p[1], float(p[2]), float(p[3])))
fig, ax = plt.subplots(figsize=(10, 10 * H / W if W else 10))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1))
cat = dict(face=[], st=[], rst=[], seq=[], buf=[], other=[], macro=[])
for n, m, x0, y0, x1, y1 in I:
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if (x1 - x0) * (y1 - y0) > 20: cat["macro"].append((x0, y0, x1, y1)); continue
    if m.startswith(("TAPCELL", "FILLER", "DECAP")): continue
    if "DFF" in m or "DHL" in m or "DLL" in m:
        k = "rst" if re.search(r"rst|rrl", n) else ("st" if re.search(r"(^|/)u?_?ft|st_", n) else ("face" if re.search(r"face|_q_reg|bf_|in_q|out_q", n) else "seq"))
        cat[k].append((cx, cy))
    elif m.startswith(("BUF", "INV", "HB")): cat["buf"].append((cx, cy))
    else: cat["other"].append((cx, cy))
for x0, y0, x1, y1 in cat["macro"]: ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.7"))
for k, c, s in (("other", "0.85", 0.3), ("buf", "k", 0.6), ("seq", "0.5", 0.8), ("face", "g", 1.2), ("st", "orange", 1.5), ("rst", "r", 4)):
    if cat[k]: ax.scatter(*zip(*cat[k]), s=s, c=c, label=f"{k} {len(cat[k])}", linewidths=0)
if P: ax.scatter([p[1] for p in P], [p[2] for p in P], s=0.5, c="b", label=f"pins {len(P)}")
ax.set_xlim(-5, W + 5); ax.set_ylim(-5, H + 5); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7, markerscale=4)
ax.set_title(title, fontsize=9)
fig.savefig(png, dpi=130, bbox_inches="tight")
print(title, "outline", W, H, {k: len(v) for k, v in cat.items()}, "pins", len(P),
      "util_est", round(sum((x1-x0)*(y1-y0) for _, m, x0, y0, x1, y1 in I if not m.startswith(("TAPCELL","FILLER"))) / (W*H), 4) if W else None)
import os
if os.path.exists(src + ".hops"):
    prall = [float(l.split("\t")[2]) for l in open(src + ".hops") if l.startswith("PR")]; pr = sorted(x for x in prall if x >= 0); print("pins without a flop through buffers", sum(x < 0 for x in prall))
    rr = sorted(float(l.split("\t")[2]) for l in open(src + ".hops") if l.startswith("RR"))
    q = lambda v, f: v[int(f * (len(v) - 1))] if v else None
    print("pin->reg n", len(pr), "p90", q(pr, .9), "max", pr[-1] if pr else None, "| reg->reg (through bufs) n", len(rr), "max", rr[-1] if rr else None, ">405", sum(x > 405 for x in rr))
