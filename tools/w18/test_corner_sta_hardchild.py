"""PF-HARDCHILD-VERDICT (S81-CAPC / ROOT-CORNER 2026-10-19): the verdict session (corner_sta.script) names the
hard-child ETM libs in OT_PF_MACRO_LIBS so the sign-off SDC's PINFLOP reference (pinflop_ref.tcl (b)) is the child
flops (clock pin + ETM insertion), the reference the route already closed against.  This is a RELAXING change, so the
OpenROAD checks pin down that it relaxes nothing else:
  * a block whose macros carry no clock_tree_path (SRAM-like) times byte-identically with and without the env line;
  * with the ETM lib named, a REAL hold violation and a REAL setup violation at the child boundary still fail;
  * the old session (no env) failed a boundary the child-flop reference passes (the s81sl_capc false FF fail).
The sign-off SDC is the shipped io_ref_skew.sdc behind the s81sl_capc signoff.sdc preamble."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.w18 import corner_sta as sta

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "physical/qwen_die_masters"
IMAGE = "openroad/orfs:latest"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"

# hm = hard child ETM: clock pin with internal insertion (min 250 / max 300 ps); d constraints relative to the clock pin.
ETM = """library(hm_tt) {
  delay_model : table_lookup; time_unit : "1ps"; voltage_unit : "1V"; current_unit : "1mA";
  capacitive_load_unit(1, ff); pulling_resistance_unit : "1kohm"; leakage_power_unit : "1pW";
  nom_process : 1; nom_voltage : 0.7; nom_temperature : 25;
  cell(hm) {
    area : 100; is_macro_cell : true;
    pin("ck") {
      direction : input; clock : true; capacitance : 1.0;
      timing() { timing_sense : positive_unate; timing_type : min_clock_tree_path;
        cell_rise(scalar) { values("250.0"); } cell_fall(scalar) { values("250.0"); } }
      timing() { timing_sense : positive_unate; timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("300.0"); } cell_fall(scalar) { values("300.0"); } }
    }
    pin("d") { direction : input; capacitance : 1.0;
      timing() { related_pin : "ck"; timing_type : setup_rising;
        rise_constraint(scalar) { values("SETUP"); } fall_constraint(scalar) { values("SETUP"); } }
      timing() { related_pin : "ck"; timing_type : hold_rising;
        rise_constraint(scalar) { values("HOLD"); } fall_constraint(scalar) { values("HOLD"); } } }
    pin("q") { direction : output;
      timing() { related_pin : "ck"; timing_type : rising_edge;
        cell_rise(scalar) { values("400.0"); } cell_fall(scalar) { values("400.0"); }
        rise_transition(scalar) { values("10.0"); } fall_transition(scalar) { values("10.0"); } } }
  }
}
"""
# sm = SRAM-like macro: clocked, setup/hold arcs, NO clock_tree_path (what every memory macro lib looks like).
SRAM = ETM.replace("hm_tt", "sm_tt").replace("cell(hm)", "cell(sm)").replace(
    """      timing() { timing_sense : positive_unate; timing_type : min_clock_tree_path;
        cell_rise(scalar) { values("250.0"); } cell_fall(scalar) { values("250.0"); } }
      timing() { timing_sense : positive_unate; timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("300.0"); } cell_fall(scalar) { values("300.0"); } }
""", "")


def lef(cell):
    return f"""VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO {cell}
  CLASS BLOCK ;
  ORIGIN 0 0 ;
  SIZE 10.8 BY 10.8 ;
  PIN ck
    DIRECTION INPUT ; USE CLOCK ;
    PORT LAYER M4 ; RECT 0 0 0.1 0.1 ; END
  END ck
  PIN d
    DIRECTION INPUT ; USE SIGNAL ;
    PORT LAYER M4 ; RECT 0 1 0.1 1.1 ; END
  END d
  PIN q
    DIRECTION OUTPUT ; USE SIGNAL ;
    PORT LAYER M4 ; RECT 0 2 0.1 2.1 ; END
  END q
END {cell}
END LIBRARY
"""


# wires-only parent of one hard child (the s81sl_capc shape: inputs straight into the child, child output to a port)
NET_HARD = """module top(input clk, input h, output q2);
  hm u_chn (.ck(clk), .d(h), .q(q2));
endmodule
"""
# no hard child: a pin flop and an SRAM-like macro
NET_SRAM = """module top(input clk, input a, input h, output q1, output q2);
  DFFHQNx1_ASAP7_75t_R pa (.CLK(clk), .D(a), .QN(q1));
  sm u_mem (.ck(clk), .d(h), .q(q2));
