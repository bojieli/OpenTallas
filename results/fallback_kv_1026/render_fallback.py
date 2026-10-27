#!/usr/bin/env python3
"""render the fallback seam classes: partitions by clock region, landed region / phy seams, failing related seams."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fb = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2])); gate = json.load(open(sys.argv[3])); out = sys.argv[4]
T = {t["name"]: t for t in plan["partition_types"]} if isinstance(plan["partition_types"], list) else plan["partition_types"]
reg = fb["part_region"]; tags = sorted({r["tag"] for r in fb["regions"]})
cm = plt.get_cmap("tab10"); col = {t: cm(i) for i, t in enumerate(tags)}
ctr = {}
fig, ax = plt.subplots(figsize=(9, 18))
for p in plan["partitions"]:
    w, h = T[p["type"]]["outline_um"]; x, y = p["origin_um"]
    ax.add_patch(Rectangle((x, y), w, h, fc=col[reg[p["name"]]], ec="k", lw=0.3, alpha=0.35))
    ctr[p["name"]] = (x + w / 2, y + h / 2)
for r in fb["regions"]:
    b = r["box_um"]; ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="k", lw=2))
    ax.text(b[0] + 80, b[3] - 300, r["tag"], fontsize=11, weight="bold")
seen = set()
for q in fb["landed_ports"]:
    k = (q["src"], q["dst"], q["cls"])
    if k in seen: continue
    seen.add(k); (x0, y0), (x1, y1) = ctr[q["src"]], ctr[q["dst"]]
    ax.plot([x0, x1], [y0, y1], color="red" if q["cls"] == "region" else "orange", lw=0.6, alpha=0.7)
neg = gate.get("residual_related_FF", [])
for s in neg:
    a, b = s.split("/", 1)[0].split("->"); (x0, y0), (x1, y1) = ctr[a], ctr[b]
    ax.plot([x0, x1], [y0, y1], color="blue", lw=3)
W = max(r["box_um"][2] for r in fb["regions"]); H = max(r["box_um"][3] for r in fb["regions"])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
ax.set_title(f"KV fallback: 8 clock regions; red = landed region seam ({sum(1 for q in fb['landed_ports'] if q['cls']=='region')} ports), "
             f"orange = landed PHY seam, blue = related seam FF hold<0 at W={gate.get('contract_ps')}", fontsize=8)
fig.savefig(out, dpi=110, bbox_inches="tight"); print(out)
