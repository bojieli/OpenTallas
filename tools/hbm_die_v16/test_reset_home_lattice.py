"""HBMc/CHAIN 10-22: reset home lattice covers the die at the requested pitch (every point within pitch/sqrt2 + site)."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reset_home_lattice import lattice  # noqa: E402


def test_lattice_covers_die_within_reach_budget():
    W, H, P = 5000.0, 3000.0, 216.0
    s = lattice(W, H, P)
    assert len({x['name'] for x in s}) == len(s)
    for x in s:
        assert 0 <= x['x'] and x['x'] + x['w'] <= W and 0 <= x['y'] and x['y'] + x['h'] <= H
        assert x['w'] == x['h'] == 32.4 and x['slide_um'] == 108.0
    worst = 0.0
    for gx in range(0, int(W), 50):
        for gy in range(0, int(H), 50):
            d = min(math.hypot(gx - (x['x'] + 16.2), gy - (x['y'] + 16.2)) for x in s)
            worst = max(worst, d)
    assert worst <= P / math.sqrt(2) + 64.8 + 32.4, worst
    assert worst < 405 / 2


def test_pitch_sets_density():
    assert len(lattice(5000, 3000, 216)) > len(lattice(5000, 3000, 432)) * 3
