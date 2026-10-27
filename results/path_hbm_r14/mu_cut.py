#!/usr/bin/env python3
"""PATH-HBM-R14 NUMBER-CHECK of Codex MU buddy hub cuts with the R12 independent per-sink blocked cut (cut_check.prof)."""
import json, sys
sys.path.insert(0, sys.argv[1])
from cut_check import prof
def run(tf, bound):
    t = json.load(open(tf)); W, H = t['outline_um']
    cores = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]) for h in t['hard_cores']]
    nets = {}
    for s in t['internal_stations']:
        nets.setdefault((s.get('launch'), tuple(s['from_um'])), []).append((s['to_um'], s['bits']))
    out = dict(outline=[W, H], cores=len(cores), stations=len(t['internal_stations']), whole=prof(W, H, nets, cores), segs=[])
    for x0, x1 in ((0.0, bound), (bound, W)):
        nn = {}
        for (l, a), sinks in nets.items():
            xs = [a[0]] + [p[0] for p, _ in sinks]
            if max(xs) < x0 or min(xs) > x1: continue
            cl = lambda p: (min(max(p[0], x0), x1) - x0, p[1])
            nn.setdefault((l, cl(a)), []).extend((cl(p), bb) for p, bb in sinks)
        cc = [(max(a, x0) - x0, y0, min(c, x1) - x0, y1) for a, y0, c, y1 in cores if c > x0 and a < x1]
        out['segs'].append(prof(x1 - x0, H, nn, cc))
    return out
r = {}
for tag, tf in zip(sys.argv[3::2], sys.argv[4::2]):
    r[tag] = run(tf, float(sys.argv[2]))
print(json.dumps(r, indent=1))
