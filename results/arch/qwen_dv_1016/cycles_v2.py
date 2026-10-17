#!/usr/bin/env python3
"""Q-DV full-path per-layer ledger (coordinator 10-16 ~23:00): q3h vs dv1 vs dv2 vs dv2r, counting SU-lane beats and
the VM/SU seam.  Hops: face-projected Manhattan, stages ceil(L/405)-1 + 1 per block boundary; an intermediate DV slice
crossed face to face costs ceil(w/405)-1.  Common parts (in-cluster tree, corridor head->tile, KV die, collective /
PHY internals, matvec issue) cancel and are not listed.

Layer = 4 R (result -> owner) + P (qkv level 9) + QK (q/k norm beats + scale) + K (export) + O (attention return ->
farthest head) + 2 A (all-reduce out + back) + 2 NORM + SILU + BCA (act -> farthest head) + SEAM.
  NORM base / dv1 / dv2 = sumsq beats + tree there and back + scale beats (the broadcast overlaps the scale pass) +
       broadcast tail (owner -> farthest head)
  NORM dv2r (residual replicated per side + norm at the consumer, EXACT: same ops, same order, h = (x*r)*g rounded
       to BF16 where the corridor word is formed) = sumsq beats + max(tree, residual stream to every slice of the side)
       + 64 scale beats at the broadcast rate + 3
  A: rows streamed farthest-first (compiler order; the per-element rank-order sum is unchanged), so the tail latency is
     the NEAREST owner's path; the far legs overlap the bandwidth-bound collective.
  Beats: base SU 64 lanes over 4,096 / 640 (q+k) / 1,536 rows; DV L lanes over the slice's own rows (single owner:
     <= 384, dv2r: 683 per side slice), q/k one head (128) per slice."""
import json, math, sys
import os
HOP = float(os.environ.get("QDV_HOP_UM", "405"))
def load(f):
    d = json.load(open(f)); return {i['n']: i for i in d['insts']}, d
def Lf(I, a, b):
    p, q = I[a], I[b]
    cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
    cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
    A, Q = cl(p, cen(q)), cl(q, cen(p)); return abs(A[0] - Q[0]) + abs(A[1] - Q[1])
def st(I, *path):
    s = sum(max(0, math.ceil(Lf(I, a, b) / HOP) - 1) + (1 if k else 0) for k, (a, b) in enumerate(zip(path, path[1:])))
    for n in path[1:-1]:
        if n.startswith('dvs_'): s += math.ceil(min(I[n]['w'], I[n]['h']) / HOP) - 1
    return s
FEED = math.ceil(5184 / HOP) - 1
def beats(rows, lanes): return math.ceil(rows / lanes)
def base(f):
    I, d = load(f)
    port = {e[3][0]: e[3][1] for e in d['buses'] if e[0].startswith('bword')}
    idx = {'sp_port_tiles_0': 0, 'sp_port_tiles_0_f1': 1, 'sp_port_tiles_1': 2, 'sp_port_tiles_1_f1': 3, 'sp_port_tiles_2': 4, 'sp_port_tiles_2_f1': 5}
    R = max(st(I, c, p, f'sp_halfband_{idx[p]}', p, f'sp_halfres_{idx[p]}', 'sp_vector_memory') for c, p in port.items())
    chain = st(I, *[f'h_{k}' for k in range(23, -1, -1)])
    BC = st(I, 'sp_su64_sfu', 'xs_tap', 'h_23') + chain
    o = dict(R=R, P=0, K=st(I, 'sp_su64_sfu', 'native59', 'd2d_rom'), O=st(I, 'd2d_rom', 'native59', 'sp_vector_memory', 'xs_tap', 'h_23') + chain,
             A=st(I, 'sp_vector_memory', 'seq_su', 'io_collective') + st(I, 'io_collective', 'seq_su', 'sp_vector_memory'),
             QK=2 * beats(640, 64), NORM=beats(4096, 64) * 2 + BC, SILU=beats(1536, 64), BCA=BC, SEAM=21, chain=chain, BC=BC)
    return o
def dv1(f, lanes=8):
    I, d = load(f); own = d['own']
    K3 = lambda c, r: f'dvs_{c * 4 + r}'; idx = lambda k: int(k.split('_')[1]); col = lambda k: idx(k) // 4; row = lambda k: idx(k) % 4
    def mesh(a, b):
        p = [a]; r = row(a); c = col(a)
        while r != row(b): r += 1 if row(b) > r else -1; p.append(K3(c, r))
        while c != col(b): c += 1 if col(b) > c else -1; p.append(K3(c, row(b)))
        return p
    I2, d2 = I, d
    q3 = json.load(open(sys.argv[1])); IB = {i['n']: i for i in q3['insts']}
    chain = st(IB, *[f'h_{k}' for k in range(23, -1, -1)])
    R = max(FEED + 1 + st(I, f'c16_{sg[0]}{sg[1:]}_1', f'dvr_{sg}', f'dvo_{sg}', f'dvw_{sg}', f'dvs_{k}') for sg, k in own.items())
    def gx(k, s):
        r = 1 if row(f'dvs_{k}') <= 1 else 2
        p = mesh(f'dvs_{k}', K3(col(f'dvs_{k}'), r)); p += mesh(p[-1], K3(0 if s == 'W' else 2, r))[1:]
        return st(I, *p, 'dvg_' + s, 'h_23' if s == 'W' else 'h_24')
    BC = max(gx(k, s) for k in range(12) for s in 'WE') + chain
    tree = 2 * max(st(I, *mesh(f'dvs_{k}', 'dvs_5')) for k in range(12))
    qkv = [own[f'{s}{g}'] for s in 'WE' for g in (0, 2, 4)]
    near_ar = min(st(I, *mesh(f'dvs_{k}', K3(col(f'dvs_{k}'), 0)), 'io_collective') for k in range(12))
    back = min(st(I, 'io_collective', K3(c, 0)) for c in range(3))
    return dict(R=R, P=max(st(I, f'dvr_{s}{g+1}', f'dvr_{s}{g}') for s in 'WE' for g in (0, 2, 4)) , K=max(st(I, *mesh(f'dvs_{k}', K3(col(f'dvs_{k}'), 3)), 'native59', 'd2d_rom') for k in qkv),
                O=st(I, 'd2d_rom', 'native59', 'dvs_7') + max(gx(k, s) for k in (3, 7, 11) for s in 'WE') + chain,
                A=near_ar + back, QK=2 * beats(128, lanes), NORM=beats(384, lanes) * 2 + tree + BC, SILU=beats(128, lanes), BCA=BC, SEAM=0, tree=tree, BC=BC)
