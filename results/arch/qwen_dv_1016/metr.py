#!/usr/bin/env python3
"""Q-DV metrics = Q-VMSLICE metr.py / dieplan2 metrics.py st() (centroid Manhattan bit-mm, stages ceil(L/500)-1,
stages at reach) + main cuts.py (CAP_MODE v3, CLUSTER_PLAN M6, cluster masters as clusters)."""
import sys, json, math, collections, argparse
sys.path.insert(0, '/home/ubuntu/wt/qdv-1016/results/arch/qwen_tp8_1012')
import cuts as C
def st(f, hop=None):
    d = json.load(open(f)); I = {i['n']: i for i in d['insts']}
    c = lambda n: (I[n]['x'] + I[n]['w'] / 2, I[n]['y'] + I[n]['h'] / 2)
    S = collections.defaultdict(lambda: [0, 0]); bm = 0; s3 = 0; mx = (0, None); longest = (0, None)
    for b, cl, bits, eps in d['buses']:
        if cl in ('clock_trunk', 'reset') or len(eps) < 2: continue
        a = c(eps[0])
        for q in eps[1:]:
            p = c(q); L = abs(a[0] - p[0]) + abs(a[1] - p[1]); s = max(0, math.ceil(L / 500) - 1)
            S[cl][0] += s; S[cl][1] = max(S[cl][1], s); bm += bits * L / 1000
            if hop:
                t = max(0, math.ceil(L / hop) - 1); s3 += t
                if t > mx[0]: mx = (t, b)
            if L > longest[0]: longest = (round(L), b)
    W = max(i['x'] + i['w'] for i in I.values()); H = max(i['y'] + i['h'] for i in I.values())
    r = dict(bitmm=round(bm), stages=sum(v[0] for v in S.values()), max_chain=max(v[1] for v in S.values()),
             die=[round(W + 21.6, 2), round(H + 21.6, 2)], mm2=round((W + 21.6) * (H + 21.6) / 1e6, 1), insts=len(I), longest_hop=longest)
    if hop: r.update({f'stages{int(hop)}': s3, f'max_chain{int(hop)}': mx})
    return r
def cutm(f, top=60, clusters=()):
    extra = tuple(m for m in ('qfd_c_b16',) + tuple(clusters) if m not in C.CLUSTER)
    C.CLUSTER = tuple(C.CLUSTER) + extra
    C.CAP_MODE = 'v3'; C.CLUSTER_PLAN = 'M6'
    A = C.Net(f); fine = A.fine(top=top)
    w = max(fine, key=lambda x: x['util'])
    return dict(worst_cut=round(w['util'], 3), worst_at=f"{w['ax']}={w['pos']} win={w['win']} bits={w['bits']} cap={w['usable']}",
                lines_over_055=sum(1 for x in fine if x['util'] > 0.55), lines_over_060=sum(1 for x in fine if x['util'] > 0.6),
                top=[(round(x['util'], 3), x['ax'], x['pos'], x['win'], int(x['bits'])) for x in sorted(fine, key=lambda x: -x['util'])[:8]])
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('model', nargs='+'); ap.add_argument('--top', type=int, default=60)
    ap.add_argument('--hop', type=float, default=405.0); ap.add_argument('--cluster', action='append', default=[])
    a = ap.parse_args()
    for f in a.model:
        r = st(f, a.hop); r.update(cutm(f, a.top, a.cluster)); print(f, json.dumps(r, default=str))
