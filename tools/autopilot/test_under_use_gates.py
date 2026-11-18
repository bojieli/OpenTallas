import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unittest
import under_use as UU
import kit_wave as KW


class Gates(unittest.TestCase):
    ITEMS = {f"r{i}": {"die": "s81", "item": f"t{i}", "status": "ENQUEUED", "q_status": "FAIL"} for i in range(3)}
    ITEMS["d"] = {"die": "s81", "item": "td", "status": "ENQUEUED", "disk_wait": "x", "q_status": ""}
    ITEMS["n"] = {"die": "s81", "item": "tn", "status": "ENQUEUED"}

    def test_split_by_gate(self):
        c = UU.row_classes(self.ITEMS, {})
        self.assertEqual(sorted(set(c.values())), ["gate:disk_wait", "gate:q_fail", "gate:q_no_queue_status"])

    def test_needs_action_after_three_ticks_once_per_class(self):
        st, cl = {}, UU.row_classes(self.ITEMS, {})
        self.assertEqual(UU.track(st, cl, 1), {})
        self.assertEqual(UU.track(st, cl, 2), {})
        due = UU.track(st, cl, 3)
        self.assertEqual(due, {"gate:q_fail": 3, "gate:disk_wait": 1, "gate:q_no_queue_status": 1})
        self.assertEqual(UU.track(st, cl, 4), {})               # posted once
        UU.track(st, {}, 5)
        self.assertEqual(UU.track(st, cl, 6), {})               # recurrence counts from 1 again

    def test_class_change_resets_the_row(self):
        st = {}
        UU.track(st, {"a": "gate:q_fail"}, 1); UU.track(st, {"a": "gate:q_fail"}, 2)
        self.assertEqual(UU.track(st, {"a": "gate:disk_wait"}, 3), {})


class FailClosed(unittest.TestCase):
    def test_bind_probe_error_blocks(self):
        cfg = {"dies": {"qc": {"gen_host": "h", "src": "/s", "plan": "/p", "kit_rtl": {"mode": "bind", "bind_out": "/b"}}}}
        rows = [{"item": "x", "kind": "type"}]
        r = KW.bind_preflight(None, cfg, {}, "qc", rows, rpy=lambda *a, **k: {"error": "ssh down"})
        self.assertIn("BIND_PREFLIGHT_UNKNOWN", r["x"])
        st = {}
        KW.bind_preflight(None, cfg, st, "qc", rows, rpy=lambda *a, **k: {"error": "e"})
        self.assertEqual(st.get("bind_preflight"), {})         # not cached: retried next tick
