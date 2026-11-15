#!/usr/bin/env python3
"""KW-FIX-45 11-12: the place stage may target the hub (as ot-run 'localhost', capped by ot-run), no other stage."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def test_default_drops_hub(self):
        self.assertEqual(kw.target_hosts(["epyc8", "intel2", "localhost", "epyc9"], "intel2"), ["epyc8", "epyc9"])
        self.assertEqual(kw.target_hosts(["intel2"], "intel2"), [])

    def test_place_keeps_hub_once_last(self):
        self.assertEqual(kw.target_hosts(["epyc2", "intel2", "epyc9", "localhost"], "intel2", True), ["epyc2", "epyc9", "localhost"])
        self.assertEqual(kw.target_hosts(["epyc2"], "intel2", True), ["epyc2"])

if __name__ == "__main__":
    unittest.main()
