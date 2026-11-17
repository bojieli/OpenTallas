"""Plain FF GRT repair restores its approved signal RC model before IO binding."""
from pathlib import Path
import shutil
import subprocess
import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.parametrize("flag,corner,mode,mm,expected", [
    ("1", "BC", "ff", 0, "golden estimate measured hold"),
    ("0", "BC", "ff", 0, "golden measured hold"),
    ("1", "TC", "ff", 0, "golden hold"),
    ("1", "BC", "tt", 0, "golden hold"),
    ("1", "BC", "ff", 1, "golden hold"),
])
def test_declared_table_restored_only_in_plain_ff_grt(tmp_path, flag, corner, mode, mm, expected):
    for name in ("hold_sdc_guard.tcl", "rc_signal_adjust.tcl"):
        shutil.copyfile(HERE / name, tmp_path / name)
    layer = tmp_path / "layers.tcl"
    layer.write_text("set_layer_rc -layer M2 -resistance 0.1 -capacitance 0.01\n")
    text = f"""
set events {{}}
set caps {{}}
set env(OT_GRT_MEASURED_HOLD) 1
set env(OT_RC_SIGNAL) {flag}
set env(OT_RC_SIGNAL_SCALE) 1.13
set env(CORNER) {corner}
set env(OT_VCLK_CORNER) {mode}
set env(LAYER_PARASITICS_FILE) {{{layer}}}
set ot_mm_active {mm}
proc set_layer_rc {{args}} {{lappend ::caps [lindex $args end]}}
proc estimate_parasitics {{args}} {{
  if {{$args ne "-global_routing"}} {{error "wrong RC basis"}}
  lappend ::events estimate
}}
proc repair_timing {{args}} {{lappend ::events [expr {{[lsearch -exact $args -hold]>=0 ? "hold" : "setup"}}]}}
source {{{tmp_path / "hold_sdc_guard.tcl"}}}
proc ot_hold_sdc_guard {{args}} {{lappend ::events golden}}
proc ot_vclk_measured_bind {{}} {{lappend ::events measured}}
"""
    # The measured helper existence guard is intentional, even though its native
    # binding command is stubbed here; the SDK counterpart is covered separately.
    (tmp_path / "vclk_measured_hold.tcl").write_text("# measured binding\n")
    text += f"""
repair_timing -hold -hold_margin 0
if {{$events ne "{expected}"}} {{error "wrong frame/order $events"}}
set events {{}}
repair_timing -hold -hold_margin 0
if {{$events ne "{expected}"}} {{error "second call differs $events"}}
if {{[llength $caps] && ([llength $caps]!=2 || abs([lindex $caps 0]-0.21018)>1e-8 || [lindex $caps 0] != [lindex $caps 1])}} {{error "RC scale compounded $caps"}}
set events {{}}
repair_timing -setup
if {{$events ne "setup"}} {{error "setup context mutated"}}
puts FRAME_PASS
"""
    result = subprocess.run(["tclsh"], input="if {[catch {\n"+text+"\n} e]} {puts stderr $e;exit 1}\n",
                            capture_output=True, text=True)
    assert result.returncode == 0 and "FRAME_PASS" in result.stdout, result.stdout + result.stderr


def test_configured_missing_helper_fails_before_native_hold(tmp_path):
    shutil.copyfile(HERE / "hold_sdc_guard.tcl", tmp_path / "hold_sdc_guard.tcl")
    text = f"""
set env(OT_RC_SIGNAL) 1
set env(CORNER) BC
set env(OT_VCLK_CORNER) ff
proc repair_timing {{args}} {{error "NATIVE MUST NOT RUN"}}
source {{{tmp_path / "hold_sdc_guard.tcl"}}}
proc ot_hold_sdc_guard {{args}} {{}}
repair_timing -hold
"""
    result = subprocess.run(["tclsh"], input="if {[catch {\n"+text+"\n} e]} {puts stderr $e;exit 1}\n",
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "configured signal RC helper missing" in result.stderr
    assert "NATIVE MUST NOT RUN" not in result.stderr


def test_configured_missing_layer_table_fails_before_native_hold(tmp_path):
    for name in ("hold_sdc_guard.tcl", "rc_signal_adjust.tcl"):
        shutil.copyfile(HERE / name, tmp_path / name)
    text = f"""
set env(OT_RC_SIGNAL) 1
set env(CORNER) BC
set env(OT_VCLK_CORNER) ff
set env(LAYER_PARASITICS_FILE) {{{tmp_path / "missing.tcl"}}}
proc repair_timing {{args}} {{error "NATIVE MUST NOT RUN"}}
source {{{tmp_path / "hold_sdc_guard.tcl"}}}
proc ot_hold_sdc_guard {{args}} {{}}
repair_timing -hold
"""
    result = subprocess.run(["tclsh"], input="if {[catch {\n"+text+"\n} e]} {puts stderr $e;exit 1}\n",
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "configured signal RC layer table missing" in result.stderr
    assert "NATIVE MUST NOT RUN" not in result.stderr
