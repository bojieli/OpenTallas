#!/usr/bin/env python3
"""DIE-S81-12 local-form re-tree (ESTIMATE): start from the CLK-LOCAL-EST-1 'fish' feed (max-bits spanning tree on the
398-region map), then edge-swap local search on the feed tree so that heavy loop-closing neighbour links become tree
edges (each move = add one off-feed adjacent region pair, drop one edge on its tree cycle).  Objective, lexicographic:
(1) long-loop crossings (off-feed, unshared ua+ub > 2.5 ns), (2) sum bits x max(0, unshared - 1.5 ns), subject to the
forwarded chain arrival not growing over CHAIN_CAP.  Model = tools/die_plan/locality.py unchanged (fish feed, spine
hop delay, branches(), margins via the shared clk_aocv g021 table + droop + spice-scaled v); CA rows via
cap_reading (count_align_plan unchanged).  usage: retree.py REPO PLAN BIND V OUTDIR [max_sweeps]"""
import json, sys, collections, time, copy
from pathlib import Path
repo, planp, bindp, v, outd = sys.argv[1:6]
sweeps = int(sys.argv[6]) if len(sys.argv) > 6 else 4
import os
OBJ = os.environ.get("OBJ", "count")
CAPF = float(os.environ.get("CAPF", "1.05"))
START = os.environ.get("START", "fish")
v = float(v); outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
D = L.load_plan(planp)
bind = json.loads(Path(bindp).read_text())
reg = {p: x["region"] for p, x in bind["parts"].items() if isinstance(x, dict) and x.get("region")}
for p in D["parts"]:
    reg.setdefault(p, p)
padj = L.part_adjacency(D)
G = L.region_geom(D, reg)
X = L.crossings(D, reg, G, padj)
E = L.region_graph(D, reg, padj, X)
taps = L.tap_points(G, X)
F0 = L.feed_tree(G, E, X, v, "fish") if START == "fish" else None
LONG, SOFT = 2500.0, 1500.0

def tap(p, c):
    return taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"])

def rebuild(adj, root):
    parent, order = {root: None}, [root]
    i = 0
    while i < len(order):
        p = order[i]; i += 1
        for c in sorted(adj[p]):
            if c not in parent:
                parent[c] = p; order.append(c)
    return dict(root=root, parent=parent, order=order, tap={(p, c): tap(p, c) for c, p in parent.items() if p},
                joined=F0["joined"], kind="fish")

def evaluate(F):
    Tr, _ = L.arrivals(G, F, v)
    tot = 0; soft = 0.0; nlong = 0; rows = []
    for x in X:
        b = L.branches(G, F, Tr, v, x)
        on = F["parent"].get(x["ra"]) == x["rb"] or F["parent"].get(x["rb"]) == x["ra"]
        u = b["ua"] + b["ub"]
        if not on and u > LONG:
            nlong += 1
        soft += x["width"] * max(0.0, u - SOFT) / 1000.0
        rows.append((x, b, on, u))
    chain = max(Tr[r] + L.ins(G[r], v) for r in Tr)
    return (nlong, soft, chain, rows)

def adj_of(F):
    a = collections.defaultdict(set)
    for c, p in F["parent"].items():
        if p:
            a[p].add(c); a[c].add(p)
    return a

def path(F, a, b):
    la, lb = L.lineage(F, a), L.lineage(F, b)
    sb = set(lb); l = next(r for r in la if r in sb)
    return la[:la.index(l) + 1] + list(reversed(lb[:lb.index(l)]))

def best_root(adj):
    best = None
    for r in sorted(adj):
        F = rebuild(adj, r)
        Tr, _ = L.arrivals(G, F, v)
        ecc = max(Tr.values())
        if best is None or ecc < best[0]:
            best = (ecc, r)
    return best[1]

F = F0
cur = evaluate(F)
log = [dict(step="fish", long=cur[0], soft=round(cur[1]), chain_ps=round(cur[2]))]
print("start", log[-1], flush=True)
CHAIN_CAP = cur[2] * CAPF
key = (lambda e: (e[0], e[1])) if OBJ == "count" else (lambda e: (e[1], e[0]))
t0 = time.time()
for sw in range(sweeps):
    improved = 0
    pb = collections.Counter()
    for x, b, on, u in cur[3]:
        if not on and u > SOFT:
            pb[tuple(sorted((x["ra"], x["rb"])))] += x["width"] * (u - SOFT)
    for (a, c), _ in pb.most_common():
        if (a, c) not in E or E[(a, c)]["face_um"] <= 0:
            continue
        if F["parent"].get(a) == c or F["parent"].get(c) == a:
            continue
        cyc = path(F, a, c)
        best = None
        A = adj_of(F)
        for i in range(len(cyc) - 1):
            p, q = cyc[i], cyc[i + 1]
            A2 = {k: set(s) for k, s in A.items()}
            A2[p].discard(q); A2[q].discard(p)
            A2.setdefault(a, set()).add(c); A2.setdefault(c, set()).add(a)
            F2 = rebuild(A2, F["root"])
            if len(F2["parent"]) != len(F["parent"]):
                continue
            ev = evaluate(F2)
            if ev[2] > CHAIN_CAP:
                continue
            if best is None or key(ev) < key(best[0]):
                best = (ev, F2, (p, q))
        if best and key(best[0]) < key(cur):
            cur, F = best[0], best[1]
            improved += 1
            log.append(dict(step=f"s{sw}", add=[a, c], drop=list(best[2]), long=cur[0], soft=round(cur[1]),
                            chain_ps=round(cur[2])))
    # re-root for the shortest chain, keep the topology
    r = best_root(adj_of(F))
    F = rebuild(adj_of(F), r)
    cur = evaluate(F)
    if cur[2] > CHAIN_CAP:
        CHAIN_CAP = cur[2]
    print(f"sweep {sw}: moves {improved} long {cur[0]} soft {cur[1]:.0f} chain {cur[2]:.0f} root {r} t {time.time()-t0:.0f}s",
          flush=True)
    if not improved:
        break
json.dump(dict(root=F["root"], parent=F["parent"], log=log, cap_ps=CHAIN_CAP), open(outd / "retree_feed.json", "w"), indent=0)
print("done", log[-1])
