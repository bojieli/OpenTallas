#!/usr/bin/env python3
"""KV-PLAN-R3: hot-spot drill-down of master-plan roads (contributors to worst gcells; over cells caused by
single-road self-overflow vs stacking; lane/slot details of the dominant buses)."""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
tool, plan, mpd, outp = sys.argv[1:5]
sys.path.insert(0, tool)
import numpy as np
import schema as S
import master_plan as MP
P = S.Plan(S.load(plan), Path(plan))
R = json.loads((Path(mpd) / "roads.json").read_text())
blk = {p: MP.part_blockers(P, p, {}) for p in P.parts}
cores = [r[:4] for b in blk.values() for r in b if r[4] != "island"]
grid = MP.Grid(P, P.die.get("pg", {}).get("grid", []), None, 0.25, "M5", [], cores)
recs = []
selfmax = {L: np.zeros_like(grid.dem[L]) for L in grid.dem}
for rd in sorted(R["roads"], key=lambda s: -s["bits"]):
    sl, horiz = grid.band(rd["a"], rd["b"], rd["band_um"])
    add = grid.load(rd["layer"], sl, horiz, rd["bits"])
    if add is None: continue
    grid.commit(rd["layer"], sl, add)
    i0, j0, i1, j1 = sl
    cap = grid.cap[rd["layer"]][j0:j1, i0:i1]
    selfmax[rd["layer"]][j0:j1, i0:i1] = np.maximum(selfmax[rd["layer"]][j0:j1, i0:i1], add / np.maximum(cap, 1e-9))
    recs.append((rd, sl))
out = dict(split={}, worst={}, lanes={})
for L in grid.dem:
    u = np.where(grid.cap[L] > 0, grid.dem[L] / np.maximum(grid.cap[L], 1e-9), 0)
    ov = u > 0.6 + 1e-6
    so = ov & (selfmax[L] > 0.6 + 1e-6)
    out["split"][L] = dict(over=int(ov.sum()), single_road_over=int(so.sum()), stacking_only=int((ov & ~so).sum()),
                           over_ge_1=int((u > 1.0).sum()), over_ge_2=int((u > 2.0).sum()))
    # worst 3 distinct hotspots
    js, is_ = np.nonzero(u > 1.0)
    order = np.argsort(-u[js, is_])
    seen = []
    for k in order:
        j, i = js[k], is_[k]
        if any(abs(j - a) < 30 and abs(i - b) < 30 for a, b in seen): continue
        seen.append((j, i))
        cont = []
        for rd, (i0, j0, i1, j1) in recs:
            if rd["layer"] == L and i0 <= i < i1 and j0 <= j < j1:
                cont.append(dict(path=rd["path"], part=rd["part"], bits=rd["bits"], band=rd["band_um"], a=rd["a"], b=rd["b"]))
        out["worst"].setdefault(L, []).append(dict(gcell_um=[round(i * MP.G, 1), round(j * MP.G, 1)], use=round(float(u[j, i]), 3),
                                                  n_roads=len(cont), sum_bits=sum(c["bits"] for c in cont), roads=cont[:12]))
        if len(seen) >= 4: break
paths = MP.census(P)
byid = {p["id"]: p for p in paths}
big = Counter()
for p in paths:
    if p["bits"] >= 512: big[(p["bits"], p["src"].split(".")[1] if "." in p["src"] else p["src"], p["dst"].split(".")[1])] += 1
out["big_paths"] = {f"{k[0]}b {k[1]}->{k[2]}": n for k, n in big.most_common(40)}
zl = [p for p in paths if p["length_um"] < 1e-6]
out["zero_length"] = dict(n=len(zl), bits=sum(p["bits"] for p in zl), kinds=dict(Counter(p["kind"] for p in zl)),
                          ex=[(p["id"], p["src"], p["dst"], p["bits"]) for p in zl[:8]])
for pid in ("L2075", "L2153", "L2066", "L2134", "L350", "L347"):
    p = byid.get(pid)
    if p:
        out["lanes"][pid] = dict(bits=p["bits"], src=p["src"], dst=p["dst"], length=p["length_um"],
                                 legs=[dict(part=l["part"], slot=l["slot"], band=l["band_um"], layers=l["layers"],
                                            pts=[[round(v, 1) for v in q] for q in l["pts"]]) for l in p["legs"]])
Path(outp).write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float)[:30000])
