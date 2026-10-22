#!/usr/bin/env python3
"""S81 G4 (L5-G4 10-21): land plan = base p4l3 land plan + rows for the 5th lane pair links (lt/lr_lk_WN2/3), copied from
the sibling s_0N <-> lk_WN0/1 rows (same class/bits/master/E/K; dst renamed).  The die STA re-derives E from the routed
G4 chains like every other row; no other row changes."""
import copy, json, sys
src, out = sys.argv[1:3]
d = json.load(open(src)); rows = {r['link']: r for r in d['links']}
for new, old in (('WN2', 'WN0'), ('WN3', 'WN1')):
    for pre in ('lt', 'lr'):
        n = f'{pre}_lk_{new}'
        assert n not in rows
        r = copy.deepcopy(rows[f'{pre}_lk_{old}']); r['link'] = n
        if r['dst'] == f'lk_{old}':
            r['dst'] = f'lk_{new}'
        r['g4_note'] = f'L5-G4: copied from {pre}_lk_{old} (5th lane pair); E/K re-derived by the die STA'
        d['links'].append(r)
d['g4'] = 'L5-G4 10-21: +4 rows lt/lr_lk_WN2/3 (5th lane pair on s_0N)'
json.dump(d, open(out, 'w'), indent=1)
print('LAND_PLAN_G4', len(d['links']))
