#!/usr/bin/env python3
"""DIE-HBM-4: region3_tok 'tsv' with the MESO-RECONCILE-2 planner (count_align_plan @32e8cbb164, min-ambiguity
directed start tree) and 12.15b spice clock cal: caller passes v = measured x1.0485 (TT); FF arrivals get the extra
x1.0552/1.0485 on top of the table FF/TT stage ratio.   usage: r4_tok.py SRC PLAN V FEED MAP OUT.tsv"""
import importlib.util, inspect, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
import region3_tok as R3
SRC = sys.argv[1]
sys.path[:0] = [SRC + '/tools', SRC + '/tools/die_plan', SRC + '/tools/throughput', SRC + '/src',
                SRC + '/tools/hbm_b2', SRC + '/tools/s81_head']
spec = importlib.util.spec_from_file_location('count_align_plan', here / 'src_mr' / 'count_align_plan.py')
cap = importlib.util.module_from_spec(spec); spec.loader.exec_module(cap); sys.modules['count_align_plan'] = cap
if not hasattr(cap, 'DSU'):                       # locality.cap_plan_corners uses CAP.DSU (main's shim, as region3)
    old = here.parent / 'src' / 'count_align_plan.py'
    s2 = importlib.util.spec_from_file_location('cap_old', old); o = importlib.util.module_from_spec(s2); s2.loader.exec_module(o)
    cap.DSU = o.DSU
import locality as Lc
FFX = 1.0552 / 1.0485
_m = Lc.margins
def margins(br_rows, Ttab, period, budget=None, ff_scale=None):
    if ff_scale is None:
        ff_scale = Ttab["classes"]["A"]["FF"]["mu_stage_ps"] / Ttab["classes"]["A"]["TT"]["mu_stage_ps"]
    return _m(br_rows, Ttab, period, budget, ff_scale * FFX)
Lc.margins = margins
R3.cmd_tsv(SRC, *sys.argv[2:7])
