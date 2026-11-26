import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_grow as LG  # noqa: E402


def row():
    return {"outline_um": [1000.0, 800.0],
            "hard_cores": [{"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [50.0, 50.0]},
                           {"inst": "b", "origin_um": [400.0, 300.0], "outline_um": [50.0, 50.0]}],
            "ft_slots": [{"name": "ft0", "in_face": "S", "out_face": "E", "in_window_um": [10.0, 90.0], "out_window_um": [10.0, 90.0],
                          "regs_um": [[50.0, 0.0], [60.0, 400.0], [1000.0, 50.0]],
                          "bit_sites_um": [[[50.0, 10.0], [52.0, 10.0]], [[1000.0, 50.0]]]}],
            "buses": [{"name": "x", "face": "N", "window_um": [200.0, 300.0]}],
            "internal_stations": [{"from_um": [120.0, 130.0], "to_um": [420.0, 330.0], "regs_um": [[250.0, 200.0]]}],
            "relay_sites": {"r": [30.0, 40.0], "s": [500.0, 500.0]},
            "clock": {"taps": [{"name": "t", "xy": [300.0, 300.0]}], "landing_contract": {"pins": [{"xy_um": [200.0, 800.0]}]},
                      "edge_clocks": [{"tap_um": [220.0, 790.0]}], "reach_fix_sinks": [[410.0, 310.0]]}}


def test_grow_shifts_cores_keeps_pins():
    g = LG.grow_row(row(), 100.0)
    assert g["outline_um"] == [1100.0, 800.0]
    assert [h["origin_um"] for h in g["hard_cores"]] == [[200.0, 100.0], [500.0, 300.0]]
    f = g["ft_slots"][0]
    assert f["regs_um"] == [[50.0, 0.0], [60.0, 400.0], [1100.0, 50.0]]           # E-face reg follows the face
    assert f["bit_sites_um"][0] == [[50.0, 10.0], [52.0, 10.0]] and f["bit_sites_um"][1] == [[1100.0, 50.0]]
    assert f["in_window_um"] == [10.0, 90.0] and g["buses"][0]["window_um"] == [200.0, 300.0]
    assert g["clock"]["landing_contract"]["pins"][0]["xy_um"] == [200.0, 800.0]
    assert g["clock"]["edge_clocks"][0]["tap_um"] == [220.0, 790.0]
    assert g["clock"]["taps"][0]["xy"] == [400.0, 300.0] and g["clock"]["reach_fix_sinks"] == [[510.0, 310.0]]
    assert g["internal_stations"][0]["regs_um"] == [[350.0, 200.0]]
    assert g["relay_sites"]["r"] == [30.0, 40.0] and g["relay_sites"]["s"] == [600.0, 500.0]


def test_invariants_pass_and_catch():
    r = row()
    g = LG.grow_row(r, 100.0)
    assert LG.check_rows(r, g) == []
    g["ft_slots"][0]["regs_um"].pop()
    assert any("register count" in b or "point set" in b for b in LG.check_rows(r, g))
    h = LG.grow_row(r, 100.0)
    h["outline_um"] = [1050.0, 800.0]
    assert any("INOUTLINE" in b for b in LG.check_rows(r, h))


def test_dy_moves_n_face_and_above_cut():
    g = LG.grow_row(row(), 0.0, 40.0, 250.0)
    assert g["outline_um"] == [1000.0, 840.0]
    assert [h["origin_um"] for h in g["hard_cores"]] == [[100.0, 100.0], [400.0, 340.0]]
    assert g["clock"]["landing_contract"]["pins"][0]["xy_um"] == [200.0, 840.0]
    assert LG.check_rows(row(), g) == []


def test_ft_interior_follows_cores():
    LG.FT_MODE[0] = "ft"
    try:
        g = LG.grow_row(row(), 100.0)
    finally:
        LG.FT_MODE[0] = True
    f = g["ft_slots"][0]
    assert f["regs_um"] == [[50.0, 0.0], [60.0, 400.0], [1100.0, 50.0]]          # x < xcut (100) stays; face points stay
    r = row(); r["ft_slots"][0]["regs_um"][1] = [300.0, 400.0]
    LG.FT_MODE[0] = "ft"
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True
    assert g["ft_slots"][0]["regs_um"][1] == [400.0, 400.0]
    assert g["ft_slots"][0]["in_window_um"] == [10.0, 90.0]


def test_ft_xcut_keeps_street():
    r = row(); r["ft_slots"][0]["regs_um"][1] = [300.0, 400.0]
    LG.FT_MODE[0] = "ft"; LG.FT_XCUT[0] = 350.0
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True; LG.FT_XCUT[0] = 0.0
    assert g["ft_slots"][0]["regs_um"][1] == [300.0, 400.0]


def test_ft_group_moves_whole():
    r = row(); r["ft_slots"][0]["bit_sites_um"][0] = [[300.0, 10.0], [360.0, 10.0]]   # straddles cut 350, centroid 330
    r["ft_slots"][0]["bit_sites_um"].append([[340.0, 200.0], [380.0, 200.0]])        # centroid 360 -> moves whole
    LG.FT_MODE[0] = "ft"; LG.FT_XCUT[0] = 350.0
    try:
        g = LG.grow_row(r, 100.0)
    finally:
        LG.FT_MODE[0] = True; LG.FT_XCUT[0] = 0.0
    b = g["ft_slots"][0]["bit_sites_um"]
    assert b[0] == [[300.0, 10.0], [360.0, 10.0]] and b[2] == [[440.0, 200.0], [480.0, 200.0]]
    assert b[1] == [[1100.0, 50.0]]


def test_raster_truncation_guard():
    r = row(); r["outline_um"] = [1442.88, 800.0]
    assert any("RASTER" in b for b in LG.check_rows(r, LG.grow_row(r, 120.96)))
    assert not any("RASTER" in b for b in LG.check_rows(r, LG.grow_row(r, 125.28)))


def test_ints_kept_and_bits_untouched():
    r = row(); r["relay_depth"] = [{"bits": [0, 31]}]; r["relay_sites"]["r"] = [30, 40]
    g = LG.grow_row(r, 100.0)
    assert g["relay_depth"] == [{"bits": [0, 31]}] and isinstance(g["relay_sites"]["r"][0], int)


def _gx():
    r = row(); r["outline_um"] = [1512.0, 1226.88]
    r["clock"]["tap_mode"] = "grid+explicit"
    r["clock"]["added_taps"] = [{"name": "clk_t16", "xy": [700.0, 300.0]}, {"name": "clk_t17", "xy": [710.0, 300.0]}]
    r["clock"]["taps"] = [{"name": "clk_t3", "xy": [300.0, 300.0]}, {"name": "clk_t17", "xy": [710.0, 300.0]}]
    return r


def test_added_taps_renamed_when_grid_grows():
    r = _gx(); g, mp = LG.rename_added_taps(r, 20)
    assert [a["name"] for a in g["clock"]["added_taps"]] == ["clk_t20", "clk_t21"]
    assert [a["name"] for a in g["clock"]["taps"]] == ["clk_t3", "clk_t21"]      # grid tap kept, reference follows
    assert r["clock"]["added_taps"][0]["name"] == "clk_t16"                       # input untouched
    assert LG.rename_added_taps(g, 20)[1] == {}                                   # idempotent


def test_rename_overlapping_ranges_single_pass():
    g, _ = LG.rename_added_taps(_gx(), 17)                                       # 16->17, 17->18, never 16->17->18
    assert [a["name"] for a in g["clock"]["added_taps"]] == ["clk_t17", "clk_t18"]
    assert [a["name"] for a in g["clock"]["taps"]] == ["clk_t3", "clk_t18"]


def test_mutant_no_rename_keeps_stale_names():
    g = LG.grow_row(_gx(), 185.76)                                               # grow_row alone (the old behaviour)
    assert [a["name"] for a in g["clock"]["added_taps"]] != ["clk_t20", "clk_t21"]


def widen_row_fixture(gap=8.64, with_contents=False):
    r = {"outline_um": [1000.0, 800.0],
         "hard_cores": [{"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [100.0, 50.0]},
                        {"inst": "b", "origin_um": [100.0 + 100.0 + gap, 100.0], "outline_um": [100.0, 50.0]},
                        {"inst": "c", "origin_um": [100.0 + 200.0 + 2 * gap, 100.0], "outline_um": [100.0, 50.0]},
                        {"inst": "far", "origin_um": [700.0, 300.0], "outline_um": [50.0, 50.0]}],
         "ft_slots": [], "buses": [{"name": "x", "face": "N", "window_um": [200.0, 300.0]}],
         "internal_stations": [{"from_um": [150.0, 125.0], "to_um": [420.0, 125.0], "regs_um": [[300.0, 125.0]], "bits": 1104}],
         "clock": {"taps": [{"name": "t", "xy": [600.0, 300.0]}]}}
    if with_contents:
        r["contents"] = [{"inst": "m0", "lef": "x.lef", "origin_um": [500.0, 500.0], "outline_um": [30.0, 20.0]},
                         {"inst": "m1", "lef": "x.lef", "origin_um": [500.0, 520.0 + gap], "outline_um": [30.0, 20.0]}]
        r["internal_stations"].append({"from_um": [510.0, 480.0], "to_um": [510.0, 600.0], "regs_um": [[510.0, 530.0]], "bits": 1104})
    return r


def test_widen_row_widens_every_busy_gap_to_channel_width():
    import adv_seatgap as SG
    r = widen_row_fixture()
    assert len(SG.macro_gap(r)[1]) == 2
    g, rep, ncut = LG.widen_row(r)
    assert ncut == 2 and g["outline_um"][0] == 1000.0 + 2 * 25.92
    assert [h["origin_um"][0] for h in g["hard_cores"]] == [100.0, 208.64 + 25.92, 317.28 + 51.84, 700.0 + 51.84]
    assert SG.macro_gap(g)[1] == []                                  # no sub-9 um busy gap left
    assert g["buses"][0]["window_um"] == [200.0, 300.0]              # pin windows stay
    assert g["internal_stations"][0]["regs_um"] == [[300.0 + 25.92, 125.0]] or g["internal_stations"][0]["regs_um"] == [[300.0 + 51.84, 125.0]] or g["internal_stations"][0]["regs_um"][0][0] > 300.0
    assert LG.check_rows(r, g, cuts=ncut) == []


def test_widen_mutant_unwidened_gap_is_still_flagged_and_cut_count_checked():
    import adv_seatgap as SG
    r = widen_row_fixture()
    g, rep, ncut = LG.widen_row(r)
    assert any("cores moved" in b for b in LG.check_rows(r, g, cuts=1))       # 3 shift groups need cuts >= 2
    assert len(SG.macro_gap(r)[1]) == 2                                          # mutant: the source row is flagged


def test_widen_contents_macros_y_axis():
    import adv_seatgap as SG
    r = widen_row_fixture(6.98, with_contents=True)
    n0 = len(SG.macro_gap(r)[1])
    g, rep, ncut = LG.widen_row(r)
    assert n0 >= 3 and SG.macro_gap(g)[1] == []
    m = {c["inst"]: c["origin_um"] for c in g["contents"]}
    assert m["m1"][1] - (m["m0"][1] + 20.0) >= 28.0 and g["outline_um"][1] > 800.0


def test_widen_leaves_kit_internal_pair_reported():
    r = widen_row_fixture(6.98, with_contents=True)
    for c in r["contents"]:
        c.pop("origin_um")                                              # a macro with no plan origin cannot be moved
    plan, kit = LG.blocked_plan_gaps(r)
    assert all(p[0] == "x" for p in plan)


def test_lattice_up_is_epsilon_safe():
    assert LG._lattice_up(25.76) == 25.92 and LG._lattice_up(25.92) == 25.92 and LG._lattice_up(0.0) == 0.0


def test_widen_steps_last_cut_off_a_raster_truncating_width():
    # 1442.88 + 25.92 = 1468.80 and 1468.8 / 4.32 lands just under 340 in float: the last cut steps until the width rasters (1477.44)
    assert LG.raster_bad(1468.8) and LG.raster_bad(1473.12) and not LG.raster_bad(1477.44)
    t = widen_row_fixture()
    one = [r for r in LG.blocked_plan_gaps(t)[0] if r[0] == "x"]
    t["outline_um"] = [round(1468.8 - sum(LG._lattice_up(r[2] - r[1]) for r in one), 4), t["outline_um"][1]]
    g, rep, ncut = LG.widen_row(t)
    assert not LG.raster_bad(g["outline_um"][0]) and not LG.raster_bad(g["outline_um"][1])
    assert abs(g["outline_um"][0] - 1477.44) < 1e-6 and rep[-1][-1] > rep[0][-1]
    import adv_seatgap as SG
    assert SG.macro_gap(g)[1] == [] and LG.check_rows(t, g, cuts=ncut) == []


def test_widen_face_grows_an_inherited_truncating_width_on_an_uncut_axis():
    t = widen_row_fixture(with_contents=True)
    t["hard_cores"] = [h for h in t["hard_cores"] if h["inst"] == "far"]      # no x gap: only the contents y cut
    t["internal_stations"] = t["internal_stations"][1:]
    t["outline_um"] = [1546.56, 800.0]                                        # c1x_C t8 W: 1546.56 / 4.32 truncates
    t["ft_slots"] = [{"name": "e", "face": "E", "xy": [1546.56, 400.0]}]
    g, rep, ncut = LG.widen_row(t)
    assert abs(g["outline_um"][0] - 1550.88) < 1e-6 and not LG.raster_bad(g["outline_um"][1])
    assert g["hard_cores"][0]["origin_um"] == [700.0, 300.0]                  # no core moved in x
    assert LG.check_rows(t, g, cuts=ncut) == []


def test_widen_x_cut_moves_interior_ft_groups_east_of_the_cut_with_the_cores():
    t = widen_row_fixture()
    # an interior ft column under core c (east of both cuts) and one under core a (west of both): only the first follows
    t["ft_slots"] = [{"name": "ft0", "in_face": "E", "out_face": "S", "in_window_um": [10.0, 20.0], "out_window_um": [5.0, 9.0],
                      "regs_um": [[1000.0, 60.0], [400.0, 60.0], [150.0, 60.0], [150.0, 0.0]],
                      "bit_sites_um": [[[400.0, 60.0], [401.0, 60.0]], [[150.0, 60.0], [151.0, 60.0]]], "width": 2}]
    g, rep, ncut = LG.widen_row(t)
    s = g["ft_slots"][0]
    assert s["regs_um"] == [[1051.84, 60.0], [451.84, 60.0], [150.0, 60.0], [150.0, 0.0]]
    assert s["bit_sites_um"] == [[[451.84, 60.0], [452.84, 60.0]], [[150.0, 60.0], [151.0, 60.0]]]
    assert s["in_window_um"] == [10.0, 20.0] and LG.FT_MODE[0] is True and LG.FT_XCUT[0] == 0.0


def test_shift_in_place_keeps_outline_and_face_points():
    r = row()
    g = LG.shift_row(r, 100.0)
    assert g["outline_um"] == [1000.0, 800.0]
    assert [h["origin_um"] for h in g["hard_cores"]] == [[200.0, 100.0], [500.0, 300.0]]
    f = g["ft_slots"][0]
    assert f["regs_um"][2] == [1000.0, 50.0] and f["bit_sites_um"][1] == [[1000.0, 50.0]]      # E-face point stays on the face
    assert g["clock"]["taps"][0]["xy"] == [400.0, 300.0] and g["internal_stations"][0]["regs_um"] == [[350.0, 200.0]]
    assert LG.check_rows(r, g) == []


def test_shift_refuses_beyond_e_room():
    import pytest
    with pytest.raises(ValueError):
        LG.shift_row(row(), 500.0)                   # cores end at x=450: room = 1000 - 8 - 450 = 542 -> 500 ok, 600 not
        LG.shift_row(row(), 600.0)


def test_shift_mutant_growth_changes_outline():
    g = LG.grow_row(row(), 100.0)
    assert g["outline_um"] == [1100.0, 800.0] and LG.check_rows(row(), g) == []   # grow is NOT shift: outline differs


def test_ve_gap_no_abut_unless_source():
    def mk(gap):
        return {"outline_um": [1000.0, 800.0], "hard_cores": [
            {"inst": "u_lf.u_ve.u_m", "origin_um": [100.0, 100.0], "outline_um": [100.0, 100.0]},
            {"inst": "u_lf.u_ve.u_s", "origin_um": [200.0 + gap, 100.0], "outline_um": [100.0, 100.0]}]}
    a = mk(8.64)
    assert LG.ve_gap_findings(a, mk(8.64)) == []       # source gap kept (pin-aligned offset)
    assert LG.ve_gap_findings(a, mk(0.0))              # abutted at 0: refused
    assert LG.ve_gap_findings(a, mk(28.08)) == []


def test_die_cap_refuses_big_growth(tmp_path):
    import json
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"partition_types": {"ot_s81sl_leaf__t1": row()}}))
    rc = LG.main(["grow", str(p), "--types", "t1", "--dx", "185.76", "--die-cap", "155.52", "--out", str(tmp_path / "o.json")])
    assert rc == 1 and not (tmp_path / "o.json").exists()


