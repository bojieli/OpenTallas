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
    monkeypatch.setattr(pg_regions, "pdn_tcl", lambda die, loads=(), parts=None: "set b [ord::get_db_block]\n# regions\n")
    P = SimpleNamespace(die=dict(pg=dict(grid=GRID, domains=[dict(nets=["VDDPHY", "VSS"])])), W=200.0, H=200.0)
    t = die_trial.psm_pdn_tcl(P)
    assert "-name {parts}" not in t and "-voltage_domains {Core} -macro" not in t
    assert "define_pdn_grid -name parts_$ot_n -voltage_domains $ot_n -macro -instances $ot_l" in t
    assert "add_pdn_connect -grid parts_$ot_n -layers {M7 M8}" in t
    assert "OT_HOOK_COVERAGE hook=die_pg_parts" in t and "@L0@" not in t
    assert t.index("set b [ord::get_db_block]") < t.index("foreach ot_r [$b getRegions]")


def test_region_without_crossing_is_skipped_or_fails():
    """FABLE-TRIAGE-HEADKV s12: a 6.48 um wide column holds no M9 stripe (pitch 39.96): skip when empty, fail with a partition."""
    grid = [dict(layer="M8", width_um=0.48, pitch_um=4.32, offset_um=2.16),
            dict(layer="M9", width_um=12.96, pitch_um=39.96, offset_um=16.47)]
    die = dict(outline_um=[100.0, 100.0], pg=dict(grid=grid, domains=[
        dict(nets=["VDDPHY", "VSS"], rect_um=[0, 0, 93.52, 100], grid=grid)]))
    cls = {c[0]: c for c in pg_regions.region_class(die, parts=[])}
    narrow = [c for c in cls.values() if c[1][2] - c[1][0] == 6480 or c[1][3] - c[1][1] == 6480]
    for c in cls.values():
        w, h = (c[1][2] - c[1][0]) / 1000, (c[1][3] - c[1][1]) / 1000
        if min(w, h) < 20:
            assert c[5] == "skip", c
    # a partition inside a no-crossing region is a plan error
    skipped = [c for c in cls.values() if c[5] == "skip"]
    assert skipped, cls
    if skipped:
        r = skipped[0][1]
        p = [((r[0] + r[2]) / 2000.0 - 0.1, (r[1] + r[3]) / 2000.0 - 0.1, (r[0] + r[2]) / 2000.0 + 0.1, (r[1] + r[3]) / 2000.0 + 0.1)]
        try:
            pg_regions.pdn_tcl(die, parts=p)
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "cannot form" in str(e)
        t = pg_regions.pdn_tcl(die, parts=[])
        assert "OT_PG_REGION_SKIP" in t
