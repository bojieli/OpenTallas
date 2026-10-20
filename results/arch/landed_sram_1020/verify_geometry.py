"""Check the endpoint triangle bound, including different SRAM write/read pins."""
from decimal import Decimal as D
from pathlib import Path
import hashlib
import itertools
import json
import re

root = Path(__file__).resolve().parent
repo = root.parents[2]
lef = repo / 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.lef'
text = lef.read_text()
width, height = map(D, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', text).groups())


def distance(a, b):
    return sum(abs(x-y) for x, y in zip(a, b))


def bound(src, wpin, rpin, dst, reach):
    assert distance(src, wpin) <= reach
    assert distance(rpin, dst) <= reach
    return distance(src, dst) <= 2*reach + distance(wpin, rpin)


# Positive boundary case disproves the previous single-point810 assumption.
src, wpin, rpin, dst = ((D(x), D(0)) for x in [-405, 0, 10, 415])
assert distance(src, dst) == 820 > 810
assert bound(src, wpin, rpin, dst, D(405))
assert distance(src, dst) == 2*D(405) + distance(wpin, rpin)
# Cover independent pin positions and both axes, including nonzero macro origin.
for sx, sy, wx, wy, rx, ry in itertools.product(range(-2, 3), repeat=6):
    a, w, r, z = (sx, sy), (wx, wy), (rx, ry), (sx+rx, sy+ry)
    reach = max(distance(a, w), distance(r, z))
    assert bound(a, w, r, z, reach)

pins = {}
for name, body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n', text, re.S):
    rects = [tuple(map(D, m)) for m in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', body)]
    pins[name] = [(x, y) for x1, y1, x2, y2 in rects for x, y in itertools.product((x1, x2), (y1, y2))]
same_bit_max = D(0)
for bit in range(64):
    a, b = pins[f'wd_in[{bit}]'], pins[f'rd_out[{bit}]']
    assert a and b
    same_bit_max = max(same_bit_max, max(distance(x,y) for x,y in itertools.product(a,b)))
assert same_bit_max <= width + height
report = dict(scope='SOURCE MODEL ONLY: no centres or old register pins establish a new placed endpoint certificate',
              proof='|s-d|1 <= |s-w|1+|w-r|1+|r-d|1 <= reachW+max_macro_write_read_pin_displacement+reachR',
              lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),
              external_reach_each_um=405, macro_width_um=float(width), macro_height_um=float(height),
              conservative_internal_displacement_um=float(width+height),
              conservative_two_external_segment_limit_um=float(810+width+height),
              same_bit_rect_corner_max_displacement_um=float(same_bit_max),
              same_bit_two_external_segment_limit_um=float(810+same_bit_max),
              selfcheck_unequal_pins_820_feasible=True,
              selfcheck_grid_cases=5**6, physical_qualified=False)
print(json.dumps(report, indent=2))
