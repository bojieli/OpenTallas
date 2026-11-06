"""Current row identity, actual terminal jobs and explicit class approvals drive recovery."""
import unittest

import wave_reconcile as R


class ReconcileTest(unittest.TestCase):
    def setUp(self):
        self.row = {"die": "s81", "item": "station", "attempt": 9, "block_sha": "a" * 64,
                    "q_id": "dead", "q_status": "RUNNING", "status": "ENQUEUED", "updated": 10}
        self.wave = {"items": {"current": self.row}}
        self.jobs = {"jobs": {"dead": {"die": "s81", "type": "station", "status": "DONE-CRASH"}}}
        self.stages = [{"die": "s81", "item": "station", "block_sha": "a" * 12, "plan_current": "yes"}]
        self.config = {"dies": {"s81": {"hold_items": {"station": "old pilot ownership hold"}}}}
        self.fix = {"die": "s81", "item": "station", "attempt": 9, "sha": "abcdef777",
                    "scope": "src", "reason": "existing source-insertion class fix", "live_checked": True,
                    "clear_hold": True}

    def report(self, **kwargs):
        return R.report(self.wave, self.jobs, self.config, self.stages, **kwargs)

    def test_terminal_cache_report_does_not_blindly_retry(self):
        result = self.report()
        self.assertEqual(result["summary"]["current_terminal_caches"], 1)
        self.assertEqual(result["cache_updates"][0]["q_status"], "DONE-CRASH")
        self.assertEqual(result["recovery_rows"], [])
        self.assertEqual(self.row["q_status"], "RUNNING")  # reporting never writes live state

    def test_only_current_merged_explicitly_checked_fix_proposes_retry(self):
        old = dict(self.row, block_sha="b" * 64, q_id="older", status="CANCELLED")
        self.wave["items"]["superseded"] = old
        self.jobs["jobs"]["older"] = {"die": "s81", "type": "station", "status": "CANCELLED"}
        result = self.report(approvals=[self.fix], merged=lambda *args: True)
        self.assertEqual(result["summary"]["terminal_caches"], 2)
        self.assertEqual(len(result["recovery_rows"]), 1)
        self.assertIn("station@9", result["recovery_rows"][0])
        self.assertEqual(self.report(approvals=[self.fix])["recovery_rows"], [])
        unchecked = dict(self.fix, live_checked=False)
        self.assertEqual(self.report(approvals=[unchecked], merged=lambda *args: True)["recovery_rows"], [])

    def test_live_spilled_alternative_preserves_job_and_hold(self):
        self.jobs["jobs"]["spilled"] = {"die": "s81", "type": "station", "status": "RUNNING",
                                             "host": "epyc4", "ran_on": "intel1"}
        result = self.report(required_types={"s81": ["station"]}, approvals=[self.fix], merged=lambda *a: True)
        self.assertEqual(result["recovery_rows"], [])
        self.assertEqual(result["holds"][0]["live_alternatives"], ["spilled"])
        self.assertFalse(result["holds"][0]["clear_approved"])

    def test_ownership_hold_requires_actual_plan_membership_and_approval(self):
        self.stages = []  # a hold can predate a changed current block, so the stage cache has no row
        result = self.report(approvals=[self.fix], merged=lambda *a: True)
        self.assertIsNone(result["holds"][0]["required_type"])
        self.assertFalse(result["holds"][0]["clear_approved"])
        result = self.report(required_types={"s81": ["station"]}, approvals=[self.fix], merged=lambda *a: True)
        self.assertTrue(result["holds"][0]["clear_approved"])
        self.assertEqual(result["recovery_rows"], [])  # no current block identity: no retry suggestion

    def test_live_generation_without_ap_job_is_not_a_ghost(self):
        self.wave["items"]["generating"] = {"die": "s81", "item": "station", "status": "RUNNING"}
        result = self.report(approvals=[self.fix], merged=lambda *a: True)
        self.assertEqual(result["recovery_rows"], [])
        self.assertEqual(result["terminal_caches"][0]["live_alternatives"], ["wave:generating"])

    def test_completed_or_counted_work_is_preserved_even_with_fix_approval(self):
        for status, counted in (("SIGNED", []), ("DONE-CRASH", ["station"])):
            with self.subTest(status=status):
                self.jobs["jobs"]["dead"]["status"] = status
                self.config["dies"]["s81"]["counted_items"] = counted
                result = self.report(required_types={"s81": ["station"]},
                                     approvals=[self.fix], merged=lambda *a: True)
                self.assertEqual(result["recovery_rows"], [])
                self.assertTrue(result["terminal_caches"][0]["completed"])
                self.assertFalse(result["holds"][0]["clear_approved"])

    def test_pattern_hold_preserves_any_live_member(self):
        self.config["dies"]["s81"]["hold_items"] = {"stat*": "family form pending"}
        self.jobs["jobs"]["spilled"] = {"die": "s81", "type": "station", "status": "RUNNING"}
        result = self.report(required_types={"s81": ["station"]})
        self.assertTrue(result["holds"][0]["required_type"])
        self.assertEqual(result["holds"][0]["live_alternatives"], ["spilled"])
        self.assertFalse(result["holds"][0]["clear_approved"])


if __name__ == "__main__":
    unittest.main()
