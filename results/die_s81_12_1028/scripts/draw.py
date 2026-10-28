import json, sys, collections
from pathlib import Path
from PIL import Image, ImageDraw
repo, planp, bindp, v, feedj, out = sys.argv[1:7]; v = float(v)
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
    fj = json.load(open(feedj)); par = fj["parent"]; order = [fj["root"]]; kids = collections.defaultdict(list)
    for c, p in par.items():
        if p: kids[p].append(c)
    i = 0
    while i < len(order): order += sorted(kids[order[i]]); i += 1
    F = dict(root=fj["root"], parent=par, order=order, kind="fish", joined=[],
             tap={(p, c): taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"]) for c, p in par.items() if p})
Tr, _ = L.arrivals(G, F, v)
xs = [g["bbox"][2] for g in G.values()]; ys = [g["bbox"][3] for g in G.values()]
S = 2400 / max(xs); Wd, Ht = int(max(xs) * S) + 20, int(max(ys) * S) + 60
im = Image.new("RGB", (Wd, Ht), "white"); dr = ImageDraw.Draw(im)
def P(x, y): return (10 + x * S, Ht - 10 - y * S)
for r, g in G.items():
    x0, y0, x1, y1 = g["bbox"]; f = min(1, Tr[r] / 16000)
    col = (int(255 * f), int(200 * (1 - abs(f - .5) * 2)) + 40, int(255 * (1 - f)))
    a, b = P(x0, y1), P(x1, y0)
    dr.rectangle([a, b], fill=tuple(int(c * .45 + 255 * .55) for c in col), outline="black")
    if (x1 - x0) * S > 40: dr.text((a[0] + 2, a[1] + 2), r, fill="black")
for c, p in F["parent"].items():
    if p:
        t = F["tap"][(p, c)]
        dr.line([P(*G[p]["cen"]), P(*t), P(*G[c]["cen"])], fill="blue", width=2)
lp = collections.Counter()
for x in X:
    b = L.branches(G, F, Tr, v, x)
    on = F["parent"].get(x["ra"]) == x["rb"] or F["parent"].get(x["rb"]) == x["ra"]
    k = tuple(sorted((x["ra"], x["rb"])))
    if not on and b["ua"] + b["ub"] > 2500: lp[k] = max(lp[k], b["ua"] + b["ub"])
for (a, b), u in lp.items():
    dr.line([P(*G[a]["cen"]), P(*G[b]["cen"])], fill="red", width=int(1 + u / 3000))
c = P(*G[F["root"]]["cen"]); dr.ellipse([c[0] - 12, c[1] - 12, c[0] + 12, c[1] + 12], fill="gold", outline="black")
dr.text((10, 5), f"S81 feed {feedj}: blue feed tree, red long-loop pairs (>2.5 ns unshared, width~ns) n_pairs={len(lp)}; fill = root arrival 0(blue)..16 ns(red); gold = root " + F["root"], fill="black")
im.save(out)
