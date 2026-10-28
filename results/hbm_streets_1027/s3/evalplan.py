"""HBM-STREETS-3: street evaluation of a plan (per-street demand) + optional zoom renders + probes.
usage: evalplan.py REPO plan.json out_prefix '{"zoom": [[x0,y0,x1,y1],...], "probe": [[x,y],...]}'"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import check, schema as S, die_clock as DC, streets as ST
import numpy as np
plan = Path(sys.argv[2]); pre = sys.argv[3]; spec = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
raw = S.load(str(plan))
P = S.Plan(raw, plan)
ko = DC.keepouts(P)
cfg = ST.config(P.die.get("streets"))
geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
flows = [(lid, int(P.ports[P.lanes[lid]["ports"][0]]["width"]), [tuple(q) for q in g[0]]) for lid, g in geo.items()] + check.channel_flows(P)
pts = [(f"{lid}#{k}", tuple(xy), "lane_station") for lid, g in geo.items() for k, xy in enumerate(g[1] if len(g) > 1 else [])]
A = ST.analyze(float(P.W), float(P.H), ko, cfg, [], [], [], flows=flows)
over = [c for c in A["cores"] if c["street_dist_um"] is None or c["street_dist_um"] > cfg["reach_um"] + 1e-6]
for c in over:
    print("OVER", c["name"], c["street_dist_um"], c["rect_um"])
print("TOTAL over", len(over), "of", len(A["cores"]), "pockets", A["streets"]["pockets"], A["streets"]["pocket_area_mm2"])
gg = cfg["raster_um"]
occ = ST.raster(float(P.W), float(P.H), ko, gg); free = ~occ
ry, rx = ST.demand(free, gg, flows, cfg)
RY, RX = ST._runs(free, 0) * gg, ST._runs(free, 1) * gg
net = A["net"]
for x, y in spec.get("probe", []):
    i, j = int(x // gg), int(y // gg)
    print("probe", (x, y), "free", bool(free[j, i]), "net", bool(net[j, i]), "req_ew", round(float(ry[j, i]), 2), "run_y", round(float(RY[j, i]), 2),
          "req_ns", round(float(rx[j, i]), 2), "run_x", round(float(RX[j, i]), 2))
if spec.get("zoom"):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    for zi, (x0, y0, x1, y1) in enumerate(spec["zoom"]):
        fig, ax = plt.subplots(figsize=(12, 12 * (y1 - y0) / (x1 - x0) + 0.8))
        ax.imshow(np.where(net, 1.0, np.where(free, 0.5, 0.0)), origin="lower", extent=(0, P.W, 0, P.H), cmap="Greens", vmin=0, vmax=1.3, interpolation="nearest")
        oset = {c["name"] for c in over}
        for r in ko:
            if r[2] < x0 or r[0] > x1 or r[3] < y0 or r[1] > y1:
                continue
            col = "red" if r[4] in oset else ("slateblue" if ST.is_phy(r[4]) else "grey")
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec="k", lw=.5, alpha=.8))
            if r[2] - r[0] > (x1 - x0) / 25:
                ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, str(r[4]).split("/")[-1][:18], fontsize=6, ha="center", va="center")
        for p in raw["partitions"]:
            w, h = raw["partition_types"][p["type"]]["outline_um"]; o = p["origin_um"]
            if o[0] > x1 or o[0] + w < x0 or o[1] > y1 or o[1] + h < y0:
                continue
            ax.add_patch(Rectangle(o, w, h, fill=False, ec="blue", lw=.8, ls="--"))
            ax.text(o[0] + 10, o[1] + 10, p["name"], fontsize=7, color="blue")
        for name, p, kind in pts:
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                ax.plot(p[0], p[1], "x", color="m", ms=4)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        ax.set_title(f"{plan.parent.name} zoom {zi}: dark green = street net, light = free pocket/narrow, red = over reach, x = lane stations")
        fig.savefig(f"{pre}_zoom{zi}.png", dpi=90, bbox_inches="tight"); plt.close(fig)
json.dump(dict(over=over, streets={k: v for k, v in A["streets"].items()}), open(pre + "_eval.json", "w"), indent=1, default=str)
