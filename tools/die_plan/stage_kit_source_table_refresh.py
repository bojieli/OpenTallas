#!/usr/bin/env python3
"""stage_kit_source_table_refresh.py -- price KIT-built source stations in the latency table (DIE-S81-88 11-13, COORD 16:04
BASELINE-HIDDEN ruling, S81 22 "unpriced" lanes).

kit_istations.py builds a source type's OUT-bus internal_stations as n u_ist flops inside the SOURCE kit.  When the lane's
fixed_cycles is below n (the table never counted those stations), bind's kit_source_station_pricing (native_istations.
annotate_kit, QC-BIND-IST-PAD) skips the lane and keeps the old receiver pad, so the built lane is delivered at table + n.
This stage adds n to the lane's fixed_cycles and to its latency row (fixed, cycles, natural), so that with the switch ON
annotate_kit selects the lane, subtracts n from the receiver pad and the built lane equals the table again.

Selection = ist_audit v2 / annotate_kit: source type has an OUT internal_stations row on the lane's source bus (n = deepest
row), the type is not native (asbuilt internal_stations_types, split_of follows), not a spine lane, no
realize_internal_stations form, and lane fixed_cycles < n.  Every other lane is left byte-identical.

usage: stage_kit_source_table_refresh.py PLAN.json ASBUILT.json OUT_PLAN.json RECEIPT.json [--expect N]
Fail-closed: --expect N refuses unless exactly N lanes are refreshed; after the edit every selected lane must have
fixed_cycles >= n and table fixed == lane fixed_cycles, else nothing is written.
"""
import argparse
import hashlib
import json
import sys


def _parts(d):
    p = d.get("partitions", [])
    return p if isinstance(p, dict) else {x["name"]: x for x in p}


def select(d, native):
    PT = d.get("partition_types", {})
    parts = _parts(d)
    ports = {p["id"]: p for p in d.get("ports", [])}
    tab = (d.get("latency") or {}).get("lanes", {})
    sel = []
    for ln in d.get("lanes", []):
        a = ports[ln["ports"][0]]["src"]
        tn = parts.get(a["part"], {}).get("type")
        t = PT.get(tn, {})
        outs = {x["name"] for x in t.get("buses", []) if x.get("dir") == "out"}
        if a["bus"] not in outs:
            continue
        n = max((len(e["regs_um"]) for e in t.get("internal_stations", []) if e.get("conn") == "bus:" + a["bus"]), default=0)
        if not n or tn in native or t.get("split_of") in native or ln.get("spine") or t.get("realize_internal_stations"):
            continue
        fx = int(ln.get("fixed_cycles") or 0)
        if fx < n:
            if ln["id"] not in tab:
                raise SystemExit(f"REFUSE: lane {ln['id']} has no latency row")
            sel.append((ln, n, fx, tn, a["bus"]))
    return sel


def stage(d, native):
    tab = d["latency"]["lanes"]
    rows = []
    for ln, n, fx, tn, bus in select(d, native):
        r = tab[ln["id"]]
        if int(r.get("fixed", 0)) != fx:
            raise SystemExit(f"REFUSE: lane {ln['id']} table fixed {r.get('fixed')} != lane fixed_cycles {fx}")
        old = {k: r.get(k) for k in ("fixed", "cycles", "natural")}
        ln["fixed_cycles"] = fx + n
        r["fixed"] = int(r.get("fixed", 0)) + n
        r["cycles"] = int(r["cycles"]) + n
        if "natural" in r:
            r["natural"] = int(r["natural"]) + n
        rows.append({"lane": ln["id"], "src_type": tn, "bus": bus, "n": n, "lane_fixed_old": fx, "lane_fixed_new": fx + n,
                     "table_old": old, "table_new": {k: r.get(k) for k in ("fixed", "cycles", "natural")}})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("asbuilt"); ap.add_argument("out"); ap.add_argument("receipt")
    ap.add_argument("--expect", type=int)
    a = ap.parse_args(argv)
    rb = open(a.plan, "rb").read()
    d = json.loads(rb)
    native = set(json.load(open(a.asbuilt)).get("internal_stations_types", []))
    rows = stage(d, native)
    if a.expect is not None and len(rows) != a.expect:
        raise SystemExit(f"REFUSE: {len(rows)} lanes selected, --expect {a.expect}")
    left = select(d, native)
    if left:
        raise SystemExit(f"REFUSE: {len(left)} lanes still unpriced after the stage")
    tab = d["latency"]["lanes"]
    for ln in d["lanes"]:
        if ln["id"] in tab and int(tab[ln["id"]].get("fixed", 0)) != int(ln.get("fixed_cycles") or 0):
            raise SystemExit(f"REFUSE: lane {ln['id']} table/lane fixed mismatch after the stage")
    out = json.dumps(d, indent=1).encode() + b"\n"
    open(a.out, "wb").write(out)
    rec = {"tool": "stage_kit_source_table_refresh", "plan_in": hashlib.sha256(rb).hexdigest()[:12],
           "plan_out": hashlib.sha256(out).hexdigest()[:12], "lanes": len(rows), "cycles_added": sum(r["n"] for r in rows),
           "rows": rows}
    json.dump(rec, open(a.receipt, "w"), indent=1)
    print(f"kit_source_table_refresh: {len(rows)} lanes, +{rec['cycles_added']} cycles, {rec['plan_in']} -> {rec['plan_out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
