"""WF-1 11-14: ORFS global_route.tcl's estimate_parasitics -global_routing no longer aborts a congested (-allow_congestion) GRT: it falls back to placement parasitics."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = (ROOT / "physical/common_flow/grt183_make.sh").read_text()
BLOCK = SH[SH.index("# OT_GRT_EST_FALLBACK begin"):SH.index("# OT_GRT_EST_FALLBACK end")]

ORFS = """proc log_cmd {args} { puts $args; uplevel 1 $args }
global_route -congestion_iterations 30 -allow_congestion
  log_cmd estimate_parasitics -global_routing
log_cmd repair_design_helper
"""


def patch(tmp_path):
    s = tmp_path / "global_route.tcl"
    s.write_text(ORFS)
    r = subprocess.run(["bash", "-c", f'S="{s}"\n' + BLOCK + "\n"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return s.read_text()


def test_sed_wraps_the_call_in_catch_with_placement_fallback(tmp_path):
    t = patch(tmp_path)
    assert "catch {log_cmd estimate_parasitics -global_routing}" in t
    assert "OT_GRT_EST_FALLBACK" in t and "log_cmd estimate_parasitics -placement" in t
    assert t.count("catch {log_cmd estimate_parasitics -global_routing}") == 1


def test_patch_is_idempotent_and_valid_tcl_shape(tmp_path):
    t = patch(tmp_path)
    s = tmp_path / "global_route.tcl"
    subprocess.run(["bash", "-c", f'S="{s}"\n' + BLOCK], check=True, capture_output=True, timeout=30)
    assert s.read_text() == t
    assert t.count("{") == t.count("}")


def test_fallback_runs_in_tclsh_when_the_global_route_estimate_fails(tmp_path):
    import shutil
    tcl = shutil.which("tclsh")
    if not tcl:
        return
    t = patch(tmp_path)
    prelude = ('proc estimate_parasitics {args} { if {"-global_routing" in $args} { error "GRT-0232 Routing congestion too high" }; puts "EST $args" }\n'
               'proc global_route {args} { puts "GRT $args" }\nproc repair_design_helper {} { puts "REPAIR" }\n')
    f = tmp_path / "run.tcl"
    f.write_text(prelude + t)
    r = subprocess.run([tcl, str(f)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "OT_GRT_EST_FALLBACK" in r.stdout and "-placement" in r.stdout and "REPAIR" in r.stdout


def test_post_grt_hooks_of_the_core_kit_generators_use_the_fallback():
    for rel in ("physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py", "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py"):
        t = (ROOT / rel).read_text()
        assert "catch {estimate_parasitics -global_routing}" in t and "estimate_parasitics -placement" in t
