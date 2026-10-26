"""A post-release ownership hook must execute in order and ship with the kit."""
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

HOOK = 'physical/common_flow/pin_reg_split.tcl'

class PreDplExtra(unittest.TestCase):
    def spec(self, **kw):
        s = dict(name='probe', kind='tile', recipe=3, clock='cts', pins={},
                 sources=[], macros=[], children=[], route={}, io_flop_at_pins=True, inhold=True, outhold=True)
        s.update(kw)
        return s

    def test_hook_executes_after_both_releases_and_ships(self):
        s = self.spec(pre_dpl_extra=[HOOK])
        hook = RT.gen_pin_hooks(s)['pre_dpl.tcl']
        harness = 'set order {}; proc source {p} {lappend ::order [file tail $p]}\n'
        r = subprocess.run(['tclsh'], input=harness + hook + '\nputs $order\n',
                           text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().split(), ['leaf_inhold_release.tcl',
                         'out_flop_release.tcl', 'pin_reg_split.tcl'])
        self.assertIn(HOOK, RT.referenced_paths(s, 'physical/ref_tile/probe'))

    def test_no_hook_preserves_existing_stage(self):
        s = self.spec()
        self.assertEqual(RT.gen_pin_hooks(s), RT.gen_pin_hooks(self.spec(pre_dpl_extra=[])))

    def test_unsafe_or_missing_path_fails(self):
        for path in ['/tmp/fix.tcl', '../fix.tcl', 'tools/no_such_pre_dpl_hook.tcl', 'bad;command.tcl']:
            with self.subTest(path=path), self.assertRaises(RT.SpecError):
                RT.gen_pin_hooks(self.spec(pre_dpl_extra=[path]))

    def test_hook_requires_stage_wrapper(self):
        with self.assertRaises(RT.SpecError):
            RT.gen_pin_hooks(self.spec(recipe=1, pre_dpl_extra=[HOOK]))

if __name__ == '__main__':
    unittest.main()
