#!/usr/bin/env python3
"""QC-A0-KITS-8 paper estimate (PLAN MODEL, R7 NLDM+Elmore chain of core_family_slice, no build):
 (A) the shipped a0k6s node plan (core_family_slice a0node, d1/uf3 mixed masters) -- its R7 window;
 (B) the SAME geometry with ONE master per level (size compensation removed) -- shows how much the plan leaned on sizes;
 (C) a SYMMETRIC lattice tree (equal wire length per level by construction) with ONE master per level.
usage: est_uniform.py REPO GEO LIBTT LIBFF PLAN_D1_JSON"""
import collections, itertools, json, sys
REPO, GEO, LTT, LFF, PD1 = sys.argv[1:6]
sys.path.insert(0, REPO + '/tools/die_plan'); sys.path.insert(0, REPO + '/results/core_lat_r7_1026'); sys.path.insert(0, REPO + '/results/core_lat_r8_1026')
import core_family_slice as F, core_infra_htree as H, l0r_r7_model as M7
ENV = F.ENV
fam = json.load(open(REPO + '/physical/die_plan/qwen_compute/cores/a0/families_a0.json'))['families'][0]
cells = sorted(set(ENV + [H.REP, H.BIG]))
libs = {'TT': H.lib_cells(LTT, cells), 'FF': H.lib_cells(LFF, cells)}
r = 0.5 * (1.80365e-2 + 1.89935e-2) * 0.8; c = 0.5 * (1.78475e-1 + 1.64264e-1) * 0.9
out = {}

def summ(res):
    return {k: dict(mean=res[k]['mean'], window=res[k]['window'], sink_spread=round(res[k]['sink_max'] - res[k]['sink_min'], 2),
                    slew=res[k]['leaf_out_slew_max']) for k in ('TT', 'FF')}

def levkey(n):
    if n[4] in ('entry', 'trunk'): return ('root',)
    pos = 0 if n[4] == 'branch' else (1 + int(n[0].rsplit('_r', 1)[1]) if n[4] == 'rep' else 0)
    return (1 if n[4] == 'leaf' else 0, M7.lvl_of(n[0]), pos)

def uniform_search(P, wc):
    """one master per level key; coordinate descent (deterministic) on TT window + FF window, slew <= 60 TT."""
    keys = sorted({levkey(n) for n in P['nodes']}, key=str)
    cur = {k: 'BUFx16f_ASAP7_75t_R' for k in keys}
    def apply(m):
        P['nodes'] = [(n[0], n[1], n[2], m[levkey(n)], n[4]) for n in P['nodes']]
        res, _ = M7.model_x(P, libs, r, c, wc)
        bad = res['TT']['leaf_out_slew_max'] > 60 or res['TT']['leaf_slew_in_max'] > 80
        return (res['TT']['window'] + res['FF']['window'] + (1e3 if bad else 0), res)
    best, res = apply(cur)
    for _ in range(3):
        for k in keys:
            for m in ENV:
                t = dict(cur); t[k] = m; v, rr = apply(t)
                if v < best - 1e-6: best, cur, res = v, t, rr
    apply(cur)
    return cur, res

# ---- (A)/(B): the shipped plan geometry, rebuilt with the same deterministic planner
d1 = json.load(open(PD1)); d1 = d1[0] if isinstance(d1, list) else d1
rec = F.plan(GEO, fam, LTT, LFF, 'probe')
P, libs_, r_, c_, wc = F._PLANS['probe']
same = sorted(n[0] for n in P['nodes']) == sorted(n[0] for n in d1['nodes_xy'])
fm = d1['frozen_masters']
P['nodes'] = [(n[0], n[1], n[2], fm.get(n[0], n[3]), n[4]) for n in P['nodes']]
resA, _ = M7.model_x(P, libs, r, c, wc)
out['A_shipped_d1_masters'] = dict(same_node_names=same, masters=collections.Counter(n[3] for n in P['nodes']), **summ(resA))
lv = collections.defaultdict(collections.Counter)
for n in P['nodes']: lv[str(levkey(n))][n[3].split('_')[0]] += 1
out['A_masters_per_level'] = {k: dict(v) for k, v in sorted(lv.items())}
mB, resB = uniform_search(P, wc)
out['B_same_geometry_one_master_per_level'] = dict(masters={str(k): v.split('_')[0] for k, v in mB.items()}, **summ(resB))

