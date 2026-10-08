#!/usr/bin/env python3
"""Harvest completed HBM die cases without interpreting process success as closure.

The OT_STA_VIEW values are ns, with setup uncertainty 210 ps in this flow.
NA means that the filtered query returned no path; it is not a passing slack.
This records preliminary case evidence, not extracted die sign-off.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def parse_log(text):
    result = {}
    match = re.search(r'OT_LEGAL instances=(\d+) overlaps=(\d+) outside=(\d+)', text)
    if match:
        result['placement'] = dict(zip(('instances', 'overlaps', 'outside'), map(int, match.groups())))
    match = re.search(r'OT_MACRO_TRACK_ASSERT (PASS|FAIL)\b', text)
    if match:
        result['on_track'] = match[1]
    match = re.search(r'OT_PA (DONE|FAIL)\b', text)
    if match:
        result['pin_access'] = match[1]
    result['pin_access_errors'] = re.findall(r'^\[ERROR DRT-0073\] (.+)$', text, re.M)
    totals = re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s+(\d+) /\s+(\d+)', text, re.M)
    if totals:
        capacity, demand, usage, h, v, overflow = totals[-1]
        result['global_route'] = dict(capacity=int(capacity), demand=int(demand), usage_percent=float(usage),
                                      overflow_h=int(h), overflow_v=int(v), overflow=int(overflow))
    views = []
    for name, instances, setup, hold in re.findall(
            r'^OT_STA_VIEW (\S+) insts=(\d+) setup_u210=(\S+) hold=(\S+)$', text, re.M):
        views.append(dict(master=name, instances=int(instances),
                          setup_u210_ps=None if setup == 'NA' else round(float(setup) * 1000, 6),
                          hold_ps=None if hold == 'NA' else round(float(hold) * 1000, 6)))
    if views:
        result['sta'] = dict(
            setup_uncertainty_ps=210, hold_uncertainty_ps=25,
            extraction='placement estimate; not post-detailed-route extraction',
            path_filter='paths starting or ending at sm* instances excluded by source flow',
            views=views, reported_views=len(views),
            views_without_numeric_result=sum(v['setup_u210_ps'] is None and v['hold_ps'] is None for v in views),
            unavailable_result_meaning='no path returned by the filtered query; not a timing pass')
    match = re.search(r'OT_STA_DONE timed_insts=(\d+)', text)
    if match:
        result['sta_declared_timed_instances'] = int(match[1])
    return result


def harvest(root, origin):
    commit = (root / 'SOURCE_COMMIT').read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('SOURCE_COMMIT must identify a full commit')
    result = dict(schema='opentallas.hbm_die_round_evidence.v1', source_commit=commit, origin=origin,
                  round=root.name, scope='completed cases only; preliminary die evidence',
                  signoff_claim=False, cases={})
    for case in sorted(root.iterdir()):
        if not case.is_dir() or not (case / 'run.log.exit').exists():
            continue
        log = case / 'run.log'
        record = parse_log(log.read_text(errors='replace'))
        record['process_exit_code'] = int((case / 'run.log.exit').read_text().strip())
        record['evidence'] = {}
        for name in ('run.log', 'run.log.exit', 'manifest.json'):
            path = case / name
            record['evidence'][name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                           path=f'{case.name}/{name}')
        manifest = json.loads((case / 'manifest.json').read_text())
        record['bundle_k'] = manifest.get('bundle_k')
        record['congestion_iterations'] = manifest.get('congestion_iterations')
        result['cases'][case.name] = record
    if not result['cases']:
        raise ValueError('no completed cases to harvest')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round', required=True, type=Path)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(harvest(args.round, args.origin), indent=2) + '\n')
