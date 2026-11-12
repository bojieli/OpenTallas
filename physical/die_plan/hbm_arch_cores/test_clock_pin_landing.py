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


# ot_wbq_root_g0: the two interior M5 clock pins (um): fifo_clk x 108.000-108.048, hbm_clk x 108.192-108.240, y 25.68-26.16.
_PINS = {"fifo_clk": (108.000, 25.68, 108.048, 26.16), "hbm_clk": (108.192, 25.68, 108.240, 26.16)}
_M4_PITCH, _M4_PHASE = 0.048, 0.024      # M4 tracks (horizontal): y = 0.024 + 0.048 n
_VIA_ENC = 0.024                          # the M5 enclosure of a V4 on a track extends this far along y each side


def _landing_tracks(box, guards):
    """M4 track y values over the pin whose V4 + M5 enclosure stays inside the pin rect and is not under an end guard"""
    x0, y0, x1, y1 = box
    out = []
    n = int((y0 - _M4_PHASE) / _M4_PITCH)
    while _M4_PHASE + n * _M4_PITCH <= y1 + _VIA_ENC:
        y = round(_M4_PHASE + n * _M4_PITCH, 4)
        n += 1
        if any(g[1] <= y <= g[3] and g[0] <= (x0 + x1) / 2 <= g[2] for g in guards):
            continue
        if y >= y0 - _VIA_ENC:
            out.append(y)
    return out


def test_end_guards_cover_both_pin_ends_of_both_clock_pins():
    for name, box in _PINS.items():
        top, bot = C.end_guards(box)
        assert top[1] == pytest.approx(box[3] - 0.06) and top[3] == pytest.approx(box[3] + 0.064), name
        assert bot[1] == pytest.approx(box[1] - 0.064) and bot[3] == pytest.approx(box[1] + 0.06), name
        assert top[0] < box[0] and top[2] > box[2]


def test_pin_end_tracks_are_blocked_so_no_landing_overshoots_the_pin_end():
    # without the guard the topmost track (y 26.136, enclosure to 26.160+) is a candidate; the ffc build used it (6 DRC)
    for name, box in _PINS.items():
        free = _landing_tracks(box, [])
        guarded = _landing_tracks(box, C.end_guards(box))
        assert any(y + _VIA_ENC > box[3] + 1e-9 for y in free), name      # the unguarded case reaches past the pin end
        assert guarded, name
        assert all(y + _VIA_ENC <= box[3] + 1e-9 for y in guarded), name  # no enclosure past the top end
        assert all(y - _VIA_ENC >= box[1] - 1e-9 for y in guarded), name  # none past the bottom end


def test_stage_exports_end_guard_env_and_guard_script_has_end_layer(tmp_path):
    k = _kit(tmp_path / "k")
    C.stage(k, ["fifo_clk", "hbm_clk"])
    pre = (k / "core_grt_pre.tcl").read_text()
    assert "OT_CPL_END_CLEAR_UM) 0.06" in pre and "OT_CPL_END_X_UM) 0.1" in pre
    t = C.GUARD.read_text()
    assert "OT_CPL_END_LAYER" in t and "erects" in t and "emine" in t
