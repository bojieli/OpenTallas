"""VM8-TIMING 2026-10-08: the route-time FF hold scene reads io_ref_routed.sdc by default (OT_MM_FF_SDC)."""
import os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl


def run_launch(spec_extra):
    spec = {"name": "t", "block": "b", "route_hold_corners": "mm",
            "verdict": {"post_sdc": ["physical/x/signoff_unc60.sdc"]},
            "source": {"branch": "main", "commit": "c" * 40}, "stages": {}, **spec_extra}
    j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": spec, "commit_full": "c" * 40, "attempt": 1,
         "created": "2026-10-08T15:00:00-07:00"}
    bodies = []

    def fake_ssh(host, c, input=None, **k):
        if input is not None:
            bodies.append(input)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
        cl.launch_stage(j, {"kind": "route", "key": "route", "threads": 4}, "echo route")
    return [l for l in bodies[0].splitlines() if l.startswith("export OT_MM_FF_SDC=") or "/.ot_mm/" in l]


def run_launch_all(spec_extra, cmd):
    spec = {"name": "t", "block": "b", "route_hold_corners": "mm",
            "verdict": {"post_sdc": ["physical/x/signoff_unc60.sdc"]},
            "source": {"branch": "main", "commit": "c" * 40}, "stages": {}, **spec_extra}
    j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": spec, "commit_full": "c" * 40, "attempt": 1,
         "created": "2026-10-08T15:00:00-07:00"}
    bodies = []

    def fake_ssh(host, c, input=None, **k):
        if input is not None:
            bodies.append(input)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
        cl.launch_stage(j, {"kind": "route", "key": "route", "threads": 4}, cmd)
    return bodies[0]


class RouteFfIoref(unittest.TestCase):
    def test_default_appends_ioref(self):
        lines = "\n".join(run_launch({}))
        self.assertIn("cp /r/cl/io_ref_routed.sdc /r/src/.ot_mm/", lines)
        self.assertIn("export OT_MM_FF_SDC='physical/x/signoff_unc60.sdc .ot_mm/io_ref_routed.sdc'", lines)

    def test_explicit_listing_kept(self):
        lines = "\n".join(run_launch({"route_ff_sdc": ["physical/x/a.sdc", "physical/common_flow/io_ref_routed.sdc"]}))
        self.assertNotIn(".ot_mm/io_ref_routed.sdc", lines)     # no second copy in the list (the tcl skips the file too)
        self.assertIn("export OT_MM_FF_SDC='physical/x/a.sdc physical/common_flow/io_ref_routed.sdc'", lines)

    def test_opt_out(self):
        lines = "\n".join(run_launch({"route_ff_ioref": False}))
        self.assertNotIn("io_ref_routed", lines)

    # MMFF-IOREF 2026-10-08: the reference travels as a file the FF scene reads last, so an inline export in the route
    # command (which overrides the loop's OT_MM_FF_SDC) cannot drop it
    def test_inline_export_still_gets_ioref_file(self):
        lines = run_launch_all({"stages": {}}, "export OT_MM_FF_SDC='physical/x/a.sdc'; echo route")
        self.assertIn("cp /r/cl/io_ref_routed.sdc /r/src/.ot_mm/ff_ioref_last.sdc", lines)
        self.assertNotIn("rm -f /r/src/.ot_mm/ff_ioref_last.sdc", lines)

    def test_opt_out_removes_ioref_file(self):
        lines = run_launch_all({"route_ff_ioref": False}, "echo route")
        self.assertIn("rm -f /r/src/.ot_mm/ff_ioref_last.sdc", lines)
        self.assertNotIn("ff_ioref_last.sdc\n", lines.replace("rm -f /r/src/.ot_mm/ff_ioref_last.sdc\n", ""))


