#!/usr/bin/env python3
"""Per-layer dependent-hop cycle ledger (373 um measured hard reach, centroid Manhattan as metrics.py; register stages =
ceil(L/373)-1 per hop).  Counts per layer from the qwen_rom token path (13 ops / layer, all critical):
  A (central SU, row-interleaved slices): 21 x dLsu (9 SU read passes x 2 [address out + data back] + 3 dependent
  writes: attn_tail, residual, q/k after rope), 5 x dLseq (attention return write, 2 allreduce reads + 2 returns),
  1 x dLnat (q / KV export read), 1 x dLxs (o_proj x read VM->xs_tap), -4 x drb (qkv, o_proj, gate_up, down landings).
  C (SU split): 4 x Lred (2 norms x [partial in + scale out]), 3 x dLxs_sw (x after rmsnorm1, rmsnorm2, SiLU*mul),
  1 x dLxs_aw, 1 x dLnat (q / KV from SU slices), 5 x dLseq, -4 x drb; SU reads / writes slice-local (0)."""
import json, math, sys
HOP = 373.0
import os
MODE = os.environ.get('HOPMODE', 'centroid')
def load(f):
    d = json.load(open(f)); return {i['n']: i for i in d['insts']}
def L(I, a, b):
    p, q = I[a], I[b]
    if MODE == 'box':   # face-to-face gap (paths_q3h.py bd()): pins on the facing faces
        l = max(0.0, q['x'] - (p['x'] + p['w']), p['x'] - (q['x'] + q['w'])) + max(0.0, q['y'] - (p['y'] + p['h']), p['y'] - (q['y'] + q['h']))
    else:
        l = abs(p['x'] + p['w'] / 2 - q['x'] - q['w'] / 2) + abs(p['y'] + p['h'] / 2 - q['y'] - q['h'] / 2)
    return max(0, math.ceil(l / HOP) - 1), round(l / 1000, 2)
def worst(I, srcs, dst):
    r = [L(I, s, dst) for s in srcs]; return max(r)
def ledger(base, var, v):
    B, V = load(base), load(var)
    S = [f'vm_s{k}' for k in range(6)]; HR = [f'sp_halfres_{k}' for k in range(6)]
    rb_old = max(L(B, h, 'sp_vector_memory') for h in HR); rb_new = max(L(V, h, s) for h, s in zip(HR, S))
    o = dict(rb_old=rb_old, rb_new=rb_new)
    g = lambda dst: (L(B, 'sp_vector_memory', dst), worst(V, S, dst))
    o['seq'] = g('seq_su'); o['nat'] = g('native59'); o['xs_aw'] = g('xs_tap')
    d = lambda t: t[1][0] - t[0][0]
    drb = rb_old[0] - rb_new[0]
    if v == 'A':
        o['su'] = g('sp_su64_sfu')
        terms = dict(su_reads_writes=21 * d(o['su']), seq=5 * d(o['seq']), nat=d(o['nat']), xs_aw=d(o['xs_aw']), rb=-4 * drb)
    else:
        U = [f'su_s{k}' for k in range(6)]
        o['red'] = worst(V, U, 'su_red'); o['xs_sw'] = (L(B, 'sp_su64_sfu', 'xs_tap'), worst(V, U, 'xs_tap'))
        o['nat_su'] = (L(B, 'sp_su64_sfu', 'native59'), worst(V, U, 'native59'))
        terms = dict(norm_reduce=4 * o['red'][0], xs_sw=3 * d(o['xs_sw']), xs_aw=d(o['xs_aw']), nat=d(o['nat_su']), seq=5 * d(o['seq']), rb=-4 * drb)
    o['terms'] = terms; o['per_layer'] = sum(terms.values()); o['per_token_36'] = 36 * o['per_layer']
    return o
if __name__ == '__main__':
    base = sys.argv[1]
    for var, v in zip(sys.argv[2::2], sys.argv[3::2]):
        print(var, json.dumps(ledger(base, var, v)))
