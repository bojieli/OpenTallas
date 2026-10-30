#!/usr/bin/env python3
"""DIE-HBM-35 estimate-before-build: every strict-bind UNPLANNED pair (bind_report.json errors) on plan PLANDIR.
Per pair (one half; NW mirrors NE): centre Manhattan distance, adjacency path (Dijkstra over partition shared edges, cost =
centre distance, +penalty when the shared edge has less free face than the pair's bits needs at 6 pins/um), cycles at the
405-um station reach + 2 boundary, and the aggregate demand vs free supply per shared edge if every gap took its path.
usage: est_gaps.py WT PLANDIR BIND_REPORT OUT_JSON"""
import sys, json, re, heapq, collections
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S, lane_add as LA
P = S.Plan(json.load(open(sys.argv[2] + "/die_plan.json")))
R = json.load(open(sys.argv[3]))
PPU, REACH = 6.0, 405.0
parts = sorted(P.parts)
cen = {a: LA.centre(P, a) for a in parts}
edges = {}
for i, a in enumerate(parts):
    for b in parts[i + 1:]:
        e = LA.shared_edge(P, a, b)
        if not e:
            continue
        df, lo, hi = e
        occ = LA.face_intervals(P, a, df) + LA.face_intervals(P, b, LA.OPP[df])
        gaps = list(LA.free_gaps(lo + 1.0, hi - 1.0, occ, 2.0))
        free = sum(g1 - g0 for g0, g1 in gaps)
        edges[(a, b)] = edges[(b, a)] = dict(len=hi - lo, free_um=free, free_pins=int(free * PPU))
adj = collections.defaultdict(list)
for (a, b) in edges:
    adj[a].append(b)
def man(a, b):
    return abs(cen[a][0] - cen[b][0]) + abs(cen[a][1] - cen[b][1])
def path(a, b, bits):
    best = {a: 0.0}; prev = {}; q = [(0.0, a)]
    while q:
        d, u = heapq.heappop(q)
        if u == b:
            break
        if d > best.get(u, 1e18):
            continue
        for v in adj[u]:
            if v.startswith("PHY") or v.startswith("vsN") and v != b:
                pass
            c = man(u, v) + (20000.0 if edges[(u, v)]["free_pins"] < bits else 0.0)
            if d + c < best.get(v, 1e18):
                best[v] = d + c; prev[v] = u; heapq.heappush(q, (d + c, v))
    if b not in prev and a != b:
        return None
    p = [b]
    while p[-1] != a:
        p.append(prev[p[-1]])
    return p[::-1]
rows = []
for e in R["errors"]:
    m = re.match(r"UNPLANNED (\S+) -> (\S+): (\d+) as-built crossing bits.*\((\d+) b planned", e)
    if not m:
        continue
    a, b, bits, planned = m[1], m[2], int(m[3]), int(m[4])
    rows.append(dict(src=a, dst=b, bits=bits, planned_direct=planned, adjacent=(a, b) in edges,
                     manhattan_um=round(man(a, b), 1)))
use = collections.Counter()
for r in rows:
    p = path(r["src"], r["dst"], r["bits"])
    r["path"] = p
    if p:
        L = sum(man(u, v) for u, v in zip(p, p[1:]))
        r["path_um"] = round(L, 1)
        r["cycles_est"] = int(-(-L // REACH)) + 2
        r["bottleneck"] = min(((edges[(u, v)]["free_pins"], f"{u}|{v}") for u, v in zip(p, p[1:])))
        for u, v in zip(p, p[1:]):
            use[tuple(sorted((u, v)))] += r["bits"]
over = []
for k, d in use.items():
    sup = edges[k]["free_pins"]
    if d > sup:
        over.append(dict(edge="|".join(k), demand=d, free_pins=sup, short=d - sup, len_um=round(edges[k]["len"], 1)))
over.sort(key=lambda x: -x["short"])
json.dump(dict(plan=sys.argv[2], bind=sys.argv[3], pairs=rows, edge_overflow=over,
               edge_use={"|".join(k): v for k, v in use.items()}), open(sys.argv[4], "w"), indent=1)
for r in sorted(rows, key=lambda r: -r["bits"]):
    if r["src"].startswith("NW"):
        continue
    print(f"{r['src']:9s}->{r['dst']:9s} {r['bits']:5d}b adj={int(r['adjacent'])} man {r['manhattan_um']:7.0f} path {r.get('path_um',0):7.0f} cyc~{r.get('cycles_est')} bott {r.get('bottleneck')} {'-'.join(r['path'] or [])}")
print("EDGE OVERFLOW (all pairs, both halves):")
for o in over:
    print(o)
