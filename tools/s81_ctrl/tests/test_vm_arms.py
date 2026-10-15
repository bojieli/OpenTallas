import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vm_arms import compact_arg, insert_arms
from stage_programs import ROOT


class VMArms(unittest.TestCase):
    def program(self):
        return {"ops": [
            dict(id="producer", eng="fld", port=0, dur=7, ext=0, preds=[]),
            dict(id="consume", eng="su", port=1, dur=9, ext=0, preds=[0]),
            dict(id="other", eng="hc", port=2, dur=3, ext=0, preds=[])]}

    def test_arm_before_write_and_slot_reuse(self):
        result = insert_arms(self.program(), {
            "consume": dict(base_row=32, nrows=8, producers=["producer"]),
            "other": {"give": True}})
        ops = {o["id"]: o for o in result["ops"]}
        self.assertEqual(ops["consume.vm_arm"]["arg"], (2 << 10) | 7)
        self.assertIn(ops["consume.vm_arm"]["op"], ops["producer"]["preds"])
        self.assertIn(ops["consume"]["op"], ops["other.vm_arm"]["preds"])
        self.assertEqual(ops["other.vm_arm"]["arg"], (1 << 20) | (1023 << 10) | 1023)
        self.assertLess(ops["consume.vm_arm"]["op"], ops["producer"]["op"])

    def test_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            insert_arms(self.program(), {})
        with self.assertRaisesRegex(ValueError, "aligned"):
            compact_arg("su", dict(base_row=3, nrows=2, producers=["producer"]))
        with self.assertRaisesRegex(ValueError, "producers"):
            compact_arg("su", dict(base_row=32, nrows=2, producers=[]))

    def test_dependency_cycle(self):
        p = self.program()
        p["ops"][0]["preds"] = [2]
        with self.assertRaisesRegex(ValueError, "cycle"):
            insert_arms(p, {"consume": dict(base_row=32, nrows=8, producers=["producer"]), "other": {"give": True}})

    def test_all_production_stage_capacity(self):
        # GIVE exercises encoding/capacity/order only, not operand ownership.
        programs = [json.loads(path.read_text()) for path in sorted(
            (ROOT / "results/rtl/s81_ctrl_20261008/programs").glob("S[0-9][0-9][0-9].json"))]
        self.assertEqual(len(programs), 59)
        count = 0
        for p in programs:
            bindings = {o["id"]: {"give": True} for o in p["ops"] if o["eng"] in ("su", "hc")}
            armed = insert_arms(p, bindings)
            self.assertLessEqual(armed["n_jobs"], 128)
            self.assertEqual(armed["vm_arm_count"], len(bindings))
            count += len(bindings)
        self.assertGreater(count, 1000)


if __name__ == "__main__":
    unittest.main()
