"""HBM-CORE-WBQ-1: the clock-pin landing guard stage is idempotent, hooks GRT and DRT, and refuses a foreign DRT hook."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_pin_landing as C


def _kit(d, cfg="export PRE_GLOBAL_ROUTE_TCL = /work/core_grt_pre.tcl\n"):
    d.mkdir(exist_ok=True)
    (d / "config.mk").write_text(cfg)
    (d / "core_grt_pre.tcl").write_text("source /work/hold_cap.tcl\n")
    return d


def test_stage_adds_before_grt_and_removes_after_drt(tmp_path):
    k = _kit(tmp_path / "k")
    r = C.stage(k, ["hbm_clk", "fifo_clk"])
    assert r["ports"] == ["fifo_clk", "hbm_clk"]
    pre, post = (k / "core_grt_pre.tcl").read_text(), (k / "core_drt_post.tcl").read_text()
    assert "source /work/hold_cap.tcl" in pre and "OT_CPL_MODE) add" in pre and "{fifo_clk hbm_clk}" in pre
    assert "OT_CPL_MODE) remove" in post
    assert C.HOOK in (k / "config.mk").read_text()
    assert (k / "clock_pin_landing_guard.tcl").read_text() == C.GUARD.read_text()


def test_stage_is_idempotent(tmp_path):
    k = _kit(tmp_path / "k")
    names = ("config.mk", "core_grt_pre.tcl", "core_drt_post.tcl")
    C.stage(k, ["fifo_clk"])
    first = [(k / f).read_text() for f in names]
    C.stage(k, ["fifo_clk"])
    assert first == [(k / f).read_text() for f in names]
    assert first[1].count("OT_CPL_BEGIN") == 1


def test_stage_refuses_foreign_drt_hook_and_empty_ports(tmp_path):
    with pytest.raises(ValueError):
        C.stage(_kit(tmp_path / "a", "export POST_DETAIL_ROUTE_TCL = /work/other.tcl\n"), ["fifo_clk"])
    with pytest.raises(ValueError):
        C.stage(_kit(tmp_path / "b"), [])


def test_guard_script_is_add_remove_and_skips_faces():
    t = C.GUARD.read_text()
    assert "OT_CPL_MODE" in t and "dbObstruction_create" in t and "dbObstruction_destroy" in t and "OT_CPL_FACE_UM" in t
