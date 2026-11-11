#!/usr/bin/env python3
"""kit_tree_mix_lint: rtl/ <-> r18h5_bundle parent/child parameter mixes (HBM-HUB-RTL-1 11-11, class of
hbm-hub-gather-phase).  Synthetic trees: the q_hub shape (rtl parent passes RESP only, bundle child adds PERIOD with a
default) FAILS; identical copies, a parent that pins the parameter, and a registry proof keyed by file sha256 pass; one
byte changed in a proven file voids the proof."""
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_tree_mix_lint as L

BUN = "physical/die_plan/hbm/bind/r18h5_bundle/rtl"
CHILD_RTL = "module rd #(parameter integer RESP=19)(input wire clk); endmodule\n"
CHILD_BUN = "module rd #(parameter integer RESP=19, parameter integer PERIOD=24)(input wire clk); endmodule\n"


def tree(root, parent_set="", child_bun=CHILD_BUN):
    (root / "rtl/q").mkdir(parents=True)
    (root / BUN / "q").mkdir(parents=True)
    (root / "rtl/q/qs.sv").write_text(f"module qs(input wire clk);\n rd #(.RESP(174){parent_set}) u (.clk(clk));\nendmodule\n")
    (root / "rtl/q/rd.sv").write_text(CHILD_RTL)
    (root / BUN / "q/rd.sv").write_text(child_bun)
    kit = root / "kit_rtl.f"
    kit.write_text(f"{root}/rtl/q/qs.sv\n{root}/{BUN}/q/rd.sv\n")
    return kit


class T(unittest.TestCase):
    def setUp(self):
        L._cache.clear()
        self.d = Path(tempfile.mkdtemp())

    def test_qhub_shape_fails(self):
        r = L.lint(tree(self.d))
        self.assertEqual(len(r["mix_param"]), 1)
        x = r["mix_param"][0]
        self.assertEqual((x["parent"], x["parent_tree"], x["child"], x["child_tree"]), ("qs", "rtl", "rd", "bundle"))
        self.assertEqual(x["unset_param_diff"], {"PERIOD": ["24", None]})
        self.assertEqual(L.main([str(self.d / "kit_rtl.f"), "--registry", str(self.d / "none.json")]), 1)

    def test_parent_pins_param_passes(self):
        r = L.lint(tree(self.d, parent_set=", .PERIOD(175)"))
        self.assertEqual((r["mixed_edges"], r["safe_mix"], r["mix_param"]), (1, 1, []))

    def test_identical_copies_pass(self):
        r = L.lint(tree(self.d, child_bun=CHILD_RTL))
        self.assertEqual((r["safe_mix"], r["mix_param"]), (1, []))

    def test_registry_proof_by_sha(self):
        kit = tree(self.d)
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        entry = dict(module="rd", pick_files={"bundle:q/rd.sv": sha(self.d / BUN / "q/rd.sv")},
                     twin_files={"rtl:q/rd.sv": sha(self.d / "rtl/q/rd.sv")}, domain={"RESP": ["174"]},
                     results=[dict(params={"RESP": "174"}, proven=True)])
        reg = self.d / "reg.json"
        reg.write_text(json.dumps(dict(proofs=[entry])))
        r = L.lint(kit, [entry])
        self.assertEqual((r["proven"], r["mix_param"]), (["qs->rd"], []))
        self.assertEqual(L.main([str(kit), "--registry", str(reg)]), 0)
        # a parent that sets a parameter outside the proven domain is not covered
        L._cache.clear()
        (self.d / "rtl/q/qs.sv").write_text("module qs(input wire clk);\n rd #(.RESP(174),.X(1)) u (.clk(clk));\nendmodule\n")
        self.assertEqual(len(L.lint(kit, [entry])["mix_param"]), 1)
        # one byte changed in a proven file voids the proof
        L._cache.clear()
        (self.d / "rtl/q/qs.sv").write_text("module qs(input wire clk);\n rd #(.RESP(174)) u (.clk(clk));\nendmodule\n")
        (self.d / BUN / "q/rd.sv").write_text(CHILD_BUN + "\n")
        self.assertEqual(len(L.lint(kit, [entry])["mix_param"]), 1)

    def test_other_tree_ignored(self):
        (self.d / "gen").mkdir()
        (self.d / "gen/top.sv").write_text("module top(input wire clk); rd u (.clk(clk)); endmodule\n")
        (self.d / BUN / "q").mkdir(parents=True)
        (self.d / BUN / "q/rd.sv").write_text(CHILD_BUN)
        kit = self.d / "k.f"
        kit.write_text(f"{self.d}/gen/top.sv\n{self.d}/{BUN}/q/rd.sv\n")
        self.assertEqual(L.lint(kit)["mixed_edges"], 0)


if __name__ == "__main__":
    unittest.main()
