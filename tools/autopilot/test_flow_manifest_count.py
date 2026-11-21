"""FLOW-OPS-0900 11-21 (FABLE-FLOW-0745 class e): sign-offs counted once -- provenance by flow manifest over every tag, a flow tag cut
at pin adoption, AUTO-RESIGN never signs a carried result twice."""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class Base(unittest.TestCase):
    def setUp(self):
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.CLOSURE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "r"
        self.origin = root / "o.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        self.repo.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo)] + list(a), check=True, capture_output=True, text=True).stdout.strip()
        self.g = g
        g("init", "-q")
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", str(self.origin))
        (self.repo / "tools/die_plan").mkdir(parents=True)
        (self.repo / "tools/die_plan/signoff.py").write_text("v1\n")
        (self.repo / "rtl.sv").write_text("a\n")
        g("add", "."); g("commit", "-qm", "c1")
        self.c1 = g("rev-parse", "HEAD")
        g("tag", "-a", "flow-20261113-lp-qc", self.c1, "-m", "old")
        (self.repo / "tools/die_plan/signoff.py").write_text("v2\n")
        g("add", "."); g("commit", "-qm", "flow change")
        self.c2 = g("rev-parse", "HEAD")
        for i, s in enumerate(("aa", "ab", "ac")):           # newer tags push the old one out of the window
            g("tag", "-a", "flow-20261117-%s-qc" % s, self.c2, "-m", "new")
        g("push", "-q", "origin", "HEAD:refs/heads/main", "--tags")
        self.saved = (self.ap.REPO, self.ap.flow_watch, self.ap.FLOW_TAGS_CHECKED, self.ap.FLOW_MANIFEST_CACHE, self.ap.AUTO_FLOW_TAG_STOP)
        self.ap.REPO = self.repo
        self.ap.flow_watch = lambda: ["tools/die_plan/signoff.py"]
        self.ap.FLOW_TAGS_CHECKED = 2
        self.ap.FLOW_MANIFEST_CACHE = root / "fm.json"
        self.ap.AUTO_FLOW_TAG_STOP = root / "stop"
        self.ap._FM.update(memo=None, dirty=False)
        self._log = self.ap.log
        self.ap.log = lambda *a, **k: None

    def tearDown(self):
        (self.ap.REPO, self.ap.flow_watch, self.ap.FLOW_TAGS_CHECKED, self.ap.FLOW_MANIFEST_CACHE, self.ap.AUTO_FLOW_TAG_STOP) = self.saved
        self.ap.log = self._log
        self.ap.CLOSURE.clear()
        self.tmp.cleanup()


