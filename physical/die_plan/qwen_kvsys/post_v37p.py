#!/usr/bin/env python3
"""KV-P6-PINS 10-23: plan v3.7 -> v3.7p.  Applies cores/core_patch_v37p.json (written by core_pins_v37p.py): every
planned hard core gets pins_file cores/<module>_pins.json (top-down pin assignment, shared by the module's instances)
and its orient (chosen so the shared pins face each instance's partners); core moves (origin_um): kvs_pc kvpc2 / kvpc3
swap (serpentine chain), pv joins to the middle of their columns (p0, p1, join, p2, p3: the closed join's 4 faces).  core_conns.json (plan dir) carries the core connectivity for the check.py core_faces rule.
usage: post_v37p.py die_plan.json PLAN_DIR > die_plan.json"""
import json
import sys
from pathlib import Path

p = json.load(open(sys.argv[1]))
patch = json.load(open(Path(sys.argv[2]) / 'cores' / 'core_patch_v37p.json'))
n = no = nm = 0
for tn, cs in patch.items():
    hs = {h['inst']: h for h in p['partition_types'][tn]['hard_cores']}
    for ci, pt in cs.items():
        if 'origin_um' in pt and pt['origin_um'] != hs[ci]['origin_um']:
            hs[ci]['origin_um'] = pt['origin_um']
            nm += 1
    for ci, pt in cs.items():
        hc = hs[ci]
        if 'pins_file' in pt and not hc.get('pins_file'):
            hc['pins_file'] = pt['pins_file']
            hc['note'] = hc.get('note', '').replace('lef/lib/pins pending', 'lef/lib pending; pins top-down (KV-P6-PINS)')
            n += 1
        if pt.get('orient', 'R0') != hc.get('orient', 'R0'):
            hc['orient'] = pt['orient']
            no += 1
p['note'] = p.get('note', '') + (f' | v3.7p (KV-P6-PINS 10-23): top-down pins_file on {n} planned hard cores ({no} '
                                 'mirrored to face their partners; {nm} moved: kvs_pc serpentine, pv join mid-column) + core_conns.json')
sys.stderr.write(f'post_v37p: {n} cores pinned, {no} re-oriented, {nm} moved\n')
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
