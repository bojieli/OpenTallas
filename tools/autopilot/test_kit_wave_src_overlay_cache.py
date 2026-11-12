#!/usr/bin/env python3
"""KW-FIX-45 11-12: src_overlay hash cache + an empty hash means CHANGED."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def _tree(self, d):
        os.makedirs(os.path.join(d, "tools")); open(os.path.join(d, "tools", "a.py"), "w").write("x=1\n")

    def test_cache_and_change(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d); kw.SRC_OVERLAY_CACHE.clear()
            h1 = kw.src_overlay_hash(d, "localhost", "intel2")
            self.assertRegex(h1, r"^[0-9a-f]{64}$")
            calls = []
            real = kw._overlay_run
            def spy(src, host, hub, script, timeout):
                calls.append(script is kw.SRC_OVERLAY_SCRIPT); return real(src, host, hub, script, timeout)
            kw._overlay_run = spy
            try:
                self.assertEqual(kw.src_overlay_hash(d, "localhost", "intel2"), h1)
                self.assertEqual(calls, [False])                      # only the cheap signature ran
                import time; time.sleep(0.01)
                open(os.path.join(d, "tools", "a.py"), "w").write("x=2\n")   # in-place content edit
                h2 = kw.src_overlay_hash(d, "localhost", "intel2")
                self.assertNotEqual(h2, h1); self.assertIn(True, calls)
            finally:
                kw._overlay_run = real

    def test_cache_survives_a_new_process(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d); kw.SRC_OVERLAY_CACHE.clear(); kw._OVL_LOADED[0] = False
            kw.OVERLAY_CACHE_FILE = os.path.join(d, "ovl.json")
            h1 = kw.src_overlay_hash(d, "localhost", "intel2")
            kw.SRC_OVERLAY_CACHE.clear(); kw._OVL_LOADED[0] = False       # a new tick = a new process
            calls = []
            real = kw._overlay_run
            def spy(src, host, hub, script, timeout):
                calls.append(script is kw.SRC_OVERLAY_SCRIPT); return real(src, host, hub, script, timeout)
            kw._overlay_run = spy
            try:
                self.assertEqual(kw.src_overlay_hash(d, "localhost", "intel2"), h1)
                self.assertEqual(calls, [False])
            finally:
                kw._overlay_run = real

    def test_unreadable_is_empty(self):
        self.assertEqual(kw.src_overlay_hash("/nonexistent/__x", "localhost", "intel2"), "")

if __name__ == "__main__":
    unittest.main()
