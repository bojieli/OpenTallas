import json, sys, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
pd = sys.argv[1]; ref = sys.argv[2]
raw = json.load(open(f"{pd}/die_plan.json")); rr = json.load(open(f"{ref}/die_plan.json"))
fig, axs = plt.subplots(1, 2, figsize=(22, 12))
for ax, (plan, d, title) in zip(axs, [(rr, ref, "c25c_d15 (before)"), (raw, pd, "d16H core_face_repin (after)")]):
    t = plan["partition_types"]["q_hub_ne"]
    for hc in t["hard_cores"]:
        x0, y0 = hc["origin_um"]; w, h = hc["outline_um"]
        if not (1500 < x0 < 4000 and 500 < y0 < 3800): continue
        ax.add_patch(plt.Rectangle((x0, y0), w, h, fill=False, lw=0.6, color="k"))
        ax.text(x0 + 3, y0 + h - 30, hc["inst"][:18], fontsize=6)
        pins = json.load(open(f"{d}/{hc['pins_file']}")); pins = pins.get("pins", pins) if isinstance(pins, dict) else pins
        o = hc.get("orient", "R0"); bycol = collections.defaultdict(list)
        for p in pins:
            x, y = p["x"], p["y"]
            if o in ("MY", "R180"): x = w - x
            if o in ("MX", "R180"): y = h - y
            nm = p.get("name", "").split("[")[0]
            bycol[nm].append((x0 + x, y0 + y))
        for i, (nm, pts) in enumerate(sorted(bycol.items())):
            if len(pts) < 2: continue
            xs, ys = zip(*pts); ax.scatter(xs, ys, s=1, color=plt.cm.tab20(hash(nm) % 20))
    ax.set_xlim(1500, 4000); ax.set_ylim(500, 3800); ax.set_aspect("equal"); ax.set_title(title)
plt.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
