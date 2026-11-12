"""COORD 11-12: lane stations inside a signed (hard, phy_macro) PHY core are exempt from street_die_leg only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check as C  # noqa: E402


class _P:
    def __init__(self, hard=True, kind="phy_macro"):
        self.die = {"io": [{"name": "io_phy_A_phy", "kind": kind, "part": "phy_A"}]}
        self.parts = {"phy_A": {"type": "t_phy"}, "core_B": {"type": "t_b"}}
        self.types = {"t_phy": {"hard": hard}, "t_b": {"hard": True}}


KO = [(0, 0, 100, 100, "io/io_phy_A_phy"), (200, 0, 300, 100, "core_B/u_mem"), (40, 40, 60, 60, "phy_A/clock_keepout_0")]
PTS = [("L1#1", (20, 20), "lane_station"),      # inside the PHY core only -> exempt
       ("L1#2", (50, 50), "lane_station"),      # inside the PHY core AND its clock keepout -> kept
       ("L2#1", (250, 50), "lane_station"),     # inside a foreign core -> kept
       ("ck#1", (20, 30), "clock_driver"),      # clock point inside the PHY -> never exempt
       ("L3#1", (150, 50), "lane_station")]     # on a street -> kept (no finding anyway)


def test_station_inside_hard_phy_exempt_only():
    kept, ex = C.phy_core_station_exempt(_P(), KO, PTS)
    assert [q[0] for q in ex] == ["L1#1"]
    assert [q[0] for q in kept] == ["L1#2", "L2#1", "ck#1", "L3#1"]


def test_soft_or_non_phy_io_not_exempt():
    for P in (_P(hard=False), _P(kind="bump_field")):
        kept, ex = C.phy_core_station_exempt(P, KO, PTS)
        assert ex == [] and kept == PTS
