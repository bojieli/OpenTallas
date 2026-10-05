#!/usr/bin/env python3
"""Audit routed evidence against current sources, without extrapolated Fmax claims.

A result applies only to its explicit top, parameters, corner and constraints.
This is a record inventory, not elaborated module or all-target coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZERO_METRICS = (
    'setup_violations', 'hold_violations', 'max_slew_violations',
    'max_cap_violations', 'max_fanout_violations', 'drc_errors',
    'antenna_violating_nets', 'antenna_violating_pins',
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_record(path: Path, root: Path) -> dict | None:
    record = json.loads(path.read_text())
    design = record.get('design', {})
    route = record.get('place_and_route')
    if not isinstance(route, dict) or not design.get('top'):
        return None
    issues = []
    sources = design.get('sources', [])
    if not sources:
        issues.append('missing_source_manifest')
    for entry in sources:
        source = root / entry.get('path', '')
        if not source.is_file():
            issues.append('missing_source:' + str(entry.get('path')))
        elif not entry.get('sha256'):
            issues.append('missing_source_hash:' + entry['path'])
        elif digest(source) != entry['sha256']:
            issues.append('changed_source:' + entry['path'])
    # Snapshot sources must also match an active RTL file. Matching a retained
    # snapshot alone says nothing about the implementation currently instantiated.
    snapshot_sources = [e['path'] for e in sources if not e.get('path', '').startswith('rtl/')]
    if snapshot_sources:
        issues.append('snapshot_or_external_sources_require_active_binding')
    artifacts = route.get('artifacts', {})
    artifact_issues = []
    for required in ('6_final.v', '6_finish.rpt', 'config.mk', 'constraint.sdc'):
        item = artifacts.get(required, {})
        artifact = root / route.get('artifact_dir', '') / required
        if not item.get('retained') or not item.get('sha256') or not artifact.is_file():
            artifact_issues.append('missing:' + required)
        elif digest(artifact) != item['sha256']:
            artifact_issues.append('hash_mismatch:' + required)
    metrics = route.get('metrics', {})
    missing = [k for k in (*ZERO_METRICS, 'setup_wns_ns', 'hold_wns_ns')
               if not isinstance(metrics.get(k), (int, float)) or not math.isfinite(metrics[k])]
    violations = [k for k in ZERO_METRICS if isinstance(metrics.get(k), (int, float)) and metrics[k] != 0]
    violations += [k for k in ('setup_wns_ns', 'hold_wns_ns')
                   if isinstance(metrics.get(k), (int, float)) and metrics[k] < 0]
    period = record.get('target_clock_period_ns')
    valid_period = isinstance(period, (int, float)) and math.isfinite(period) and period > 0
    routed_pass = not missing and not violations and valid_period
    current_verified = routed_pass and not issues and not artifact_issues
    return {
        'record': str(path.relative_to(root)), 'sha256': digest(path),
        'view': record.get('view', {}).get('name'), 'top': design['top'],
        'parameters': design.get('parameters', {}),
        'corner': record.get('corner', {}).get('name'),
        'tested_period_ns': period,
        'verified_current_frequency_mhz': 1000 / period if current_verified else None,
        'routed_checks_pass': routed_pass, 'current_source_and_artifact_verified': current_verified,
        'source_issues': issues, 'artifact_issues': artifact_issues,
        'missing_metrics': missing, 'violations': violations,
        'setup_wns_ns': metrics.get('setup_wns_ns'),
        'hold_wns_ns': metrics.get('hold_wns_ns'),
        'standard_cell_area_um2': metrics.get('standard_cell_area_um2'),
        'false_path_from_ports': design.get('false_path_from_ports', []),
        'signal_integrity_constraints': route.get('signal_integrity_constraints'),
        'overall_record_status': record.get('acceptance', {}).get('status', record.get('status')),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/physical_abi3/current_evidence_audit.json')
    args = parser.parse_args()
    rows = []
    for path in sorted((ROOT / 'results/physical_abi3').rglob('*.json')):
        if path.resolve() == args.output.resolve():
            continue
        row = inspect_record(path, ROOT)
        if row:
            rows.append(row)
    views = {}
    for view in sorted({r['view'] for r in rows if r['view']}):
        selected = [r for r in rows if r['view'] == view]
        views[view] = {
            'routed_records': len(selected),
            'routed_checks_pass': sum(r['routed_checks_pass'] for r in selected),
            'current_source_and_artifact_verified': sum(r['current_source_and_artifact_verified'] for r in selected),
            'source_issues': sum(bool(r['source_issues']) for r in selected),
            'artifact_issues': sum(bool(r['artifact_issues']) for r in selected),
            'missing_metrics': sum(bool(r['missing_metrics']) for r in selected),
            'violation_counts': dict(Counter(k for r in selected for k in r['violations'])),
        }
    report = {'schema': 'opentallas.current_physical_evidence.v1',
              'scope': 'Recorded routed tops/configurations only. No inferred child-module coverage, target completeness, multi-corner signoff, silicon or whole-chip frequency claim. Source files may include dirty changes. Snapshot/external sources require explicit active binding.',
              'producer': {'path': 'tools/audit_current_physical_evidence.py', 'sha256': digest(Path(__file__))},
              'frequency_basis': '1000 / tested period ns only after routed checks, current source hashes and required retained artifacts pass; never slack-extrapolated Fmax.',
              'views': views, 'records': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(views, indent=2))


if __name__ == '__main__':
    main()
