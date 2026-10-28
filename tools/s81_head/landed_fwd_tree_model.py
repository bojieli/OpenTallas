"""LAND-HEAD-3 model-only: neighbour-forwarded region clocks along the link graph (12.13b form).
Region clock of each partition = forwarded from a neighbour along a minimum spanning tree (Prim, Manhattan entry distance)
of the plan's crossing graph, rooted at ROOT; each forwarded leg = L-leg with BUFx24 repeaters every rep_um. Writes tree.json
in die_trial format for landed_topo_model.py."""
import json, sys, heapq, collections
plan = json.load(open(sys.argv[1])); base = json.load(open(sys.argv[2])); out = sys.argv[3]
ROOT = sys.argv[4] if len(sys.argv) > 4 else "sp2"; REP = 450.0
xy = {t["part"]: t["xy"] for t in base["taps"]}
adj = collections.defaultdict(set)
for p in plan["ports"]:
    a, b = p["src"]["part"], p["dst"]["part"]
    if a in xy and b in xy and a != b: adj[a].add(b); adj[b].add(a)
D = lambda a, b: abs(xy[a][0]-xy[b][0]) + abs(xy[a][1]-xy[b][1])
par = {ROOT: None}; h = [(D(ROOT, n), ROOT, n) for n in adj[ROOT]]; heapq.heapify(h)
while h:
    d, u, v = heapq.heappop(h)
    if v in par: continue
    par[v] = u
    for w in adj[v]:
        if w not in par: heapq.heappush(h, (D(v, w), v, w))
assert len(par) == len(xy), (len(par), len(xy))
sites, parent_of, node_buf, taps = {}, {}, {}, []
ids = {n: i for i, n in enumerate(sorted(par, key=lambda n: (n != ROOT, n)))}
for n, i in ids.items():
    node_buf[str(i)] = f"b{i}"; sites[f"b{i}"] = list(xy[n])
    taps.append(dict(port=f"t_{n}__clk", part=n, tap="clk", xy=list(xy[n]), node=i))
for n, u in par.items():
    if u is None: continue
    i = ids[n]; (x0, y0), (x1, y1) = xy[u], xy[n]
    pts = [(x0, y0), (x1, y0), (x1, y1)]
    L = D(u, n); k = max(0, int(-(-L // REP)) - 1); prev = f"b{ids[u]}"
    for j in range(k):
        s = L * (j + 1) / (k + 1)
        hx = abs(x1 - x0)
        p = (x0 + (x1 - x0) * min(1, s / hx) if hx else x0, y0 if s <= hx else y0 + (y1 - y0) * (s - hx) / max(1e-9, abs(y1 - y0)))
        r = f"r{i}_{j}"; sites[r] = [round(p[0], 3), round(p[1], 3)]; parent_of[r] = prev; prev = r
    parent_of[f"b{i}"] = prev
json.dump(dict(meta=dict(form="link_forwarded_mst", root=ROOT, rep_um=REP), taps=taps, node_buf=node_buf,
               parent_of=parent_of, sites=sites), open(out, "w"))
depth = {}
def dep(n): return 0 if par[n] is None else dep(par[n]) + 1
print("forwarded hops max", max(dep(n) for n in par), "links in tree", len(par) - 1, "graph edges", sum(len(v) for v in adj.values()) // 2)
