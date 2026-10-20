"""Diagnostic two-pin unsigned producer -> Yosys -> binder controls; no native qualification."""
import json
import os
import unittest
from unittest.mock import patch
import test_kv_expand_parameters as T

class UnsignedFlow(T.ExpansionParameters):
    def setUp(self):
        super().setUp()
        self.mod = 'ot_qwen_tp8_pv_slice_t'
        source = self.root / self.rtl[self.mod]
        source.write_text(source.read_text().replace('#(', "#(parameter [31:0] SCALE=32'hffffffff, ", 1))
        self.profiles[self.mod]['parameters']['SCALE'] = 0xffffffff
        self.profiles[self.mod]['identity'] = T.P.artifact_identity(self.root, self.views[self.mod], self.rtl[self.mod])
        self.write_profiles()
        parent = self.root / 'parent.sv'
        parent.write_text(parent.read_text().replace(self.mod+' #(', self.mod+" #(.SCALE(32'hffffffff),", 1))

    def test_high_unsigned_actual_flow(self):
        self.assertEqual(self.expand(), 0)
        side = json.loads((self.run/'case_kv/die.v.params.json').read_text())
        literal = "32'sb"+'1'*32
        self.assertEqual(side['f__u0']['SCALE'], literal)
        self.assertEqual(self.bind(), 0)
        self.assertIn('.SCALE('+literal+')', (self.root/'bound/die_bound.v').read_text())
        with self.assertRaisesRegex(ValueError, 'qualification missing'):
            self.bind(False)
        side['f__u0']['SCALE'] = "32'sb"+'0'*32
        (self.run/'case_kv/die.v.params.json').write_text(json.dumps(side))
        with self.assertRaisesRegex(ValueError, 'sidecar missing/conflicting'):
            self.bind()

    def test_high_unsigned_wrong_profile_refuses(self):
        self.profiles[self.mod]['parameters']['SCALE'] = -1
        self.write_profiles()
        with self.assertRaisesRegex(ValueError, 'profile/source/view mismatch'):
            self.expand()

    def test_high_unsigned_missing_profile_refuses_env_override(self):
        self.profiles.pop(self.mod)
        self.write_profiles()
        for diagnostic in (False, True):
            with self.subTest(diagnostic=diagnostic), patch.dict(os.environ, {'OT_KV_PARAM_DIAG':'1'}):
                with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
                    self.expand(diagnostic)

    def test_high_unsigned_strict_missing_receipt_refuses(self):
        original = (self.run/'case_kv/die.v').read_bytes()
        with self.assertRaisesRegex(ValueError, 'qualification missing'):
            self.expand(False)
        self.assertEqual((self.run/'case_kv/die.v').read_bytes(), original)


def load_tests(loader, tests, pattern):
    names = ('test_high_unsigned_actual_flow', 'test_high_unsigned_wrong_profile_refuses',
             'test_high_unsigned_missing_profile_refuses_env_override', 'test_high_unsigned_strict_missing_receipt_refuses')
    return unittest.TestSuite(UnsignedFlow(name) for name in names)
