#!/usr/bin/env python3
"""Collect existing item9 route reports; never run synthesis, P&R or STA.

A driver timeout is not a route terminal while its source-bound container is
alive. Intermediate WC min paths are not FF hold qualification. The enclosing
32-caller obligation remains open even when a child closes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def classes(content):
    groups = {}
    seen = set()
    for block in re.split(r'(?=^Startpoint:)', content, flags=re.M):
        start = re.search(r'^Startpoint:\s*(\S+)', block, re.M)
        end = re.search(r'^Endpoint:\s*(\S+)', block, re.M)
        slack = re.search(r'^\s*([-+]?\d+(?:\.\d+)?)\s+slack\s+\((VIOLATED|MET)\)', block, re.M)
        if not (start and end and slack) or slack[2] != 'VIOLATED':
            continue
        path_type = re.search(r'^Path Type:\s*(\S+)', block, re.M)
        path_type = path_type[1] if path_type else 'unspecified'
        identity = (start[1], end[1], path_type)
        if identity in seen:
            continue
        seen.add(identity)
        normal = lambda s: re.sub(r'\[\d+\]', '[*]', s)
        cone = (normal(start[1]), normal(end[1]), path_type)
        ps = float(slack[1])
        if cone not in groups:
            groups[cone] = dict(start_class=cone[0], end_class=cone[1], path_type=path_type,
                                reported_unique_paths=0, worst_ps=ps,
                                example=dict(start=start[1], end=end[1], slack_ps=ps))
        row = groups[cone]
        row['reported_unique_paths'] += 1
        if ps < row['worst_ps']:
            row['worst_ps'] = ps
            row['example'] = dict(start=start[1], end=end[1], slack_ps=ps)
    return sorted(groups.values(), key=lambda row: row['worst_ps'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('route_root', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--container', action='append', default=[])
    p.add_argument('--source-commit', required=True)
    a = p.parse_args()
    assert a.route_root.is_absolute() and a.output.is_absolute()
    assert not a.output.exists(), 'Retain earlier observations and failures'
    a.output.mkdir(parents=True)
    root = a.route_root
    identities = []
    for name in a.container:
        proc = subprocess.run(['docker', 'inspect', name], text=True, capture_output=True)
        if proc.returncode:
            identities.append(dict(requested_id=name, inspect_exit=proc.returncode, identity_unresolved=True))
            continue
        item = json.loads(proc.stdout)[0]
        mounts = item['Mounts']
        matches = any(Path(m['Source']) == root or root in Path(m['Source']).parents for m in mounts)
        identities.append(dict(id=item['Id'], running=item['State']['Running'],
                               pid=item['State']['Pid'], source_bound_to_route_root=matches,
                               mounts=[dict(source=m['Source'], destination=m['Destination']) for m in mounts]))
    useful_live = any(x.get('running') and x.get('source_bound_to_route_root') for x in identities)
    unresolved = any(x.get('identity_unresolved') or not x.get('source_bound_to_route_root', False)
                     for x in identities)
    records = {}
    for name in ('physical.json', 'corner_sta.json', 'result.json'):
        if (root / name).is_file():
            records[name] = json.loads((root / name).read_text())
    report_files = sorted(set(root.glob('work/orfs/reports/asap7/*/base/*.rpt')) |
                          set(root.glob('work/orfs/logs/asap7/*/base/5_1_grt*.log')) |
                          set(root.glob('work/orfs/routed_*.log')) |
                          set(root.glob('*sta_ss.log')) | set(root.glob('*sta_ff.log')) |
                          set(root.glob('corner*.log')))
    reports = []
    for source in report_files:
        # Snapshot once: the live native repair log may append while collecting.
        data = source.read_bytes()
        dest = a.output / source.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        text = data.decode(errors='replace')
        progress = re.findall(r'^\s*(\d+)\s*\|\s*\d+\s*\|.*?\|\s*([-+]?\d+\.\d+)\s*\|\s*([-+]?\d+\.\d+)\s*\|\s*(\S+)', text, re.M)
        corner = 'FF' if re.search(r'(?:_ff|routed_FF)', source.name) else None
        if corner is None and (source.name == '4_cts_final.rpt' or 'grt' in source.name):
            corner = 'WC_INTERMEDIATE_NOT_FINAL_SSFF'
        reports.append(dict(path=str(source), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                            corner=corner, classes=classes(text),
                            class_counts_cover_reported_paths_only=True,
                            latest_native_setup_repair=None if not progress else
                            dict(iteration=int(progress[-1][0]), worst_ps=float(progress[-1][1]),
                                 tns_ps=float(progress[-1][2]), endpoint=progress[-1][3])))
    physical = records.get('physical.json', {})
    corner = records.get('corner_sta.json', {})
    minimum = records.get('result.json', {})
    minimum_corners = minimum.get('routed_corner_reports', [])
    minimum_terminal = (minimum.get('phase') == 'FLOW_TERMINAL' and minimum.get('exit') == 0
                        and {r.get('corner') for r in minimum_corners} == {'SS', 'FF'}
                        and all(r.get('exit') == 0 and r.get('metrics', {}).get('CLOCK_COUNT') == '4'
                                for r in minimum_corners))
    actual_final = bool(physical.get('flow_completed') and corner.get('setup_ss') and corner.get('hold_ff'))
    if useful_live:
        verdict = 'LIVE_ROUTE_NO_FINAL_SSFF_VERDICT'
    elif unresolved or not actual_final:
        if minimum_terminal and not unresolved:
            by_corner = {r['corner']: r['metrics'] for r in minimum_corners}
            ss = float(by_corner['SS']['SETUP'])
            ff = float(by_corner['FF']['HOLD'])
            verdict = ('MIN32_ROUTED_TIMING_PASS_PARENT_OPEN' if ss >= 0 and ff >= 0
                       else 'MIN32_ROUTED_TIMING_FAIL_PARENT_OPEN')
        else:
            verdict = 'NO_VERIFIED_FINAL_SSFF_TERMINAL'
    elif (corner.get('closes_signoff') and physical.get('design', {}).get('closed')
          and not physical.get('design', {}).get('false_path_io')):
        verdict = 'CHILD_ROUTED_SSFF_PASS_PARENT_OPEN'
    else:
        verdict = 'CHILD_ROUTED_SSFF_FAIL_PARENT_OPEN'
    record = dict(owner='Codex/Dirac item9', observed_UTC=datetime.now(timezone.utc).isoformat(),
                  source_commit=a.source_commit, route_root=str(root), containers=identities,
                  verdict=verdict, reports=reports, existing_records=records,
                  SS_setup_ps=corner.get('setup_ss', {}).get('worst_slack_ps'),
                  FF_hold_ps=corner.get('hold_ff', {}).get('worst_slack_ps'),
                  parent_context_qualified=False, caller_loaded_context_obligation_retained=True,
                  adopted=False, no_tool_or_gate_rerun=True, no_live_job_changed=True)
    if minimum_terminal:
        record['SS_setup_ps'] = float(next(r for r in minimum_corners if r['corner'] == 'SS')['metrics']['SETUP'])
        record['FF_hold_ps'] = float(next(r for r in minimum_corners if r['corner'] == 'FF')['metrics']['HOLD'])
        record['minimum_IO_budget_is_not_measured_parent_delay'] = True
    (a.output / 'verdict.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(verdict=verdict, useful_source_bound_live=useful_live,
                          latest_repairs=[r['latest_native_setup_repair'] for r in reports
                                          if r['latest_native_setup_repair']],
                          SS_setup_ps=record['SS_setup_ps'], FF_hold_ps=record['FF_hold_ps'])))


if __name__ == '__main__':
    main()
