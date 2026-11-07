import json, re, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); sites = open(sys.argv[2]).read()
L = [34.572, 354.252, 725.772, 1045.452]
col = {"x_ctl_o": "tab:blue", "x_sc_o": "tab:purple", "x_stm_o": "tab:green", "x_su_c_o": "tab:orange", "x_su_c_p1_o": "tab:red"}
fig, ax = plt.subplots(1, 2, figsize=(13, 14))
for a, title in zip(ax, ["before: lane pin -> port straight (crossing bits, flop free)", "vE: pin -> mouth site -> port"]):
    a.add_patch(Rectangle((0, 0), 622.08, 1339.2, fill=False, lw=1))
    for k, y in enumerate(L):
        a.add_patch(Rectangle((190.092, y), 414.72, 267.84, color="0.85")); a.text(397, y + 130, f"lane{k}", ha="center")
    a.set_xlim(-10, 632); a.set_ylim(-10, 1350); a.set_aspect("equal"); a.set_title(title, fontsize=10)
for B, qb, i, x, y, s, P, b, aft in d["bits"]:
    if not b: continue
    c = col[B]
    ax[0].plot([x, P[0]], [y, P[1]], color=c, lw=0.3, alpha=0.5)
    if s:
        ax[1].plot([x, s[0]], [y, s[1]], color=c, lw=0.3, alpha=0.5)
        ax[1].plot([s[0], s[0], P[0]], [s[1], P[1], P[1]], color=c, lw=0.3, alpha=0.3)
bins = [tuple(map(float, m.group(1).split())) for m in re.finditer(r"u_bin_\S+\} \{([\d. ]+)\}", sites)]
ax[1].scatter([p[0] for p in bins], [p[1] for p in bins], s=1, c="0.4", label="bin replicas (vC sites)")
for B, c in col.items():
    pts = [bb[5] for bb in d["bits"] if bb[0] == B and bb[5]]
    ax[1].scatter([p[0] for p in pts], [p[1] for p in pts], s=2, c=c, label=f"u_bout_{B} ({len(pts)})")
ax[1].legend(loc="upper right", fontsize=7, markerscale=4)
fig.suptitle("DQ85-SUL0 vE slw_su_l0__cl76fb247e: lane-fed bout bits FIRM at the source lane channel mouth (x 186.5)", fontsize=11)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=110)
