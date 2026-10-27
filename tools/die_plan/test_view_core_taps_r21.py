"""CLOCK-KV-R21 (b): view_core_taps pin-view match (signed LEF == plan pins, PG / strap_* tolerated) + orientation."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kv_r21"))
import view_core_taps as V  # noqa: E402


def test_view_match_rules():
    lef = {"ck[0]": ("M5", 1.0, 2.0), "d[0]": ("M4", 0.0, 5.0), "VDD": ("M7", 0, 0)}
    ok, det = V.view_match(lef, {"ck[0]": ("M5", 1.0, 2.0), "d[0]": ("M4", 0.0, 5.0), "strap_bsel[0]": ("M5", 3, 0)})
    assert ok and det["plan_straps"] == ["strap_bsel[0]"]
    ok, det = V.view_match(lef, {"ck[0]": ("M5", 1.0, 2.0), "d[0]": ("M4", 0.0, 9.0)})   # mirrored data pin
    assert not ok and det["geom_diff"] == 1
    ok, _ = V.view_match(lef, {"ck[0]": ("M5", 1.0, 2.0)})                             # pin missing in plan
    assert not ok


def test_place_orient():
    h = dict(outline_um=[10.0, 20.0], origin_um=[100.0, 200.0], orient="MX")
    assert V.place(h, (1.0, 2.0)) == [101.0, 218.0]
    h["orient"] = "R0"; h["track_offset_um"] = [0.0, 0.012]
    assert V.place(h, (1.0, 2.0)) == [101.0, 202.012]
