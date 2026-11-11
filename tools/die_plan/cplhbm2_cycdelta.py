#!/usr/bin/env python3
"""CPL-HBM-2: cycle delta for a position delta = links whose length exceeds the core_place timing limit
(--timing class) after the move, with the extra pipeline cycles they need (reach 360 x 0.8 = 288 um/cycle).
station: extra = ceil(len_after/288) - 1 - nreg ; direct link: extra = ceil((len_after - limit)/288).
usage: cycdelta.py REPO PLAN TYPE EV.json  -> TSV rows on stdout"""
import json, math, sys
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
base = [M.llen(q) for q in range(len(M.L))]
ev = json.load(open(evp))["rows"][0]
CP.apply_seed(M, ev["cores_after"], lambda s: None)
nreg = {q: n for (_, q, n) in M.stations}
STEP = 0.8 * 360.0
tot = 0
for q, (a, b, w, kind) in enumerate(M.L):
    ln = M.llen(q)
    if ln <= M.maxlen[q] + 1e-6:
        continue
    if kind == "station":
        ex = max(0, math.ceil(ln / STEP) - 1 - nreg[q]); nr = nreg[q]
    else:
        ex = math.ceil((ln - M.maxlen[q]) / STEP); nr = 0
    tot += ex
    print("%s\t%s\t%s\t%.0f\t%.1f\t%.1f\t%.1f\t%d\t%d" % (tn, M.Llab[q], kind, w, base[q], ln, M.maxlen[q], nr, ex))
print("# %s extra cycles total %d (links over limit listed above)" % (tn, tot), file=sys.stderr)
