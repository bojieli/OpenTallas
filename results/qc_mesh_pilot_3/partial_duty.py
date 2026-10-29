#!/usr/bin/env python3
"""Diagnostic both-edge pulse widths on the available routed clips, no mesh proof."""
import json
from pathlib import Path
import sys


def read(p):
    rows = {}
    for line in p.read_text().splitlines():
        fields = line.split()
        if len(fields) == 5:
            rows[(fields[1], fields[0])] = tuple(map(float, fields[2:]))
    return rows


root = Path(sys.argv[1])
result = {"status": "PARTIAL_DIAGNOSTIC", "period_ps": 833, "corners": {}}
for corner in ("TT", "FF"):
    mid = [read(root/'mid'/f'tree_drt_{corner}{suffix}.txt') for suffix in ('', '_fall')]
    vals = {}
    complete = []
    for clip in ('c0', 'c1', 'c2', 'c3', 'core'):
        p = root/clip
        if not (p/f'tree_drt_{corner}_fall.txt').exists():
            continue
        complete.append(clip)
        entry = (json.loads((p/'clip.json').read_text())['entry'], 'A')
        edges = []
        for edge, suffix in enumerate(('', '_fall')):
            data = read(p/f'tree_drt_{corner}{suffix}.txt')
            shift = tuple(mid[edge][entry][i]-data[entry][i] for i in (0, 1))
            edges.append({k: tuple(v[i]+shift[i] for i in (0, 1)) for k, v in data.items()})
        for key in sorted(edges[0].keys() & edges[1].keys()):
            name, pin = key
            if pin != 'A' or not name.startswith(('M', 'L_')):
                continue
            r, f = edges[0][key], edges[1][key]
            vals[name] = {"high_min_ps": 416.5+f[1]-r[0], "high_max_ps": 416.5+f[0]-r[1],
                          "low_min_ps": 416.5+r[1]-f[0], "low_max_ps": 416.5+r[0]-f[1]}
    result['corners'][corner] = {"clips": complete, "sinks": vals,
       "min_high_ps": min(v['high_min_ps'] for v in vals.values()),
       "min_low_ps": min(v['low_min_ps'] for v in vals.values())}
print(json.dumps(result, indent=2))
