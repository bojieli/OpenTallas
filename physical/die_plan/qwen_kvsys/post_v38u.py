#!/usr/bin/env python3
"""KVG3-WI 10-24: apply the hub_Wi host-core pins (core_pins_hr.py -> cores/core_patch_v38u.json) to the plan.

Touches ONLY partition_types.kv3_hub_Wi.hard_cores[].{pins_file, orient, note} of the 22 planned qkd_hr_* cores (the
pins come from the real instance members in u_host; glue:* members stay partition glue, see core_pins_hr.py).  The
core connectivity for the G0C core_faces rule is in core_conns.json (kv3_hub_Wi entries, same tool).
usage: post_v38u.py die_plan.json PLAN_DIR > die_plan.json"""
import json
import sys
from pathlib import Path

TN = 'kv3_hub_Wi'
p = json.load(open(sys.argv[1]))
patch = json.load(open(Path(sys.argv[2]) / 'cores' / 'core_patch_v38u.json'))[TN]
n = 0
for hc in p['partition_types'][TN]['hard_cores']:
    pt = patch.get(hc['inst'])
    if pt is None:
        continue
    for k in ('pins_file', 'orient', 'note'):
        hc[k] = pt[k]
    n += 1
assert n == len(patch), (n, len(patch))
print(f'post_v38u: {n} {TN} hard cores pinned', file=sys.stderr)
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
