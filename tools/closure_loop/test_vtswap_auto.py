"""merge-eco 2026-10-09: the VT-swap setup ECO is the loop's automatic ECO stage for a thin TT setup miss
(TT in [-45, 0), FF >= 0, DRC 0) before NEEDS_RTL; a miss at the first target re-runs once at the next target."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl


def fleet():
    f = Mock()
    f.fits.return_value = (True, "ok")
    return f


class VtswapAutoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(cl, "STATE", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.j = dict(name="vt", status="READY", host="host", run="/run", attempt=1, stage_idx=0, benches={},
                      spec={"block": "blk", "stages": {}, "verdict": {"macros": [], "corner_sta": "{RUN}/routes/x/corner_sta.json"}, "source": {"commit": "abc"}}, events=[])
        self.m = dict(ss_ps=-12.53, ff_ps=18.6, drc=0, post_sdc=["physical/common_flow/io_ref_routed.sdc"],
                      setup_corner="tt", sdc_name="6_final.sdc", orfs_dir="/run/routes/x/work/orfs")

    def launch(self, m=None):
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "experiment"), patch.object(cl, "ledger"):
            self.assertTrue(cl.start_vtswap_eco(self.j, fleet(), m or self.m))
        return ls.call_args.args[2]

    def test_eligibility_window(self):
        ok = lambda **kw: cl.vtswap_eligible(self.j, dict(self.m, **kw))  # noqa: E731
        self.assertTrue(ok())
        self.assertTrue(ok(ss_ps=-45.0))
        self.assertFalse(ok(ss_ps=-45.01))          # deeper misses are RTL work
        self.assertFalse(ok(ss_ps=0.0))             # not a miss
        self.assertFalse(ok(ff_ps=-0.5))            # hold miss: the hold ECO's job
        self.assertFalse(ok(drc=3))
        self.assertFalse(ok(errors=["x"]))
        self.assertFalse(cl.vtswap_eligible(self.j, self.m, failed=["lef_check"]))
        self.assertFalse(cl.vtswap_eligible(self.j, self.m, benches_ok=False))

    def test_spec_can_turn_it_off(self):
        self.j["spec"]["hold_eco"] = {"vtswap": False}
        self.assertFalse(cl.vtswap_eligible(self.j, self.m))
        self.j["spec"]["hold_eco"] = {"enabled": False}
        self.assertFalse(cl.vtswap_eligible(self.j, self.m))

    def test_not_after_a_hold_eco_or_an_installed_eco(self):
        self.j["eco"] = dict(tried=True, out="/run/cl/eco")
        self.assertFalse(cl.vtswap_eligible(self.j, self.m))
        self.j["eco"] = dict(tried=True, kind="vtswap", installed="now")
        self.assertFalse(cl.vtswap_eligible(self.j, self.m))

    def test_first_launch_command(self):
        cmd = self.launch()
        self.assertIn("bash {CL}/vtswap_eco.sh /rb /ob /run/cl/eco-vtswap-t10 blk", cmd)
        for s in ("TARGET=10", "CAP_PCT=2", "DRC0=0", "SETUP_LIB=TT", "SDC_NAME=6_final.sdc",
                  "ORFS_W18=/run/routes/x/work/orfs", "physical/common_flow/io_ref_routed.sdc"):
            self.assertIn(s, cmd)
        self.assertEqual((self.j["status"], self.j["stage_key"], self.j["attempt"]), ("ECO", "hold_eco", 1))
        self.assertEqual(self.j["eco"]["kind"], "vtswap")
        self.assertEqual(self.j["eco"]["pre"], dict(ss_ps=-12.53, ff_ps=18.6))
        self.assertIn("vtswap_eco.sh", cl.HELPERS)
        self.assertIn("vtswap_eco.tcl", cl.HELPERS)
        for h in ("vtswap_eco.sh", "vtswap_eco.tcl"):
            self.assertTrue((cl.HERE / h).exists())

    def test_ladder_then_needs_rtl(self):
        self.launch()
        self.assertTrue(cl.vtswap_eligible(self.j, self.m))
        cmd = self.launch()
        self.assertIn("TARGET=5 ", cmd)
        self.assertIn("/run/cl/eco-vtswap-t5-r2", cmd)
        self.assertEqual(self.j["attempt"], 2)             # fresh hold_eco.a2 tag; a1 stays as evidence
        self.assertEqual([e["target_ps"] for e in self.j["eco_history"]], [10.0])
        self.assertFalse(cl.vtswap_eligible(self.j, self.m))   # both targets used -> NEEDS_RTL path

    def test_capacity_wait_stays_at_verdict(self):
        f = Mock()
        f.fits.return_value = (False, "busy")
        with patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "launch_stage") as ls:
            self.assertTrue(cl.start_vtswap_eco(self.j, f, self.m))
        ls.assert_not_called()
        self.assertEqual(self.j["status"], "READY")
        self.assertNotIn("eco", self.j)

    def _complete(self, res, rc=0):
        self.j["metrics"] = self.m
        self.j["failed_checks"] = []
        with patch.object(cl, "bench_track", return_value=True), patch.object(cl, "cal_track"), \
                patch.object(cl, "poll_stage", return_value=("DONE", rc)), \
                patch.object(cl, "ssh", return_value=Mock(stdout=json.dumps(res))), \
                patch.object(cl, "eco_paths", return_value=("/rb", "/ob")), patch.object(cl, "ship_helpers"), \
                patch.object(cl, "launch_stage") as ls, patch.object(cl, "experiment"), patch.object(cl, "ledger"), \
                patch.object(cl, "summarize_failure", return_value=False), patch.object(cl, "finish") as fin, \
                patch.object(cl, "failure_text", return_value="2026-10-09 NEEDS_RTL: x"):
            cl.step(self.j, fleet())
        return ls, fin

    def test_miss_at_10_relaunches_at_5_then_needs_rtl(self):
        self.launch()
        miss = dict(tt_ps=4.36, ss_ps=4.36, ff_ps=18.6, drc=0, errors=["LVT 2.004 % over the 2.0 % cap"])
        ls, fin = self._complete(miss)
        fin.assert_not_called()
        self.assertIn("TARGET=5 ", ls.call_args.args[2])
        self.assertEqual(self.j["status"], "ECO")
        ls, fin = self._complete(miss)
        ls.assert_not_called()
        self.assertEqual(fin.call_args.args[1], "NEEDS_RTL")

    def test_pass_installs(self):
        self.launch()
        ok = dict(tt_ps=7.75, ss_ps=7.75, ff_ps=18.6, drc=0, errors=[], cells_added=0)
        ls, fin = self._complete(ok)
        fin.assert_not_called()
        self.assertEqual(ls.call_args.args[1]["kind"], "eco_install")
        self.assertEqual(self.j["status"], "ECO_INSTALL")

    def test_verdict_launches_vtswap_before_needs_rtl(self):
        m = dict(self.m)
        with patch.object(cl, "adoption_held", return_value=False), patch.object(cl, "get_metrics", return_value=m), \
                patch.object(cl, "precollect_cmd", return_value=None), patch.object(cl, "routed_ioref", return_value=None), \
                patch.object(cl, "measured_resta", return_value=None), patch.object(cl, "cal_reroute", return_value=False), \
                patch.object(cl, "benches_done", return_value=True), patch.object(cl, "start_hold_eco") as hold, \
                patch.object(cl, "start_vtswap_eco", return_value=True) as vt, patch.object(cl, "finish") as fin:
            cl.do_verdict(self.j, fleet(), [])
        hold.assert_not_called()
        vt.assert_called_once()
        fin.assert_not_called()


if __name__ == "__main__":
    unittest.main()
