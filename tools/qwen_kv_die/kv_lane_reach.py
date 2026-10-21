#!/usr/bin/env python3
"""Actual pin-to-pin audit of every net incident to an orientation-adapted lane.

Reports all incident pairs. Fixed lane data/epoch/forwarded-clock transport
must meet its declared width-class reach; root clock/reset distribution is
reported separately and remains subject to CTS/reset-window qualification.
The distance is the shortest Manhattan span between actual pin rectangles'
centres, an optimistic bound. Missing geometry or overreach fails closed.
"""

import collections
import math
import re
import kv_lane_orientation as L


def audit(netlist, lef, before_place, after_place, orientation, reach_classes, extra=()):
    """extra: instances added to the audited scope (HKV-STATIONS inserted relay stations / moved landing frames)"""
    from kv_fwd_lanes import expr_bits, INST, CONN

    report = orientation
    changed = {x["instance"] for x in report["changes"]} | set(extra)
    txt = lef
    macros = {m["name"]: m for m in L.C.parse_lef(txt)}
    # Attach direction (shared LEF reader intentionally omits direction).
    cur = pin = None
    directions = {}
    for line in txt.splitlines():
        s = line.strip().split()
        if not s:
            continue
        if s[0] == "MACRO":
            cur = s[1]
        elif s[0] == "PIN":
            pin = s[1]
        elif s[0] == "DIRECTION" and cur and pin:
            directions[cur, pin] = s[1]
    for m in macros.values():
        m["pd"] = {x["name"]: x for x in m["pins"]}
    text = netlist
    wires = {
        m[1]: int(m[0]) + 1 for m in re.findall(r"wire\s+\[(\d+):0\]\s+(\S+);", text)
    }
    # a net assigned a literal (die.v `assign n_x__tie0 = 1'b0;`) is a constant, not lane transport
    const = {
        f"{m[0]}[{i}]"
        for m in re.findall(r"^\s*assign\s+(\S+)\s*=\s*(\d+)'[bB][01]+\s*;", text, re.M)
        for i in range(int(m[1]))
    }
    insts = {}
    for line in text.splitlines():
        m = INST.match(line)
        if m:
            insts[m[3]] = (m[2], dict(CONN.findall(m[4])))
    placements = []
    for text_place in (before_place, after_place):
        placements.append(
            {
                n: (float(x) * 1000, float(y) * 1000, o)
                for n, x, y, o in re.findall(
                    r"ot_mts::place \[\$_blk findInst (\S+)\] (\S+) (\S+) (\S+)",
                    text_place,
                )
            }
        )
    incident = {}
    unmeasured = []
    for n in sorted(changed):
        if n not in insts:
            # KVR-PLACE2 10-19: an inserted / moved station absent from the audited netlist is a netlist/record mismatch
            # (kvs14r-f9ef813ab-kvrplace: KeyError on a chained AFTER stage) -- fail closed, never skip silently
            unmeasured.append(dict(net=None, endpoint=(n, None, None), reason="audited instance missing from the netlist"))
            continue
        for port, expr in insts[n][1].items():
            for bit, b in enumerate(expr_bits(expr, wires)):
                if b not in ("0", "1") and b not in const:
                    incident.setdefault(b, []).append((n, port, bit))
    ends = collections.defaultdict(list)
    for n, (master, cs) in insts.items():
        for port, expr in cs.items():
            for bit, b in enumerate(expr_bits(expr, wires)):
                if b in incident:
                    ends[b].append((n, port, bit))

    def points(ep, index):
        n, port, bit = ep
        master = insts[n][0]
        m = macros.get(master)
        pl = placements[index].get(n)
        if m is None or pl is None:
            return []
        pin = m["pd"].get(port + f"[{bit}]") or (
            m["pd"].get(port) if bit == 0 else None
        )
        if pin is None:
            return []
        x, y, o = pl
        return [
            (x + (q[0] + q[2]) / 2, y + (q[1] + q[3]) / 2)
            for lay, r in pin["rects"]
            for q in [L.C.transform_rect(r, o, m["W"], m["H"])]
        ]

    def direction(ep):
        n, port, bit = ep
        mst = insts[n][0]
        return directions.get((mst, port + f"[{bit}]"), directions.get((mst, port)))

    rows = []
    for b, touched in incident.items():
        es = ends[b]
        drivers = [e for e in es if direction(e) in ("OUTPUT", "INOUT")]
        loads = [e for e in es if direction(e) in ("INPUT", "INOUT")]
        for e in es:
            if direction(e) is None:
                unmeasured.append(
                    dict(net=b, endpoint=e, reason="missing LEF direction")
                )
        if not drivers and any(e[1] in ("a", "ea", "ckf") for e in touched):
            unmeasured.append(
                dict(
                    net=b,
                    endpoints=touched,
                    reason="lane transport has no measured driver",
                )
            )
        for s in drivers:
            for d in loads:
                if s == d or not (s[0] in changed or d[0] in changed):
                    continue
                # root clock/reset fanout is CTS/release-window qualified; lane transport is a fixed hop.
                tp = any(
                    e[0] in changed and e[1] in ("a", "b", "ck_o", "ckf", "ea", "eb")
                    for e in (s, d)
                )
                widths = [
                    int(insts[e[0]][0].rsplit("_", 1)[1])
                    for e in (s, d)
                    if insts[e[0]][0].startswith(("qkd_rlys", "qkd_landsh"))
                ]
                width = max(widths, default=1)
                reach = next(
                    (um for limit, um in reach_classes if width <= limit),
                    reach_classes[-1][1],
                )
                spans = []
                for i in (0, 1):
                    a, c = points(s, i), points(d, i)
                    spans.append(
                        min(
                            (abs(x - u) + abs(y - v)) / 1000 for x, y in a for u, v in c
                        )
                        if a and c
                        else None
                    )
                row = dict(
                    net=b,
                    src=s,
                    dst=d,
                    before=spans[0],
                    after=spans[1],
                    reach=reach,
                    transport=tp,
                )
                if None in spans:
                    unmeasured.append(row)
                else:
                    rows.append(row)
    grouped = {}
    for row in rows:
        key = (
            tuple(row["src"][:2]),
            tuple(row["dst"][:2]),
            row["transport"],
            row["reach"],
        )
        group = grouped.setdefault(
            key,
            dict(
                src=list(key[0]),
                dst=list(key[1]),
                transport=key[2],
                reach_um=key[3],
                bit_pairs=0,
                before_max_um=0,
                after_max_um=0,
                before_overreach_bits=0,
                after_overreach_bits=0,
                newly_overreach_bits=0,
            ),
        )
        group["bit_pairs"] += 1
        group["before_max_um"] = max(group["before_max_um"], row["before"])
        group["after_max_um"] = max(group["after_max_um"], row["after"])
        group["before_overreach_bits"] += row["before"] > row["reach"]
        group["after_overreach_bits"] += row["after"] > row["reach"]
        group["newly_overreach_bits"] += row["before"] <= row["reach"] < row["after"]
    groups = list(grouped.values())
    transport = [g for g in groups if g["transport"]]
    violations = [g for g in transport if g["after_overreach_bits"]]
    repairs = []
    failing_pairs = {}
    for g in violations:
        key = (g["src"][0], g["dst"][0])
        previous = failing_pairs.get(key)
        if (
            previous is None
            or g["after_max_um"] / g["reach_um"]
            > previous["after_max_um"] / previous["reach_um"]
        ):
            failing_pairs[key] = g
    for g in failing_pairs.values():
        # A concrete lower bound for planning, never an invented live station:
        # reserve independent full-width hop frames and then recompile E/K/ages.
        source, target = g["src"][0], g["dst"][0]
        width = max(
            int(insts[e][0].rsplit("_", 1)[1])
            for e in (source, target)
            if insts[e][0].startswith(("qkd_rlys", "qkd_landsh"))
        )
        station = f"qkd_rlysh_{width}"
        m = macros.get(station)
        repairs.append(
            dict(
                src=g["src"],
                dst=g["dst"],
                station_master=station,
                station_outline_um=[m["W"] / 1000, m["H"] / 1000] if m else None,
                minimum_extra_hops=math.ceil(g["after_max_um"] / g["reach_um"]) - 1,
                span_um=g["after_max_um"],
                reach_um=g["reach_um"],
                required="Reserve nonoverlapping channel slots at actual pin reach, insert full-width forwarded stations, "
                "then recompile lane half-cycle age, landing E/K and exact schedule. No live insertion or qualification implied.",
            )
        )
    return dict(
        schema="opentallas.kv_lane_incident_reach.v1",
        status="FAIL" if violations or unmeasured else "PASS",
        summary=dict(
            audited_instances=len(changed),
            measured_pairs=len(rows),
            unmeasured_pairs=len(unmeasured),
            transport_pairs=sum(g["bit_pairs"] for g in transport),
            before_overreach_bits=sum(g["before_overreach_bits"] for g in transport),
            after_overreach_bits=sum(g["after_overreach_bits"] for g in transport),
            newly_overreach_bits=sum(g["newly_overreach_bits"] for g in transport),
            transport_groups=len(transport),
            violating_groups=len(violations),
            violating_instance_pairs=len(failing_pairs),
            before_worst_um=max((g["before_max_um"] for g in transport), default=0),
            after_worst_um=max((g["after_max_um"] for g in transport), default=0),
        ),
        groups=groups,
        unmeasured=unmeasured,
        reservation_repairs=repairs,
    )
