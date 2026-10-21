"""Unsigned32 parameter regression; missing-profile policy stays strict."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import kv_expand_parameters as P

class UnsignedParameters(unittest.TestCase):
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

    def test_missing_profile_policy_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'leaf.sv').write_text("module leaf #(parameter [31:0] SCALE=32'h3DB504F3)(input ck); endmodule")
            for diagnostic in (False, True):
                for env in ('0', '1'):
                    with self.subTest(diagnostic=diagnostic, env=env), mock.patch.dict(os.environ, {'OT_KV_PARAM_DIAG': env}):
                        with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
                            P.preserve(root, 'leaf', {}, 'leaf.sv', 'unused_view', {}, diagnostic)

if __name__ == '__main__':
    unittest.main(verbosity=2)
