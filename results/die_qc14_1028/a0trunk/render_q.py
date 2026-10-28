# DIE-QC-14: render the planned A0 trunk (macros, ICG, inverter legs, sinks); usage render_q.py trunk.json cl.json out.png
import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
T = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2]))
fig, ax = plt.subplots(figsize=(7, 16)); ax.set_xlim(0, G["W"]); ax.set_ylim(0, G["H"]); ax.set_aspect("equal")
for m in G["macros"]:
    ax.add_patch(Rectangle((m[0], m[1]), m[2]-m[0], m[3]-m[1], fc="#ddd", ec="#888", lw=0.5))
def walk(nd):
    if nd["kind"] != "merge": return
    for kid, lg in zip(nd["kids"], nd["legs"]):
        xs = [p[0] for p in lg["pts"]]; ys = [p[1] for p in lg["pts"]]
        el = lg["wire"] - (abs(nd["p"][0]-kid["p"][0]) + abs(nd["p"][1]-kid["p"][1])) > 0.5
        ax.plot(xs, ys, "-", color="#d62728" if el else "#1f77b4", lw=0.8)
        ax.plot(xs[1:-1], ys[1:-1], "o", ms=1.8, color="k")
        walk(kid)
    ax.plot(*nd["p"], "s", ms=2.5, color="purple")
walk(T["tree"])
rl = T["root_leg"]; ax.plot([p[0] for p in rl], [p[1] for p in rl], "-", color="green", lw=1.2)
for s in T["sinks"]:
    ax.plot(*s["p"], "^" if s["kind"] == "child" else ".", ms=4, color="orange" if s["kind"] == "child" else "teal")
ax.plot(*T["summary"]["icg"]["site"], "*", ms=10, color="red")
sm = T["summary"]
ax.set_title("A0 nk trunk %s: %d INV, %.1f mm, elongation %.0f um on %d legs\nred = elongated leg, blue = straight, green = root leg, star = ICG, ^ = child pin"
             % (sys.argv[1].split("/")[-1], sm["n_inv"], sm["trunk_wire_um"]/1000, sm["elongation_um"], sm["elongated_legs"]), fontsize=8)
fig.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
