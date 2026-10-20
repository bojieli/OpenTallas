"""QW-CB16A0 10-20: exact grid placement of every CB16 fullm(b) scalar/reset control FF (arc consistency + forest assignment).

Grid GRID um over the outline; a cell is legal when it is outside every hard child + HALO, outside every reserved ring bay +
BAYPAD and inside the outline margin.  Every control edge (scalar d, q fanout, hard rst_n / sidx pins, ring-bay rsi to the
bay's FAR corner, ports) must be Manhattan <= REFF.  Domains are pruned to arc consistency (taxicab distance transform);
on a forest AC is exact, so an empty domain proves infeasibility of THIS grid/halo model and a non-empty fixpoint yields an
assignment (closest-to-hint unoccupied grid site per node, children chosen consistently from the root).  Cycles are checked explicitly.
"""
import json, sys, collections, hashlib, pathlib
import numpy as np
from scipy import ndimage

inp = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); d = json.loads(inp.read_text())
GRID, HALO, BAYPAD, EDGE = 10.8, 10.8, 4.32, 10.8
REFF = float(sys.argv[3]) if len(sys.argv) > 3 else 385.0
W, H = d["outline"]; S = d["scalar"]; names = sorted(S)
nx, ny = int((W - 2 * EDGE) // GRID) + 1, int((H - 2 * EDGE) // GRID) + 1
gx = EDGE + GRID * np.arange(nx); gy = EDGE + GRID * np.arange(ny)
X, Y = np.meshgrid(gx, gy, indexing="ij")
legal = np.ones((nx, ny), bool)
for (hx, hy, hw, hh) in d["hard"].values():
    legal &= ~((X > hx - HALO) & (X < hx + hw + HALO) & (Y > hy - HALO) & (Y < hy + hh + HALO))
for (bx, by, bw, bh) in d["bays"].values():
    legal &= ~((X > bx - BAYPAD) & (X < bx + bw + BAYPAD) & (Y > by - BAYPAD) & (Y < by + bh + BAYPAD))
RG = int(np.floor(REFF / GRID + 1e-9))

def ends(e):
    if "point" in e: return ("f", [tuple(e["point"])])
    if "node" in e: return ("v", e["node"])
    x, y, w, h = e["box"]; return ("f", [(x, y), (x + w, y), (x, y + h), (x + w, y + h)])

adj = collections.defaultdict(set); fixed = collections.defaultdict(list); nedge = collections.Counter()
for e in d["edges"]:
    a, b = ends(e["src"]), ends(e["dst"]); nedge[e["kind"]] += 1
    if a[0] == "v" and b[0] == "v": adj[a[1]].add(b[1]); adj[b[1]].add(a[1])
    elif a[0] == "v": fixed[a[1]].append(b[1])
    else: fixed[b[1]].append(a[1])
dom = {}
for n in names:
    m = legal.copy()
    for pts in fixed[n]:
        for (px, py) in pts: m &= (np.abs(X - px) + np.abs(Y - py)) <= REFF
    dom[n] = m

def dil(m):
    if not m.any(): return m
    dt = ndimage.distance_transform_cdt(~m, metric="taxicab"); return dt <= RG

queue = collections.deque(names); inq = set(names); rounds = 0
while queue:
    n = queue.popleft(); inq.discard(n); rounds += 1
    dn = dil(dom[n])
    for v in adj[n]:
        nm = dom[v] & dn
        if nm.sum() != dom[v].sum():
            dom[v] = nm
            if v not in inq: queue.append(v); inq.add(v)
empty = [n for n in names if not dom[n].any()]
# cycle check (forest => AC exact)
seen = set(); cyc = 0
for r in names:
    if r in seen: continue
    st = [(r, None)]; seen.add(r)
    while st:
        u, p = st.pop()
        for v in adj[u]:
            if v == p: continue
            if v in seen: cyc += 1; continue
            seen.add(v); st.append((v, u))
res = dict(name=d["name"], grid_um=GRID, halo_um=HALO, baypad_um=BAYPAD, reff_um=REFF, legal_cells=int(legal.sum()), nodes=len(names),
           edges=dict(nedge), cycles_back_edges=cyc // 2, ac_rounds=rounds, empty=empty[:50], n_empty=len(empty),
           input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest())
if empty:
    res["status"] = "INFEASIBLE_AC"
    res["empty_detail"] = {n: dict(hint=S[n]["hint"], fixed=fixed[n], nbrs=sorted(adj[n])) for n in empty[:12]}
else:
    pos = {}; occ = np.zeros((nx, ny))
    order = []; seen = set()
    for r in sorted(names, key=lambda n: -len(fixed[n])):
        if r in seen: continue
        st = [r]; seen.add(r)
        while st:
            u = st.pop(); order.append(u)
            for v in sorted(adj[u]):
                if v not in seen: seen.add(v); st.append(v)
    for n in order:
        m = dom[n].copy()
        for v in adj[n]:
            if v in pos:
                px, py = pos[v]; m &= (np.abs(X - px) + np.abs(Y - py)) <= RG * GRID + 1e-6
        if not m.any(): res.setdefault("assign_fail", []).append(n); continue
        hx, hy = S[n]["hint"]; cost = np.where(m, np.abs(X - hx) + np.abs(Y - hy) + 1e4 * occ, np.inf); i, j = np.unravel_index(np.argmin(cost), cost.shape); occ[i, j] += 1
        pos[n] = (float(gx[i]), float(gy[j]))
    res["status"] = "FEASIBLE" if not res.get("assign_fail") else "ASSIGN_FAIL"
    res["pos"] = {n: [round(p[0], 3), round(p[1], 3)] for n, p in pos.items()}
    res["moved_max_um"] = round(max(abs(pos[n][0] - S[n]["hint"][0]) + abs(pos[n][1] - S[n]["hint"][1]) for n in pos), 1)
out.write_text(json.dumps(res, indent=1) + "\n")
print("CONTROL_AC", d["name"], res["status"], "empty", len(empty), "cycles", res["cycles_back_edges"], "moved_max", res.get("moved_max_um"))
