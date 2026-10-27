"""S81-CORE-LAT-R13: core_family_slice unit checks (no docker, no build)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_family_slice as F


def test_splits_family_menu():
    fam = dict(leaf_target=48)
    assert F.splits_for(13238, fam)[:2] == [2, 2]          # W/E x 2 islands per side always
    assert F.splits_for(3655, fam) == [2, 2, 4, 4]
    assert F.splits_for(100, fam) == [2, 2, 1] or F.splits_for(100, fam)[:2] == [2, 2]


def test_farthest_clusters_cover_and_limit():
    pts = [(float(x), float(y), "DFF", "r%d_%d" % (x, y), "CLK") for x in range(0, 200, 5) for y in (0, 1)]
    pts += [(5.0, 150.0, "DFF", "iso", "CLK")]
    g = F.farthest_clusters(pts, 30.0)
    flat = [p for x in g for p in x]
    assert sorted(flat) == sorted(pts)                       # every sink exactly once
    for x in g:
        cx = sum(p[0] for p in x) / len(x); cy = sum(p[1] for p in x) / len(x)
        assert max(abs(p[0] - cx) + abs(p[1] - cy) for p in x) <= 30.0
