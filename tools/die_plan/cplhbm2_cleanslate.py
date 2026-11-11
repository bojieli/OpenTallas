#!/usr/bin/env python3
"""CPL-HBM-2 (DO_NOT_COUNT): clean-slate constructive seed for core_place.py.
Ignores the current core coordinates: every rigid cluster (abutted cores, as core_place groups them) is lifted out,
then placed one at a time (most link bits first) at the legal 4.32-lattice spot (coarse scan, then a fine scan around
the best) and flip that minimise bits x Manhattan to the type faces/buses/fixed points and the clusters already
placed (links to unplaced clusters are ignored). Legality = core_place.TypeModel.legal (outline + pin-channel need,
gap, ft regs/clock/reset keep-outs, channels, die-band overlap not grown). Writes a --seed JSON for core_place.py.
usage: cleanslate.py PLAN TYPE[,TYPE..] OUT_SEED.json [--repo R] [--die hbm] [--step 17.28] [--order bits|area]
       [--anchor E|W|N|S] (optional bias: ties broken toward that face)"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("types"); ap.add_argument("out")
ap.add_argument("--repo", default="."); ap.add_argument("--die", default="hbm")
ap.add_argument("--step", type=float, default=17.28); ap.add_argument("--order", default="bits")
ap.add_argument("--gap", default="auto")
a = ap.parse_args()
sys.path.insert(0, str(Path(a.repo) / "tools" / "die_plan"))
import core_place as CP  # noqa: E402
import route_supply as RS  # noqa: E402

plan = Path(a.plan)
P = json.loads(plan.read_text())
repo = Path(a.repo).resolve()
RS.REF_DIRS[:] = [str(plan.parent)]
die_dir = plan.parent
rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
for k, f in (("views", "route_supply_views.json"), ("kit_views", "route_supply_kit_views.json")):
    try:
        d = json.loads((repo / "tools" / "die_plan" / f).read_text())
        rs_cfg[k] = d.get("views", {}) if k == "views" else d.get(a.die, {})
    except (OSError, ValueError, AttributeError):
        rs_cfg[k] = {}
conns = RS.load_conns(die_dir, None, plan.parent, [])
seeds = {}
for tn in a.types.split(","):
    t = P["partition_types"][tn]
    cfg = dict(gap=34.56, sweeps=0, topk=4, lam=4.0, reach=360.0, grid_um=21.6, grt_halving="full", fixed_re="", rs=rs_cfg)
    M = CP.TypeModel(tn, t, die_dir, repo, conns, cfg)
    mg = 34.56
    for k in range(M.m):
        for j in range(k + 1, M.m):
            x, y, w, h = M.cbb[k]; X, Y, Wj, Hj = M.cbb[j]
            mg = min(mg, max(X - (x + w), x - (X + Wj), Y - (y + h), y - (Y + Hj)))
    cfg["gap"] = max(CP.G, math.floor(mg / CP.G + 1e-6) * CP.G) if a.gap == "auto" else float(a.gap)
    M.init_limits()
    # lift every movable cluster far outside (distinct spots, never overlapping anything)
    placed = [bool(M.cfix[k]) for k in range(M.m)]
    for k in range(M.m):
        if not placed[k]:
            M.cpos[k] = (-1e6 - 5e3 * k, -1e6)
    M.band_now = np.zeros(len(M.bands))
    for k in range(M.m):
        if placed[k]:
            M.band_now += M._band_k(k)

    def kbits(k):
        return sum(M.L[q][2] for i in M.CL[k] for q in M.inc[i])
    order = sorted([k for k in range(M.m) if not placed[k]],
                   key=(lambda k: -kbits(k)) if a.order == "bits" else (lambda k: -M.cbb[k, 2] * M.cbb[k, 3]))

    def lcost(k):
        c = 0.0
        for i in M.CL[k]:
            for q in M.inc[i]:
                A, B, w, kind = M.L[q]
                o = B if (A[0] is not None and M.cid[A[0]] == k) else A
                if o[0] is not None and M.cid[o[0]] != k and not placed[M.cid[o[0]]]:
                    continue
                c += w * M.llen(q)
        return c
    W, H = M.W, M.H
    for k in order:
        w, h = M.cbb[k, 2], M.cbb[k, 3]
        flips = list(CP.FLIP) if len(M.CL[k]) == 1 else [M.cflip[k]]
        best = None
        for step, region in ((a.step, None), (CP.G, "fine")):
            if region is None:
                xs = np.arange(CP.G, W - w - CP.G + 1e-6, step)
                ys = np.arange(CP.G, H - h - CP.G + 1e-6, step)
            else:
                if best is None:
                    break
                bx, by = best[1]
                xs = np.arange(max(CP.G, bx - 3 * a.step), min(W - w - CP.G, bx + 3 * a.step) + 1e-6, step)
                ys = np.arange(max(CP.G, by - 3 * a.step), min(H - h - CP.G, by + 3 * a.step) + 1e-6, step)
            for fl in flips:
                M.cflip[k] = fl
                for x in xs:
                    for y in ys:
                        p = (CP.snap(x), CP.snap(y))
                        if not M.legal(k, *p, fl=fl):
                            continue
                        M.cpos[k] = p
                        c = lcost(k)
                        if best is None or c < best[0] - 1e-6:
                            best = (c, p, fl)
                M.cpos[k] = (-1e6 - 5e3 * k, -1e6)
        if best is None:
            print("  %s cluster %d (%s) NO LEGAL SPOT" % (tn, k, M.inst[M.CL[k][0]]))
            continue
        old = M._band_k(k) if M.bands else None
        M.cpos[k] = best[1]; M.cflip[k] = best[2]; placed[k] = True
        if M.bands:
            M.band_now += M._band_k(k) - old
    seeds[tn] = {M.inst[i]: dict(origin_um=[round(v, 4) for v in M.core_origin(i)], orient=M.core_orient(i))
                 for i in range(M.n) if placed[M.cid[i]]}
    print(tn, "gap %.2f" % cfg["gap"], "clusters", M.m, "placed", sum(placed), "bit-mm %.0f" % (M.cost(range(len(M.L))) / 1e3))
json.dump(seeds, open(a.out, "w"), indent=1)
