#!/usr/bin/env python3
"""PATH-S81-PD6 clock diagnostics on the converted tap arrivals: region-root arrival spread, per-region tap spread,
per-partition tap spread, leaf->tap leg delay, root->region-root path. Usage: pd6_clock_diag_1026.py PROOF TREE OUT"""
import json
import sys
from collections import defaultdict


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100 * len(v)))]


def main(proof, tree_p, out):
    T = json.load(open(tree_p))
    nodes = {int(k): v for k, v in T["nodes"].items()}
    res = {}
    for C in ("TT", "FF"):
        A = json.load(open(f"{proof}/tap_arrivals_{C}.json"))
        nl = A["node_late_ps"]
        taps = A["taps"]
        # region roots
        rr = {}
        for t in taps:
            rr[t["region"]] = t["cppr_node"]
        rarr = {r: nl[p] for r, p in rr.items()}
        reg_taps, part_taps = defaultdict(list), defaultdict(list)
        legs = []
        for t in taps:
            reg_taps[t["region"]].append(t["late_ps"])
            part_taps[t["part"]].append(t)
            legs.append(t["late_ps"] - nl[t["tree_path"]])
        rspread = {r: max(v) - min(v) for r, v in reg_taps.items()}
        rbelow = {r: (min(v) - rarr[r], max(v) - rarr[r]) for r, v in reg_taps.items()}
        pspread = {}
        for p, tl in part_taps.items():
            v = [t["late_ps"] for t in tl]
            pspread[p] = (max(v) - min(v), len(tl), len(set(t["region"] for t in tl)))
        # depth of region trees (stages below region root)
        st = A["node_stages"]
        rdepth = {}
        for t in taps:
            rdepth.setdefault(t["region"], set()).add(t["stages_from_root"] - st[t["cppr_node"]])
        r = dict(
            region_root_arrival=dict(min=round(min(rarr.values()), 1), max=round(max(rarr.values()), 1),
                                     spread=round(max(rarr.values()) - min(rarr.values()), 1),
                                     p10=round(q(list(rarr.values()), 10), 1), p90=round(q(list(rarr.values()), 90), 1)),
            region_root_worst5_late=sorted(((round(v, 1), k) for k, v in rarr.items()), reverse=True)[:5],
            region_root_worst5_early=sorted(((round(v, 1), k) for k, v in rarr.items()))[:5],
            region_tree_below_root_ps=dict(min=round(min(b[0] for b in rbelow.values()), 1),
                                           max=round(max(b[1] for b in rbelow.values()), 1)),
            region_tap_spread=dict(p50=round(q(list(rspread.values()), 50), 1), p90=round(q(list(rspread.values()), 90), 1),
                                   max=round(max(rspread.values()), 1),
                                   worst5=sorted(((round(v, 1), k) for k, v in rspread.items()), reverse=True)[:5],
                                   over_80=sum(1 for v in rspread.values() if v > 80)),
            region_stage_depths_below_root={k: sorted(v) for k, v in sorted(rdepth.items(), key=lambda kv: -len(kv[1]))[:8]},
            part_tap_spread=dict(p50=round(q([v[0] for v in pspread.values()], 50), 1),
                                 p90=round(q([v[0] for v in pspread.values()], 90), 1),
                                 max=round(max(v[0] for v in pspread.values()), 1),
                                 over_80=sum(1 for v in pspread.values() if v[0] > 80),
                                 worst8=sorted(((round(v[0], 1), k, v[1], v[2]) for k, v in pspread.items()), reverse=True)[:8]),
            leaf_to_tap_leg_ps=dict(p50=round(q(legs, 50), 1), p90=round(q(legs, 90), 1), max=round(max(legs), 1)),
            tap_slew_ps=dict(p50=round(q([t["slew_ps"] for t in taps], 50), 1), max=round(max(t["slew_ps"] for t in taps), 1)),
        )
        res[C] = r
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1)[:6000])


if __name__ == "__main__":
    main(*sys.argv[1:4])
