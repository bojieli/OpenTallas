"""Requested clock reach remains binding when legal repeater sites are unavailable."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM


def run_blocked(length, reach, legal_x=None):
    cells = {"driver": {"x": 0.0, "y": 0.0}}
    nets = [{"name": "tail", "drv": "driver", "loads": ["port:tap"]}]
    out = {"unplaced": []}
    def forbidden_cell(*args, **kwargs):
        raise AssertionError("no legal repeater is available")
    # Equal-cut sites are blocked. The one-repeater fallback can use only a site
    # near the driver, whose far hop was previously accepted against 750 um.
    def blocked(_keepouts, point):
        return legal_x is None or abs(point[0] - legal_x) > 0.01
    with patch.object(CM, "free_near", return_value=(None, None)), \
         patch.object(CM, "detour_sites", return_value=None), \
         patch.object(CM, "hitf", side_effect=blocked):
        added = CM.split_long(cells, nets, object(), {"tap": (length, 0)},
                              reach, forbidden_cell, out=out, both_l=True)
    assert added == 0
    assert nets[0]["loads"] == ["port:tap"]
    return out


def test_unsplit_tail_between_405_and_750_is_structural():
    out = run_blocked(600.0, 405.0)
    assert len(out["unplaced"]) == 1
    assert "405 um" in out["unplaced"][0][2]
    assert out["unsplit_clock_branches"][0]["span_bound_um"] > 405


def test_one_repeater_fallback_cannot_admit_long_far_hop():
    out = run_blocked(700.0, 405.0, legal_x=108.0)
    assert len(out["unplaced"]) == 1
    assert "405 um" in out["unplaced"][0][2]


def test_larger_explicit_bound_preserves_legal_direct_tail():
    out = run_blocked(800.0, 900.0)
    assert out["unplaced"] == []
    assert not out.get("unsplit_clock_branches")
