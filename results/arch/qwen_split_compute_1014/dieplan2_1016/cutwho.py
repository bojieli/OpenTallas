import sys, json, numpy as np
sys.path.insert(0, '/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_tp8_1012')
import cuts as C
C.CAP_MODE = 'v3'; C.CLUSTER_PLAN = sys.argv[2] if len(sys.argv) > 2 else 'A'
p = sys.argv[1]; d = json.load(open(p))
A = C.Net(p)
# record bus ids per segment
I = A.I; ids = []
cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
for b, c, bits, eps in d['buses']:
    pp = [I[e] for e in eps if e in I]
    if len(pp) < 2 or c in ('clock_trunk',): continue
    for a, q in (list(zip(pp, pp[1:])) if len(pp) == 2 else [(pp[0], t) for t in pp[1:]]):
        ox = min(a['x'] + a['w'], q['x'] + q['w']) - max(a['x'], q['x'])
        oy = min(a['y'] + a['h'], q['y'] + q['h']) - max(a['y'], q['y'])
        if (ox > 0 and -1.0 <= -oy <= 1.0) or (oy > 0 and -1.0 <= -ox <= 1.0): continue
        ids.append((b, a['n'], q['n']))
fine = A.fine(top=int(sys.argv[3]) if len(sys.argv) > 3 else 30)
for f in fine:
    if f['util'] <= 0.6: continue
    ax, cp, lo = f['ax'], f['pos'], f['win'][0]
    bits, cap, cov, k, Cc, w = A.cut(ax, cp, np.array([lo, lo + C.FINE]))
    p0, p1 = (0, 2) if ax == 'x' else (1, 3)
    S = A.S; m = (np.minimum(S[:, p0], S[:, p1]) < cp) & (cp < np.maximum(S[:, p0], S[:, p1]))
    idx = np.nonzero(m)[0]
    who = {}
    for j, kk in zip(idx, k):
        if kk == 0:
            key = (ids[j][1], ids[j][2]); who[key] = who.get(key, 0) + S[j, 4]
    top = sorted(who.items(), key=lambda t: -t[1])[:4]
    print(f"{f['util']:.3f} {ax}={cp} win={f['win']} bits={f['bits']} cap={f['usable']} :: " + '; '.join(f'{a}->{b} {int(v)}' for (a, b), v in top))
