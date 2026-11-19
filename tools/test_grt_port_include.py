"""S81-COL-GRT-PORT 11-17 (COORD, FABLE-PD-S81-1100 B3): opt-in inclusion of input-port starts in the GRT hold repair."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOK = HERE / "grt_nonport_hold.tcl"

MOCK = r'''
set ::env(OT_GRT_NONPORT_HOLD) 1
set ::ot_mm_active 1; set ::ot_mm_synced 1; set ::ot_mm_stage 4_cts.sdc
set ::ot_hold_scope_supported_modes {reg2reg nonport}
proc ::ot_hold_repair_scope {b} {}
proc ::ot_repair_timing {args} { if {[info exists ::env(OT_HOLD_REPAIR_SCOPE)]} { return "SCOPE=<$::env(OT_HOLD_REPAIR_SCOPE)>" }; return "SCOPE=unset" }
'''


def _run(pre=""):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    src = MOCK + pre + "\nsource {" + str(HOOK) + "}\nputs [::ot_repair_timing]\nputs \"AFTER [info exists ::env(OT_HOLD_REPAIR_SCOPE)]\"\n"
    r = subprocess.run(["tclsh"], input=src, text=True, capture_output=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_default_still_excludes_input_starts():
    out = _run()
    assert "SCOPE=<nonport>" in out and "AFTER 0" in out and "INCLUDED" not in out, out


def test_include_opt_in_runs_the_repair_over_all_paths():
    out = _run("set ::env(OT_GRT_PORT_HOLD_INCLUDE) 1\nset ::env(OT_GRT_PORT_HOLD_PORTS) 1\n")        # WAVE-PILOT-FIX 11-19: INCLUDE needs the explicit PORTS marker
    assert "SCOPE=<>" in out and "AFTER 0" in out and "input-port starts INCLUDED" in out, out
    stale = _run("set ::env(OT_GRT_PORT_HOLD_INCLUDE) 1\n")                                              # a kit made before 11-18 lever 3: INCLUDE alone is stale
    assert "SCOPE=<nonport>" in stale and "INCLUDED" not in stale, stale


def test_native_scope_skips_the_false_path_only_when_included():
    t = HOOK.read_text()
    assert "!$::ot_grt_port_include} { set_false_path -hold -from $inputs }" in t
    assert "!$::ot_grt_port_include} { unset_path_exceptions -hold -from $inputs }" in t


def test_gen_phys_wires_the_item_knob():
    g = (HERE / "die_plan" / "gen_phys.py").read_text()
    assert 'os.environ.get("OT_GRT_PORT_HOLD_MARGIN_PS"' in g and "export OT_GRT_PORT_HOLD_INCLUDE = 1" in g
    assert g.index("OT_GRT_PORT_HOLD_MARGIN_PS") < g.index("export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}")
