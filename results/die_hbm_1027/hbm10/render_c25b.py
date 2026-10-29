import json, sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); T = P["partition_types"]; out = sys.argv[2]
NEW = {"u_mu_fused_root", "u_mu_fused_program", "u_host_cp_rxs", "u_hb_dbk_Q__q0", "u_hb_dbk_Q__q1", "u_mu_fused_n4"}
views = [("root", (0, 4800, 1684.8, 6400), "root: fused root/programme + n4x stations"),
         ("root", (0, 300, 1100, 1200), "root: host_cp_rxs 480 high"),
         ("q_hub_nw", (2700, 600, 7500, 1300), "q_hub_nw: vp4_banks_cp q0/q1 275.4 high"),
         ("q_hub_nw", (4600, 3300, 8460, 4100), "q_hub_nw: n4 <-> E face n4x stations")]
fig, axs = plt.subplots(2, 2, figsize=(22, 18))
for ax, (tn, (x0, y0, x1, y1), title) in zip(axs.flat, views):
    t = T[tn]
    for c in t["hard_cores"]:
        dx, dy = c.get("track_offset_um", [0, 0]); x, y = c["origin_um"][0] + dx, c["origin_um"][1] + dy
        w, h = c["outline_um"]
        if x > x1 or x + w < x0 or y > y1 or y + h < y0: continue
        new = c["inst"] in NEW
        ax.add_patch(Rectangle((x, y), w, h, fill=True, alpha=0.35 if new else 0.15, fc="tab:red" if new else "tab:blue",
                               ec="k", lw=1.2 if new else 0.5))
        ax.text(x + w / 2, y + h / 2, c["inst"].replace("u_", "")[:22], fontsize=7, ha="center", va="center")
    for st in t.get("internal_stations", []):
        if "n4x" not in st.get("conn", "") and "host_cp_rxs" not in json.dumps(st): continue
        pts = [st["from_um"]] + st["regs_um"] + [st["to_um"]]
        col = "tab:green" if "n4x" in st["conn"] else "tab:orange"
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=col, lw=0.8)
        ax.plot([p[0] for p in st["regs_um"]], [p[1] for p in st["regs_um"]], "s", color=col, ms=4)
    for tp in t["clock"]["taps"]:
        if tp["name"].split(".")[0] in NEW and x0 <= tp["xy"][0] <= x1 and y0 <= tp["xy"][1] <= y1:
            ax.plot(*tp["xy"], "k+", ms=10)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_title(title)
fig.tight_layout(); fig.savefig(out, dpi=80)
