#!/usr/bin/env python3
"""simulated annealing on the feed tree (edge swaps on adjacent region pairs), objective long-loop count + soft/2e4,
chain cap; starts from a retree_feed.json.  usage: anneal.py REPO PLAN BIND V START_JSON OUT_JSON ITERS SEED"""
import json, sys, random, math, collections, time, os
repo, planp, bindp, v, sj, oj, iters, seed = sys.argv[1:9]; v = float(v); iters = int(iters); random.seed(int(seed))
sys.argv = [sys.argv[0], repo, planp, bindp, str(v), "/tmp/_rt_unused", "0"]
os.environ["START"] = "fish"
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "retree.py")).read().split("F = F0\ncur = evaluate(F)")[0]
exec(src)
fj = json.load(open(sj))
A = collections.defaultdict(set)
for c, p in fj["parent"].items():
    if p: A[p].add(c); A[c].add(p)
F = rebuild(A, fj["root"]); cur = evaluate(F); cap = cur[2] * float(os.environ.get("CAPF", "1.10"))
def J(e): return e[0] + e[1] / 2e4
best = (J(cur), F, cur); T0 = float(os.environ.get("T0", "3.0")); Tm = T0; t0 = time.time()
cand = [k for k, e in E.items() if e["face_um"] > 0]
for it in range(iters):
    a, c = random.choice(cand)
    if F["parent"].get(a) == c or F["parent"].get(c) == a: continue
    cyc = path(F, a, c); i = random.randrange(len(cyc) - 1); p, q = cyc[i], cyc[i + 1]
    A2 = adj_of(F); A2[p].discard(q); A2[q].discard(p); A2[a].add(c); A2[c].add(a)
    F2 = rebuild(A2, F["root"]); ev = evaluate(F2)
    if ev[2] > cap: continue
    d = J(ev) - J(cur)
    if d <= 0 or random.random() < math.exp(-d / Tm):
        F, cur = F2, ev
        if J(cur) < best[0]: best = (J(cur), F, cur)
    Tm = max(0.05, T0 * (1 - it / iters))
    if it % 1000 == 0: print(it, "cur", cur[0], round(cur[1]), "best", best[2][0], round(best[2][1]), round(best[2][2]), f"{time.time()-t0:.0f}s", flush=True)
F = best[1]; r = best_root(adj_of(F)); F = rebuild(adj_of(F), r); ev = evaluate(F)
json.dump(dict(root=F["root"], parent=F["parent"], long=ev[0], soft=ev[1], chain_ps=ev[2]), open(oj, "w"))
print("final long", ev[0], "soft", round(ev[1]), "chain", round(ev[2]), "root", r)
