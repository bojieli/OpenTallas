#!/usr/bin/env python3
"""PATH-KV-ASTK2 10-25: unit tests of replica_check.py (hierarchical + flat netlists, merged-replica mutants).
run: python3 -m unittest test_replica_check   (from this directory)"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replica_check  # noqa: E402

SPEC = {"rules": [
    {"name": "wdec", "module": "qkd_astk_wdec", "inst_re": r"g_zn_(\d)_u_zn[./]u_wd$", "groups": ["0", "1", "2", "3"],
     "ff_per_inst": 3},
    {"name": "zh", "module": "qkd_astk_zhrep", "inst_re": r"u_ctl[./]g_zh\\?\[(\d+)\\?\][./]u_zh$", "groups": ["0", "1"],
     "ff_per_inst": 2}]}


def wdec_mod(nff=3):
    cells = "\n".join(f"  DFFHQNx1_ASAP7_75t_R \\kt_r_reg[{i}]  (.CLK(ck), .D(d[{i}]), .QN(q[{i}]));" for i in range(nff))
    return f"module qkd_astk_wdec(ck, d, q);\n  input ck;\n  input [2:0] d;\n  output [2:0] q;\n{cells}\nendmodule\n"


ZH = ("module qkd_astk_zhrep(ck, q);\n  input ck;\n  output [1:0] q;\n"
      "  DFFHQNx1_ASAP7_75t_R \\q_reg[0]  (.CLK(ck));\n  DFFHQNx1_ASAP7_75t_R \\q_reg[1]  (.CLK(ck));\nendmodule\n")


def top(zones=(0, 1, 2, 3), zh=(0, 1), extra=""):
    insts = "\n".join(f"  qkd_astk_wdec \\u_u_strip_u_strip_g_zn_{z}_u_zn.u_wd  (.ck(ck));" for z in zones)
    insts += "\n" + "\n".join(f"  qkd_astk_zhrep \\u_u_strip_u_strip_u_ctl.g_zh[{k}].u_zh  (.ck(ck));" for k in zh)
    return (f"module kv3_astk(ck);\n  input ck;\n  wire \\x.y ;\n{insts}\n"
            "  DFFHQNx1_ASAP7_75t_R \\u_u_strip_u_strip_g_zn_2_u_zn.zq$_DFF_P_  (.CLK(ck));\n"
            f"  BUFx2_ASAP7_75t_R _1_ (.A(ck));\n{extra}endmodule\n")


def flat(zones=(0, 1, 2, 3), nff=3):
    lines = [f"  DFFHQNx1_ASAP7_75t_R \\u_u_strip_u_strip_g_zn_{z}_u_zn.u_wd/kt_r_reg[{i}]  (.CLK(ck));"
             for z in zones for i in range(nff)]
    lines += [f"  DFFHQNx1_ASAP7_75t_R \\u_u_strip_u_strip_u_ctl.g_zh[{k}].u_zh/q_reg[{i}]  (.CLK(ck));"
              for k in (0, 1) for i in (0, 1)]
    return "module kv3_astk(ck);\n  input ck;\n" + "\n".join(lines) + "\nendmodule\n"


class ReplicaCheck(unittest.TestCase):
    def run_check(self, netlist, spec=SPEC):
        with tempfile.TemporaryDirectory() as d:
            n, s, o = Path(d) / "n.v", Path(d) / "s.json", Path(d) / "o.json"
            n.write_text(netlist)
            s.write_text(json.dumps(spec))
            rc = replica_check.main(["--expect", str(s), "--netlist", str(n), "--out", str(o)])
            return rc, json.loads(o.read_text())

    def test_hier_pass(self):
        rc, r = self.run_check(wdec_mod() + ZH + top())
        self.assertEqual((rc, r["verdict"]), (0, "PASS"))
        self.assertEqual(r["rules"][0]["ff_total"], 12)

    def test_flat_pass(self):
        rc, r = self.run_check(flat())
        self.assertEqual((rc, r["verdict"]), (0, "PASS"))

    def test_merged_zone_mutant_fails(self):
        # opt_merge folded zn_0/1/3 into zn_2's copy (the W2 failure): only one wdec instance survives
        rc, r = self.run_check(wdec_mod() + ZH + top(zones=(2,)))
        self.assertEqual((rc, r["verdict"]), (1, "FAIL"))
        self.assertEqual(r["rules"][0]["missing"], ["0", "1", "3"])

    def test_merged_bits_mutant_fails(self):
        # replicas kept as instances but bits merged inside (2 of 3 flops left)
        rc, r = self.run_check(wdec_mod(2) + ZH + top())
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(r["rules"][0]["bad"]), ["0", "1", "2", "3"])

    def test_flat_merged_mutant_fails(self):
        rc, r = self.run_check(flat(zones=(0, 2)))
        self.assertEqual(rc, 1)
        self.assertEqual(r["rules"][0]["missing"], ["1", "3"])

    def test_extra_instance_fails(self):
        rc, r = self.run_check(wdec_mod() + ZH + top(zh=(0, 1, 2)))
        self.assertEqual(rc, 1)
        self.assertEqual(r["rules"][1]["extra"], ["2"])

    def test_wrong_module_fails(self):
        # a paramod-renamed or different module under the replica path is not the declared replica
        pm = "\\$paramod$abc\\qkd_astk_wdec"     # yosys: module \$paramod$abc\qkd_astk_wdec (...)
        net = (wdec_mod().replace("module qkd_astk_wdec(", "module " + pm + " (") + ZH
               + top().replace("qkd_astk_wdec \\", pm + " \\"))
        rc, r = self.run_check(net)
        self.assertEqual(rc, 1)
        self.assertTrue(r["rules"][0]["module_mismatch"])

    def test_empty_netlist_errors(self):
        rc, r = self.run_check("// nothing\n")
        self.assertEqual((rc, r["verdict"]), (2, "ERROR"))


if __name__ == "__main__":
    unittest.main()
