"""PORT-BUF-AT-PIN (S81-SVCRS-3 11-10): gen_phys type kits source the shared port_buf_at_pin.tcl from their
PRE_DETAIL_PLACE hook; the hook is placement-only and leaves drivers within OT_PBP_MAX_UM (10 um) untouched."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP  # noqa: E402

ROOT = HERE.parents[1]
TCL = ROOT / "physical/common_flow/port_buf_at_pin.tcl"


class PortBufAtPinKit(unittest.TestCase):
    def test_line_sources_kit_copy(self):
        self.assertIn("source /work/port_buf_at_pin.tcl", GP.PORT_BUF_AT_PIN_LINE)

    def test_generator_gated_and_copies(self):
        src = (HERE / "gen_phys.py").read_text()
        self.assertIn('if t.get("port_buf_at_pin", False) is True:', src)
        self.assertIn('kd / "port_buf_at_pin.tcl"', src)

    def test_tcl_placement_only(self):
        body = "\n".join(l for l in TCL.read_text().splitlines() if not l.lstrip().startswith("#"))
        for forbidden in ("insert_buffer", "repair_", "makeInst", "dbInst_create", "connect", "disconnect", "set_dont_touch"):
            self.assertNotIn(forbidden, body)
        self.assertIn("setLocation", body)
        self.assertRegex(body, r"OT_PBP_MAX_UM\)\] \? double\(\$::env\(OT_PBP_MAX_UM\)\) : 10\.0")
        self.assertIn("if {$d <= $ot_pbp_max} continue", body)


if __name__ == "__main__":
    unittest.main()
