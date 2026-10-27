#!/usr/bin/env python3
"""Collect an actual completed two-net canonical PG coupon without rerunning it."""
import argparse
import csv
import json
from pathlib import Path
import re

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('kit', type=Path)
ap.add_argument('--out', type=Path)
a = ap.parse_args()
m = json.loads((a.kit/'irwin.json').read_text())
log = (a.kit/'psm/psm.log').read_text()
errors = []
if not re.search(r'^EXIT 0$', log, re.M):
    errors.append('missing terminal EXIT 0')
for net in ('VDD', 'VSS'):
    for tag in ('OT_PG_CHECK_OK', 'OT_PSM_OK'):
        if not re.search(rf'^{tag} {net}$', log, re.M):
            errors.append(f'missing {tag} {net}')
if re.search(r'OT_PG_CHECK_FAIL|OT_PSM_FAIL|\[ERROR', log):
    errors.append('explicit PG/solver error in log')
if not re.search(r'^OT_BUMPS .*pad_fallback 0\b', log, re.M):
    errors.append('missing actual finite pad-source geometry / fallback0')
values = {}
for net in ('VDD', 'VSS'):
    rows = list(csv.DictReader((a.kit/f'psm/ir_{net}.csv').open()))
    values[net] = {r['Instance']: r for r in rows}
    if len(rows) != len(values[net]) or len(rows) != m['load_blocks']:
        errors.append(f'{net}: expected one supply terminal per load instance')
if values['VDD'].keys() != values['VSS'].keys():
    errors.append('VDD/VSS load sets differ')
if errors:
    raise SystemExit('; '.join(errors))
samples = []
for name, r in values['VDD'].items():
    s = values['VSS'][name]
    vd = (.7-float(r['Voltage']))*1000
    vs = float(s['Voltage'])*1000
    samples.append(dict(instance=name, vdd_drop_mv=vd, vss_bounce_mv=vs,
                        sum_mv=vd+vs,
                        global_vdd_xy_um=[float(r['X location'])+m['window_um'][0],
                                          float(r['Y location'])+m['window_um'][1]]))
worst = max(samples, key=lambda s:s['sum_mv'])
total = worst['sum_mv'] + m['below_m7_mv']
r = dict(verdict='PASS' if total <= m['ir_budget_mv'] else 'FAIL',
         review='UNCHECKED: independent NUMBER-CHECK required before owner gate claim',
         kit=str(a.kit.resolve()), grid=m['grid'], matched_loads=len(samples),
         power_w=m['power_w'], window_um=m['window_um'], bump_pad_um=m['bump_pad_um'],
         bumps=m['bumps'], co_located_worst=worst, above_m7_mv=worst['sum_mv'],
         below_m7_mv=m['below_m7_mv'], total_mv=total, budget_mv=m['ir_budget_mv'],
         below_m7_basis=m['below_m7_basis'],
         vdd_separate_worst_mv=max(s['vdd_drop_mv'] for s in samples),
         vss_separate_worst_mv=max(s['vss_bounce_mv'] for s in samples),
         co_location='same physical43um load instance, its distinct VDD/VSS PG terminals',
         no_plan_adoption=True)
print(json.dumps(r, indent=2))
if a.out:
    with a.out.open('x') as f:
        f.write(json.dumps(r, indent=2)+'\n')
raise SystemExit(int(r['verdict'] != 'PASS'))
