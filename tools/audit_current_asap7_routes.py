"""Index source-current final routes without inferring hierarchy or clock closure.

A record is eligible only with current source hashes, verified retained artifacts,
a passing extracted acceptance check and a finite tested period. Rows remain
separate by parameters; slack-derived Fmax is deliberately not used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('1_2_yosys.v', '6_final.v', '6_finish.rpt', 'constraint.sdc',
            'config.mk', 'metadata.json', '5_route_drc.rpt')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(record: dict, root: Path) -> dict:
    design = record.get('design', {})
    route = record.get('place_and_route', {})
    reasons = []
    sources = design.get('sources', [])
    if not sources:
        reasons.append('missing source inventory')
    for source in sources:
        path = root / source.get('path', '')
        if not path.is_file() or digest(path) != source.get('sha256'):
            reasons.append('source mismatch: ' + source.get('path', ''))
        elif not source.get('path', '').startswith('rtl/'):
            reasons.append('experimental source: ' + source.get('path', ''))
    period = design.get('clock_period_ns')
    if not isinstance(period, (int, float)) or not math.isfinite(period) or period <= 0:
        reasons.append('missing finite positive tested period')
    checks = record.get('acceptance', {}).get('checks', [])
    extracted = [c for c in checks if c.get('stage') == 'place_and_route']
    if record.get('acceptance', {}).get('status') != 'pass' or len(extracted) != 1:
        reasons.append('no passing extracted acceptance')
    else:
        check = extracted[0]
        for key in ('setup_violations', 'hold_violations', 'drc_errors',
                    'antenna_violating_nets', 'antenna_violating_pins',
                    'max_slew_violations', 'max_cap_violations', 'max_fanout_violations'):
            if check.get(key) != 0:
                reasons.append('nonzero or missing ' + key)
        for key in ('setup_wns_ns', 'hold_wns_ns'):
            value = check.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                reasons.append('invalid ' + key)
    artifacts = route.get('artifacts', {})
    for name in REQUIRED:
        info = artifacts.get(name, {})
        path = root / route.get('artifact_dir', '') / name
        if not info.get('retained') or not path.is_file() or digest(path) != info.get('sha256'):
            reasons.append('unverified artifact: ' + name)
    return dict(top=design.get('top', design.get('block')),
                parameters=design.get('parameters', {}),
                tested_period_ns=period, corner=record.get('corner', {}).get('name'),
                eligible=not reasons, exclusions=reasons,
                area_um2=design.get('area_um2'), sources=sources)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for path in sorted((ROOT/'results/physical_abi3/asap7').rglob('*.json')):
        if '_artifacts' in str(path) or path.resolve() == args.output.resolve():
            continue
        try:
            record = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(record, dict) or not isinstance(record.get('place_and_route'), dict):
            continue
        row = audit(record, ROOT)
        row.update(record=str(path.relative_to(ROOT)), record_sha256=digest(path))
        rows.append(row)
    result = dict(schema='opentallas.current_asap7_routes.v1',
                  scope='Recorded configurations only; current workspace source equality and retained evidence audit. No elaborated hierarchy coverage, multi-corner signoff, energy or whole-chip clock claim.',
                  producer='tools/audit_current_asap7_routes.py', producer_sha256=digest(Path(__file__)),
                  eligible_count=sum(r['eligible'] for r in rows), records=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('Eligible current-source routes:', result['eligible_count'], 'of', len(rows))
    for row in rows:
        if row['eligible']:
            print(row['top'], row['parameters'], row['tested_period_ns'], row['record'])


if __name__ == '__main__':
    main()
