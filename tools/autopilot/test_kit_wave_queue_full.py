"""KIT-TRIAGE-1 11-01 (OWNER: keep the queue full): merge-gated pending retries + once-per-code auto re-judge"""
import unittest
from types import SimpleNamespace

import kit_wave as KW


class PendingRetries(unittest.TestCase):
    TSV = ("# sha\tscope\tdie\titem@attempt\tlane\tnote\n"
           "abc1234\thub\ts81\tt14@2\tKIT-TRIAGE-1\tclassifier\n"
           "def5678\tsrc\ts81\tt28@1\tKIT-TRIAGE-1\tHB4 hook\n"
           "zzz\thub\ts81\tbad@1\n"                      # not a sha
           "abc1234\tother\ts81\tbad@2\n"                # bad scope
           "abc1234\thub\ts81\tnoattempt\n")

    def test_parse(self):
        rows = KW.parse_pending(self.TSV)
        self.assertEqual([(r["sha"], r["scope"], r["retry"]) for r in rows],
                         [("abc1234", "hub", "t14@2"), ("def5678", "src", "t28@1")])

    def test_release_only_merged_and_once(self):
        cfg = {"dies": {"s81": {"retry": ["x@1"], "src_sha": "s"}}}
        st, notices = {}, {}
        merged = lambda sha, scope, die: sha == "abc1234"
        KW.release_pending(cfg, st, KW.parse_pending(self.TSV), merged, notices)
        self.assertEqual(cfg["dies"]["s81"]["retry"], ["x@1", "t14@2"])
        self.assertEqual(len(notices["s81"]), 1)
        # next tick: fresh config (never written back) -> the released row is re-added without a new notice
        cfg2, n2 = {"dies": {"s81": {"src_sha": "s"}}}, {}
        KW.release_pending(cfg2, st, KW.parse_pending(self.TSV), lambda *a: False, n2)
        self.assertEqual(cfg2["dies"]["s81"]["retry"], ["t14@2"])
        self.assertEqual(n2, {})

    def test_unknown_die_ignored(self):
        cfg, st = {"dies": {}}, {}
        KW.release_pending(cfg, st, KW.parse_pending(self.TSV), lambda *a: True, {})
        self.assertEqual(st.get("pending_released"), {})


class AutoRejudge(unittest.TestCase):
    def test_once_per_code(self):
        calls = []
        AP = SimpleNamespace(log=lambda m: calls.append(m), rpy=lambda *a, **k: {})
        st = {"items": {}}
        self.assertIsNotNone(KW.auto_rejudge(AP, {"dies": {}}, st, {}))
        self.assertEqual(st["auto_rejudge_code"], KW.wave_code_id())
        self.assertIsNone(KW.auto_rejudge(AP, {"dies": {}}, st, {}))     # same code: nothing to do

    def test_failure_retries_next_tick(self):
        AP = SimpleNamespace(log=lambda m: None, rpy=lambda *a, **k: (_ for _ in ()).throw(OSError("ssh")))
        st = {"items": {"k": dict(die="d", item="a", attempt=1, status="FAIL", stage="geom", evidence="h:/x",
                                  kit="h:/k", **{"class": "PLAN"})}}
        self.assertIsNone(KW.auto_rejudge(AP, {"dies": {}}, st, {}))
        self.assertNotIn("auto_rejudge_code", st)


if __name__ == "__main__":
    unittest.main()
