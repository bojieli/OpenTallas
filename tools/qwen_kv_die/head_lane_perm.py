"""KVPLAN2 2215 (2026-10-16): bottleneck lane -> grid-slot assignment for the r4 head plan (head_native_plan_r4.py --perm).
Cost of lane t in slot s = the worst per-hop pin-region bound of its chains: lane kp/kpv/gf -> stk -> ktree group (2 hops),
front quarter -> stin -> lane inputs (2), lane nb -> nb1 -> nb2 -> head E face (3), front -> stin -> lane rst_n (2, + RW).
The bottleneck assignment is found by threshold + bipartite matching, then pairwise swaps cut the sum.
Run from the repo root:  RW=40 python3 tools/qwen_kv_die/head_lane_perm.py CHANNEL|- KTREE_X
head_reach400 plans (RW=40, ktree x 540, score x 388.8, reach 400):
  r4: head_native_plan_r4.py OUT --reach 400 --perm <PERM of '-'> --ktree-x 540 --score-x 388.8
  ft: head_native_plan_r4.py OUT --channel 16.2,351.0,712.8 --reach 400 --perm <PERM of '16.2,351.0,712.8'> --ktree-x 540 --score-x 388.8
"""
import sys, json, itertools
sys.path.insert(0, 'tools/qwen_kv_die')
import head_native_plan_r4 as H
ch = tuple(map(float, sys.argv[1].split(','))) if len(sys.argv) > 1 and sys.argv[1] != '-' else None
lane = H.read_pins('physical/ref_tile/qkh_lane8_ref_b/views/ot_qkh_lane8/ot_qkh_lane8.lef')
kt = H.read_pins('physical/ref_tile/qkh_ktree_ref/views/ot_qkh_ktree/ot_qkh_ktree.lef')
dy = ch[0] if ch else 0.
grid = [(43.2 + 172.8 * c, 54. + 151.2 * r + (dy if r >= 1 else 0.)) for c in range(6) for r in range(3) if not (r == 0 and c in (2, 3))]
kx, ky = float(sys.argv[2]) if len(sys.argv) > 2 else 388.8, 54.
W = H.W
import os; RW = float(os.environ.get('RW', '40'))
def reg(x, y, names): return H.region([(x + lane[n][0], y + lane[n][1]) for n in lane if n.split('[')[0] in names])
def cost(t, s):
    x, y = grid[s]
    kp = H.region([(kx + kt[f'kp_in[{j}]'][0], ky + kt[f'kp_in[{j}]'][1]) for j in range(32 * t, 32 * t + 32)] + [(kx + kt[f'gf_in[{t}]'][0], ky + kt[f'gf_in[{t}]'][1])])
    a = H.bound(reg(x, y, ('kp', 'kpv', 'gf')), kp) + 21.6 + 5.4        # + the stk's own N->S span
    fr = [(216 + 135 * (t // 4) + 32.4 * (t % 4), 48.6), (216 + 135 * (t // 4) + 32.4 * (t % 4 + 1), 48.6)]
    b = H.bound(fr, reg(x, y, ('c_in', 'row_in', 'e_in', 'lt_in', 'hid', 'q_valid_in', 'q_beat_in', 'q_data_in'))) + 43.2 + 32.4
    nbt = [(W, 197.1 + 0.096 * 64 * t), (W, 197.1 + 0.096 * (64 * t + 63))]
    c = H.bound(reg(x, y, ('nb',)), nbt) + 2 * 32.4
    r = H.bound(fr, reg(x, y, ('rst_n',))) + 43.2 + 32.4 + RW
    return max(a / 2, b / 2, c / 3, r / 2), (round(a / 2), round(b / 2), round(c / 3), round(r / 2))
C = [[cost(t, s) for s in range(16)] for t in range(16)]
def match(th):
    ms = {}
    def aug(t, seen):
        for s in range(16):
            if C[t][s][0] <= th and s not in seen:
                seen.add(s)
                if s not in ms or aug(ms[s], seen):
                    ms[s] = t; return True
        return False
    for t in range(16):
        if not aug(t, set()): return None
    return {t: s for s, t in ms.items()}
vals = sorted({C[t][s][0] for t in range(16) for s in range(16)})
best = None
for v in vals:
    m = match(v)
    if m: best = (v, m); break
v, m = best
# second criterion: among bottleneck-feasible, minimise sum (greedy swaps)
perm = [m[t] for t in range(16)]
def tot(p): return sum(C[t][p[t]][0] for t in range(16))
improved = True
while improved:
    improved = False
    for i, j in itertools.combinations(range(16), 2):
        q = perm[:]; q[i], q[j] = q[j], q[i]
        if max(C[t][q[t]][0] for t in range(16)) <= v and tot(q) < tot(perm) - 1e-6:
            perm = q; improved = True
print('identity worst', round(max(C[t][t][0] for t in range(16)), 1), 'best bottleneck', round(v, 1))
print('PERM', ','.join(map(str, perm)))
for t in range(16): print(' lane', t, 'slot', perm[t], grid[perm[t]], 'kp/front/nb per hop', C[t][perm[t]][1], 'identity', C[t][t][1])
