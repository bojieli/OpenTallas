#!/usr/bin/env python3
"""CLOCK-KV-R18 12.8e mesh RE-sign (R18 mesh-fed band, band_feed strap: the 96 band stubs are ordinary mesh loads) = CLOCK-KV-R17
mesh_mc17.py plus (RULING NUMBER-CHECK-KV-R17) the wire-RC variation of the tree ABOVE the mesh, sigma key tree_wire_rel
(qc_clk_mesh2.netlist: one Gaussian per routed tree edge, sigma = 3 % x the edge wire delay, wire share = 1 - AOCV class-A
cell share per corner, hierarchical), so the differential tree delay between mesh drivers is simulated.  R17 text:
12.8e mesh sign-off: whole-die linear RC transient of the routed R15 continuous mesh with SPICE-characterised
Thevenin drivers (QC-CLK-MESH-2 solve, kv_r7/qc_clk_mesh2.py, unchanged), MC over
  * driver mismatch   DELVTRAND n/p N(0, vt_mV) per driver site (Thevenin dvt_ps_per_mV, ngspice-fitted)
  * wire RC           N(1, wire_rel) per 54-um strap segment
  * tree (random)     hierarchical N(0, s*sqrt(stages)) per H-tree edge, shared by everything below it (die root -> drivers
                      AND the leaf-fed band roots)
plus the 12.4a b1 within-die GRADIENT g %/mm (deterministic, worst direction per pair): every tree edge delay d_e scales by
(1 + g * (mid_e - die_root) . u); two extra nominal solves (u = x, u = y) give each load's shift vector S_l (ps per unit
g along x / y); pair gradient term = |S_a - S_b| (exact worst over directions u, since the shift is linear in u).
Loads = 1824 array stub inputs (mesh) + 90 leaf-fed band-root inputs (tree pseudo loads: routed B arrival + the same
per-sample tree offset of their leaf node + their own gradient shift; no mesh averaging).
Output per corner: abs arrivals per sample (sample 0 = nominal), routed nominal per load, gradient vectors, summary.
usage: mesh_mc17.py REC.json --thev THEV.json --corner TT --samples 12 --routed BUILD/mesh_TT.json --out OUT.json"""
import argparse, copy, json, math, random, sys, time
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument('rec'); ap.add_argument('--thev', required=True); ap.add_argument('--corner', default='TT')
ap.add_argument('--samples', type=int, default=12); ap.add_argument('--routed', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--sigma', default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0, "tree_wire_rel": 0.03, "tree_wire_share": {"TT": 0.4674, "FF": 0.5415}}')
ap.add_argument('--grad-pct-per-mm', type=float, default=0.21)
ap.add_argument('--qc', required=True, help='dir holding qc_clk_mesh2.py')
a = ap.parse_args()
sys.path.insert(0, a.qc)
import qc_clk_mesh2 as Q
rec = json.load(open(a.rec)); thev = json.load(open(a.thev)); sig = json.loads(a.sigma); C = a.corner
g = a.grad_pct_per_mm / 100.0
by = {n['tag']: n for n in rec['nodes']}
rx, ry = rec['root_xy']

def tree_off(seed):
    """replicates qc_clk_mesh2.netlist's hierarchical tree offsets (same RNG stream: first draws after Random(1000s+17))."""
    rnd = random.Random(1000 * seed + 17)
    off = {}
    if seed and sig.get('tree_ps_per_stage'):
        for n in sorted(rec['nodes'], key=lambda n: len(n['tag'])):
            if n['parent'] is None:
                off[n['tag']] = 0.0; continue
            nst = max(1, math.ceil(n['leg_um'] / 450.0 - 1e-9))
            off[n['tag']] = off[n['parent']] + rnd.gauss(0.0, sig['tree_ps_per_stage'] * math.sqrt(nst))
    return off

# gradient shift vectors G (ps*mm): G(n) = G(p) + (arr n - arr p) * (mid(n,p) - root) / 1000
G = {}
for n in sorted(rec['nodes'], key=lambda n: len(n['tag'])):
    if n['parent'] is None:
        G[n['tag']] = (0.0, 0.0); continue
    p = by[n['parent']]
    dly = n['arr'][C] - p['arr'][C]
    mx, my = (n['xy'][0] + p['xy'][0]) / 2 - rx, (n['xy'][1] + p['xy'][1]) / 2 - ry
    G[n['tag']] = (G[p['tag']][0] + dly * mx / 1000.0, G[p['tag']][1] + dly * my / 1000.0)
def band_G(b):
    p = by[b['parent']]
    dly = b['arr'][C] - p['arr'][C]
    mx, my = (b['xy'][0] + p['xy'][0]) / 2 - rx, (b['xy'][1] + p['xy'][1]) / 2 - ry
    return (G[p['tag']][0] + dly * mx / 1000.0, G[p['tag']][1] + dly * my / 1000.0)

