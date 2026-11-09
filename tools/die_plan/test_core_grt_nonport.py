"""Core generator integration for the already qualified, opt-in GRT hold scope."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_flow


def generate(path, **kwargs):
    path.mkdir()
    cfg = core_flow.apply(path, core_flow.binding(250, 202.5), "core",
                          rc_cal=False, grt_pre_extra=("/work/custom_pre.tcl",),
                          grt_post_extra=("/work/custom_post.tcl",), **kwargs)
    return cfg


def test_opt_in_stages_shared_scope_after_existing_wrappers(tmp_path):
    kit = tmp_path / "enabled"
    cfg = generate(kit, grt_nonport_hold=True)
    hook = (kit / "grt_pre_core.tcl").read_text()
    assert hook.splitlines()[-1] == "source /work/grt_nonport_hold.tcl"
    assert hook.index("source /work/custom_pre.tcl") < hook.index("source /work/hold_pad_hb4.tcl")
    assert hook.index("source /work/hold_pad_hb4.tcl") < hook.index("OT_GRT_BUFFER_CAP")
    assert (kit / "grt_nonport_hold.tcl").read_bytes() == (core_flow.TOOL.parent / "grt_nonport_hold.tcl").read_bytes()
    assert "export OT_GRT_NONPORT_HOLD = 1" in cfg


def test_default_is_original_generated_output(tmp_path):
    plain, enabled = tmp_path / "plain", tmp_path / "enabled"
    before = generate(plain)
    after = generate(enabled, grt_nonport_hold=True)
    assert not (plain / "grt_nonport_hold.tcl").exists()
    assert all("OT_GRT_NONPORT_HOLD" not in line for line in before)
    assert before == [line for line in after if "OT_GRT_NONPORT_HOLD" not in line]
    assert (enabled / "grt_pre_core.tcl").read_text() == (plain / "grt_pre_core.tcl").read_text() + "source /work/grt_nonport_hold.tcl\n"
    for name in ("grt_post_core.tcl", "pre_floorplan_core.tcl", "clock_binding.json", "orfs_hold_mm.py"):
        assert (enabled / name).read_bytes() == (plain / name).read_bytes()
