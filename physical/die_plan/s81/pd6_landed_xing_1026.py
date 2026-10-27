#!/usr/bin/env python3
"""PATH-S81-PD6: landed crossings (cross-region connected partition pairs) vs the plan landing window T/2:
per crossing worst clock damage over all tap pairs (die_sta_related plan_landing form, CPPR at the LCA, no OCV) and
the mean-tap form (FALLBACK-S81 land_report form).  Usage: PROOF PLAN OUT"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import die_sta_related as D  # noqa: E402

W = 833.333 / 2


def main(proof, plan_p, out):
    D.CPPR_LCA = True
    plan = json.load(open(plan_p))
    res = {}
    for c in ("TT", "FF"):
        meta, taps = D.load_taps(Path(proof), c)
        rng = meta["cppr_node_range_ps"]
        nl = meta["node_late_ps"]
        pairs, _ = D.build_pairs(plan, taps)
        xs = defaultdict(lambda: [0.0, None, 0.0, 0.0])
        bypart = defaultdict(list)
        for p, r in taps.items():
            bypart[r["part"]].append(r)
        for x, y, tag in pairs["landed"]:
            A, B = taps[x], taps[y]
            cr = D.credit(rng, D.pair_node(A, B), A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"])
            d = max(A["late_ps"] - B["early_ps"] - cr, B["late_ps"] - A["early_ps"] - cr)
            if d > xs[tag][0]:
                xs[tag][0] = d
                xs[tag][1] = (x, y)
                xs[tag][2] = nl[A["cppr_node"]] - nl[B["cppr_node"]]
                xs[tag][3] = (A["late_ps"] - nl[A["cppr_node"]]) - (B["late_ps"] - nl[B["cppr_node"]])
        mean = {}
        for tag in xs:
            s, t = tag.split("->")
            ms = sum(r["late_ps"] for r in bypart[s]) / len(bypart[s])
            mt = sum(r["late_ps"] for r in bypart[t]) / len(bypart[t])
            mean[tag] = abs(ms - mt)
        fail = {k: v for k, v in xs.items() if v[0] > W}
        mfail = {k: v for k, v in mean.items() if v > W}
        root_dom = sum(1 for v in fail.values() if abs(v[2]) >= abs(v[3]))
        res[c] = dict(window_ps=round(W, 2), crossings=len(xs), fail_worst_tap=len(fail), fail_mean_tap=len(mfail),
                      fail_root_arrival_dominated=root_dom, fail_region_tree_dominated=len(fail) - root_dom,
                      damage_max_ps=round(max(v[0] for v in xs.values()), 1),
                      mean_tap_max_ps=round(max(mean.values()), 1),
                      worst10=[dict(crossing=k, damage_ps=round(v[0], 1), d_root_ps=round(v[2], 1), d_tree_ps=round(v[3], 1))
                               for k, v in sorted(xs.items(), key=lambda kv: -kv[1][0])[:10]])
        print(c, {k: v for k, v in res[c].items() if k != "worst10"})
        for w in res[c]["worst10"][:5]:
            print("   ", w)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
