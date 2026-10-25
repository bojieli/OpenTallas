"""Route search must offer inboard escapes when an aligned PHY row is unavailable."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("s81_route_under_test", HERE / "gen_plan_v4.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def test_aligned_phy_endpoints_can_escape_row():
    a, b = (0, 19), (6, 19)
    paths = list(G.candidates(a, b))
    assert [a, (0, 18), (6, 18), b] in paths
    assert len({tuple(p) for p in paths}) == len(paths)
    for path in paths:
        assert path[0] == a and path[-1] == b
        assert all(x[0] == y[0] or x[1] == y[1] for x, y in zip(path, path[1:]))
        assert all(0 <= x < G.NC and 0 <= y < G.NR for x, y in G.poly_cells(path))


def test_vertical_phy_link_has_inboard_column_escape():
    a, b = (0, 0), (0, 15)
    assert [a, (1, 0), (1, 15), b] in list(G.candidates(a, b))