TCL_STUBS = r"""
set ::reads {}
proc read_sdc {args} { lappend ::reads [lindex $args end] }
proc set_mode {m} {}
proc write_sdc {args} {}
proc set_propagated_clock {args} {}
proc all_clocks {} { return {} }
proc set_false_path {args} {}
proc estimate_parasitics {args} {}
proc unset_path_exceptions {args} {}
proc find_timing_paths {args} { return {} }
source [lindex $argv 0]
set ::ot_mm_active 1
set ::ot_mm_stage 3_place.sdc
set ::env(RESULTS_DIR) [lindex $argv 1]
ot_mm_sync
puts "READS [join $::reads ,]"
"""


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class FfSceneReadsIorefLast(unittest.TestCase):
    """orfs_hold_mm.tcl ot_mm_sync: the loop's ff_ioref_last.sdc is read after the job's own FF SDCs, once"""

    def sync(self, ff, with_file=True):
        d = tempfile.mkdtemp()
        try:
            for f in ff + ["ff_ioref_last.sdc"]:
                Path(d, f).write_text("")
            if not with_file:
                os.remove(Path(d, "ff_ioref_last.sdc"))
            tcl = Path(d, "t.tcl")
            tcl.write_text(TCL_STUBS)
            env = dict(os.environ, OT_MM_FF_SDC=" ".join(str(Path(d, f)) for f in ff),
                       OT_MM_IOREF_FILE=str(Path(d, "ff_ioref_last.sdc")))
            out = subprocess.run(["tclsh", str(tcl), str(Path(__file__).parent.parent / "orfs_hold_mm.tcl"), d],
                                 env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            reads = [l for l in out.stdout.splitlines() if l.startswith("READS ")][0][6:].split(",")
            return [Path(r).name for r in reads if r]
        finally:
            shutil.rmtree(d)

    def test_inline_list_gets_ioref_last(self):
        self.assertEqual(self.sync(["a.sdc", "b.sdc"])[-3:], ["a.sdc", "b.sdc", "ff_ioref_last.sdc"])

    def test_listed_ioref_not_read_twice(self):
        r = self.sync(["a.sdc", "io_ref_routed.sdc"])
        self.assertEqual(r[-2:], ["a.sdc", "io_ref_routed.sdc"])
        self.assertNotIn("ff_ioref_last.sdc", r)

    def test_opt_out_no_file(self):
        self.assertNotIn("ff_ioref_last.sdc", self.sync(["a.sdc"], with_file=False))


SHIM_STUBS = r"""
proc set_mode {m} {}
proc write_sdc {args} {}
proc set_propagated_clock {args} {}
proc all_clocks {} { return {} }
proc set_false_path {args} {}
proc estimate_parasitics {args} {}
proc unset_path_exceptions {args} {}
proc find_timing_paths {args} { return {} }
proc get_pins {args} { return [list [lindex $args end]] }
proc get_ports {args} { return {} }
proc get_property {args} { return "ALLSCENES" }
proc report_clock_latency {args} { puts "RCL $args" }
proc report_arrival {args} { puts "(c ^) r 10.0:12.5 f ---:---"; puts "(c v) r 11.0:14.0 f 1:2" }
namespace eval sta { proc redirect_string_begin {} { rename ::puts ::ot_rp; proc ::puts {s} { append ::ot_rb $s "\n" } ; set ::ot_rb "" }
                     proc redirect_string_end {} { rename ::puts {}; rename ::ot_rp ::puts; return $::ot_rb } }
proc read_sdc {f} { puts "IN [get_property p arrival_max_rise] [get_property -object_type pin p arrival_min_rise] [get_property p name] [info exists ::ot_ioref_scene]"; report_clock_latency -clocks c }
source [lindex $argv 0]
set ::ot_mm_active 1
set ::ot_mm_stage 3_place.sdc
set ::env(RESULTS_DIR) [lindex $argv 1]
ot_mm_sync
puts "OUT [get_property p arrival_max_rise] [info exists ::ot_ioref_scene]"
report_clock_latency -clocks c
"""


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class FfSceneArrivalsAreBc(unittest.TestCase):
    """MMFF-INSERTION: while the FF SDCs are read, pin arrivals / clock latency come from scene BC only"""

    def test_shim(self):
        d = tempfile.mkdtemp()
        try:
            Path(d, "a.sdc").write_text("")
            Path(d, "t.tcl").write_text(SHIM_STUBS)
            env = dict(os.environ, OT_MM_FF_SDC=str(Path(d, "a.sdc")), OT_MM_IOREF_FILE=str(Path(d, "none.sdc")))
            out = subprocess.run(["tclsh", str(Path(d, "t.tcl")), str(Path(__file__).parent.parent / "orfs_hold_mm.tcl"), d],
                                 env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            o = out.stdout.splitlines()
            self.assertIn("IN 14.0 10.0 ALLSCENES 1", o)            # max/min of the BC rise arrivals; other props pass through
            self.assertIn("RCL -clocks c -scenes BC", o)
            self.assertIn("OUT ALLSCENES 0", o)                    # restored after the sync
            self.assertEqual(o[-1], "RCL -clocks c")
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
