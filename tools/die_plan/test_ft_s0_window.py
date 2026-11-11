"""ft_s0_window: plan station 0 vs the slot's in window (COORD 11-11 03:0x)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "autopilot"))
import check as C  # noqa: E402


def _P(regs0):
    t = {"outline_um": [829.44, 4320.0],
         "ft_slots": [{"name": "L1259x2", "in_face": "E", "out_face": "N", "in_window_um": [38.464, 220.714],
                       "regs_um": [regs0, [738.72, 2337.12]], "stations": 2, "width": 4}]}
    return SimpleNamespace(types={"q_b010": t}, budgets={})


def test_station0_far_from_in_window_is_error():
    R = C.Report()
    s = C.check_ft_s0_window(_P([790.56, 2185.92]), R)
    assert s["over_reach"] == 1 and s["worst"][0]["um"] > 2000
    assert [i["level"] for i in R.items] == ["ERROR"] and R.items[0]["check"] == "ft_s0_window"


def test_station0_at_in_window_passes():
    R = C.Report()
    s = C.check_ft_s0_window(_P([828.0, 120.0]), R)
    assert s == {"slots": 1, "over_reach": 0, "worst": []} and R.items == []
    near, far = C.ft_s0_window_um(_P([828.0, 120.0]).types["q_b010"], _P([828.0, 120.0]).types["q_b010"]["ft_slots"][0])
    assert near < 2 and 100 < far < 103
