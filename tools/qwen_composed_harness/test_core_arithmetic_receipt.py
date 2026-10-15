"""Negative controls for arithmetic build provenance (not numeric qualification)."""
import json
from pathlib import Path
import tempfile
import unittest
from core_arithmetic_receipt import digest, validate


class ArithmeticProvenance(unittest.TestCase):
    def fixture(self, root):
        core = root / 'obj'
        core.mkdir()
        (core / 'Vot_hdc_core_vector_weight_native_candidate__ALL.a').write_bytes(b'parent')
        (core / 'child.a').write_bytes(b'pipeline')
        rtl = root / 'ot_hdc_fastfp.sv'
        rtl.write_text('module ot_hdc_fp32_add_fast; endmodule\n')
        r = dict(exit=0, hierarchical=True, command=['-GG=3072', '-GLV=6'],
                 fp_units='RTL rtl/hdc/ot_hdc_fastfp.sv', source_sha256={str(rtl): digest(rtl)})
        (root / 'receipt.json').write_text(json.dumps(r))
        return core, rtl, r

    def test_completed_arithmetic_scope_stays_non_native(self):
        with tempfile.TemporaryDirectory() as d:
            core, _, _ = self.fixture(Path(d))
            self.assertFalse(validate(core)['native_full_token'])

    def test_changed_rtl_fails(self):
        with tempfile.TemporaryDirectory() as d:
            core, rtl, _ = self.fixture(Path(d))
            rtl.write_text('changed arithmetic')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                validate(core)

    def test_dpi_source_fails_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            core, rtl, r = self.fixture(root)
            rtl.write_text('import "DPI-C" function int replacement();')
            r['source_sha256'][str(rtl)] = digest(rtl)
            (root / 'receipt.json').write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError, 'DPI import'):
                validate(core)

    def test_incomplete_build_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            core, _, r = self.fixture(root)
            r['exit'] = 1
            (root / 'receipt.json').write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError, 'completed successfully'):
                validate(core)


if __name__ == '__main__':
    unittest.main()
