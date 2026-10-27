#!/usr/bin/env python3
"""TOK-SCHED (2026-10-25): price the S81 vsw LR=1 lane-input stage (main 8d6af30b15, +1 cycle on vsw o_v/o_d/o_f) in the
composed DS token price.  Runs tools/s81_dv/tokfunc/compose_tok_ds.py UNCHANGED, except that every DAG node of op
--op (default ffn.quant2: the SW command of the slice beat leaf, vp SW pin -> last vs result, which waits for the
vsw result by event) gets one extra priced-edge component of --delta cycles (default 1).  Applied before the calendar
too (same build_components hook), so the AR50/MTP6 static calendars see the same node cycles.

  python3 run_vsw.py --out DIR [--delta 1] [--op ffn.quant2] [--plan die_plan.json] [compose args...]
"""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/s81_dv/tokfunc'))
import importlib.util
spec = importlib.util.spec_from_file_location('compose_tok_ds', ROOT / 'tools/s81_dv/tokfunc/compose_tok_ds.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

ap = argparse.ArgumentParser()
ap.add_argument('--delta', type=float, default=1.0)
ap.add_argument('--op', default='ffn.quant2')
ap.add_argument('--plan', help='die_plan.json copy (sparse worktrees); digest only')
a, rest = ap.parse_known_args()
if a.plan:
    M.PLAN = Path(a.plan).resolve()
_bc = M.build_components
HIT = {}

def build_components(wl, base, dag, ops, slots, xparts):
    comps, hooks, extra, ov = _bc(wl, base, dag, ops, slots, xparts)
    n_hit = 0
    if a.delta:
        for n in dag['nodes']:
            if n.get('op') == a.op:
                comps[n['id']].append(M.comp(a.delta, M.EDGE, 'edge', f'S81.VSW_LR1 vsw lane-input stage +{a.delta:g} '
                                             '(main 8d6af30b15, ot_s81sl_vsw LR=1)'))
                n_hit += 1
    HIT.setdefault(wl, []).append(dict(nodes=n_hit, critical=sum(1 for n in dag['nodes'] if n.get('op') == a.op
                                                                     and n.get('critical'))))
    return comps, hooks, extra, ov

M.build_components = build_components
rc = M.main(rest)
print('vsw hook:', a.op, '+', a.delta, HIT)
sys.exit(rc)
