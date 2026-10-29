import json, sys, collections
tree, arrTT, arrFF, part, out = sys.argv[1:6]
t = json.load(open(tree)); N = t["nodes"]
taps = [x for x in t["taps"] if x["part"] == part]
def anc(n):
    r = []
    while n is not None:
        r.append(n); n = N[str(n)].get("parent")
    return r
paths = [anc(x["node"]) for x in taps]
common = set(paths[0])
for p in paths[1:]: common &= set(p)
lca = max(common, key=lambda n: N[str(n)]["level"])
sub = set()
for p in paths:
    for n in p:
        if n == lca: break
        sub.add(n)
keys = collections.Counter(k for n in sub for k in N[str(n)])
print("ntaps", len(taps), "lca", lca, N[str(lca)], "subnodes", len(sub), keys)
odd = {k: v for k, v in N[str(lca)].items()}
def rd(f):
    a = {}
    for l in open(f):
        s = l.split()
        if s and s[0] == "T": a[s[1]] = (float(s[2]), float(s[3]) if len(s) > 3 else None, float(s[4]) if len(s) > 4 else None)
    return a
A = {"TT": rd(arrTT), "FF": rd(arrFF)}
early = {}
for n in sub:
    d = N[str(n)]
    for k in d:
        if "early" in k or "delay" in k or "sink" in k: early.setdefault(k, []).append((n, d[k]))
print("early-ish keys", {k: v[:5] for k, v in early.items()})
res = dict(part=part, lca=lca, lca_node=N[str(lca)], taps=[])
for x, p in zip(taps, paths):
    d = N[str(x["node"])]
    res["taps"].append(dict(port=x["port"], xy=x["xy"], depth_below_lca=p.index(lca), node=d,
                            TT=A["TT"].get(x["port"]), FF=A["FF"].get(x["port"])))
for c in ("TT", "FF"):
    v = [(r[c][0], r["port"]) for r in res["taps"] if r[c]]
    print(c, "n", len(v), "min", min(v), "max", max(v), "spread", round(max(v)[0] - min(v)[0], 1))
json.dump(res, open(out, "w"), indent=1)
