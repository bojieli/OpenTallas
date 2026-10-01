#!/usr/bin/env python3
"""Inventory physical JSON records without upgrading their engineering verdicts.

ORFS --orfs-corner is the P&R corner; the top-level corner describes the
standalone STA view and can still say TT for a WC P&R run. Missing sign-off
fields are unknown, never a pass. This tool does not poll or restart jobs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def option(argv, name):
    try:
        return argv[argv.index(name) + 1]
    except (ValueError, IndexError):
        return None


def finite(value):
    return isinstance(value, (float, int)) and math.isfinite(value)


def inventory(path, root):
    try:
        record = json.loads(path.read_text())
        if not isinstance(record, dict):
            raise ValueError('record is not an object')
    except (OSError, ValueError) as error:
        return {'path': str(path), 'status': 'unreadable', 'error': str(error),
                'signoff_proven': False}
    argv = record.get('runner', {}).get('argv', [])
    pnr = record.get('place_and_route', {}) or {}
    metrics = pnr.get('metrics', {}) or {}
    design = record.get('design', {}) or {}
    checks = record.get('acceptance', {}).get('checks', [])
    check = next((c for c in checks if c.get('stage') == 'place_and_route'), {})
    constraints = pnr.get('signal_integrity_constraints', {}) or {}
    corner = option(argv, '--orfs-corner')
    hold_corners = constraints.get('hold_corners')
    if hold_corners is None:
        raw = option(argv, '--hold-corners')
        hold_corners = raw.split(',') if raw else []
    pins = []
    for source in design.get('sources', []):
        relative = source.get('path')
        expected = source.get('sha256')
        local = root / relative if relative else None
        actual = hashlib.sha256(local.read_bytes()).hexdigest() if local and local.is_file() else None
        pins.append({'path': relative, 'record_sha256': expected,
                     'worktree_sha256': actual,
                     'current': bool(expected and actual == expected)})
    currency = bool(pins) and all(p['current'] for p in pins)
    period = design.get('clock_period_ns', record.get('target_clock_period_ns'))
    setup_uncertainty = design.get('clock_uncertainty_ns')
    hold_uncertainty = design.get('clock_uncertainty_hold_ns')
    setup = check.get('setup_wns_ns', metrics.get('setup_wns_ns'))
    hold = check.get('hold_wns_ns', metrics.get('hold_wns_ns'))
    missing = []
    if corner != 'WC':
        missing.append('SS/WC P&R corner not demonstrated')
    if 'BC' not in hold_corners:
        missing.append('FF/BC hold corner not demonstrated')
    if not finite(period) or period > 0.833:
        missing.append('0.833 ns or faster clock not demonstrated')
    if not finite(setup_uncertainty) or setup_uncertainty < 0.060:
        missing.append('60 ps setup uncertainty not demonstrated')
    if not finite(hold_uncertainty) or hold_uncertainty < 0.025:
        missing.append('25 ps hold uncertainty not demonstrated')
    if not record.get('flow_completed') or record.get('status') != 'pass' or check.get('met') is not True:
        missing.append('completed passing P&R verdict absent')
    for field in ('drc_errors', 'antenna_violating_nets', 'antenna_violating_pins',
                  'setup_violations', 'hold_violations', 'max_slew_violations',
                  'max_cap_violations', 'max_fanout_violations'):
        if check.get(field) != 0:
            missing.append(field + ' not proven zero')
    for field, value in [('setup_wns_ns', setup), ('hold_wns_ns', hold)]:
        if not finite(value) or value < 0:
            missing.append(field + ' not proven nonnegative')
    if not currency:
        missing.append('all RTL/source hashes not current')
    return {'path': str(path), 'status': record.get('status'),
            'flow_completed': record.get('flow_completed'),
            'completed_at': record.get('completed_at'), 'error': record.get('error'),
            'acceptance': record.get('acceptance'),
            'clock_period_ns': period, 'setup_uncertainty_ns': setup_uncertainty,
            'hold_uncertainty_ns': hold_uncertainty,
            'standalone_sta_corner': record.get('corner', {}).get('name'),
            'pnr_orfs_corner': corner, 'hold_corners': hold_corners,
            'setup_wns_ns': setup, 'hold_wns_ns': hold,
            'drc_errors': check.get('drc_errors'),
            'git_commit': record.get('git', {}).get('commit'),
            'sources_current': currency, 'sources': pins,
            'signoff_proven': not missing, 'signoff_missing': missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', type=Path)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    paths = sorted(p for p in args.records.iterdir() if p.is_file()) if args.records.is_dir() else [args.records]
    print(json.dumps({'schema': 'opentallas.w10.campaign_inventory.v1',
                      'source_root': str(args.source_root.resolve()),
                      'records': [inventory(p, args.source_root) for p in paths]}, indent=2))


if __name__ == '__main__':
    main()
