#!/usr/bin/env python3
"""VISLAYOUT3-KVHEAD grow_type.py: grow (dx>0) or shrink (dx<0) one partition type along x at a cut line.

    grow_type.py PLAN_IN PLAN_OUT LEDGER TYPE --cut XC --dx D [--bins IN OUT] [--bins-path P]
                 [--part NAME:DXO ...] [--scan]

Every x coordinate of the type (points [x,y], rects [x0,y0,x1,y1], ft bit sites, regs, pins, relays, taps, bands,
keepouts, contents origins) with x >= XC moves by D; x < XC stays.  outline_um[0] += D.  A shrink (D < 0) requires the
removed band [XC+D, XC) to be free of every coordinate (asserted), so nothing collapses.  Rect corners straddling XC
stretch (bands / keepouts keep their side).  --part NAME:DXO moves a die partition origin x by DXO.  --bins shifts the
type's clock sink-bin inventory with the same rule.  --scan: print the x-occupancy histogram (10.8-um bins) and the
widest empty x bands of the type, write nothing.  Nothing else in the plan changes (asserted)."""
import argparse, copy, json, sys

ap = argparse.ArgumentParser()
ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("ledger"); ap.add_argument("type")
ap.add_argument("--cut", type=float); ap.add_argument("--dx", type=float)
ap.add_argument("--bins", nargs=2); ap.add_argument("--bins-path")
ap.add_argument("--part", action="append", default=[])
ap.add_argument("--scan", action="store_true")
a = ap.parse_args()
P = json.load(open(a.plan_in)); P0 = copy.deepcopy(P)
t = P["partition_types"][a.type]
W, H = t["outline_um"]
SKIP = {"outline_um", "resized_from_um"}


def coords(o, path=()):
    """yield (container, key, kind) for every x-bearing numeric list"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP:
                continue
            if isinstance(v, list) and len(v) in (2, 4) and all(isinstance(z, (int, float)) for z in v):
                yield v, path + (k,)
            else:
                yield from coords(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, list) and len(v) in (2, 4) and all(isinstance(z, (int, float)) for z in v):
                yield v, path + (i,)
            else:
                yield from coords(v, path + (i,))


def is_size(path):
    s = ".".join(map(str, path))
    return s.endswith("outline_um") or s.endswith("size_um")


xs = []
for v, path in coords(t):
    if is_size(path):
        continue
    xs.extend([v[0]] if len(v) == 2 else [v[0], v[2]])
if a.scan:
    import collections
    h = collections.Counter(int(x // 10.8) for x in xs)
    occ = sorted(h)
    gaps, prev = [], 0.0
    for b in occ:
        lo = b * 10.8
        if lo - prev > 20:
            gaps.append((round(lo - prev, 1), round(prev, 1), round(lo, 1)))
        prev = (b + 1) * 10.8
    if W - prev > 20:
        gaps.append((round(W - prev, 1), round(prev, 1), round(W, 1)))
    print("TYPE", a.type, "W", W, "coords", len(xs))
    print("widest empty x bands:", sorted(gaps, reverse=True)[:8])
    sys.exit(0)
XC, D = a.cut, a.dx
if D < 0:
    bad = [x for x in xs if XC + D <= x < XC]
    assert not bad, f"shrink band [{XC + D}, {XC}) holds {len(bad)} coords, e.g. {bad[:5]}"
n = 0
for v, path in coords(t):
    if is_size(path):
        continue
    idx = [0] if len(v) == 2 else [0, 2]
    for i in idx:
        if v[i] >= XC:
            v[i] = round(v[i] + D, 4); n += 1
t["outline_um"][0] = round(W + D, 4)
moved_parts = []
for spec in a.part:
    name, dxo = spec.split(":")
    p = next(p for p in P["partitions"] if p["name"] == name)
    p["origin_um"][0] = round(p["origin_um"][0] + float(dxo), 4); moved_parts.append([name, p["origin_um"]])
led = {"type": a.type, "cut": XC, "dx": D, "outline_from": [W, H], "outline_to": t["outline_um"], "coords_moved": n,
       "parts": moved_parts}
if a.bins:
    B = json.load(open(a.bins[0])); m = 0
    for b in B["bins"]:
        if b[0] >= XC:
            b[0] = round(b[0] + D, 4); m += 1
    B["source"] = B.get("source", "") + f" | VISLAYOUT3-KVHEAD grow_type: {m} bins x>={XC} moved {D}"
    json.dump(B, open(a.bins[1], "w")); led["bins_moved"] = m
    if a.bins_path:
        t["clock"]["sink_bins_file"] = a.bins_path
# invariants: only this type and the named partitions changed
for k in P:
    if k not in ("partition_types", "partitions"):
        assert P[k] == P0[k], k
for tn in P["partition_types"]:
    if tn != a.type:
        assert P["partition_types"][tn] == P0["partition_types"][tn], tn
names = {s.split(":")[0] for s in a.part}
for p, p0 in zip(P["partitions"], P0["partitions"]):
    if p["name"] not in names:
        assert p == p0, p["name"]
json.dump(P, open(a.plan_out, "w"), indent=1)
json.dump(led, open(a.ledger, "w"), indent=1)
print(json.dumps(led))
