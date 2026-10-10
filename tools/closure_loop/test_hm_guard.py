"""HM-GUARD (2026-10-08): the route-time hold-margin auto-reduction decision (tools/orfs_hold_mm.tcl ot_hm_decide /
ot_hm_buffers, run under tclsh) and the loop's event parsing."""
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl

TCL = cl.HERE.parent / "orfs_hold_mm.tcl"


def tcl(expr):
    # source only the pure procs (the rest of the file needs OpenROAD); ot_env_num is pure too
    src = TCL.read_text()
    procs = []
    for name in ("ot_env_num", "ot_hm_buffers", "ot_hm_decide"):
        i = src.index(f"proc {name} ")
        j = src.index("\nproc ", i + 1)
        procs.append(src[i:j])
    r = subprocess.run(["tclsh"], input="\n".join(procs) + f"\nputs [{expr}]\n", capture_output=True, text=True, check=True)
    return r.stdout.split()


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class HmDecideTests(unittest.TestCase):
    def decide(self, hm, worst, n, buffers, core=67000.0, area=0.08):
        out = tcl(f"ot_hm_decide {hm} {worst} {n} {buffers} {core} {area} 10000 8.0 10.0")
        return float(out[0]), float(out[1])

    def test_rx128_flood_real_hold_passes(self):
        # qfd_link_rx128: 72,493 endpoints inside 50 ps, real FF ws +2.85 -> floor 10
        new, pts = self.decide(50, 2.85, 72493, 146000)
        self.assertEqual(new, 10.0)
        self.assertGreater(pts, 8.0)

    def test_s81_rootcam_small_real_violation(self):
        # S81 PQ root CAM: 17,152 endpoints, real FF ws -4.97 -> 14.97 + round up -> 15.0
        new, _ = self.decide(50, -4.97, 17152, 21700, core=17700.0)
        self.assertAlmostEqual(new, 15.0)

    def test_area_trigger_below_endpoint_limit(self):
        # 6,000 endpoints but 20k projected buffers in a 17.7k um2 core (+9 pts) -> reduce
        new, pts = self.decide(50, 1.0, 6000, 20000, core=17700.0)
        self.assertEqual(new, 10.0)
        self.assertGreater(pts, 8.0)

    def test_small_block_keeps_margin(self):
        new, _ = self.decide(50, -3.0, 800, 1200)
        self.assertEqual(new, 50.0)

    def test_deep_real_violation_never_raises_margin(self):
        # VM8-like: real FF ws -128.7 -> violation + floor exceeds HM: keep HM (real repair, not a margin flood)
        new, _ = self.decide(50, -128.7, 13700, 102000)
        self.assertEqual(new, 50.0)

    def test_margin_at_floor_untouched(self):
        new, _ = self.decide(10, 2.0, 50000, 60000)
        self.assertEqual(new, 10.0)

    def test_buffer_projection(self):
        # deficits 50-2.85=47.15 -> 3, 50-30=20 -> 1, 50-49=1 -> 1, 60 >= hm -> 0
        self.assertEqual(int(tcl("ot_hm_buffers {2.85 30 49 60} 50 20")[0]), 5)


def run_repair(stats, guard_hm, env=""):
    """ot_repair_timing under tclsh with stubbed OpenROAD: ot_hold_stats pops `stats` ({ws tns viol} per call),
    ot_hm_guard rewrites -hold_margin to guard_hm; returns the repair_timing calls and the printed guard lines."""
    src = TCL.read_text()
    procs = []
    for name in ("ot_env_num", "ot_hold_guard_on", "ot_hold_stage", "ot_hold_stop_cap", "ot_hold_stop_args", "ot_hold_stop",
                 "ot_repair_timing"):
        i = src.index(f"proc {name} ")
        j = src.index("\nproc ", i + 1) if src.find("\nproc ", i + 1) > 0 else len(src)
        procs.append(src[i:j])
    stubs = f"""
set ::calls {{}}
set ::stats {{{' '.join('{' + ' '.join(map(str, x)) + '}' for x in stats)}}}
proc log_cmd {{args}} {{ lappend ::calls [join $args " "] }}
proc ot_hold_stats {{}} {{ set s [lindex $::stats 0]; if {{[llength $::stats] > 1}} {{ set ::stats [lrange $::stats 1 end] }}; return $s }}
proc ot_hm_guard {{a}} {{ set i [lsearch -exact $a -hold_margin]; return [lreplace $a [expr {{$i + 1}}] [expr {{$i + 1}}] {guard_hm}] }}
proc ot_hold_window_report {{why hist}} {{ puts "STALL $why" }}
{env}
"""
    body = stubs + "\n".join(procs) + "\not_repair_timing {-setup_margin 0 -hold_margin 50 -verbose}\n" \
        "foreach c $::calls { puts \"CALL $c\" }\n"
    r = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True)
    calls = [ln[5:] for ln in r.stdout.splitlines() if ln.startswith("CALL ")]
    return calls, r.stdout


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class MetFirstTests(unittest.TestCase):
    def test_flood_repairs_at_hm0_and_stops_when_met(self):
        # su_ctlh vf-lvt: HM-AUTO 50 -> 26.3 on a 60k-endpoint flood, real ws -16.24; HM 0 repair meets -> stop
        calls, out = run_repair([(-16.24, -12174.0, 3796), (0.4, 0.0, 0)], 26.3)
        self.assertEqual(len(calls), 2)
        self.assertIn("-setup", calls[0])
        self.assertIn("-hold_margin 0.0", calls[1])
        self.assertIn("-hold", calls[1])
        self.assertIn("margin chase skipped", out)

    def test_flood_already_met_skips_hold_repair(self):
        calls, out = run_repair([(2.85, 0.0, 0)], 10.0)
        self.assertEqual(len(calls), 1)
        self.assertIn("margin chase skipped", out)

    def test_flood_still_violating_falls_back_to_guarded_chunks(self):
        calls, _ = run_repair([(-40.0, -9000.0, 900), (-30.0, -5000.0, 500), (-10.0, -100.0, 20), (12.0, 0.0, 0)], 50 - 1)
        self.assertIn("-hold_margin 0.0", calls[1])
        self.assertTrue(any("-max_iterations" in c and "-hold_margin 49" in c for c in calls[2:]))

    def test_no_flood_keeps_margin_chase(self):
        calls, out = run_repair([(-3.0, -10.0, 4), (50.5, 0.0, 0)], 50)
        self.assertNotIn("margin chase skipped", out)
        self.assertIn("-hold_margin 50", calls[1])
        self.assertIn("-max_iterations", calls[1])

    def test_opt_out(self):
        calls, out = run_repair([(-16.24, -12174.0, 3796), (27.0, 0.0, 0)], 26.3, env="set ::env(OT_HOLD_FLOOD_MET_FIRST) 0")
        self.assertNotIn("-hold_margin 0.0", " ".join(calls))
        self.assertIn("-hold_margin 26.3", calls[1])


