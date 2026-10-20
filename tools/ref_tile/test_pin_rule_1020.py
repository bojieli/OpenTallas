"""OWNER 10-20 ~09:05 pin-register rule in the pre-route gate and the kit generator (ROOT8-RULES): pin registers are
required only at region crossings (landing rings) and on wires over the 405 um reach (textbook wire_reach, see
tools/test_textbook_pin_rule_1020.py); same-region tiles may connect directly.  The strict 10-15 every-pin form stays
behind spec "pin_regs_rule": "every_pin" / env OT_PIN_REGS_STRICT=1."""
import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import ref_tile as RT  # noqa: E402
import pre_route_gate as PG  # noqa: E402

LATE = dt.datetime.fromisoformat("2026-10-20T10:00:00-07:00")


def sev(kd, spec):
    g = PG.Gate()
    PG.check_pin_regs(g, kd, spec, now=LATE)
    return [i["severity"] for i in g.items if i["check"] == "pin_regs"]


class PinRule1020(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.kd = Path(self.td.name)
        (self.kd / "kit.env").write_text("EXTRA=(--orfs-var OT_KEEP_PIN_REGS=1)\n")      # no OT_PIN_REGS=1

    def tearDown(self):
        self.td.cleanup()

    def test_same_region_kit_without_pin_regs_is_info(self):
        self.assertEqual(sev(self.kd, {}), ["INFO"])
        self.assertEqual(sev(self.kd, {"pin_regs": {"enable": False}}), ["INFO"])            # no reason needed

    def test_region_crossing_without_pin_regs_fails(self):
        self.assertEqual(sev(self.kd, {"region_crossing_ports": "^xr_"}), ["FAIL"])
        self.assertEqual(sev(self.kd, {"region_crossing_ports": "^xr_",
                                       "pin_regs": {"enable": False, "reason": "kit lands xr_* in an OT_LANDED ring"}}),
                         ["INFO"])

    def test_strict_form_is_opt_in(self):
        self.assertEqual(sev(self.kd, {"pin_regs_rule": "every_pin"}), ["FAIL"])
        os.environ["OT_PIN_REGS_STRICT"] = "1"
        try:
            self.assertEqual(sev(self.kd, {}), ["FAIL"])
        finally:
            del os.environ["OT_PIN_REGS_STRICT"]

    def test_plan_opt_out_reason(self):
        base = {"kind": "tile", "clock_port": "clk"}
        self.assertFalse(RT.pin_regs_plan(dict(base, pin_regs={"enable": False}))["enable"])
        for extra in ({"pin_regs_rule": "every_pin"}, {"region_crossing_ports": "^xr_"}):
            with self.assertRaises(RT.SpecError):
                RT.pin_regs_plan(dict(base, pin_regs={"enable": False}, **extra))
        # a kit that inserts pin registers records the same rule text as before (generated kits stay byte-identical)
        self.assertEqual(RT.pin_regs_plan(dict(base, pin_regs={"enable": True}))["rule"], RT.PIN_REGS_RULE_STRICT)


if __name__ == "__main__":
    unittest.main()
