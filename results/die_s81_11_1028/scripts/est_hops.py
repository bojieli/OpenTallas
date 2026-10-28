#!/usr/bin/env python3
"""DIE-S81-11 ESTIMATE (12.16 b(i)): hop chains for crossings with large unshared clock.  Region graph = every region
pair that already has a crossing (either direction) with unshared clock <= U; for each far crossing (unshared > U) the
fewest-hop path src -> dst over that graph (BFS), its hop count, the worst hop unshared, and the summed physical
crossing distance (dist_um) as a detour proxy vs the direct crossing.  Info only (estimate before build)."""
import json, sys
from collections import defaultdict, deque
rows = json.load(open(sys.argv[1]))
fails = {o["port"] for o in json.load(open(sys.argv[2]))["crossings"] if not o.get("depth")}
def us(r): return max(r.get("unshared_a_ps", 0), r.get("unshared_b_ps", 0))
for U in (2500, 3400):
    g = defaultdict(dict)
    for r in rows:
        if r["src"] != r["dst"] and us(r) <= U:
            for a, b in ((r["src"], r["dst"]), (r["dst"], r["src"])):
                if b not in g[a] or us(r) < us(g[a][b]):
                    g[a][b] = r
    far = [r for r in rows if us(r) > U and r["src"] != r["dst"]]
    pairs = {}
    for r in far:
        pairs.setdefault((r["src"], r["dst"]), []).append(r)
    tot_extra = 0; nores = 0; out = []
    for (u, v), rs in sorted(pairs.items()):
        prev = {u: None}; q = deque([u])
        while q:
            x = q.popleft()
            if x == v: break
            for y in g[x]:
                if y not in prev:
                    prev[y] = x; q.append(y)
        if v not in prev:
            nores += len(rs); out.append((u, v, len(rs), None)); continue
        path = [v]
        while prev[path[-1]] is not None: path.append(prev[path[-1]])
        path.reverse()
        hops = len(path) - 1
        wu = max(us(g[a][b]) for a, b in zip(path, path[1:]))
        dsum = sum(g[a][b]["dist_um"] for a, b in zip(path, path[1:]))
        tot_extra += (hops - 1) * len(rs)
        out.append((u, v, len(rs), dict(hops=hops, worst_hop_unsh=round(wu), path_dist_um=round(dsum), direct_um=round(rs[0]["dist_um"]),
                                         direct_unsh=round(max(us(r) for r in rs)), fail=sum(r["port"] in fails for r in rs), path=path)))
    print(f"U={U}: far crossings {len(far)} in {len(pairs)} directed pairs, no path {nores}, extra hops (crossings x (hops-1)) {tot_extra}")
    for o in out:
        print("  ", o[0], "->", o[1], "n", o[2], o[3])