class TestManifestCount(Base):
    def test_old_tag_outside_window_still_carries(self):
        """the 11-21 case: the pin sits ON flow-20261113-lp-qc, newer tags filled the 30-tag window"""
        self.ap.FLOW_TAGS_CHECKED = 0                         # the old 30-newest window is empty: the match must not use it
        self.assertEqual(self.ap.flow_tags("qwen_compute"), [])
        # a design-only change on top of c1 (another branch): same flow content, not the tag commit
        self.g("checkout", "-q", "-b", "side", self.c1)
        (self.repo / "rtl.sv").write_text("z\n")
        self.g("add", "."); self.g("commit", "-qm", "design only")
        side = self.g("rev-parse", "HEAD")
        p = self.ap.resolve_provenance("main@" + self.c1[:12], "", "qwen_compute")
        self.assertEqual((p["flow_tag"], p.get("error")), ("flow-20261113-lp-qc", None))
        p = self.ap.resolve_provenance("side@" + side[:12], "", "qwen_compute")
        self.assertEqual((p["flow_tag"], p.get("error")), ("flow-20261113-lp-qc", None))
        self.assertTrue(p["flow_manifest"])
        p = self.ap.resolve_provenance("main@" + self.c1[:12], "", "s81")   # qc-only tags do not cover s81
        self.assertEqual(p["flow_tag"], "")
        self.assertIn("no flow release tag", p["error"])

    def test_manifest_cache_persisted(self):
        self.ap.resolve_provenance("main@" + self.c1[:12], "", "qwen_compute")
        memo = json.loads(Path(self.ap.FLOW_MANIFEST_CACHE).read_text())
        self.assertTrue(any(k.startswith(self.c1) for k in memo))

    def test_lstree_manifest_pure(self):
        a = "100644 blob 11\ttools/die_plan/signoff.py\0100644 blob 22\trtl.sv\0"
        b = "100644 blob 22\trtl.sv\0100644 blob 11\ttools/die_plan/signoff.py\0100644 blob 33\ttools/die_plan/test_x.py\0"
        w, x = ["tools/die_plan/*.py"], ["*/test_*.py"]
        self.assertEqual(self.ap.manifest_of_lstree(a, w, x, None), self.ap.manifest_of_lstree(b, w, x, None))
        self.assertEqual(self.ap.flow_watch_roots(["tools/die_plan/*.tcl", "physical/common_flow/*", "tools/x.py"]),
                         ["physical/common_flow", "tools/die_plan", "tools/x.py"])
        self.assertEqual(self.ap.flow_watch_roots(["*.py"]), [])

    def test_tag_names(self):
        self.assertEqual([self.ap.flow_tag_suffix(n) for n in (0, 25, 26, 27, 52)], ["a", "z", "aa", "ab", "ba"])
        taken = ["flow-20261121-a-qc", "flow-20261121-b-s81", "flow-20261120-c-qc"]
        self.assertEqual(self.ap.next_flow_tag_name("20261121", taken, "kv"), "flow-20261121-c-kv")

    def _c3(self):
        (self.repo / "tools/die_plan/signoff.py").write_text("v3\n")
        self.g("add", "."); self.g("commit", "-qm", "flow v3")
        return self.g("rev-parse", "HEAD")

    def _canary(self, src, verdict="PASS", done=True, name="run1"):
        d = Path(self.ap.CANARY_ROOT) / name
        d.mkdir(parents=True)
        (d / "canary_meta.json").write_text(json.dumps({"spec": {"die": "qwen_compute", "item": "ref"},
                                                         "src": "/x/flow-canary/sources/" + src, "src_commit": src}))
        if done:
            (d / "canary.json").write_text(json.dumps({"src": src, "verdict": verdict}))

    def test_no_canary_no_tag(self):
        """COORD ruling 4: an auto-cut tag never skips the canary"""
        c3 = self._c3()
        self.ap.CANARY_ROOT = str(Path(self.tmp.name) / "canary")
        tag, why = self.ap.ensure_pin_tag("qwen_compute", c3, day="20261121")
        self.assertIsNone(tag)
        self.assertIn("WAIT-CANARY no qwen_compute canary run", why)
        self._canary(c3, done=False)
        self.assertIn("canary running", self.ap.ensure_pin_tag("qwen_compute", c3, day="20261121")[1])
        out = subprocess.run(["git", "--git-dir", str(self.origin), "tag"], capture_output=True, text=True).stdout.split()
        self.assertNotIn("flow-20261121-a-qc", out)

    def test_canary_gating_verdict(self):
        import canary_gate as CG
        c3 = self._c3()
        self.ap.CANARY_ROOT = str(Path(self.tmp.name) / "canary")
        self._canary(c3)
        saved = CG.regression
        try:
            CG.regression = lambda run, root, repo, seed=True: ("REGRESSION", "slower")
            ok, why = self.ap.canary_released(self.ap.flow_manifest(c3, "qwen_compute"), "qwen_compute")
            self.assertFalse(ok)
            self.assertIn("REGRESSION", why)
            CG.regression = lambda run, root, repo, seed=True: ("NO-REGRESSION", "ok")
            ok, why = self.ap.canary_released(self.ap.flow_manifest(c3, "qwen_compute"), "qwen_compute")
            self.assertTrue(ok)
            tag, why = self.ap.ensure_pin_tag("qwen_compute", c3, day="20261121")
            self.assertEqual((tag, why), ("flow-20261121-a-qc", "cut"))
            # a canary of ANOTHER flow never releases this one
            self.assertFalse(self.ap.canary_released(self.ap.flow_manifest(self.c2, "qwen_compute"), "qwen_compute")[0])
        finally:
            CG.regression = saved

    def test_pin_tag_cut_once(self):
        c3 = self._c3()
        self.ap.canary_released = lambda m, d: (True, "canary NO-REGRESSION (test)")
        p = self.ap.resolve_provenance("main@" + c3[:12], "", "qwen_compute")
        self.assertIn("no flow release tag", p["error"])
        tag, why = self.ap.ensure_pin_tag("qwen_compute", c3, day="20261121")
        self.assertEqual((tag, why), ("flow-20261121-a-qc", "cut"))
        out = subprocess.run(["git", "--git-dir", str(self.origin), "tag"], capture_output=True, text=True).stdout.split()
        self.assertIn("flow-20261121-a-qc", out)
        self.assertEqual(self.ap.ensure_pin_tag("qwen_compute", c3, day="20261121"), ("flow-20261121-a-qc", "carried"))
        self.ap.CLOSURE.clear()
        p = self.ap.resolve_provenance("main@" + c3[:12], "", "qwen_compute")
        self.assertEqual((p["flow_tag"], p.get("error")), ("flow-20261121-a-qc", None))
        # the pin of an already-carried flow cuts nothing
        self.assertEqual(self.ap.ensure_pin_tag("qwen_compute", self.c1), ("flow-20261113-lp-qc", "carried"))

    def test_pin_tag_stop_and_bad_input(self):
        Path(self.ap.AUTO_FLOW_TAG_STOP).write_text("")
        self.assertIsNone(self.ap.ensure_pin_tag("qwen_compute", self.c2)[0])
        self.assertIsNone(self.ap.ensure_pin_tag("nodie", self.c2)[0])
        self.assertIsNone(self.ap.ensure_pin_tag("qwen_compute", "zz")[0])


