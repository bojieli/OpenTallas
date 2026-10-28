"""critical-chain geometry: what fraction of lane-weighted (ds_ar-critical) traffic CAN sit inside a <=cap region."""
import json, sys, collections
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
T = P['partition_types']; rect = {}
for p in P['partitions']:
    w, h = T[p['type']]['outline_um']; x, y = p['origin_um']; rect[p['name']] = (x, y, x + w, y + h)
lw = {k: v['w'] for k, v in S['lanes'].items()}; pl = S['port_lane']
crit = collections.Counter(); hops = collections.Counter()
for q in P['ports']:
    a, b = q['src']['part'], q['dst']['part']
    if a == b or a not in rect or b not in rect: continue
    w = lw.get(pl.get(q['id']), 0.0)
    if w: crit[tuple(sorted((a, b)))] += w
tot = sum(crit.values())
for cap in (3.0, 3.5, 4.0, 6.0, 10.0):
    ok = 0
    for (a, b), w in crit.items():
        A, B = rect[a], rect[b]
        bx = (min(A[0], B[0]), min(A[1], B[1]), max(A[2], B[2]), max(A[3], B[3]))
        if max(bx[2] - bx[0], bx[3] - bx[1]) <= cap * 1000: ok += w
    print(f'cap {cap} mm: pair bbox fits for {100*ok/tot:.1f} % of critical weight')
big = sorted(crit.items(), key=lambda kv: -kv[1])[:10]
for (a, b), w in big:
    A, B = rect[a], rect[b]
    print(a, b, round(w), 'part sizes mm', round((A[2]-A[0])/1e3,2), round((A[3]-A[1])/1e3,2), '|', round((B[2]-B[0])/1e3,2), round((B[3]-B[1])/1e3,2))
# lanes with weight: number of ports (= stations/hops) per lane
ln = {l['id']: l for l in P['lanes']}
print('critical lanes', sum(1 for k, v in lw.items() if v > 0), 'mean ports per critical lane',
      round(sum(len(ln[k]['ports']) for k, v in lw.items() if v > 0 and k in ln) / max(1, sum(1 for k, v in lw.items() if v > 0 and k in ln)), 1))
