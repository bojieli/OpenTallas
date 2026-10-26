#!/usr/bin/env python3
"""KV-PLAN-R3: replay master-plan roads.json on the plan's gcell grid and attribute corridor_tracks over-use
(per layer, per path, per partition/type, self-overflow from narrow bands vs aggregation) + bay overlap + core lattice.
usage: kv_mp_roads_attr.py <master_plan tool dir> <plan.json> <mp out dir> <out.json>"""
import json, math, sys
from collections import defaultdict, Counter
from pathlib import Path
tool, plan, mpd, outp = sys.argv[1:5]
sys.path.insert(0, tool)
import numpy as np
import schema as S
import master_plan as MP
P = S.Plan(S.load(plan), Path(plan))
R = json.loads((Path(mpd) / "roads.json").read_text())
G = MP.G
blk = {p: MP.part_blockers(P, p, {}) for p in P.parts}
cores = [r[:4] for b in blk.values() for r in b if r[4] != "island"]
grid = MP.Grid(P, P.die.get("pg", {}).get("grid", []), None, 0.25, "M5", [], cores)
cap0 = {L: float(grid.cap[L].max()) for L in grid.cap}
contrib = {L: defaultdict(list) for L in grid.cap}   # not per cell (too big): per road record its slice
recs = []
for k, rd in enumerate(sorted(R["roads"], key=lambda s: -s["bits"])):
    sl, horiz = grid.band(rd["a"], rd["b"], rd["band_um"])
    add = grid.load(rd["layer"], sl, horiz, rd["bits"])
    if add is None:
        continue
    i0, j0, i1, j1 = sl
    across = (j1 - j0) if horiz else (i1 - i0)
    self_use = float((add / np.maximum(grid.cap[rd["layer"]][j0:j1, i0:i1], 1e-9)).max())
    grid.commit(rd["layer"], sl, add)
    L = abs(rd["a"][0] - rd["b"][0]) + abs(rd["a"][1] - rd["b"][1])
    recs.append(dict(k=k, sl=sl, add=add, rd=rd, self_use=self_use, across=across, len=L, horiz=horiz))
use = {}
for L in grid.cap:
    with np.errstate(divide="ignore", invalid="ignore"):
        use[L] = np.where(grid.cap[L] > 0, grid.dem[L] / np.maximum(grid.cap[L], 1e-9), 0)
over = {L: use[L] > 0.6 + 1e-6 for L in use}
# attribution: per road, number of over cells it touches and its share of over demand
agg_type = defaultdict(lambda: defaultdict(float)); agg_path = defaultdict(lambda: dict(cells=0, bits=0, over_dem=0.0))
selfover = Counter(); selfover_bits = Counter(); aggr_only = Counter()
for r in recs:
    L = r["rd"]["layer"]; i0, j0, i1, j1 = r["sl"]
    ov = over[L][j0:j1, i0:i1]
    if not ov.any():
        continue
    od = float((r["add"] * ov).sum())
    t = P.parts[r["rd"]["part"]]["type"]
    agg_type[(L, t)]["over_dem"] += od
    agg_type[(L, t)]["roads"] += 1
    agg_type[(L, t)]["bitmm"] += r["rd"]["bits"] * r["len"] / 1000
    key = (L, r["rd"]["path"], r["rd"]["part"])
    a = agg_path[key]; a["cells"] += int(ov.sum()); a["bits"] = r["rd"]["bits"]; a["over_dem"] += od
    a["band"] = r["rd"]["band_um"]; a["self_use"] = max(a.get("self_use", 0), r["self_use"]); a["type"] = t
    if r["self_use"] > 0.6:
        selfover[L] += 1; selfover_bits[L] += r["rd"]["bits"]
    else:
        aggr_only[L] += 1
# band-width stats for all roads per layer
bandhist = {L: Counter() for L in grid.cap}
for r in recs:
    bandhist[r["rd"]["layer"]][(r["across"], "self>0.6" if r["self_use"] > 0.6 else "ok")] += 1
# tracks needed vs available per over-road: needed width = bits/(0.6*cap per gcell)
need = []
for (L, pid, part), a in sorted(agg_path.items(), key=lambda kv: -kv[1]["over_dem"])[:60]:
    w_need = a["bits"] / (0.6 * cap0[L]) * G
    need.append(dict(layer=L, path=pid, part=part, type=a["type"], bits=a["bits"], band_um=a["band"],
                     self_use=round(a["self_use"], 3), over_cells=a["cells"], band_needed_um_at_0p6=round(w_need, 1)))
# over cells: per partition (location)
cell_part = defaultdict(Counter)
for p in P.parts:
    x0, y0, x1, y1 = P.rect(p)
    i0, j0, i1, j1 = grid.idx((x0, y0, x1, y1))
    for L in over:
        n = int(over[L][j0:j1, i0:i1].sum())
        if n:
            cell_part[L][P.parts[p]["type"]] += n
# zero-length / slot window stats
out = dict(cap_tracks_per_gcell=cap0,
           layers={L: dict(over=int(over[L].sum()), max=round(float(use[L].max()), 3),
                           self_over_roads=selfover[L], self_over_bits=selfover_bits[L], aggregation_only_roads=aggr_only[L])
                   for L in use},
           band_hist={L: {f"{a}cells_{s}": n for (a, s), n in sorted(v.items())} for L, v in bandhist.items()},
           top_type_over={f"{L}|{t}": dict(v) for (L, t), v in sorted(agg_type.items(), key=lambda kv: -kv[1]["over_dem"])[:40]},
           over_cells_by_type={L: dict(v.most_common(15)) for L, v in cell_part.items()},
           top_roads=need)
Path(outp).write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float)[:20000])
