#!/usr/bin/env python3
"""Measured block clock insertions -> calibrations.json for budget_sheet.py --calib (CLAUDE BUDGETS, 2026-10-06).

Sources: the closure loop's calibrate records (~/.local/state/closure_loop/jobs/<job>.json "calibration": ck_insertion.py
boundary-register SS/FF mean/min/max after CTS) -- newest job per block wins -- plus --extra JSON entries for measured
values recorded elsewhere (e.g. the Z20c q-element ETM).  Values are inputs to the sheets, never edited by hand here.
"""
import argparse, glob, json, os
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--state', default=os.path.expanduser('~/.local/state/closure_loop/jobs'))
ap.add_argument('--extra', action='append', default=[])
ap.add_argument('--out', required=True)
a = ap.parse_args()
out = {}
for f in sorted(glob.glob(f'{a.state}/*.json'), key=os.path.getmtime):
    j = json.load(open(f))
    c = j.get('calibration')
    if not c or 'env' not in c:
        continue
    e = c['env']
    out[j['spec']['block']] = dict(ss_mean=e['CK_SS_MEAN'], ss_min=e['CK_SS_MIN'], ss_max=e['CK_SS_MAX'],
                                   ff_mean=e['CK_FF_MEAN'], ff_min=e['CK_FF_MIN'], ff_max=e['CK_FF_MAX'],
                                   source=f"closure-loop calibrate {j['name']} ({j.get('host')}:{j.get('run')})")
for x in a.extra:
    for k, v in json.loads(Path(x).read_text()).items():
        out.setdefault(k, v)
Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
print(len(out), sorted(out))
