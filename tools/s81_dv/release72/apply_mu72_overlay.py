#!/usr/bin/env python3
"""S81-DIE72-G2: bind the four end parents to the MU72 assembly tops (update the existing master rows in place:
module, clocks, view note; ports / straps / landing data unchanged).  Usage: apply_mu72_overlay.py BIND_TABLE"""
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); t = json.loads(p.read_text())
o = json.loads(Path(__file__).with_name('mu72_overlay.json').read_text())
for m, e in o['masters'].items():
    row = t['masters'][m]
    e = dict(e); add = e.pop('mode_unused_add', [])
    row.update(e)
    mu = row.setdefault('mode_unused', [])
    for a in add:
        if not any(x.get('port') == a['port'] and x.get('when') == a['when'] for x in mu):
            mu.append(a)
t.setdefault('rtl_widths', {}).update(o['rtl_widths'])
p.write_text(json.dumps(t, indent=1) + '\n')
print('MU72_OVERLAY', ' '.join(f"{m}->{e['module']}" for m, e in o['masters'].items()))
