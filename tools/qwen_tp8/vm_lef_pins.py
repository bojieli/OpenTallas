#!/usr/bin/env python3
"""LEF pin reader for the VM leaf planner (claude/qwen-tp8-vm-1013): macro SIZE and per-pin RECT centroids of a closed
view, grouped by bus.  Used by vm_leaf_plan.py / vm_plane_lanes.py so every lane endpoint is a real LEF pin centroid."""
import re, sys, json, collections
from pathlib import Path

def read(path):
    size = None; pins = {}; cur = None; layer = None
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if not t: continue
        if t[0] == 'SIZE' and size is None: size = (float(t[1]), float(t[3]))
        elif t[0] == 'PIN': cur = t[1]; pins[cur] = dict(rects=[], layer=None, dir=None)
        elif t[0] == 'DIRECTION' and cur: pins[cur]['dir'] = t[1]
        elif t[0] == 'LAYER' and cur: layer = t[1]
        elif t[0] == 'RECT' and cur and cur in pins:
            r = [float(v) for v in t[1:5]]; pins[cur]['rects'].append(r); pins[cur]['layer'] = layer
        elif t[0] == 'END' and len(t) > 1 and t[1] == cur: cur = None
        elif t[0] == 'OBS': cur = None
    out = {}
    for n, p in pins.items():
        if not p['rects'] or n in ('VDD', 'VSS'): continue
        x = sum((r[0] + r[2]) / 2 for r in p['rects']) / len(p['rects']); y = sum((r[1] + r[3]) / 2 for r in p['rects']) / len(p['rects'])
        out[n] = dict(x=x, y=y, layer=p['layer'], dir=p['dir'])
    return size, out

def face(size, p):
    d = {'W': p['x'], 'E': size[0] - p['x'], 'S': p['y'], 'N': size[1] - p['y']}
    return min(d, key=d.get)

def groups(path):
    """bus -> dict(n, face(s), layers, bbox, centroid, bits{index: (x, y)})"""
    size, pins = read(path); g = collections.defaultdict(dict)
    for n, p in pins.items():
        m = re.match(r'(.*)\[(\d+)\]$', n); g[m.group(1) if m else n][int(m.group(2)) if m else 0] = p
    res = {}
    for b, d in g.items():
        xs = [p['x'] for p in d.values()]; ys = [p['y'] for p in d.values()]
        res[b] = dict(n=len(d), faces=dict(collections.Counter(face(size, p) for p in d.values())), layers=sorted({p['layer'] for p in d.values()}),
                      dir=next(iter(d.values()))['dir'], bbox=[round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)],
                      centroid=[round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)], bits={k: (p['x'], p['y']) for k, p in d.items()})
    return size, res

if __name__ == '__main__':
    for f in sys.argv[1:]:
        size, g = groups(f); print(f, size)
        for b, v in sorted(g.items()): print('  ', b, v['n'], v['dir'], v['faces'], v['layers'], v['bbox'], v['centroid'])
