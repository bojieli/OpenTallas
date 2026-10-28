#!/usr/bin/env python3
"""current clock topology from tap_arrivals tree_path: region root = LCP of its taps' tree_path, parent region = the
region whose root is the longest proper prefix; per crossing (cur.json rows) the region-tree relation."""
import json, sys, collections, os
proof, bindp, curp = sys.argv[1:4]
t = json.load(open(os.path.join(proof, "tap_arrivals_TT.json"))); bind = json.load(open(bindp))
pr = {p: v["region"] for p, v in bind["parts"].items() if isinstance(v, dict) and v.get("region")}
nl = t["node_late_ps"]
paths = collections.defaultdict(list); arr = collections.defaultdict(list)
for x in t["taps"]:
    r = pr.get(x["part"])
    if r and "tree_path" in x: paths[r].append(x["tree_path"]); arr[r].append(x["late_ps"])
def lcp(ps):
    s = min(ps); e = max(ps); n = 0
    while n < min(len(s), len(e)) and s[n] == e[n]: n += 1
    return s[:n]
root = {r: lcp(p) for r, p in paths.items()}
par = {}
for r, p in root.items():
    best = None
    for q, pq in root.items():
        if q != r and len(pq) < len(p) and p.startswith(pq) and (best is None or len(pq) > len(root[best])): best = q
    par[r] = best
def lineage(r):
    out = [r]
    while par[out[-1]] is not None: out.append(par[out[-1]])
    return out
dep = {r: len(lineage(r)) - 1 for r in root}
rootarr = {r: nl.get(p) for r, p in root.items()}
print("regions", len(root), "top-level (parent None)", sum(1 for r in par if par[r] is None),
      "region-tree depth hist", sorted(collections.Counter(dep.values()).items()))
print("region root path length (tree levels) med/max", sorted(len(p) for p in root.values())[len(root)//2], max(len(p) for p in root.values()))
ra = [v for v in rootarr.values() if v is not None]; ra.sort()
print("region root arrival TT ns: min %.2f med %.2f max %.2f" % (ra[0]/1e3, ra[len(ra)//2]/1e3, ra[-1]/1e3))
ins = sorted((max(arr[r]) - (rootarr[r] or 0)) for r in root if rootarr[r] is not None)
print("in-region insertion (root->tap max) TT ns: med %.2f max %.2f" % (ins[len(ins)//2]/1e3, ins[-1]/1e3))
cur = json.load(open(curp)); rel = collections.Counter(); hops = collections.Counter()
for r in cur["rows"]:
    a, b = r["tag"].split("->")
    if a not in root or b not in root: rel["no-root"] += 1; continue
    la, lb = lineage(a), lineage(b); sb = set(lb)
    L = next((q for q in la if q in sb), None)
    h = (la.index(L) + lb.index(L)) if L else len(la) + len(lb)
    hops[min(h, 20)] += 1
    rel["tree-edge" if h == 1 else ("no common region (die root)" if L is None else "loop via region")] += 1
print("crossing relation:", dict(rel)); print("region-tree hops between crossing regions:", sorted(hops.items()))
json.dump(dict(parent=par, root_path=root, root_arr=rootarr), open(os.path.join(os.path.dirname(curp), "cur_topo.json"), "w"))
