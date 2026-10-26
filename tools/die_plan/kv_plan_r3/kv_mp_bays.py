#!/usr/bin/env python3
"""KV-PLAN-R3: bay_fill overlap analysis (which cores, nearest legal glue along the route, free glue columns of the
partition type) + hub column bit sums + core-centre array characterisation per core type."""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
tool, plan, mpd, outp = sys.argv[1:5]
sys.path.insert(0, tool)
import schema as S
import master_plan as MP
P = S.Plan(S.load(plan), Path(plan))
G = json.loads((Path(mpd) / "gates.json").read_text())["gates"]
R = json.loads((Path(mpd) / "roads.json").read_text())
fails = [b for b in R["bays"] if b["issues"]]
out = dict(n_fail=len(fails))
out["by_part_core"] = Counter(f"{b['part']}|{b['issues'][0]}|{b['path']}|{b['kind']}|{b['bits']}" for b in fails).most_common(100)
out["by_type"] = Counter(b["type"] for b in fails).most_common()
# per failing bay: blocker rect, free y-intervals along a vertical route at that x inside partition
def free_iv(part, x, horiz, coord):
    x0, y0, x1, y1 = P.rect(part)
    bl = [c for c in MP.part_blockers(P, part, {}) if c[4] != "island"]
    if not horiz:
        occ = sorted((c[1], c[3], c[4]) for c in bl if c[0] - 1 <= x <= c[2] + 1)
        lo, hi = y0, y1
    else:
        occ = sorted((c[0], c[2], c[4]) for c in bl if c[1] - 1 <= coord <= c[3] + 1)
        lo, hi = x0, x1
    ivs, cur = [], lo
    for a, b, n in occ:
        if a > cur + 1: ivs.append((round(cur, 1), round(a, 1)))
        cur = max(cur, b)
    if hi > cur + 1: ivs.append((round(cur, 1), round(hi, 1)))
    return ivs, [(round(a, 1), round(b, 1), n) for a, b, n in occ]
ex = {}
for b in fails:
    k = (b["part"], b["path"])
    if k in ex: continue
    x, y = b["xy_um"]
    iv, occ = free_iv(b["part"], x, b["horiz"], y)
    ex[k] = dict(xy=b["xy_um"], horiz=b["horiz"], bits=b["bits"], band=b["band"], issue=b["issues"], part_rect=[round(v, 1) for v in P.rect(b["part"])],
                 free_glue_along_route=iv, cores_on_route=occ)
out["examples"] = {f"{k[0]}|{k[1]}": v for k, v in list(ex.items())[:40]}
# free vertical glue columns in each failing type's partitions: x-ranges where no core overlaps full height
cols = {}
for part in sorted({b["part"] for b in fails}):
    x0, y0, x1, y1 = P.rect(part)
    bl = [c for c in MP.part_blockers(P, part, {}) if c[4] != "island"]
    xs = sorted({round(v, 2) for c in bl for v in (c[0], c[2])} | {round(x0, 2), round(x1, 2)})
    free = []
    for a, b2 in zip(xs, xs[1:]):
        m = (a + b2) / 2
        if not any(c[0] < m < c[2] for c in bl) and b2 - a > 2: free.append((a, b2))
    cols[part] = dict(rect=[round(v, 1) for v in (x0, y0, x1, y1)], full_height_free_x=free,
                      cores=sorted({(c[5], round(c[2] - c[0], 1), round(c[3] - c[1], 1)) for c in bl}))
out["free_cols"] = cols
# hub columns: sum bits of vertical roads per (part, x gcell, layer)
col = defaultdict(int)
for rd in R["roads"]:
    if rd["part"].startswith("hub") and abs(rd["a"][0] - rd["b"][0]) < 1e-6:
        col[(rd["part"], round(rd["a"][0], 1), rd["layer"])] += rd["bits"]
out["hub_vertical_columns"] = sorted(([k[0], k[1], k[2], v] for k, v in col.items()), key=lambda t: -t[3])[:30]
hubx = defaultdict(int)
for (p, x, L), v in col.items(): hubx[(p, x)] += v
out["hub_vertical_x_total"] = sorted(([k[0], k[1], v] for k, v in hubx.items()), key=lambda t: -t[2])[:20]
for p in P.parts:
    if p.startswith("hub") or p in ("hroot", "sys_c"):
        out.setdefault("hub_rects", {})[p] = [round(v, 1) for v in P.rect(p)]
Path(outp).write_text(json.dumps(out, indent=1, default=str))
