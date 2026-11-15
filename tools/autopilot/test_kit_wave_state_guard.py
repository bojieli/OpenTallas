#!/usr/bin/env python3
"""KW-FIX-45 11-12: save_state never drops rows another writer added (STATE-GUARD)."""
import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def test_stale_copy_keeps_rows(self):
        with tempfile.TemporaryDirectory() as d:
            kw.save_state({"items": {"a": {"x": 1}, "b": {"x": 2}}, "prep": {}, "pass_n": 0}, d)
            stale = {"items": {"a": {"x": 9}}, "prep": {}, "pass_n": 1}        # loaded before row b existed on disk
            kw.save_state(stale, d)
            got = json.load(open(os.path.join(d, kw.STATE_FILE)))["items"]
            self.assertEqual(set(got), {"a", "b"}); self.assertEqual(got["a"]["x"], 9)

    def test_empty_over_populated_refused(self):
        with tempfile.TemporaryDirectory() as d:
            kw.save_state({"items": {"a": {}}, "prep": {}, "pass_n": 0}, d)
            kw.save_state({"items": {}, "prep": {}, "pass_n": 0}, d)
            self.assertEqual(set(json.load(open(os.path.join(d, kw.STATE_FILE)))["items"]), {"a"})

if __name__ == "__main__":
    unittest.main()
