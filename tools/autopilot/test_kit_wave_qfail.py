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


if __name__ == "__main__":
    unittest.main()
