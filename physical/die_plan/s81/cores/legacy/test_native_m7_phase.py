"""DIE-S81-85 11-09 (native split class fix 3, at the source): native M7 clock root pins and the kit M7 tracks follow
the DIE M7 lattice in the core frame.   python3 -m pytest -q -p no:cacheprovider --noconftest test_native_m7_phase.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402


def plan(off, orient="R0", origin=(639.36, 8.64), w=794.88):
    hc = dict(module="m", pins_file="inputs/core_pins/m.json", origin_um=list(origin), outline_um=[w, 1209.6],
              orient=orient, track_offset_um=list(off))
    return hc, {"partition_types": {"t": {"hard_cores": [hc]}}}


def root(cx):
    return {"clk": ["M7", cx - 0.016, 8.288, cx + 0.016, 9.056]}


def test_phase_is_the_die_lattice_in_the_core_frame():
    hc, P = plan([0.0, 0.0])
    assert G.native_m7_phase(root(85.664), hc, P) == 0.032            # origin on the lattice: the source phase
    hc, P = plan([0.108, 0.012])
    assert G.native_m7_phase(root(85.684), hc, P) == pytest.approx(0.052)   # 0.032 - 0.108 (mod 0.064)


def test_source_phase_root_refused_at_the_core_offset():
    hc, P = plan([0.108, 0.012])
    with pytest.raises(SystemExit, match=r"off the die M7 lattice .* clk \+0.020"):
        G.native_m7_phase(root(85.664), hc, P)


def test_mirrored_and_inconsistent_instances():
    hc, P = plan([0.108, 0.012], orient="MY")
    loc = round((round(794.88 * 1000) + round(639.468 * 1000) - 32) % 64) / 1000.0
    assert G.native_m7_phase(root(85.632 + loc), hc, P) == pytest.approx(loc)
    hc, P = plan([0.108, 0.012])
    other = dict(hc, origin_um=[639.36 + 0.016, 8.64])
    P["partition_types"]["u"] = {"hard_cores": [other]}
    with pytest.raises(SystemExit, match="plan instances put the die M7 lattice"):
        G.native_m7_phase(root(85.684), hc, P)


def test_kit_tracks_take_the_phase():
    t = G.kit_tracks(None, 0.052)
    assert "make_tracks M7 -x_offset 0.052 -x_pitch 0.064" in t
