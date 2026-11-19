#!/usr/bin/env python3
"""WAVE-TICK-1119: the tick-time structure fixes (one ps per 20 s, parallel per-die probes with unchanged results)"""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

os.environ["OT_TOOL_SKEW_REMOTE"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP_MOD  # noqa: E402
import kit_wave as KW  # noqa: E402
from test_tool_skew import MeasureAll  # noqa: E402


class PsCache(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.old = AP_MOD.sh
        AP_MOD.PS_CACHE.update(t=0.0, out="")

        def fake(cmd, timeout=300, input=None):
            self.calls.append(cmd)
            return 0, "11 100 ot-run /kit/a\n12 5 python3 /other\n", ""
        AP_MOD.sh = fake

    def tearDown(self):
        AP_MOD.sh = self.old
        AP_MOD.PS_CACHE.update(t=0.0, out="")

    def test_one_ps_for_many_jobs_within_ttl(self):
        for _ in range(50):
            self.assertEqual(AP_MOD.hub_procs("/kit/a"), [(11, 100)])
            self.assertEqual(AP_MOD.hub_procs("/kit/none"), [])
        self.assertEqual(len(self.calls), 1)

    def test_refresh_after_ttl(self):
        AP_MOD.hub_ps_text(now=1000.0)
        AP_MOD.hub_ps_text(now=1000.0 + AP_MOD.PS_TTL_S - 1)
        self.assertEqual(len(self.calls), 1)
        AP_MOD.hub_ps_text(now=1000.0 + AP_MOD.PS_TTL_S + 1)
        self.assertEqual(len(self.calls), 2)

    def test_failed_ps_is_not_cached(self):
        AP_MOD.sh = lambda cmd, timeout=300, input=None: (1, "", "boom")
        self.assertEqual(AP_MOD.hub_procs("/kit/a"), [])
        AP_MOD.sh = lambda cmd, timeout=300, input=None: (0, "11 100 ot-run /kit/a\n", "")
        self.assertEqual(AP_MOD.hub_procs("/kit/a"), [(11, 100)])


class OverlayParallel(unittest.TestCase):
    def test_merge_src_overlay_parallel_in_die_order(self):
        seen, lock = [], threading.Lock()
        old = KW.src_overlay_hash

        def fake(src, host, hub, timeout=None):
            with lock:
                seen.append(src)
            return "" if src == "/bad" else "ab" * 32
        KW.src_overlay_hash = fake
        try:
            cfg = {"dies": {"a": dict(enabled=True, src="/a", gen_host="h1"), "b": dict(enabled=True, src="/bad", gen_host="h2"),
                            "c": dict(enabled=False, src="/c", gen_host="h3"), "d": dict(enabled=True, src="/d", gen_host="h1")}}
            logs = []
            KW.merge_src_overlay(cfg, "hub", logs.append)
        finally:
            KW.src_overlay_hash = old
        self.assertEqual(sorted(seen), ["/a", "/bad", "/d"])
        self.assertEqual(cfg["dies"]["a"]["_src_overlay"], "ab" * 32)
        self.assertEqual(cfg["dies"]["b"]["_src_overlay"], "")
        self.assertNotIn("_src_overlay", cfg["dies"]["c"])
        self.assertEqual(logs, ["KIT-WAVE src_overlay: b unreadable on h2; hold compares without it"])

    def test_overlay_cache_save_is_thread_safe(self):
        with tempfile.TemporaryDirectory() as t:
            old = KW.OVERLAY_CACHE_FILE
            KW.OVERLAY_CACHE_FILE = str(Path(t) / "ovl.json")
            try:
                ths = [threading.Thread(target=KW._overlay_cache_save) for _ in range(16)]
                [x.start() for x in ths]
                [x.join() for x in ths]
                self.assertTrue(Path(KW.OVERLAY_CACHE_FILE).exists())
                self.assertEqual(sorted(p.name for p in Path(t).iterdir()), ["ovl.json"])
            finally:
                KW.OVERLAY_CACHE_FILE = old


class ToolSkewParallel(MeasureAll):
    """the two-die measure_all of test_tool_skew now runs the workers in parallel; its results and log lines must be identical"""
    def test_parallel_matches_serial(self):
        rows, ap, tbl = self.run_all("warn")
        self.assertEqual(rows["qwen_kvsys"]["n_differ"], 1)
        self.assertEqual(rows["s81"]["n_differ"], 0)
        txt = "\n".join(ap.logs)
        self.assertEqual(txt.count("TOOL-SKEW WARN qwen_kvsys"), 1)
        self.assertEqual(txt.count("TOOL-SKEW OK s81"), 1)


if __name__ == "__main__":
    unittest.main()
