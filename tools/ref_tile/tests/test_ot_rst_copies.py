"""KV-RELAYGEN 2026-10-19: physical/common_flow/ot_rst_copies.py (regional reset relay copies) on synthetic netlists."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("ot_rst_copies", ROOT / "physical/common_flow/ot_rst_copies.py")
RS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RS)


def ff(d, c, r, q, typ="$_DFF_PN0_"):
    return {"type": typ, "port_directions": {"C": "input", "D": "input", "R": "input", "Q": "output"},
            "connections": {"C": [c], "D": [d], "R": [r], "Q": [q]}}


def netlist(n_copies=3, loads=600, bad_copy=False, mixed=0, wide=0, name="u_m.u_rst_relay.rst_n"):
    cells, nb = {}, 100
    copies = list(range(10, 10 + n_copies))
    for k, q in enumerate(copies):
        cells[f"u_m.u_rst_relay.relay_q[0][{k}]$_DFF_PN0_"] = ff(7 if (bad_copy and k == 2) else 5, 2, 3, q)
    for i in range(loads):
        cells[f"u_m.u_core.r{i}$_DFF_PN0_"] = ff(nb, 2, copies[0], nb + 1)
        nb += 2
    for i in range(mixed):
        cells[f"u_m.and{i}"] = {"type": "$and", "port_directions": {"A": "input", "B": "input", "Y": "output"},
                                "connections": {"A": [copies[0], 4], "B": [4, 4], "Y": [nb, nb + 1]}}
        nb += 2
    for i in range(wide):
        cells[f"u_m.u_w.v{i}"] = {"type": "$adff", "parameters": {"WIDTH": "00000000000000000000000001000000"},
                                  "port_directions": {"CLK": "input", "ARST": "input", "D": "input", "Q": "output"},
                                  "connections": {"CLK": [2], "ARST": [copies[0]], "D": list(range(nb, nb + 64)),
                                                  "Q": list(range(nb + 64, nb + 128))}}
        nb += 128
    return {"modules": {"top": {"attributes": {"top": "00000000000000000000000000000001"}, "ports": {},
                                "cells": cells, "netnames": {name: {"bits": copies}, "rst_c": {"bits": copies}}}}}


class T(unittest.TestCase):
    def run_nl(self, nl, mx=256):
        with tempfile.TemporaryDirectory() as td:
            j = Path(td) / "in.json"
            j.write_text(json.dumps(nl))
            rc = RS.main(["--json", str(j), "--max", str(mx), "--ys", f"{td}/o.ys", "--tsv", f"{td}/o.tsv"])
            return rc, (Path(td) / "o.ys").read_text(), (Path(td) / "o.tsv").read_text()

    def test_split_even(self):
        rc, ys, tsv = self.run_nl(netlist())
        self.assertEqual(rc, 0)
        row = tsv.splitlines()[1].split("\t")
        self.assertEqual(row[1:6], ["3", "600", "0", "400", "200,200,200"])
        self.assertEqual(row[6], "OK")
        self.assertEqual(ys.count("connect -port"), 400)
        self.assertEqual(ys.count("add -wire"), 3)
        self.assertIn("connect -set \\ot_rrs__", ys)
        self.assertTrue(ys.startswith("cd \\top\n"))

    def test_dedup_alias_names(self):
        _, _, tsv = self.run_nl(netlist())
        self.assertEqual(len(tsv.splitlines()), 2)      # rst_c alias does not match the regex; one family

    def test_refuse_non_identical(self):
        _, ys, tsv = self.run_nl(netlist(bad_copy=True))
        self.assertIn("REFUSED copies are not identical", tsv)
        self.assertNotIn("connect -port", ys)

    def test_over_reported(self):
        _, _, tsv = self.run_nl(netlist(n_copies=2, loads=600))
        self.assertIn("OVER max 256", tsv)
        self.assertIn("REGIONS >= 3", tsv)

    def test_mixed_port_stays(self):
        _, ys, tsv = self.run_nl(netlist(loads=300, mixed=5))
        row = tsv.splitlines()[1].split("\t")
        self.assertEqual(row[3], "5")
        self.assertNotIn("and0", ys)

    def test_wide_flop_weight(self):
        _, ys, tsv = self.run_nl(netlist(loads=0, wide=9))
        row = tsv.splitlines()[1].split("\t")
        self.assertEqual(row[2], str(9 * 64))
        self.assertEqual(sorted(map(int, row[5].split(","))), [192, 192, 192])

    def test_repeated_multibit_port_uses_named_alias(self):
        nl = netlist(loads=0)
        cells = nl["modules"]["top"]["cells"]
        for i in range(3):
            cells[f"u_m.repeat{i}"] = {"type": "$and", "port_directions": {"A": "input", "B": "input", "Y": "output"},
                "connections": {"A": [10, 10], "B": [4, 4], "Y": [100+2*i, 101+2*i]}}
        _, ys, tsv = self.run_nl(nl)
        self.assertNotIn("{", ys)
        self.assertIn("__c1__v2 2", ys)
        self.assertIn("__c1__v2[0]", ys)
        self.assertIn("__c1__v2[1]", ys)
        self.assertIn("repeat1 A \\ot_rrs__", ys)
        self.assertIn("3\t6\t0\t2\t2,2,2\tOK", tsv)

    def test_landing_family_name(self):
        _, _, tsv = self.run_nl(netlist(name="host_rst_n__ot_rlv"))
        self.assertIn("host_rst_n__ot_rlv\t3\t600", tsv)

    def test_attribute_marked_family(self):
        nl = netlist(name="u_m.rst_n_x")
        nl["modules"]["top"]["netnames"]["u_m.rst_n_x"]["attributes"] = {"ot_rst_split": "00000000000000000000000000000001"}
        _, _, tsv = self.run_nl(nl)
        self.assertIn("u_m.rst_n_x\t3\t600", tsv)

    # KV-PC6 10-20: per-group kept decision leaves (hgo of qkd_kvs_pc: 192 copies, 24 ot_kvpc5_and2 enables)
    def leaf_nl(self, leaf_type="ot_kvpc5_and2", leaf_cells=None, bad_input=False):
        nl = netlist(n_copies=4, loads=400, name="u_m.hgo_qv")
        mods = nl["modules"]
        mods["top"]["netnames"]["u_m.hgo_qv"]["attributes"] = {"ot_rst_split": "00000000000000000000000000000001"}
        cells = mods["top"]["cells"]
        mods[leaf_type] = {"attributes": {"keep_hierarchy": "00000000000000000000000000000001"},
                           "ports": {"a": {"direction": "input", "bits": [2]}, "b": {"direction": "input", "bits": [3]},
                                     "y": {"direction": "output", "bits": [4]}},
                           "cells": leaf_cells if leaf_cells is not None else {"$and$1": {"type": "$and",
                               "connections": {"A": [2], "B": [3], "Y": [4]}}}}
        for k in range(4):
            en = 60 + k
            cells[f"u_m.g[{k}].u_go"] = {"type": leaf_type,
                "port_directions": {"a": "input", "b": "input", "y": "output"},
                "connections": {"a": [8 if (bad_input and k == 3) else 6], "b": [3], "y": [en]}}
            name = next(n for n in cells if n.startswith("u_m.u_rst_relay.relay_q[0][%d]" % k))
            cells[name] = {"type": "$_SDFFE_PN0P_", "port_directions": {"C": "input", "D": "input", "R": "input",
                           "E": "input", "Q": "output"}, "connections": {"C": [2], "D": ["1"], "R": [3], "E": [en],
                           "Q": [10 + k]}}
        return nl

    def test_leaf_equivalent_enables_accepted(self):
        _, ys, tsv = self.run_nl(self.leaf_nl(), mx=100)
        row = tsv.splitlines()[1].split("\t")
        self.assertEqual(row[0], "u_m.hgo_qv")
        self.assertEqual(row[6], "OK")
        self.assertEqual(row[5], "100,100,100,100")
        self.assertEqual(ys.count("connect -port"), 300)

    def test_leaf_different_inputs_refused(self):
        _, ys, tsv = self.run_nl(self.leaf_nl(bad_input=True))
        self.assertIn("REFUSED copies are not identical", tsv)
        self.assertNotIn("connect -port", ys)

    def test_sequential_leaf_refused(self):
        seq = {"r": {"type": "$dff", "connections": {"CLK": [2], "D": [3], "Q": [4]}}}
        _, ys, tsv = self.run_nl(self.leaf_nl(leaf_type="ot_seq_leaf", leaf_cells=seq))
        self.assertIn("REFUSED copies are not identical", tsv)
        self.assertNotIn("connect -port", ys)

    def test_undefined_leaf_refused(self):
        nl = self.leaf_nl(leaf_type="ot_bb_leaf")
        nl["modules"]["ot_bb_leaf"]["attributes"]["blackbox"] = "00000000000000000000000000000001"
        _, _, tsv = self.run_nl(nl)
        self.assertIn("REFUSED copies are not identical", tsv)

    def test_primitive_and_not_looked_through(self):
        nl = self.leaf_nl()
        for k in range(4):
            c = nl["modules"]["top"]["cells"][f"u_m.g[{k}].u_go"]
            c["type"] = "$and"
            c["port_directions"] = {"A": "input", "B": "input", "Y": "output"}
            c["connections"] = {"A": [6], "B": [3], "Y": [60 + k]}
        _, _, tsv = self.run_nl(nl)
        self.assertIn("REFUSED copies are not identical", tsv)

    def test_single_bit_relay_untouched(self):
        nl = netlist(n_copies=1)
        _, ys, tsv = self.run_nl(nl)
        self.assertEqual(len(tsv.splitlines()), 1)
        self.assertEqual(ys, "cd \\top\ncd ..\n")


if __name__ == "__main__":
    unittest.main()
