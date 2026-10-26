#!/usr/bin/env python3
"""Lane-ordered N face for ot_s81_engram_mixq_shcol_b (compact 2x2 MIX4 cluster, S-ENGRAM+NORM MIX4-PARENT 10-16).

The spread plan (spread_face_pins.py) puts each 256-bit bus contiguously along the N face, so a mul4's 384 operand bits
are scattered over the whole 164 um face.  In the compact column the payload leaf sits under the mul4 pair's E half
(add8 W of it), so this plan keeps every legal track position of the spread plan and only re-assigns names:
W -> E: ov, iv, ph, then lane by lane (lanes 0..7): h, kv, w, result bits of that 32-bit lane.  Lanes 0-3 (mul4[2c])
land on the W half, lanes 4-7 (mul4[2c+1]) on the E half.  The S (VM) face and W (clock/reset) face are unchanged.

    python3 tools/s81_engram_mix/banded/repin_shcolb.py IN.tcl OUT.tcl
"""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
lines = open(src).read().splitlines()
head = [l for l in lines if not l.startswith('place_pin')]
pins = []
for l in lines:
    m = re.match(r'place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}(.*)$', l)
    if m:
        pins.append(dict(name=m[1], layer=m[2], x=float(m[3]), y=float(m[4]), rest=m[5], line=l))
H = max(p['y'] for p in pins)
north = sorted([p for p in pins if abs(p['y'] - H) < 1e-6], key=lambda p: p['x'])
order = ['ov', 'iv', 'ph'] + [f'{b}[{32 * l + i}]' for l in range(8) for b in ('h', 'kv', 'w', 'result') for i in range(32)]
assert sorted(order) == sorted(p['name'] for p in north), 'N face set changed'
out = list(head)
for p in pins:
    if abs(p['y'] - H) >= 1e-6:
        out.append(p['line'])
for p, name in zip(north, order):
    out.append(f"place_pin -pin_name {{{name}}} -layer {p['layer']} -location {{{p['x']:.3f} {p['y']:.3f}}}{p['rest']}")
out[0:0] = ['# lane-ordered N face (tools/s81_engram_mix/banded/repin_shcolb.py): positions of ' + src.rsplit('/', 1)[-1] + ', names W->E ov iv ph, then per lane h kv w result']
open(dst, 'w').write('\n'.join(out) + '\n')
print(len(pins), 'pins;', len(north), 'N face re-ordered')
