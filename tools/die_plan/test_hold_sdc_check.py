import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
import hold_sdc_check as H

HERE = Path(__file__).resolve().parent


def kit(sha=True, stage_body=None, stale=False):
    k = Path(tempfile.mkdtemp()) / "t1"
    k.mkdir()
    (k / "constraint.sdc").write_text("set_output_delay -min 12 -clock vclk [all_outputs]\n")
    h = hashlib.sha256((k / "constraint.sdc").read_bytes()).hexdigest()
    (k / "config.mk").write_text("export SDC_FILE = /work/constraint.sdc\n" + (f"export OT_SIGNOFF_SDC_SHA = {h[:16] if not stale else '0' * 16}\n" if sha else ""))
    (k / "hold_pad_hb4.tcl").write_text("repair_timing -hold\n")
    (k / "hold_sdc_guard.tcl").write_text("proc x {} {}\n")
    if stage_body:
        (k / "stage.tcl").write_text(stage_body)
    return k


class Check(unittest.TestCase):
    def test_clean_kit(self):
        self.assertEqual(H.kit_findings(kit(stage_body="source /work/hold_sdc_guard.tcl\nrepair_timing -hold\n")), [])

    def test_missing_or_stale_hash(self):
        self.assertTrue(H.kit_findings(kit(sha=False))[0].startswith("HOLD-SDC-NOHASH"))
        self.assertTrue(H.kit_findings(kit(stale=True))[0].startswith("HOLD-SDC-NOHASH"))

    def test_hold_stage_without_guard(self):
        f = H.kit_findings(kit(stage_body="read_sdc /work/constraint.sdc\nrepair_timing -hold -hold_margin 0\n"))
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0].startswith("HOLD-SDC-NOGUARD t1/stage.tcl"))

    def test_comment_only_mention_is_not_a_stage(self):
        self.assertEqual(H.kit_findings(kit(stage_body="# repair_timing -hold is run by ORFS\nputs x\n")), [])

    def test_compare_mode(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.sdc").write_text("x\n"); (d / "b.sdc").write_text("x\n"); (d / "c.sdc").write_text("y\n")
        self.assertEqual(H.compare(d / "a.sdc", d / "b.sdc"), [])
        self.assertTrue(H.compare(d / "a.sdc", d / "c.sdc")[0].startswith("HOLD-SDC-HASH"))

    def test_non_type_kit_is_skipped(self):
        self.assertEqual(H.kit_findings(tempfile.mkdtemp()), [])


@unittest.skipUnless(subprocess.run(["which", "tclsh"], capture_output=True).returncode == 0, "no tclsh")
class Guard(unittest.TestCase):
    """hold_sdc_guard.tcl under tclsh with stub OpenSTA commands: re-applies the golden min output delay a session lacks, no-op when equal, errors on a hash mismatch"""
    SCRIPT = r"""
set d [lindex $argv 0]; set mode [lindex $argv 1]
proc all_outputs {} { return {o0 o1} }
proc all_inputs {args} { return {i0} }
proc get_full_name {p} { return $p }
proc get_ports {args} {
    set ports [lindex $args end]
    if {$ports eq {bus[*]}} { return {bus[0] bus[1]} }
    return $ports
}
set ::log {}
proc set_output_delay {args} { lappend ::log $args }
proc set_input_delay {args} { lappend ::log $args }
set session "set_output_delay -clock vclk -max 30.0 {o0 o1}"
if {$mode eq "equal"} { set session "set_output_delay -clock vclk -min 12.0 {o0 o1}" }
if {[string match "bus_*" $mode]} {
    set session {set_output_delay 12.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {bus[0]}]}
    if {$mode eq "bus_equal"} {
        append session "\n" {set_output_delay 12.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {bus[1]}]}
    }
    if {$mode eq "bus_mismatch"} {
        append session "\n" {set_output_delay 13.0000 -clock [get_clocks {vclk}] -min -add_delay [get_ports {bus[1]}]}
    }
}
proc write_sdc {args} { global session; set f [open [lindex $args end] w]; puts $f $session; close $f }
proc repair_timing {args} { global rt; set rt $args }
source $d/hold_sdc_guard.tcl
set ::ot_hsg_dir $d
if {$mode eq "badhash"} { set ::env(OT_SIGNOFF_SDC_SHA) 00000000deadbeef }
if {[catch {repair_timing -hold} err]} { puts "ERR $err" } else { puts "OK rt=$rt applied=[llength $::log]" }
"""

    def run_(self, mode):
        d = Path(tempfile.mkdtemp())
        (d / "hold_sdc_guard.tcl").write_text((HERE / "hold_sdc_guard.tcl").read_text())
        ports = "bus[*]" if mode.startswith("bus_") else "o0 o1"
        (d / "constraint.sdc").write_text(
            f"set_output_delay -min 12.0 -clock vclk [get_ports {{{ports}}}]\n"
        )
        (d / "s.tcl").write_text(self.SCRIPT)
        return subprocess.run(["tclsh", str(d / "s.tcl"), str(d), mode], capture_output=True, text=True).stdout

    def test_missing_min_is_reapplied(self):
        o = self.run_("missing")
        self.assertIn("session_missing 2 reapplied_lines 1", o)
        self.assertIn("OK rt=-hold applied=1", o)

    def test_equal_session_untouched(self):
        o = self.run_("equal")
        self.assertIn("session_missing 0 reapplied_lines 0", o)
        self.assertIn("applied=0", o)

    def test_written_clock_collection_and_bus_match(self):
        o = self.run_("bus_equal")
        self.assertIn("io_golden 2 session_missing 0 reapplied_lines 0", o)
        self.assertIn("OK rt=-hold applied=0", o)

    def test_bus_bit_missing_or_mismatched_is_reapplied(self):
        for mode in ("bus_missing", "bus_mismatch"):
            with self.subTest(mode=mode):
                o = self.run_(mode)
                self.assertIn("io_golden 2 session_missing 1 reapplied_lines 1", o)
                self.assertIn("OK rt=-hold applied=1", o)

    def test_hash_mismatch_fails_the_stage(self):
        self.assertIn("ERR HOLD-SDC-MISMATCH", self.run_("badhash"))


class Messages(unittest.TestCase):
    def test_hold_in_a_message_string_is_not_a_stage(self):
        self.assertEqual(H.kit_findings(kit(stage_body='puts "OT_HOLD_GATE INFO repair_timing -hold stays information only"\n')), [])

    def test_catch_wrapped_stage_is_a_stage(self):
        f = H.kit_findings(kit(stage_body="if {[catch {repair_timing -hold -hold_margin 1} e]} { puts $e }\n"))
        self.assertEqual(len(f), 1)
