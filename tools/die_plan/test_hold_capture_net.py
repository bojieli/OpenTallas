"""Macro capture obligations and shared-net reroute risks from the bksel hold ECO."""
from pathlib import Path
import subprocess
import sys
import importlib.util
import shutil
import pytest
import os

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_eco_internal as H

HEADER = "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps\tnet\n"
OPENROAD = os.environ.get("OPENROAD_BIN") or shutil.which("openroad")


def test_macro_capture_is_selected_and_plan_roundtrips(tmp_path):
    rows = H.read_endpoints(HEADER + "hist/gsel[0]\ts_g0/QN\treg\tmacro\t-4.11\t400\tg0\n"
                            "ordinary/ADDR\ts_g0/QN\treg\treg\t-20\t400\tg0\n"
                            "hist/gsel[1]\tINPUT\tport\tmacro\t-20\t400\tg1\n")
    plan = H.plan(rows)
    assert plan["cells"] == [("hist/gsel[0]", 1)]
    path = tmp_path / "plan.tsv"
    H.write_plan(plan, path)
    assert "hist/gsel[0]\t1\tmacro" in path.read_text()
    assert H.read_plan(path.read_text()) == plan["cells"]


def test_positive_unmodified_shared_net_capture_is_not_silently_omitted(tmp_path):
    # gsel8 was +10.291 before the other seven loads left its net, then -4.11 after reroute.
    # Its old positive slack is evidence of risk, not justification for an unpriced automatic insert.
    rows = H.read_endpoints(HEADER + "hist/gsel[0]\ts_g0/QN\treg\tmacro\t-1\t400\tg0\n"
                            "hist/gsel[8]\ts_g0/QN\treg\tmacro\t10.291\t400\tg0\n"
                            "unrelated/D\ts_g1/QN\treg\treg\t10.487\t400\tg1\n")
    plan = H.plan(rows)
    assert plan["cells"] == [("hist/gsel[0]", 1)]
    assert [r["endpoint"] for r in plan["siblings"]] == ["hist/gsel[8]"]
    assert plan["summary"]["touched_net_coverage"] == "reported"
    out = tmp_path / "plan.tsv"
    H.write_plan(plan, out)
    assert "# reroute sibling hist/gsel[8] net=g0 ff_ps=10.291" in out.read_text()
    # Six-field legacy tables remain usable but cannot claim net coverage.
    old = H.plan(H.read_endpoints(HEADER.rsplit("\tnet", 1)[0] + "\nff/D\ts/Q\treg\treg\t-1\t400\n"))
    assert old["summary"]["touched_net_coverage"] == "not_measured"


def test_tcl_planner_selects_timed_macro_and_reports_untouched_positive_sibling(tmp_path):
    output = tmp_path / "plan.tsv"
    script = f"""
source {HERE / 'post_route_drv/hold_eco_internal_plan.tcl'}
namespace eval sta {{proc time_sta_ui {{x}} {{return 1.0}}}}
proc get_ports {{args}} {{return {{}}}}
proc get_full_name {{x}} {{return $x}}
proc get_pins {{args}} {{return {{}}}}
proc ot_hei_pin_info {{name}} {{
  if {{[string match hist/* $name]}} {{return {{macro g0}}}}
  return {{reg g1}}
}}
proc find_timing_paths {{args}} {{
  if {{[lindex $args [expr {{[lsearch -exact $args -path_delay]+1}}]] eq "max"}} {{return {{t0 t8 tx}}}}
  return {{h0 h8 hx}}
}}
proc get_property {{path prop}} {{
  if {{$prop eq "endpoint"}} {{return [dict get {{t0 hist/gsel0 t8 hist/gsel8 tx ordinary/ADDR h0 hist/gsel0 h8 hist/gsel8 hx ordinary/ADDR}} $path]}}
  if {{$prop eq "startpoint"}} {{return s_g0/QN}}
  return [dict get {{t0 400 t8 400 tx 400 h0 -1 h8 10.291 hx -20}} $path]
}}
ot_hei_auto_plan {{}} {{}} {output}
"""
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert run.returncode == 0 and not run.stderr, run.stdout + run.stderr
    assert H.read_plan(output.read_text()) == [("hist/gsel0", 1)]
    assert "reroute sibling hist/gsel8 net=g0 ff_ps=10.291" in output.read_text()
    assert "unmodified_touched_siblings=1" in run.stdout


@pytest.mark.skipif(not OPENROAD, reason="OpenROAD required for actual macro classification")
def test_actual_sta_macro_with_non_flop_input_name(tmp_path):
    spec = importlib.util.spec_from_file_location("capture_fixture", HERE / "post_route_drv/test_nonport_scope_sta.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    thresholds = "\n".join(f"{k}_threshold_pct_{edge} : 50;" for k in ("input", "output") for edge in ("rise", "fall"))
    thresholds += "\n" + "\n".join(f"slew_{k}_threshold_pct_{edge} : {v};" for k, v in (("lower", 20), ("upper", 80)) for edge in ("rise", "fall"))
    lib = fixture.LIB.replace("delay_model : table_lookup;", "delay_model : table_lookup;\n" + thresholds)
    macro_at = lib.index("cell (CLOCKED_MACRO)")
    lib = lib[:macro_at] + lib[macro_at:].replace('"D"', '"gsel0"').replace("pin (D)", "pin (gsel0)")
    lef_at = fixture.LEF.index("MACRO CLOCKED_MACRO")
    lef = fixture.LEF[:lef_at] + fixture.LEF[lef_at:].replace("PIN D\n", "PIN gsel0\n").replace("END D\n", "END gsel0\n")
    netlist = fixture.NETLIST.replace("u_macro(.CK(CK), .D(DIN)", "u_macro(.CK(CK), .gsel0(qi)")
    netlist = netlist.replace("module top(input CK, DIN, output R2O, MOUT);",
                              "module top(CK, DIN, R2O, MOUT); input CK; input DIN; output R2O; output MOUT;")
    for name, content in (("f.lib", lib), ("f.lef", lef), ("f.v", netlist)):
        (tmp_path / name).write_text(content)
    output = tmp_path / "actual.tsv"
    script = f"""read_lef {tmp_path}/f.lef
read_liberty {tmp_path}/f.lib
read_verilog {tmp_path}/f.v
link_design top
create_clock -name clk -period 0.833 [get_ports CK]
set_clock_uncertainty -hold 0.2 [get_clocks clk]
set_input_delay -clock clk -min -0.02 [get_ports DIN]
set_input_delay -clock clk -max 0.1 [get_ports DIN]
set_output_delay -clock clk -min 0 [all_outputs]
set_output_delay -clock clk -max 0.1 [all_outputs]
source {HERE}/post_route_drv/hold_eco_internal_plan.tcl
puts "MACRO_INFO [ot_hei_pin_info u_macro/gsel0]"
puts "MACRO_CLOCK [ot_hei_pin_info u_macro/CK]"
puts "MACRO_OUTPUT [ot_hei_pin_info u_macro/Q]"
ot_hei_auto_plan {{}} {{}} {output}
exit
"""
    path = tmp_path / "actual.tcl"
    path.write_text(script)
    run = subprocess.run([OPENROAD, "-no_init", "-exit", str(path)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "MACRO_INFO macro" in run.stdout
    assert "MACRO_CLOCK other" in run.stdout and "MACRO_OUTPUT other" in run.stdout
    assert "u_macro/gsel0" in dict(H.read_plan(output.read_text()))
