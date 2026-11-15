#!/usr/bin/env python3
"""KW-FIX-35 11-08 (KW-PROV-1): a staged wave src whose .gitignore is `*` (kw33/src_d95ec) must still index tracked
RTL and untracked RTL under rtl/ (git grep --untracked alone returns nothing there)."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prov_view as P

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def _git(d, *a):
    subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, env=ENV)


class IgnoreAll(unittest.TestCase):
    def setUp(self):
        P._RTL_CACHE.clear()
        P._RTL_ROOT_INDEX.clear()
        self.td = tempfile.TemporaryDirectory()
        d = self.td.name
        os.makedirs(os.path.join(d, "rtl", "physical", "a0_core"))
        os.makedirs(os.path.join(d, "rtl", "x", "y", "z"))
        open(os.path.join(d, "rtl", "physical", "a0_core", "t.sv"), "w").write(
            "module qfd_tile_t (input wire clk, input wire [3:0] n_a, output wire [1:0] q);\nendmodule\n")
        _git(d, "init", "-q")
        _git(d, "add", "rtl")
        _git(d, "commit", "-q", "-m", "i")
        open(os.path.join(d, ".gitignore"), "w").write("*\n")
        open(os.path.join(d, "rtl", "x", "y", "z", "n.sv"), "w").write(
            "module ot_untracked_new (input wire a, output wire b);\nendmodule\n")

    def tearDown(self):
        self.td.cleanup()

    def test_tracked_found_under_ignore_all(self):
        dirs, f = P.rtl_dirs("qfd_tile_t", [self.td.name])
        self.assertEqual(dirs, {"clk": "input", "n_a": "input", "q": "output"})
        self.assertTrue(f.endswith("t.sv"))

    def test_untracked_rtl_found_under_ignore_all(self):
        dirs, f = P.rtl_dirs("ot_untracked_new", [self.td.name])
        self.assertEqual(dirs, {"a": "input", "b": "output"})


if __name__ == "__main__":
    unittest.main()
