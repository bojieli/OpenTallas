#!/usr/bin/env python3
"""QC-EVENT-S25: worst writer_start hop per branch (origin -> stage 0 ... last stage -> cland_fstart_out face pin), as
landing_place places the chain (origin-anchored, core-clear relocation), on every type of a plan.
usage: wstart_hops.py TOOLS_DIE_PLAN PLAN.json [LIMIT]  -> rows over LIMIT (default 405) + a summary line"""
import json, sys
sys.path.insert(0, sys.argv[1])
import landing_place as LP
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
P = json.load(open(sys.argv[2])); LIM = float(sys.argv[3]) if len(sys.argv) > 3 else 405.0
n = bad = 0; worst = (0, None)
for tn, t in sorted(P["partition_types"].items()):
    ws = (t.get("clock") or {}).get("landing_writer_start")
    if not ws:
        continue
    o = LP._start_origin_xy(t)
    if o is None:
        continue
    pins = {p["name"]: tuple(p["xy_um"]) for p in t["clock"]["landing_contract"]["pins"]}
    for bus, br in sorted(ws["branches"].items()):
        cs = [LP._centre(r) for r in LP._chain_clear_of_hard_cores(t, o, br["stages"])]
        face = pins.get("cland_fstart_out_" + bus)
        hops = [md(o, cs[0])] + [md(p, q) for p, q in zip(cs, cs[1:])] + ([md(cs[-1], face)] if face else [])
        n += 1
        if max(hops) > worst[0]:
            worst = (max(hops), f"{tn}.{bus}")
        if max(hops) > LIM:
            bad += 1
            print(f"OVER {tn} {bus} depth {len(br['stages'])} max_hop {max(hops):.1f} hops {[round(h) for h in hops]}")
print(f"SUMMARY branches {n} over_{LIM:g} {bad} worst {worst[0]:.1f} {worst[1]}")
