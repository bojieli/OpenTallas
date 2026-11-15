"""KIT-OPS-1 11-12 (COORD): a plain ISSUES verdict rejects a build like BAD (WAIT-FORM, relaunch on a new form fingerprint);
ISSUES-ACCEPT still accepts; VISUAL-QUEUE.tsv drops WAIT-VISUAL rows whose own build already carries BAD / ISSUES."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "kv3_sys_c", "event": "ev", "plan": "/x/plan_c.json", "src": "/s/src_a", "core_kit": "ck", "gen_env": {}}
T_VERDICT = "2026-11-12 16:20"
TS = time.mktime(time.strptime(T_VERDICT, "%Y-%m-%d %H:%M"))


class IssuesReject(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "coord" / "autopilot").mkdir(parents=True)
        (self.root / "coord" / "lanes").mkdir(parents=True)
        (self.root / "coord" / "bin").mkdir(parents=True)
        self.review = self.root / "coord" / "lanes" / "GEOM-REVIEW.md"
        self.review.write_text("# review\n")
        self.adir = self.root / "kv_sys_c" / "a12"
        self.adir.mkdir(parents=True)
        (self.adir / "spec.json").write_text(json.dumps(SPEC))
        self.cfg = {"dies": {"qwen_kvsys": {"gen_hosts": [], "plan": "/x/plan_c.json"}}, "visual_gate_since": "2026-11-12 04:25"}
        self.p = [mock.patch.object(K, "type_block_sha", lambda *a, **k: "tb1"),
                  mock.patch.object(K.Path, "home", lambda: self.root),
                  mock.patch.object(K.subprocess, "run", lambda *a, **k: None)]
        for x in self.p:
            x.start()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})
        K._GEOM_CACHE.update(mtime=None, v={}, ts={})

    def tearDown(self):
        for x in self.p:
            x.stop()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})
        K._GEOM_CACHE.update(mtime=None, v={}, ts={})
        self.td.cleanup()

    def verdict(self, v, attempt=12):
        with open(self.review, "a") as f:
            f.write(f"- {T_VERDICT} PST GEOM VERDICT [GEOM-VIS-10 viewed] qwen_kvsys/kv3_sys_c attempt_{attempt} 3_place (epyc8): {v}. text\n")
        st = os.stat(self.review)
        os.utime(self.review, (st.st_atime, st.st_mtime + 1))

    def rec(self):
        return {"die": "qwen_kvsys", "item": "kv3_sys_c", "kind": "type", "attempt": 12, "started": TS - 3600,
                "dir": str(self.adir), "status": "ROUTE-HELD", "kit": "/k", "kit_host": "epyc8",
                "route_hold": "WAIT-VISUAL: place done, needs a visual verdict GOOD / OK / ISSUES-ACCEPT"}

    def test_issues_is_wait_form(self):
        self.verdict("ISSUES")
        self.assertTrue(K.visual_hold(self.cfg, self.rec()).startswith("WAIT-FORM: visual verdict ISSUES"))

    def test_issues_accept_still_accepts(self):
        self.verdict("ISSUES-ACCEPT")
        self.assertIsNone(K.visual_hold(self.cfg, self.rec()))
        self.assertEqual(K.geom_verdicts()[("qwen_kvsys", "kv3_sys_c")], (12, "ISSUES-ACCEPT"))   # not read as ISSUES

    def test_no_verdict_waits_visual(self):
        self.assertTrue(K.visual_hold(self.cfg, self.rec()).startswith("WAIT-VISUAL"))

    def test_queue_drops_rejected_rows(self):
        st = {"items": {"a": self.rec(), "b": dict(self.rec(), item="kv3_pc_v3", attempt=3)}}
        self.verdict("ISSUES")
        n = K.visual_queue_publish(self.cfg, st)
        self.assertEqual(n, 1)                                            # only the unrated kv3_pc_v3 row is listed
        self.assertTrue(st["items"]["a"]["route_hold"].startswith("WAIT-FORM: visual verdict ISSUES"))
        body = (self.root / "coord" / "lanes" / "VISUAL-QUEUE.tsv").read_text()
        self.assertNotIn("kv3_sys_c", body)
        self.assertIn("kv3_pc_v3", body)

    def test_form_wait_holds_on_issues_until_form_changes(self):
        rec = self.rec()
        self.verdict("ISSUES")
        K.visual_hold(self.cfg, rec)                                      # binds the rated form, as the tick does
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC)):
            self.assertTrue(K.form_wait(self.cfg, {"items": {}}, "qwen_kvsys", "kv3_sys_c", rec))
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC, gen_env={"OT_CLAND_STRIP_DENS": "1.0"})):
            self.assertFalse(K.form_wait(self.cfg, {"items": {}}, "qwen_kvsys", "kv3_sys_c", rec))


if __name__ == "__main__":
    unittest.main()
