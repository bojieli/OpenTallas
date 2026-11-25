"""SITE-IN-MACRO 11-25: core_place.write_type re-sites the explicit bank sites of an internal station with its regs_um
(KV A5t3-A5t6: 22 i_ectl_Q_N_kf bit sites of 8 kv3_pc_v1 types stayed behind and ended on u_kvpc1_f)."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_site_in_macro as AS  # noqa: E402
import core_place as CP  # noqa: E402


def pc_type(core_origin):
    """kv3_pc_v1 shape: kvpc1_f 90.72 x 267.84, station i_ectl_Q_N_kf with 3 registers and a 2-bit bank per stage"""
    return dict(outline_um=[1200.0, 1600.0],
                hard_cores=[dict(inst="kvpc1_f", origin_um=list(core_origin), outline_um=[90.72, 267.84], orient="MX")],
                internal_stations=[dict(conn="bus:i_ectl_Q_N_kf", from_um=[1061.748, 317.79], to_um=[913.99, 777.292],
                                        regs_um=[[967.68, 319.68], [915.84, 522.72], [915.84, 669.6]], bits=1,
                                        bit_site_cell_um=[1.404, 0.27],
                                        bit_sites_um=[[[1060.02, 493.02], [965.304, 539.19]], [[1046.412, 606.15], [868.536, 677.16]],
                                                      [[914.004, 625.59], [833.544, 918.54]]])])


def moved(core_new, regs_new):
    base = pc_type((665.28, 246.24))                      # A5t5: the core elsewhere, sites legal
    assert AS.counts({"partition_types": {"b": base}}) == {}
    t_new = copy.deepcopy(base)
    t_new["hard_cores"][0]["origin_um"] = list(core_new)
    t_new["internal_stations"][0]["regs_um"] = regs_new
    rep = {}
    CP.resite_station_banks(base, t_new, rep)
    return base, t_new, rep


def test_kvpc1_f_banks_follow_the_regs_and_clear_the_macro():
    # A5t6: kvpc1_f at (993.6, 246.24) covers the old bank at (1060.02, 493.02); reg 0 moved 60 um up
    base, t_new, rep = moved((993.6, 246.24), [[967.68, 379.68], [915.84, 522.72], [915.84, 669.6]])
    stale = copy.deepcopy(t_new)
    stale["internal_stations"][0]["bit_sites_um"] = base["internal_stations"][0]["bit_sites_um"]
    assert AS.counts({"partition_types": {"stale": stale}})["stale"]["in_core"] >= 1      # what the stale plan carried
    assert AS.counts({"partition_types": {"t": t_new}}) == {}                            # 0 sites in the macro now
    g = t_new["internal_stations"][0]["bit_sites_um"]
    assert [len(x) for x in g] == [2, 2, 2] and rep["bank_sites_moved"] >= 1 and rep["bank_rows"] == 1
    # the bank of the moved register 0 moved with it by the 60 um shift (x kept, +60 y) unless it had to clear the core
    assert abs(g[0][1][1] - (539.19 + 60.0)) < 17.0
    assert g[2] == base["internal_stations"][0]["bit_sites_um"][2]                       # register 2 did not move: bank untouched


def test_unmoved_station_is_byte_identical():
    base, t_new, rep = moved((665.28, 246.24), copy.deepcopy(pc_type((0, 0)))["internal_stations"][0]["regs_um"])
    assert t_new["internal_stations"][0]["bit_sites_um"] == base["internal_stations"][0]["bit_sites_um"]
    assert rep["bank_sites_moved"] == 0


def test_move_off_blocks_is_opt_in():
    import ft_bit_sites as FB
    slot = dict(name="s", bit_sites_um=[[[9.99, 9.99]]], bit_site_cell_um=[1.404, 0.27])
    box = (0.0, 0.0, 40.0, 40.0)
    blocks = [(5.0, 5.0, 15.0, 15.0)]
    same, n0 = FB.snap_slots([slot], (0.0, 0.0), core_box=box, blocks=blocks)
    assert n0 == 0 and same[0]["bit_sites_um"] == [[[9.99, 9.99]]]                      # legacy: a free grid point on a block stays
    out, n1 = FB.snap_slots([slot], (0.0, 0.0), core_box=box, blocks=blocks, radius_um=43.2, move_off_blocks=True)
    x, y = out[0]["bit_sites_um"][0][0]
    assert n1 == 1 and not (x < 15.0 and 5.0 < x + 1.404 and y < 15.0 and 5.0 < y + 0.27)


def test_fixed_points_only_when_bank_resite_is_off():
    t = dict(outline_um=[500.0, 500.0], hard_cores=[],
             internal_stations=[dict(conn="bus:i_ectl", regs_um=[[100.0, 100.0]], bit_sites_um=[[[300.0, 300.0]]])])
    for on, n in ((True, 0), (False, 1)):
        me = SimpleNamespace(t=t, cfg=dict(bank_resite=on), W=500.0, H=500.0, owner=lambda p, tol=0.0: None)
        CP.TypeModel._fixed_geometry(me)
        assert len(me.FP) == n


def test_legaliser_keeps_whole_footprints_clear_of_ft_relay_and_own_sites():
    import adv_geom_static as G
    base, t_new, rep = moved((993.6, 246.24), [[967.68, 379.68], [915.84, 522.72], [915.84, 669.6]])
    # ft sites and a relay flop right where the cleared bank wants to land (just below the 2.16 um core halo), one column apart
    ft = [[1060.02, 240.0 + 0.27 * k] for k in range(0, 3)]
    t_new["ft_slots"] = [dict(name="ft0", width=3, stations=1, bit_site_cell_um=[1.404, 0.27], bit_sites_um=[[list(p) for p in ft]])]
    t_new["relay_sites"] = {"r0": [1062.0, 240.0]}
    base2 = copy.deepcopy(t_new)
    for e in base2["internal_stations"]:
        e["regs_um"] = copy.deepcopy(base["internal_stations"][0]["regs_um"])
    rep = {}
    CP.resite_station_banks(base2, t_new, rep)
    ss = G.bit_sites(t_new)
    assert G.site_collisions(ss, (0.0, 0.0)) == []                                  # ADV-BITSITE-AREA: 0 colliding footprints
    assert AS.counts({"partition_types": {"t": t_new}}) == {}
