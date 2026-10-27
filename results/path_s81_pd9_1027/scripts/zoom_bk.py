import json, sys
sys.path.insert(0, sys.argv[4])
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S, die_clock as DCM
d, out, plan = sys.argv[1], sys.argv[2], sys.argv[3]
M = json.load(open(d + "/mesh.json")); P = json.load(open(d + "/place.json")); N = json.load(open(d + "/nets.json"))["nets"]
raw = json.load(open(plan)); raw.pop("plan_deltas", None); PL = S.Plan(raw)
x0, x1, y0, y1 = 15600, 18400, 21900, 23700
fig, ax = plt.subplots(figsize=(14, 9))
ko = DCM.keepouts(PL)
for r in ko:
    if r[2] > x0 and r[0] < x1 and r[3] > y0 and r[1] < y1:
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#f3d9a4", ec="#a07020", lw=0.6))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, str(r[4]).split("/")[-1][-22:], fontsize=6, ha="center")
for y in M["ys"]:
    if y0 <= y <= y1: ax.axhline(y, color="#58a", lw=0.8)
for x in M["xs"]:
    if x0 <= x <= x1: ax.axvline(x, color="#58a", lw=0.8)
inwin = lambda q: x0 - 50 <= q["x"] <= x1 + 50 and y0 - 50 <= q["y"] <= y1 + 50
for n in N:
    a = P.get(n["drv"])
    if a is None: continue
    for l in n["loads"]:
        b = P.get(l)
        if b is None or not (inwin(a) or inwin(b)): continue
        if b.get("kind") == "stub" or a.get("kind") == "stub": continue
        ax.plot([a["x"], a["x"], b["x"]], [a["y"], b["y"], b["y"]], color="r", lw=1.0)
for nm, c in P.items():
    if not inwin(c): continue
    k = c.get("kind")
    sty = {"drv": ("bs", 5), "node": ("r^", 6), "rep": ("kD", 6)}.get(k)
    if sty: ax.plot(c["x"], c["y"], sty[0], ms=sty[1])
    if nm.startswith("ckm_r9_h110101011") or nm.startswith("ckm_n9_h110101011") or nm.startswith("ckm_n8_h11010101"):
        ax.annotate(nm, (c["x"], c["y"]), fontsize=7, xytext=(4, -10), textcoords="offset points")
for dd in M.get("dropped_drivers", []):
    ax.plot(*dd["ideal"], "mx", ms=14, mew=3)
    ax.annotate(dd["name"] + " DROPPED", dd["ideal"], fontsize=8, color="m", xytext=(6, 6), textcoords="offset points")
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
ax.set_title("PATH-S81-PD9 me1 bk_sel: hard cores (tan), mesh straps (blue), tree legs (red), drivers (blue sq), nodes (red tri), leg reps (black diamond); magenta X = dropped row-60 drivers", fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=110); print(out)
