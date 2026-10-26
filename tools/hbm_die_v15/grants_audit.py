#!/usr/bin/env python3
"""Final geometry audit of a die grant contract against its plan: every die-level slot inside the die (20 um edge), no
slot/slot or slot/foreign-plan-block overlap (a slot may cover its own plan_block).   grants_audit.py GRANTS PLAN_DIR"""
import json, sys
G = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2] + '/compact.P.json'))
W, H = G['slots'][0]['outline']['w'], G['slots'][0]['outline']['h']
SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}
T = []
for s in G['slots'][1:]:
    if s.get('parent') != 'die' or s.get('origin', {}).get('x') is None:
        continue
    fp = s.get('placed_footprint') or s['outline']; o = s['origin'].get('orient', 'R0')
    w, h = (fp['h'], fp['w']) if o in SWAP and not s.get('placed_footprint') else (fp['w'], fp['h'])
    T.append((s['name'], s['origin']['x'], s['origin']['y'], w, h, s.get('plan_block')))
rep = {t[5] for t in T if t[5]}
O = [(k, b['x'], b['y'], b['w'], b['h'], None) for k, b in P.items() if k not in rep]
ov = lambda a, b: a[1] < b[1] + b[3] - 1e-6 and b[1] < a[1] + a[3] - 1e-6 and a[2] < b[2] + b[4] - 1e-6 and b[2] < a[2] + a[4] - 1e-6
bad = [(a[0], b[0]) for i, a in enumerate(T) for b in T[i + 1:] + O if ov(a, b)]
out = [t[0] for t in T if t[1] < 20 - 1e-6 or t[2] < 20 - 1e-6 or t[1] + t[3] > W - 20 + 1e-6 or t[2] + t[4] > H - 20 + 1e-6]
print(json.dumps(dict(slots=len(T), overlaps=bad[:20], n_overlaps=len(bad), outside=out)))
sys.exit(1 if bad or out else 0)
