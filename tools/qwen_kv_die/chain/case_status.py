#!/usr/bin/env python3
"""Validate real-case logs even when caught OpenROAD errors leave process exit zero."""
import argparse
import json
import math
from pathlib import Path
import re


def check(log, stage, process_exit=0, case_kind='a'):
    failures = []
    if process_exit:
        failures.append(f'process_exit={process_exit}')
    failures.extend(re.findall(r'^.*(?:\[ERROR\b|^Error:|^OT_.*FAIL\b).*$', log, re.M))
    if stage == 'run.tcl' and str(case_kind).startswith('a'):
        required = [r'^OT_LEGAL instances=\d+ overlaps=0 outside=0$',
                    r'^OT_ASSERT PASS$', r'^OT_PA DONE$']
    elif stage == 'run_pa.tcl':
        required = [r'^OT_PA DONE$', r'^OT_PDN PASS\b',
                    r'^OT_PGCHECK VDD PASS$', r'^OT_PGCHECK VSS PASS$']
    elif stage == 'run_pdn.tcl':
        required = [r'^OT_PDN PASS\b', r'^OT_PGCHECK VDD PASS$', r'^OT_PGCHECK VSS PASS$']
    elif re.fullmatch(r'grt_(tt|ff|ss)\.tcl', stage):
        # A completed clock/SPEF load is insufficient: require real STA output.
        required = []
        for metric in ('tns', 'wns', 'worst slack'):
            # OpenSTA prints 'tns max -1.0' (path type) on current builds, 'tns -1.0' on older ones.
            matches = re.findall(r'^' + metric + r'(?:\s+(?:max|min))?\s+(\S+)\s*$', log, re.M)
            try:
                valid = bool(matches) and all(math.isfinite(float(v)) for v in matches)
            except ValueError:
                valid = False
            if not valid:
                failures.append(f'missing or nonfinite numeric STA metric: {metric}')
    else:
        required = []
    for pattern in required:
        if not re.search(pattern, log, re.M):
            failures.append(f'missing success marker: {pattern}')
    return dict(status='FAIL' if failures else 'PASS', process_exit=process_exit,
                exit_code=process_exit or int(bool(failures)), failures=failures,
                scope='physical flow stage only; no native/full-token qualification')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--stage', required=True)
    p.add_argument('--process-exit', type=int, required=True)
    a = p.parse_args()
    try:
        manifest = a.log.parent/'manifest.json'
        kind = json.loads(manifest.read_text()).get('case', 'a') if manifest.exists() else 'a'
        report = check(a.log.read_text(errors='replace'), Path(a.stage).name, a.process_exit, kind)
    except (OSError, ValueError) as e:
        report = dict(status='FAIL', process_exit=a.process_exit, exit_code=a.process_exit or 1,
                      failures=[str(e)])
    a.log.with_name(a.log.name+'.status.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"OT_CASE_STATUS {report['status']} process_exit={a.process_exit} exit={report['exit_code']}")
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
