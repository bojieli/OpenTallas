"""OT_CLK_PAIR_BAL (HBM-TAPS 11-12, DIE-HBM-100; default off): staging, the grt183_make.sh GRT hook (after the
clk_leaf_repeat grt pass, else after the first GRT estimate), resume classification, the post-GRT ECO clock-edit skip,
and the Tcl's default-off return.  Local, no Docker/OpenROAD."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
sys.path.insert(0, str(HERE / "post_route_drv"))
import core_flow  # noqa: E402
import kit_resume as KR  # noqa: E402
import post_grt_chain as PGC  # noqa: E402

CPB = ROOT / "physical/common_flow/clk_pair_bal.tcl"
CLR = ROOT / "physical/common_flow/clk_leaf_repeat.tcl"
WRAP = ROOT / "physical/common_flow/grt183_make.sh"
CTS = "a\nsource_step_tcl POST CTS\norfs_write_db x\n"
GRT = ("  source_step_tcl PRE GLOBAL_ROUTE\n  set_propagated_clock [all_clocks]\n  log_cmd estimate_parasitics -global_routing\n"
       "  repair_design_helper\n  log_cmd estimate_parasitics -global_routing\n")
PH = "  source /work/clk_pair_bal.tcl ;# OT_CLK_PAIR_BAL"


def kit(tmp_path, leaf=True, pair=True):
    w, s = tmp_path / "work", tmp_path / "scripts"
    w.mkdir(); s.mkdir()
    (s / "cts.tcl").write_text(CTS); (s / "global_route.tcl").write_text(GRT); (w / "config.mk").write_text("")
    if leaf:
        shutil.copyfile(CLR, w / "clk_leaf_repeat_default.tcl")
    if pair:
        shutil.copyfile(CPB, w / "clk_pair_bal.tcl")
    return w, s


def run(w, s):
    e = dict(os.environ, OT_GRT183_WORK=str(w), OT_GRT183_SCRIPTS=str(s))
    p = subprocess.run(["bash", str(WRAP), "true"], env=e, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


def test_stage_grt183_stages_pair_bal(tmp_path):
    core_flow.stage_grt183(tmp_path)
    assert (tmp_path / "clk_pair_bal.tcl").read_bytes() == CPB.read_bytes()


def test_hook_after_leaf_grt_pass_once(tmp_path):
    w, s = kit(tmp_path)
    run(w, s); run(w, s)                                          # idempotent per container
    g = (s / "global_route.tcl").read_text().splitlines()
    j = next(i for i, x in enumerate(g) if x.endswith(";# OT_CLK_LEAF_REPEAT grt"))
    assert g[j - 1] == "  log_cmd estimate_parasitics -global_routing"
    assert g[j + 1] == PH and g[j + 2] == "  repair_design_helper"
    assert sum("clk_pair_bal" in x for x in g) == 1


def test_hook_without_leaf_file(tmp_path):
    w, s = kit(tmp_path, leaf=False)
    run(w, s)
    g = (s / "global_route.tcl").read_text().splitlines()
    assert g[g.index("  log_cmd estimate_parasitics -global_routing") + 1] == PH
    assert sum("clk_pair_bal" in x for x in g) == 1


def test_no_kit_file_no_patch(tmp_path):
    w, s = kit(tmp_path, pair=False)
    run(w, s)
    assert "clk_pair_bal" not in (s / "global_route.tcl").read_text()


def test_resume_stage_and_eco_skip():
    st = KR.classify({"grt183_make.sh": WRAP.read_text()}, ["grt183_make.sh", "clk_pair_bal.tcl"], {})
    assert st["clk_pair_bal.tcl"] == "grt"
    assert "clk_pair_bal.tcl" in PGC.CLOCK_EDIT_HOOKS


def test_tcl_default_off_returns_before_any_command(tmp_path):
    if not shutil.which("tclsh"):
        return
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_CLK_PAIR_BAL")}
    for val in (None, "0"):
        if val is not None:
            e["OT_CLK_PAIR_BAL"] = val
        p = subprocess.run(["tclsh"], input=f"source {CPB}\nputs CPB_SKIPPED\n", env=e, capture_output=True, text=True)
        assert p.returncode == 0 and "CPB_SKIPPED" in p.stdout, p.stdout + p.stderr
