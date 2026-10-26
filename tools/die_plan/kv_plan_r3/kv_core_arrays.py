#!/usr/bin/env python3
"""KV-PLAN-R3: KV core-centre arrays per module (die frame): x/y lines, repeats, irregular gaps; partition lattice."""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
tool, plan, outp = sys.argv[1:4]
sys.path.insert(0, tool)
import schema as S
import master_plan as MP
P = S.Plan(S.load(plan), Path(plan))
cen = defaultdict(list)
for part in P.parts:
    for c in MP.part_blockers(P, part, {}):
        if c[4] == "island": continue
        cen[c[5]].append((round((c[0] + c[2]) / 2, 3), round((c[1] + c[3]) / 2, 3), part, round(c[2]-c[0],2), round(c[3]-c[1],2)))
def lines(v, tol=4.32):
    v = sorted(v); out = []
    for a in v:
        if out and a - out[-1][-1] <= tol: out[-1].append(a)
        else: out.append([a])
    return [round(sum(g) / len(g), 3) for g in out]
res = dict(types={}, parts={})
allc = []
for m, cs in sorted(cen.items(), key=lambda kv: -len(kv[1])):
    xs, ys = lines([c[0] for c in cs]), lines([c[1] for c in cs])
    gx = Counter(round(b - a, 2) for a, b in zip(xs, xs[1:])); gy = Counter(round(b - a, 2) for a, b in zip(ys, ys[1:]))
    res["types"][m] = dict(n=len(cs), size=[cs[0][3], cs[0][4]], x_lines=xs[:40], x_gaps=dict(gx.most_common(8)), y_lines_n=len(ys),
                           y_gaps=dict(gy.most_common(8)), parts=dict(Counter(c[2].rsplit("_", 1)[0] for c in cs).most_common(8)),
                           x_mod_8p64=sorted({round(x % 8.64, 2) for x in xs})[:10], y_mod_8p64=sorted({round(y % 8.64, 2) for y in ys})[:10])
    allc += cs
px = Counter(); py = Counter()
for part in P.parts:
    x0, y0, x1, y1 = P.rect(part)
    res["parts"][part] = [round(v, 2) for v in (x0, y0, x1, y1)] + [P.parts[part]["type"]]
xs = lines([c[0] for c in allc], 8.64); ys = lines([c[1] for c in allc], 8.64)
res["all"] = dict(n=len(allc), x_lines=xs, x_gaps=[round(b - a, 2) for a, b in zip(xs, xs[1:])])
Path(outp).write_text(json.dumps(res, indent=1))
for m, t in res["types"].items():
    print(m, t["n"], t["size"], "xg", t["x_gaps"], "yg", t["y_gaps"], "ylines", t["y_lines_n"], t["parts"], "xmod", t["x_mod_8p64"], "ymod", t["y_mod_8p64"])
print("ALL x lines", xs); print("x gaps", res["all"]["x_gaps"])
cols = sorted({(v[0], v[2]) for v in res["parts"].values()}); rows = sorted({(v[1], v[3]) for v in res["parts"].values()})
print("part cols", cols); print("part rows", rows[:60])
print(Counter(v[4].split("_v")[0] for v in res["parts"].values()))
