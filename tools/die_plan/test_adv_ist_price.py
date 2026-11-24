"""pytest: ADV-IST-PRICE judge on the KV A3c positive (COORD 11-23 20:3x: A3c strict stopped on 'native stations exceed priced lane depth')
and the regenerated A3b/A3d negatives."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_ist_price as A  # noqa: E402


def test_a3c_l816_flagged():
    # A3c lane L816: table stations 23 / cycles 41, live ft stations 24 (GROWHOPS), landing 15, source stations 1
    why = A.judge({"stations": 23, "clock_landing": 15, "cycles": 41}, 24, 15, 1)
    assert any(w.startswith("STALE-TABLE stations") for w in why)
    assert any(w.startswith("PRICE-SHORT") and "= 42" in w for w in why)


def test_a3c_l736_flagged_with_source_depth():
    why = A.judge({"stations": 4, "clock_landing": 4, "cycles": 19}, 5, 4, 9)
    assert any("= 20" in w for w in why)


def test_regenerated_lane_passes():
    # A3b/A3d shape: table matches live counts and carries cycles >= 2 + ft + landing + source stations
    assert A.judge({"stations": 24, "clock_landing": 15, "cycles": 42}, 24, 15, 1) == []
    assert A.judge({"stations": 6, "clock_landing": 4, "cycles": 21}, 6, 4, 9) == []


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-IST-PRICE not checked")