def run(r, seed, sg):
    t = time.time()
    N = Q.netlist(r, C, None, 0.0, sigma=sg, seed=seed, ndr=None, drv_mult=1)
    res, t0 = Q.solve_netlist(N, C, thev)
    tp = {k[1]: v + t0 for k, v in res.items() if k[0] == 't'}
    return tp, N, time.time() - t

samples, grad = [], {}
for s in range(a.samples + 1):
    tp, N, dt = run(rec, s, sig)
    off = tree_off(s)
    for b in rec['band']:
        tp[b['root']] = b['arr'][C] + off.get(b['parent'], 0.0)
    nan = [k for k, v in tp.items() if v != v]
    assert not nan, nan[:5]
    samples.append(tp)
    print(json.dumps(dict(sample=s, nodes=N['nodes'], drivers=len(N['drv']), loads=len(tp),
                          skew=round(max(tp.values()) - min(tp.values()), 3), sec=round(dt, 1))), flush=True)
# Solve at the physical gradient.  A unit gradient means 100 %/mm and
# can move a large die's driver edge by hundreds of ns, far outside the
# transient horizon.  Normalize the measured response for the existing
# per-unit output contract instead of driving that unphysical stimulus.
grad_solve_scale = g if g != 0.0 else 0.0021
for ax in (0, 1):
    r2 = copy.deepcopy(rec)
    for n in r2['nodes']:
        if n['driver']:
            n['arr'][C] += grad_solve_scale * G[n['tag']][ax]
    tp, N, dt = run(r2, 0, sig)
    for b in rec['band']:
        tp[b['root']] = b['arr'][C] + grad_solve_scale * band_G(b)[ax]
    grad[ax] = {k: (tp[k] - samples[0][k]) / grad_solve_scale for k in tp}
    print('grad axis', ax, 'shift range per unit g', round(min(grad[ax].values()), 1), round(max(grad[ax].values()), 1), flush=True)
rt = {k: v['late'] for k, v in json.load(open(a.routed))['stubs'].items()}
loads = sorted(samples[0])
gv = {k: [round(g * grad[0][k], 4), round(g * grad[1][k], 4)] for k in loads}
# summary
mc = samples[1:]
nom_skew = max(samples[0].values()) - min(samples[0].values())
mc_skew = max(max(s_.values()) - min(s_.values()) for s_ in mc)
dev = [s_[k] - samples[0][k] - (sum(x[k] for x in mc) / len(mc) - samples[0][k]) for s_ in mc for k in loads]
sd = (sum(v * v for v in dev) / max(1, len(dev) - 1)) ** 0.5
gap = {k: (rt[k] - samples[0][k]) for k in loads if k in rt}
gm = sum(gap.values()) / len(gap)
gap_spread = max(gap.values()) - min(gap.values())
# gradient worst pair: max |S_a - S_b| (sample 64 directions on the extreme projections)
gw = 0.0
for i in range(64):
    th = math.pi * i / 64
    pr = [gv[k][0] * math.cos(th) + gv[k][1] * math.sin(th) for k in loads]
    gw = max(gw, max(pr) - min(pr))
mesh_only = [k for k in loads if not k.startswith('ckm_br_')]
def sk(s_, ks): return max(s_[k] for k in ks) - min(s_[k] for k in ks)
out = dict(lane='CLOCK-KV-R18', method=__doc__, rec=a.rec, corner=C, thev=thev[C], sigma=sig, grad_pct_per_mm=a.grad_pct_per_mm,
           samples_n=a.samples, loads=loads, arr=[[round(s_[k], 3) for k in loads] for s_ in samples],
           routed=[round(rt.get(k, float('nan')), 3) for k in loads], grad_vec_ps=[gv[k] for k in loads],
           summary=dict(nominal_skew_ps=round(nom_skew, 2), mc_worst_skew_ps=round(mc_skew, 2),
                        mesh_only_nominal_skew_ps=round(sk(samples[0], mesh_only), 2),
                        mesh_only_mc_worst_skew_ps=round(max(sk(s_, mesh_only) for s_ in mc), 2),
                        per_load_sigma_ps=round(sd, 2), pair_3sigma_ps=round(3 * sd * 2 ** 0.5, 2),
                        gradient_worst_pair_ps=round(gw, 2), routed_minus_sim_mean_ps=round(gm, 2),
                        routed_minus_sim_spread_ps=round(gap_spread, 2),
                        dieU_bound_ps=round(mc_skew + gap_spread + gw, 2)),
           checked='UNCHECKED')
Path(a.out).write_text(json.dumps(out))
print('SUMMARY', C, json.dumps(out['summary']))
