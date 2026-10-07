"""Fail-closed preparation checks; no simulated physical closure claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import s81_capture_startup_patch as patch


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='capture-startup-test-')
        self.root = Path(self.tmp.name)
        self.base = self.root / 'baseline'
        self.base.mkdir()
        self.plan = json.loads((patch.ROOT / 'results/rtl/s81_ph_20261006/capture/startup_endpoint_model_20261007/one_pin_plan.json').read_text())
        for name in self.plan['original_sha256']:
            (self.base / name).write_text('fixture: ' + name)
            self.plan['original_sha256'][name] = patch.sha(self.base / name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_corner_scripts_and_preserved_constraints(self):
        out = patch.prepare(self.base, self.root / 'candidate', self.plan)
        self.assertEqual((out / '6_final.sdc').read_bytes(), (self.base / '6_final.sdc').read_bytes())
        body = (out / 'patch.tcl').read_text()
        self.assertNotIn('repair_timing', body)
        self.assertNotIn('report_worst_slack', body)
        for corner, check in [('ss', 'max'), ('ff', 'min')]:
            text = (out / f'sta_{corner}.tcl').read_text()
            self.assertIn(f'read_db {out}/6_final.odb', text)
            self.assertIn(f'read_spef {out}/6_final.spef', text)
            self.assertIn('S81_TARGET endpoint=', text)
            self.assertIn('slack_' + check, text)
            self.assertNotIn('insert_buffer', text)
        with self.assertRaises(ValueError):
            patch.prepare(self.base, out, self.plan)

    def test_changed_original_rejected_before_writes(self):
        (self.base / '6_final.spef').write_text('changed')
        with self.assertRaises(ValueError):
            patch.prepare(self.base, self.root / 'candidate', self.plan)
        self.assertFalse((self.root / 'candidate').exists())

    def test_scope_and_logic_negative_controls(self):
        for key, value in [('endpoint', 'payload[0]/D'), ('cells', ['INVx1_ASAP7_75t_R'])]:
            candidate = copy.deepcopy(self.plan)
            candidate['patches'][0][key] = value
            with self.assertRaises(ValueError):
                patch.validate(candidate)
        duplicate = copy.deepcopy(self.plan)
        duplicate['patches'].append(copy.deepcopy(duplicate['patches'][0]))
        with self.assertRaises(ValueError):
            patch.validate(duplicate)


if __name__ == '__main__':
    unittest.main()