endmodule
"""
# the s81sl_capc signoff.sdc preamble (physical/ref_tile/s81sl_capc kit), then the shipped io_ref_skew.sdc
PRE = """set ::ot_ref_pre_cts 0
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ::env(OT_IO_SKEW) 90
set ::env(OT_IO_HOLD_SKEW) 50
set ::env(OT_REF_GLOB) {*}
"""
TCL = """set L /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $L/lib/NLDM/*SEQ*RVT_TT*.lib* $L/lib/NLDM/*SIMPLE*RVT_TT*.lib* $L/lib/NLDM/*INVBUF*RVT_TT*.lib* $L/lib/NLDM/*AO*RVT_TT*.lib*] { read_liberty $f }
read_liberty /src/w/CELL/CELL_tt.lib
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/w/CELL/CELL.lef
read_verilog /src/w/t.v
link_design top
PFLINE
source /src/w/signoff.sdc
puts "OT_HOLD_WS [sta::worst_slack_cmd min]"
puts "OT_SETUP_WS [sta::worst_slack_cmd max]"
report_checks -path_delay min -digits 3
report_checks -path_delay max -digits 3
write_sdc -digits 3 /tmp/o.sdc
puts [exec cat /tmp/o.sdc]
"""


def have_orfs():
    return bool(shutil.which("docker")) and not subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True).returncode


def session(cell, net, lib, env):
    """One verdict-shaped OpenROAD session; env=True uses the env line corner_sta.script emits for this macro."""
    pf = ""
    if env:
        pf = next(l for l in sta.script("tt", "/b", [f"w/{cell}"]).splitlines() if "OT_PF_MACRO_LIBS" in l)
    with tempfile.TemporaryDirectory() as t:
        w = Path(t)
        (w / cell).mkdir()
        (w / cell / f"{cell}_tt.lib").write_text(lib)
        (w / cell / f"{cell}.lef").write_text(lef(cell))
        (w / "t.v").write_text(net)
        (w / "signoff.sdc").write_text(PRE + (D / "io_ref_skew.sdc").read_text())
        (w / "t.tcl").write_text(TCL.replace("CELL", cell).replace("PFLINE", pf))
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{t}:/src/w", IMAGE, OPENROAD, "-no_init", "-exit",
                            "/src/w/t.tcl"], capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr
    hold = re.search(r"OT_HOLD_WS (\S+)", out)
    setup = re.search(r"OT_SETUP_WS (\S+)", out)
    assert hold and setup, out[-3000:]
    # worst_slack_cmd is in seconds; write_sdc stamps the wall-clock date (dropped so two sessions compare by bytes)
    out = re.sub(r"(?m)^#.*\d\d:\d\d:\d\d \d{4}$", "#<date>", out)
    return float(hold.group(1)) * 1e12, float(setup.group(1)) * 1e12, out


def etm(setup, hold):
    return ETM.replace('"SETUP"', f'"{setup}"').replace('"HOLD"', f'"{hold}"')


@unittest.skipUnless(have_orfs(), "no docker / ORFS image")
class HardChildVerdict(unittest.TestCase):
    def test_no_hard_child_byte_identical(self):
        """SRAM-like macro libs carry no clock_tree_path: naming them changes no reference, no constraint, no slack."""
        _, _, off = session("sm", NET_SRAM, SRAM.replace('"SETUP"', '"10.0"').replace('"HOLD"', '"5.0"'), env=False)
        _, _, on = session("sm", NET_SRAM, SRAM.replace('"SETUP"', '"10.0"').replace('"HOLD"', '"5.0"'), env=True)
        self.assertIn("QDM reference pin", off)
        self.assertEqual(off, on)

    def test_child_flop_reference_passes_what_the_route_closed(self):
        """Child flops at pin + 250 ps; d hold 160 ps after the pin (internal path + flop hold): a met boundary.
        The old session referenced the raw clock pin and failed it (the s81sl_capc false FF fail)."""
        hold_on, setup_on, out = session("hm", NET_HARD, etm(10.0, 160.0), env=True)
        self.assertRegex(out, r"QDM reference pin u_chn/ck clock arrival max 300\.0* min 250\.0*")
        self.assertGreater(hold_on, 0.0, out[-3000:])
        self.assertGreater(setup_on, 0.0, out[-3000:])
        hold_off, _, out = session("hm", NET_HARD, etm(10.0, 160.0), env=False)
        self.assertLess(hold_off, 0.0, out[-3000:])
        self.assertAlmostEqual(hold_on - hold_off, 250.0, places=1)   # relaxed by exactly the child's min insertion

    def test_real_hold_violation_still_fails(self):
        """d needs data 400 ps after the clock pin (150 ps past the child flops): a real violation, still FAIL."""
        hold, _, out = session("hm", NET_HARD, etm(10.0, 400.0), env=True)
        self.assertRegex(out, r"QDM reference pin u_chn/ck clock arrival max 300\.0* min 250\.0*")
        self.assertLess(hold, 0.0, out[-3000:])
        self.assertAlmostEqual(hold, 250.0 - 400.0 - 25.0, delta=5.0)

    def test_real_setup_violation_still_fails(self):
        """d setup 300 ps at the clock pin: the input budget no longer fits the cycle, still FAIL."""
        _, setup, out = session("hm", NET_HARD, etm(300.0, 160.0), env=True)
        self.assertLess(setup, 0.0, out[-3000:])


if __name__ == "__main__":
    unittest.main()
