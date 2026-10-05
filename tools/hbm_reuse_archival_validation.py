#!/usr/bin/env python3
"""Validate a source-bound archived proposal without relocating its runner.

The original tests and campaign inputs remain unchanged. Only this test adapter
selects the record's original source root for archival replay; execution continues
to reject relocation. No compiler, simulation, or service is launched.
"""
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import hbm_ds_frontend_reuse as inventory
import prepare_hbm_rf_connected_reuse_r5 as preparation
import test_hbm_rf_connected_reuse_r5 as checks


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stored = json.loads((preparation.OUT / preparation.PROPOSAL).read_text())
    manifest = json.loads(preparation.MANIFEST.read_text())
    original_root = Path(manifest['source_root'])
    for path, expected in {**stored['source_sha256'], **stored['gate_tool_sha256']}.items():
        if digest(preparation.ROOT / path) != expected:
            raise ValueError('current-tree source/tool differs from archived proposal: ' + path)
    raw = subprocess.check_output(
        ['/usr/bin/python3', '-c',
         'import json,sys;sys.path.insert(0,"tools");'
         'import prepare_hbm_rf_connected_reuse_r5 as p;'
         'print(json.dumps(p.prepare(),sort_keys=True))'],
        cwd=original_root, timeout=30)
    replay = json.loads(raw)
    if replay != stored:
        raise ValueError('original source-bound proposal replay differs')
    original_verify = inventory.verify_inputs

    def verify_recorded_inputs(record):
        if Path(record['source_root']) != original_root:
            return original_verify(record)
        for path, expected in record['source_sha256'].items():
            if digest(preparation.ROOT / path) != expected:
                raise ValueError('current-tree source differs: ' + path)
        with patch.object(inventory, 'ROOT', original_root):
            return original_verify(record)

    if preparation.ROOT != original_root:
        try:
            original_verify(manifest)
        except ValueError as error:
            if str(error) != 'source root changed':
                raise
        else:
            raise ValueError('runner relocation guard failed')
    with patch.object(inventory, 'verify_inputs', side_effect=verify_recorded_inputs), \
         patch.object(preparation, 'prepare', return_value=replay):
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(checks.Reuse))
    if not result.wasSuccessful():
        raise SystemExit(1)
    print('PASS archival source/tool/proposal replay and unchanged16controls; '
          'relocated runner remains rejected; no RTL execution credit')


if __name__ == '__main__':
    main()
