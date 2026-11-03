"""DIE-HBM-60 d44v: ft_nudge keeps FT bit sites off the clock branch-buffer / leg-repeater halo (check.py clock)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_nudge as N  # noqa: E402
import check as C  # noqa: E402


def test_clock_points_and_halo():
    t = {"clock": {"branch_buffers": [{"xy": [10.0, 10.0], "leg_repeaters": [{"xy": [50.0, 20.0]}]}]}}
    pts = N.clock_points(t)
    assert pts == [(10.0, 10.0), (50.0, 20.0)]
    wh = N.CELL_DEFAULT
    assert N.near_clock(49.0, 19.9, wh, pts)                       # cell box covers the repeater
    assert N.near_clock(50.0 + C.CLOCK_BUF_HALO_UM - 0.1, 20.0, wh, pts)
    assert not N.near_clock(50.0 + C.CLOCK_BUF_HALO_UM + 0.1, 20.0, wh, pts)
    assert not N.near_clock(30.0, 30.0, wh, pts)
    assert N.clock_points({}) == []
