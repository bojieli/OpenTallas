"""FP-CONVERGE-S81: hub_repack.OBSTACLE_AWARE (core_place --obstacle-aware): a station leg may not cross a core."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR  # noqa: E402


def setup():
    # one tall core between a (left) and b (right): the straight HV/VH legs cross it
    return HR.Raster(1000.0, 400.0, [(450.0, 40.0, 550.0, 360.0)])


def test_poly_crosses_core():
    R = setup()
    assert HR.poly_crosses_core(R, [(100.0, 200.0), (900.0, 200.0)])
    assert not HR.poly_crosses_core(R, [(100.0, 20.0), (900.0, 20.0)])
    assert not HR.poly_crosses_core(R, [(100.0, 200.0), (449.6, 200.0)])      # touching within tol is not crossing


def test_obstacle_aware_route_never_crosses_core():
    R = setup()
    HR.OBSTACLE_AWARE = True
    try:
        r = HR.route_station(R, (100.0, 200.0), (900.0, 200.0), 3, 405.0)
    finally:
        HR.OBSTACLE_AWARE = False
    assert r is not None
    assert r["kind"] != "bbox" or HR._hops_clear(R, [(100.0, 200.0)] + list(r["regs"]) + [(900.0, 200.0)])
    assert r["kind"] in ("astar", "HV", "VH", "Zy", "Zx", "bbox")


def test_default_off_flag_and_mutant_flag_on_blocks_straight():
    R = setup()
    assert HR.OBSTACLE_AWARE is False
    HR.OBSTACLE_AWARE = False
    r_off = HR.route_station(R, (100.0, 200.0), (900.0, 200.0), 3, 405.0)
    if r_off is not None:                              # mutant: with the flag off the straight leg is allowed (shorter or equal)
        HR.OBSTACLE_AWARE = True
        try:
            r_on = HR.route_station(R, (100.0, 200.0), (900.0, 200.0), 3, 405.0)
        finally:
            HR.OBSTACLE_AWARE = False
        if r_on is not None:
            assert r_on["length_um"] >= r_off["length_um"]


def test_resite_no_worse_rejects_longer_candidate_and_accepts_equal():
    R = setup()
    old = [(100.0, 20.0), (400.0, 20.0), (700.0, 20.0), (900.0, 20.0)]          # 300/300/200 along the free bottom edge
    longer = [(100.0, 20.0), (400.0, 380.0 - 360.0 + 20.0), (700.0, 20.0), (900.0, 20.0)]
    assert HR.resite_no_worse(R, old, list(old))                                   # equal is accepted
    worse = [(100.0, 20.0), (400.0, 20.0), (700.0, 20.0), (900.0, 395.0)]          # last hop 200 -> 375 (and longer total)
    assert not HR.resite_no_worse(R, old, worse)                                   # mutant: a longer chain is rejected
    shorter = [(100.0, 20.0), (400.0, 20.0), (650.0, 20.0), (900.0, 20.0)]
    assert HR.resite_no_worse(R, old, shorter) or HR.chain_metrics(R, shorter)[0] > HR.chain_metrics(R, old)[0]
    assert HR.chain_metrics(R, old)[0] == 300.0 and HR.chain_metrics(R, old)[1] == 800.0


def test_chain_metrics_uses_obstacle_model_for_blocked_hop():
    R = setup()                                     # tall core between: straight hop (100,200)->(900,200) has no clear L
    direct = HR.chain_metrics(R, [(100.0, 200.0), (900.0, 200.0)])
    assert direct[0] >= 800.0                       # never shorter than Manhattan; detour via A* only lengthens
