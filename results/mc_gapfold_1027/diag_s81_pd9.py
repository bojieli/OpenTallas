"""PD11 r3 diagnostic: per-pair U from the NEW main mesh_signoff (gap folded) on S81 PD9 me1 + Codex MC, neighbour pairs <= 1 mm."""
import json, sys, tempfile, os
from pathlib import Path
sys.path.insert(0, sys.argv[1]); import die_sta_related as R
B, mc, C = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
S = json.load(open(mc)); P = json.load(open(B / 'place.json'))
L = [k for k in S['loads'] if k in P and not k.startswith('ckm_br_')]
d = Path(tempfile.mkdtemp(dir=sys.argv[5]))
(d / 'mesh.json').write_text(json.dumps({'taps': [{'port': k, 'stub': k} for k in L]}))
os.symlink(B / f'mesh_{C}.json', d / f'mesh_{C}.json')
taps = {k: dict(late_ps=0.0, early_ps=0.0, cppr_node='h') for k in L}
U, rec = R.mesh_signoff(d, taps, {'cppr_node_range_ps': {'h': 0}}, C, mc, 'tree')
Rr = 1000.0; xy = {k: (P[k]['x'], P[k]['y']) for k in L}; cell = {}
for k in L: cell.setdefault((int(xy[k][0] // Rr), int(xy[k][1] // Rr)), []).append(k)
n = 0
for a in L:
    x, y = xy[a]; gx, gy = int(x // Rr), int(y // Rr)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for b in cell.get((gx + dx, gy + dy), []):
                if b <= a: continue
                if abs(x - xy[b][0]) + abs(y - xy[b][1]) > Rr: continue
                U(a, b); n += 1
print(C, 'mesh-mesh pairs', n, json.dumps(U.stats()))
