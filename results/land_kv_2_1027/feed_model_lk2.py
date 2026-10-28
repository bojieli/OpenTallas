"""LAND-KV-2 ANALYTIC (MODELLED, not a gate number): link-following region clock feed on a region map.
feed_model_lk2.py PLAN TABLE_JSON [k_ocv=0.05]
Feed = maximum-bit spanning tree of the region link graph, rooted at the graph centre; each tree hop is a forwarded
clock leg padded to ONE PERIOD (whole-cycle hop, the MESO-COUNT-1 / option (a) contract -- NOT the current ring window).
Per crossing u->v: tree hops h between the regions; unshared ~= 2*L_loc + h*P (L_loc = region-local tree ~ 0.321 ps/um x
0.75 x region span); p = k_ocv * unshared (k fitted on LAND-KV-1 lpo rows: median 0.050, max 0.078);
margin_countaligned = P/2 - p (nominal phase = whole cycles, absorbed by count alignment).  Also prints the same for the
current ZERO-CENTRED window with an unpadded forwarded hop (d = leg delay)."""
import json, sys, collections, heapq
plan, tab = sys.argv[1:3]; k = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
P = json.load(open(plan)); T = json.load(open(tab)); PER = 833.0; PSUM = 0.321
TY = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
def box(n):
    p = parts[n]; w, h = TY[p["type"]]["outline_um"]; x, y = p["origin_um"]; return (x, y, x + w, y + h)
mem = collections.defaultdict(list)
for r in T["regions"]:
    for n in r["parts"]: mem[r["tag"]].append(n)
rb = {r: (min(box(n)[0] for n in m), min(box(n)[1] for n in m), max(box(n)[2] for n in m), max(box(n)[3] for n in m)) for r, m in mem.items()}
rc = {r: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for r, b in rb.items()}
Lloc = {r: PSUM * 0.75 * max(b[2] - b[0], b[3] - b[1]) for r, b in rb.items()}
E = collections.Counter()
for q in T["ports"]: E[tuple(sorted((q["src_region"], q["dst_region"])))] += q["width"]
adj = collections.defaultdict(dict)
for (a, b), w in E.items(): adj[a][b] = w; adj[b][a] = w
# graph centre by hop eccentricity
def bfs(s):
    D = {s: 0}; Q = [s]
    for u in Q:
        for v in adj[u]:
            if v not in D: D[v] = D[u] + 1; Q.append(v)
    return D
root = min(adj, key=lambda s: (max(bfs(s).values()), s))
# max-bit spanning tree (Prim)
par = {root: None}; dep = {root: 0}; hq = [(-w, root, v) for v, w in adj[root].items()]; heapq.heapify(hq)
while hq:
    w, u, v = heapq.heappop(hq)
    if v in par: continue
    par[v] = u; dep[v] = dep[u] + 1
    for x, wx in adj[v].items():
        if x not in par: heapq.heappush(hq, (-wx, v, x))
def hops(a, b):
    h = 0
    while a != b:
        if dep[a] >= dep[b]: a = par[a]
        else: b = par[b]
        h += 1
    return h
H = collections.Counter(); m_ca = []; m_zc = []
for q in T["ports"]:
    a, b = q["src_region"], q["dst_region"]; h = hops(a, b); H[h] += 1
    un = Lloc[a] + Lloc[b] + h * PER
    m_ca.append(PER / 2 - k * un)
    dist = abs(rc[a][0] - rc[b][0]) + abs(rc[a][1] - rc[b][1])
    m_zc.append(PER / 2 - (PSUM * dist + k * (Lloc[a] + Lloc[b] + PSUM * dist)) if h == 1 else None)
zc = [m for m in m_zc if m is not None]
print(json.dumps(dict(regions=len(mem), crossings=len(T["ports"]), root=root, tree_depth=max(dep.values()),
    hop_hist=dict(sorted(H.items())), k_ocv=k,
    countaligned_padded=dict(worst=round(min(m_ca)), under0=sum(m < 0 for m in m_ca), under100=sum(m < 100 for m in m_ca)),
    zero_centred_unpadded_tree_edges=dict(n=len(zc), worst=round(min(zc)), under0=sum(m < 0 for m in zc)))))
