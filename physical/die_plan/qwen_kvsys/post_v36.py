#!/usr/bin/env python3
"""KV-P5 10-23: KV die plan v3.6 = v3.5 + kv3_hg_v1 split by row (COORD 17:4x R8: split or equalise).

The hg rows 1-5 forward kvs_attn.acal_Q (and the kg start) row to row, 2 cycles a hop, while as built every row got them at
one depth (replica set).  R8 landing pads restore the as-built equality at the sink, which needs pad 2 (row 2) .. 8 (row 5)
-- a per-ROW value, identical in the four quadrants.  A type is hardened once, so kv3_hg_v1 (rows 1-5 x 4 quadrants) splits
into kv3_hg_v1_r1 .. kv3_hg_v1_r5 (one type per row, 4 instances each); every other property stays.  Structural follow-up
(G3 cost): an ID-selected landing delay would merge them back into one type.

    python3 post_v36.py die_plan_v35.json > die_plan.json
"""
import copy
import json
import re
import sys

p = json.load(open(sys.argv[1]))
T = p['partition_types']
base = T.pop('kv3_hg_v1')
ROW = re.compile(r'_(\d+)$')
rows = sorted({int(ROW.search(x['name']).group(1)) for x in p['partitions'] if x['type'] == 'kv3_hg_v1'})
for r in rows:
    t = copy.deepcopy(base)
    t['module'] = f"{base['module']}_r{r}"
    t['note'] = (base.get('note', '') + f' | v3.6 (KV-P5 10-23): row {r} of the former kv3_hg_v1 (R8 row landing pads)').strip(' |')
    T[f'kv3_hg_v1_r{r}'] = t
for x in p['partitions']:
    if x['type'] == 'kv3_hg_v1':
        x['type'] = 'kv3_hg_v1_r%d' % int(ROW.search(x['name']).group(1))
p['note'] = p.get('note', '') + ' | v3.6 (KV-P5 10-23): kv3_hg_v1 split by row r1-r5 (R8)'
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
