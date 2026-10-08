"""LOOP-GAPS 2026-10-08 regressions: ECO judged on the option-B line with the job's own sign-off SDCs, the smh piece
flow honouring the loop's hold margin, mutant benches that print FAIL but exit 0, retry output set aside."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl

sys.path.insert(0, str(cl.HERE.parent))
import hbm_accel_smh_physical as smh  # noqa: E402


class LoopGapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(cl, "STATE", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.j = dict(name="gap", status="READY", host="host", run="/run", attempt=1,
                      spec={"block": "blk", "stages": {}, "verdict": {}, "source": {"commit": "abc"}}, events=[])
        cl.save_job(self.j)

    # 1. hold ECO: sign-off SDC + setup-only measured neighbour clock, setup judged at TT
    def test_eco_uses_route_signoff_sdc_and_setup_post_sdc(self):
        m = dict(ss_ps=100.3, ff_ps=-18.0, post_sdc=[], sdc_name="6_signoff.sdc",
                 setup_post_sdc=["physical/common_flow/nbr_clk_measured.sdc"])
        fleet = Mock()
        fleet.fits.return_value = (True, "ok")
        with patch.object(cl, "eco_paths", return_value=("/route", "/route")), \
                patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage") as launch, \
                patch.object(cl, "experiment"):
            self.assertTrue(cl.start_hold_eco(self.j, fleet, m))
        cmd = launch.call_args.args[2]
        self.assertIn("SDC_NAME=6_signoff.sdc", cmd)
        self.assertIn("SETUP_POST_SDC=physical/common_flow/nbr_clk_measured.sdc", cmd)
        self.assertIn("SETUP_LIB=TT", cmd)
        self.assertEqual(self.j["eco"]["sdc_name"], "6_signoff.sdc")

    def test_eco_result_judged_at_tt(self):
        # m3f: TT +102.75 / FF +20.33 / DRC 0 passes even though an SS sensitivity is negative
        res = dict(ss_ps=102.75, tt_ps=102.75, ss_sensitivity_ps=-40.0, ff_ps=20.33, drc=0, errors=[])
        self.assertTrue(cl.eco_passes(res, 0))
        self.assertFalse(cl.eco_passes(dict(res, tt_ps=-1.0), 0))

    def test_hold_eco_refuses_missing_signoff_sdc(self):
        out = Path(self.tmp.name) / "eco"
        r = subprocess.run(["bash", str(cl.HERE / "hold_eco.sh"), "/nonexistent/route", "/nonexistent/ob", str(out), "blk"],
                           env={"PATH": "/usr/bin:/bin", "SDC_NAME": "6_signoff.sdc"}, capture_output=True, text=True,
                           cwd=self.tmp.name)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("sign-off SDC /nonexistent/ob/6_signoff.sdc missing", r.stdout)

    # 2. smh piece flow honours the loop HM (ns) + the 25 ps sign-off hold uncertainty
    def test_smh_hold_margin_follows_loop_hm(self):
        self.assertEqual(smh.loop_hold_margin("25", {"HM": "0.05"}), "75")
        self.assertEqual(smh.loop_hold_margin("25", {}), "25")
        self.assertEqual(smh.loop_hold_margin("100", {"HM": "0.05"}), "100")

    # 3. negative-control bench: the log's FAIL verdict counts regardless of rc
    def test_expected_fail_reads_log_regardless_of_rc(self):
        st = dict(expect="fail", fail_regex=None)
        self.assertTrue(cl.expected_fail_seen(st, 0, "running\nFAIL: mismatch at 12\n"))
        self.assertTrue(cl.expected_fail_seen(st, 1, "crash"))
        self.assertFalse(cl.expected_fail_seen(st, 0, "all PASS\n"))
        st = dict(expect="fail", fail_regex=r'"status": *"fail"')
        self.assertTrue(cl.expected_fail_seen(st, 0, '"status": "fail"'))
        self.assertFalse(cl.expected_fail_seen(st, 2, "Traceback"))

    # 4. same-host retry: the previous stage output is moved aside as <dir>.attemptN
    def test_retry_moves_previous_output_aside(self):
        run = Path(self.tmp.name) / "run"
        d = run / "routes" / cl.label("gap")
        (d / "prep").mkdir(parents=True)
        self.j.update(run=str(run), attempt=2)
        sh = cl.retry_aside(self.j, dict(kind="route", key="route"))
        subprocess.run(["bash", "-ec", sh], check=True)
        self.assertFalse(d.exists())
        self.assertTrue((run / "routes" / f"{cl.label('gap')}.attempt1" / "prep").is_dir())
        # an explicit spec out_dir is honoured for any stage kind
        o = run / "collect_out"
        o.mkdir()
        sh = cl.retry_aside(self.j, dict(kind="collect", key="collect", out_dir="{RUN}/collect_out"))
        subprocess.run(["bash", "-ec", sh], check=True)
        self.assertTrue((run / "collect_out.attempt1").is_dir())
        self.assertEqual(cl.retry_aside(self.j, dict(kind="bench", key="bench_x")), "")


if __name__ == "__main__":
    unittest.main()
