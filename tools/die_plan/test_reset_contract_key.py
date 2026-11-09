"""RESET-KEY 11-09: landing clones <type>__cl<hex> resolve to their base type's die reset contract entry."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_reset_contract as KRC  # noqa: E402
import lec  # noqa: E402

MODS = ["s81p_col_h9_r0_p2__t1", "s81p_ot_s81sl_leaf__t40", "kv3_pc__cl254f2e73", "dsdv_gunit_l0"]


class Member(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(lec.reset_contract_member("dsdv_gunit_l0", MODS), ("dsdv_gunit_l0", "exact"))
        self.assertEqual(lec.reset_contract_member("kv3_pc__cl254f2e73", MODS), ("kv3_pc__cl254f2e73", "exact"))

    def test_clone_base_through_die_prefix(self):
        self.assertEqual(lec.reset_contract_member("col_h9_r0_p2__t1__cl0045af7b", MODS),
                         ("s81p_col_h9_r0_p2__t1", "clone_base"))
        self.assertEqual(lec.reset_contract_member("ot_s81sl_leaf__t40__cl86ea32b3__sid5S", MODS),
                         ("s81p_ot_s81sl_leaf__t40", "clone_base"))
        self.assertEqual(lec.reset_contract_member("s81p_col_h9_r0_p2__t1__cl0045af7b", MODS),
                         ("s81p_col_h9_r0_p2__t1", "clone_base"))

    def test_not_covered(self):
        self.assertEqual(lec.reset_contract_member("col_h9_r0_p3__t1__cl0cd90c0e", MODS), (None, None))
        self.assertEqual(lec.reset_contract_member("col_h9_r0_p2__t1", MODS), (None, None))  # no clone suffix

    def test_ambiguous_and_near_miss_are_errors(self):
        with self.assertRaisesRegex(ValueError, "several"):
            lec.reset_contract_member("a__t1__cl00000000", ["s81p_a__t1", "hbm_a__t1"])
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            lec.reset_contract_member("a__t1__cl00000000", ["x_y_z_a__t1"])


class GateAndStage(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "src" / "reset_contract").mkdir(parents=True)
        r = self.d / "src" / "reset_contract" / "receipt.txt"
        r.write_text("proof\n")
        self.src = self.d / "src" / "reset_contract.json"
        self.src.write_text(json.dumps({"schema": "opentallas.reset_contract.v1", "die": "s81", "edges": 64,
                                        "modules": MODS, "proof": {
                                            "verdict": "PASS", "assert_edges": 66, "mutant": "CAUGHT",
                                            "receipt": "reset_contract/receipt.txt",
                                            "receipt_sha256": hashlib.sha256(r.read_bytes()).hexdigest()}}))

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_clone_kit_staged_and_granted_64(self):
        kd = self.d / "kit"
        kd.mkdir()
        got = KRC.stage(kd, "col_h9_r0_p2__t1__cl0045af7b", self.src)
        self.assertEqual((got["edges"], got["listed_as"]), (64, "s81p_col_h9_r0_p2__t1"))
        env = {}
        rep = lec.reset_contract_gate(kd, "col_h9_r0_p2__t1__cl0045af7b", environ=env)
        self.assertEqual((rep["used"], env["OT_LEC_RESET_CYCLES"]), (64, "64"))
        self.assertEqual(rep["contract"]["listed_as"], "s81p_col_h9_r0_p2__t1")

    def test_uncovered_clone_untouched(self):
        kd = self.d / "kit2"
        kd.mkdir()
        self.assertIsNone(KRC.stage(kd, "col_h9_r0_p3__t1__cl0cd90c0e", self.src))
        self.assertFalse((kd / "reset_contract.json").exists())

    def test_near_miss_is_flow_error(self):
        c = json.loads(self.src.read_text())
        c["modules"] = ["x_y_z_a__t1"]
        self.src.write_text(json.dumps(c))
        rep = lec.reset_contract_gate(self.src.parent, "a__t1__cl00000000",
                                      environ={"OT_LEC_RESET_CONTRACT": str(self.src)})
        self.assertIn("flow_error", rep)
        with self.assertRaises(SystemExit):
            KRC.stage(self.d, "a__t1__cl00000000", self.src)


if __name__ == "__main__":
    unittest.main()
