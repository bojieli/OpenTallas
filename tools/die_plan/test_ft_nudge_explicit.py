"""DIE-HBM-75 11-05: ft_nudge keeps an explicit regs_um chain; only a station centre inside a core moves."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_nudge as N  # noqa: E402


def test_free_chain_unchanged():
    regs = [[50.0, 150.0], [250.0, 150.0], [250.0, 400.0]]
    out, worst, smax = N.nudge_explicit(regs, [(100, 100, 200, 200)], 1000, 1000, (0, 150), (250, 600))
    assert out == regs and worst == 0.0 and smax == 0.0


def test_only_hit_station_moves_and_stays_close():
    regs = [[50.0, 150.0], [150.0, 150.0], [300.0, 150.0]]
    out, worst, smax = N.nudge_explicit(regs, [(100, 100, 200, 200)], 1000, 1000, (0, 150), (400, 150))
    assert out[0] == regs[0] and out[2] == regs[2]
    assert not N.inside(out[1], [(100, 100, 200, 200)])
    assert smax <= N.MAX_SLIDE and worst <= 160.0
