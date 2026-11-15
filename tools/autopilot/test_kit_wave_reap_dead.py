#!/usr/bin/env python3
"""KW-FIX-46 REAP-DEAD: a RUNNING row whose unit is gone and a RETRY-INFRA row with a spent budget become terminal."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, active=(), probe="{}", probe_rc=0):
        self.active, self.cmds, self.logs, self.probe, self.probe_rc = set(active), [], [], probe, probe_rc

    def unit_active(self, u):
        return u in self.active

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        if input and "me = str(os.getpid())" in input:
            return self.probe_rc, self.probe + "\n", ""
        return 0, '{"containers": [], "scopes": []}\n', ""

    def log(self, m):
        self.logs.append(m)


def rec(d, name, status, age_min, **kw):
    jd = Path(d) / name
    jd.mkdir()
    (jd / "spec.json").write_text(json.dumps({"work": f"/srv/kw/{name}"}))
    t = time.time() - age_min * 60
    r = dict(die="s81", item=name, kind="type", event="e", attempt=3, status=status, unit=f"u-{name}", dir=str(jd),
             started=t, updated=t, infra_base=0)
    r.update(kw)
    return r


CFG = {"dies": {"s81": {"event": "e"}}, "infra_attempts": 3}


class Reap(unittest.TestCase):
    def test_dead_running_row_reaped_after_n_minutes(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": rec(d, "a", "RUNNING", 200), "young": rec(d, "young", "RUNNING", 10),
                            "live": rec(d, "live", "RUNNING", 500)}}
            ap, n = AP(active={"u-live"}), {}
            self.assertEqual(KW.reap_dead(ap, CFG, st, n), 1)
            self.assertEqual((st["items"]["a"]["status"], st["items"]["a"]["class"]), ("FAIL", "INFRA"))
            self.assertIn("REAP-DEAD R1", st["items"]["a"]["reason"])
            self.assertIn(["systemctl", "--user", "stop", "u-a"], ap.cmds)
            self.assertEqual(st["items"]["young"]["status"], "RUNNING")          # inside the window
            self.assertEqual(st["items"]["live"]["status"], "RUNNING")           # unit active: never reaped

    def test_row_with_result_json_is_left_to_collect(self):
        with tempfile.TemporaryDirectory() as d:
            r = rec(d, "a", "RUNNING", 400)
            (Path(r["dir"]) / "result.json").write_text("{}")
            st = {"items": {"a": r}}
            self.assertEqual(KW.reap_dead(AP(), CFG, st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")

    def test_spent_retry_infra_becomes_terminal_open_budget_stays(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"spent": rec(d, "spent", "RETRY-INFRA", 60, attempt=12, infra_base=1),
                            "open": rec(d, "open", "RETRY-INFRA", 60, attempt=2)}}
            self.assertEqual(KW.reap_dead(AP(), CFG, st, {}), 1)
            self.assertEqual((st["items"]["spent"]["status"], st["items"]["spent"]["class"]), ("FAIL", "INFRA"))
            self.assertIn("R3", st["items"]["spent"]["reason"])
            self.assertEqual(st["items"]["open"]["status"], "RETRY-INFRA")
            self.assertFalse(KW.infra_relaunch_due(CFG, st["items"]["spent"]))

    def test_silent_active_unit_only_reported(self):
        with tempfile.TemporaryDirectory() as d:
            r = rec(d, "a", "RUNNING", 900)
            lg = Path(r["dir"]) / "place.live.log"
            lg.write_text("x")
            import os
            old = time.time() - 600 * 60
            os.utime(lg, (old, old))
            st = {"items": {"a": r}}
            ap = AP(active={"u-a"}, probe=json.dumps({"/srv/kw/a": [4242]}))      # an ot-run waiter names the root
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")
            self.assertTrue(any("SILENT" in m and "alive" in m for m in ap.logs))
            ap = AP(active={"u-a"}, probe_rc=1)                                    # unreadable host: nothing reaped
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")
            ap = AP(active={"u-a"})                                                # nothing alive anywhere: a zombie, R2
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}), 1)
            self.assertEqual((st["items"]["a"]["status"], st["items"]["a"]["class"]), ("FAIL", "INFRA"))
            self.assertIn("REAP-DEAD R2", st["items"]["a"]["reason"])
            self.assertIn(["systemctl", "--user", "stop", "u-a"], ap.cmds)

    def test_dry_and_off(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": rec(d, "a", "RUNNING", 400)}}
            ap = AP()
            ap.DRY = True
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")
            self.assertEqual(KW.reap_dead(AP(), dict(CFG, reap_dead_min=0), st, {}), 0)
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
