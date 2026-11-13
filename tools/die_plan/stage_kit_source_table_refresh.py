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

--dest (S81-R12BA-FIN 11-12, LATCHECK-1 UNPRICED_KIT_STATIONS): also price the RECEIVER's kit-built IN stations.  The
receiver kit turns m pad stages of u_lpad_<bus> into its m IN-bus stations (kit_istations packed_input_delay); when the
bound pad (table fixed + pad - kit source n) is below m, the kit adds the missing stations and the built lane is long by
the deficit.  The schema rule is fixed_cycles = source + destination stations, so with --dest a lane needs
fixed + pad >= n + m (m = deepest non-core IN row on the receiver bus; IN stations are kit-built on native types too); the deficit is added to
fixed_cycles and to the latency row (fixed, cycles, natural).  Without --dest the selection is byte-identical to before.

usage: stage_kit_source_table_refresh.py PLAN.json ASBUILT.json OUT_PLAN.json RECEIPT.json [--expect N] [--dest]
Fail-closed: --expect N refuses unless exactly N lanes are refreshed; after the edit no lane may still be selected and
table fixed == lane fixed_cycles on every lane, else nothing is written.
"""
import argparse
import hashlib
import json
import sys


def _parts(d):
    p = d.get("partitions", [])
    return p if isinstance(p, dict) else {x["name"]: x for x in p}


def _kit_depth(t, tn, bus, direction, native):
    """deepest internal_stations row on bus (0 when the type has none, is native or realises its stations itself)"""
    if bus not in {x["name"] for x in t.get("buses", []) if x.get("dir") == direction}:
        return 0
    if tn in native or t.get("split_of") in native or t.get("realize_internal_stations"):
        return 0
    return max((len(e["regs_um"]) for e in t.get("internal_stations", []) if e.get("conn") == "bus:" + bus), default=0)


def _src_depth_all(t, bus):
    """source OUT stations the bind subtracts from the receiver pad: kit-priced or native (realize forms own theirs)"""
    if t.get("realize_internal_stations"):
        return 0
    if bus not in {x["name"] for x in t.get("buses", []) if x.get("dir") == "out"}:
        return 0
    return max((len(e["regs_um"]) for e in t.get("internal_stations", []) if e.get("conn") == "bus:" + bus), default=0)


def _dest_depth(t, bus):
    """receiver IN bus chain depth kit_istations builds (deepest non-core row; core pin-face chains are not pad stages).
    IN stations are never realised natively (native_istations.source_entries is OUT-only), so no native exclusion."""
    if bus not in {x["name"] for x in t.get("buses", []) if x.get("dir") == "in"}:
        return 0
    return max((len(e["regs_um"]) for e in t.get("internal_stations", [])
                if e.get("conn") == "bus:" + bus and not e.get("core")), default=0)


def select(d, native, dest=False):
    PT = d.get("partition_types", {})
    parts = _parts(d)
    ports = {p["id"]: p for p in d.get("ports", [])}
    tab = (d.get("latency") or {}).get("lanes", {})
    sel = []
    for ln in d.get("lanes", []):
        if ln.get("spine"):
            continue
        a = ports[ln["ports"][0]]["src"]
        tn = parts.get(a["part"], {}).get("type")
        n = _kit_depth(PT.get(tn, {}), tn, a["bus"], "out", native)
        m, dn, dbus = 0, None, None
        if dest:
            z = ports[ln["ports"][-1]]["dst"]
            dn, dbus = parts.get(z["part"], {}).get("type"), z["bus"]
            m = _dest_depth(PT.get(dn, {}), dbus)
        fx = int(ln.get("fixed_cycles") or 0)
        if dest and m:
            if ln["id"] not in tab:
                raise SystemExit(f"REFUSE: lane {ln['id']} has no latency row")
            # bound receiver pad = fixed + pad - source stations (kit-priced or native: lane_pad() subtracts both).
            # Any packed pad >= 1 absorbs the IN stations (kit_istations packed_input_delay; LATCHECK-1 kit_bus = 0),
            # so only a lane whose receiver pad is 0 is long; it gets fixed = source + destination.
            n_all = _src_depth_all(PT.get(tn, {}), a["bus"])
            pad = int(tab[ln["id"]].get("pad", 0) or 0)
            if fx + pad - n_all <= 0:
                sel.append((ln, n_all + m - fx - pad, fx, tn, a["bus"], n_all, m, dn, dbus))
        elif n and fx < n:
            if ln["id"] not in tab:
                raise SystemExit(f"REFUSE: lane {ln['id']} has no latency row")
            sel.append((ln, n, fx, tn, a["bus"], n, 0, None, None))
    return sel


def stage(d, native, dest=False):
    tab = d["latency"]["lanes"]
    rows = []
    for ln, add, fx, tn, bus, n, m, dn, dbus in select(d, native, dest):
        r = tab[ln["id"]]
        if int(r.get("fixed", 0)) != fx:
            raise SystemExit(f"REFUSE: lane {ln['id']} table fixed {r.get('fixed')} != lane fixed_cycles {fx}")
        old = {k: r.get(k) for k in ("fixed", "cycles", "natural")}
        ln["fixed_cycles"] = fx + add
        r["fixed"] = int(r.get("fixed", 0)) + add
        r["cycles"] = int(r["cycles"]) + add
        if "natural" in r:
            r["natural"] = int(r["natural"]) + add
        row = {"lane": ln["id"], "src_type": tn, "bus": bus, "n": add, "lane_fixed_old": fx, "lane_fixed_new": fx + add,
               "table_old": old, "table_new": {k: r.get(k) for k in ("fixed", "cycles", "natural")}}
        if dest:
            row.update(src_kit=n, dst_type=dn, dst_bus=dbus, dst_kit=m)
        rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("asbuilt"); ap.add_argument("out"); ap.add_argument("receipt")
    ap.add_argument("--expect", type=int)
    ap.add_argument("--dest", action="store_true", help="also price receiver kit IN stations (fixed = source + destination)")
    a = ap.parse_args(argv)
    rb = open(a.plan, "rb").read()
    d = json.loads(rb)
    native = set(json.load(open(a.asbuilt)).get("internal_stations_types", []))
    rows = stage(d, native, a.dest)
    if a.expect is not None and len(rows) != a.expect:
        raise SystemExit(f"REFUSE: {len(rows)} lanes selected, --expect {a.expect}")
    left = select(d, native, a.dest)
    if left:
        raise SystemExit(f"REFUSE: {len(left)} lanes still unpriced after the stage")
    tab = d["latency"]["lanes"]
    for ln in d["lanes"]:
        if ln["id"] in tab and int(tab[ln["id"]].get("fixed", 0)) != int(ln.get("fixed_cycles") or 0):
            raise SystemExit(f"REFUSE: lane {ln['id']} table/lane fixed mismatch after the stage")
    out = json.dumps(d, indent=1).encode() + b"\n"
    open(a.out, "wb").write(out)
    rec = {"tool": "stage_kit_source_table_refresh", "dest": a.dest, "plan_in": hashlib.sha256(rb).hexdigest()[:12],
           "plan_out": hashlib.sha256(out).hexdigest()[:12], "lanes": len(rows), "cycles_added": sum(r["n"] for r in rows),
           "rows": rows}
    json.dump(rec, open(a.receipt, "w"), indent=1)
    print(f"kit_source_table_refresh{' --dest' if a.dest else ''}: {len(rows)} lanes, +{rec['cycles_added']} cycles, "
          f"{rec['plan_in']} -> {rec['plan_out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
