#!/usr/bin/env python3
"""Q-DV per-layer dependent-hop ledger, q3h (central VM/SU) vs DV, on the two relay-skip models.  A hop is the
face-projected pin-to-pin Manhattan length (the cut model's pin rule); register stages = ceil(L / HOP) - 1, HOP = 405 um
(planning reach, measured 425).  Only the transfers that DIFFER between the designs are counted; the shared head chain,
column corridors, in-cluster tree, KV die and collective/PHY internals are identical and cancel.

Per layer (TP8 compute die, Q_OPS order; all serial on the token's critical path):
  R  result landing, 4 x (qkv, o, gate/up, down): worst cluster -> VM (q3h: bword + port<->half-band + half-train + rb) /
     -> owning slice (DV: far-band feedthrough 12 stages in the near cluster + station + lane)
  P  qkv level 9 between pair stations (DV only), 1 x
  X  broadcast source, 3 x (h after RMSNorm1 / RMSNorm2, act after SiLU*mul): SU -> xs_tap -> first head (q3h) / worst
     slice -> gather exit -> first head (DV)
  O  o_proj input, 1 x: d2d attention return -> native59 -> VM -> xs_tap -> first head / native59 -> top slice -> gather
  N  global scalar tree, 2 x (RMSNorm1, RMSNorm2): 0 (inside the SU) / worst slice -> root slice and back (DV)
  A  all-reduce, 2 x (o, down): VM -> seq_su -> collective and back to VM / worst slice -> bottom row -> collective, back
  K  q / K / V export, 1 x: SU -> native59 -> d2d / worst qkv-owning slice -> top row -> native59 -> d2d
  S  SU <-> VM: abutted registered seam in q3h (0), slice-local in DV (0): not counted (no gain claimed)."""
import json, math, sys
HOP = 405.0
FEED = math.ceil(5184 / HOP) - 1          # far-band rs feedthrough inside the near cluster (registered, as bc_o)
def load(f):
    d = json.load(open(f)); return {i['n']: i for i in d['insts']}, d
def L(I, a, b):
    p, q = I[a], I[b]
    cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
    cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
    A, Q = cl(p, cen(q)), cl(q, cen(p))
    return abs(A[0] - Q[0]) + abs(A[1] - Q[1])
THRU = math.ceil(1944 / HOP) - 1          # crossing an intermediate DV slice face to face: in-slice relay registers
def st(I, *path):
    """stages along a block path; every INTERMEDIATE DV slice adds its face-to-face crossing (THRU).  Conservative:
    the q3h paths are not charged their crossings of the 2.5-mm port tiles or the 4.9-mm VM."""
    s = sum(max(0, math.ceil(L(I, a, b) / HOP) - 1) + (1 if k else 0) for k, (a, b) in enumerate(zip(path, path[1:])))
    return s + THRU * sum(1 for n in path[1:-1] if n.startswith('dvs_'))
def base(f):
    I, d = load(f)
    port = {}
    for b, c, bits, eps in d['buses']:
        if b.startswith('bword'): port[eps[0]] = eps[1]
    hb = lambda p: 'sp_halfband_' + str({'sp_port_tiles_0': 0, 'sp_port_tiles_0_f1': 1, 'sp_port_tiles_1': 2, 'sp_port_tiles_1_f1': 3, 'sp_port_tiles_2': 4, 'sp_port_tiles_2_f1': 5}[p])
    hr = lambda p: 'sp_halfres_' + hb(p)[-1]
    R = max(st(I, cl, p, hb(p), p, hr(p), 'sp_vector_memory') for cl, p in port.items())
    X = st(I, 'sp_su64_sfu', 'xs_tap', 'h_23')
    O = st(I, 'd2d_rom', 'native59', 'sp_vector_memory', 'xs_tap', 'h_23')
    A = st(I, 'sp_vector_memory', 'seq_su', 'io_collective') + st(I, 'io_collective', 'seq_su', 'sp_vector_memory')
    K = st(I, 'sp_su64_sfu', 'native59', 'd2d_rom')
    return dict(R=R, P=0, X=X, O=O, N=0, A=A, K=K)
def dv(f):
    I, d = load(f); own = d['own']; ring = {}
    K3 = lambda col, row: f'dvs_{col * 4 + row}'
    idx = lambda k: k if isinstance(k, int) else int(k.split('_')[1])
    col_of = lambda k: idx(k) // 4; row_of = lambda k: idx(k) % 4
    def mesh(a, b):                                    # column then row path on the mesh
        ca, ra, cb, rb = col_of(a), row_of(a), col_of(b), row_of(b); path = [a]
        r = ra
        while r != rb: r += 1 if rb > r else -1; path.append(K3(ca, r))
        c = ca
        while c != cb: c += 1 if cb > c else -1; path.append(K3(c, rb))
        return path
    R = 0
    for sg, k in own.items():
        s, g = sg[0], int(sg[1:])
        near = f'c16_{s}{g}_1'
        R = max(R, FEED + 1 + st(I, near, f'dvr_{s}{g}', f'dvo_{s}{g}', f'dvw_{s}{g}', f'dvs_{k}'))
    P = max(st(I, f'dvr_{s}{g+1}', f'dvr_{s}{g}') for s in 'WE' for g in (0, 2, 4))
    def gx(k, side):                                   # gather path from slice k to the exit of a side
        row = 1 if row_of(k) <= 1 else 2
        p = [f'dvs_{k}'] + mesh(f'dvs_{k}', K3(col_of(k), row))[1:]
        p += mesh(p[-1], K3(0 if side == 'W' else 2, row))[1:]
        return st(I, *p, 'dvg_' + side, 'h_23' if side == 'W' else 'h_24')
    X = max(gx(k, s) for k in range(12) for s in 'WE')
    O = st(I, 'd2d_rom', 'native59', 'dvs_7') + max(gx(k, s) for k in (3, 7, 11) for s in 'WE') - 0
    root = 'dvs_5'
    N = 2 * max(st(I, *mesh(f'dvs_{k}', root)) for k in range(12))
    A = max(st(I, *mesh(f'dvs_{k}', K3(col_of(f'dvs_{k}'), 0)), 'io_collective') for k in range(12)) + \
        max(st(I, 'io_collective', *mesh(K3(c, 0), K3(c, 3))) for c in range(3))
    qkv = [own[f'{s}{g}'] for s in 'WE' for g in (0, 2, 4)]
    Kx = max(st(I, *mesh(f'dvs_{k}', K3(col_of(f'dvs_{k}'), 3)), 'native59', 'd2d_rom') for k in qkv)
    return dict(R=R, P=P, X=X, O=O, N=N, A=A, K=Kx)
MULT = dict(R=4, P=1, X=3, O=1, N=2, A=2, K=1)
if __name__ == '__main__':
    b, v = base(sys.argv[1]), dv(sys.argv[2])
    extra = dict(lane_serialise=8, qknorm_8lane=6)        # gate/up's level-7 bursts on the one-word lane; one head on 8 lanes (16 beats vs 10)
    delta = {k: MULT[k] * (v[k] - b[k]) for k in MULT}
    per_layer = sum(delta.values()) + sum(extra.values())
    print(json.dumps(dict(hop_um=HOP, feedthrough_stages=FEED, slice_crossing_stages=THRU, base=b, dv=v, mult=MULT, delta=delta, extra=extra,
                          per_layer=per_layer, per_token_36=36 * per_layer), indent=1))
