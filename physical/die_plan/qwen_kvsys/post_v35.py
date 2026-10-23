#!/usr/bin/env python3
"""KV-P5 10-23: KV die plan v3.5 = v3.4 + COORD R8 (2) source-side replica groups for the hub_Wi broadcasts.

kvs_emb.px_tok / kvs_emb.px_tep / host.boot_go leave hub_Wi (west of the centre band) and reach the W quadrants through
hub_Wo (2 cycles) but the E quadrants through hub_Eo (8 cycles); as built every pc row got them at one depth (BINDER2
bus_groups replica sets).  Padding at the sink landing would give the replicated pc types different pads per
quadrant (R8 type conflict, PLAN-TOOL3 r8.py: kv3_pc / _v1 / _v2 / _v3 pads [0, 6]).  Here the delay goes on the
FIRST HOP instead: one latency group (kind replica) per broadcast over its hub_Wi -> hub_Wo and hub_Wi -> hub_Eo lanes,
so gen.py latency pads the W first hop to the E one at the hub_Wo in bus (a singleton type) and every row of both
halves sees the same depth.  boot_go's hub_Wi -> sys_c lane is a different sink and stays out of the group.

    python3 post_v35.py die_plan_v34.json > die_plan.json
"""
import json
import sys

GROUPS = [('r8_px_tok', 'kvs_emb.px_tok'), ('r8_px_tep', 'kvs_emb.px_tep'), ('r8_boot_go', 'host.boot_go')]
p = json.load(open(sys.argv[1]))
ports = {x['id']: x for x in p['ports']}
lg = []
for name, src in GROUPS:
    first = []
    for ln in p['lanes']:
        if ln.get('note') != f'tap_tree {src}':
            continue
        a, b = ports[ln['ports'][0]], ports[ln['ports'][-1]]
        if a['src']['part'] == 'hub_Wi' and b['dst']['part'] in ('hub_Wo', 'hub_Eo'):
            first.append(ln['id'])
    assert len(first) == 2, (name, first)
    lg.append(dict(name=name, kind='replica', lanes=sorted(first), source=src,
                   note='KV-P5 v3.5: W/E first hops of a hub_Wi broadcast padded to one depth (R8 (2), source side)'))
p['latency_groups'] = p.get('latency_groups', []) + lg
p['note'] = p.get('note', '') + ' | v3.5 (KV-P5 10-23): R8 source-side replica groups ' + ', '.join(g['name'] for g in lg)
json.dump(p, sys.stdout, indent=1)
sys.stdout.write('\n')
