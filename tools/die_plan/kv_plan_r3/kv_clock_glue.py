#!/usr/bin/env python3
"""KV-PLAN-R3: mesh drivers / H-tree nodes vs KV core outlines: share inside cores, nearest-glue displacement,
full-width glue rows/cols per partition type (candidate pushdown island lattice)."""
import json, sys, math
from collections import defaultdict, Counter
from pathlib import Path
tool, plan, mesh, outp = sys.argv[1:5]
sys.path.insert(0, tool)
import schema as S
import master_plan as MP
P = S.Plan(S.load(plan), Path(plan))
M = json.loads(Path(mesh).read_text())
cores = []
for part in P.parts:
    for c in MP.part_blockers(P, part, {}):
        if c[4] != "island": cores.append((c[0], c[1], c[2], c[3], part, c[5]))
# bucket cores by 200-um tiles
B = 200.0
bk = defaultdict(list)
for c in cores:
    for i in range(int(c[0] // B), int(c[2] // B) + 1):
        for j in range(int(c[1] // B), int(c[3] // B) + 1):
            bk[(i, j)].append(c)
def incore(x, y, m=4.32):
    return next((c for c in bk[(int(x // B), int(y // B))] if c[0] - m < x < c[2] + m and c[1] - m < y < c[3] + m), None)
def nearest_glue(x, y):
    c = incore(x, y)
    if not c: return 0.0, "x"
    best = None
    for dx, dy, ax in ((c[0] - 4.32 - x, 0, "x"), (c[2] + 4.32 - x, 0, "x"), (0, c[1] - 4.32 - y, "y"), (0, c[3] + 4.32 - y, "y")):
        if incore(x + dx, y + dy) is None:
            d = abs(dx) + abs(dy)
            if best is None or d < best[0]: best = (d, ax)
    return best if best else (999.0, "?")
pts = [("driver", d["site"]) for d in M["drivers"].values()]
for h in M["htree"]:
    pts.append(("node", h["a"]))
res = {}
for kind in ("driver", "node"):
    ps = [p for k, p in pts if k == kind]
    dd = [nearest_glue(*p) for p in ps]
    inn = [d for d in dd if d[0] > 0]
    mods = Counter(incore(*p)[5] for p in ps if incore(*p))
    ds = sorted(d[0] for d in inn)
    res[kind] = dict(n=len(ps), in_core=len(inn), max_disp=round(ds[-1], 2) if ds else 0, p50=round(ds[len(ds)//2], 2) if ds else 0,
                     p90=round(ds[int(len(ds)*0.9)], 2) if ds else 0, over_60=sum(1 for d in ds if d > 60), over_108=sum(1 for d in ds if d > 108),
                     by_core=dict(mods.most_common(12)))
# full-width glue rows (y) per representative partition type
rows = {}
for part in ("hg_EN_1", "hgi_EN_1", "hg_WN_1", "pv_N_1", "pc_EN_1", "hub_Wi", "hub_Ei", "hub_C", "hub_Eo", "hub_Wo", "hroot_EN" if "hroot_EN" in P.parts else None):
    if not part or part not in P.parts: continue
    x0, y0, x1, y1 = P.rect(part)
    bl = [c for c in cores if c[4] == part]
    ys = sorted({v for c in bl for v in (c[1], c[3])} | {y0, y1})
    fr = [(round(a, 2), round(b, 2)) for a, b in zip(ys, ys[1:]) if b - a > 2 and not any(c[1] < (a + b) / 2 < c[3] for c in bl)]
    xs = sorted({v for c in bl for v in (c[0], c[2])} | {x0, x1})
    fc = [(round(a, 2), round(b, 2)) for a, b in zip(xs, xs[1:]) if b - a > 2 and not any(c[0] < (a + b) / 2 < c[2] for c in bl)]
    rows[part] = dict(rect=[round(v, 2) for v in (x0, y0, x1, y1)], glue_rows_y=fr, glue_cols_x=fc, n_cores=len(bl),
                      core_area_frac=round(sum((c[2]-c[0])*(c[3]-c[1]) for c in bl)/((x1-x0)*(y1-y0)), 3))
res["glue"] = rows
res["mesh_meta"] = {k: M["meta"].get(k) for k in ("nx", "ny", "pitch_um")}
Path(outp).write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1)[:9000])
