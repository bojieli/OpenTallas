"""DIE-HBM-10: render the C22 idx Q2 homes (types q_b013..q_b000, W -> E as on the NW side) with ft bit sites + regs."""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); T = P["partition_types"]; out = sys.argv[2]
order = [p for p in P["partitions"] if p["name"].startswith("NW_b0")]; order.sort(key=lambda p: p["origin_um"][0])
fig, ax = plt.subplots(figsize=(16, 14))
for p in order:
    t = T[p["type"]]; ox, oy = p["origin_um"]; W, H = t["outline_um"]
    ax.add_patch(Rectangle((ox, oy), W, H, fill=False, lw=1.5, ec="k")); ax.text(ox + 5, oy + H + 20, p["name"], fontsize=8)
    for h in t["hard_cores"]:
        q2 = h["inst"].startswith("u_hb_idx__s_Q2")
        ax.add_patch(Rectangle((ox + h["origin_um"][0], oy + h["origin_um"][1]), *h["outline_um"], fc="tab:red" if q2 else "tab:blue", alpha=.55, ec="k", lw=.3))
    for c in t.get("contents", []):
        if c.get("origin_um") and c.get("outline_um"):
            ax.add_patch(Rectangle((ox + c["origin_um"][0], oy + c["origin_um"][1]), *c["outline_um"], fc="orange", alpha=.8))
    xs, ys, rx, ry = [], [], [], []
    for s in t.get("ft_slots", []):
        for st in s.get("bit_sites_um") or []:
            xs += [ox + x for x, y in st[::25]]; ys += [oy + y for x, y in st[::25]]
        for r in s.get("regs_um") or []: rx.append(ox + r[0]); ry.append(oy + r[1])
    ax.plot(xs, ys, ",", color="green"); ax.plot(rx, ry, "x", color="purple", ms=4)
ax.set_aspect("equal"); ax.autoscale(); ax.set_title("C22 NW_b0xx: idx Q2 pieces (red), other hard cores (blue), ft bit sites (green, 1/25), station regs (x)")
plt.savefig(out, dpi=110, bbox_inches="tight")
