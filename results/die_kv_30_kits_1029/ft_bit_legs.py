#!/usr/bin/env python3
"""DIE-KV-30-KITS: per-bit FT legs from the kit's ft_bit_sites.tcl (pin_i -> stage 1..N -> pin_o), Manhattan, vs 405 um."""
import json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'tools/die_plan'))
import schema as S
from gen_phys import type_pins
P = S.Plan(json.load(open(sys.argv[2])))
kits = Path(sys.argv[3]); out = {}
rx = re.compile(r'dict set ff_bit_sites \{(\w+),(\d+),(\d+)\} \{([\d.]+) ([\d.]+)\}')
for t in sys.argv[4].split(','):
    pins = {(b, i): (x, y) for b, i, _, x, y, _ in type_pins(P, t)}
    sites = defaultdict(dict)
    f = kits / t / 'ft_bit_sites.tcl'
    for m in rx.finditer(f.read_text() if f.exists() else ''):
        sites[(m[1], int(m[3]))][int(m[2])] = (float(m[4]), float(m[5]))
    worst = defaultdict(float)
    for (sl, bit), st in sites.items():
        a = pins.get((sl + '_i', bit)); b = pins.get((sl + '_o', bit))
        if a is None or b is None: continue
        pts = [a] + [st[k] for k in sorted(st)] + [b]
        worst[sl] = max(worst[sl], max(abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q in zip(pts, pts[1:])))
    over = sorted(((s, round(v, 2)) for s, v in worst.items() if v > 405), key=lambda r: -r[1])
    out[t] = dict(slots_with_sites=len(worst), worst_leg_um=round(max(worst.values(), default=0), 2), over_405=over)
    print(t, out[t]['slots_with_sites'], out[t]['worst_leg_um'], over[:6])
Path(sys.argv[5]).write_text(json.dumps(out, indent=1) + '\n')
