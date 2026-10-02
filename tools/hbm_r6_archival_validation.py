#!/usr/bin/env python3
"""Read-only main archival validation of r6; never run a campaign or alter ROOT guards.

All current-tree inputs are checked before an original-root pure prepare replay.
The recorded worker and failed-output paths are explicit external prerequisites.
No compiler, make build, simulation, service or configuration mutation is invoked.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
import hbm_ds_frontend_copy_r6 as inventory
import prepare_hbm_rf_connected_calibration_r6 as preparation
import run_hbm_rf_connected_calibration_r6 as runner
import test_hbm_rf_connected_calibration_r6 as checks

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / 'results/uarch/hbm_connected_cxx_calibration_r6_20261002/runtime_parser_prepared_gate.json'
GO = ROOT / 'results/rtl/hbm_connected_calibration_parent_20261002_r2/GO.json'


def check_pins(root, pins):
    for path, expected in pins.items():
        if inventory.digest(root / path) != expected:
            raise ValueError('archival source/tool/model mismatch: ' + path)


def assert_root_guard(module, manifest):
    """Both r5 and r6 production helpers must continue rejecting relocation."""
    if module.ROOT == Path(manifest['source_root']):
        raise ValueError('archival validator must run outside recorded worker root')
    try:
        module.verify_inputs(manifest)
    except ValueError as error:
        if str(error) != 'source root changed':
            raise
    else:
        raise ValueError('production ROOT relocation guard failed')


def validate_archive(proposal_path=PROPOSAL, go_path=GO):
    stored = json.loads(proposal_path.read_text())
    go = json.loads(go_path.read_text())
    runner.validate_go(go, proposal_path, go['source_commit'])
    manifest_path = ROOT / stored['reuse_inventory_pin']['path']
    if inventory.digest(manifest_path) != stored['reuse_inventory_pin']['sha256']:
        raise ValueError('archival inventory mismatch')
    manifest = json.loads(manifest_path.read_text())
    original_root = Path(manifest['source_root'])
    if stored['execution_source_root'] != str(original_root):
        raise ValueError('proposal/manifest ROOT mismatch')
    pins = {**stored['source_sha256'], **stored['gate_tool_sha256'],
            stored['calibration_model_path']: stored['calibration_model_sha256'],
            stored['reuse_inventory_pin']['path']: stored['reuse_inventory_pin']['sha256']}
    check_pins(ROOT, pins)
    check_pins(original_root, pins)
    # The preserved model explicitly pins the old raw failure and external inputs.
    # derive validates current-tree source/compiler/inventory and those raw files.
    derived = preparation.derive(json.loads(preparation.BASE.read_text()))
    if derived != stored:
        raise ValueError('main preparation derivation differs from admitted proposal')
    assert_root_guard(inventory, manifest)
    assert_root_guard(preparation.B.I, manifest)
    # Do not invoke historical preparers in main: their git history belongs to
    # the recorded worker. Both actual verify_inputs guards above remain intact;
    # main derives pinned r6 data without consulting private source commits.
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=original_root, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=original_root, text=True)
    if head != go['source_commit'] or dirty:
        raise ValueError('recorded worker must remain clean at admitted source commit')
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    code = ('import json,sys;sys.path.insert(0,"tools");'
            'import prepare_hbm_rf_connected_calibration_r6 as p;'
            'print(json.dumps(p.prepare(),sort_keys=True))')
    raw = subprocess.check_output([sys.executable, '-B', '-c', code],
                                  cwd=original_root, env=env, timeout=30)
    if json.loads(raw) != stored:
        raise ValueError('recorded-root pure prepare replay differs')
    # Recheck current and worker bytes after replay; no ROOT/global patches.
    check_pins(ROOT, pins)
    check_pins(original_root, pins)
    return dict(schema='opentallas.H1.r6.archival-validation.v1',
                proposal_sha256=inventory.digest(proposal_path),
                source_commit=head, recorded_source_root=str(original_root),
                current_tree_pins=len(pins), unchanged_ROOT_guards=True,
                both_production_helper_relocations_refused=True,
                exact_original_root_replay=True, launches=0,
                physical_credit=False, token_credit=False)


def main():
    receipt = validate_archive()
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(checks.CalibrationTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    receipt.update(verdict='PASS_ARCHIVAL_REPLAY_AND_16_STATIC_MOCK_CONTROLS',
                   tests_run=result.testsRun)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
