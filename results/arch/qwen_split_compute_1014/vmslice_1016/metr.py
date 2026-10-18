#!/usr/bin/env python3
"""Q-VMSLICE metrics: same functions as Q-DIEPLAN3 (dieplan2_1016/metrics.py st(): centroid Manhattan bit-mm, stages
ceil(L/500)-1; run_metrics.py cut: main cuts.py CAP_MODE v3, CLUSTER_PLAN M6, qfd_c_b16 as cluster) + stages at the
measured hard reach 373 um.  python3 metr.py MODEL.json [--top N]"""
import sys, json, math, collections, argparse
import numpy as np
WT = '/home/ubuntu/wt/q-vmslice-1016'
sys.path.insert(0, WT + '/results/arch/qwen_tp8_1012')
import cuts as C
ns = {}; exec(open('/home/ubuntu/artifacts/qvmslice-1016/ref/metrics.py').read().split('\nfor f in sys.argv[1:]:')[0].replace("sys.path.insert(0,'/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_tp8_1012')", ''), ns)
def st373(f, hop=373.0):
    d = json.load(open(f)); I = {i['n']: i for i in d['insts']}
    c = lambda n: (I[n]['x'] + I[n]['w'] / 2, I[n]['y'] + I[n]['h'] / 2)
    tot = 0; mx = (0, None)
    for b, cl, bits, eps in d['buses']:
        if cl in ('clock_trunk', 'reset') or len(eps) < 2: continue
        a = c(eps[0])
        for q in eps[1:]:
            p = c(q); L = abs(a[0] - p[0]) + abs(a[1] - p[1]); s = max(0, math.ceil(L / hop) - 1)
            tot += s
            if s > mx[0]: mx = (s, b)
    return tot, mx
def cutm(f, top=60):
    C.CLUSTER = tuple(C.CLUSTER) + ('qfd_c_b16',) if 'qfd_c_b16' not in C.CLUSTER else C.CLUSTER
    C.CAP_MODE = 'v3'; C.CLUSTER_PLAN = 'M6'
    A = C.Net(f); fine = A.fine(top=top)
    w = max(fine, key=lambda x: x['util'])
    return dict(worst_cut=round(w['util'], 3), worst_at=f"{w['ax']}={w['pos']} win={w['win']} bits={w['bits']} cap={w['usable']}",
                lines_over_055=sum(1 for x in fine if x['util'] > 0.55), lines_over_060=sum(1 for x in fine if x['util'] > 0.6),
                top=[(round(x['util'], 3), x['ax'], x['pos'], x['win'], int(x['bits'])) for x in sorted(fine, key=lambda x: -x['util'])[:8]])
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('model', nargs='+'); ap.add_argument('--top', type=int, default=60)
    a = ap.parse_args()
    for f in a.model:
        r = ns['st'](f); s, mx = st373(f); r.update(stages373=s, max_chain373=mx[0], max_chain373_bus=mx[1]); r.update(cutm(f, a.top))
        print(f, json.dumps(r, default=str))
