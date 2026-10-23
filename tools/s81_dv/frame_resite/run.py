#!/usr/bin/env python3
import json, copy, sys, time
import numpy as np
import hops as H, optimize as O, netgraph as g
R = '/home/ubuntu/scratch/s81-p8/resite'
d = json.load(open(f'{R}/orig.json'))
dp = json.load(open('/home/ubuntu/wt/s81-p6-1023/physical/die_plan/s81/die_plan.json'))['partition_types']
bands = [(M, k) for M in ('col_h9', 'col_h10') for k in range(3)] if len(sys.argv) < 2 else [(a.split(':')[0], int(a.split(':')[1])) for a in sys.argv[1:]]
res = {}
for M, k in bands:
    pts = sorted(p for p in dp if p.startswith(f'{M}_r{k}_') and p.endswith('__t1'))
    lst = copy.deepcopy(d['masters'][M][f'r{k}'])
    models = [H.Model(M, k, lst, dp[p]) for p in pts]
    O.EXCL.clear()
    if k == 0:   # x bus: E port -> one xo station -> W port, and E port -> cfifo: stage-bound, reported separately
        for m in models:
            for gr in m.groups:
                ends = {gr['a'], gr['b']}
                if any(e.startswith('u_xo') for e in ends) and any(e.startswith('P:x') for e in ends):
                    O.EXCL.add((gr['a'], gr['b']))
    logl = []
    def log(s):
        print(s, flush=True); logl.append(s)
    log(f'== {M} r{k} ptypes {pts}')
    t = time.time()
    O.glob(models)
    before = [(a, gr, p) for m, p in zip(models, pts) for a, t_, gr in m.hops()]
    b_tot = sum(t_ for m in models for a, t_, gr in m.hops())
    before_sites = dict(models[0].site)
    cur = O.optimize(models, [dp[p] for p in pts], log, rounds=60)
    after = [(a, gr, p, m) for m, p in zip(models, pts) for a, t_, gr in m.hops()]
    soft = {p: dict(m.spos) for m, p in zip(models, pts)}
    def ser(gr, a, p):
        return dict(hop=round(a, 1), a=gr['a'], b=gr['b'], bits=gr['bits'], la=gr['la'][:4], lb=gr['lb'][:4], ptype=p)
    res[f'{M}_r{k}'] = dict(ptypes=pts, log=logl, before_sites=before_sites, after_sites=dict(models[0].site),
                            before=[ser(gr, a, p) for a, gr, p in sorted(before, key=lambda x: -x[0]) if a > 500],
                            after=[dict(ser(gr, a, p), excl=O.excluded(gr)) for a, gr, p, m in sorted(after, key=lambda x: -x[0]) if a > 500],
                            before_max=max(a for a, *_ in before), after_max=cur[0],
                            before_bitdist=b_tot, after_bitdist=sum(t_ for m in models for a, t_, gr in m.hops()), excl=sorted(map(list, O.EXCL)),
                            soft=soft, info=str(models[0].info), secs=time.time() - t)
    log(f'  done {time.time() - t:.0f}s')
json.dump(res, open(f'{R}/opt_' + '_'.join(f'{M}r{k}' for M, k in bands) + '.json', 'w'), indent=0, default=float)
