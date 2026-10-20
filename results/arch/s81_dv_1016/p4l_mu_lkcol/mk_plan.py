#!/usr/bin/env python3
"""MU-DIE-S81 (10-19): the multi-user release die plan = p4l_mu (dv_plan --mu 1) with the SerDes column slot rev2
of p4l_lkcol (8 lk_* slots 259.2 x 3596.4, coordinator 10-19 02:00; link attach points unchanged).
MU-DIE-S81/PATH (10-19): p4l_mu is generated with --pathfix:
  dv_plan.py --out results/arch/s81_dv_1016/p4l_mu --layout p4 --tier-w 276 --lanes 4 --p4l --p4h-drop 6 --frame-w 1436.832 \
             --revision dv-p4l-mu1-pathfix --mu 1 --pathfix
Only the lk_* block geometry is taken from p4l_lkcol; every other block / link is p4l_mu's."""
import json
from pathlib import Path
B = Path(__file__).resolve().parent.parent
base = json.load(open(B / 'p4l/plan.json'))
lk = json.load(open(B / 'p4l_lkcol/plan.json'))
mu = json.load(open(B / 'p4l_mu/plan.json'))
assert [b['name'] for b in base['blocks']] == [b['name'] for b in lk['blocks']] == [b['name'] for b in mu['blocks']]
n = 0
for i, (b0, b1) in enumerate(zip(base['blocks'], lk['blocks'])):
    if b0 != b1:
        assert b1['name'].startswith('lk_'), b1['name']
        assert mu['blocks'][i] == b0, b1['name']
        mu['blocks'][i] = b1
        n += 1
assert base['links'] == lk['links']
mu['facts']['mu_lkcol'] = f'MU-DIE-S81: {n} lk_* slots from p4l_lkcol rev2 (259.2 x 3596.4)'
(B / 'p4l_mu_lkcol/plan.json').write_text(json.dumps(mu) + '\n')
print('lk slots replaced', n)
