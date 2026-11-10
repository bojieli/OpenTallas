#!/usr/bin/env python3
"""future_lec_commit pins the future-LEC snapshot of a new attempt (KW-FIX-43 11-10, COORD LEC class fix)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW


class FutureLecCommit(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.orig = KW.future_lec_snapshot
        KW.future_lec_snapshot = lambda snapshot, commit=None: self.calls.append((snapshot, commit)) or {"commit": commit}

    def tearDown(self):
        KW.future_lec_snapshot = self.orig

    def test_pin_sources(self):
        cfg = {"dies": {"hbm": {}, "s81": {"future_lec_commit": "d" * 40}}}
        KW.future_lec_for(cfg, "hbm", "/x")                      # unset: scheduler checkout HEAD
        cfg["future_lec_commit"] = "g" * 40
        KW.future_lec_for(cfg, "hbm", "/x")                      # global pin
        KW.future_lec_for(cfg, "s81", "/y")                      # die pin wins
        self.assertEqual([c for _, c in self.calls], [None, "g" * 40, "d" * 40])
        self.assertEqual(self.calls[-1][0], "/y")


if __name__ == "__main__":
    unittest.main()
