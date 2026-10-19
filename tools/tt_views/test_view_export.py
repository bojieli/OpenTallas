#!/usr/bin/env python3
"""view_export constraint sequence = the routed verdict's (export-sdc 2026-10-13).

Unit tests need nothing.  The re-export test needs docker and a CLOSED closure-loop route on this host:

    OT_VIEW_EXPORT_ORFS=<RUN>/routes/<LABEL>/work/orfs OT_VIEW_EXPORT_NAME=<block> [OT_VIEW_EXPORT_OUT=<scratch dir>]
    [OT_VIEW_EXPORT_MACRO_VIEWS=dir:dir] python3 tools/tt_views/test_view_export.py

It re-exports the route's 6_final ODB at TT and FF and requires the export session's TT setup / FF hold slack to equal
the route's routed_ioref verdict within 0.05 ps (reference: s81su_smt_hb1_ref-v2-hb1-ab43f2fe0 on ot-epyc1tb, verdict
TT +11.51 / FF +3.66; the kit-SDC-instead-of-routed-SDC export read FF -19.69).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import view_export as ve  # noqa: E402

NICK = "results/asap7/blk/base"
MEAS = """read_lef /p/tech.lef
read_liberty /p/x_{C}.lib
read_db /work/%s/6_final.odb
read_sdc /work/%s/6_final.sdc
read_spef /work/%s/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/k/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_REGS [llength [all_registers]]"
if {[llength [all_clocks]]} { puts "OT_REGS_CLOCKED 1" } else { puts "OT_REGS_CLOCKED 0" }
puts "OT_CORNER {c}"
puts "OT_WS [sta::worst_slack_cmd max]"
""" % (NICK, NICK, NICK)


def mkrun(root, eco=None, json_orfs=False):
    """a closure-loop run tree: route ORFS (+ optional hold-ECO ORFS with other content) and a routed_ioref verdict"""
    run = root / "run"
    orfs = run / "routes/L/work/orfs"
    for d, tag in [(orfs, "route")] + ([(run / "cl/eco/orfs", eco)] if eco else []):
        (d / NICK).mkdir(parents=True)
        for n in ("6_final.odb", "6_final.spef", "6_final.sdc"):
            (d / NICK / n).write_text(f"{n} of {tag}\n")
    for f in ("physical/ref_tile/k/signoff.sdc", "physical/common_flow/io_ref_routed.sdc"):
        (run / "src" / f).parent.mkdir(parents=True, exist_ok=True)
        (run / "src" / f).write_text(f + "\n")
    meas = run / "cl/routed_ioref.a1_meas"
    meas.mkdir(parents=True, exist_ok=True)
    (meas / "app0_io_ref_routed.sdc").write_text("ioref\n")
    for c, lab in (("ss", "tt"), ("ff", "ff")):
        (meas / f"meas_{c}.tcl").write_text(MEAS.replace("{C}", lab.upper()).replace("{c}", lab))
    res = dict(setup_tt=dict(worst_slack_ps=11.51, errors=[], rc=0), hold_ff=dict(worst_slack_ps=3.66, errors=[], rc=0))
    if json_orfs:
        res["orfs"] = str(orfs)
    (run / "cl/routed_ioref.a1.json").write_text(json.dumps(res))
    return run, orfs


class Sequence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_section_is_the_verdict_order(self):
        sec = ve.verdict_section(MEAS)
        self.assertEqual([l.split()[0] for l in sec],
                         ["read_db", "read_sdc", "read_spef", "set_propagated_clock", "read_sdc", "read_sdc", "read_sdc"])
        self.assertTrue(sec[1].endswith("/6_final.sdc") and sec[-1] == "read_sdc /meas/app0_io_ref_routed.sdc")
        with self.assertRaises(ve.VerdictError):
            ve.verdict_section("read_db x\nread_spef y\n")

    def test_discovery_and_replay_roots(self):
        run, orfs = mkrun(self.tmp)
        vj = ve.find_verdict(orfs)
        self.assertEqual(vj, (run / "cl/routed_ioref.a1.json").resolve())
        vd = ve.load_verdict(vj, orfs, orfs / NICK)
        self.assertEqual(vd["expect"], {"tt": 11.51, "ff": 3.66})
        self.assertEqual(vd["work"], orfs.resolve())
        self.assertEqual(vd["sec"]["ff"][1], f"read_sdc /work/{NICK}/6_final.sdc")
        self.assertIn("/src/physical/ref_tile/k/signoff.sdc", vd["files"])
        self.assertIsNone(ve.find_verdict(self.tmp / "a/b/c/d/orfs"))

    def test_installed_eco_dir_is_the_verdict_dir(self):
        # ECO installed: its odb / spef were copied into the route base, the verdict was timed in the ECO dir
        run, orfs = mkrun(self.tmp, eco="eco")
        for n in ("6_final.odb", "6_final.spef"):
            shutil.copy(run / "cl/eco/orfs" / NICK / n, orfs / NICK / n)
        vd = ve.load_verdict(ve.find_verdict(orfs), orfs, orfs / NICK)
        self.assertEqual(vd["work"], (run / "cl/eco/orfs").resolve())

    def test_untried_eco_dir_is_not_used(self):
        run, orfs = mkrun(self.tmp, eco="eco-not-installed")
        vd = ve.load_verdict(ve.find_verdict(orfs), orfs, orfs / NICK)
        self.assertEqual(vd["work"], orfs.resolve())

    def test_stale_verdict_is_refused(self):
        run, orfs = mkrun(self.tmp, json_orfs=True)
        (orfs / NICK / "6_final.odb").write_text("a later ECO\n")
        other = self.tmp / "base"
        other.mkdir()
        (other / "6_final.odb").write_text("exported db\n")
        (other / "6_final.spef").write_text("6_final.spef of route\n")
        with self.assertRaises(ve.VerdictError):
            ve.load_verdict(ve.find_verdict(orfs), orfs, other)

    def test_unclean_verdict_is_refused(self):
        run, orfs = mkrun(self.tmp)
        vj = run / "cl/routed_ioref.a1.json"
        d = json.loads(vj.read_text())
        d["hold_ff"]["errors"] = ["[ERROR STA-1]"]
        vj.write_text(json.dumps(d))
        with self.assertRaises(ve.VerdictError):
            ve.load_verdict(vj, orfs, orfs / NICK)

    def mkjob(self, ioref=True):
        """an ARCHIVED legacy-lane run: job.json + run/cl (no verdict Tcl), job commit tree with the post-SDCs"""
        ar, src = self.tmp / "ar", self.tmp / "src"
        (ar / "run/cl").mkdir(parents=True)
        for f in ("physical/k/signoff_unc60.sdc", "physical/common_flow/io_ref_routed.sdc"):
            (src / f).parent.mkdir(parents=True, exist_ok=True)
            (src / f).write_text(f + "\n")
        (ar / "run/cl/io_ref_routed.sdc").write_text("loop copy\n")
        (ar / "job.json").write_text(json.dumps(dict(name="j", spec=dict(source=dict(commit="abc")), metrics=dict(
            sdc_name="6_final.sdc", post_sdc=["physical/k/signoff_unc60.sdc", "physical/common_flow/io_ref_routed.sdc"],
            setup_post_sdc=[], setup_corner="tt", ss_ps=7.7, ff_ps=18.5))))
        r = dict(appended=["/host/run/cl/io_ref_routed.sdc"], inserted=[], replaced={},
                 setup_tt=dict(worst_slack_ps=7.75, errors=[]), hold_ff=dict(worst_slack_ps=18.6, errors=[]))
        if not ioref:
            r["setup_tt"] = dict(error="no w18_sta_ss.tcl")
        (ar / "run/cl/routed_ioref.a2.json").write_text(json.dumps(r))
        return ar, src

    def test_job_replay_is_the_jobs_post_sdc_order(self):
        ar, src = self.mkjob()
        jb = ve.load_job(ar / "job.json", src, None, NICK)
        self.assertEqual(jb["expect"], {"tt": 7.75, "ff": 18.6})
        self.assertEqual(jb["seq"]["ss"], [
            f"read_db /in/{NICK}/6_final.odb", f"read_sdc /in/{NICK}/6_final.sdc", f"read_spef /in/{NICK}/6_final.spef",
            "set_propagated_clock [all_clocks]", "read_sdc /src/physical/k/signoff_unc60.sdc",
            "read_sdc /src/physical/common_flow/io_ref_routed.sdc", "read_sdc /cl/io_ref_routed.sdc"])
        self.assertEqual(jb["seq"]["ss"], jb["seq"]["ff"])

    def test_job_replay_without_a_clean_ioref_uses_the_metrics(self):
        ar, src = self.mkjob(ioref=False)
        jb = ve.load_job(ar / "job.json", src, None, NICK)
        self.assertEqual(jb["expect"], {"tt": 7.7, "ff": 18.5})
        self.assertNotIn("read_sdc /cl/io_ref_routed.sdc", jb["seq"]["ss"])     # nothing was appended to that verdict

    def test_job_replay_refuses_a_missing_post_sdc(self):
        ar, src = self.mkjob()
        (src / "physical/k/signoff_unc60.sdc").unlink()
        with self.assertRaises(ve.VerdictError):
            ve.load_job(ar / "job.json", src, None, NICK)

    def test_job_replay_keeps_original_extra_sdc_before_post_sdc(self):
        ar, src = self.mkjob()
        extra = ar / "original_extra.sdc"
        extra.write_text("create_clock -name core_clk -period 1024 [get_ports clk]\n")
        jb = ve.load_job(ar / "job.json", src, None, NICK, extra)
        for c in ("ss", "ff"):
            self.assertEqual(jb["seq"][c][4], "read_sdc /job_extra.sdc")
            self.assertEqual(jb["seq"][c][5], "read_sdc /src/physical/k/signoff_unc60.sdc")
        self.assertEqual(jb["files"]["/job_extra.sdc"]["host"], str(extra))
        self.assertEqual(jb["expect"], {"tt": 7.75, "ff": 18.6})

    def test_job_replay_refuses_missing_original_extra_sdc(self):
        ar, src = self.mkjob()
        with self.assertRaises(ve.VerdictError):
            ve.load_job(ar / "job.json", src, None, NICK, ar / "missing.sdc")

    def test_ws(self):
        self.assertEqual(ve.ws_ps("OT_WS max 1.15e-11 min -2e-12"), (11.5, -2.0))


# RLYH0-NE 2026-10-19: qfd_rlyh0_128_NE_65x30 east pin column (default closing-bloat abstract vs exact shapes)
LEF_HEAD = """VERSION 5.8 ;
MACRO t
  SIZE 64.776 BY 30.216 ;
  PIN b[115]
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  64.692 11.76 64.776 11.784 ;
    END
  END b[115]
  PIN b[116]
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  64.692 11.856 64.776 11.88 ;
    END
  END b[116]
  OBS
    LAYER M4 ;
