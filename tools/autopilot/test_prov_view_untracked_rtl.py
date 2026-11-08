#!/usr/bin/env python3
"""DIE-HBM-91-KCLS 11-08 (class k1): contract-abstract pin directions in a staged wave src.

The wave src (kw33/src_d95ec) is a newer tree rsynced over an old .git, so RTL added since the old index
(rtl/hbm_accel/cores_split/reform_1106/ot_pdie_serdes_rx_bm3.sv: ot_pdie_serdes_rx_bm3_rest, ot_pdie_serdes_rx_bm_native)
is untracked there.  rtl_dirs must still find its ports (git grep --untracked); a pins_file kept only as .gz is read.
"""
import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prov_view as P

RTL = """module ot_tracked (input wire clk, output wire [3:0] q);
endmodule
"""
NEW = """module ot_new_split #(parameter integer N = 2) (
    input  wire          clk,
    input  wire [N-1:0]  S,
    output wire [7:0]    lam
);
endmodule
"""


def _git(d, *a):
    subprocess.run(["git", "-C", d, *a], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


class UntrackedRtl(unittest.TestCase):
    def setUp(self):
        P._RTL_CACHE.clear()
        self.td = tempfile.TemporaryDirectory()
        d = self.td.name
        os.makedirs(os.path.join(d, "rtl", "a", "b", "c"))
        open(os.path.join(d, "rtl", "old.sv"), "w").write(RTL)
        _git(d, "init", "-q")
        _git(d, "add", "rtl/old.sv")
        _git(d, "commit", "-q", "-m", "old index")
        # rsynced later over the old .git: deep and untracked (the os.walk fallback would not reach it either)
        open(os.path.join(d, "rtl", "a", "b", "c", "new_split.sv"), "w").write(NEW)

    def tearDown(self):
        self.td.cleanup()

    def test_untracked_definition_found(self):
        dirs, f = P.rtl_dirs("ot_new_split", [self.td.name])
        self.assertEqual(dirs, {"clk": "input", "S": "input", "lam": "output"})
        self.assertTrue(f.endswith("new_split.sv"))

    def test_tracked_definition_unchanged(self):
        dirs, _ = P.rtl_dirs("ot_tracked", [self.td.name])
        self.assertEqual(dirs, {"clk": "input", "q": "output"})

    def test_absent_module_stays_empty(self):
        self.assertEqual(P.rtl_dirs("ot_nowhere", [self.td.name]), ({}, None))


class GzPins(unittest.TestCase):
    def test_gz_only_pins_file(self):
        with tempfile.TemporaryDirectory() as d:
            with gzip.open(os.path.join(d, "p.json.gz"), "wt") as fh:
                json.dump({"pins": [{"name": "pma_tx[0]", "layer": "M5", "x": 1.0, "y": 2.0}]}, fh)
            got = P.plan_pins({"pins_file": "p.json"}, d)
            self.assertEqual([p["name"] for p in got], ["pma_tx[0]"])

    def test_plain_file_wins(self):
        with tempfile.TemporaryDirectory() as d:
            json.dump([{"name": "a"}], open(os.path.join(d, "p.json"), "w"))
            with gzip.open(os.path.join(d, "p.json.gz"), "wt") as fh:
                json.dump([{"name": "b"}], fh)
            self.assertEqual([p["name"] for p in P.plan_pins({"pins_file": "p.json"}, d)], ["a"])

    def test_missing_both_still_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):
                P.plan_pins({"pins_file": "p.json"}, d)


class CoreTables(unittest.TestCase):
    """Root contract children without RTL of their own (ot_hbm_hc_root_static__hcp_sys1, __tailx_sk_fsr)."""

    def _root(self, d):
        os.makedirs(os.path.join(d, "physical/die_plan/hbm/cores/ports"))
        os.makedirs(os.path.join(d, "physical/die_plan/hbm_arch_cores"))
        os.makedirs(os.path.join(d, "rtl"))
        json.dump({"m__cut": {"m__cut": [["u_core_pop", "input", 1, 0], ["u_core_o", "output", 32, 0], ["x", "bad", 1, 0]]}},
                  open(os.path.join(d, "physical/die_plan/hbm/cores/ports/ports_cut.json"), "w"))
        json.dump({"m__sk": {"files": ["rtl/sk.sv"], "top": "ot_sk_top"}},
                  open(os.path.join(d, "physical/die_plan/hbm_arch_cores/recipes_b2.json"), "w"))
        open(os.path.join(d, "rtl", "sk.sv"), "w").write("module ot_sk_top (input wire clk, output wire [3:0] y);\nendmodule\n")

    def setUp(self):
        P._RTL_CACHE.clear()

    def test_cut_port_table(self):
        with tempfile.TemporaryDirectory() as d:
            self._root(d)
            dirs, src = P.core_table_dirs("m__cut", [d])
            self.assertEqual(dirs, {"u_core_pop": "input", "u_core_o": "output"})
            self.assertEqual(src, ["port table physical/die_plan/hbm/cores/ports/ports_cut.json"])

    def test_recipe_top_rtl(self):
        with tempfile.TemporaryDirectory() as d:
            self._root(d)
            dirs, src = P.core_table_dirs("m__sk", [d])
            self.assertEqual(dirs, {"clk": "input", "y": "output"})
            self.assertEqual(src, ["recipe top ot_sk_top"])

    def test_unknown_module_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self._root(d)
            self.assertEqual(P.core_table_dirs("nope", [d]), ({}, []))

    def test_two_recipe_tops_ambiguous(self):
        with tempfile.TemporaryDirectory() as d:
            self._root(d)
            os.makedirs(os.path.join(d, "physical/die_plan/hbm/cores/harden"))
            json.dump({"m__sk__1x1": {"files": [], "top": "other_top"}},
                      open(os.path.join(d, "physical/die_plan/hbm/cores/harden/recipes_split.json"), "w"))
            self.assertEqual(P.core_table_dirs("m__sk", [d]), ({}, []))


if __name__ == "__main__":
    unittest.main()
