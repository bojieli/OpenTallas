"""Negative controls for build provenance, using small synthetic ELF fixtures."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'tools/qwen_composed_harness/attention_rtl_library_check.py'
SPEC = importlib.util.spec_from_file_location('attention_check', SOURCE)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


@unittest.skipUnless(shutil.which('gcc') and shutil.which('nm'), 'requires gcc and nm')
class LibraryCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'receipt.json').write_text(json.dumps({'hierarchical': True, 'fp_units': 'RTL actual'}))
        self.manifest = ''.join('0' * 64 + '  rtl/' + unit + '\n' for unit in (
            'ot_hdc_fp32_add_lat.sv', 'ot_hdc_fp32_mul_lat.sv',
            'ot_hdc_fastfp.sv', 'ot_qwen_tp8_attention_service.sv'))
        (self.root / 'source.sha256').write_text(self.manifest)

    def library(self, source):
        c = self.root / 'fixture.c'
        c.write_text(source)
        subprocess.run(['gcc', '-shared', '-fPIC', str(c), '-o',
                        str(self.root / 'libot_qwen_tp8_attention_service.so')], check=True)

    def test_valid_build_fixture_keeps_scope_limits(self):
        self.library('int rtl_symbol(void){return 0;}')
        result = CHECK.check(self.root)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['full_native_token_qualified'])
        self.assertFalse(result['static_production_schedule_qualified'])

    def test_dpi_symbol_mutants(self):
        for symbol in ('nhb_fadd', 'nhb_fmul', 'ot_v41x_fadd', 'ot_v41x_fmul'):
            with self.subTest(symbol=symbol):
                self.library('extern int ' + symbol + '(void); int caller(void){return ' + symbol + '();}')
                with self.assertRaisesRegex(ValueError, 'behavioral FP symbol'):
                    CHECK.check(self.root)

    def test_source_mutant(self):
        self.library('int rtl_symbol(void){return 0;}')
        (self.root / 'source.sha256').write_text(self.manifest + '0' * 64 + '  rtl/test/sim_nhb_fp_lat_dpi.sv\n')
        with self.assertRaisesRegex(ValueError, 'behavioral FP source'):
            CHECK.check(self.root)

    def test_missing_real_multiplier(self):
        (self.root / 'source.sha256').write_text(self.manifest.replace('ot_hdc_fp32_mul_lat.sv', 'stub.sv'))
        with self.assertRaisesRegex(ValueError, 'missing source-pinned actual RTL unit'):
            CHECK.check(self.root)


if __name__ == '__main__':
    unittest.main()
