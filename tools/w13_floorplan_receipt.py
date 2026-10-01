#!/usr/bin/env python3
"""Read-only W13 floorplan provenance and SM memory admission; never starts jobs."""
import argparse
import hashlib
import json
from pathlib import Path

CHIP = Path('results/physical_abi3/asap7/chip')
SMS = {'qwen': 'ot_gpu_sm_q', 'v41': 'ot_gpu_sm_v'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admission(available_kib, lease_floor_gib, modeled_peak_gib):
    required = max(lease_floor_gib, modeled_peak_gib)
    return {'passed': available_kib >= required * 1048576,
            'available_kib': available_kib, 'lease_floor_gib': lease_floor_gib,
            'modeled_peak_gib': modeled_peak_gib, 'required_gib': required,
            'scope': 'Fresh MemAvailable prerequisite only; existing lease and queue ownership still required.'}


def receipt(root, floorplan_dir):
    from w13_column_corner_gate import check
    issues, records = [], {}
    for model, block in SMS.items():
        fp = floorplan_dir / (model + '_hbm_die.json')
        record_path = root / CHIP / 'blocks' / (block + '.json')
        if not fp.is_file() or not record_path.is_file():
            issues.append(block + ':missing_floorplan_or_block_record')
            continue
        floorplan, record = json.loads(fp.read_text()), json.loads(record_path.read_text())
        expected = CHIP / 'abstracts' / block / (block + '.lef')
        lef = root / expected
        abstract = record.get('abstract', {}).get('lef', {})
        if not lef.is_file() or abstract.get('path') != str(expected) or abstract.get('sha256') != digest(lef):
            issues.append(block + ':actual_lef_pin_mismatch')
            continue
        if floorplan.get('sm_tile', {}).get('abstract_lef') != str(expected):
            issues.append(block + ':floorplan_did_not_use_actual_lef')
        gate = check(root, block, [s['path'] for s in record.get('sources', [])])
        if not gate['passed'] or record.get('closed_against_budget') is not True:
            issues.append(block + ':sm_context_gate_failed')
        records[model] = {'block': block, 'floorplan': str(fp), 'floorplan_sha256': digest(fp),
                          'actual_sm_lef': str(expected), 'actual_sm_lef_sha256': digest(lef),
                          'block_record_sha256': digest(record_path), 'corner_gate': gate}
    return {'schema': 'opentallas.w13.floorplan_companion.v1', 'passed': not issues,
            'issues': issues, 'models': records,
            'claim_boundary': 'Companion pins for existing actual SM LEFs and qualified records; no new route, simulation, or floorplan claim.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--floorplan-dir', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--available-kib', type=int, help='Fresh worker MemAvailable in KiB; mandatory for admission')
    p.add_argument('--lease-floor-gib', type=float, default=55)
    p.add_argument('--admission-only', action='store_true')
    args = p.parse_args()
    from chip_assembly.floorplans import BLOCKS
    peak = max(BLOCKS[b].peak_gb for b in SMS.values())
    if args.available_kib is None or args.available_kib < 0 or args.lease_floor_gib <= 0:
        p.error('Supply fresh nonnegative --available-kib and positive --lease-floor-gib')
    memory = admission(args.available_kib, args.lease_floor_gib, peak)
    result = {'schema': 'opentallas.w13.sm_admission.v1', 'passed': memory['passed']} if args.admission_only else receipt(args.root.resolve(), args.floorplan_dir or args.root / 'results/floorplan/hbm_gpu')
    result['memory_admission'] = memory
    result['passed'] = result['passed'] and memory['passed']
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
