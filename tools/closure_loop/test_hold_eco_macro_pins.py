"""Exercise the real Tcl exporter/window with a small STA API fixture.

The completed cmdproc_n route supplies the physical coverage evidence; these
tests guard macro inclusion, Tcl bus-name round trips, and fail-closed selection
without rerouting an array or requiring OpenROAD on the coordinator.
"""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


@unittest.skipUnless(shutil.which("tclsh"), "tclsh required")
class MacroPinCoverage(unittest.TestCase):
    def run_tcl(self, script, cwd):
        path = pathlib.Path(cwd) / "test.tcl"
        path.write_text(script)
        result = subprocess.run(["tclsh", str(path)], text=True,
                                capture_output=True, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_original_guides_required_and_no_fresh_route_on_rejection(self):
        source = (HERE / "hold_eco.tcl").read_text()
        guide_check = source[source.index("set guides [expr"):source.index("set snap [dict create]")]
        route = source[source.index("set ra [expr"):source.index("filler_placement")]
        with tempfile.TemporaryDirectory() as tmp:
            output = self.run_tcl(r'''
proc envd {n d} {return $d}
namespace eval grt {proc have_routes {} {return $::have_guides}}
set calls {}
proc global_route args {lappend ::calls $args}
proc detailed_route args {incr ::drt_calls; error "DRT-0218"}
set have_guides 0
set rc [catch {@CHECK@} err]
if {!$rc || ![string match {*original route guides required*} $err] || [llength $calls]} {
    error "missing guides did not fail closed"
}
set have_guides 1
@CHECK@
if {$calls ne {-start_incremental}} {error "original guides not used"}
set ::env(OT_OUT) .
set drt_calls 0
set rc [catch {@ROUTE@} err]
if {!$rc || $err ne "DRT-0218" || $drt_calls != 1} {error "guide rejection swallowed"}
if {$calls ne {-start_incremental {-end_incremental -allow_congestion -resistance_aware}}} {
    error "unexpected fresh route: $calls"
}
puts PASS
'''.replace("@CHECK@", guide_check).replace("@ROUTE@", route), tmp)
            self.assertIn("PASS", output)

    def test_export_and_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self.run_tcl(r'''
proc read_lef args {}
proc read_liberty args {}
proc read_db args {}
proc read_sdc args {}
proc set_propagated_clock args {}
proc all_clocks {} {return core_clk}
proc write_sdc args {}
namespace eval sta {proc worst_slack_cmd args {return 6.096e-11}}
set ::env(OT_CORNER) ss
set ::env(OT_DB) fixture.odb
set ::env(OT_SDC) fixture.sdc
set ::env(OT_EFF) eff_ss.sdc
set ::env(OT_MACROS) ""
set ::env(OT_POST_SDC) ""
set ::env(OT_SPEF) ""
proc get_pins args {return {flop/D}}
proc all_registers args {
    if {$args ne "-data_pins"} {error "must request timing-check data pins"}
    return {flop/D {u_cmem/b_addr_in[0]} {u_cmem/b_addr_in[1]} macro/unknown macro/unconstrained}
}
proc all_outputs {} {return out}
proc get_full_name p {return $p}
set values [dict create flop/D 100 {u_cmem/b_addr_in[0]} 646.189575 \
    {u_cmem/b_addr_in[1]} 670.676086 out 90 macro/unconstrained INF]
proc get_property {p prop} {
    if {$prop eq "slack_max"} {return [dict get $::values $p]}
    if {$prop eq "is_port"} {return [expr {$p eq "out"}]}
    if {$prop eq "endpoint"} {return $p}
    if {$prop eq "startpoint"} {return launch/Q}
    if {$prop eq "slack"} {return -20.46}
    error "unexpected property $prop"
}
proc find_timing_paths args {return {}}
source @CORNER@
set f [open eff_ss.sdc.slack]
set exported [read $f]; close $f
set ::ot_ss_slack [dict create]
foreach line [split [string trim $exported] \n] {
    if {[llength $line] != 2} {error "bad serialized pin: $line"}
    if {[dict exists $::ot_ss_slack [lindex $line 0]]} {error "duplicate pin"}
    dict set ::ot_ss_slack {*}$line
}
if {[dict size $::ot_ss_slack] != 4} {error "incorrect export: $exported"}
if {[dict get $::ot_ss_slack {u_cmem/b_addr_in[0]}] != 646.189575} {error "macro slack lost"}
source @WINDOW@
# The failed job's macro address pin must be fixable, while unknown SS data
# must remain excluded rather than being labelled a physically infeasible path.
proc find_timing_paths args {
    return {{u_cmem/b_addr_in[0]} macro/unknown macro/unconstrained tight/D impossible/D}
}
dict set ::ot_ss_slack tight/D 110
dict set ::ot_ss_slack impossible/D 99
set win [ot_window 21 40 15 test 15]
if {[dict get $win fixable] ne {{u_cmem/b_addr_in[0]}}} {error "macro not fixable: $win"}
if {[dict get $win nodata] ne {macro/unknown macro/unconstrained}} {error "missing-data guard lost: $win"}
if {[dict get $win tight] ne {tight/D}} {error "tight window guard lost: $win"}
if {[dict get $win infeasible] ne {impossible/D}} {error "SS/FF 15 ps guard lost: $win"}
puts PASS
'''.replace("@CORNER@", str(HERE / "hold_eco_corner.tcl"))
                .replace("@WINDOW@", str(HERE / "hold_eco_window.tcl")), tmp)
            self.assertIn("PASS", output)


if __name__ == "__main__":
    unittest.main()
