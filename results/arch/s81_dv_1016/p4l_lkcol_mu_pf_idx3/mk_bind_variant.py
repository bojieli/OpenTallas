#!/usr/bin/env python3
"""S81-DIEPLACE2 (10-20): bind-check variant of the --idxrd 3 plan for the CURRENT GEN source (no dsdv_idx_rg2 RTL yet):
the 8 readers + qf and their links are removed and every region's rq / rd lane is re-ended on its controller (reader
bypassed, wire extended through the empty reader slot).  Everything else (6 dropped row-1 frames, widened service band
1,431 x 1,100, re-routed mu_0S / mu_7S) is the idx3 plan, so the strict bind proves the frame / band / lane changes bind
to the MU RTL; the reader masters bind later (S81-L20RD / S81-MU6)."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
drop = {i for i, b in enumerate(p['blocks']) if b['kind'] == 'idx'}
names = [b['name'] for b in p['blocks']]
remap, nb = {}, []
for i, b in enumerate(p['blocks']):
    if i not in drop:
        remap[i] = len(nb); nb.append(b)
idx = {b['name']: i for i, b in enumerate(nb)}
nl = []
for l in p['links']:
    if l['c'] == 'idx' or l['i'][:5] in ('hrqc_', 'hrdc_'):
        continue
    l = json.loads(json.dumps(l))
    if l['i'][:4] in ('hrq_', 'hrd_'):
        k = int(l['i'][4:]); e = 1 if l['i'][:4] == 'hrq_' else 0
        C = nb[idx[f'ctrl_{k:02d}']]
        x, y = l['e'][e][2], l['e'][e][3]
        yc = C['y'] + C['h']
        l['e'][e] = [idx[f'ctrl_{k:02d}'], 'rq' if e else 'rd', x, round(yc, 1), 'box']
        seg = [x, y, x, round(yc, 1), l['b']] if e else [x, round(yc, 1), x, y, l['b']]
        l['h'] = l['h'] + [seg] if e else [seg] + l['h']
        l['L'] = round(l['L'] + abs(y - yc), 1)
    else:
        for e in l['e']:
            assert e[0] not in drop, l['i']
            e[0] = remap[e[0]]
    nl.append(l)
p['blocks'], p['links'] = nb, nl
p['facts']['bind_variant'] = 'S81-DIEPLACE2: idx3 plan with readers bypassed (no dsdv_idx_rg2 RTL in GEN yet); rq/rd re-ended on the controllers'
json.dump(p, open(dst, 'w'))
print('blocks', len(nb), 'links', len(nl), 'dropped', [names[i] for i in sorted(drop)])
