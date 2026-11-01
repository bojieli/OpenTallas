"""KIT-TRIAGE-1 11-01: a queue-FAILed (route / sign-off) wave kit relaunches only when its attempt is released"""
import unittest

import kit_wave as KW


class QueueFailRelaunch(unittest.TestCase):
    def setUp(self):
        self.cfg = {"dies": {"d": {"event": "e", "retry": []}}}
        self.rows = [dict(die="d", item="t1", kind="type", state="NEEDS-KIT", owner="KIT-WAVE", live_job="none",
                          last_activity="", next_step="", evidence="", default_owner="", replicas="1", members="")]

    def pick(self, q_status, retry):
        self.cfg["dies"]["d"]["retry"] = retry
        st = {"items": {KW.item_key("d", "e", "t1", "b" * 12): dict(die="d", item="t1", attempt=3, status="ENQUEUED",
                                                                     q_status=q_status, event="e")}}
        picks, skip = KW.select(self.rows, self.cfg, "d", st, {"t1": "b" * 12})
        return [p["item"] for p in picks], skip

    def test_queue_fail_released(self):
        self.assertEqual(self.pick("FAIL", ["t1@3"])[0], ["t1"])

    def test_queue_fail_not_released(self):
        picks, skip = self.pick("FAIL", [])
        self.assertEqual(picks, [])
        self.assertTrue(any("queue FAIL" in k for k in skip))

    def test_running_queue_job_never_relaunched(self):
        self.assertEqual(self.pick("RUNNING", ["t1@3"])[0], [])



class InfraBudget(unittest.TestCase):
    def test_budget_counts_since_design_verdict(self):
        cfg = {"dies": {"d": {"event": "e"}}, "infra_attempts": 3}
        rec = dict(die="d", event="e", attempt=5, infra_base=4, status="FAIL", **{"class": "INFRA"})
        self.assertTrue(KW.infra_relaunch_due(cfg, rec))
        self.assertFalse(KW.infra_relaunch_due(cfg, dict(rec, infra_base=1)))
        self.assertFalse(KW.infra_relaunch_due(cfg, dict(rec, infra_base=None, attempt=3)))

    def test_sigterm_is_infra(self):
        self.assertEqual(KW.classify("geom_run", "ot-run: RAN on localhost (unit x): exit 143\n")[0], "INFRA")



class LandingBand(unittest.TestCase):
    def test_landing_band_is_plan(self):
        c, why = KW.classify("gen", "Traceback\nValueError: svc_lo_dsdv_svc_rs__t7.hbm_i0: landing band absent\n")
        self.assertEqual(c, "PLAN")
        self.assertIn("hbm_i0", why)


if __name__ == "__main__":
    unittest.main()
