#!/usr/bin/env python3
"""KV-G3 10-24: hub_Ei fault-leg internal stations re-spaced to the implemented M4-M7 reach (405 um; Codex reach405
sizes every ft slot to <= 396.9 um).  v3.8v spaced them at <= 675 um (3 on i_dcal_flt, hop 556; 2 on i_hp_fault_N_q,
hop 504): vI placement shows those hops as the only ff->ff legs > 400 um (558 max).  Now ceil(L / HOP) - 1 stations
on the same L paths: i_dcal_flt 2226 um -> 5 (hop 371), i_hp_fault_N_q 1513 um -> 3 (hop 378); lanes L357 / L758
fixed_cycles += the added stations (fault age).   usage: post_v38y.py die_plan.json > die_plan.json"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post_v38v import stations  # noqa: E402

HOP = 400.0
LANES = {"bus:i_dcal_flt": "L357", "bus:i_hp_fault_N_q": "L758"}


def main():
    p = json.load(open(sys.argv[1]))
    t = p["partition_types"]["kv3_hub_Ei"]
    for e in t["internal_stations"]:
        if e.get("conn") not in LANES:
            continue
        pts = [e["from_um"]] + [e["to_um"]]
        # the v3.8v L path: from -> corner -> to (corner shared by both legs: x of from, y of to / or the jog)
        corner = [e["from_um"][0], e["to_um"][1]] if e["conn"] == "bus:i_dcal_flt" else [e["to_um"][0], e["from_um"][1]]
        pts = [e["from_um"], corner, e["to_um"]]
        L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
        n = math.ceil(L / HOP) - 1
        old = len(e["regs_um"])
        regs, L, h = stations(pts, n)
        e["regs_um"] = regs
        e["note"] = f"KV-G3 v3.8y R3-INTERNAL FIRM (plan cell): path {L:.0f} um, {n} stations, hop {h:.0f} <= {HOP:g}"
        ln = next(x for x in p["lanes"] if x["id"] == LANES[e["conn"]])
        ln["fixed_cycles"] = ln.get("fixed_cycles", 0) + n - old
        ln["note"] = ln.get("note", "") + f" | v3.8y +{n - old} (hub_Ei fault-leg stations at <= {HOP:g} um)"
        sys.stderr.write(f"{e['conn']}: {old} -> {n} stations, hop {h:.0f}\n")
    p["note"] = p.get("note", "") + " | v3.8y (KV-G3): hub_Ei fault-leg stations at <= 400 um"
    json.dump(p, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
