#!/usr/bin/env python3
"""Prepare, but never execute, the explicitly new PVE1 constraint contract."""
import argparse
import hashlib
import json
from pathlib import Path

SDC_SHA256 = '360040de16ad28c433a94d550c87806ce4cbe3237e9baea0604c0640ef1df044'
SOURCE_COMMIT = 'fb5df1ac4ee6df1011165e32e91aadc29bc702ae'
RTL_INVENTORY_SHA256 = 'ecc8ec8f4f8af06c436caf2ce41c245194622e4adc560aa842c555cc990329f3'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(plan, sdc, source_root):
    if plan['schema'] != 'PVE1_NEW_SOURCE_CONSTRAINT_PLAN_V1':
        raise ValueError('unsupported contract')
    if plan['source_commit'] != SOURCE_COMMIT or digest(sdc) != SDC_SHA256:
        raise ValueError('source or literal constraint identity differs')
    if plan['constraints'] != dict(period_ps=1111, setup_uncertainty_ps=60,
            hold_uncertainty_ps=25, input_delay_ps=0, output_delay_ps=0,
            false_path_from=['rst_n'], output_load_literal=3.898, max_fanout=32):
        raise ValueError('constraint declaration differs')
    if plan['model']['parameters'] != dict(MLAT=5, ALAT=4) or plan['model']['added_cycles'] != 0:
        raise ValueError('RTL latency model differs')
    pins = plan['rtl_pins']
    if len(pins) != 12 or len({p['path'] for p in pins}) != 12:
        raise ValueError('complete unique original RTL inventory required')
    if hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != RTL_INVENTORY_SHA256:
        raise ValueError('original RTL manifest identity differs')
    for pin in pins:
        path = Path(pin['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('source path escapes root')
        if digest(Path(source_root) / path) != pin['sha256']:
            raise ValueError('RTL source identity differs: ' + str(path))
    if plan['historical_sdc_equivalence_claim'] is not False:
        raise ValueError('historical SDC equivalence is unavailable')


def prepare(plan_path, sdc, source_root, destination, *, enable=False):
    if not enable:
        raise ValueError('default off: explicit --enable-new-source-constraints required')
    plan = json.loads(Path(plan_path).read_text())
    validate(plan, sdc, source_root)
    bindings_path = Path(plan_path).parent / 'source_bindings.json'
    if digest(bindings_path) != plan['identity']['source_bindings_sha256']:
        raise ValueError('source binding manifest changed')
    bindings = json.loads(bindings_path.read_text())
    for file in bindings['files'].values():
        if 'text' in file and hashlib.sha256(file['text'].encode()).hexdigest() != file['sha256']:
            raise ValueError('script snapshot hash differs')
    destination = Path(destination)
    # A review bundle cannot replace the live namespace or an existing bundle.
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError('fresh absolute review directory required')
    for forbidden in (Path('/work'), Path('/home/ubuntu/ot-retained/pve1-w11-su2-live-20261003/work')):
        if destination == forbidden or forbidden in destination.parents:
            raise ValueError('live work namespace is forbidden')
    destination.mkdir()
    (destination / 'new_source_constraint.sdc').write_bytes(Path(sdc).read_bytes())
    # Future entrypoint only. No interpreter, subprocess, library, ODB or stage
    # is opened by this preparation tool. The native loader returns early when
    # an existing design is loaded; this makes the new binding explicit without
    # changing the pinned resize source or manufacturing 2_floorplan.sdc.
    (destination / 'new_source_resize_entry.tcl').write_text(
        '# NEW constraint lineage; reviewed terminal ODB and fresh lease required.\n'
        'source $::env(SCRIPTS_DIR)/load.tcl\n'
        'load_design 3_3_place_gp.odb new_source_constraint.sdc\n'
        'source $::env(SCRIPTS_DIR)/resize.tcl\n')
    record = dict(schema='PVE1_NEW_SOURCE_CONSTRAINT_PREPARATION_V1',
        status='PREPARED_FOR_REVIEW_ONLY', execution_performed=False,
        terminal_odb_captured=False, qualification='NOT_RUN',
        historical_sdc_equivalence_claim=False, plan_sha256=digest(plan_path),
        preparer_sha256=digest(__file__), source_commit=SOURCE_COMMIT,
        files={p.name: digest(p) for p in destination.iterdir()})
    (destination / 'preparation.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--sdc', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--prepare-dir', type=Path, required=True)
    parser.add_argument('--enable-new-source-constraints', action='store_true')
    args = parser.parse_args(argv)
    try:
        record = prepare(args.plan, args.sdc, args.source_root, args.prepare_dir,
                         enable=args.enable_new_source_constraints)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, 'REFUSED: ' + str(exc) + '\n')
    print(json.dumps(record, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
