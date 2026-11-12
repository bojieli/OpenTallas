"""S81-T51-PINFIX-2: stage_t51_m7_rephase helpers.   python3 -m pytest -q -p no:cacheprovider --noconftest test_stage_t51_m7_rephase.py"""
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("st", HERE / "stage_t51_m7_rephase.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
G = st.gen(HERE.parents[2])

LEF = """MACRO m
  PIN clk
    PORT
      LAYER M7 ;
        RECT 85.648 604.384 85.68 605.152 ;
    END
  END clk
  PIN d
    PORT
      LAYER M7 ;
        RECT 10.0 1.0 10.032 1.768 ;
      LAYER M5 ;
        RECT 85.648 1.0 85.672 1.084 ;
    END
  END d
END m
"""


def plan(off=(0.108, 0.012)):
    hc = dict(module="m", pins_file="p.json", origin_um=[639.36, 8.64], outline_um=[794.88, 1209.6], orient="R0",
              track_offset_um=list(off))
    return hc, {"partition_types": {"t": {"hard_cores": [hc]}}}


def test_shift_lef_moves_only_named_m7_rects():
    out, n = st.shift_lef(LEF, {"clk"}, 0.02)
    assert n == 1 and "RECT 85.6680 604.3840 85.7000 605.1520 ;" in out
    assert "RECT 10.0 1.0 10.032 1.768 ;" in out and "RECT 85.648 1.0 85.672 1.084 ;" in out


def test_derive_shift_is_the_generator_phase():
    hc, P = plan()
    d, ph = st.derive_shift(G, hc, P, {"clk": [85.648, 604.384, 85.68, 605.152]})
    assert d == pytest.approx(0.020) and ph == pytest.approx(0.052)
    moved = {"clk": ["M7", 85.668, 604.384, 85.7, 605.152]}
    assert G.native_m7_phase(moved, hc, P) == pytest.approx(0.052)       # no refusal after the shift


def test_derive_shift_refuses_mixed_residues():
    hc, P = plan()
    with pytest.raises(SystemExit, match="different shifts"):
        st.derive_shift(G, hc, P, {"a": [85.648, 0, 85.68, 1], "b": [85.652, 0, 85.684, 1]})


def test_pinhash_follows_xy():
    a = [dict(name="clk", layer="M7", x=85.664, y=604.768)]
    b = [dict(name="clk", layer="M7", x=85.684, y=604.768)]
    assert st.pinhash(a) != st.pinhash(b) and len(st.pinhash(a)) == 12


def _type(taps, fwd):
    return {"clock": {"taps": taps, "child_root_taps": {"forwarded_roots": fwd}}}


def test_forwarded_root_may_lack_a_tap():
    moved = {"m.clk_t1": 0.02, "m.fclk_in_ft2_i": 0.02}
    t = _type([{"name": "a", "xy": [1, 2], "lands_on": [{"pin": "m.clk_t1", "xy": [1, 2]}]}], ["fclk_in_ft2_i"])
    assert st.check_landings(t, moved, 1) == ["m.fclk_in_ft2_i"]


def test_unlanded_root_not_forwarded_refuses():
    moved = {"m.clk_t1": 0.02, "m.clk_t2": 0.02}
    t = _type([{"name": "a", "xy": [1, 2], "lands_on": [{"pin": "m.clk_t1", "xy": [1, 2]}]}], ["fclk_in_ft2_i"])
    with pytest.raises(SystemExit, match="neither a tap nor a forwarded entry.*clk_t2"):
        st.check_landings(t, moved, 1)
