"""ADV-BITSITE-AREA (COORD 11-24): ft / station / landing bank bit sites off the core or outline, and collisions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import ft_bit_sites as FB  # noqa: E402
import plan_advisory as PA  # noqa: E402

CELL = [1.404, 0.27]


def ptype(ft, ist=(), banks=()):
    t = {"outline_um": [100.0, 100.0], "ft_slots": [{"name": "ft0", "width": 1, "stations": 2, "bit_sites_um": ft,
                                                     "bit_site_cell_um": CELL}]}
    if ist:
        t["internal_stations"] = [{"conn": "c0", "bit_sites_um": [list(ist)], "bit_site_cell_um": CELL}]
    if banks:
        t["clock"] = {"soft_reg_banks": [{"id": "cs0", "bit_sites_um": list(banks), "bit_site_cell_um": CELL}]}
    return t


def test_clean_type_is_silent():
    t = ptype([[[10.0, 10.0], [20.0, 10.0]]], ist=[[30.0, 10.0]], banks=[[40.0, 10.0]])
    assert G.bitsite_area({"partition_types": {"a": t}}, "p") == []


def test_off_core_off_outline_and_collisions():
    t = ptype([[[10.0, 10.0], [10.54, 10.0]]],            # 0.54 um apart, 1.404 wide: collide
              ist=[[1.0, 50.0]],                          # inside the outline, off the 4.32 core inset
              banks=[[99.5, 50.0], [20.0, 10.0]])         # off the outline (right edge) ; clean
    out = G.bitsite_area({"partition_types": {"leaf_t7": t}}, "p")
    w = out[0]
    assert w.startswith("WARN ADV-BITSITE-AREA leaf_t7: 5 bit sites: 2 off CORE_AREA") and "(1 off the outline" in w
    assert "1 colliding footprint(s) (e.g. ft_slots[ft0],0,0 x ft_slots[ft0],0,1)" in w
    assert out[-1].startswith("LIST ADV-BITSITE-AREA 1 type(s): 2 off-core (1 off-outline), 1 colliding, of 5 bit sites")
    assert "ist 1" in out[-1] and "land 1" in out[-1]


def test_collisions_agree_with_ft_bit_sites_census():
    stage = [[10.0 + 0.054 * i, 10.0 + 0.084 * (i % 3)] for i in range(13)]    # QC su_c y-compression form
    t = ptype([stage])
    org = G.core_area(t)[:2]
    ref = FB.footprint_conflicts(t["ft_slots"], org)
    got = G.site_collisions(G.bit_sites(t), tuple(org))
    assert len(got) == len(ref) > 0


def test_registered_in_plan_advisory():
    assert ("BITSITE-AREA", "adv_bitsite_area") in PA.CHECKS
    import adv_bitsite_area
    assert adv_bitsite_area.findings is G.bitsite_area
