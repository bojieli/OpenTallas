"""L2H-GEN2D-RST 10-19: bounded reset route search (reset_forest_geometry.bounded_route)."""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hbm_die_v15"))

import reset_forest_geometry as rfg
from reset_forest_geometry import bounded_route
from die_clock_tree import Grid


@pytest.fixture(autouse=True)
def _bound():
    old = rfg.ROUTE_DETOUR, rfg.ROUTE_SLACK, rfg.ROUTE_MAX_POPS
    rfg.ROUTE_DETOUR, rfg.ROUTE_SLACK, rfg.ROUTE_MAX_POPS = 2.0, 64, 3_000_000
    yield
    rfg.ROUTE_DETOUR, rfg.ROUTE_SLACK, rfg.ROUTE_MAX_POPS = old


def test_same_length_as_unbounded_on_a_detour_grid():
    g = Grid(3000., 3000., [(500., 0., 520., 600.)])   # a wall with a gap above: path must detour (190 cells, cap 244)
    a, b = g.cell(100., 100.), g.cell(1000., 100.)
    ref = g._route(a, b, 5.)
    got = bounded_route(g, a, b, 5.)
    assert len(got) == len(ref) and got[0] == a and got[-1] == b


def test_blocked_run_budget_is_unchanged():
    g = Grid(2000., 2000., [(500., 0., 560., 2000.)])   # 6-cell wall, full height
    a, b = g.cell(100., 100.), g.cell(1000., 100.)
    assert bounded_route(g, a, b, 70.)                     # R = 7 cells overflies the 6-cell wall
    with pytest.raises(SystemExit):
        bounded_route(g, a, b, 50.)                        # R = 5 cells does not (same as the unbounded router)
    with pytest.raises(SystemExit):
        g._route(a, b, 50.)


def test_walled_target_fails_fast():
    # a target enclosed by a thick ring on a large grid: the unbounded router floods the whole grid; the bounded one stops
    g = Grid(20000., 20000., [(9000., 9000., 11000., 9500.), (9000., 10500., 11000., 11000.),
                              (9000., 9000., 9500., 11000.), (10500., 9000., 11000., 11000.)])
    a, b = g.cell(8000., 10000.), g.cell(10000., 10000.)
    t = time.time()
    with pytest.raises(SystemExit):
        bounded_route(g, a, b, 50.)
    assert time.time() - t < 30


def test_legacy_mode_is_the_clock_router():
    rfg.ROUTE_DETOUR = 0.0
    g = Grid(1000., 1000., [])
    a, b = g.cell(5., 5.), g.cell(905., 505.)
    assert bounded_route(g, a, b, 50.) == g._route(a, b, 50.)
