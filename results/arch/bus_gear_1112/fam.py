#!/usr/bin/env python3
"""Bus-family view: for each lane family (port-id class) the width, hop count, types touched (endpoint or ft),
how many of those types are open in RELAYOUT-QUEUE, and the densest pin window seen."""
import csv, collections, re
DIE = {'qwen_compute': 'qc', 'qwen_kvsys': 'kv', 's81_head': 'head', 's81': 's81', 'hbm': 'hbm'}
X = list(csv.DictReader(open('crossings.tsv'), delimiter='\t'))
Q = [r for r in csv.DictReader(open('RELAYOUT-QUEUE.tsv'), delimiter='\t') if r['die'] in DIE]
strip = lambda t: re.sub(r'__(cl|pv)[0-9a-f]{8}', '', t)
openq = collections.defaultdict(dict)
for q in Q:
    openq[DIE[q['die']]][strip(q['type'])] = q['top_smell'][:40]

def fam(die, pid):
    f = re.sub(r'(__\d+)$', '', pid)
    if die == 'hbm':
        f = re.sub(r'_\d+$', '', f); f = re.sub(r'm$', '', f)
    elif die == 's81':
        f = re.sub(r'_(W|E)\d', '_*', f); f = re.sub(r'_p\d', '_p*', f); f = re.sub(r'__svc_\d+__svc_\d+', '__svc', f)
        f = re.sub(r'_[0-9]+$', '_*', f); f = re.sub(r'_s_\d[NS]_L\d', '_s', f)
    elif die == 'qc':
        f = re.sub(r'_(W|E)\d_', '_*_', f); f = re.sub(r'_\d\d__', '_xx__', f); f = re.sub(r'__[a-z]+\d+$', '__*', f)
    elif die == 'kv':
        f = re.sub(r'_\d+$', '', f)
    else:
        f = re.sub(r'\d+', '#', f)
    return f

F = collections.defaultdict(lambda: dict(w=collections.Counter(), hops=0, types=set(), dens=0.0))
for r in X:
    k = (r['die'], fam(r['die'], r['port']))
    f = F[k]
    f['w'][int(r['width'])] += int(r['n'])
    f['hops'] += int(r['n'])
    f['types'].update([strip(r['src_type']), strip(r['dst_type'])])
    f['dens'] = max(f['dens'], float(r['pins_per_um'] or 0))
rows = []
for (die, fm), f in F.items():
    wmax = max(f['w'])
    op = sorted(t for t in f['types'] if t in openq[die])
    bitsum = sum(w * n for w, n in f['w'].items())
    rows.append(dict(die=die, family=fm, wmax=wmax, hops=f['hops'], bit_hops=bitsum, types=len(f['types']),
                     open_types=len(op), open_list=','.join(op[:6]), dens=f['dens'],
                     score=wmax * len(op)))
rows.sort(key=lambda r: -r['score'])
ks = list(rows[0])
with open('families.tsv', 'w') as fo:
    fo.write('\t'.join(ks) + '\n')
    for r in rows:
        fo.write('\t'.join(str(r[k]) for k in ks) + '\n')
for r in rows[:60]:
    print(f"{r['die']:4s} {r['family'][:34]:34s} w={r['wmax']:5d} hops={r['hops']:4d} open={r['open_types']:3d}/{r['types']:3d} dens={r['dens']:5.2f} {r['open_list'][:110]}")
