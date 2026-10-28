import json, sys, collections, re
from pathlib import Path
repo, planp, bindp, v, feedj = sys.argv[1:6]; v = float(v)
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
D = L.load_plan(planp)
bind = json.loads(Path(bindp).read_text())
reg = {p: x["region"] for p, x in bind["parts"].items() if isinstance(x, dict) and x.get("region")}
for p in D["parts"]: reg.setdefault(p, p)
padj = L.part_adjacency(D); G = L.region_geom(D, reg); X = L.crossings(D, reg, G, padj); E = L.region_graph(D, reg, padj, X)
taps = L.tap_points(G, X)
if feedj == "fish":
    F = L.feed_tree(G, E, X, v, "fish")
else:
    fj = json.load(open(feedj))
    par = fj["parent"]; order = [fj["root"]]; kids = collections.defaultdict(list)
    for c, p in par.items():
        if p: kids[p].append(c)
    i = 0
    while i < len(order):
        order += sorted(kids[order[i]]); i += 1
    F = dict(root=fj["root"], parent=par, order=order, kind="fish", joined=[],
             tap={(p, c): taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"]) for c, p in par.items() if p})
Tr, _ = L.arrivals(G, F, v)
cls = collections.Counter(); pairs = collections.Counter(); hist = collections.Counter()
def fam(r): return re.sub(r"\d+", "#", r)
for x in X:
    b = L.branches(G, F, Tr, v, x)
    on = F["parent"].get(x["ra"]) == x["rb"] or F["parent"].get(x["rb"]) == x["ra"]
    u = b["ua"] + b["ub"]
    if not on and u > 2500:
        pairs[tuple(sorted((x["ra"], x["rb"])))] += 1
        cls[tuple(sorted((fam(x["ra"]), fam(x["rb"]))))] += 1
        hist[int(u // 2000) * 2] += 1
print("long", sum(pairs.values()), "pairs", len(pairs))
print("unshared ns hist (2ns bins)", sorted(hist.items()))
print("family pairs", cls.most_common(25))
