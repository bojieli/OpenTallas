#!/usr/bin/env python3
"""FLOW-HOLD 2026-10-16: spec "hold_budget": "die" (results/arch/boundary_hold_budget_1016/RULE.md).
Default kits regenerate without any OT_BH line; a die-budget kit drops the pin hold pads, carries the credited boundary
min delays in sign-off and route, and repairs the boundary at margin 0; non-qualifying specs are refused."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import clock_entry_constraints as CEC  # noqa: E402
import ref_tile as RT  # noqa: E402

SPEC = RT.ROOT / "tools/ref_tile/specs_hcoll_v5/hcoll_v5_ctl2.json"


def gen(mut=None):
    d = json.loads(SPEC.read_text())
    if mut:
        mut(d)
    tmp = SPEC.parent / f"_hold_budget_test_{id(d)}.json"
    tmp.write_text(json.dumps(d))
    try:
        out = Path(tempfile.mkdtemp())
        r = RT.gen(str(tmp), out_root=out)
        return out / r["kit"]
    finally:
        tmp.unlink()


@unittest.skipUnless(SPEC.exists(), "ctl2 spec not checked out")
class HoldBudget(unittest.TestCase):
    def test_default_kit_has_no_budget_lines(self):
        k = gen()
        sdc = (k / "signoff.sdc").read_text()
        self.assertNotIn("OT_BH", sdc)
        self.assertNotIn("OT_IO_HOLD_BUDGET", sdc)
        self.assertNotIn("OT_IO_HOLD_BUDGET", (k / "kit.env").read_text())

    def test_die_kit(self):
        k = gen(lambda d: d.update(hold_budget="die"))
        sdc = (k / "signoff.sdc").read_text()
        env = (k / "kit.env").read_text()
        self.assertIn("set ::env(OT_IO_HOLD_BUDGET) die", sdc)
        self.assertIn("set ::env(OT_BH_ROUTE_RELIEF_PS) 0", sdc)
        self.assertIn("set_input_delay [expr $qdm_lmin + $ot_bhc + $ot_bhu + $ot_bhr] -min", sdc)
        # setup side unchanged
        self.assertIn("set_input_delay [expr $ot_ib + $qdm_lmax + $ot_sk] -max", sdc)
        self.assertIn("OT_IO_HOLD_BUDGET=die", env)
        self.assertNotIn("OT_INHOLD_MASTER", env)
        self.assertNotIn("OT_IOHOLD_IN", env)
        spec = json.loads((k / "spec.json").read_text())
        self.assertFalse(spec["inhold"])
        self.assertFalse(spec["outhold"])
        self.assertEqual(spec["route"]["io_hold_margin_ns"], 0.0)
        ffr = (k / "signoff_ffrepair.sdc").read_text()
        relief = round(spec["route"]["hold_margin_ns"] * 1000)
        self.assertIn(f"set ::env(OT_BH_ROUTE_RELIEF_PS) {relief}", ffr)
        self.assertIn(f"OT_BH_ROUTE_RELIEF_PS={relief}", env)

    def test_die_refuses_pads(self):
        with self.assertRaises(RT.SpecError):
            gen(lambda d: d.update(hold_budget="die", inhold=True))

    def test_die_refuses_pin_exclusion(self):
        with self.assertRaises(RT.SpecError):
            gen(lambda d: d.update(hold_budget="die", pin_regs={"enable": True, "exclude": "^x", "reason": "r"}))

    def test_unknown_value(self):
        with self.assertRaises(RT.SpecError):
            gen(lambda d: d.update(hold_budget="half"))


class Strip(unittest.TestCase):
    def test_strip(self):
        t = "a\n# OT_BH begin x\nb\n# OT_BH end\nc\nd ;# OT_BH\ne"
        self.assertEqual(CEC.strip_hold_budget(t, False), "a\nc\ne")
        self.assertEqual(CEC.strip_hold_budget(t, True), t)


if __name__ == "__main__":
    unittest.main()