# ---- (C): symmetric lattice tree
class MZ:  # identity maze: cells are coordinates
    def xy(self, p): return (round(p[0], 3), round(p[1], 3))
sinks = []
for l in open(GEO):
    if l.startswith('SINK'):
        f = l.split(); sinks.append((float(f[1]), float(f[2]), f[4], f[5]))
W, Hh = 47.52, 432.0; E = (23.76, 216.0)
# levels: list of tip offset sets
LEVELS = [[(0, -108), (0, 108)], [(0, -54), (0, 54)], [(0, -27), (0, 27)],
          [(-11.88, -13.5), (11.88, -13.5), (-11.88, 13.5), (11.88, 13.5)],
          [(-5.94, -6.75), (5.94, -6.75), (-5.94, 6.75), (5.94, 6.75)], [(0, -3.375), (0, 3.375)]]

def build(levels, leaf_cap=None):
    nodes = [('root', None, E, 'BUFx24_ASAP7_75t_R', 'entry')]; land = {}; wires = []
    hubs = [('', E, 'root')]   # (name digits, hub xy, driver feeding this hub)
    for li, offs in enumerate(levels):
        nh = []
        for dg, hp, drv in hubs:
            # stack of len(offs) branch buffers at the hub, 1.08 um pitch centred on the hub (as the shipped planner)
            k = len(offs); kids = []
            for i, o in enumerate(offs):
                nm = 'T' + dg + str(i)
                bx = (hp[0], hp[1] + (i - (k - 1) / 2) * 1.08)
                nodes.append((nm + '_br', drv, bx, 'BUFx16f_ASAP7_75t_R', 'branch')); kids.append(nm)
                tip = (hp[0] + o[0], hp[1] + o[1])
                nh.append((dg + str(i), tip, nm + '_br'))
            # the feeding driver lands on this hub (seg = its own wire length; hub edge name = dg)
            hubname = 'H' + (dg or 'R')
            seg = 0.0 if drv == 'root' else abs(levels[li - 1][int(dg[-1])][0]) + abs(levels[li - 1][int(dg[-1])][1])
            land[drv] = (seg, hubname); wires.append(dict(level=li, edge=hubname, segs=[seg], cells=[[hp]]))
        hubs = nh
    leafsinks = {}
    pts = {('T' + dg): tp for dg, tp, drv in hubs}
    for dg, tp, drv in hubs:
        nm = 'T' + dg
        nodes.append((nm, drv, tp, 'BUFx16f_ASAP7_75t_R', 'leaf'))
        seg = abs(levels[-1][int(dg[-1])][0]) + abs(levels[-1][int(dg[-1])][1])
        hubname = 'L' + dg; land[drv] = (seg, hubname); wires.append(dict(level=len(levels), edge=hubname, segs=[seg], cells=[[tp]]))
        leafsinks[nm] = []
    names = sorted(pts)
    for s in sinks:
        u = min(names, key=lambda u: (abs(s[0] - pts[u][0]) + abs(s[1] - pts[u][1]), u)); leafsinks[u].append(s)
    empty = [u for u in names if not leafsinks[u]]
    for u in empty:   # empty leaf: keep the driver (symmetric load on its parent) but it drives nothing -> model needs sinks; give it a dummy
        del leafsinks[u]
    return dict(mz=MZ(), nodes=nodes, land=land, wires=wires, leafsinks=leafsinks), empty

PC, empty = build(LEVELS)
cnt = sorted(len(v) for v in PC['leafsinks'].values())
spread = []
for u, v in PC['leafsinks'].items():
    p = [n[2] for n in PC['nodes'] if n[0] == u][0]; spread.append(max(abs(s[0] - p[0]) + abs(s[1] - p[1]) for s in v))
mC, resC = uniform_search(PC, {})
out['C_symmetric_lattice_one_master_per_level'] = dict(levels_um=[[abs(o[0]) + abs(o[1]) for o in L][0] for L in LEVELS],
    stages=len(LEVELS) + 2, cells=len(PC['nodes']), leaves=len(PC['leafsinks']), empty_leaves=len(empty),
    leaf_members=dict(min=cnt[0], p10=cnt[len(cnt) // 10], median=cnt[len(cnt) // 2], p90=cnt[9 * len(cnt) // 10], max=cnt[-1]),
    leaf_spread_max_um=round(max(spread), 2), masters={str(k): v.split('_')[0] for k, v in mC.items()}, **summ(resC))
print(json.dumps(out, indent=1, default=str))
