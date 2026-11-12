"""KW-FIX-45 11-11: a superseded or cancelled attempt's units, containers and queue job are stopped (no zombie routes)."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import kit_wave as KW


class Reap(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.cmds, self.logs, self.remote = [], [], []

        def sh(cmd, timeout=None, input=None):
            if input:
                self.remote.append(json.loads(cmd[-1].strip("'"))["roots"])
                return 0, json.dumps({"containers": ["dpkit-old-1"], "scopes": []}), ""
            self.cmds.append(list(cmd))
            return 0, "", ""
        self.AP = SimpleNamespace(DRY=False, log=self.logs.append, sh=sh, HUB_NAME="intel2", AP_DIR=str(self.t))
        (self.t / "state.json").write_text(json.dumps({"jobs": {
            "jold": {"status": "RUNNING", "unit": "ap-jold-a1"},
            "jdone": {"status": "DONE-STRUCTURAL", "unit": "ap-jdone-a1"}}}))
        now = time.time()
        self.st = {"items": {
            "d|t|b1": dict(die="d", item="t", attempt=7, status="ENQUEUED", q_id="jold", started=now - 3600,
                           kit="h:/w/items/t/attempt_7/gen/t", dir=str(self.t / "none")),
            "d|t|b2": dict(die="d", item="t", attempt=8, status="RUNNING", unit="kw-new", started=now - 60,
                           kit="h:/w/items/t/attempt_8/gen/t", dir=str(self.t / "none2")),
            "d|u|b1": dict(die="d", item="u", attempt=3, status="ENQUEUED", q_id="jdone", started=now - 3600,
                           kit="h:/w/items/u/attempt_3/gen/u", dir=str(self.t / "n3")),
            "d|c|b1": dict(die="d", item="c", attempt=2, status="CANCELLED", updated=now - 600,
                           kit="h:/w/items/c/attempt_2/gen/c", dir=str(self.t / "n4")),
        }}
        self.cfg = {"dies": {"d": {}}}

    def test_older_live_attempt_is_stopped_and_marked_superseded(self):
        notices = {}
        n = KW.reap_stale_attempts(self.AP, self.cfg, self.st, notices, self.t)
        old = self.st["items"]["d|t|b1"]
        self.assertEqual((old["status"], old["class"]), ("CANCELLED", "SUPERSEDED"))
        self.assertEqual(self.st["items"]["d|t|b2"]["status"], "RUNNING")            # the newer attempt is untouched
        self.assertIn(["systemctl", "--user", "stop", "ap-jold-a1"], self.cmds)       # queue unit
        self.assertTrue(any(c[1:2] == ["--cancel-dir"] and c[2].endswith("attempt_7/gen/t") for c in self.cmds))
        self.assertNotIn(["systemctl", "--user", "stop", "kw-new"], self.cmds)
        self.assertEqual(n, 2)                                                        # the superseded attempt + the cancelled row

    def test_cancelled_row_is_reaped_once_with_a_fleet_stop(self):
        KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t)
        self.assertTrue(any(any(r.endswith("attempt_2/gen/c") or "items/c" in r for r in roots) for roots in self.remote)
                        or self.remote)
        self.assertIn("reaped", self.st["items"]["d|c|b1"])
        self.remote.clear(); self.cmds.clear()
        KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(self.remote, [])                                             # idempotent: no second stop

    def test_finished_queue_job_and_lone_attempt_are_not_touched(self):
        KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(self.st["items"]["d|u|b1"]["status"], "ENQUEUED")
        self.assertNotIn(["systemctl", "--user", "stop", "ap-jdone-a1"], self.cmds)

    def test_opt_out_and_dry_run_do_nothing(self):
        self.cfg["reap_stale_attempts"] = False
        self.assertEqual(KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t), 0)
        self.cfg = {"dies": {"d": {}}}; self.AP.DRY = True
        KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(self.cmds, []); self.assertEqual(self.st["items"]["d|t|b1"]["status"], "ENQUEUED")

    def test_reap_dry_run_option_only_logs(self):
        self.cfg["reap_dry_run"] = True
        KW.reap_stale_attempts(self.AP, self.cfg, self.st, {}, self.t)
        self.assertEqual(self.cmds, []); self.assertEqual(self.remote, [])
        self.assertEqual(self.st["items"]["d|t|b1"]["status"], "ENQUEUED")
        self.assertTrue(any("REAP would stop d/t@7" in l for l in self.logs))

    def test_hooked_into_the_tick_after_cancel_superseded(self):
        src = Path(KW.__file__).read_text()
        self.assertLess(src.index("cancel_superseded(AP, cfg, st, notices, ap_dir)\n"), src.index("reap_stale_attempts(AP, cfg, st, notices, ap_dir)      #"))


if __name__ == "__main__":
    unittest.main()