"""
CLOSED_OBS = "     RECT  64.716 11.808 64.757 12.792 ;\n  END\nEND t\n"   # merged landings: wide, 0.024 from b[115]
EXACT_OBS = "     RECT  64.716 11.808 64.757 11.832 ;\n  END\nEND t\n"   # the real min-width landing


class ExactAbstract(unittest.TestCase):
    def run_choose(self, default_obs, exact_obs):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "t.lef").write_text(LEF_HEAD + default_obs)

            def fake_run(cmd, **kw):
                calls.append(cmd)
                (out / f"t{ve.EXACT_LEF_SUFFIX}").write_text(LEF_HEAD + exact_obs)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            real, ve.subprocess.run = ve.subprocess.run, fake_run
            try:
                rec = ve.choose_abstract(out, "t", out, "img")
            finally:
                ve.subprocess.run = real
            tcl = (out / "export_exact_abstract.tcl").read_text() if calls else ""
            return rec, (out / "t.lef").read_text(), calls, (out / f"t{ve.EXACT_LEF_SUFFIX}").exists(), tcl

    def test_clean_default_kept_without_extra_session(self):
        rec, lef, calls, side, tcl = self.run_choose(EXACT_OBS, EXACT_OBS)
        self.assertEqual((rec["mode"], rec["default_pin_access_violations"], calls, side), ("default", 0, [], False))

    def test_blocked_pin_takes_exact_abstract(self):
        rec, lef, calls, side, tcl = self.run_choose(CLOSED_OBS, EXACT_OBS)
        self.assertEqual((rec["mode"], rec["default_pin_access_violations"], rec["exact_pin_access_violations"]),
                         ("exact", 1, 0))
        self.assertIn("11.832", lef)
        self.assertIn("write_abstract_lef -bloat_factor 0", tcl)
        self.assertFalse(side)

    def test_exact_no_better_keeps_default(self):
        rec, lef, calls, side, tcl = self.run_choose(CLOSED_OBS, CLOSED_OBS)
        self.assertEqual((rec["mode"], len(calls), side), ("default", 1, False))
        self.assertIn("12.792", lef)


# TW3-LGTAP 2026-10-19: hbm_sfu_lg_pair_tap_leaf top face -- the default abstract's M5 edge band OVERLAPS the pins (0
# raw violations), the finalize band carve leaves 0.6 x 0.036 slivers 0.048 from the next pin (child_lint (i) FAIL)
BAND_HEAD = """VERSION 5.8 ;
MACRO t
  SIZE 10 BY 10 ;
