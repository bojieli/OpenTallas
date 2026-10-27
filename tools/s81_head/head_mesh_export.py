#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-3: export a head_mesh_r3 output dir as a die_clock_mesh-style mesh.json for master_plan.py --mesh
(htree edges, drivers, taps with stub, xs/ys strap lines).  The strap lines are exported as the full lattice
(xs[0]..xs[-1] / ys[0]..ys[-1], die_infra.clock_rects form) -- PESSIMISTIC vs the built mesh, whose M9 columns stop at
the tile array / serdes strip rows."""
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
N = json.loads((d / "tree_nodes.json").read_text())
S = json.loads((d / "straps.json").read_text())
T = json.loads((d / "stubs.json").read_text())
by = {n["tag"]: n for n in N}
def depth(n):
    k = 0
    while n.get("parent"):
        n = by[n["parent"]]; k += 1
    return k
ht = [dict(tag=n["tag"], level=depth(n), a=by[n["parent"]]["xy"], b=n["xy"], len_um=n["leg"], nseg=n["nseg"])
      for n in N if n.get("parent")]
drv = {n["tag"]: dict(site=n["xy"]) for n in N if not n["kids"]}
xs = sorted({s[1] for s in S if s[0] == "M9"}); ys = sorted({s[1] for s in S if s[0] == "M8"})


def strap_of(t):
    # INFRA-FIRST-HEAD-4: strap binding [layer, index into ys (M8) / xs (M9)] of the stub foot (footless_stubs gate)
    L, f = t["strap_layer"], t["strap_pt"]
    line, c = (ys, f[1]) if L == "M8" else (xs, f[0])
    k = min(range(len(line)), key=lambda i: abs(line[i] - c))
    assert abs(line[k] - c) < 1e-3, (t, L, c)
    return [L, k]


taps = [dict(name=t.get("inst") or t["part"], part=t["part"], tap=t["kind"] + ":" + (t.get("inst") or "").split(".")[-1],
             xy=t["xy"], foot=t["strap_pt"], stub_um=t["stub_um"], stub=dict(um=t["stub_um"], layer="M7/M8 pushdown",
             kind=t["kind"]), strap=strap_of(t), early_ps=0.0) for t in T]
pitch = [177.12, 259.2]          # R3-R15 lattice (M9 177.12 / M8 rows 1036.8 / 4 per tile row)
if "--pitch-from-straps" in sys.argv:
    # HEAD-CORE-R17: mean mesh pitch from the built straps (densified M8 rows): M9 = median column gap, M8 = mean gap
    # between consecutive tile-array rows (kinds tile_row / tile_row_dense), the K_PITCH input of master_plan's pair model
    gx = sorted(b - a for a, b in zip(xs, xs[1:]))
    ty = sorted({s[1] for s in S if s[0] == "M8" and s[4] in ("tile_row", "tile_row_dense")})
    gy = [b - a for a, b in zip(ty, ty[1:])]
    pitch = [round(gx[len(gx) // 2], 3), round(sum(gy) / len(gy), 3)]
    print("pitch_um from straps", pitch, "max M8 gap", round(max(gy), 3))
M = dict(meta=dict(ndr="8w", pitch_um=pitch, regions_depth=0, trunk_um=0.0, form="head_mesh_r3 continuous"),
         htree=ht, drivers=drv, taps=taps, xs=xs, ys=ys)
(d / "mesh.json").write_text(json.dumps(M))
print(len(ht), "edges", len(drv), "drivers", len(taps), "taps", len(xs), "xs", len(ys), "ys")