def test_shift_clamps_e_band_points_inside_the_outline():
    r = row()
    r["clock"]["taps"].append({"name": "e", "xy": [980.0, 300.0]})         # E-band tap: x + 100 would leave the outline
    g = LG.shift_row(r, 100.0)
    assert g["clock"]["taps"][1]["xy"][0] <= 1000.0 - 8.0 + 1e-9
    assert LG.check_rows(r, g) == []


def test_shift_e_band_compresses_keeps_order_and_distinct_x():
    r = row()
    r["clock"]["taps"].append({"name": "e1", "xy": [970.0, 8.64]})
    r["clock"]["taps"].append({"name": "e2", "xy": [995.0, 8.64]})         # already past W - margin: stays put
    g = LG.shift_row(r, 100.0)
    x1, x2 = g["clock"]["taps"][1]["xy"][0], g["clock"]["taps"][2]["xy"][0]
    assert x1 < x2 and x2 == 995.0 and x1 < 992.0 - 0.5                        # mutant (clamp to W-8): x1 == 992 == pile-up
    assert x2 - x1 > 0.5


def test_pick_grow_dx_skips_raster_truncating_and_respects_min():
    dx = LG.pick_grow_dx(1512.0, 144.06, 155.52)
    assert dx is not None and 144.06 <= dx <= 155.52 and round(dx / 4.32, 6) == round(dx / 4.32) and not LG.raster_bad(1512.0 + dx)
    assert LG.pick_grow_dx(1512.0, 200.0, 155.52) is None                    # mutant: need above the die cap -> none
