import json
import tempfile
import time
import unittest
from pathlib import Path
import pending_actions as PA
import limit_outage as LO


class Pending(unittest.TestCase):
    def cfg(self):
        return {"dies": {"s81": {"src": "/old", "hold_items": {"*": "x", "k2": "y"}}}}

    def test_marker_gates_src_switch_and_hold_drop(self):
        m = Path(tempfile.mkdtemp()) / "marker.json"
        act = [{"id": "a1", "when": [{"json_eq": {"path": str(m), "key": "smoke.ok", "value": True}}],
                "do": [{"set": {"die": "s81", "key": "src", "value": "/new"}}, {"delete_hold": {"die": "s81", "key": "*"}}]}]
        c, logs = self.cfg(), []
        self.assertEqual(PA.apply_cfg(c, act, logs.append), [])
        self.assertEqual(c["dies"]["s81"]["src"], "/old")                      # marker absent: nothing
        m.write_text(json.dumps({"smoke": {"ok": True}}))
        self.assertEqual(PA.apply_cfg(c, act, logs.append), ["a1"])
        self.assertEqual((c["dies"]["s81"]["src"], list(c["dies"]["s81"]["hold_items"])), ("/new", ["k2"]))
        self.assertEqual(PA.apply_cfg(c, act, logs.append), ["a1"])            # idempotent
        self.assertEqual(len(logs), 2)

    def test_unknown_or_unreadable_condition_never_fires(self):
        self.assertFalse(PA.ready({"id": "x", "when": [{"bogus": 1}]}))
        self.assertFalse(PA.ready({"id": "x", "when": [{"exists": "/nonexistent/z"}]}))
        self.assertTrue(PA.ready({"id": "x", "when": []}))
        self.assertTrue(PA.ready({"id": "x", "when": [{"after": 1}]}, now=5))

    def test_relaunch_infra_once(self):
        st = {"items": {"a": {"die": "s81", "status": "FAIL", "class": "INFRA"}, "b": {"die": "s81", "status": "FAIL", "class": "PLAN"},
                        "c": {"die": "kv", "status": "FAIL", "class": "INFRA"}, "d": {"die": "s81", "status": "FAIL", "class": "INFRA", "blocked": "B"}}}
        act = [{"id": "r1", "when": [], "do": [{"relaunch_infra": {"die": "s81"}}]}]
        done = {}
        self.assertEqual(PA.apply_rows(st, act, done, lambda m: None, now=7), 1)
        self.assertEqual([k for k, r in st["items"].items() if r["status"] == "RETRY-INFRA"], ["a"])
        st["items"]["a"]["status"] = "FAIL"
        self.assertEqual(PA.apply_rows(st, act, done, lambda m: None, now=8), 0)   # ledger: once

    def test_bad_file_is_empty(self):
        self.assertEqual(PA.load("{not json"), [])
        self.assertEqual(PA.load('{"actions": [{"no_id": 1}]}'), [])


class Outage(unittest.TestCase):
    def coord(self, nlanes, now):
        c = Path(tempfile.mkdtemp())
        (c / "lanes").mkdir(); (c / "autopilot").mkdir()
        t = time.strftime("%Y-%m-%d %H:%M", time.localtime(now - 60))
        (c / "lanes/COORD-REVIEW-QUEUE.md").write_text("".join(f"- {t} PST READY [LANE{i} -> COORD] x\n" for i in range(nlanes)))
        (c / "autopilot/log.txt").write_text("x\n")
        (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"s81": {"hold_items": {"*": "h", "k": "h"}}}}))
        (c / "autopilot/pending_actions.json").write_text(json.dumps({"actions": [{"id": "a", "when": [], "do": [{"delete_hold": {"die": "s81", "key": "*"}}]}]}))
        return c

    def test_two_low_samples_declare_outage_and_start_tick_when_idle(self):
        now, started = time.time(), []
        c = self.coord(1, now)
        self.assertFalse(LO.run(c, now, start=lambda: started.append(1))[0])      # first low sample
        import os
        os.utime(c / "autopilot/log.txt", (now - 3000, now - 3000))
        out, msg = LO.run(c, now, start=lambda: started.append(1))
        self.assertTrue(out)
        self.assertEqual(started, [1])
        body = (c / "lanes/handoff/LIMIT-OUTAGE.md").read_text()
        self.assertIn("- a: when []", body)
        self.assertIn("- s81/k", body)
        self.assertNotIn("- s81/*", body)                                          # the hold with a pending action is not listed

    def test_enough_lanes_is_no_outage(self):
        now = time.time()
        c = self.coord(4, now)
        for _ in range(3):
            self.assertFalse(LO.run(c, now, start=lambda: self.fail("no start"))[0])
