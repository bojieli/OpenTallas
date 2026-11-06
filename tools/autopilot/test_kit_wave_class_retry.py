"""KW-RELAUNCH-1 11-05: a released retry of one class launches while a sibling class of the same parent is routing"""
import unittest

import kit_wave as KW

LIVE = "ap-3368eccf0362-a1 3368eccf0362; ot-run pid 407147 /x/items/t40__clb/attempt_6/gen/t40__clb"


class ClassRetryUnderRoutingParent(unittest.TestCase):
    def setUp(self):
        self.cfg = {"dies": {"d": {"event": "e", "retry": [],
                                   "take_states": ["NEEDS-KIT", "FIX", "GEOM-REQ", "KIT-PLACED", "REVIEW"]}}}
        self.names = {"t40__cla": "a" * 12, "t40__clb": "b" * 12, "t40__clc": "c" * 12}
        self.st = {"items": {
            KW.item_key("d", "e", "t40__cla", "a" * 12): dict(die="d", item="t40__cla", attempt=8, status="ENQUEUED",
                                                              q_status="FAIL", event="e"),
            KW.item_key("d", "e", "t40__clb", "b" * 12): dict(die="d", item="t40__clb", attempt=6, status="ENQUEUED",
                                                              q_status="RUNNING", event="e")}}

    def row(self, state="ROUTING", owner="KIT-WAVE-3", live=LIVE):
        return [dict(die="d", item="t40", kind="type", state=state, owner=owner, live_job=live, last_activity="",
                     next_step="", evidence="", default_owner="", replicas="1", members="")]

    def pick(self, rows, retry):
        self.cfg["dies"]["d"]["retry"] = retry
        picks, skip = KW.select(rows, self.cfg, "d", self.st, self.names)
        return sorted(p["item"] for p in picks), skip

    def test_released_class_launches_under_routing_parent(self):
        self.assertEqual(self.pick(self.row(), ["t40__cla@8"])[0], ["t40__cla"])

    def test_unreleased_and_new_classes_wait(self):
        # t40__clc has no record (new class): it still waits for the parent row to leave ROUTING
        self.assertEqual(self.pick(self.row(), [])[0], [])

    def test_other_lane_routing_parent_still_skipped(self):
        self.assertEqual(self.pick(self.row(owner="DIE-S81-65", live="ot-run pid 1 /lane/run"), ["t40__cla@8"])[0], [])

    def test_take_state_parent_unchanged(self):
        # REVIEW parent: normal path, the new class and the released class both launch
        self.assertEqual(self.pick(self.row(state="REVIEW", live="none"), ["t40__cla@8"])[0], ["t40__cla", "t40__clc"])


if __name__ == "__main__":
    unittest.main()
