"""DIE-HBM-97 11-10 (COORD ruling): GPL-1010 per-pass Nesterov cap with overflow > 0.1 -> STRUCTURAL gpl-noconverge"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_TMP = tempfile.TemporaryDirectory()
os.environ.setdefault("AP_DIR", _TMP.name)
os.environ.setdefault("AP_QUEUE_FILE", str(Path(_TMP.name) / "queue.tsv"))
os.environ.setdefault("AP_COORD_FILES", str(Path(_TMP.name) / "coord"))
os.environ.setdefault("AP_RELEASE_CACHE", str(Path(_TMP.name) / "release_cache.json"))
os.environ.setdefault("AP_OT_RUN_SIGNALS", str(Path(_TMP.name) / "no_signals.log"))
os.environ.setdefault("AP_WATCHDOG_LOG", str(Path(_TMP.name) / "no_watchdog.log"))
import kit_wave as KW  # noqa: E402
import autopilot as AP  # noqa: E402

HEAD = ("[INFO GPL-0084] ---- Execute Nesterov Global Placement.\n"
        "Iteration | Overflow |     HPWL (um) |  HPWL(%) |   Penalty | Group\n"
        "---------------------------------------------------------------\n")
CAP = ("[WARNING GPL-1010] GPL reached the maximum number of iterations for nesterov 5000. "
       "Placement may have failed to converge.\n[INFO GPL-1014] Final placement area: 19569.01 (+0.00%)\n")
CONVERGED = "[INFO GPL-1001] Global placement finished at iteration 468\n"


def rows(start, stop, ov_first, ov_last, step=10):
    n = max(1, (stop - start) // step)
    out = []
    for i, it in enumerate(range(start, stop + 1, step)):
        ov = ov_first + (ov_last - ov_first) * min(i, n) / n
        out.append(f"{it:>9} | {ov:8.4f} |  6.432818e+07 |   +0.02% |  2.47e+11 |      ")
    return "\n".join(out) + "\n"


def gp_log(passes):
    """passes: [(start, stop, ov_first, ov_last, capped)] -> a 3_3_place_gp log with one table per pass"""
    t = "global_placement -density 0.5 -routability_driven -timing_driven\n"
    for start, stop, a, b, capped in passes:
        t += HEAD + rows(start, stop, a, b)
        t += CAP if capped else CONVERGED
        t += "[INFO GPL-0087] Routability end iteration: increase inflation and revert back to snapshot.\n"
    return t


# kv_line vC: last row 4,990 at overflow ~0.370, then the flow went on into repair_design and DPL-0038
VC = gp_log([(0, 4990, 0.9853, 0.3704, True)])
DPL_TAIL = ("[INFO RSZ-0035] Inserted 459212 buffers in 210377 nets.\n"
            "[ERROR DPL-0038] Detailed placement failed: utilization 153% exceeds the core area.\n"
            "Error: detail_place.tcl, 12 DPL-0038\nmake: *** [Makefile:540: do-3_5_place_dp] Error 1\n"
            "ot-run: RAN on epyc7 (unit kwp-x): exit 2\nKW_PLACE_RC=2\n")


class GplCapParser(unittest.TestCase):
    def test_cap_at_037_is_noconverge(self):
        hit = KW.gpl_cap_noconverge(VC)
        self.assertIsNotNone(hit)
        self.assertIn("iteration 4990", hit)
        self.assertIn("overflow 0.370", hit)

    def test_cap_at_008_is_not(self):
        self.assertIsNone(KW.gpl_cap_noconverge(gp_log([(0, 4990, 0.98, 0.08, True)])))

    def test_no_cap_is_not(self):
        # converging peer (q_b011 468 rows at <= 0.1) and a high-overflow log without GPL-1010
        self.assertIsNone(KW.gpl_cap_noconverge(gp_log([(0, 460, 0.98, 0.099, False)])))
        self.assertIsNone(KW.gpl_cap_noconverge(gp_log([(0, 4990, 0.98, 0.45, False)])))

    def test_restart_first_capped_pass_above_limit_decides(self):
        # vB style: converged pass, a capped pass at 0.05 (not this class), then the first capped pass above 0.1
        # (cumulative counter far beyond 5,000) decides, not the later worse one
        log = gp_log([(0, 500, 0.98, 0.30, False), (510, 5500, 0.30, 0.05, True),
                      (5510, 225900, 0.50, 0.42, True), (225910, 230900, 0.6, 0.61, True)])
        hit = KW.gpl_cap_noconverge(log)
        self.assertIsNotNone(hit)
        self.assertIn("iteration 225900", hit)
        self.assertIn("overflow 0.420", hit)
        self.assertIn("capped pass 2", hit)

    def test_restart_all_capped_passes_below_limit(self):
        log = gp_log([(0, 4990, 0.98, 0.09, True), (5000, 9990, 0.4, 0.07, True)])
        self.assertIsNone(KW.gpl_cap_noconverge(log))

    def test_cap_line_without_a_row_is_not(self):
        self.assertIsNone(KW.gpl_cap_noconverge(CAP))


class KitWaveClassify(unittest.TestCase):
    def probe(self, log):
        """the after_place probe's awk on a real file -> its KW_GPL lines"""
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "3_3_place_gp.log"
            f.write_text(log)
            p = subprocess.run(["bash", "-c", f"{KW.GPL_PROBE_AWK} {f}"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout

    def test_place_fail_cap_037_is_structural(self):
        cls, why = KW.classify("place", DPL_TAIL + self.probe(VC))
        self.assertEqual(cls, "STRUCTURAL", why)
        self.assertIn("gpl-noconverge", why)
        self.assertIn("iteration 4990", why)
        self.assertIn("overflow 0.370", why)
        self.assertIn(cls, KW.CLASSES)

    def test_cap_wins_over_infra_exit(self):
        # the unit was then stopped from outside / OOM-killed in the resizer: the capped placement still decides
        t = DPL_TAIL.replace("exit 2", "exit 143") + "Killed\n" + self.probe(VC)
        self.assertEqual(KW.classify("place", t)[0], "STRUCTURAL")

    def test_place_fail_cap_008_is_not_structural(self):
        cls, why = KW.classify("place", DPL_TAIL + self.probe(gp_log([(0, 4990, 0.98, 0.08, True)])))
        self.assertNotEqual(cls, "STRUCTURAL", why)
        self.assertNotIn("gpl-noconverge", why)

    def test_place_fail_without_cap_is_not_structural(self):
        cls, why = KW.classify("place", DPL_TAIL + self.probe(gp_log([(0, 4990, 0.98, 0.45, False)])))
        self.assertNotEqual(cls, "STRUCTURAL", why)

    def test_restart_probe(self):
        log = gp_log([(0, 500, 0.98, 0.30, False), (510, 5500, 0.30, 0.05, True), (5510, 225900, 0.5, 0.42, True)])
        cls, why = KW.classify("place", DPL_TAIL + self.probe(log))
        self.assertEqual(cls, "STRUCTURAL", why)
        self.assertIn("iteration 225900", why)

    def test_other_stage_not_this_rule(self):
        cls, why = KW.classify("geom", "AUTO-GEOM FAIL grt=FAIL(3)\n" + self.probe(VC))
        self.assertNotIn("gpl-noconverge", why)


class AutopilotClassify(unittest.TestCase):
    def probe(self, log):
        with tempfile.TemporaryDirectory() as d:
            K = Path(d)
            (K / "config.mk").write_text("export DESIGN_NAME = x\n")
            b = K / "run/logs/asap7/x/base"
            b.mkdir(parents=True)
            (b / "3_3_place_gp.log").write_text(log)
            (b / "3_5_place_dp.log").write_text(DPL_TAIL)
            (K / "run_grt.log").write_text(log + DPL_TAIL)
            p = subprocess.run([sys.executable, "-c", AP.PROBE_CLASSIFY,
                                json.dumps({"kit": str(K), "since": 0, "goal": "grt"})], capture_output=True, text=True)
            self.assertIn("AP_JSON ", p.stdout, p.stderr)
            return json.loads(p.stdout.split("AP_JSON ", 1)[1])

    def test_vc_is_structural_gpl_noconverge(self):
        c = self.probe(VC)
        cls, kind, why = AP.classify(c, {"exit": 2})
        self.assertEqual((cls, kind), ("STRUCTURAL", "gpl-noconverge"), why)
        self.assertIn("iteration 4990", why)

    def test_cap_at_008_is_not(self):
        c = self.probe(gp_log([(0, 4990, 0.98, 0.08, True)]))
        self.assertNotEqual(AP.classify(c, {"exit": 2})[1], "gpl-noconverge")

    def test_no_cap_is_not(self):
        c = self.probe(gp_log([(0, 4990, 0.98, 0.45, False)]))
        self.assertNotIn("gpl_cap", c)
        self.assertNotEqual(AP.classify(c, {"exit": 2})[1], "gpl-noconverge")

    def test_restart(self):
        c = self.probe(gp_log([(0, 500, 0.98, 0.3, False), (510, 5500, 0.3, 0.05, True), (5510, 225900, 0.5, 0.42, True)]))
        cls, kind, why = AP.classify(c, {"exit": 2})
        self.assertEqual(kind, "gpl-noconverge", why)
        self.assertIn("iteration 225900", why)


if __name__ == "__main__":
    unittest.main()
