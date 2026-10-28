#!/usr/bin/env python3
"""DIE-HEAD-5 (COORD 10-28 01:2x, DRT-TRIAL-1 HOLD -875 ps root cause): hd_tile core clock taps become EARLY core taps
(clock.core_taps = "early", 12.3 v5.0 macro insertion-delay balancing from the core's own SIGNED view) with the
signed capsules' measured routed pin-register MEAN insertion at the clock port (signoff.json core_latency.measured,
contract hard_core_latency, clock_port ft_mstrap_i): insertion_ps = TT mean, insertion_ff_ps = FF mean.

Root cause it removes: the plan said 'INSERTION PENDING' 250 and declared no early taps, so the kit took the OLD view's
legacy ETM max_clock_tree_path bound (415.63 elemA / 378.76 elemB, core_latency.txt basis legacy_etm_max_bound) and
CTS balanced the tile registers up to it behind the tile tree (706-743 ps FF vs the 202.5 target).

    head_plan_coretaps_signed.py PLAN.json [PLAN2.json ...] --capsules DIR   (in place; DIR/<elemA|elemB>_signed/signoff.json)
"""
import argparse
import json
from pathlib import Path

MOD = {"ot_s81hd_elemA_cv": "elemA", "ot_s81hd_elemB_cv": "elemB"}


def means(cap, name):
    s = json.loads((Path(cap) / f"{name}_signed" / "signoff.json").read_text())
    assert s["verdict"] == "SIGNED", (name, s["verdict"])
    c = s["core_latency"]
    assert c["contract"]["kind"] == "hard_core_latency" and c["contract"]["clock_port"] == "ft_mstrap_i", c["contract"]
    return round(c["measured"]["tt"]["mean"], 2), round(c["measured"]["ff"]["mean"], 2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--capsules", required=True)
    a = ap.parse_args(argv)
    m = {k: means(a.capsules, v) for k, v in MOD.items()}
    for f in a.plans:
        txt = Path(f).read_text()
        ind = 2 if txt.startswith('{\n  "') else 1
        p = json.loads(txt)
        t = p["partition_types"]["hd_tile"]
        ck = t["clock"]
        cores = {c["inst"]: c["module"] for c in t["hard_cores"]}
        rows = []
        for tp in ck["taps"]:
            if tp.get("kind") != "core":
                continue
            inst = tp["name"].rsplit(".", 1)[0]
            tt, ff = m[cores[inst]]
            tp.update(insertion_ps=tt, insertion_ff_ps=ff,
                      budget_owner=f"SIGNED capsule {MOD[cores[inst]]}_signed signoff.json core_latency.measured "
                                      "pin-register mean at ft_mstrap_i (results/head_core_clockfreeze_release)",
                      note="DIE-HEAD-5: early core tap (12.3 v5.0) at the signed view's measured mean insertion; "
                           "die tree delivers it max(0, insertion - common latency) early")
            rows.append((tp["name"], tt, ff))
        ck["core_taps"] = "early"
        Path(f).write_text(json.dumps(p, indent=ind) + "\n")
        print(f, rows)


if __name__ == "__main__":
    main()
