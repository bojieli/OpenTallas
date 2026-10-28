"""DIE-HBM-10 trial2b render: plan partitions, clock tree edges (node -> parent), taps coloured by FF duty."""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
Q = "/srv/opentallas-scratch2/claude/die-hbm-10/trial2b"
P = json.load(open("/srv/opentallas-scratch2/claude/die-hbm-10/c22v/die_plan.json")); PT = P["partition_types"]
T = json.load(open(f"{Q}/kit/clock/tree.json")); D = json.load(open(f"{Q}/duty_trial2.json"))
fig, ax = plt.subplots(figsize=(22, 15))
for p in P["partitions"]:
    o = PT[p["type"]]["outline_um"]; x, y = p["origin_um"]
    ax.add_patch(plt.Rectangle((x, y), o[0], o[1], fill=PT[p["type"]].get("hard", False), fc="#eee", ec="#888", lw=0.4))
N = T["nodes"]; segs = []
for k, n in N.items():
    if n.get("parent") is not None:
        q = N[str(n["parent"])]; segs.append([(q["x"], q["y"]), (n["x"], q["y"]), (n["x"], n["y"])])
ax.add_collection(LineCollection(segs, colors="#1f77b4", lw=0.3))
# per-tap FF duty from arrival file (rise/fall arrival -> duty), via duty_eval convention: high = T/2 + (fall-rise)
arr = {}
for l in open(f"{Q}/c_FF/arr_FF.txt"):
    f = l.split()
    if len(f) >= 4 and f[0] == "F": arr[f[1]] = (float(f[2]), float(f[3]))
xs, ys, cs = [], [], []
for t in T["taps"]:
    a = arr.get(t["port"])
    if a: xs.append(t["xy"][0]); ys.append(t["xy"][1]); cs.append(100 * (0.5 + 1.0552 * (a[0] - a[1]) / 833.0))
sc = ax.scatter(xs, ys, c=cs, s=6, cmap="coolwarm", vmin=40, vmax=60)
plt.colorbar(sc, ax=ax, label="FF duty % at tap (spice x1.0552); outside 45-55 = fail")
w = [x for x in D["corners"]["FF"]["worst"][:3]]
ax.set_title(f"trial2b C22v inv2 clock-only GRT: overflow 0; TT outside45-55 {D['corners']['TT']['outside_45_55']}, FF {D['corners']['FF']['outside_45_55']}, MPW fail 0; worst FF {w[0]['port']} {w[0]['duty']}")
ax.set_xlim(0, 28400); ax.set_ylim(0, 18550); ax.set_aspect("equal")
fig.savefig(f"{Q}/trial2b_render.png", dpi=90, bbox_inches="tight")
