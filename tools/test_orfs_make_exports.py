"""Exercise the actual config writer through GNU Make, not string quoting alone."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import run_abi3_physical as P


class MakeExports(unittest.TestCase):
    def exported(self, values, *, old=False, recursive=False):
        lines = P.orfs_config_lines(
            'fixture', dict(top='dut', sources=['rtl/dut.sv'], parameters={}),
            'asap7', dict(corner_env=None, extra_config=values), 50, .5,
            memory_max_bits=None)
        if old:
            lines = [f'export {k} = {v}' for k, v in values.items()]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'config.mk').write_text('TC_NLDM_LIB_FILES := real_tt.lib\n' + '\n'.join(lines) + '\n')
            (root/'dump.py').write_text(
                'import os,json\nprint(json.dumps({k:os.environ.get(k) for k in ' + repr(list(values)) + '}))\n')
            recipe = ('\t@$(MAKE) --no-print-directory -f Makefile child\n' if recursive
                      else f'\t@{sys.executable} dump.py\n')
            (root/'Makefile').write_text('include config.mk\nall:\n' + recipe +
                                        f'child:\n\t@{sys.executable} dump.py\n')
            run = subprocess.run(['make', '--no-print-directory', '-f', 'Makefile', 'all'],
                                 cwd=root, capture_output=True, text=True, check=True)
            return json.loads(run.stdout)

    def test_actual_writer_preserves_exclusion_and_reset_regex(self):
        values = {'OT_PIN_REGS_EXCLUDE': r'^ckv$|^(f_ks|f_pw|t_kd|t_st)(\[.*\])?$',
                  'OT_PIN_REGS_RESET': r'^(rst|rsv)(\[.*\])?$'}
        self.assertEqual(self.exported(values), values)
        self.assertEqual(self.exported(values, recursive=True), values)
        self.assertNotEqual(self.exported(values, old=True), values)

    def test_all_literal_patterns_and_control_names_roundtrip(self):
        values = {'RESET_INCLUDE': r'^reset$|^clear_n$', 'RESET_EXCLUDE': r'^status$',
                  'SYNTH_RESET_INCLUDE': r'^reset$', 'SYNTH_RESET_EXCLUDE': r'^data$',
                  'OT_HOLD_PAD_STRONG_RE': r'^(n_y|rq_row)$',
                  'OT_FCL_TAP_RE': r'^ck[0-9]+[ew]?$',
                  'CUSTOM_PATTERN': r'^x#y\#z\\#w$',
                  'OT_PIN_REGS_CLOCK': 'ck$local,ckv',
                  'OT_PIN_REGS_RESET_PORTS': 'rst$local,rsv'}
        self.assertEqual(self.exported(values), values)

    def test_intentional_make_references_remain_expressions(self):
        values = {'WC_NLDM_LIB_FILES': '$(TC_NLDM_LIB_FILES)',
                  'ADDITIONAL_LIBS': '${TC_NLDM_LIB_FILES}'}
        self.assertEqual(self.exported(values), {k: 'real_tt.lib' for k in values})

    def test_multiline_literal_refuses_before_config_generation(self):
        for value in ['^data$\nexport X=bad', '^data$\rnext']:
            with self.assertRaises(P.FlowError):
                self.exported({'OT_PIN_REGS_EXCLUDE': value})


if __name__ == '__main__':
    unittest.main()
