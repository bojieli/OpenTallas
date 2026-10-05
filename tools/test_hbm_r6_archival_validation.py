#!/usr/bin/env python3
"""Negative controls for archival pins/guard; no campaign execution."""
import tempfile
import types
import unittest
from pathlib import Path
import hbm_r6_archival_validation as A

class ArchivalControls(unittest.TestCase):
    def test_changed_pinned_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'source';path.write_bytes(b'pinned')
            pins={'source':A.inventory.digest(path)}
            A.check_pins(root,pins)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'archival source/tool/model mismatch'):
                A.check_pins(root,pins)
    def test_missing_pinned_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                A.check_pins(Path(directory),{'missing':'0'*64})
    def test_guard_bypass_refused(self):
        module=types.SimpleNamespace(ROOT=Path('/tmp/relocated'),verify_inputs=lambda record:None)
        with self.assertRaisesRegex(ValueError,'production ROOT relocation guard failed'):
            A.assert_root_guard(module,{'source_root':'/tmp/original'})
    def test_unrelated_failure_not_mistaken_for_guard(self):
        def wrong(record):raise ValueError('tool changed')
        module=types.SimpleNamespace(ROOT=Path('/tmp/relocated'),verify_inputs=wrong)
        with self.assertRaisesRegex(ValueError,'tool changed'):
            A.assert_root_guard(module,{'source_root':'/tmp/original'})
    def test_requires_archival_location(self):
        module=types.SimpleNamespace(ROOT=Path('/tmp/original'))
        with self.assertRaisesRegex(ValueError,'outside recorded worker root'):
            A.assert_root_guard(module,{'source_root':'/tmp/original'})

if __name__=='__main__':unittest.main()
