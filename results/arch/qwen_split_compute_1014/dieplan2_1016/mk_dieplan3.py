#!/usr/bin/env python3
"""Q-DIEPLAN2r (Q-COMPUTE-DIE helper, 2026-10-16): q2o2 homes = owner 5-column layout on the b2 graph.

usage: mk_dieplan3.py BASE_HOMES OUT_HOMES [--lattice 8.64] [--tt-above] [--embed-west] [--dvm-slot W,H]

BASE = qcd_owner2d_t950-homes.json (q2o1). The b2 graph (OT_SPLIT_B2=1) re-draws the port strips itself (one port
variant per side, halfband/halfres per side, no port<->_f1 pair lines); homes of retired masters are dropped by
OT_SPLIT_HOMES_REBASE. Moves (positions only):
  L. the centre cluster built on the SU (VM, SU, seq_su, xs_tap, tt_ctlm, res_train_issue, up4_sel_station, native59,
     cbuf|crom pack) moves rigidly so the SU origin sits on the --lattice grid (the hardened SU kit
     qfd_sp_su64_sfu_pr keeps its 346 interior M7 clock pins >= 0.5 um off the die M8 PG lines y = 0 mod 8.64 only
     when its origin is on that lattice); the VM keeps its abutment with the SU.
  T. --tt-above: tt_ctlm (+ res_train_issue, up4_sel_station) leaves the SU W face for the white space above the SU,
     centred on the core axis, so its six port commands (b2_tc 341 b each, W and E) and native59 (380 b) no longer cross
     the SU (over-SU routing is M8/M9 only: the M7-capped hard SU).
  E. --embed-west: embed_prov moves beside seq_su (embed -> seq_su 528 b runs no longer down the SU W edge).
  S. --seq-dy / --xs-dy (seq_dy a multiple of 1.728 = lcm(M4 0.048, M6 0.064 x3, site 0.216): the mirrored kit pins
     stay on seq_su's own M4 / M6 tracks; xs_dy a multiple of 0.432 so the SU xsw mirror stays on M4 tracks): seq_su and xs_tap stand on the SU W face where the SU kit's seq group (acc .. si, y 406.8 ..
     758.8) and xsw face them; the strip under seq_su (above the VM) is the straight vrd / vwr drop to the VM.
  --dvm-slot is recorded only (DVM column body 129.6 x 920.16 pending Q-XSLEAF closure; not bound in q2o2).
"""
import argparse, json, itertools
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('base'); ap.add_argument('out')
ap.add_argument('--lattice', type=float, default=8.64)
ap.add_argument('--tt-above', action='store_true')
ap.add_argument('--tt-xy', default=None, help='tt_ctlm origin x,y for --tt-above (default: centred above the SU)')
ap.add_argument('--embed-west', action='store_true')
ap.add_argument('--embed-gap', type=float, default=21.6, help='--embed-west channel to seq_su (um)')
ap.add_argument('--embed-xy', default=None, help='embed_prov origin x,y (e.g. beside tt_ctlm above the SU)')
ap.add_argument('--dvm-slot', default='129.6,920.16')
ap.add_argument('--seq-dy', type=float, default=None, help='seq_su origin y above the SU origin (face the kit seq pins)')
ap.add_argument('--xs-dy', type=float, default=None, help='xs_tap origin y above the SU origin (face the kit xsw)')
a = ap.parse_args()
B = json.load(open(a.base)); H = {k: dict(v) for k, v in B['homes'].items()}
q = lambda v, s=0.216: round(round(v / s) * s, 4)
su = H['sp_su64_sfu']
L = a.lattice
dx = round(round(su['x'] / L) * L - su['x'], 4); dy = round(round(su['y'] / L) * L - su['y'], 4)
CLUSTER = ['sp_vector_memory', 'sp_su64_sfu', 'seq_su', 'xs_tap', 'tt_ctlm', 'res_train_issue', 'up4_sel_station',
           'native59'] + [n for n in H if n.startswith(('cbuf_g_', 'crom_g_'))]
for n in CLUSTER:
    H[n]['x'] = round(H[n]['x'] + dx, 4); H[n]['y'] = round(H[n]['y'] + dy, 4)
assert abs(H['sp_su64_sfu']['x'] / L - round(H['sp_su64_sfu']['x'] / L)) < 1e-6
assert abs(H['sp_su64_sfu']['y'] / L - round(H['sp_su64_sfu']['y'] / L)) < 1e-6
su = H['sp_su64_sfu']
moves = dict(lattice_shift=[dx, dy])
if a.tt_above:
    t = H['tt_ctlm']
    if a.tt_xy:
        tx, ty = (float(v) for v in a.tt_xy.split(','))
    else:
        tx, ty = su['x'] + su['w'] / 2 - t['w'] / 2, su['y'] + su['h'] + 21.6
    old = (t['x'], t['y'])
    t['x'], t['y'] = q(tx), q(ty)
    for n in ('res_train_issue', 'up4_sel_station'):
        H[n]['x'] = round(H[n]['x'] + t['x'] - old[0], 4); H[n]['y'] = round(H[n]['y'] + t['y'] - old[1], 4)
    moves['tt_ctlm'] = [t['x'], t['y']]
if a.seq_dy is not None:
    H['seq_su']['y'] = q(su['y'] + a.seq_dy); moves['seq_su'] = [H['seq_su']['x'], H['seq_su']['y']]
if a.xs_dy is not None:
    H['xs_tap']['y'] = q(su['y'] + a.xs_dy); moves['xs_tap'] = [H['xs_tap']['x'], H['xs_tap']['y']]
if a.embed_west:
    e, s = H['embed_prov'], H['seq_su']
    e['x'], e['y'] = q(s['x'] - e['w'] - a.embed_gap), q(s['y'])
    moves['embed_prov'] = [e['x'], e['y']]
if a.embed_xy:
    e = H['embed_prov']; e['x'], e['y'] = (q(float(v)) for v in a.embed_xy.split(','))
    moves['embed_prov'] = [e['x'], e['y']]
D = B['die']
for n, h in H.items():
    assert h['x'] >= -1e-3 and h['y'] >= -1e-3 and h['x'] + h['w'] <= D['w'] + 1e-3 and h['y'] + h['h'] <= D['h'] + 1e-3, n
ov = [(n1, n2) for (n1, a1), (n2, a2) in itertools.combinations(H.items(), 2)
      if min(a1['x'] + a1['w'], a2['x'] + a2['w']) - max(a1['x'], a2['x']) > 0.01
      and min(a1['y'] + a1['h'], a2['y'] + a2['h']) - max(a1['y'], a2['y']) > 0.01]
assert not ov, ov[:10]
res = dict(B); res['homes'] = H; res['candidate'] = Path(a.out).stem.replace('-homes', '')
res['params'] = dict(B['params'], source='mk_dieplan3.py', base=Path(a.base).name, lattice=L, tt_above=a.tt_above,
                     embed_west=a.embed_west, dvm_slot_um=[float(v) for v in a.dvm_slot.split(',')], moves=moves,
                     graph='b2 (OT_SPLIT_B2=1 physical trial, compact selector)')
res['params'].pop('interim_exception', None)
Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps(moves))
