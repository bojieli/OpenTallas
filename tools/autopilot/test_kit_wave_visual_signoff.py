"""KIT-OPS-1 11-13 (OWNER 03:5x, visual gate moves to sign-off): with kit_wave.json visual_gate "signoff" a placed type routes
without a verdict; a verdict GOOD / OK / ISSUES-ACCEPT is still needed before the autopilot archives (counts) it; a BAD / ISSUES
verdict keeps a held row at WAIT-FORM, withholds the archive and discards a routed build (CANCELLED WAIT-FORM, data kept)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "kv3_sys_c", "event": "ev", "plan": "/x/plan_c.json", "src": "/s/src_a", "core_kit": "ck", "gen_env": {}}
T_VERDICT = "2026-11-13 04:20"
TS = time.mktime(time.strptime(T_VERDICT, "%Y-%m-%d %H:%M"))


class FakeAP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self):
        self.calls, self.logs = [], []

    def sh(self, cmd, timeout=None):
        self.calls.append(cmd)
        return 0, "", ""

    def log(self, m):
        self.logs.append(m)


class VisualSignoff(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.ap = self.root / "coord" / "autopilot"
        self.ap.mkdir(parents=True)
        (self.root / "coord" / "lanes").mkdir(parents=True)
        (self.root / "coord" / "bin").mkdir(parents=True)
        self.review = self.root / "coord" / "lanes" / "GEOM-REVIEW.md"
        self.review.write_text("# review\n")
        self.adir = self.root / "kv_sys_c" / "a12"
        self.adir.mkdir(parents=True)
        (self.adir / "spec.json").write_text(json.dumps(SPEC))
        self.cfg = {"dies": {"qwen_kvsys": {"gen_hosts": [], "plan": "/x/plan_c.json"}},
                    "visual_gate_since": "2026-11-12 04:25", "visual_gate": "signoff"}
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

    def rec(self, status="ROUTE-HELD", **kw):
        r = {"die": "qwen_kvsys", "item": "kv3_sys_c", "kind": "type", "attempt": 12, "started": TS - 3600,
             "dir": str(self.adir), "status": status, "kit": "epyc8:/k", "kit_host": "epyc8", "updated": TS - 60,
             "route_hold": "WAIT-VISUAL: place done, needs a visual verdict GOOD / OK / ISSUES-ACCEPT"}
        r.update(kw)
        return r

    def write_ap(self, recs, cfg=None):
        (self.ap / "kit_wave.json").write_text(json.dumps(cfg or self.cfg))
        (self.ap / K.STATE_FILE).write_text(json.dumps({"items": {f"k{i}": r for i, r in enumerate(recs)}}))

    # ---- route: no hold without a verdict in signoff mode, hold in route mode
    def test_signoff_mode_routes_without_verdict(self):
        self.assertIsNone(K.visual_hold(self.cfg, self.rec()))
        self.assertTrue(K.visual_hold(dict(self.cfg, visual_gate="route"), self.rec()).startswith("WAIT-VISUAL"))
        self.assertTrue(K.visual_hold({k: v for k, v in self.cfg.items() if k != "visual_gate"}, self.rec()).startswith("WAIT-VISUAL"))

    def test_signoff_mode_bad_still_wait_form(self):
        self.verdict("BAD")
        self.assertTrue(K.visual_hold(self.cfg, self.rec()).startswith("WAIT-FORM: visual verdict BAD"))

    # ---- count: the autopilot archive waits for an accepting verdict
    def test_archive_held_without_verdict(self):
        self.write_ap([self.rec("ENQUEUED")])
        g, why = K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"})
        self.assertEqual(g, "hold")
        self.assertIn(K.VISUAL_SIGNOFF, why)

    def test_archive_after_good(self):
        self.verdict("GOOD")
        self.write_ap([self.rec("ENQUEUED")])
        self.assertEqual(K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"}), ("", ""))

    def test_archive_refused_on_issues(self):
        self.verdict("ISSUES")
        self.write_ap([self.rec("ENQUEUED")])
        g, why = K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"})
        self.assertEqual(g, "reject")
        self.assertIn("ISSUES", why)

    def test_not_gated(self):
        self.write_ap([self.rec("ENQUEUED")], dict(self.cfg, visual_gate="route"))
        self.assertEqual(K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"}), ("", ""))
        self.write_ap([self.rec("ENQUEUED")])
        self.assertEqual(K.signoff_visual_gate(str(self.ap), {"kit": "other:/k"}), ("", ""))       # no wave row
        self.write_ap([self.rec("ENQUEUED", kind="core")])
        self.assertEqual(K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"}), ("", ""))       # hard core exempt
        self.write_ap([self.rec("ENQUEUED", started=K.visual_gate_t0(self.cfg) - 10)])
        self.assertEqual(K.signoff_visual_gate(str(self.ap), {"kit": "epyc8:/k"}), ("", ""))       # placed before the gate

    # ---- a routed build rated BAD is discarded to WAIT-FORM, its data kept
    def test_discard_routed_bad(self):
        self.verdict("BAD")
        r = self.rec("ENQUEUED", q_id="j1")
        st = {"items": {"a": r}}
        ap = FakeAP()
        with mock.patch.object(K, "grt_arm_reclaim", side_effect=AssertionError("reclaim must not run")), \
                mock.patch.object(K, "grt_arm_withdraw", lambda *a, **k: "withdrawn"), \
                mock.patch.object(K, "attempt_root", lambda rec: "/root"), \
                mock.patch.object(K.WJ, "stop_on_fleet", lambda *a, **k: {}), \
                mock.patch.object(K.WJ, "stopped_names", lambda res: []):
            n = K.visual_reject_discard(ap, self.cfg, st, {}, {"j1": {"status": "RUNNING", "unit": "u-route"}})
        self.assertEqual(n, 1)
        self.assertEqual((r["status"], r["class"]), ("CANCELLED", "WAIT-FORM"))
        self.assertTrue(r["reason"].startswith("WAIT-FORM: visual verdict BAD"))
        self.assertEqual(r["reclaim"], "kept (no reclaim)")
        self.assertIn(["systemctl", "--user", "stop", "u-route"], ap.calls)

    def test_no_discard_on_good_or_route_mode(self):
        self.verdict("GOOD")
        r = self.rec("ENQUEUED")
        self.assertEqual(K.visual_reject_discard(FakeAP(), self.cfg, {"items": {"a": r}}, {}, {}), 0)
        self.assertEqual(r["status"], "ENQUEUED")
        self.assertEqual(K.visual_reject_discard(FakeAP(), dict(self.cfg, visual_gate="route"), {"items": {"a": r}}, {}, {}), 0)

    # ---- the review queue lists routed builds still owed a verdict
    def test_queue_lists_routed_without_verdict(self):
        st = {"items": {"a": self.rec("ENQUEUED", q_status="RUNNING")}}
        with mock.patch.object(K, "kit_class", lambda d, i: "qwen_kvsys|kv3|fam"):
            n = K.visual_queue_publish(self.cfg, st)
        self.assertEqual(n, 1)
        body = (self.root / "coord" / "lanes" / "VISUAL-QUEUE.tsv").read_text()
        self.assertIn("\t" + K.VISUAL_SIGNOFF + "\t", body)

    def test_queue_route_mode_unchanged(self):
        st = {"items": {"a": self.rec("ENQUEUED", q_status="RUNNING")}}
        with mock.patch.object(K, "kit_class", lambda d, i: "qwen_kvsys|kv3|fam"):
            self.assertEqual(K.visual_queue_publish(dict(self.cfg, visual_gate="route"), st), 0)

    def test_queue_class_shows_gate(self):
        self.assertEqual(K.queue_class({"status": "SIGNED", "visual_gate": "archive pending: WAIT-VISUAL-SIGNOFF: x"})[0], "visual")
        self.assertEqual(K.queue_class({"status": "SIGNED"})[0], "archive")


if __name__ == "__main__":
    unittest.main()
