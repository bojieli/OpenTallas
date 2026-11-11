#!/usr/bin/env python3
"""list links over their timing limit for an event's cores_after. usage: tvdiag.py REPO PLAN TYPE EV.json"""
import json, sys
from pathlib import Path
repo, plan, tn, evp = sys.argv[1:5]
sys.path.insert(0, repo + "/tools/die_plan")
import core_place as CP, route_supply as RS
P = json.load(open(plan)); t = P["partition_types"][tn]
RS.REF_DIRS[:] = [str(Path(plan).parent)]
conns = RS.load_conns(Path(plan).parent, None, Path(plan).parent, [])
cfg = dict(gap=34.56, sweeps=0, topk=4, lam=4.0, reach=360.0, grid_um=21.6, grt_halving="full", fixed_re="", rs=dict(RS.DEFAULTS), timing="class")
M = CP.TypeModel(tn, t, Path(plan).parent, Path(repo), conns, cfg)
M.init_limits()
ev = json.load(open(evp))["rows"][0]
seed = ev["cores_after"]
CP.apply_seed(M, seed, print)
for q, (a, b, w, kind) in enumerate(M.L):
    ln = M.llen(q)
    if ln > M.maxlen[q] + 1e-6:
        na = M.inst[a[0]] if a[0] is not None else "fix%s" % (tuple(round(v) for v in a[1]),)
        nb = M.inst[b[0]] if b[0] is not None else "fix%s" % (tuple(round(v) for v in b[1]),)
        print("TV %-8s %-30s -> %-30s bits %5.0f len %7.1f lim %7.1f" % (kind, na, nb, w, ln, M.maxlen[q]))
