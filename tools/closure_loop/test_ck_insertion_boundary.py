"""False paths cannot hide physical pin registers from clock insertion."""
import pathlib
import subprocess
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ck_insertion as C

class Boundary(unittest.TestCase):
    def probe(self, inputs='{din rst_n}', outputs='{dout}', fanout='{capture/D interior/RESET other/D}'):
        setup = r'''
proc get_full_name {p} {return $p}
# OpenSTA semantics: -data_pins includes asynchronous set/clear pins.
proc all_registers {args} {
 if {"-async_pins" in $args} {return {interior/RESET arst/RESETN}}
 if {"-clock_pins" in $args} {return {capture/CLK interior/CLK launch/CLK arst/CLK other/CLK}}
 if {"-data_pins" in $args} {return {capture/D interior/D interior/RESET other/D launch/D arst/D arst/RESETN}}
 error "unexpected all_registers $args"
}
proc all_inputs {args} {return INPUTS}
proc all_outputs {} {return OUTPUTS}
# Mock a false-path data input, asynchronous reset of an internal flop,
# and an input in a different clock domain. No timing paths exist.
proc get_fanout {args} {
 if {[lindex $args end] ne "all"} {error "disabled arcs were excluded"}
 return FANOUT
}
proc get_fanin {args} {
 if {[lindex $args end] ne "all"} {error "disabled arcs were excluded"}
 return {launch/Q other/Q passthrough}
}
proc find_timing_paths {args} {error "must not use timed paths"}
set regs [dict create capture capture/CLK interior interior/CLK launch launch/CLK arst arst/CLK]
'''.replace('INPUTS', inputs).replace('OUTPUTS', outputs).replace('FANOUT', fanout)
        code = setup+'\nif {[catch {\n'+C.BOUNDARY_TCL+'\n} e]} {puts stderr $e;exit 1}\nputs [lsort [dict keys $bnd]]\n'
        r = subprocess.run(['tclsh'], input=code, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_false_path_capture_and_launch_are_boundary_but_reset_and_other_domain_are_not(self):
        self.assertEqual(self.probe(), 'capture launch')

    def test_async_reset_only_flop_is_not_boundary_although_data_pins_lists_reset(self):
        # arst's only connection from a port is its RESETN pin, which OpenSTA
        # reports under -data_pins too; it must not become a boundary register.
        self.assertEqual(self.probe(fanout='{capture/D arst/RESETN interior/RESET}'), 'capture launch')
        self.assertEqual(self.probe(outputs='{}', fanout='{arst/RESETN}'), '')

    def test_clock_pins_never_select_boundary(self):
        self.assertEqual(self.probe(outputs='{}', fanout='{arst/CLK capture/CLK}'), '')

    def test_no_data_ports_does_not_promote_internal_clock_sinks(self):
        self.assertEqual(self.probe('{}', '{}'), '')

    def test_generated_tcl_uses_structural_membership(self):
        t = C.tcl('tt', '6_final.odb', '6_final.sdc', True, 'lane_ckf', raw_source=True)
        self.assertIn(C.BOUNDARY_TCL, t)
        self.assertNotIn('find_timing_paths', C.BOUNDARY_TCL)
        self.assertIn('find_timing_paths -group_path_count 1', t)

if __name__ == '__main__':
    unittest.main()
