#!/usr/bin/env python3
"""Recompute exact published quarter pin to planned station distances.

This proves the stated centerline model, not placement or routed-wire reach.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'results/arch/s81_topk_plana_parent_1021'
model = json.loads((PACKET / 'geometry.json').read_text())
lef = (ROOT / 'physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q/dsdv_bksel_q.lef').read_text()
pins = {}
for match in re.finditer(r'  PIN ([^\n]+)\n(.*?)\n  END \1\n', lef, re.S):
    if not re.match(r'(lane|f_c|f_cr|t_s|t_o)(\[|$)', match[1]):
        continue
    rect = re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', match[2])
    assert rect, match[1]
    x0, y0, x1, y1 = map(float, rect.groups())
    pins[match[1]] = ((x0 + x1) / 2, (y0 + y1) / 2)
assert len(pins) == 1801, len(pins)
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
distances = []
for quarter, ybase in enumerate([43.2, 864, 1771.2, 2592]):
    north, east = model['N_paths'][quarter], model['E_paths'][quarter]
    for name, (x, y) in pins.items():
        actual = [43.2 + 648 - x, ybase + (y if quarter < 2 else 648 - y)]
        station = east[0] if name.startswith('t_o') else north[0]
        distances.append(md(actual, station))
    for path in [north, east + north[2:]]:
        distances += [md(a, b) for a, b in zip(path, path[1:])]
assert len(distances) == 7244
assert max(distances) <= 405
assert abs(max(distances) - model['max_manhattan_um']) < 0.0001
rects = model['rectangles']
for rect in rects:
    assert all(0 <= rect['xy'][k] <= rect['xy'][k] + rect['wh'][k] <= [907.2, 3283.2][k] for k in [0, 1])
for index, a in enumerate(rects):
    for b in rects[index + 1:]:
        assert not all(min(a['xy'][k] + a['wh'][k], b['xy'][k] + b['wh'][k]) > max(a['xy'][k], b['xy'][k]) + 1e-6 for k in [0, 1])
print(f'PLANA_GEOMETRY_PASS checks={len(distances)} max_um={max(distances):.4f}; centerline scope only')
