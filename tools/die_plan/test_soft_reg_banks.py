"""Actual CS inventory has one bank per native stage, not per logical row."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import taps
import soft_reg_banks as B


def bank(n=8, name="HI0", x=0):
    return dict(id=name, cell_glob=f"*{name}_*", source="core_stations",
                bit_site_cell_um=[1, 2], bit_sites_um=[[x + i, 0] for i in range(n)])


def test_actual_class_inventory_and_area():
    # Real S81 G4 HI stage has 1025 FF; VE has 742. Logical plan row
    # multiplicity is irrelevant to the canonical actual-bank inventory.
    t = dict(outline_um=[2000, 20], internal_stations=[dict(conn="logical")]*147,
             clock=dict(soft_reg_banks=[bank(1025), bank(742, "VE0", 1100)]))
    sites = B.sink_sites(t)
    assert len(sites) == 1767
    assert sites[0] == (.5, 1, 1)
    assert B.area(t) == 3534
    assert t["clock"]["soft_reg_banks"][0]["bit_sites_um"][0] == [0, 0]


def test_planned_sinks_and_recentre_include_actual_bank(monkeypatch):
    import gen_phys
    import ft_full_stage
    monkeypatch.setattr(gen_phys, "type_pins", lambda *a: [])
    monkeypatch.setattr(ft_full_stage, "load", lambda *a: {})
    t = dict(outline_um=[100, 100], clock=dict(soft_reg_banks=[bank()]))
    P = SimpleNamespace(types={"t": t})
    assert taps.planned_sinks(P, "t") == [(i+.5, 1., "soft_reg_bank") for i in range(8)]
    assert taps.sink_sites(P, "t", control=False) == B.sink_sites(t)
    assert taps.recentre_sinks(P, "t") == B.sink_sites(t)


def test_full_placed_bins_remain_authoritative(tmp_path, monkeypatch):
    p = tmp_path / "bins.json"
    p.write_text(json.dumps(dict(bins=[[20, 30, 1767]])))
    t = dict(clock=dict(sink_bins_file="bins.json", soft_reg_banks=[bank()],
                        sink_sites_um=[[50, 60, 2]]))
    P = SimpleNamespace(types={"t": t}, path=str(tmp_path / "plan.json"))
    monkeypatch.setattr(taps, "planned_sinks", lambda *a, **kw: pytest.fail("placed inventory counted twice"))
    assert taps.sink_sites(P, "t", control=False) == [(50., 60., 2.), (20., 30., 1767.)]


def test_native_domain_inventory_remains_authoritative(monkeypatch):
    import native_clock_domains
    monkeypatch.setattr(native_clock_domains, "core_planning_sites", lambda *a: [(5, 6, 8)])
    P = SimpleNamespace(types={"t": dict(clock=dict(native_domains={}, soft_reg_banks=[bank()]))})
    assert taps.sink_sites(P, "t", control=False) == [(5, 6, 8)]


@pytest.mark.parametrize("change", [
    lambda rows: rows.append(copy.deepcopy(rows[0])),
    lambda rows: rows[0].update(bit_sites_um=[[float("nan"), 0]]),
    lambda rows: rows[0].update(bit_site_cell_um=[0, 2]),
    lambda rows: rows[0].update(bit_sites_um=[]),
    lambda rows: rows[0].update(bit_sites_um=[[[0, 0]]]),
    lambda rows: rows[0].update(bit_sites_um=[[0, 0], [0, 0]]),
    lambda rows: rows[0].update(bit_sites_um=[[100, 0]]),
    lambda rows: rows[0].update(source=""),
])
def test_bad_inventory_fails_closed(change):
    t = dict(outline_um=[100, 100], clock=dict(soft_reg_banks=[bank()]))
    change(t["clock"]["soft_reg_banks"])
    with pytest.raises(ValueError, match="soft_reg_banks"):
        B.sink_sites(t)


def test_default_unchanged():
    assert B.sink_sites({}) == []
    assert B.area({}) == 0
