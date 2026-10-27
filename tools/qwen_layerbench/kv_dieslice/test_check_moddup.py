#!/usr/bin/env python3
"""Unit tests for check_moddup.py (one source per module in a Verilator source list)."""
import os
import subprocess
import sys
import tempfile
import unittest

H = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(H, 'check_moddup.py')


def run(d, listname='vl.f'):
    p = subprocess.run([sys.executable, '-I', TOOL, os.path.join(d, listname)], capture_output=True, text=True, cwd=d)
    return p.returncode, p.stdout


class ModdupTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = self.t.name

    def tearDown(self):
        self.t.cleanup()

    def w(self, name, text):
        p = os.path.join(self.d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(text)
        return p

    def test_clean_list_passes(self):
        a = self.w('a.sv', 'module a; endmodule\n// module ghost; endmodule\n/* module ghost2; */\n')
        b = self.w('b.sv', 'module b #(parameter W=1) (input wire c); endmodule\n')
        self.w('vl.f', f'-Wno-MODDUP\n--top-module a\n-y {self.d}/lib\n+incdir+{self.d}\n{a}\n{b}\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 0, out)
        self.assertIn('MODDUP_CHECK PASS sources 2 duplicated_modules 0', out)

    def test_two_revisions_of_one_module_fail(self):
        # the TOK-QK-3 case: an old vehicle copy and the fixed copy of the same controller file in one list
        old = self.w('vehicle4/qkd_ctrl_pc_nc.sv', 'module qkd_ctrl_pc_sched_nc; reg boot = 0; endmodule\n')
        new = self.w('boot2005/qkd_ctrl_pc_nc.sv', 'module qkd_ctrl_pc_sched_nc; reg boot_win = 1; endmodule\n')
        self.w('vl.f', f'{old}\n{new}\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn('MODDUP qkd_ctrl_pc_sched_nc defined in 2 files (DIFFERENT module text)', out)
        self.assertLess(out.index('vehicle4'), out.index('boot2005'))   # report keeps list order (first = kept)

    def test_identical_copies_still_fail(self):
        a = self.w('x/t.sv', 'module t; endmodule\n')
        b = self.w('y/t.sv', 'module  t;\n  endmodule // same text\n')
        self.w('vl.f', f'{a}\n{b}\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn('identical module text', out)

    def test_same_module_in_another_file_body(self):
        # the main ot_qkvd_kcmd_tap case: a second definition inside a different file
        a = self.w('kcmd_tap.sv', 'module kcmd_tap; wire a; endmodule\n')
        b = self.w('kv_desc.sv', 'module kv_desc; endmodule\nmodule kcmd_tap; wire b; endmodule\n')
        self.w('vl.f', f'{a}\n{b}\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn('MODDUP kcmd_tap', out)
        self.assertNotIn('MODDUP kv_desc', out)

    def test_nested_lists_and_relisting(self):
        a = self.w('a.sv', 'module a; endmodule\n')
        self.w('sub.f', f'{a}\n')
        self.w('vl.f', f'-f {self.d}/sub.f\n{a}\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 0, out)
        self.assertIn('listed twice', out)

    def test_nested_duplicate_fails(self):
        a = self.w('p/a.sv', 'module a; endmodule\n')
        b = self.w('q/a.sv', 'module a; wire z; endmodule\n')
        self.w('sub.f', f'{b}\n')
        self.w('vl.f', f'{a}\n-f {self.d}/sub.f\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)

    def test_drop_redundant_identical_copy(self):
        cells = self.w('bind_cells.sv', 'module bank; wire a; endmodule\nmodule ff; endmodule\nmodule other; endmodule\n')
        bank = self.w('lib/bank.sv', 'module bank;  wire a;  endmodule\nmodule ff; endmodule\n')
        self.w('vl.f', f'{cells}\n{bank}\n')
        p = subprocess.run([sys.executable, '-I', TOOL, '--drop-redundant', os.path.join(self.d, 'vl.f')],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('MODDUP_DROP', p.stdout)
        self.assertNotIn('lib/bank.sv', open(os.path.join(self.d, 'vl.f')).read())

    def test_drop_redundant_keeps_different_text(self):
        a = self.w('kcmd_tap.sv', 'module kcmd_tap; wire a; endmodule\n')
        b = self.w('kv_desc.sv', 'module kcmd_tap; wire b; endmodule\n')
        self.w('vl.f', f'{a}\n{b}\n')
        p = subprocess.run([sys.executable, '-I', TOOL, '--drop-redundant', os.path.join(self.d, 'vl.f')],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('kv_desc.sv', open(os.path.join(self.d, 'vl.f')).read())

    def test_unreadable_source(self):
        self.w('vl.f', f'{self.d}/missing.sv\n')
        rc, out = run(self.d)
        self.assertEqual(rc, 2, out)


if __name__ == '__main__':
    unittest.main()
