"""KW-FIX-35-K 11-08: cancel_superseded keeps an active row whose item is held (hold_items) or whose own plan block
is unchanged in the current plan; every other superseded active row is still stopped (COORD 11-01 18:3x)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import kit_wave as KW


class SupersedeKeep(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.stops, self.logs = [], []

        def sh(cmd, timeout=None, input=None):
            if input:
                return 0, json.dumps({"containers": [], "scopes": []}), ""
            self.stops.append(cmd[-1])
            return 0, "", ""
        self.AP = SimpleNamespace(DRY=False, log=self.logs.append, sh=sh, HUB_NAME="intel2")
        self.cur, self.old = "a" * 40, "b" * 40
        self.cfg = {"dies": {"d": {"plan": "/p.json", "event": "e2", "gen_host": "h",
                                   "hold_items": {"phy*": "in flight on the r8 plan, do not re-pick"}}}}
        (self.t / "state.json").write_text(json.dumps({"jobs": {}}))
        self.st = {"plans": {"h:/p.json|e2": {"blocks": {"phy": self.cur, "io": self.cur, "same": self.old}}},
                   "items": {
                       # held item on an old block: the plan switch must not stop it
                       KW.item_key("d", "e2", "phy", self.old): dict(die="d", item="phy", attempt=7, status="RUNNING",
                                                                     unit="kw-phy-7", stage="geom", block_sha=self.old),
                       # not held, old block: still stopped (original rule)
                       KW.item_key("d", "e2", "io", self.old): dict(die="d", item="io", attempt=3, status="RUNNING",
                                                                    unit="kw-io-3", stage="place", block_sha=self.old),
                       # own block unchanged, only the event label moved (key on the old event, no block in key)
                       KW.item_key("d", "e1", "same"): dict(die="d", item="same", attempt=1, status="RUNNING",
                                                            unit="kw-same-1", stage="place", block_sha=self.old),
                   }}

    def rec(self, item, blk=None, ev="e2"):
        return self.st["items"][KW.item_key("d", ev, item, blk)]

    def test_held_and_unchanged_kept_others_stopped(self):
        n = KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(n, 1)
        self.assertEqual(self.stops, ["kw-io-3"])
        self.assertEqual(self.rec("phy", self.old)["status"], "RUNNING")
        self.assertIn("hold_items", self.rec("phy", self.old)["supersede_kept"])
        self.assertEqual(self.rec("same", ev="e1")["status"], "RUNNING")
        self.assertIn("unchanged", self.rec("same", ev="e1")["supersede_kept"])
        self.assertEqual(self.rec("io", self.old)["class"], "SUPERSEDED")
        self.assertEqual(sum("SUPERSEDED-KEEP" in m for m in self.logs), 2)

    def test_keep_logged_once(self):
        KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(sum("SUPERSEDED-KEEP" in m for m in self.logs), 2)

    def test_hold_lifted_then_stopped(self):
        KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        self.cfg["dies"]["d"]["hold_items"] = {}
        KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        self.assertIn("kw-phy-7", self.stops)
        self.assertEqual(self.rec("phy", self.old)["class"], "SUPERSEDED")

    def test_dry_run_changes_nothing_physical(self):
        self.AP.DRY = True
        KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(self.stops, [])


if __name__ == "__main__":
    unittest.main()
