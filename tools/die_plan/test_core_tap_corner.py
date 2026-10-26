"""Core source arrival must use the selected corner, in generated and FF-only sessions."""
import subprocess
from pathlib import Path
import gen_phys as G
import schema as S
from test_corelat import pair_with_core


def plan_with_core(*args, **kwargs):
    raw = pair_with_core(*args, **kwargs)
    raw["partition_types"]["fa"]["hard_cores"] = [{"inst": "u_c"}]
    return S.Plan(raw)


def test_generated_core_overlay_tracks_corner_and_fallback():
    p = plan_with_core(430, 350)
    assert G.core_tap_rows(p, "fa")[0][3:] == (180, 430)
    assert G.core_tap_rows(p, "fa", "FF")[0][3:] == (147.5, 350)
    text = G.core_tap_ff_sdc(p, "fa")
    assert "-147.5000 [get_ports clk_c0]" in text
    assert "-180.0000" not in text
    p = plan_with_core(520, None, die_ff=200)
    assert "-221.2000 [get_ports clk_c0]" in G.core_tap_ff_sdc(p, "fa")


def test_runtime_ff_binding_and_missing_overlay_fail_closed(tmp_path):
    helper = Path(G.__file__).with_name("vclk_corner.tcl")
    (tmp_path / "vclk_corner.tcl").write_text(helper.read_text())
    (tmp_path / "constraint.sdc").write_text(
        "# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n"
        "set_clock_latency -source -clock clk -180.0000 [get_ports clk_c0]\n")
    (tmp_path / "core_taps_ff.sdc").write_text(
        "set_clock_latency -source -clock clk -147.5000 [get_ports clk_c0]\n")
    fixture = r"""
proc get_ports {p} {return $p}
proc set_clock_latency {args} {puts "LATENCY [join $args { }]"}
proc read_sdc {p} {uplevel #0 [list source $p]}
source vclk_corner.tcl
ot_core_tap_bind ff
ot_core_tap_bind tt
file delete core_taps_ff.sdc
if {![catch {ot_core_tap_bind ff} msg]} {error "missing overlay accepted"}
puts "EXPECTED $msg"
"""
    result = subprocess.run(["tclsh"], input=fixture, text=True, cwd=tmp_path,
                            capture_output=True, check=True)
    assert "LATENCY -source -clock clk -147.5000 clk_c0" in result.stdout
    assert "LATENCY -source -clock clk -180.0000 clk_c0" in result.stdout
    assert "EXPECTED core tap corner: missing FF overlay" in result.stdout
    assert not result.stderr


def test_unmarked_kit_ignores_stale_overlay(tmp_path):
    helper = Path(G.__file__).with_name("vclk_corner.tcl")
    (tmp_path / "vclk_corner.tcl").write_text(helper.read_text())
    (tmp_path / "constraint.sdc").write_text("# historical kit\n")
    (tmp_path / "core_taps_ff.sdc").write_text("error stale_overlay_loaded\n")
    result = subprocess.run(["tclsh"], input="source vclk_corner.tcl\not_core_tap_bind ff\nputs OK\n",
                            text=True, cwd=tmp_path, capture_output=True, check=True)
    assert result.stdout.strip() == "OK"
    assert not result.stderr
