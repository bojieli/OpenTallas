import json, tempfile
from pathlib import Path
import render_type_heat as R


def test_blank_type_is_not_modelled():
    t = {"outline_um": [200, 100], "clock": {"tap_um": [100, 50]}}
    with tempfile.TemporaryDirectory() as d:
        r = R.render_type("x", t, str(Path(d) / "x.png"))
    assert r["modelled"] is False and r["peak_util"] is None and r["legs_over_405"] is None


def test_detail_draws_pins_stations_legs():
    t = {"outline_um": [1000, 100], "clock": {"tap_um": [500, 50], "landing_contract": {"pins": [
        {"name": "a_i", "dir": "in", "xy_um": [0.0, 50.0]}, {"name": "a_o", "dir": "out", "xy_um": [1000.0, 50.0]}]}},
         "ft_slots": [{"name": "a", "in_face": "W", "out_face": "E", "stations": 4, "in_window_um": [40, 60], "out_window_um": [40, 60]}]}
    legs = R.chain_legs(t)
    assert len(legs) == 1 and len(legs[0][1]) == 5 and abs(legs[0][2][0] - 250.0) < 1e-6 and max(legs[0][2]) <= 405
    assert len(R.pin_pts(t)) == 2
    with tempfile.TemporaryDirectory() as d:
        r = R.render_type("x", t, str(Path(d) / "x.png"), [("clk", 500.0, 50.0)])
    assert r["detail"] and r["chains"] == 1 and r["pins"] == 2 and r["max_hop_um"] == 250.0 and r["hops_over_405"] == 0
    t["ft_slots"][0]["stations"] = 2
    assert R.chain_legs(t)[0][2][0] == 500.0
