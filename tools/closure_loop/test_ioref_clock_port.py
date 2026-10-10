"""S81-TAIL 2026-10-08: io_ref_routed.sdc drops data input delays on real-clock source ports before it measures the
routed insertion (s81ph dsfd_ctrl_pc: set_input_delay -clock vclk on ckh[0] made hbm_clk read 796 TT instead of 226)."""
import re
import unittest
from pathlib import Path

SDC = Path(__file__).resolve().parents[2] / "physical/common_flow/io_ref_routed.sdc"


class IorefClockPort(unittest.TestCase):
    def setUp(self):
        self.t = SDC.read_text()

    def test_unset_per_reference_clock_and_edge(self):
        # unset_input_delay without -clock only removes clock-less delays (checked in OpenSTA 26Q3)
        self.assertRegex(self.t, r"unset_input_delay -clock \$ot_ir_c \[get_ports \$sn\]")
        self.assertRegex(self.t, r"unset_input_delay -clock \$ot_ir_c -clock_fall \[get_ports \$sn\]")

    def test_only_clock_source_ports(self):
        blk = self.t[self.t.index("foreach cn $ot_ir_real {\n  foreach s [get_property"):]
        self.assertIn("get_ports -quiet $sn", blk[:600])

    def test_before_the_arrival_measurement(self):
        self.assertLess(self.t.index("unset_input_delay -clock"), self.t.index("set ot_ir_ins [dict create]"))
        self.assertLess(self.t.index("set ot_ir_real {}"), self.t.index("unset_input_delay -clock"))


if __name__ == "__main__":
    unittest.main()
