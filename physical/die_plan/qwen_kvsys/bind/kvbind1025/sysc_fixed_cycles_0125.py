#!/usr/bin/env python3
"""PATH-KV 2026-10-26: make every lane whose source is a native-internal-station OUT bus price exactly the
stations its source type places (plan self-consistency for native_istations.annotate).

Main's SYS3 kv3_sys_c (e055c9ee57) keeps the SYS_C UCIe north detour for o_host_link_rst_n: 8 internal stations
on a 2662 um path (from_um -> regs_um -> to_um, every hop <= 405 um).  Lane L747 (tap_tree host.link_rst_n) still
carried the pre-detour v3.9f value fixed_cycles 5 (2160 um straight path), so the strict bind stops at
'native stations L747: fixed_cycles must equal 8'.  5 stations cannot span the detour at <= 405 um
(ceil(2662/405)-1 = 6 minimum), and moving the trunk back onto the ft1 corridor / VDDPHY domain is the thing the
detour removed.  So the lane takes the geometry's count: L747 fixed 5 -> 8, latency 19 -> 22 (+3 cycles on the host
link-reset forward route host.link_rst_n -> serdes_E.rst_n, control-only; same value Codex aef2c30627 derived
'L747 forward stations 5->8', lat L747 19->22).

Derived, never hand-set: for each type T in TYPES and each OUT internal station on bus B, the lane whose ports start
at a partition of type T on bus B gets fixed_cycles = len(regs_um); latency.lanes[L].{fixed,cycles,natural} move by
the same delta.  usage: sysc_fixed_cycles_0125.py PLAN_IN PLAN_OUT REPORT"""
import json
import sys

TYPES = ["kv3_sys_c"]


def main(pin, pout, rep):
    P = json.load(open(pin))
    ports = {x["id"]: x for x in P["ports"]}
    lanes = {x["id"]: x for x in P["lanes"]}
    lat = P["latency"]["lanes"]
    ptype = {n: p["type"] for n, p in P["partitions"].items()} if isinstance(P["partitions"], dict) else \
        {p["name"]: p["type"] for p in P["partitions"]}
    changes = []
    for tn in TYPES:
        for e in P["partition_types"][tn].get("internal_stations", []):
            if not e.get("conn", "").startswith("bus:"):
                continue
            bus = e["conn"][4:]
            n = len(e["regs_um"])
            for L in P["lanes"]:
                first = ports[L["ports"][0]]["src"]
                if first.get("bus") != bus or ptype.get(first.get("part")) != tn:
                    continue
                old = int(L.get("fixed_cycles", 0))
                if old == n:
                    continue
                d = n - old
                L["fixed_cycles"] = n
                L["note"] = L.get("note", "") + f" | 0125 fixed_cycles = {tn} internal_stations {bus} ({n}, SYS3 north detour)"
                la = lat[L["id"]]
                before = dict(la)
                for k in ("fixed", "cycles", "natural"):
                    la[k] = int(la[k]) + d
                changes.append(dict(lane=L["id"], type=tn, bus=bus, fixed=[old, n], latency_before=before, latency_after=dict(la)))
    for c in changes:
        la = lat[c["lane"]]
        base = la["boundary"] + la["stations"]
        if la["cycles"] < base + la["fixed"]:
            raise SystemExit(f"{c['lane']}: cycles {la['cycles']} < boundary+stations+fixed {base + la['fixed']}")
    json.dump(P, open(pout, "w"), indent=1)
    open(pout, "a").write("\n")
    json.dump(dict(schema="opentallas.kv.sysc_fixed_cycles.v1", changes=changes), open(rep, "w"), indent=1)
    print(json.dumps(changes))


if __name__ == "__main__":
    main(*sys.argv[1:])
