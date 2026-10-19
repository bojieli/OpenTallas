"""False paths cannot hide physical pin registers from clock insertion."""
import pathlib
import subprocess
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ck_insertion as C

class Boundary(unittest.TestCase):
    def probe(self, inputs='{din rst_n}', outputs='{dout}'):
        setup = r'''
proc get_full_name {p} {return $p}
proc all_registers {args} {return {capture/D interior/D other/D launch/D}}
proc all_inputs {args} {return INPUTS}
proc all_outputs {} {return OUTPUTS}
# Mock a false-path data input, asynchronous reset of an internal flop,
# and an input in a different clock domain. No timing paths exist.
proc get_fanout {args} {
 if {[lindex $args end] ne "all"} {error "disabled arcs were excluded"}
 return {capture/D interior/RESET other/D}
}
proc get_fanin {args} {
 if {[lindex $args end] ne "all"} {error "disabled arcs were excluded"}
 return {launch/Q other/Q passthrough}
}
proc find_timing_paths {args} {error "must not use timed paths"}
set regs [dict create capture capture/CLK interior interior/CLK launch launch/CLK]
'''.replace('INPUTS', inputs).replace('OUTPUTS', outputs)
        code = setup+'\nif {[catch {\n'+C.BOUNDARY_TCL+'\n} e]} {puts stderr $e;exit 1}\nputs [lsort [dict keys $bnd]]\n'
        r = subprocess.run(['tclsh'], input=code, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_false_path_capture_and_launch_are_boundary_but_reset_and_other_domain_are_not(self):
        self.assertEqual(self.probe(), 'capture launch')

    def test_no_data_ports_does_not_promote_internal_clock_sinks(self):
        self.assertEqual(self.probe('{}', '{}'), '')

    def test_generated_tcl_uses_structural_membership(self):
        t = C.tcl('tt', '6_final.odb', '6_final.sdc', True, 'lane_ckf', raw_source=True)
        self.assertIn(C.BOUNDARY_TCL, t)
        self.assertNotIn('find_timing_paths', t)

if __name__ == '__main__':
    unittest.main()
