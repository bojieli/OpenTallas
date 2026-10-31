"""clock.tap_mode grid+explicit (DIE-S81-39 10-31): the R4 grid unchanged + validated ADDED taps."""
import copy
import json
from pathlib import Path
import pytest
import schema
import taps
import reset_tree as RT


def raw():
    return json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())


def plan(added, **ck):
    r = raw()
    t = r["partition_types"]["src"]["clock"]
    t.update(tap_mode="grid+explicit", added_taps=added, **ck)
    return schema.Plan(r)


def n_grid():
    return len(schema._grid_taps(schema.Plan(raw()), "src"))


def test_grid_taps_equal_grid_mode():
    grid = schema.tap_grid(schema.Plan(raw()), "src")
    P = plan([])
    assert schema.tap_grid(P, "src") == grid
    assert taps.grid_explicit_sites(P, "src") == grid


def test_added_names_must_follow_the_grid_in_order():
    n = n_grid()
    with pytest.raises(ValueError, match="names/order"):
        taps.grid_explicit_sites(plan([dict(name=f"clk_t{n + 1}", xy=[100., 100.])]), "src")


def test_added_tap_in_a_macro_halo_is_refused(monkeypatch):
    n = n_grid()
    monkeypatch.setattr(schema, "placed_macro_boxes", lambda t, halo=0.0: {"m": (50. - halo, 50. - halo, 200. + halo, 200. + halo)})
    with pytest.raises(ValueError, match="outline/halo"):
        taps.grid_explicit_sites(plan([dict(name=f"clk_t{n}", xy=[204., 120.])]), "src")


def test_empty_added_tap_is_refused(monkeypatch):
    n = n_grid()
    monkeypatch.setattr(taps, "sink_sites", lambda P, tn, control=True: [(432., 432., 5.)])
    monkeypatch.setattr(RT, "for_type", lambda P, tn: {"relays": []})
    with pytest.raises(ValueError, match="empty=True"):
        taps.grid_explicit_taps(plan([dict(name=f"clk_t{n}", xy=[60., 60.])]), "src")


def test_tap_holding_only_relays_is_accepted(monkeypatch):
    n = n_grid()
    monkeypatch.setattr(taps, "sink_sites", lambda P, tn, control=True: [(432., 432., 5.)])
    monkeypatch.setattr(RT, "for_type", lambda P, tn: {"relays": [{"xy": (62., 62.)}, {"xy": (70., 58.)}]})
    out = taps.grid_explicit_taps(plan([dict(name=f"clk_t{n}", xy=[60., 60.])]), "src")
    assert out[-1][0] == f"clk_t{n}" and out[-1][3] == 2


def test_grid_taps_keep_grid_rules_but_added_taps_get_radius(monkeypatch):
    n = n_grid()
    monkeypatch.setattr(RT, "for_type", lambda P, tn: {"relays": []})
    # an added tap far from its only sink fails its radius; an empty grid tap is allowed (grid mode)
    monkeypatch.setattr(taps, "sink_sites", lambda P, tn, control=True: [(20., 20., 1.)])
    with pytest.raises(ValueError, match="radius="):
        taps.grid_explicit_taps(plan([dict(name=f"clk_t{n}", xy=[60., 60.])], tap_radius_um=10.), "src")
