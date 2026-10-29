#!/usr/bin/env python3
"""HBM-CORES-KITS-7 estimate (12.14 estimate-before-build): GQ q1 -> ring_ag q1 transport.

Option R (paired-lot relocation): move u_hb_coll_Q_ring_ag__q1 next to the GQ east face, 0 cycles.
Option P (explicit pipeline event): keep the slots, register every GQ->ring ra_* bit N times (coherent), +N cycles a
ring record.

usage: gq_ring_transport_estimate.py DIE_PLAN_JSON CODEX_PAIR_ESTIMATE_JSON CODEX_Q1_ENDPOINTS_JSON REPO_ROOT OUT_JSON
Plan-level numbers only (planned station from/to points, plan outlines); the actual-pin reach comes from the Codex
packet (gq_q1_direct_endpoints.json / gq_ring_pair_estimate.json). No physical claim.
"""
import collections
import json
import math
import sys

plan_p, pair_p, ends_p, repo, out_p = sys.argv[1:6]
REACH, HOP_PLAN, CLR, W = 405.0, 360.0, 4.32, 233.28
RING_OLD = (5641.92, 2419.2)
CANDS = {"q_hub_nw": (4527.36, 2626.56), "q_hub_ne": (4544.64, 2540.16)}
P = json.load(open(plan_p))
res = dict(plan=plan_p, reach_um=REACH, hops_rule_um=HOP_PLAN, hubs={})


def overlap(h, x0, y0):
    (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
    return ox < x0 + W + CLR and ox + w > x0 - CLR and oy < y0 + W + CLR and oy + hh > y0 - CLR


for tn in ("q_hub_nw", "q_hub_ne"):
    t = P["partition_types"][tn]
    hc = [h for h in t["hard_cores"] if h["inst"] != "u_hb_coll_Q_ring_ag__q1"]
    row = {}
    for cname, (x0, y0) in [("codex_best", CANDS[tn]), ("nw_slot", CANDS["q_hub_nw"])]:
        dx, dy = x0 - RING_OLD[0], y0 - RING_OLD[1]
        hits = [h["inst"] for h in hc if overlap(h, x0, y0)]
        legs = collections.defaultdict(lambda: dict(bits=0, old=0.0, new=0.0, plan_regs=0))
        for s in t["internal_stations"]:
            c = s["conn"]
            if "ring_ag" not in c or s.get("r9_segments") != [1, 1]:
                continue
            f, to = s["from_um"], s["to_um"]
            inr = lambda p: RING_OLD[0] - 1 <= p[0] <= RING_OLD[0] + W + 1 and RING_OLD[1] - 1 <= p[1] <= RING_OLD[1] + W + 1
            if inr(f):
                r, o = f, to
            elif inr(to):
                r, o = to, f
            else:
                continue
            a, b = c.split("|")
            other = (b if "ring_ag" in a else a).split(".")[0]
            g = legs[other]
            g["bits"] += s["bits"]
            g["old"] = max(g["old"], abs(r[0] - o[0]) + abs(r[1] - o[1]))
            g["new"] = max(g["new"], abs(r[0] + dx - o[0]) + abs(r[1] + dy - o[1]))
            g["plan_regs"] = max(g["plan_regs"], len(s["regs_um"]))
        for g in legs.values():
            g.update(old=round(g["old"], 1), new=round(g["new"], 1), hops405_old=math.ceil(g["old"] / REACH),
                     hops405_new=math.ceil(g["new"] / REACH))
        row[cname] = dict(origin_um=[x0, y0], hard_collisions_4p32=hits, ring_legs_plan_points=dict(legs))
    res["hubs"][tn] = row

pair = json.load(open(pair_p))
res["codex_actual_pin_reach"] = {r["type"]: dict(best=r["best"][0]["origin_um"], max_um=r["best"][0]["max_direct_reach_um"],
                                                 station_centres_inside=len(r["best"][0]["station_centres_inside"]),
                                                 bus_stations=sorted({x[2] for x in r["best"][0]["station_centres_inside"]
                                                                      if x[2].startswith("bus:")}))
                                 for r in pair["rows"]}
ends = json.load(open(ends_p))
lmax, lmin = ends["new_max_um"], ends["new_min_um"]
res["pipeline_regs_q1"] = dict(direct_min_um=lmin, direct_max_um=lmax, regs_at_405=math.ceil(lmax / REACH) - 1,
                               regs_at_360=math.ceil(lmax / HOP_PLAN) - 1)

sys.path.insert(0, repo + "/tools/throughput")
import accepted_cost as A  # noqa: E402

price = {}
for m in ("ds", "qwen"):
    run, count = A.hbm_schedule(m)
    base = run()
    for n in (1, 3, 4, 8):
        r = A.hbm_loss(run, count, "COLL.*", None, base=base, delta=n)
        price[f"{m}_N{n}"] = dict(records=r["program_records"], added_cycles=r["added_cycles"], loss_pct=r["e2e_loss_pct"],
                                  at_1906=round(1905.97 * (1 - r["e2e_loss_pct"] / 100), 1) if m == "ds" else None)
res["pipeline_price_S2_COLL_all"] = price
json.dump(res, open(out_p, "w"), indent=1)
print(json.dumps(res, indent=1))
