"""Exercise the actual opt-in ECO hook blocks without loading OpenROAD."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def block(text, name):
    start = f'# OT_PG_STRICT_{name}_BEGIN\n'
    end = f'# OT_PG_STRICT_{name}_END\n'
    return text.split(start, 1)[1].split(end, 1)[0]


class PgEcoHooks(unittest.TestCase):
    def run_hook(self, name, strict, refuse=False, helper=True):
        text = (ROOT / name).read_text()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'native_pg_binding.tcl'
            if helper:
                path.write_text('''
proc ot_pg_prepare {b} {puts "prepare:$b"; return fresh_mapping}
proc ot_pg_assert_all_native {b m} {
    puts "assert:$b:$m"
    if {$::refuse} {error OT_PG_NATIVE_FAILURE}
}
''')
            script = '''
proc envd {n d} {expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d}}
namespace eval ord {proc get_db_block {} {return actual_block}}
proc global_connect {} {puts global_connect}
'''
            script += f'set ::env(OT_PG_STRICT) {strict}\nset ::env(OT_PG_HELPER) {{{path}}}\nset ::refuse {int(refuse)}\n'
            # Tcl stdin normally continues after errors; a caught script gives
            # the same fatal propagation as OpenROAD sourcing the whole file.
            script += 'set rc [catch {\n' + block(text, 'LOADER') + block(text, 'FINAL')
            script += '\nputs publication\n} msg]\nif {$rc} {puts stderr $msg; exit 2}\n'
            return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)

    def test_default_off_has_no_helper_dependency(self):
        for name in ('hold_eco.tcl', 'vtswap_eco.tcl'):
            with self.subTest(name=name):
                r = self.run_hook(name, 0, helper=False)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.splitlines(), ['publication'])

    def test_final_fresh_map_after_connect(self):
        for name in ('hold_eco.tcl', 'vtswap_eco.tcl'):
            with self.subTest(name=name):
                r = self.run_hook(name, 1)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.splitlines(), [
                    'global_connect', 'prepare:actual_block',
                    'assert:actual_block:fresh_mapping', 'publication'])

    def test_missing_pg_refuses_publication(self):
        for name in ('hold_eco.tcl', 'vtswap_eco.tcl'):
            with self.subTest(name=name):
                r = self.run_hook(name, 1, refuse=True)
                self.assertEqual(r.returncode, 2)
                self.assertIn('OT_PG_NATIVE_FAILURE', r.stderr)
                self.assertNotIn('publication', r.stdout)

    def test_missing_helper_refuses(self):
        for name in ('hold_eco.tcl', 'vtswap_eco.tcl'):
            with self.subTest(name=name):
                r = self.run_hook(name, 1, helper=False)
                self.assertEqual(r.returncode, 2)
                self.assertIn('OT_PG_HELPER_MISSING', r.stderr)
                self.assertNotIn('global_connect', r.stdout)
                self.assertNotIn('publication', r.stdout)

    def test_hook_precedes_final_artifacts_and_extraction(self):
        for name in ('hold_eco.tcl', 'vtswap_eco.tcl'):
            text = (ROOT / name).read_text()
            after = text.split('# OT_PG_STRICT_FINAL_END\n', 1)[1]
            self.assertIn('write_db ', after)
            self.assertIn('write_def ', after)
            self.assertIn('write_verilog ', after)
            if name == 'hold_eco.tcl':
                self.assertIn('extract_parasitics ', after)
                self.assertIn('write_spef ', after)
                self.assertLess(text.index('filler_placement $ot_fill'), text.index('# OT_PG_STRICT_FINAL_BEGIN'))


if __name__ == '__main__':
    unittest.main()
