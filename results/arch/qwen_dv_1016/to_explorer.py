#!/usr/bin/env python3
"""Q-DV planning model -> opentallas.dataflow.links.v1 record (for dataflow_links.py import).  Ends are the cut model's
face-projected pin points (planning, not generated pins); clocks/resets omitted.  to_explorer.py MODEL OUT ID LABEL REV NOTE"""
import json, sys, gzip
m, out, rid, label, rev, note = sys.argv[1:7]
d = json.load(open(m)); I = d['insts']; ix = {i['n']: k for k, i in enumerate(I)}
cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
grp = lambda i: i['n'].split('_')[0]
B = dict(name=[i['n'] for i in I], master=[i['m'] for i in I], kind=[i['m'] for i in I], group=[grp(i) for i in I],
         reg=[1 if i['m'] == 'qfd_dv_lane_relay' else 0 for i in I], x=[i['x'] for i in I], y=[i['y'] for i in I],
         w=[i['w'] for i in I], h=[i['h'] for i in I])
L = []
for b, c, bits, eps in d['buses']:
    if c in ('clock_trunk', 'reset'): continue
    p = [e for e in eps if e in ix]
    if len(p) < 2: continue
    pairs = list(zip(p, p[1:])) if len(p) == 2 else [(p[0], t) for t in p[1:]]
    for k, (a, q) in enumerate(pairs):
        A, Q = cl(I[ix[a]], cen(I[ix[q]])), cl(I[ix[q]], cen(I[ix[a]]))
        L.append(dict(i=b if len(pairs) == 1 else f'{b}#{k}', c=c, b=bits, d=1, e=[[ix[a], 'o', round(A[0], 2), round(A[1], 2), 'pin'], [ix[q], 'i', round(Q[0], 2), round(Q[1], 2), 'pin']], s=None))
W = max(i['x'] + i['w'] for i in I) + 21.6; H = max(i['y'] + i['h'] for i in I) + 21.6
rec = dict(schema='opentallas.dataflow.links.v1', id=rid, label=label, design='qwen_rom', token_designs=['qwen_rom'], revision=rev, role='candidate',
           scope='Q-DV relay-skip planning model (graph surgery on q3h final smoke); no GEN, no routed qualification',
           reach_um=405.0, reach_source='planning hop 405 um (provisional; H-REACH buffered reach pending)', outline=[round(W, 2), round(H, 2)],
           registers='relays implicit (stage counts = ceil(L/405)-1 in cycles_v2.py)', stages_explicit=False,
           direction='first end drives (model bus order)', pins='face-projected planning points, not generated pins',
           candidate=dict(of='qwen_r2h5', agent='Q-DV', name=rev, note=note, log='/home/ubuntu/claude-takeover-20261007/HANDOFF.md (0cj Q-DV)'),
           blocks=B, links=L, provenance=dict(inputs=[dict(path=m, sha256=__import__('hashlib').sha256(open(m, 'rb').read()).hexdigest(), role='Q-DV model')]))
json.dump(rec, open(out, 'w'))
print(out, len(I), 'blocks', len(L), 'links')
