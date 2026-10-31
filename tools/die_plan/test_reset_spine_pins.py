"""DIE-KV-52 10-31 (OWNER): bound reset-spine ports (plan reset_spine_pins[]) get a real interior pin site.
python3 -m pytest -q tools/die_plan/test_reset_spine_pins.py"""
import json
from pathlib import Path

import pytest

import gen_phys as G
import schema as S

HERE = Path(__file__).resolve().parent


def _plan(rows):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    tn = next(iter(raw["partition_types"]))
    if rows is not None:
        raw["partition_types"][tn]["reset_spine_pins"] = rows
    return S.Plan(raw), tn


def test_reset_spine_pin_is_placed_and_bound():
    P, tn = _plan([dict(name="ri_core_rst_n", width=1, layer="M7", sites_um=[[10.0, 8.64]])])
    assert G.reset_spine_pin_sites(P, tn) == [("ri_core_rst_n[0]", "M7", 10.0, 8.64)]
    pins = G.type_pins(P, tn)
    io = G.io_tcl(P, tn, pins)
    assert "place_pin -pin_name {ri_core_rst_n[0]} -layer M7 -location {10.0000 8.6400}" in io
    assert ("ri_core_rst_n", 0) in {(p["bus"], p["bit"]) for p in G.port_bind_pin_records(P, tn, pins)}
    assert "ri_core_rst_n[0]" in {r["name"] for r in G.plan_pin_records(P, tn, pins)}


def test_no_reset_spine_pins_keeps_kit_bytes():
    P0, tn = _plan(None)
    P1, _ = _plan([])
    assert G.reset_spine_pin_sites(P0, tn) == []
    assert G.io_tcl(P0, tn, G.type_pins(P0, tn)) == G.io_tcl(P1, tn, G.type_pins(P1, tn))


def test_site_count_must_match_width():
    P, tn = _plan([dict(name="ri_core_rst_n", width=2, layer="M7", sites_um=[[10.0, 8.64]])])
    with pytest.raises(ValueError, match="exactly 2 sites_um"):
        G.reset_spine_pin_sites(P, tn)
