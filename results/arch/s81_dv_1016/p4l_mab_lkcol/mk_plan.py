#!/usr/bin/env python3
"""MU-DIE-S81/MAB (10-19): the copy-A/B rank-die plan = p4l_mab (dv_plan --mu 2: AB pair on s_0S, lk_WS2 / lk_WS3 at the
rev2 3596.4-tall positions of copyb_relay_plan.json if_slot_3596, rt_0S) with the SerDes column slot rev2 of p4l_lkcol
(8 A lk_* slots 259.2 x 3596.4, coordinator 10-19 02:00; link attach points unchanged).  Only the A lk_* block geometry
is taken from p4l_lkcol; every other block / link is p4l_mab's (as p4l_mu_lkcol/mk_plan.py does for p4l_mu)."""
import json
from pathlib import Path
B = Path(__file__).resolve().parent.parent
base = json.load(open(B / 'p4l/plan.json'))
lk = json.load(open(B / 'p4l_lkcol/plan.json'))
mab = json.load(open(B / 'p4l_mab/plan.json'))
nb = len(base['blocks'])
assert [b['name'] for b in base['blocks']] == [b['name'] for b in lk['blocks']] == [b['name'] for b in mab['blocks'][:nb]]
assert [b['name'] for b in mab['blocks'][nb:]] == ['lk_WS2', 'lk_WS3'], [b['name'] for b in mab['blocks'][nb:]]
n = 0
for i, (b0, b1) in enumerate(zip(base['blocks'], lk['blocks'])):
    if b0 != b1:
        assert b1['name'].startswith('lk_'), b1['name']
        assert mab['blocks'][i] == b0, b1['name']
        mab['blocks'][i] = b1
        n += 1
assert base['links'] == lk['links']
bl = mab['blocks']
for i, a in enumerate(bl):          # no block overlaps after the swap (B slots vs grown A slots)
    for b in bl[i + 1:]:
        e = 1e-6                    # abutted frames touch to float precision
        assert not (a['x'] < b['x'] + b['w'] - e and b['x'] < a['x'] + a['w'] - e and a['y'] < b['y'] + b['h'] - e and
                    b['y'] < a['y'] + a['h'] - e), (a['name'], b['name'])
mab['facts']['mu_lkcol'] = f'MU-DIE-S81/MAB: {n} A lk_* slots from p4l_lkcol rev2 (259.2 x 3596.4); B slots lk_WS2 / lk_WS3 rev2 (dv_plan --mu 2)'
(B / 'p4l_mab_lkcol/plan.json').write_text(json.dumps(mab) + '\n')
print('lk slots replaced', n)
