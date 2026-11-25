#!/usr/bin/env python3
"""QC-SUC-FTSITE 11-25 row SUC-WEST: su_c W-margin re-seat (C1o v13 base).
Cause (slw_su_c cl92142dac GRT, congestion.rpt): 99% of 14.7k overflow units in x0-100 y100-300, the 43-um W margin between the
die W face and bottom core u_va (OBS M1-M6), 80% vertical (M3 7598, M7 4885, M5 3572).  Three station chains run down that margin
and under the core row although source/sink sit in or by the street: x_su_l1_p1_o (764: leaf street -> (645,42) -> (315,194) ->
(217,42) -> (22,59) -> (35,333) -> W face), x_su_l1_i (438) and x_su_l1_p1_i (438) (W face -> x=21.6 margin -> y=32.5 under va).
Fix (positions only; station COUNT unchanged -> latency/LATCHECK unchanged; pins/windows unchanged):
  x_su_l1_p1_o: keep station 0 at the u_vc source, then up the vb|vc gap into the street and west along it to the W face pin.
  x_su_l1_i / x_su_l1_p1_i: along the street (y 290-545) to x of the va leaf, last station under va; the face->leaf leg crosses
  u_va on M7 (free over the core) instead of the margin.
Per-bit FIRM relay_sites keyed u_ist_<bus>_<k>.* move with their station (same delta).  usage: su_c_westfix.py IN OUT LEDGER
"""
import json, sys
inp, out, led = sys.argv[1:4]
P = json.load(open(inp)); PT = P["partition_types"]
def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def plan_p1o(st):
    s0 = st["regs_um"][0]; to = st["to_um"]
    assert len(st["regs_um"]) == 5, st["regs_um"]
    return [list(s0), [610.0, 300.0], [420.0, 400.0], [220.0, round((400+to[1])/2, 3)], [60.0, round(to[1]-4, 3)]]
def plan_in(st, first):
    n = len(st["regs_um"]); to = st["to_um"]; x1 = round(to[0], 3)
    street = [first] if first else []
    k = n - 1 - len(street)                      # stations along the street before the over-core leg
    fy = st["from_um"][1]; y0 = min(fy, 545.0) if not first else first[1]
    x0 = 25.0 if not first else first[0]
    for i in range(k):
        f = (i + 1) / k
        street.append([round(x0 + (x1 - x0) * f, 3), round(y0 + (290.0 - y0) * f, 3)])
    street.append([x1, 32.48])                   # last station under u_va, next to the leaf
    assert len(street) == n
    return street
types = [t for t in ("sle_su_c", "slw_su_c__cl19bb38ef", "slw_su_c__cl92142dac") if t in PT]
L = {}
for tn in types:
    t = PT[tn]; boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0]+c["outline_um"][0], c["origin_um"][1]+c["outline_um"][1]) for c in t["hard_cores"]]
    inside = lambda q: any(a < q[0] < c and b < q[1] < d for a, b, c, d in boxes)
    rs = t.get("relay_sites") or {}
    L[tn] = {}
    for st in t.get("internal_stations", []):
        c = st["conn"]
        if c == "bus:x_su_l1_p1_o": new = plan_p1o(st)
        elif c == "bus:x_su_l1_i": new = plan_in(st, None)
        elif c == "bus:x_su_l1_p1_i": new = plan_in(st, [22.0, 545.0])
        else: continue
        old = st["regs_um"]
        bad = [q for q in new if inside(q)]
        assert not bad, (tn, c, bad)
        pts = [st["from_um"]] + new + [st["to_um"]]
        hops = [round(man(a, b), 1) for a, b in zip(pts, pts[1:])]
        bus = c.split(":", 1)[1]; moved = 0
        for k, (o, n) in enumerate(zip(old, new)):
            dx, dy = n[0]-o[0], n[1]-o[1]
            pre = f"u_ist_{bus}_{k}."
            for key in [key for key in rs if key.startswith(pre)]:
                x, y = rs[key]; rs[key] = [round(x+dx, 4), round(y+dy, 4)]; moved += 1
        st["regs_um"] = new
        st["note"] = st.get("note", "") + " | QC-SUC-FTSITE SUC-WEST 11-25: off the W margin (GRT 14.7k overflow at x0-100); street + over-core M7 leg, same station count"
        L[tn][c] = dict(old=old, new=new, hops=hops, relay_sites_moved=moved)
        print(tn, c, "hops", hops, "relay_sites moved", moved)
    t["note"] = t.get("note", "") + " | QC-SUC-FTSITE SUC-WEST 11-25: x_su_l1_* station chains re-seated off the W margin (positions only, 0 cycles)"
json.dump(P, open(out, "w"), separators=(",", ":")); json.dump(L, open(led, "w"), indent=1)
