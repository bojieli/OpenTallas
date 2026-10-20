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

    def test_unsigned_packed_actual_and_high_bit(self):
        source = "module ot_qkh_ktree #(parameter [31:0] SCALE=32'h3DB504F3)(input ck); endmodule"
        defaults = P.integer_defaults(source, 'ot_qkh_ktree')
        self.assertEqual(defaults['SCALE'], 0x3DB504F3)
        self.assertIsInstance(defaults['SCALE'], P.U32)
        values, literals = P.evaluated({'SCALE': '1'*32}, defaults, 'ot_qkh_ktree')
        self.assertEqual(values['SCALE'], 0xffffffff)
        self.assertIsInstance(values['SCALE'], P.U32)
        self.assertEqual(literals['SCALE'], "32'sb" + '1'*32)
        signed, _ = P.evaluated({'SCALE': '1'*32}, {'SCALE': 0}, 'm')
        self.assertEqual(signed['SCALE'], -1)

    def test_unsigned_packed_range_and_unknowns_refuse(self):
        for value in ("4294967296", "-1", "32'h100000000", "32'hxxxxxxxx", "16'hffff", "32'b2", "1+2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                P.integer_defaults('module m #(parameter [31:0] P='+value+')(input a);', 'm')
        for declaration in ('parameter [30:0] P=0', 'parameter signed [31:0] P=0', 'parameter logic [31:0] P=0'):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                P.integer_defaults('module m #('+declaration+')(input a);', 'm')
        for value in ('32\'hffffffff', "32'd4294967295", '4294967295', "32'b"+'1'*32):
            self.assertEqual(P.integer_defaults('module m #(parameter [31:0] P='+value+')(input a);', 'm')['P'], 0xffffffff)

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
