#!/usr/bin/env python3
"""KW-FIX-45 11-12: die_gen_env is the default env of every item; item_env wins."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def test_default_and_override(self):
        d = {"die_gen_env": {"OT_PLACE_MAX_FANOUT": "64"}, "item_env": {"a": {"OT_PLACE_MAX_FANOUT": "32", "OT_X": "1"}}}
        self.assertEqual(kw.item_env(d, "b"), {"OT_PLACE_MAX_FANOUT": "64"})
        self.assertEqual(kw.item_env(d, "a"), {"OT_PLACE_MAX_FANOUT": "32", "OT_X": "1"})
        self.assertEqual(kw.item_env({}, "b"), {})

    def test_invalid_default_refused(self):
        with self.assertRaises(ValueError):
            kw.item_env({"die_gen_env": {"BAD": "1"}}, "b")

if __name__ == "__main__":
    unittest.main()
