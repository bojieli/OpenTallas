"""KV-GEN8 10-19: OT_KV_PARAM_DIAG autoprofile preserves exact parameters, is never qualified, and strict still refuses."""
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import kv_expand_parameters as P

RTL = 'module leaf #(parameter integer A = 3, parameter integer B = -2) (input wire ck);\nendmodule\n'


class ParamDiag(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        (self.root / 'rtl').mkdir()
        (self.root / 'rtl/leaf.sv').write_text(RTL)
        vd = self.root / 'v/leaf'; vd.mkdir(parents=True)
        for f in ('leaf.lef', 'leaf_tt.lib', 'leaf_ff.lib', 'insertion.json'):
            (vd / f).write_text(f)

    def test_strict_missing_profile_refuses(self):
        with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
            P.preserve(self.root, 'leaf', {}, 'rtl/leaf.sv', 'v/leaf', {}, False)

    def test_diagnostic_flag_alone_needs_a_profile(self):
        with mock.patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '0'}):
            with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
                P.preserve(self.root, 'leaf', {}, 'rtl/leaf.sv', 'v/leaf', {}, True)

    @mock.patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '1'})
    def test_diagnostic_autoprofile_exact_unqualified(self):
        ov = {'A': format(7, '032b')}
        lit, prof = P.preserve(self.root, 'leaf', ov, 'rtl/leaf.sv', 'v/leaf', {}, True)
        self.assertEqual(prof['parameters'], {'A': 7, 'B': -2})
        self.assertFalse(prof['native_qualified'])
        self.assertEqual(lit['B'], "32'sb" + format(-2 & 0xffffffff, '032b'))
        # verify_bound path: the recorded profile re-checks against the same identity
        lit2, prof2 = P.preserve(self.root, 'leaf', ov, 'rtl/leaf.sv', 'v/leaf', {'leaf': dict(prof, diagnostic_autoprofile=True)}, True)
        self.assertEqual((lit2, prof2), (lit, prof))
        # a changed view is detected
        (self.root / 'v/leaf/leaf.lef').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            P.preserve(self.root, 'leaf', ov, 'rtl/leaf.sv', 'v/leaf', {'leaf': prof}, True)


if __name__ == '__main__':
    unittest.main()
