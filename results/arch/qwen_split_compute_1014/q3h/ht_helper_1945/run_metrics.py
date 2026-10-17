#!/usr/bin/env python3
"""metrics.py + cutwho (lines > 0.55) on a model, as dieplan2_1016/metrics.py / cutwho.py (CAP_MODE v3, CLUSTER_PLAN M6,
FINE 260).  qfd_c_b16 is added to cuts.CLUSTER (the die routes over a C_B16 on M8 / M9 only, + M6 for horizontal wires
under plan M6) unless --c16-as-v3 (then it is an M5-capped slot like any non-cluster block: optimistic).
  python3 run_metrics.py MODEL.json [--plan M6] [--c16-as-v3] [--top 60]"""
import sys, json, argparse
import numpy as np
sys.path.insert(0, '/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_tp8_1012')
sys.path.insert(0, '/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_split_compute_1014/dieplan2_1016')
import cuts as C
ap = argparse.ArgumentParser(); ap.add_argument('model'); ap.add_argument('--plan', default='M6')
ap.add_argument('--c16-as-v3', action='store_true'); ap.add_argument('--top', type=int, default=60)
a = ap.parse_args()
if not a.c16_as_v3:
    C.CLUSTER = tuple(C.CLUSTER) + ('qfd_c_b16',)
C.CAP_MODE = 'v3'; C.CLUSTER_PLAN = a.plan
import importlib.util
spec = importlib.util.spec_from_file_location('mt', '/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_split_compute_1014/dieplan2_1016/metrics.py')
src = open(spec.origin).read().split('\nfor f in sys.argv[1:]:')[0]
ns = {}; exec(src, ns)
r = ns['st'](a.model)
d = json.load(open(a.model))
A = C.Net(a.model); I = A.I; ids = []
for b, c, bits, eps in d['buses']:
    pp = [I[e] for e in eps if e in I]
    if len(pp) < 2 or c in ('clock_trunk',): continue
    for x, q in (list(zip(pp, pp[1:])) if len(pp) == 2 else [(pp[0], t) for t in pp[1:]]):
        ox = min(x['x'] + x['w'], q['x'] + q['w']) - max(x['x'], q['x'])
        oy = min(x['y'] + x['h'], q['y'] + q['h']) - max(x['y'], q['y'])
        if (ox > 0 and -1.0 <= -oy <= 1.0) or (oy > 0 and -1.0 <= -ox <= 1.0): continue
        if (ox > 0 and 0.0 <= -oy <= getattr(C, 'FACE_GAP_UM', -1)) or (oy > 0 and 0.0 <= -ox <= getattr(C, 'FACE_GAP_UM', -1)): continue
        ids.append((b, x['n'], q['n']))
fine = A.fine(top=a.top)
r.update(worst_cut=round(max(f['util'] for f in fine), 3), lines_over_060=sum(1 for f in fine if f['util'] > 0.6),
         lines_over_055=sum(1 for f in fine if f['util'] > 0.55))
print(a.model, json.dumps(r))
for f in fine:
    if f['util'] <= 0.55: continue
    ax, cp, lo = f['ax'], f['pos'], f['win'][0]
    bits, cap, cov, k, Cc, w = A.cut(ax, cp, np.array([lo, lo + C.FINE]))
    p0, p1 = (0, 2) if ax == 'x' else (1, 3)
    S = A.S; m = (np.minimum(S[:, p0], S[:, p1]) < cp) & (cp < np.maximum(S[:, p0], S[:, p1]))
    who = {}
    for j, kk in zip(np.nonzero(m)[0], k):
        if kk == 0:
            key = (ids[j][1], ids[j][2]); who[key] = who.get(key, 0) + S[j, 4]
    top = sorted(who.items(), key=lambda t: -t[1])[:4]
    print(f"  {f['util']:.3f} {ax}={cp} win={f['win']} bits={f['bits']} cap={f['usable']} fam={f['fam']} :: " + '; '.join(f'{x}->{y} {int(v)}' for (x, y), v in top))
