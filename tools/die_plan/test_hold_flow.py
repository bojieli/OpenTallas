"""Fresh GRT hold uses the signed frame without changing clocks or margins."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_flow
import hold_sdc_check


def kit(tmp_path, contract=None):
    (tmp_path / "constraint.sdc").write_text("create_clock -period 833 [get_ports clk]\n")
    (tmp_path / "config.mk").write_text("export CORNER = TC\nexport OT_SIGNOFF_SDC_SHA = deadbeefdeadbeef\n")
    (tmp_path / "sdc_lint.json").write_text(json.dumps(dict(insertion_ff_ps=342, insertion_tol_ps=40)))
    (tmp_path / "grt_post.tcl").write_text(
        'if {[llength [info procs ot_pgtt_remove]]} { ot_pgtt_remove }\n'
        'if {[llength [info procs ot_pgcko_remove]]} { ot_pgcko_remove }\n'
        'clock_post_mutation\n')
    shutil.copyfile(HERE / "hold_sdc_guard.tcl", tmp_path / "hold_sdc_guard.tcl")
    if contract:
        (tmp_path / "core.json").write_text(json.dumps(dict(clock_contract=contract)))
        (tmp_path / "boundary_guard_context.json").write_text(json.dumps(dict(source_core_json="core.json")))
    return tmp_path


def test_final_sdc_frame_and_post_mutation_order(tmp_path):
    kd = kit(tmp_path)
    with (kd / "constraint.sdc").open("a") as f:
        f.write("set_clock_uncertainty -hold 25 [get_clocks clk]\n")
    expected = hashlib.sha256((kd / "constraint.sdc").read_bytes()).hexdigest()[:16]
    assert hold_flow.install(kd) == dict(measured_hold=True, reference="rebind")
    first = ((kd / "config.mk").read_text(), (kd / "grt_post.tcl").read_text())
    assert expected in first[0] and "deadbeef" not in first[0]
    assert "OT_GRT_MEASURED_HOLD = 1" in first[0]
    post = first[1]
    assert post.index("clock_post_mutation") < post.index("source /work/core_final_repair.tcl")
    assert post.index("source /work/core_final_repair.tcl") < post.index("ot_pgtt_remove")
    assert post.index("source /work/core_final_repair.tcl") < post.index("ot_pgcko_remove")
    assert hold_sdc_check.kit_findings(kd) == []
    hold_flow.install(kd)
    assert first == ((kd / "config.mk").read_text(), (kd / "grt_post.tcl").read_text())


@pytest.mark.parametrize("measured,contract,wanted", [
    (False, None, "rebind"),
    (True, {"kind": "hard_core_latency"}, "bound-ff"),
])
def test_bound_contract_or_optout_keeps_its_reference(tmp_path, measured, contract, wanted):
    kd = kit(tmp_path, contract)
    result = hold_flow.install(kd, measured=measured)
    assert result == dict(measured_hold=False, reference=wanted)
    assert "OT_GRT_MEASURED_HOLD" not in (kd / "config.mk").read_text()
    assert not (kd / "vclk_measured_hold.tcl").exists()


@pytest.mark.parametrize("flag,corner,mode,mm,wanted", [
    ("1", "BC", "ff", 0, "golden measured hold"),
    ("1", "TC", "ff", 0, "golden hold"),
    ("1", "BC", "tt", 0, "golden hold"),
    ("0", "BC", "ff", 0, "golden hold"),
    ("1", "BC", "ff", 1, "golden hold"),
])
def test_only_plain_ff_grt_binds_before_native_hold(tmp_path, flag, corner, mode, mm, wanted):
    shutil.copyfile(HERE / "hold_sdc_guard.tcl", tmp_path / "hold_sdc_guard.tcl")
    (tmp_path / "vclk_measured_hold.tcl").write_text("# owned helper exists\n")
    script = f'''
set events {{}}
set uncertainty 25
set margin 0
set period 833
set ::env(OT_GRT_MEASURED_HOLD) {flag}
set ::env(CORNER) {corner}
set ::env(OT_VCLK_CORNER) {mode}
set ::ot_mm_active {mm}
proc repair_timing {{args}} {{lappend ::events [expr {{[lsearch -exact $args -hold] >= 0 ? "hold" : "setup"}}]}}
source {{{tmp_path / "hold_sdc_guard.tcl"}}}
proc ot_hold_sdc_guard {{args}} {{lappend ::events golden}}
proc ot_vclk_measured_bind {{}} {{lappend ::events measured}}
repair_timing -hold -hold_margin 0
if {{$events ne "{wanted}"}} {{error "wrong FF repair order: $events"}}
set events {{}}
repair_timing -setup
if {{$events ne "setup"}} {{error "setup frame changed"}}
if {{$uncertainty != 25 || $margin != 0 || $period != 833}} {{error "policy changed"}}
puts FRAME_PASS
'''
    run = subprocess.run(["tclsh"], input="if {[catch {\n" + script + "\n} e]} {puts stderr $e;exit 1}\n", text=True, capture_output=True)
    assert run.returncode == 0 and "FRAME_PASS" in run.stdout, run.stdout + run.stderr