class ShipFhTests(unittest.TestCase):
    def test_ship_refreshes_flowhold_snapshot(self):
        # drive-2155: hold_corners_patch.py re-copies {FH}/tools/orfs_hold_mm.* over the shipped helpers; the launch
        # env must bring the FH snapshot up to the loop's helper first
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as t:
            run, fh = Path(t) / "run", Path(t) / "fh"
            for d in (run / "cl", run / "src/tools", fh / "tools"):
                d.mkdir(parents=True)
            (run / "cl/orfs_hold_mm.py").write_text("new py")
            (run / "cl/orfs_hold_mm.tcl").write_text("new tcl")
            (fh / "tools/orfs_hold_mm.py").write_text("stale py")
            (fh / "tools/closure_loop").mkdir()
            (fh / "tools/closure_loop/h1_patch.py").write_text("stale h1")
            (run / "cl/h1_patch.py").write_text("new h1")
            (run / "cl/hold_corners_patch.py").write_text("new hcp")
            ttb = Path(t) / "ttb"
            (ttb / "physical/common_flow").mkdir(parents=True)
            (ttb / "physical/common_flow/link_budget_consistent.sdc").write_text("stale lbc")
            (run / "cl/link_budget_consistent.sdc").write_text("new lbc")
            with patch.object(cl, "SNAPSHOT_REFRESH", (((str(fh), str(Path(t) / "absent")), cl.FH_FILES),
                                                       ((str(ttb),), cl.TTB_FILES))):
                env = cl.fp_lint_env(dict(run=str(run), spec={}), "x", lint=False)
            subprocess.run(["bash", "-c", env], check=True)
            self.assertEqual((fh / "tools/orfs_hold_mm.py").read_text(), "new py")
            self.assertEqual((fh / "tools/orfs_hold_mm.tcl").read_text(), "new tcl")
            self.assertEqual((run / "src/tools/orfs_hold_mm.tcl").read_text(), "new tcl")
            self.assertEqual((ttb / "physical/common_flow/link_budget_consistent.sdc").read_text(), "new lbc")
            self.assertEqual((fh / "tools/closure_loop/h1_patch.py").read_text(), "new h1")
            self.assertEqual((fh / "tools/closure_loop/hold_corners_patch.py").read_text(), "new hcp")
            self.assertEqual(sorted(x.name for x in (fh / "tools").iterdir()), ["closure_loop", "orfs_hold_mm.py", "orfs_hold_mm.tcl"])
            self.assertFalse(any(x.name.startswith(".") for x in (fh / "tools/closure_loop").iterdir()))


class AbcNoDchTests(unittest.TestCase):
    def test_no_dch_only_when_asked(self):
        import sys
        import tempfile
        from pathlib import Path
        sys.path.insert(0, str(cl.HERE.parent))
        import orfs_hold_mm as m
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "abc_speed.script").write_text("&get -n\n&st\n&dch\n&nf\n&synch2\n")
            (d / "abc_area.script").write_text("&get -n\n&dch -f\n&nf\n")
            self.assertEqual(m.patch_abc_no_dch(d, {}), "off")
            self.assertIn("&dch", (d / "abc_speed.script").read_text())
            m.patch_abc_no_dch(d, {"OT_ABC_NO_DCH": "1"})
            self.assertEqual((d / "abc_speed.script").read_text(), "&get -n\n&st\n&synch2\n&nf\n&synch2\n")
            self.assertNotIn("&dch", (d / "abc_area.script").read_text())
        self.assertIn("-e OT_ABC_NO_DCH", cl.DOCKER_SHIM)


class HmEventTests(unittest.TestCase):
    def test_lines_and_dedup(self):
        rpt = "OT_HM_AUTO stage=cts HM auto-reduced 50->10: 72493 endpoints in margin (worst FF hold 2.85)\n"
        self.assertEqual(cl.hm_auto_lines(rpt), ["stage=cts HM auto-reduced 50->10: 72493 endpoints in margin (worst FF hold 2.85)"])
        j = dict(name="x", host="h", run="/r", attempt=1)
        with patch.object(cl, "ssh", Mock(return_value=Mock(stdout=rpt))), patch.object(cl, "log"):
            cl.hm_auto_events(j)
            cl.hm_auto_events(j)
        self.assertEqual(len([e for e in j["events"] if "HM auto-reduced 50->10" in e]), 1)


if __name__ == "__main__":
    unittest.main()
