"""link_budget_consistent.sdc: the virtual-clock reference L comes from standard-cell register clock pins, not from
early hard-macro clock pins (q-kvd 2026-10-12, qkd_d2d_ref-q8-aeca40e24: L 1,422.5 between macro pin 1,139 and face
flops ~1,700 failed every output by -122 ps).  Synthetic design in OpenROAD (the register cell is a timing-arc model: this OpenROAD's Verilog reader crashes on a hand-written ff group): clk -> 3 x 100 ps buffers -> two
registers (arrival 300); clk -> macro clock pin directly (arrival 0).  Old reference: mid(0, 300) = 150; new: 300.
Without the macro the SDC keeps its report_clock_latency reference (300 as well)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SDC = ROOT / "physical/common_flow/link_budget_consistent.sdc"

LEF = """VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS DATABASE MICRONS 1000 ; END UNITS
MANUFACTURINGGRID 0.001 ;
SITE core SIZE 0.054 BY 0.27 ; CLASS CORE ; SYMMETRY Y ; END core
LAYER M1 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.036 ; WIDTH 0.018 ; END M1
{macros}
END LIBRARY
"""
PIN = "  PIN {n} DIRECTION {d} ; {use}PORT LAYER M1 ; RECT 0 0 0.018 0.018 ; END END {n}\n"


def macro(name, cls, pins):
    body = "".join(PIN.format(n=n, d=d, use=("USE CLOCK ; " if n == "CLK" else "")) for n, d in pins)
    return f"MACRO {name}\n  CLASS {cls} ;\n  SIZE 1.0 BY 0.27 ;\n  SITE core ;\n{body}END {name}\n"


LIB = """library(t) {
  delay_model : table_lookup ; time_unit : "1ps" ; capacitive_load_unit (1, ff) ; voltage_unit : "1V" ;
  current_unit : "1mA" ; pulling_resistance_unit : "1kohm" ; leakage_power_unit : "1nW" ;
  default_max_transition : 500 ;
  slew_lower_threshold_pct_rise : 20 ; slew_upper_threshold_pct_rise : 80 ; slew_lower_threshold_pct_fall : 20 ;
  slew_upper_threshold_pct_fall : 80 ; input_threshold_pct_rise : 50 ; input_threshold_pct_fall : 50 ;
  output_threshold_pct_rise : 50 ; output_threshold_pct_fall : 50 ; nom_voltage : 0.7 ; nom_temperature : 25 ; nom_process : 1 ;
  cell(BUFx2) { area : 1 ; pin(A) { direction : input ; capacitance : 1 ; }
    pin(Y) { direction : output ; function : "A" ;
      timing() { related_pin : "A" ; timing_sense : positive_unate ;
        cell_rise(scalar) { values("100") ; } cell_fall(scalar) { values("100") ; }
        rise_transition(scalar) { values("10") ; } fall_transition(scalar) { values("10") ; } } } }
  cell(DFFHQNx1) { area : 1 ;
    pin(CLK) { direction : input ; clock : true ; capacitance : 1 ; }
    pin(D) { direction : input ; capacitance : 1 ;
      timing() { related_pin : "CLK" ; timing_type : setup_rising ;
        rise_constraint(scalar) { values("10") ; } fall_constraint(scalar) { values("10") ; } } }
    pin(QN) { direction : output ;
      timing() { related_pin : "CLK" ; timing_type : rising_edge ;
        cell_rise(scalar) { values("50") ; } cell_fall(scalar) { values("50") ; }
        rise_transition(scalar) { values("10") ; } fall_transition(scalar) { values("10") ; } } } }
  cell(HMAC) { area : 10 ;
    pin(CLK) { direction : input ; clock : true ; capacitance : 1 ; }
    pin(D) { direction : input ; capacitance : 1 ;
      timing() { related_pin : "CLK" ; timing_type : setup_rising ;
        rise_constraint(scalar) { values("10") ; } fall_constraint(scalar) { values("10") ; } } }
    pin(Q) { direction : output ;
      timing() { related_pin : "CLK" ; timing_type : rising_edge ;
        cell_rise(scalar) { values("50") ; } cell_fall(scalar) { values("50") ; }
        rise_transition(scalar) { values("10") ; } fall_transition(scalar) { values("10") ; } } } }
}
"""

VLOG = """module top (clk, din, dout, mdin);
  input clk;
  input din;
  input mdin;
  output dout;
  wire c1;
  wire c2;
  wire c3;
  wire q0;
  BUFx2 b1 (.A(clk), .Y(c1));
  BUFx2 b2 (.A(c1), .Y(c2));
  BUFx2 b3 (.A(c2), .Y(c3));
  DFFHQNx1 r_in (.CLK(c3), .D(din), .QN(q0));
  DFFHQNx1 r_out (.CLK(c3), .D(q0), .QN(dout));
{mac}endmodule
"""


def run(tmp_path, with_macro, src_lat=0.0):
    tmp_path.mkdir(parents=True, exist_ok=True)
    macros = [macro("BUFx2", "CORE", [("A", "INPUT"), ("Y", "OUTPUT")]),
              macro("DFFHQNx1", "CORE", [("CLK", "INPUT"), ("D", "INPUT"), ("QN", "OUTPUT")]),
              macro("HMAC", "BLOCK", [("CLK", "INPUT"), ("D", "INPUT"), ("Q", "OUTPUT")])]
    (tmp_path / "t.lef").write_text(LEF.format(macros="".join(macros)))
    (tmp_path / "t.lib").write_text(LIB)
    mac = "  wire mq;\n  HMAC u_mac (.CLK(clk), .D(mdin), .Q(mq));\n" if with_macro else ""
    (tmp_path / "t.v").write_text(VLOG.format(mac=mac))
    (tmp_path / "t.sdc").write_text("create_clock -name clk -period 833.333 [get_ports clk]\nset_propagated_clock [all_clocks]\n"
        + (f"set_clock_latency -source {src_lat} [get_clocks clk]\n" if src_lat else ""))
    (tmp_path / "run.tcl").write_text(
        f"read_lef {tmp_path}/t.lef\nread_liberty {tmp_path}/t.lib\nread_verilog {tmp_path}/t.v\nlink_design top\n"
        f"read_sdc {tmp_path}/t.sdc\nsource {SDC}\nreport_checks -path_delay max -to [get_ports dout] -format end\nexit\n")
    p = subprocess.run(["openroad", "-no_init", "-exit", str(tmp_path / "run.tcl")], capture_output=True, text=True, timeout=120)
    out = p.stdout + p.stderr
    m = re.search(r"OT_LINK_BUDGET clock clk T [\d.]+ L ([\d.-]+) \(([\d.-]+)\.\.([\d.-]+) ([^)]*)\)", out)
    assert m, out[-3000:]
    return float(m.group(1)), m.group(4), out


@pytest.mark.skipif(shutil.which("openroad") is None, reason="openroad not installed")
def test_reference_excludes_macro_clock_pins(tmp_path):
    L, ref, out = run(tmp_path / "mac", True)
    assert ref.startswith("std_regs 2"), out[-2000:]
    assert abs(L - 300.0) < 1.0, (L, out[-2000:])  # old midpoint (0 + 300) / 2 = 150 would fail every output 150 ps


@pytest.mark.skipif(shutil.which("openroad") is None, reason="openroad not installed")
def test_macro_free_block_keeps_clock_latency_reference(tmp_path):
    L, ref, out = run(tmp_path / "nomac", False)
    assert ref == "clock_latency", out[-2000:]
    assert abs(L - 300.0) < 1.0, (L, out[-2000:])


@pytest.mark.skipif(shutil.which("openroad") is None, reason="openroad not installed")
def test_source_latency_counted_once_on_both_references(tmp_path):
    # die-delivered leaf with source latency 200: register arrival 500 (the report path removes its duplicate)
    L1, ref1, out1 = run(tmp_path / "mac", True, 200.0)
    L2, ref2, out2 = run(tmp_path / "nomac", False, 200.0)
    assert ref1.startswith("std_regs") and ref2 == "clock_latency"
    assert abs(L1 - 500.0) < 1.0 and abs(L2 - 500.0) < 1.0, (L1, L2, out1[-1500:], out2[-1500:])
