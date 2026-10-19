#!/usr/bin/env python3
"""Check cross-net intersections on every generated PG metal and via-cut layer."""
import json
from collections import defaultdict
from pathlib import Path
import sys
layers = defaultdict(list)
for line in Path(sys.argv[1]).read_text().splitlines():
    net, layer, *xy = line.split()
    layers[layer].append((net, *map(int, xy)))
counts = {}
for layer, shapes in layers.items():
    active = []
    overlaps = []
    for a in sorted(shapes, key=lambda t: t[1]):
        active = [b for b in active if b[3] > a[1]]
        for b in active:
            if a[0] != b[0] and max(a[2], b[2]) < min(a[4], b[4]):
                overlaps.append((a, b))
        active.append(a)
    counts[layer] = {'shapes': len(shapes), 'cross_net_intersections': len(overlaps)}
    if overlaps:
        raise SystemExit(f'{layer}: VDD/VSS short: {overlaps[:3]}')
if not {'M5', 'M6', 'M7', 'M8', 'M9', 'V5', 'V6', 'V7', 'V8'} <= layers.keys():
    raise SystemExit('missing expected PG metal/via layers')
print(json.dumps(counts, indent=2, sort_keys=True))
