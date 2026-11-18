#!/usr/bin/env python3
"""FABLE-DIE-QC 11-17: rebuild the QC die clock-chain inputs (region map + comb feed) from a finished die_trial kit
tree.json (the M4 clock of record).  usage: recon.py TREE.json BASE_MAP.json OUT_DIR"""
import json, sys, hashlib, collections
t = json.load(open(sys.argv[1])); base = json.load(open(sys.argv[2])); out = sys.argv[3]
n = t["nodes"]
def region_of(i):
    while i is not None:
        x = n[str(i)]
        if "region_root" in x: return x["region_root"]
        i = x["parent"]
pr = {}; bad = []
for tp in t["taps"]:
    r = region_of(tp["node"]); p = tp["part"]
    if pr.setdefault(p, r) != r: bad.append((p, pr[p], r))
par = {}
for x in n.values():
    e = x.get("feed_edge")
    if e:
        a, b = e.split("->"); assert par.setdefault(b, a) == a
root = t["meta"]["link_feed"]["root"]; par[root] = None
bm = base["part_region"]
diff = {p: (bm.get(p), r) for p, r in pr.items() if bm.get(p) != r}
only_base = sorted(set(bm) - set(pr))
print("parts with taps", len(pr), "regions", len(set(pr.values())), "conflicts", len(bad), "feed nodes", len(par), "root", root)
print("vs base map: base parts", len(bm), "differ", len(diff), list(diff.items())[:12], "only in base", len(only_base), only_base[:12])
# map in base order, new parts appended
m = {p: pr.get(p, bm[p]) for p in bm}; m.update({p: r for p, r in pr.items() if p not in m})
def dep(r):
    d = 0
    while par[r]: r = par[r]; d += 1
    return d
fo = collections.Counter(v for v in par.values() if v)
print("feed depth max", max(dep(r) for r in par), "fanout max", max(fo.values()), "regions in map", len(set(m.values())), "map==feed", set(m.values()) == set(par))
for ind in (0, 1, None):
    s = json.dumps({"part_region": m}, indent=ind); print("map sha indent", ind, hashlib.sha256(s.encode()).hexdigest()[:12], hashlib.sha256((s+"\n").encode()).hexdigest()[:12])
json.dump({"part_region": m}, open(out + "/regions_s3d.json", "w"), indent=0)
json.dump(dict(root=root, parent=par, joined=[], tap={}), open(out + "/feed_comb_fw_3.json", "w"), indent=0)
print("dme_regions", len(t["meta"]["link_feed"]["dme_regions"]))
json.dump(sorted(t["meta"]["link_feed"]["dme_regions"]), open(out + "/dme_regions.json", "w"))
