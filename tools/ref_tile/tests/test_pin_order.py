"""ROOT-PINORDER 2026-10-19 (HBM-HCRING finding): ordered pins across abutted faces.

- pre_route_gate.check_pin_order: an abutted bus (pin_ranges / abutted_ports) wider than 32 b FAILs without a defined
  bit order (route.pin_balance or an exact io_tcl); pin_order_waiver {port: reason} exempts a channel-routed port.
- ref_tile.pin_order_desc_env: pin_order_desc needs its own pin_ranges entry and route.pin_balance.
- run_abi3_physical.io_constraints_tcl: OT_PIN_ORDER_DESC reverses only the named ports; unset = byte-identical.
Pure python (no OpenROAD).
"""
import os
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2]))
import pre_route_gate as PRG  # noqa: E402
import ref_tile as RT  # noqa: E402
import run_abi3_physical as RAP  # noqa: E402


def reg(names, n, face="S", rng=None):
    return {"names": names, "face": face, "range": rng, "n": n}


def st(balance=False, exact=False):
    return {"exact": exact, "balance": balance, "group_max": 1 if balance else 32}


class CheckPinOrder(unittest.TestCase):
    def run_check(self, spec, plan):
        g = PRG.Gate()
        PRG.check_pin_order(g, spec, plan)
        return g

    def test_ranged_wide_bus_without_order_fails(self):
        spec = {"pin_ranges": {"sum_out": [3, 604.4]}}
        g = self.run_check(spec, (st(), [reg(["sum_out"], 2048, rng=(3, 604.4))]))
        self.assertEqual(g.verdict, "FAIL")
        self.assertIn("sum_out (2048 b, S face)", g.items[0]["message"])

    def test_pin_balance_or_exact_io_tcl_passes(self):
        spec = {"pin_ranges": {"sum_out": [3, 604.4]}}
        regs = [reg(["sum_out"], 2048, rng=(3, 604.4))]
        self.assertEqual(self.run_check(spec, (st(balance=True), regs)).verdict, "PASS")
        self.assertEqual(self.run_check(spec, (st(exact=True), regs)).verdict, "PASS")

    def test_narrow_or_unabutted_bus_passes(self):
        spec = {"pin_ranges": {"v": [3, 10]}}
        regs = [reg(["v"], 32, rng=(3, 10)), reg(["wide_plain", "x"], 4096)]   # 32 b ranged; wide but not abutted
        self.assertEqual(self.run_check(spec, (st(), regs)).verdict, "PASS")

    def test_abutted_ports_list_counts(self):
        g = self.run_check({"abutted_ports": ["d"]}, (st(), [reg(["d"], 64)]))
        self.assertEqual(g.verdict, "FAIL")

    def test_unresolved_width_warns(self):
        g = self.run_check({"pin_ranges": {"d": [0, 9]}}, (st(), [reg(["d"], None, rng=(0, 9))]))
        self.assertEqual(g.verdict, "WARN")

    def test_waiver_needs_reason(self):
        spec = {"pin_ranges": {"d": [0, 9]}, "pin_order_waiver": {"d": "channel-routed through the 20 um hub channel"}}
        self.assertEqual(self.run_check(spec, (st(), [reg(["d"], 64, rng=(0, 9))])).verdict, "PASS")
        spec["pin_order_waiver"] = {"d": ""}
        self.assertEqual(self.run_check(spec, (st(), [reg(["d"], 64, rng=(0, 9))])).verdict, "FAIL")

    def test_no_plan_is_silent(self):
        self.assertEqual(self.run_check({"pin_ranges": {"d": [0, 9]}}, None).verdict, "PASS")


class PinOrderDescEnv(unittest.TestCase):
    def test_env(self):
        s = {"pin_ranges": {"s_i": [3, 604.4]}, "pin_order_desc": ["s_i"], "route": {"pin_balance": {"group_max": 1}}}
        self.assertEqual(RT.pin_order_desc_env(s), ["export OT_PIN_ORDER_DESC='s_i'"])
        self.assertEqual(RT.pin_order_desc_env({"route": {}}), [])

    def test_refusals(self):
        with self.assertRaises(RT.SpecError):
            RT.pin_order_desc_env({"pin_ranges": {}, "pin_order_desc": ["s_i"], "route": {"pin_balance": {}}})
        with self.assertRaises(RT.SpecError):
            RT.pin_order_desc_env({"pin_ranges": {"s_i": [0, 1]}, "pin_order_desc": ["s_i"], "route": {}})


class IoConstraintsDesc(unittest.TestCase):
    REGIONS = [{"edge": "bottom", "regex": "^(s_i)$"}, {"edge": "top", "regex": "^(o)$"}]

    def tcl(self, desc):
        old = os.environ.pop("OT_PIN_ORDER_DESC", None)
        try:
            if desc is not None:
                os.environ["OT_PIN_ORDER_DESC"] = desc
            return RAP.io_constraints_tcl(self.REGIONS)
        finally:
            os.environ.pop("OT_PIN_ORDER_DESC", None)
            if old is not None:
                os.environ["OT_PIN_ORDER_DESC"] = old

    def test_unset_is_unchanged(self):
        base = self.tcl(None)
        self.assertEqual(base, self.tcl(""))
        self.assertNotIn("ot_order_pins", base)

    def test_desc_wraps_matches(self):
        t = self.tcl("s_i")
        self.assertIn("set ot_pin_desc {s_i}", t)
        self.assertIn("return [lreverse $names]", t)
        self.assertIn("ot_order_pins [ot_match_pins {^(s_i)$}]", t)

    def test_bad_name_refused(self):
        with self.assertRaises(ValueError):
            self.tcl("s_i[3]")


if __name__ == "__main__":
    unittest.main()
