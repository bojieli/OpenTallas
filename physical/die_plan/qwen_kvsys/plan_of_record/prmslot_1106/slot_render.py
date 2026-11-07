import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base, new, out = sys.argv[1:4]
B = json.load(open(base)); N = json.load(open(new))
X0, X1, Y0, Y1 = 230, 700, 300, 720
fig, ax = plt.subplots(figsize=(11, 10), dpi=130)
def pts(o, acc):
    if isinstance(o, list):
        if len(o) == 2 and all(isinstance(v, (int, float)) for v in o): acc.append(o)
        else:
            for v in o: pts(v, acc)
    elif isinstance(o, dict):
        for v in o.values(): pts(v, acc)
for h in N["hard_cores"]:
    (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
    me = h["module"] == "qkd_hr_core_prompt"
    ax.add_patch(Rectangle((ox, oy), w, hh, fc="tab:orange" if me else "lightsteelblue", alpha=0.35, ec="k", lw=1.2))
    ax.text(ox + 3, oy + 3, h["inst"].replace("host__", ""), fontsize=7, clip_on=True)
for h in B["hard_cores"]:
    if h["module"] == "qkd_hr_core_prompt":
        (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
        ax.add_patch(Rectangle((ox, oy), w, hh, fill=False, ec="tab:red", ls="--", lw=1.0, label="old prompt 233.28"))
for nm, T, c, mk in (("base", B, "grey", "x"), ("new", N, "tab:green", ".")):
    for s in T["ft_slots"]:
        a = []; pts(s.get("bit_sites_um", []), a)
        a = [q for q in a if X0 <= q[0] <= X1 and Y0 <= q[1] <= Y1]
        if a: ax.scatter([q[0] for q in a], [q[1] for q in a], s=2, c=c, marker=mk, label=f"ft bit sites {nm}" if s["name"] == "ft24" else None)
        r = [q for q in s.get("regs_um", []) if X0 <= q[0] <= X1 and Y0 <= q[1] <= Y1]
        for q in r: ax.plot(q[0], q[1], marker="D", ms=5, mfc="none", mec=c); ax.text(q[0] + 1, q[1] + 2, s["name"], fontsize=6, color=c)
for tp in N["clock"]["taps"]:
    x, y = tp["xy"]
    if X0 <= x <= X1 and Y0 <= y <= Y1: ax.plot(x, y, "b^", ms=6); ax.text(x + 2, y, tp["name"].replace("host__", ""), fontsize=6, color="b")
for tp in B["clock"]["taps"]:
    if "prompt" in tp["name"]: ax.plot(*tp["xy"], "^", mfc="none", mec="grey", ms=6)
a = []; pts(N["clock"]["landing_contract"].get("collector_tree", {}), a)
a = [q for q in a if X0 <= q[0] <= X1 and Y0 <= q[1] <= Y1]
if a: ax.scatter([q[0] for q in a], [q[1] for q in a], s=12, c="purple", marker="s", label="collector relays")
a = []; pts(N["reset"], a); a = [q for q in a if X0 <= q[0] <= X1 and Y0 <= q[1] <= Y1]
if a: ax.scatter([q[0] for q in a], [q[1] for q in a], s=12, c="brown", marker="*", label="reset sites")
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title("KV kv3_hub_Wi type frame: qkd_hr_core_prompt 233.28 -> 254.88 (origin 319.68,380.16 fixed)\nKV-PRMSLOT-1 11-06; ft24 station 3 +8.64 E", fontsize=9)
ax.legend(fontsize=7, loc="upper left")
fig.savefig(out, bbox_inches="tight")
