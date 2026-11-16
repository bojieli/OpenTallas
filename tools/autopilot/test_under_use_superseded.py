import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unittest
import under_use as UU

CFG = {"dies": {"s81": {"event": "e2"}}}


class Superseded(unittest.TestCase):
    ITEMS = {
        "a": {"die": "s81", "item": "t1", "status": "ENQUEUED", "event": "e2", "q_status": "FAIL"},
        "b": {"die": "s81", "item": "t2", "status": "ENQUEUED", "event": "e1", "q_status": "FAIL"},
        "c": {"die": "s81", "item": "t3", "status": "ENQUEUED", "event": "e1", "q_status": "RUNNING"},
    }

    def test_only_current_event_rows_counted_by_queue_status(self):
        c = UU.hold_counts(self.ITEMS, CFG)
        self.assertEqual(c["gate:q_fail"], 1)
        self.assertEqual(c["superseded"], 2)

    def test_line_reports_superseded_apart_and_never_posts_them(self):
        s = UU.line("", self.ITEMS, CFG)
        self.assertIn("rows not launching 1: gate:q_fail=1", s)
        self.assertTrue(s.endswith("retire or relaunch) 2"), s)
        st, cl = {}, UU.row_classes(self.ITEMS, CFG)
        for t in range(4):
            due = UU.track(st, cl, t)
        self.assertNotIn("superseded", st["posted"])
