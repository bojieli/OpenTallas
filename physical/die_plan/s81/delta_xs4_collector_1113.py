#!/usr/bin/env python3
"""S81 plan event XS4-CORE, stage 3 (HARD-S81-DSDV-1 11-13): after the row re-layout (delta_xs4_core_1113.py) and the reach
stage (reach_fix.py fix --classes 1,2,3,4,5) the reset tree of each C type is solved again from the new taps and
published to the plan landing contract AND the landing sidecar (collector sources / children re-pick their nearest tap:
plan_event_1104.publish_tree, the xfin event form).

    python3 physical/die_plan/s81/delta_xs4_collector_1113.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT      (cwd = repo root)
"""
import gzip, json, re, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import schema as S, reset_tree as RT
from plan_event_1104 import plan_text, publish_tree


def main():
    src, out, side_src, side_out = sys.argv[1:5]
    rd = lambda f: json.loads(gzip.decompress(Path(f).read_bytes()) if f.endswith(".gz") else Path(f).read_text())
    P, T = rd(src), rd(side_src)
    Pn = S.Plan(S.load(src), src)
    report = {}
    for tn in sorted(P["partition_types"]):
        t = P["partition_types"][tn]
        if not re.match(r"dsdv_slice_\w+_C__t\d+$", tn) or not any(c.get("module") == "ot_s81sl_xs4" for c in t.get("hard_cores") or []):
            continue
        lc = t["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(tn) or {}
        tree = json.loads(json.dumps(RT.for_type(Pn, tn)))
        old = lc.get("collector_tree") or st.get("tree")
        rep = report[tn] = dict(reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])])
        publish_tree(lc, st, tree, rep)
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
