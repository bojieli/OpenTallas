#!/usr/bin/env python3
# KV-P6-SPINE 10-23: python3 g2_columns_v37s.py PLAN.json TOOLS_DIR BIN_UM Y1,Y2,... (run from the plan dir)
"""column bits probe: at horizontal cuts, bits of vertical lane runs per x-bin and per partition segment (G0 cut model)."""
import json, sys, collections
sys.path.insert(0, sys.argv[2])
import check, schema as S
P = S.Plan(json.load(open(sys.argv[1])))
geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
segs = []
for lid, (pts, _, _) in geo.items():
    w = P.ports[P.lanes[lid]["ports"][0]]["width"]
    for p, q in zip(pts, pts[1:]):
        if abs(p[0]-q[0]) < 1e-6 and abs(p[1]-q[1]) > 1e-6:
            segs.append((p[0], min(p[1], q[1]), max(p[1], q[1]), w, lid))
BIN = float(sys.argv[3]) if len(sys.argv) > 3 else 400.0
pden = check.track_density(P, check.PART_FT_LAYERS["V"], check.FT_TRACK_FRAC)
avail = P.layer_budget.get("cut_avail", {})
die_den = sum(avail.get(n, 0)/P.layers[n]["pitch_um"] for n in P.layer_budget["die_layers"] if P.layers[n]["dir"] == "V")
rects = {n: P.rect(n) for n in P.parts}
out = {}
worst = (0, None)
for y in [float(v) for v in sys.argv[4].split(",")]:
    bins = collections.Counter()
    hit = [(x, w) for x, a, b, w, l in segs if a < y < b]
    for x, w in hit:
        bins[int(x // BIN) * BIN] += w
    tot = sum(w for _, w in hit)
    parts = []
    for pn, r in rects.items():
        if r[1] < y < r[3]:
            sb = sum(w for x, w in hit if r[0] - 1e-6 <= x <= r[2] + 1e-6)
            cap = (r[2] - r[0]) * (pden + die_den)
            if sb:
                parts.append((round(sb / cap, 4), pn, sb, round(cap)))
                worst = max(worst, (sb / cap, f"y{y:g}:{pn}"))
    parts.sort(reverse=True)
    mx = max(bins.values()) if bins else 0
    out[f"{y:g}"] = dict(total_bits=tot, max_bin_bits=mx, max_bin_share=round(mx / tot, 3) if tot else 0,
                         bins={f"{k:.0f}": v for k, v in sorted(bins.items())}, worst_parts=parts[:4])
out["worst_partition_segment"] = dict(ratio=round(worst[0], 4), at=worst[1])
out["model"] = dict(bin_um=BIN, ft_track_density_per_um=round(pden, 3), die_den=round(die_den, 3))
json.dump(out, sys.stdout, indent=1)
