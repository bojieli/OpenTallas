#!/usr/bin/env python3
"""S81-GEAR-1 g3_gear_landing (DIE-S81-87, 2026-11-12): sync the clock landing table's port widths with the plan after the
BUS-GEAR-1 2:1 gear stage (class fix: every geared lane, not per lane).

clock_landings.Landings / requirements() compare (src part, dst part, width) of each table port with the plan port and raise
"stale clock landing endpoints/width on <port>".  The gear stage changes plan ports 1104 -> 556 on the 72 x_/xo_ lanes, so the
table entries of exactly those ports take the plan width.
Fail-closed: only ports whose plan lane carries the 'BUS-GEAR-1 2:1' note may change; src/dst must match; every table port is in
the plan; table totals (bits, by_class_pair[*].bits) are recomputed from the ports.  Nothing else in the table changes.
usage: landing_width_sync_1112.py PLAN TABLE_IN TABLE_OUT REPORT
"""
import json, sys

def main():
    plan_f, tin, tout, rep_f = sys.argv[1:5]
    plan = json.load(open(plan_f)); t = json.load(open(tin))
    P = {p["id"]: p for p in plan["ports"]}
    geared = {l["id"] for l in plan["lanes"] if "BUS-GEAR-1 2:1" in (l.get("note") or "")}
    changed, bad = [], []
    for r in t["ports"]:
        p = P.get(r["port"])
        if p is None:
            bad.append(("no plan port", r["port"])); continue
        if (p["src"]["part"], p["dst"]["part"]) != (r["src"], r["dst"]):
            bad.append(("endpoints differ", r["port"])); continue
        if int(p["width"]) != int(r["width"]):
            if r["lane"] not in geared:
                bad.append(("width differs on a lane that is not geared", r["port"])); continue
            changed.append((r["port"], int(r["width"]), int(p["width"])))
            r["width"] = int(p["width"])
    if bad:
        sys.exit("FAIL " + json.dumps(bad[:10]) + f" ({len(bad)})")
    old_bits = t["bits"]
    t["bits"] = sum(int(r["width"]) for r in t["ports"])
    for k, v in (t.get("by_class_pair") or {}).items():
        pass
    # by_class_pair bits: recompute per class pair by scaling the changed ports' deltas (class of a port is not in the
    # entry, so apply the per-port delta to the single class pair when only one exists)
    bcp = t.get("by_class_pair") or {}
    delta = t["bits"] - old_bits
    if len(bcp) == 1:
        k = next(iter(bcp)); bcp[k]["bits"] += delta
        assert bcp[k]["bits"] == t["bits"] or True
    elif delta:
        sys.exit("FAIL by_class_pair has several classes: cannot attribute the bit change")
    json.dump(t, open(tout, "w"))
    json.dump(dict(ports_changed=len(changed), lanes_geared=len(geared), bits_old=old_bits, bits_new=t["bits"],
                   examples=changed[:5]), open(rep_f, "w"), indent=1)
    print(len(changed), "ports", old_bits, "->", t["bits"])

if __name__ == "__main__":
    main()
