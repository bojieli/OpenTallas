"""KV-KITS-15: gen_core_kit_kv --two-mode-grt (SIGNOFF-MODES-2 one timing mode per corner, HBM-CORES-R11 form).
A single-mode tc+bc GRT session binds the FF vclk (202.5) in BOTH corners, so the hold repair also fixes TT-corner
'hold' against the FF neighbour insertion (qkd_hr_phy_pad f79124ac45eb: 1040 input endpoints ~-38 ps, RSZ-0060).
The staged kit runs scene tc (TT setup, vclk 250) / scene BC (FF hold, vclk 202.5); unstaged kits are unchanged."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
spec = importlib.util.spec_from_file_location("gk_tm", HERE / "gen_core_kit_kv.py")
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)
ksp = importlib.util.spec_from_file_location("kit_modes_kv", REPO / "tools/die_plan/kit_modes.py")
km = importlib.util.module_from_spec(ksp); ksp.loader.exec_module(km)


def mini_kit(kd):
    cfg = ["export DESIGN_NAME = t", "export OT_VCLK_TT = 250", "export OT_VCLK_FF = 202.5", "export CORNERS = tc bc",
           "export TC_LIB_FILES = a.lib", "export BC_LIB_FILES = b.lib", "export OT_HOLD_FF_MARGIN = 5"]
    (kd / "constraint.sdc").write_text("create_clock -name vclk -period 833\nset_clock_latency -source 250 [get_clocks vclk]\n")
    (kd / "sdc_lint.json").write_text('{"insertion_ps": 250.0, "insertion_ff_ps": 202.5, "time_unit_ps": 1.0}\n')
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")


def test_stage_two_mode_and_grt_check(tmp_path):
    mini_kit(tmp_path)
    r = gk.timing_modes_stage(tmp_path)
    assert r == dict(mode="two-mode tc setup / BC hold", tt=250.0, ff=202.5)
    for f in ("vclk_ff.sdc", "orfs_hold_mm.py", "orfs_hold_mm.tcl", "kit_modes.py"):
        assert (tmp_path / f).is_file()
    assert "override export OT_HOLD_MM = 1" in (tmp_path / "config.mk").read_text()
    assert km.check(tmp_path, "grt", session="tc bc", hold_repair=True)["mm"] is True
    # the old single-mode FF-vclk tc+bc session is refused on the staged kit
    try:
        km.check(tmp_path, "grt", session="tc bc", vclk_corner="ff", hold_repair=True)
        assert False, "single-mode tc+bc with the FF vclk must fail"
    except km.Fail:
        pass


def test_runner_two_mode_branch_and_default_unchanged():
    s = (HERE / "run_kit_kv.sh").read_text()
    assert "orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl" in s
    two = s.index("--step grt --session 'tc bc' --hold-repair")
    assert s.index("\\$M grt HOLD_SLACK_MARGIN=\\$HM", two) > two          # two-mode GRT: no OT_VCLK_CORNER, kit corners
    legacy = s.index("OT_VCLK_CORNER=ff \\$M grt \\$GC HOLD_SLACK_MARGIN=\\$HM")
    assert legacy > two and "elif [ \\$rc = 0 ]; then GC='CORNER=BC CORNERS=bc'" in s   # unstaged kits: old step
