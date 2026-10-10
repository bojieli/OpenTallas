"""DRV6 (review-0725, coordinator APPROVED 2026-10-09): the post-CTS early-fail gate judges IO paths at the IO-reference
insertion (io_ref_routed.sdc rule), not at the virtual clock's ideal latency."""
import tempfile
import unittest
from pathlib import Path

import stuckscan as ss

NS = {}
exec("import re, os\n" + ss.PROBE[ss.PROBE.index("def rd("):ss.PROBE.index("def probe_base")], NS)

RPT = """cts final report_checks -path_delay max
--------------------------------------------------------------------------
Startpoint: u.q$_DFF_P_ (rising edge-triggered flip-flop clocked by core_clk)
Endpoint: o[1] (output port clocked by ot_lb_v_core_clk)
Path Group: ot_lb_v_core_clk
Path Type: max

Fanout     Cap    Slew   Delay    Time   Description
-----------------------------------------------------------------------------
                          0.00    0.00   clock core_clk (rise edge)
                          0.00    0.00   clock source latency
                 16.30 1212.00 1212.00 ^ u.q$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
     1    0.86   18.81  574.21 1786.21 v u.q$_DFF_P_/QN (DFFHQNx1_ASAP7_75t_R)
                                         o[1] (net)
                 14.03    0.00 1786.21 v o[1] (out)
                               1786.21   data arrival time

                  0.00  833.00  833.00   clock ot_lb_v_core_clk (rise edge)
                       1039.79 1872.79   clock network delay (ideal)
                        -60.00 1812.79   clock uncertainty
                       -518.50 1294.29   output external delay
                               1294.29   data required time
-----------------------------------------------------------------------------
                               -491.92   slack (VIOLATED)

Startpoint: g.d$_DFF_P_ (rising edge-triggered flip-flop clocked by core_clk)
Endpoint: g.e$_DFF_P_ (rising edge-triggered flip-flop clocked by core_clk)
Path Group: core_clk
Path Type: max

Fanout     Cap    Slew   Delay    Time   Description
-----------------------------------------------------------------------------
                          0.00    0.00   clock core_clk (rise edge)
                 16.30 1200.00 1200.00 ^ g.d$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
     1    0.86   18.81  100.00 1300.00 v g.d$_DFF_P_/QN (DFFHQNx1_ASAP7_75t_R)
                               1300.00   data arrival time
                               -50.00   slack (VIOLATED)

==========================================================================
"""


class IorefGate(unittest.TestCase):
    def paths(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "4_cts_final.rpt"
            f.write_text(RPT)
            return NS["worst_paths"](str(f))

    def test_parse_virtual_latency_and_register_clock(self):
        p = self.paths()[0]
        self.assertEqual((p["vlat_launch"], p["vlat_capture"], p["flop_ck_ps"]), (None, 1039.79, 1212.0))
        self.assertIsNone(self.paths()[1]["vlat_capture"])

    def test_output_path_moves_to_measured_insertion(self):
        b = dict(worst=dict(paths=self.paths()), period=833.333)
        r = ss.ioref_rejudge(b, dict(calibration=dict(env=dict(CK_SS_MEAN=1221))))
        self.assertAlmostEqual(r["paths"][0]["ioref_ps"], -491.92 + 1221 - 1039.79, places=1)
        self.assertEqual(r["paths"][1]["ioref_ps"], -50.0)                # reg->reg untouched
        r = ss.ioref_rejudge(b, {})                                         # no measurement: the path's own flop
        self.assertAlmostEqual(r["paths"][0]["ioref_ps"], -491.92 + 1212 - 1039.79, places=1)

    def test_gate_relaxes_false_io_failure(self):
        b = dict(worst=dict(paths=self.paths()), period=833.333, corner="TT", current="4_1_cts.tmp.log",
                 metrics={"4_1_cts": {"cts__timing__setup__ws": -491.92, "cts__timing__drv__setup_violation_count": 3887,
                                      "cts__timing__setup__tns": -695161}})
        j = dict(name="x", calibration=dict(env=dict(CK_SS_MEAN=1221)), spec=dict(block="b", source=dict(commit="0")))
        hp = ss.hopeless(b, j, 0)
        self.assertFalse([v for v, _ in hp if v == "EARLY_FAIL_SETUP"])
        b["worst"]["paths"][0]["slack_ps"] = -800.0                          # still hopeless at the IO reference
        hp = ss.hopeless(b, j, 0)
        self.assertEqual(hp[0][0], "EARLY_FAIL_SETUP")
        self.assertIn("IO-reference insertion", hp[0][1])


    def test_real_clock_port_at_zero_latency(self):
        # retry545_cl2: the output is constrained on core_clk itself, propagated latency 0 at the port
        rpt = RPT.replace("(output port clocked by ot_lb_v_core_clk)", "(output port clocked by core_clk)").replace(
            "                       1039.79 1872.79   clock network delay (ideal)",
            "                          0.00  833.00   clock network delay (propagated)")
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "r.rpt"
            f.write_text(rpt)
            p = NS["worst_paths"](str(f))[0]
        self.assertEqual(p["vlat_capture"], 0.0)
        r = ss.ioref_rejudge(dict(worst=dict(paths=[p]), period=833.333), dict(calibration=dict(env=dict(CK_SS_MEAN=973))))
        self.assertAlmostEqual(r["paths"][0]["ioref_ps"], -491.92 + 973, places=1)


if __name__ == "__main__":
    unittest.main()


class TwoClockIoref(unittest.TestCase):
    """cont-takeover 2026-10-10: an IO path of an uncalibrated clock group keeps its own register clock arrival"""
    def _p(self, clk):
        return dict(slack_ps=-500.0, start="r", start_kind="(rising edge-triggered flip-flop clocked by x)",
                    end="o", end_kind=f"(output port clocked by {clk})", vlat_capture=80.0, vlat_launch=None,
                    flop_ck_ps=840.0, group=clk)

    def test_pclk_io_uses_own_arrival(self):
        j = dict(calibration=dict(env=dict(CK_SS_MEAN=81)), spec=dict(stages=dict(calibrate=dict(clock="core_clk"))))
        r = ss.ioref_rejudge(dict(worst=dict(paths=[self._p("ot_lb_v_pclk")]), period=833.333), j)
        self.assertAlmostEqual(r["paths"][0]["ioref_ps"], -500 + 840 - 80, places=1)
        self.assertIn("pclk", r["source"])

    def test_core_io_uses_calibrated_insertion(self):
        j = dict(calibration=dict(env=dict(CK_SS_MEAN=1221)), spec=dict(stages=dict(calibrate=dict(clock="core_clk"))))
        r = ss.ioref_rejudge(dict(worst=dict(paths=[self._p("ot_lb_v_core_clk")]), period=833.333), j)
        self.assertAlmostEqual(r["paths"][0]["ioref_ps"], -500 + 1221 - 80, places=1)

    def test_port_clock_parse(self):
        self.assertEqual(ss.port_clock("(input port clocked by pclk)"), "pclk")
        self.assertIsNone(ss.port_clock("(rising edge-triggered flip-flop)"))

