"""S81-CORE-LAT-R14 10-27: gen_core_kit_legacy.py fixes -- M6 pin grant (ot_s81sl_xrt3 KeyError 'M6') and the
hard-children refusal detail (dsdv_bksel_q / ot_s81sl_capc5r).  Pure unit tests (no repo plan / ORFS needed).
    python3 -m pytest -q -p no:cacheprovider --noconftest physical/die_plan/s81/cores/legacy/test_gen_core_kit_legacy_r14.py"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

W, H = 207.36, 164.16
# xrt3 plan placement (die_plan.json dsdv_slice_iq_C__t1 / c3x_C__t1): MX, origin y 1019.52, track_offset y 0.036
INST = dict(module="X", pins_file="p.json", outline_um=[W, H], orient="MX", origin_um=[492.48, 1019.52],
            track_offset_um=[0.108, 0.036], obs_max="M6", inst="u_c.u_xr")


def _plan(*insts):
    return {"partition_types": {f"t{i}": {"hard_cores": [c]} for i, c in enumerate(insts)}}


def _pins():
    # the real xrt3 M6 phase: 4 nm in the core frame (c_d[0] at y 6.852)
    return [dict(name="a[0]", layer="M6", x=0.042, y=6.852), dict(name="a[1]", layer="M6", x=W - 0.042, y=14.148),
            dict(name="b[0]", layer="M4", x=0.042, y=6.828), dict(name="c[0]", layer="M5", x=10.284, y=0.042)]


def test_no_m6_pins_byte_identical():
    pins = [q for q in _pins() if q["layer"] != "M6"]
    assert G.m6_pin_grant(pins, dict(INST, obs_max=None), _plan(INST)) is None
    assert G.kit_tracks(None) == G.TRACKS


def test_m6_grant_phase_from_die_lattice():
    off = G.m6_pin_grant(_pins(), INST, _plan(INST, dict(INST, origin_um=[570.24, 1019.52])))
    assert off == pytest.approx(0.004)
    t = G.kit_tracks(off)
    assert "make_tracks M6 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.004 -y_pitch 0.064" in t
    assert [ln for ln in t.splitlines() if "M6" not in ln] == [ln for ln in G.TRACKS.splitlines() if "M6" not in ln]
    assert G.RECT["M6"] == (0.084, 0.032)                       # plan pin half-width 0.042 on the W/E face


def test_m6_needs_plan_grant():
    with pytest.raises(SystemExit, match="obs_max"):
        G.m6_pin_grant(_pins(), dict(INST, obs_max="M5"), _plan(INST))


def test_m6_only_on_ew_faces():
    pins = _pins() + [dict(name="n[0]", layer="M6", x=50.0, y=H - 0.016)]
    with pytest.raises(SystemExit, match="E/W"):
        G.m6_pin_grant(pins, INST, _plan(INST))


def test_m6_phase_mismatch_refused():
    pins = _pins() + [dict(name="a[2]", layer="M6", x=0.042, y=20.0)]       # 20.000 = 32 nm phase
    with pytest.raises(SystemExit, match="track phases"):
        G.m6_pin_grant(pins, INST, _plan(INST))
    other = dict(INST, origin_um=[492.48, 1019.52 + 0.048])                 # an instance off the die M6 lattice phase
    with pytest.raises(SystemExit, match="plan instance"):
        G.m6_pin_grant(_pins(), INST, _plan(INST, other))


def test_hard_children_refusal_lists_missing(tmp_path):
    v = tmp_path / "physical/ref_tile/k/views/ot_child"
    v.mkdir(parents=True)
    for ext in (".lef", "_tt.lib", "_ff.lib"):
        (v / f"ot_child{ext}").write_text("x")
    (v / "insertion.json").write_text("{}")
    spec = {"children": [{"view": "physical/ref_tile/k/views/ot_child", "inst": f"u{i}"} for i in range(3)]}
    msg = G.hard_children_refusal("top", spec, tmp_path)
    assert "3 hard children must be SIGNED first (refused)" in msg and "ot_child x3 missing [bb, signoff=none]" in msg
    (v / "ot_child_bb.v").write_text("module ot_child(); endmodule")
    (tmp_path / "physical/ref_tile/k/signoff").mkdir()
    (tmp_path / "physical/ref_tile/k/signoff/signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
    assert "ot_child x3 missing [nothing]" in G.hard_children_refusal("top", spec, tmp_path)
