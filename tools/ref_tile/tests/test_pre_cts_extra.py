"""An explicit clock adapter must execute before generated IO wrapping and ship."""
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT


class ExtraClockHook(unittest.TestCase):
    def spec(self, **kw):
        s = {'name': 'probe', 'kind': 'tile', 'clock': 'spine', 'recipe': 1,
             'sources': [], 'children': [], 'macros': [], 'pins': {}, 'route': {},
             'inhold': False, 'outhold': False}
        s.update(kw)
        return s

    def test_adapter_executes_before_io_wrapper(self):
        s = self.spec(pre_cts_extra=['clock_adapter.tcl'])
        hooks = RT.gen_hooks(s, 'physical/ref_tile/probe')
        harness = r'''
set ::roots {}; set ::boundary 0
proc source {path} {
  switch -glob -- $path {
    */clock_spine.tcl {
      proc ot_clock_spine {} {lappend ::roots ck; return 1}
      proc clock_tree_synthesis {args} {ot_clock_spine}
    }
    */clock_adapter.tcl {
      if {![llength [info procs ot_clock_spine]]} {error "missing spine"}
      rename ot_clock_spine original_spine
      proc ot_clock_spine {} {original_spine; lappend ::roots ckd; return 1}
    }
    */pre_cts_skew.tcl {
      rename clock_tree_synthesis original_cts
      proc clock_tree_synthesis {args} {original_cts {*}$args;set ::boundary 1}
    }
  }
}
'''
        script = harness + hooks['pre_cts.tcl'] + '\nclock_tree_synthesis\nputs "$::roots/$::boundary"\n'
        r = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), 'ck ckd/1')
        self.assertIn('clock_adapter.tcl', '\n'.join(RT.referenced_paths(s, 'physical/ref_tile/probe')))

    def test_no_adapter_preserves_existing_hook(self):
        s = self.spec()
        plain = RT.gen_hooks(s, 'physical/ref_tile/probe')
        self.assertEqual(plain, RT.gen_hooks(self.spec(pre_cts_extra=[]), 'physical/ref_tile/probe'))
        self.assertNotIn('clock_adapter', plain['pre_cts.tcl'])


if __name__ == '__main__':
    unittest.main()
