"""C9-KVPV-CLAND-LEG: reader START target inside a grown macro box snaps to the nearest legal point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_start_corridor_event as K  # noqa: E402


def test_legal_target_unchanged():
    assert K.legal_target((50.0, 50.0), [[100.0, 100.0, 200.0, 200.0]], 400.0, 400.0) == ((50.0, 50.0), False)


def test_target_inside_macro_snaps_to_nearest_grown_edge():
    t, moved = K.legal_target((110.0, 150.0), [[100.0, 100.0, 200.0, 200.0]], 400.0, 400.0)
    assert moved and t == (100.0 - K.CLEAR_UM, 150.0)
    from start_obstacle_path import path
    assert path((10.0, 12.0), t, [[100.0, 100.0, 200.0, 200.0]], clearance_um=K.CLEAR_UM, bounds=(0.0, 0.0, 400.0, 400.0))


def test_target_in_abutted_macros_skips_illegal_edge():
    obs = [[100.0, 100.0, 200.0, 200.0], [200.0, 100.0, 300.0, 200.0]]
    t, moved = K.legal_target((198.0, 120.0), obs, 400.0, 400.0)
    assert moved and t == (198.0, 100.0 - K.CLEAR_UM)
    from start_obstacle_path import path
    assert path((10.0, 12.0), t, obs, clearance_um=K.CLEAR_UM, bounds=(0.0, 0.0, 400.0, 400.0))


def test_no_legal_point_returns_none():
    assert K.legal_target((50.0, 50.0), [[0.0, 0.0, 100.0, 100.0]], 100.0, 100.0) == (None, True)


def test_snapped_target_relays_may_sit_along_own_band():
    """v12 i_slg_W_N_rsp: the snapped target is 4.3 um under its own band; the last corridor leg runs in that band's
    clearance, so the band must not forbid sites (it is the destination)"""
    from start_obstacle_path import relay_sites
    own = [40.0, 241.9, 590.0, 298.9]
    tgt, _ = K.legal_target((560.0, 270.4), [[50.0, 242.0, 590.0, 300.0]], 700.0, 700.0)
    assert tgt == (560.0, 242.0 - K.CLEAR_UM)
    route = [(10.0, 12.0), (10.0, tgt[1]), tgt]
    sites = relay_sites(route, 2, max_hop_um=300.0, site_boxes=[], clearance_um=K.CLEAR_UM)
    assert len(sites) == 2
    import pytest
    with pytest.raises(ValueError):
        relay_sites(route, 2, max_hop_um=300.0, site_boxes=[own], clearance_um=K.CLEAR_UM)