class TestPinTagsStep(unittest.TestCase):
    def test_once_per_pin(self):
        import kit_wave as KW
        calls, logs = [], []

        class AP:
            @staticmethod
            def ensure_pin_tag(die, sha):
                calls.append((die, sha))
                return ("flow-x-qc", "cut") if die == "qwen_compute" else (None, "push failed")
            log = staticmethod(logs.append)
        cfg = {"dies": {"qwen_compute": {"src_sha": "a" * 40}, "s81": {"src_sha": "b" * 40}, "hbm": {}}}
        st = {}
        KW.pin_tags_step(AP, cfg, st)
        KW.pin_tags_step(AP, cfg, st)
        self.assertEqual(calls.count(("qwen_compute", "a" * 40)), 1)     # tagged once
        self.assertEqual(calls.count(("s81", "b" * 40)), 2)              # failure retried next tick
        cfg["dies"]["qwen_compute"]["src_sha"] = "c" * 40                # a new pin adopted
        KW.pin_tags_step(AP, cfg, st)
        self.assertIn(("qwen_compute", "c" * 40), calls)
        self.assertEqual(KW.pin_tags_step(AP, dict(cfg, auto_flow_tag=False), st), [])


class TestResignCarried(unittest.TestCase):
    def test_wave_carried_is_skipped(self):
        import auto_resign as AR
        c = dict(die="s81", name="slice_station__t43", module="slice_station__t43", host="intel1", path="/k", source="wave",
                 src="main@3c913dbdfb23")
        p = dict(record="/k/signoff.json", name="slice_station__t43", top="slice_station__t43", db_ok=True, odb_sha="x")
        ctx = dict(holds=[], cache={}, revoked="", retired="", tag=lambda d: "flow-x-s81", tool_key=lambda t: "k", shas={},
                   build_commit=lambda c, p: "3c913dbdfb23", carried=lambda src, die: "flow-20261113-mt-s81")
        act, why = AR.judge(c, p, ctx, {})
        self.assertEqual(act, "SKIP")
        self.assertIn("flow-20261113-mt-s81", why)
        ctx["carried"] = lambda src, die: ""
        self.assertEqual(AR.judge(c, p, ctx, {})[0], "LAUNCH")
        self.assertEqual(AR.judge(dict(c, source="registry"), p, dict(ctx, carried=lambda s, d: "t"), {})[0], "LAUNCH")


if __name__ == "__main__":
    unittest.main()


class TestSpareAdmission(unittest.TestCase):
    """COORD ruling 3: re-sign promotion is the lowest priority, spare admission only"""
    ST = "epyc2 admits 100 GB, load 10/128 threads 20/128 | epyc10 admits 50 GB, load 96/96 threads 96/96"

    def test_spare(self):
        import under_use as UU
        cfg = {"dies": {"s81": {"event": "J6"}}}
        run = {"a": {"die": "s81", "item": "t1", "status": "ENQUEUED", "event": "J6", "q_status": "RUNNING"}}
        self.assertTrue(UU.spare_admission(self.ST, run, cfg)[0])
        wait = dict(run, b={"die": "s81", "item": "t2", "status": "ENQUEUED", "event": "J6", "q_status": ""})
        ok, why = UU.spare_admission(self.ST, wait, cfg)
        self.assertFalse(ok)
        self.assertIn("wait for admission", why)
        old = {"b": {"die": "s81", "item": "t2", "status": "ENQUEUED", "event": "J5", "q_status": ""}}   # superseded event: not waiting
        self.assertTrue(UU.spare_admission(self.ST, old, cfg)[0])
        self.assertFalse(UU.spare_admission("epyc10 admits 50 GB, load 96/96", {}, cfg)[0])     # no idle thread
        self.assertFalse(UU.spare_admission("", {}, cfg)[0])                                  # unknown = not spare
        self.assertFalse(UU.spare_admission(self.ST, {}, cfg, [{"status": None}])[0])         # queue row not submitted

    def test_tick_step_waits(self):
        import autopilot
        ap = importlib.reload(autopilot)
        logs = []
        saved = (ap.log, ap.retry_unversioned)
        ap.log = logs.append
        ran = []
        ap.retry_unversioned = lambda st: ran.append(1)
        try:
            st = {"jobs": {"x": {"status": "SIGNED-UNVERSIONED", "archive": "h:/a"}}}
            ok, why = ap.retry_unversioned_spare(st, status_text="epyc10 admits 50 GB, load 96/96")
            self.assertFalse(ok)
            self.assertEqual(ran, [])
            ok, why = ap.retry_unversioned_spare(st, status_text=self.ST)
            self.assertTrue(ok, why)
            self.assertEqual(ran, [1])
        finally:
            ap.log, ap.retry_unversioned = saved
