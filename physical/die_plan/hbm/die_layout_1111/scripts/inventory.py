"""DIE-LAYOUT-HBM: inventory of HBM die links >= 256 b that are > 1 mm or over reach (explorer links.tsv of plan e6bb764f1f22),
grouped; per group the bits, the corridor direction and the M8/M9 over-the-cell (form d) supply check."""
import csv, json, sys, collections
R = list(csv.DictReader(open(sys.argv[1]), delimiter='\t')); P = json.load(open(sys.argv[2]))
part = {p['name']: p for p in P['partitions']}; T = P['partition_types']
def box(n):
    p = part[n]; w, h = T[p['type']]['outline_um']
    if p['orient'] in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
    return p['origin_um'][0], p['origin_um'][1], w, h
def grp(d, s, via):
    k = lambda n: n.split('_', 1)[1] if '_' in n else n
    a, b = k(d), k(s); ab = {a, b}
    if all(x.startswith('b0') for x in ab): return 'A bank ring/bank-bank'
    if d in ('root',) or s in ('root',) or 'PHY_NC' in (d, s) or any(v.startswith('vsN') for v in via): return 'C vsN column / root / PHY_NC'
    if 'hub' in ab and (ab & {'su00', 'su01', 'su10', 'su11', 'su20', 'su21', 'su30', 'su31', 'sm0', 'sm1', 'sm2', 'sm3'}): return 'B hub<->su/sm transits'
    if ab & {'mcb', 'mca'} or (ab & {'spt0', 'spt1', 'spt2', 'spu0', 'spu1'} and ('hub' in ab or 'PHY' in ''.join(ab))): return 'D mcb/spt/spu columns, hub<->PHY'
    if all(x.startswith('su') or x.startswith('b1') for x in ab): return 'E su rows (su/sfu/b1xx)'
    if 'hub' in ab: return 'F hub<->other (bank/b1xx/spb/io)'
    return 'G other'
rows = []
for r in R:
    b = int(r['bits']); L = float(r['length_um'] or 0); hop = float(r['max_hop_um'] or 0)
    if b < 256 or not (L > 1000 or r['status'] == 'over'): continue
    d = r['driver'].split('.')[0]; s = r['sinks'].split('.')[0]; via = [v for v in (r['via'] or '').split(',') if v]
    x0, y0, w0, h0 = box(d) if d in part else (0, 0, 0, 0); x1, y1, w1, h1 = box(s) if s in part else (0, 0, 0, 0)
    dx = abs((x0 + w0 / 2) - (x1 + w1 / 2)); dy = abs((y0 + h0 / 2) - (y1 + h1 / 2))
    rows.append(dict(group=grp(d, s, via), id=r['id'], bits=b, len_um=round(L), max_hop=round(hop), stages=r['stages'], status=r['status'],
                     driver=d, sink=s, n_cross=len(via), cross=','.join(via), dir='NS' if dy > dx else 'EW', bit_mm=round(b * L / 1000)))
rows.sort(key=lambda r: (r['group'], -r['bits'] * r['len_um']))
with open(sys.argv[3], 'w') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)
G = collections.defaultdict(list)
for r in rows: G[r['group']].append(r)
for g, L in sorted(G.items()):
    ns = sum(r['bits'] for r in L if r['dir'] == 'NS'); ew = sum(r['bits'] for r in L if r['dir'] == 'EW')
    print(f"{g}: {len(L)} links, {sum(r['bits'] for r in L)} b (NS {ns}, EW {ew}), over-reach {sum(r['status']=='over' for r in L)}, "
          f"crossing >=1 other block {sum(r['n_cross']>0 for r in L)}, bit-mm {sum(r['bit_mm'] for r in L)}, len {min(r['len_um'] for r in L)}-{max(r['len_um'] for r in L)}; top: "
          + '; '.join(f"{r['id']} {r['bits']}b {r['len_um']}um {r['driver']}->{r['sink']} {r['status']}" for r in sorted(L, key=lambda r: -r['bit_mm'])[:5]))
print(len(rows), 'links total')
