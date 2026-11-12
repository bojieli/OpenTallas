"""PIN_FACE_BLOCKED guard (HBM-GEOM-2 11-12): PHY_NW / PHY_NC / q_b010 geometry in miniature."""
import json

import pytest

import pin_face_guard as G

LEF = "MACRO phy\n  SIZE 2661.12 BY 1177.2 ;\nEND phy\n"


def phy(tmp_path, y, o):
    p = tmp_path / "phy.lef"
    p.write_text(LEF)
    return [{"inst": "u_phy_Q", "master": "phy", "lef": str(p), "x": 0.0, "y": y, "o": o}]


def w_pins(lo, hi, n=100):
    return [("L8_i", i, "M4", 0.0, lo + (hi - lo) * i / (n - 1), "W") for i in range(n)]


OUT = (2661.12, 2073.6)


def test_r0_macro_blocks_the_w_window(tmp_path):
    """PHY_NW today: macro at the bottom, W pins y 1-1055 all against it."""
    rep = G.apply("PHY_NW", tmp_path, OUT, w_pins(1, 1055), [], phy(tmp_path, 0.0, "R0"))
    assert rep["blocked_pins"] == 100
    assert rep["free_spans_um"]["W"] == [[1187.2, 2073.6]]
    assert json.loads((tmp_path / "pin_face_blocked.json").read_text())["rows"][0]["bus"] == "L8_i"


def test_flipped_macro_clears_a_window_below_880(tmp_path):
    """phy_flip: macro at y 889.92 MX, W window re-laid to y 0.5-879.6: nothing blocked, no receipt."""
    rep = G.apply("PHY_NW", tmp_path, OUT, w_pins(0.5, 879.6), [], phy(tmp_path, 889.92, "MX"))
    assert rep["rows"] == [] and rep["taps"] == []
    assert not (tmp_path / "pin_face_blocked.json").exists()


def test_flip_without_window_clip_reports_the_overlap(tmp_path):
    """the flip alone (window still 1-1055) blocks only the pins above 879.92."""
    rep = G.apply("PHY_NW", tmp_path, OUT, w_pins(1, 1055), [], phy(tmp_path, 889.92, "MX"))
    lo, hi = rep["rows"][0]["blocked_spans_um"][0]
    assert 879.9 <= lo < 890.0 and hi == pytest.approx(1055)
    assert rep["free_spans_um"]["W"] == [[0.0, 879.92]]


def test_tap_inside_a_macro(tmp_path):
    rep = G.apply("PHY_NC", tmp_path, OUT, [], [("clk", 1442.9, 1000.0), ("arst_n", 1442.9, 4.32)],
                  phy(tmp_path, 889.92, "MX"))
    assert [t["pin"] for t in rep["taps"]] == ["clk"]


def test_error_mode_raises(tmp_path):
    with pytest.raises(ValueError, match="PIN_FACE_BLOCKED"):
        G.apply("PHY_NW", tmp_path, OUT, w_pins(1, 1055), [], phy(tmp_path, 0.0, "R0"), mode="error")


def test_off_and_no_macro(tmp_path):
    assert G.apply("PHY_NW", tmp_path, OUT, w_pins(1, 1055), [], phy(tmp_path, 0.0, "R0"), mode="off") is None
    assert G.apply("q", tmp_path, OUT, w_pins(1, 1055), [], []) is None


def test_s_face_gaps_q_b010_shape(tmp_path):
    """q_b010: a row of macros 4.32 um above the S face; only the gaps wider than 2 x clear stay free."""
    p = tmp_path / "m.lef"
    p.write_text("MACRO m\n SIZE 106.272 BY 290.304 ;\nEND m\n")
    placed = [{"inst": f"m{i}", "master": "m", "lef": str(p), "x": x, "y": 4.32, "o": "R0"}
              for i, x in enumerate((66.528, 178.848, 316.224))]
    pins = [("L5054_o", i, "M5", 70.0 + i, 0.0, "S") for i in range(50)]
    rep = G.check("q_b010", (1304.64, 2479.68), pins, [], G.macro_boxes(placed))
    assert rep["blocked_pins"] == 50
    assert rep["free_spans_um"]["S"][0] == [0.0, 56.528]
    assert G.check("q_b010", (1304.64, 2479.68), pins, [], G.macro_boxes(
        [dict(q, y=4.32 + 17.28) for q in placed]))["blocked_pins"] == 0
