#!/usr/bin/env python3
"""CPL-QC-2: plan type (+ optional delta {type:{inst:[x,y,orient]}}) -> moves file for cp_probe.tcl (CORE-PLACE-1 format).
usage: mk_moves.py PLAN TYPE OUT [DELTA]"""
import json, re, sys
plan, tn, out = sys.argv[1:4]
d = json.load(open(sys.argv[4])).get(tn, {}) if len(sys.argv) > 4 else {}
t = json.load(open(plan))['partition_types'][tn]
L = ['# %s %s delta=%s' % (plan, tn, sys.argv[4] if len(sys.argv) > 4 else '-')]
for h in t['hard_cores']:
    inst = h.get('physical_inst') or h['inst']
    key = re.sub(r'[^A-Za-z0-9]+', '_', inst).strip('_')
    dx, dy = h.get('track_offset_um', [0, 0])
    x, y, o = h['origin_um'][0], h['origin_um'][1], h.get('orient', 'R0')
    if h['inst'] in d:
        x, y, o = d[h['inst']]
    L.append('%s %.4f %.4f %s' % (key, x + dx, y + dy, o))
open(out, 'w').write('\n'.join(L) + '\n')
print(len(L) - 1, 'macros')
