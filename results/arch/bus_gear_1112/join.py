#!/usr/bin/env python3
"""Join crossing inventory with RELAYOUT-QUEUE open rows: per type, widest bus, total bus pins,
densest pin window, ft bits; score = pin/corridor pressure on failing types."""
import csv, collections, re
DIE = {'qwen_compute': 'qc', 'qwen_kvsys': 'kv', 's81_head': 'head', 's81': 's81', 'hbm': 'hbm'}
X = list(csv.DictReader(open('crossings.tsv'), delimiter='\t'))
F = list(csv.DictReader(open('faces.tsv'), delimiter='\t'))
T = list(csv.DictReader(open('ft.tsv'), delimiter='\t'))
Q = [r for r in csv.DictReader(open('RELAYOUT-QUEUE.tsv'), delimiter='\t') if r['die'] in DIE]
per = collections.defaultdict(lambda: dict(maxw=0, maxbus='', pins=0, maxdens=0.0, densbus='', ft=0, ftmax=0,
                                           facemax=0.0, faceinfo='', nbus=0))
for r in X:
    w = int(r['width'])
    for side in ('src', 'dst'):
        k = (r['die'], r[side + '_type'])
        p = per[k]
        p['pins'] += w; p['nbus'] += 1
        if w > p['maxw']:
            p['maxw'] = w; p['maxbus'] = f"{r['port']}:{r[side + '_bus']}({r['src_type']}->{r['dst_type']})"
        d = float(r['pins_per_um'] or 0)
        if d > p['maxdens']:
            p['maxdens'] = d; p['densbus'] = f"{r['port']} {w}b/{r['win_um']}um"
for r in T:
    p = per[(r['die'], r['type'])]; p['ft'] = int(r['ft_bits']); p['ftmax'] = int(r['ft_max_slot'])
for r in F:
    p = per[(r['die'], r['type'])]
    d = float(r['pins_per_um'] or 0)
    if d > p['facemax']:
        p['facemax'] = d; p['faceinfo'] = f"{r['face']} {r['pins']}p({r['bus_pins']}+ft{r['ft_pins']})/{r['face_um']}um"
rows = []
for q in Q:
    die = DIE[q['die']]
    t = q['type']
    base = re.sub(r'__(cl|pv)[0-9a-f]{8}', '', t)
    p = per.get((die, t))
    if p is None:   # cluster / variant rename: nearest base in plan
        cands = [k for k in per if k[0] == die and re.sub(r'__(cl|pv)[0-9a-f]{8}', '', k[1]) == base]
        p = per[cands[0]] if cands else None
    if p is None:
        continue
    score = max(p['maxw'], p['ft'] / 2) * (1 + p['facemax'] / 4)
    rows.append(dict(die=die, type=t, smell=q['top_smell'][:70], status=q['status'], owner=q.get('assigned_owner') or q.get('current_owner'),
                     maxw=p['maxw'], maxbus=p['maxbus'][:90], pins=p['pins'], face=p['faceinfo'], facemax=p['facemax'],
                     dens=p['densbus'], ft=p['ft'], ftmax=p['ftmax'], score=round(score)))
rows.sort(key=lambda r: -r['score'])
ks = list(rows[0].keys())
with open('joined.tsv', 'w') as f:
    f.write('\t'.join(ks) + '\n')
    for r in rows:
        f.write('\t'.join(str(r[k]) for k in ks) + '\n')
print(len(rows))
