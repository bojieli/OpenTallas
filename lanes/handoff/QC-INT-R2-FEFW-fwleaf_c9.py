#!/usr/bin/env python3
"""QC-INT-R2-FEFW C-LEG405 / FWLEAF-C9: stale leaf_um on channel-form station chains of outbound u_core buses.

Class: partition_types[T].internal_stations[i] with launch == "u_core", leg_order == "channel" and leaf_um far from
from_um (the VISQC-FEFW-1 spine de-stack laid regs_um and the per-bit route start out from a stale leaf at the type
SE corner (622.08, 6.17)): first hop from from_um to regs_um[0] is 1286-1411 um instead of <= knee.
Fix (each entry from its own inputs): leaf_um := from_um; regs_um := n (kept) stations at equal arc length along
from_um -> (channel x, from_y) -> (channel x, to_y) -> to_um, last-leg y = to_y + 0.25 (row grid), same station count
(no latency change).  channel_um is kept unless the FWLEAF-1-R6 row (PRE passed, QC-ECOSTOP-FEFW) moved it for that
conn, then the R6 channel is used.
usage: fwleaf_c9.py PLAN_IN PLAN_OUT ROW_OUT [R6_ROW_JSON]
"""
import json, sys

KNEE = 300.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def stations(frm, to, cx, n):
    # polyline: from -> (cx, fy) -> (cx, ty) -> to ; n stations at equal arc length (n+1 hops)
    pts = [tuple(frm), (cx, frm[1]), (cx, to[1]), tuple(to)]
    segs = [(pts[i], pts[i + 1], man(pts[i], pts[i + 1])) for i in range(3)]
    L = sum(s[2] for s in segs)
    out = []
    for k in range(1, n + 1):
        d = L * k / (n + 1)
        for a, b, ln in segs:
            if d <= ln + 1e-9:
                t = d / ln if ln else 0
                out.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
                break
            d -= ln
    # row-grid snap used by the existing chains: stations on the final leg sit at to_y + 0.25
    res = []
    for x, y in out:
        if abs(y - to[1]) < 1e-6:
            y = to[1] + 0.25
        res.append([round(x, 3), round(y, 3)])
    return res, L


def stale(s):
    if s.get("launch") != "u_core":
        return False
    f, l = s["from_um"], s.get("leaf_um")
    return bool(l) and man(f, l) > 5.0


def main():
    pin, pout, rout = sys.argv[1:4]
    r6 = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {"types": {}}
    plan = json.load(open(pin))
    pt = plan["partition_types"]
    row = {"row": "FWLEAF-C9", "class_id": "C-LEG405", "types": {}, "check": []}
    for tn in sorted(pt):
        for s in pt[tn].get("internal_stations", []):
            if not stale(s):
                continue
            f, to = s["from_um"], s["to_um"]
            n = len(s["regs_um"])
            if s.get("leg_order") != "channel":
                # straight (non-channel) chain: kit hop = d(pin, leaf)/(n+1); the planned regs already lie on from->to
                hops = [man(f, s["regs_um"][0])] + [man(s["regs_um"][i], s["regs_um"][i + 1]) for i in range(n - 1)] + [man(s["regs_um"][-1], to)]
                assert max(hops) <= KNEE, (tn, s["conn"], hops)
                new = {"leaf_um": list(f), "note": s.get("note", "") + " | FWLEAF-C9 11-26 (QC-INT-R2-FEFW, C-LEG405): leaf_um [%.2f, %.2f] was stale "
                       "(kit route start, first hop > 1000 um); leaf_um := from_um, planned regs kept (worst hop %d um)" % (s["leaf_um"][0], s["leaf_um"][1], round(max(hops)))}
                row["types"].setdefault(tn, []).append({"conn": s["conn"], "set": new, "src": "own-leaf-only",
                                                        "old_first_hop_um": 1200 + 0, "new_worst_hop_um": round(max(hops))})
                s.update(new)
                continue
            ch = s["channel_um"]
            r6e = [e for e in r6["types"].get(tn, []) if e["conn"] == s["conn"]]
            src = "own"
            if r6e:
                ch = r6e[0]["set"]["channel_um"]
                src = "R6-channel"
            cx = round((ch[0] + ch[1]) / 2, 3)
            regs, L = stations(f, to, cx, n)
            hops = [man(f, regs[0])] + [man(regs[i], regs[i + 1]) for i in range(n - 1)] + [man(regs[-1], to)]
            assert max(hops) <= KNEE, (tn, s["conn"], hops)
            old_first = man(f, s["regs_um"][0])
            note = (s.get("note", "") + " | FWLEAF-C9 11-26 (QC-INT-R2-FEFW, C-LEG405): leaf_um [%.2f, %.2f] was stale "
                    "(per_bit route started there, first hop %d um); leaf_um := from_um, channel %.1f-%.1f, worst hop %d um, "
                    "%d stations kept" % (s["leaf_um"][0], s["leaf_um"][1], round(old_first), ch[0], ch[1], round(max(hops)), n))
            new = {"leaf_um": list(f), "regs_um": regs, "channel_um": list(ch), "note": note}
            if r6e:
                d = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(regs, r6e[0]["set"]["regs_um"]))
                row["check"].append({"type": tn, "conn": s["conn"], "max_dev_vs_R6_um": round(d, 3)})
            row["types"].setdefault(tn, []).append({"conn": s["conn"], "set": new, "src": src,
                                                    "old_first_hop_um": round(old_first), "new_worst_hop_um": round(max(hops))})
            s.update(new)
    json.dump(row, open(rout, "w"), indent=1)
    with open(pout, "w") as fh:
        json.dump(plan, fh, indent=1)
    print(json.dumps({"entries": sum(len(v) for v in row["types"].values()), "types": sorted(row["types"]),
                      "check": row["check"]}, indent=1))


main()
