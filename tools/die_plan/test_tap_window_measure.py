"""S81-COL-CLK-1116 spec 0b: tap_window_measure.py turns the CTS tap statistics into per-port window rows."""
import json

import tap_window_measure as M

LOG = """junk
OT_TAP_BALANCE it1 target 450: clk=430(425-457,97) clk_c0=447(447-447,1) clk_t10=348(323-475,454)
OT_TAP_BALANCE it3 target 450: clk=452(447-479,97) clk_c0=447(447-447,1) clk_t10=348(323-475,454) clk_t18=424(409-504,2103)
OT_TAP_BALANCE done: 599 delay cells; tap mean insertion 349..479 ps
"""


def test_last_line_and_parse():
    taps = M.parse_taps(M.last_tap_line(LOG))
    assert set(taps) == {"clk", "clk_c0", "clk_t10", "clk_t18"}
    assert taps["clk_t10"] == dict(mean=348.0, min=323.0, max=475.0, sinks=454)


def test_windows_half_range_with_floor():
    taps = M.parse_taps(M.last_tap_line(LOG))
    w = M.windows(taps)
    assert w == {"clk": 16, "clk_c0": 10, "clk_t10": 76, "clk_t18": 48}
    assert M.windows(taps, floor=20)["clk_c0"] == 20


def test_summary_and_cli(tmp_path):
    p = tmp_path / "cts.log"
    p.write_text(LOG)
    out = tmp_path / "rows.json"
    assert M.main(["--type", "T", "--log", str(p), "--out", str(out), "--cap", "40"]) == 0
    assert json.loads(out.read_text()) == {"clock.tap_window.per_port_ps": {"T": {
        "clk": 16, "clk_c0": 10, "clk_t10": 76, "clk_t18": 48}}}
    s = M.summary(M.parse_taps(M.last_tap_line(LOG)), M.windows(M.parse_taps(M.last_tap_line(LOG))), 40)
    assert s["over_cap"] == {"clk_t10": 76, "clk_t18": 48} and s["mean_spread"] == 104.0


def test_no_line_is_error(tmp_path):
    p = tmp_path / "x.log"
    p.write_text("nothing\n")
    assert M.main(["--type", "T", "--log", str(p)]) == 2
