#!/usr/bin/env python3
"""MU-DIE-S81/IDX (10-19): p4l_mu_lkcol + the 16 regional index readers.  Raw plan = tools/s81_dv/dv_plan.py --layout p4
--p4l --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --mu 1 --idxrd 1 --out <raw>; then the SerDes column rev2
lk_* slots of p4l_lkcol are applied exactly as p4l_mu_lkcol/mk_plan.py does.  usage: mk_plan.py <raw>/plan.json"""
import json, sys
from pathlib import Path
B = Path(__file__).resolve().parent.parent
raw = json.load(open(sys.argv[1]))
lk = {b['name']: b for b in json.load(open(B / 'p4l_lkcol/plan.json'))['blocks'] if b['name'].startswith('lk_')}
n = 0
for i, b in enumerate(raw['blocks']):
    if b['name'] in lk and lk[b['name']] != b:
        raw['blocks'][i] = lk[b['name']]; n += 1
raw['facts']['mu_lkcol'] = f'MU-DIE-S81: {n} lk_* slots from p4l_lkcol rev2 (259.2 x 3596.4)'
(B / 'p4l_mu_idx/plan.json').write_text(json.dumps(raw) + '\n')
print('lk slots replaced', n)