""" + "".join(f"""  PIN p{i}
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  {x:.3f} 9.916 {x + 0.024:.3f} 10 ;
    END
  END p{i}
""" for i, x in enumerate((1.0, 1.048, 1.672))) + """  OBS
    LAYER M5 ;
"""
BAND_OBS = "     RECT  0.5 9 3 9.952 ;\n  END\nEND t\n"
BAND_EXACT_OBS = "     RECT  1 9 1.024 9.952 ;\n     RECT  1.048 9 1.072 9.952 ;\n     RECT  1.672 9 1.696 9.952 ;\n  END\nEND t\n"


class ExactAbstractAfterFinalize(unittest.TestCase):
    def test_band_carve_slivers_take_exact_abstract(self):
        aps = ve.pin_access_violations
        self.assertEqual(len(aps(BAND_HEAD + BAND_EXACT_OBS)), 0)
        bad = aps(BAND_HEAD + BAND_OBS)
        self.assertTrue(bad and bad[0][2] == 0.048, bad)
        calls = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "t.lef").write_text(BAND_HEAD + BAND_OBS)

            def fake_run(cmd, **kw):
                calls.append(cmd)
                (out / f"t{ve.EXACT_LEF_SUFFIX}").write_text(BAND_HEAD + BAND_EXACT_OBS)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            real, ve.subprocess.run = ve.subprocess.run, fake_run
            try:
                rec = ve.choose_abstract(out, "t", out, "img")
            finally:
                ve.subprocess.run = real
            self.assertEqual((rec["mode"], rec["exact_pin_access_violations"], len(calls)), ("exact", 0, 1))
            self.assertNotIn("0.5 9 3 9.952", (out / "t.lef").read_text())


    def test_big_exact_abstract_patched_in_pin_windows_only(self):
        # a huge exact LEF (1.13 M RECTs on the real tile) is never judged whole: its shapes go in only inside the pin
        # windows; the default band outside the windows stays, the real pin wires come back
        calls = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "t.lef").write_text(BAND_HEAD + BAND_OBS)

            def fake_run(cmd, **kw):
                calls.append(cmd)
                (out / f"t{ve.EXACT_LEF_SUFFIX}").write_text(BAND_HEAD + BAND_EXACT_OBS)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            real, ve.subprocess.run = ve.subprocess.run, fake_run
            cap, ve.EXACT_FULL_MAX_RECTS = ve.EXACT_FULL_MAX_RECTS, 2
            try:
                rec = ve.choose_abstract(out, "t", out, "img")
            finally:
                ve.subprocess.run, ve.EXACT_FULL_MAX_RECTS = real, cap
            lef = (out / "t.lef").read_text()
            self.assertEqual((rec["mode"], rec["exact_pin_access_violations"], rec["window_pin_access_violations"]),
                             ("exact_windows", None, 0))
            self.assertEqual(rec["window_patch"]["windows"], 3)
            self.assertIn("RECT  1 9.916 1.024 9.952 ;", lef)      # p0's own wire, clipped to its window
            self.assertIn("RECT  1.768 9.916 3 9.952 ;", lef)    # default band beyond p2's window kept
            self.assertEqual(ve.pin_access_violations(lef), [])
            self.assertFalse((out / f"t{ve.EXACT_LEF_SUFFIX}").exists())


@unittest.skipUnless(os.environ.get("OT_VIEW_EXPORT_ORFS") and shutil.which("docker"),
                     "set OT_VIEW_EXPORT_ORFS / OT_VIEW_EXPORT_NAME to a closed loop route on this host")
class ReexportMatchesVerdict(unittest.TestCase):
    def test_tt_ff_match_the_routed_verdict(self):
        orfs = Path(os.environ["OT_VIEW_EXPORT_ORFS"])
        out = Path(os.environ.get("OT_VIEW_EXPORT_OUT") or tempfile.mkdtemp())
        vj = ve.find_verdict(orfs.resolve())
        self.assertIsNotNone(vj, "the route has no routed_ioref verdict")
        want = json.loads(vj.read_text())
        cmd = [sys.executable, str(HERE / "view_export.py"), "--orfs-dir", str(orfs), "--name",
               os.environ["OT_VIEW_EXPORT_NAME"], "--out", str(out), "--corners", "tt,ff", "--tmp-dir", str(out / "tmp")]
        for d in filter(None, os.environ.get("OT_VIEW_EXPORT_MACRO_VIEWS", "").split(":")):
            cmd += ["--macro-view", d]
        rc = subprocess.run(cmd).returncode
        rec = json.loads((out / "abstract.json").read_text())
        chk = rec["verdict"]["check"]
        print("EXPORT_VS_VERDICT", json.dumps(chk))
        for c, key in (("tt", "setup_tt"), ("ff", "hold_ff")):
            self.assertEqual(rec["sdc_sequence"][c]["mode"], "verdict")
            self.assertAlmostEqual(chk[c]["export_ps"], want[key]["worst_slack_ps"], delta=0.055)
            self.assertTrue(chk[c]["ok"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
