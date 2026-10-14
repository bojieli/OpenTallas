"""Verify the serial boundary runs before hold repair in both CTS hook forms."""
import pathlib
import subprocess
import tempfile
import unittest

HOOK = pathlib.Path(__file__).resolve().parents[1] / 'physical/s81_ph_views/mtp/wfc_ser_ref.tcl'
STUBS = '''
namespace eval sta {proc find_timing_paths {args} {}}
namespace eval ord {proc get_db_block {} {return stub}}
proc get_clocks {args} {return [lindex $args end]}
proc get_property {args} {
 if {[lindex $args end] eq "is_propagated"} {return $::prop}
 return 1111.111
}
proc all_registers {args} {return {}}
proc get_ports {args} {return {}}
proc estimate_parasitics {args} {}
proc clock_tree_synthesis {args} {puts ORIGINAL_CTS}
'''


class HookOrder(unittest.TestCase):
    def run_hook(self, propagated):
        with tempfile.TemporaryDirectory() as td:
            caller = pathlib.Path(td) / 'test_pre_cts.tcl'
            caller.write_text(f'set ::prop {int(propagated)}\n' + STUBS +
                              f'source {{{HOOK}}}\nputs AFTER_SOURCE\n' +
                              ('' if propagated else 'clock_tree_synthesis\n'))
            return subprocess.run(['tclsh', str(caller)], check=True, capture_output=True,
                                  text=True).stdout

    def test_generated_callback_applies_serial_boundary_immediately(self):
        out = self.run_hook(True)
        self.assertIn('OT_SER balance:', out)
        self.assertLess(out.index('OT_SER_BOUNDARY'), out.index('AFTER_SOURCE'))
        self.assertNotIn('ORIGINAL_CTS', out)

    def test_legacy_callback_defers_until_tree_exists(self):
        out = self.run_hook(False)
        self.assertLess(out.index('AFTER_SOURCE'), out.index('ORIGINAL_CTS'))
        self.assertLess(out.index('ORIGINAL_CTS'), out.index('OT_SER balance:'))
        self.assertLess(out.index('OT_SER balance:'), out.index('OT_SER_BOUNDARY'))


if __name__ == '__main__':
    unittest.main()
