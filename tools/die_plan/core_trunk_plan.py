#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 hcroot: 12.8c SHALLOW_FIXED_TRUNK plan for the HBM root HC-tree cores (plan model only, UNCHECKED).

  trunk_plan.py GEO OUTPREFIX --libtt TT.lib --libff FF.lib [--splits 2,2,4] [--trunk-cell BUFx4_ASAP7_75t_R]
                [--trunk-n N | --target-tt 250 --target-ff 202.5] [--src-slew 20]

Structure (METHODOLOGY 12.8a-d1): core clock pin at the geometric centre (master-plan entry) -> ONE designed fixed trunk
chain of N identical cells in the entry island (series, <=1.08 um local hops, dont_touch, FIRM) -> the equal-structure
H-tree of tools/die_plan/core_infra_htree.py (buffer at every branch point, equal level lengths, equal-count leaf
clusters) -> registers.  N is chosen by the plan BEFORE any build from the plan model: smallest |TT-250| + |FF-202.5|
(deterministic; ties -> fewer cells).  No measured input, no per-sink padding, no trims.  The same N/cell is meant to be
shared by every type with this outline when their trees predict alike (12.8c "same cell chain per type").
Model = core_infra_htree.model (ASAP7 NLDM + Elmore, rc 0.8/0.9 setRC calibration) + the trunk chain on the same
NLDM tables (stage load = next cell A cin + 1.08 um local wire; last stage drives the tree root BUFx24 + local wire).
"""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_infra_htree as H

def trunk(L, cell, n, root_cin, r, c, src_slew, loc_um=1.08):
    d = 0.0; s = src_slew; per = []
    for i in range(n):
        load = (L[cell]['cin'] if i < n - 1 else root_cin) + c * loc_um
        dd = 0.5 * (H.interp(L[cell]['rise'], s, load) + H.interp(L[cell]['fall'], s, load))
        so = 0.5 * (H.interp(L[cell]['trise'], s, load) + H.interp(L[cell]['tfall'], s, load))
        el = r * loc_um * (c * loc_um / 2 + load)
        d += dd + el; s = math.hypot(so, 2.2 * el); per.append(round(dd + el, 2))
    return d, s, per

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('geo'); ap.add_argument('out')
    ap.add_argument('--libtt', required=True); ap.add_argument('--libff', required=True)
    ap.add_argument('--splits', default='2,2,4'); ap.add_argument('--smax', type=float, default=70.0)
    ap.add_argument('--rc', default='0.8,0.9'); ap.add_argument('--src-slew', type=float, default=20.0)
    ap.add_argument('--trunk-cell', default='BUFx4_ASAP7_75t_R'); ap.add_argument('--trunk-n', type=int, default=None)
    ap.add_argument('--target-tt', type=float, default=250.0); ap.add_argument('--target-ff', type=float, default=202.5)
    a = ap.parse_args()
    P = H.plan(a.geo, [int(x) for x in a.splits.split(',')], a.smax, [], None)
    kr, kc = map(float, a.rc.split(','))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = [H.REP, H.BIG, a.trunk_cell]
    libs = {'TT': H.lib_cells(a.libtt, cells), 'FF': H.lib_cells(a.libff, cells)}
    tree0 = {k: H.model(P, {k: libs[k]}, r, c, a.src_slew)[k] for k in libs}
    cands = []
    for n in ([a.trunk_n] if a.trunk_n is not None else range(0, 16)):
        res = {}
        for k in libs:
            if n:
                td, ts, per = trunk(libs[k], a.trunk_cell, n, libs[k][H.BIG]['cin'], r, c, a.src_slew)
            else:
                td, ts, per = 0.0, a.src_slew, []
            t = H.model(P, {k: libs[k]}, r, c, ts)[k]
            res[k] = dict(trunk_ps=round(td, 2), trunk_out_slew_ps=round(ts, 2), trunk_stage_ps=per,
                          mean=round(t['mean'] + td, 2), window=t['window'], sink_min=round(t['sink_min'] + td, 2),
                          sink_max=round(t['sink_max'] + td, 2), tree_mean=t['mean'])
        cost = abs(res['TT']['mean'] - a.target_tt) + abs(res['FF']['mean'] - a.target_ff)
        cands.append((round(cost, 3), n, res))
    cost, n, res = min(cands, key=lambda x: (x[0], x[1]))
    leafs = [x for x in P['nodes'] if x[4] == 'leaf']
    mz = P['mz']
    rep = dict(scope='PLAN MODEL ONLY (core_infra_htree NLDM+Elmore rc %s, src slew %.0f ps) + fixed trunk chain; UNCHECKED' % (a.rc, a.src_slew),
               rule='12.8c SHALLOW_FIXED_TRUNK: ONE designed fixed trunk chain at the centre entry, same chain per type; no per-sink padding',
               geo=a.geo, entry=list(P['entry']), splits=P['splits'], n_sinks=sum(len(v) for v in P['leafsinks'].values()),
               leaf_load=[min(len(v) for v in P['leafsinks'].values()), max(len(v) for v in P['leafsinks'].values())],
               level_len_um=P['T'], repeaters_per_edge=[k - 1 for k in P['K']], tree_only=tree0,
               trunk=dict(cell=a.trunk_cell, n=n, island='entry island (8.64 x 8.64 um at the centre)', dont_touch=True, firm=True),
               pred=res, target=dict(TT=a.target_tt, FF=a.target_ff), band_tt=[230, 270], band_ff=[182.5, 222.5],
               in_band=dict(TT=230 <= res['TT']['mean'] <= 270, FF=182.5 <= res['FF']['mean'] <= 222.5),
               window_ok=max(res['TT']['window'], res['FF']['window']) <= 20,
               candidates=[dict(n=x[1], cost=x[0], TT=x[2]['TT']['mean'], FF=x[2]['FF']['mean']) for x in cands],
               nodes=[(x[0], x[1], mz.xy(x[2]), x[3], x[4]) for x in P['nodes']],
               leaf_sites={x[0]: mz.xy(x[2]) for x in leafs})
    Path(a.out + '.json').write_text(json.dumps(rep, indent=1))
    H.emit_tcl(P, a.out + '.tree_spec.tcl')
    print(json.dumps({k: rep[k] for k in ('n_sinks', 'splits', 'leaf_load', 'level_len_um', 'repeaters_per_edge', 'trunk', 'pred', 'in_band', 'window_ok')}, indent=0))

if __name__ == '__main__':
    main()
