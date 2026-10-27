"""top-down band-room delta for the landing bands no macro-free site can hold: per (type, face) the face strip depth
D = max over its still-failing buses of ceil(area/max(window,8.64)/2.16)*2.16 (each band directly behind its own
window, all within reach), + the 17.28-um margin rule already inside the outline. Die impact = per lattice cut."""
import json, sys, math, collections
sys.path.insert(0, 'tools/die_plan')
import clock_landing_plan as CLP
P = json.load(open(sys.argv[1])); still = json.load(open(sys.argv[2]))
T = P['partition_types']
cnt = collections.Counter(p['type'] for p in P['partitions'])
inst = collections.defaultdict(list)
for p in P['partitions']: inst[p['type']].append(p['name'])
D = collections.defaultdict(float); buses = collections.defaultdict(list)
for s in still:
    t = T[s['type']]; b = CLP._bus_geom(t, s['bus']); lo, hi = b['window_um']
    rw = 64 * math.ceil((s['width'] + 1) / 64); area = (5*rw*.2916 + 4*rw*.0729 + 160*.2916) / .40
    d = math.ceil(max(8.64, area / max(hi - lo, 8.64)) / 2.16) * 2.16
    k = (s['type'], b['face']); D[k] = max(D[k], d); buses[k].append(s['bus'])
rows = [dict(type=k[0], face=k[1], strip_um=round(v, 2), buses=buses[k], instances=inst[k[0]], outline=T[k[0]]['outline_um']) for k, v in sorted(D.items())]
fx = collections.Counter(); fy = collections.Counter()
for r in rows:
    (fx if r['face'] in 'EW' else fy)[r['type']] = max((fx if r['face'] in 'EW' else fy)[r['type']], r['strip_um'])
json.dump(dict(rows=rows, max_strip_um=max(D.values()), types=len({r['type'] for r in rows}), faces=len(rows),
               bands=len(still)), open(sys.argv[3], 'w'), indent=1)
print('bands', len(still), 'type-faces', len(rows), 'types', len({r['type'] for r in rows}), 'max strip', max(D.values()))
for r in rows: print(r['type'], r['face'], r['strip_um'], len(r['buses']), r['instances'])
