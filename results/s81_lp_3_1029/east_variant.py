#!/usr/bin/env python3
"""S81-LP-3 (2026-10-29, COORD ruling (b)): east LP lane kit = copy of the chosen west variant under the east module
name dsfd_coll_lane_e_safe8_ntf (RTL wrapper body identical to the w wrapper: same ot_s81ph_coll_lane_safe4 instance u,
same params), LEC against the east RTL (run_kit lec on the e top).  Geometry, macros, plan pins, LEF and the centre
clock-entry slice are the west variant's, byte for byte except the module / kit names.  Orientation in the parent
(e.g. MX/MY) is the parent's placement choice, not a kit change.
    python3 east_variant.py BC     # results/s81_lp_3_1029/lane/E<V> + recipes.json entry
"""
import json, os, shutil, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
V = sys.argv[1]
L = R / 'results/s81_lp_3_1029/lane'
W, E = 'dsfd_coll_lane_w_safe8_ntf', 'dsfd_coll_lane_e_safe8_ntf'
src, d = L / V, L / ('E' + V)
(d / 'slices').mkdir(parents=True, exist_ok=True)
sp = json.load(open(src / 'spec.json'))
assert sp['top'] == W
sp['top'] = E
sp['name'] = sp['name'].replace('lane_w_', 'lane_e_')
sp['structural_change'] += f' S81-LP-3 east twin of {V} (COORD ruling (b)): module {E}, LEC vs the east RTL.'
(d / 'spec.json').write_text(json.dumps(sp, indent=1) + '\n')
pp = json.load(open(src / 'plan_pins.json'))
assert pp['module'] == W
pp['module'] = E
(d / 'plan_pins.json').write_text(json.dumps(pp, indent=0) + '\n')
lef = (src / 'lane.lef').read_text()
assert lef.count(W) == 2
(d / 'lane.lef').write_text(lef.replace(W, E))
plan = json.load(open(src / 'kit_plan.json'))
(typ, pt), = plan['partition_types'].items()
pt['module'] = E
for c in pt['contents']:
    c['module'] = E
hc = pt['hard_cores'][0]
hc['module'] = E
hc['pins_file'] = os.path.relpath(d / 'plan_pins.json', R / 'physical/die_plan/s81')
hc['lef'] = str((d / 'lane.lef').relative_to(R))
plan['partition_types'] = {typ.replace('lane_w', 'lane_e'): pt}
(d / 'kit_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
sl = json.load(open(src / 'slices' / f'{W}.json'))
sl['type'] = sl['module'] = E
sl['event'] += f' + east_variant.py {V}'
(d / 'slices' / f'{E}.json').write_text(json.dumps(sl, indent=1) + '\n')
recs = json.load(open(L / 'recipes.json'))
r = dict(recs[f'{W}__{V}'])
r.update(ref_tile=str(d.relative_to(R)), plan=str((d / 'kit_plan.json').relative_to(R)), plan_module=E,
         suffix=r['suffix'].replace('lp3', 'lp3e'))
recs[f'{E}__{V}'] = r
(L / 'recipes.json').write_text(json.dumps(recs, indent=1) + '\n')
print('EAST', d.relative_to(R), r['suffix'])
