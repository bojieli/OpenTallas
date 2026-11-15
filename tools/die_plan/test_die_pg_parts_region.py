"""GENBUG-3 (2026-11-15): with die.pg.domains the partition macro grids go into the region domains (one grid per
ot_pg_* region, partitions by centre), not into the stripe-less default Core domain (PDN-0233: empty grids)."""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial  # noqa: E402
import pg_regions  # noqa: E402

GRID = [dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32),
        dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32)]


def test_plain_die_keeps_one_parts_grid_in_core():
    P = SimpleNamespace(die=dict(pg=dict(grid=GRID)), W=200.0, H=200.0)
    t = die_trial.psm_pdn_tcl(P)
    assert "define_pdn_grid -name {parts} -voltage_domains {CORE} -macro" in t
    assert "parts_$ot_n" not in t


def test_region_die_has_no_core_parts_grid(monkeypatch):
    monkeypatch.setattr(pg_regions, "pdn_tcl", lambda die, loads=(): "set b [ord::get_db_block]\n# regions\n")
    P = SimpleNamespace(die=dict(pg=dict(grid=GRID, domains=[dict(nets=["VDDPHY", "VSS"])])), W=200.0, H=200.0)
    t = die_trial.psm_pdn_tcl(P)
    assert "-name {parts}" not in t and "-voltage_domains {Core} -macro" not in t
    assert "define_pdn_grid -name parts_$ot_n -voltage_domains $ot_n -macro -instances $ot_l" in t
    assert "add_pdn_connect -grid parts_$ot_n -layers {M7 M8}" in t
    assert "OT_HOOK_COVERAGE hook=die_pg_parts" in t and "@L0@" not in t
    assert t.index("set b [ord::get_db_block]") < t.index("foreach ot_r [$b getRegions]")
