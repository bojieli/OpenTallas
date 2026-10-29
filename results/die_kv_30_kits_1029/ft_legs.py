#!/usr/bin/env python3
"""DIE-KV-30-KITS: per-FT-slot max planned Manhattan leg (pin_i -> station regs_um ... -> pin_o) vs 405 um."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'tools/die_plan'))
import schema as S
from gen_phys import type_pins
raw = json.load(open(sys.argv[2])); P = S.Plan(raw)
out = {}
for t in sys.argv[3].split(','):
    pins = {(b, i): (x, y) for b, i, _, x, y, _ in type_pins(P, t)}
    worst, over, rows = 0.0, [], []
    for sl in P.types[t].get('ft_slots', []):
        regs = [tuple(r[:2]) for r in sl.get('regs_um', [])]
        m = 0.0
        for bit in range(sl['width'] + 1):
            a = pins.get((sl['name'] + '_i', bit)); b = pins.get((sl['name'] + '_o', bit))
            if a is None or b is None: continue
            pts = [a] + regs + [b]
            m = max(m, max(abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q in zip(pts, pts[1:])))
        rows.append((sl['name'], sl['stations'], len(regs), round(m, 2)))
        worst = max(worst, m)
        if m > 405: over.append(rows[-1])
    out[t] = dict(slots=len(rows), worst_leg_um=round(worst, 2), over_405=over)
    print(t, 'slots', len(rows), 'worst_leg_um', round(worst, 2), 'over405', over[:5])
Path(sys.argv[4]).write_text(json.dumps(out, indent=1) + '\n')