def dv2(f, lanes=8, rep=False):
    I, d = load(f)
    side = lambda s: [f'dvs_{s}{g}' for g in range(6)]
    R = FEED + 1 + st(I, 'c16_W5_1', 'dvs_W5')
    P = max(st(I, f'dvs_{s}{g+1}', f'dvs_{s}{g}') for s in 'WE' for g in (0, 2, 4))
    cross = ['dvs_W0', 'dvx_w', 'dvx_e', 'dvs_E0'] if 'dvx_w' in I else ['dvs_W0', 'dvs_E0']
    far = st(I, *side('W')[::-1], *cross[1:], *side('E')[1:])            # W5 -> E5 along the stream
    within = st(I, *side('W')[::-1])                                     # W5 -> W0
    tree_side = 2 * max(st(I, *side('W')[k:3][::-1] or ['dvs_W2']) if k < 3 else st(I, *side('W')[2:k + 1]) for k in range(6))
    tree_die = 2 * st(I, 'dvs_W5', 'dvs_W4', 'dvs_W3', 'dvs_W2', 'dvs_W1', 'dvs_W0', cross[1])
    if 'dvl_a' in I:                                 # dv2r8f: D2D group at the N end of the W column, lane to W5
        bb = ['dvs_E4', 'dvs_E3', 'dvs_E2', 'dvs_E1', 'dvs_E0', 'dvs_W0', 'dvs_W1', 'dvs_W2', 'dvs_W3', 'dvs_W4', 'dvs_W5']
        K = st(I, *bb, 'dvl_b', 'dvl_a', 'native59', 'd2d_rom')
        O = st(I, 'd2d_rom', 'native59', 'dvl_a', 'dvl_b', 'dvs_W5', 'dvs_W4', 'dvs_W3', 'dvs_W2', 'dvs_W1', 'dvs_W0', 'dvs_E0', 'dvs_E1', 'dvs_E2', 'dvs_E3', 'dvs_E4', 'dvs_E5')
    else:
        K = st(I, 'dvs_W4', 'dvs_W3', 'dvs_W2', 'dvs_W1', 'dvs_W0', 'dvk_W', 'native59', 'd2d_rom')
        O = st(I, 'd2d_rom', 'native59', 'dvk_W', 'dvs_W0', 'dvs_W1', 'dvs_W2', 'dvs_W3', 'dvs_W4', 'dvs_W5')
    if d.get('variant') == 'A':                     # dv2r8e A: collective at the W edge, AR enters at the backbone end W5
        A = st(I, 'dvs_W5', 'io_collective') + st(I, 'io_collective', 'dvs_W5')
    else:
        A = st(I, 'dvs_W0', 'dva_W', 'io_collective') + st(I, 'io_collective', 'dva_W', 'dvs_W0')
    o = dict(R=R, P=P, K=K, O=O, A=A, QK=2 * beats(128, lanes), SILU=beats(128, lanes), BCA=far, SEAM=0, far=far, within=within)
    if rep:
        o.update(NORM=beats(683, lanes) + max(tree_side, within) + 64 + 3, tree=tree_side)
    else:
        o.update(NORM=beats(384, lanes) * 2 + tree_die + far, tree=tree_die)
    return o
KEYS = ('R', 'P', 'QK', 'K', 'O', 'A', 'NORM', 'SILU', 'BCA', 'SEAM')
MULT = dict(R=4, P=1, QK=1, K=1, O=1, A=2, NORM=2, SILU=1, BCA=1, SEAM=1)
def layer(o): return sum(MULT[k] * o[k] for k in KEYS) + (8 if 'far' in o or 'tree' in o else 0)   # +8 lane/stream serialisation (DV)
if __name__ == '__main__':
    q3h, dv1f, dv2f = sys.argv[1:4]
    D = dict(q3h=base(q3h), dv1_L8=dv1(dv1f, 8), dv2_L8=dv2(dv2f, 8), dv2r_L8=dv2(dv2f, 8, True), dv2r_L16=dv2(dv2f, 16, True))
    b = layer(D['q3h'])
    for k, o in D.items():
        o['layer'] = layer(o); o['delta_layer'] = o['layer'] - b
    print(json.dumps(D, indent=1))
