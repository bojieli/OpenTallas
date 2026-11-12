"""DIE-PROTO-3: compact render inputs: guide area per layer on a BIN-um grid (guide rects, DBU 1000/um assumed from
the GRT guide file) + taps {xy, late TT/FF} + partition rects (die frame) from the plan."""
import json, sys, gzip, collections
guide, tta, ttf, plan, out = sys.argv[1:6]; BIN = float(sys.argv[6]) if len(sys.argv) > 6 else 100.0
g = collections.defaultdict(float)
dbu = 1000.0
with open(guide) as f:
    for ln in f:
        p = ln.split()
        if len(p) == 5 and p[4].startswith('M'):
            x1, y1, x2, y2 = (float(v) / dbu for v in p[:4]); L = p[4]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            g[(L, int(cx // BIN), int(cy // BIN))] += (x2 - x1) * (y2 - y1)
T = json.load(open(tta)); F = json.load(open(ttf))
taps = []
FF = {r['port']: r for r in F['taps']}
for r in T['taps']:
    rf = FF.get(r['port'], {})
    taps.append([r['xy_um'][0], r['xy_um'][1], r.get('late_ps'), r.get('early_ps'), rf.get('late_ps'), rf.get('early_ps'), r.get('part')])
P = json.load(gzip.open(plan) if plan.endswith('.gz') else open(plan))
ty = P['partition_types']
parts = []
for p in P['partitions']:
    w, h = ty[p['type']]['outline_um']
    if p.get('orient', 'R0') in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
    parts.append([p['name'], p['type'], p['origin_um'][0], p['origin_um'][1], w, h])
json.dump(dict(bin=BIN, guide=[[k[0], k[1], k[2], v] for k, v in g.items()], taps=taps, parts=parts,
               die=P['die'].get('outline_um') or P['die'].get('size_um')), open(out, 'w'))
print('guide cells', len(g), 'taps', len(taps), 'parts', len(parts))
