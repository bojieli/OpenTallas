"""S81-COLGEN-1 11-14: lane_pad_route (FABLE-TYPES-S81-COL C4) -- lane pad stages follow a wall-avoiding route, hops <= limit."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_pad_route as L


def core(inst, x, y, w, h, mod="ot_v41_bf_col3_c"):
    return dict(inst=inst, module=mod, origin_um=[x, y], outline_um=[w, h])


def ptype():
    """1400 x 900 die; a wall x 400-800, y 52-250 above a 52-um strip (the C4 shape); a rom macro in the way north of it"""
    return dict(outline_um=[1400, 900],
                hard_cores=[core("u_wall", 400, 52, 400, 198), core("u_rom", 900, 300, 100, 100, "ot_rom")],
                internal_stations=[dict(conn="bus:b", from_um=[100, 0], to_um=[1300, 90], launch="face flop", capture="x",
                                        regs_um=[[300, 0], [500, 0], [700, 0], [900, 0], [1250, 0]])])


def test_walls_grow_to_the_edge_through_the_strip():
    (raw, g), = L.walls(ptype())
    assert raw == (400, 52, 800, 250)
    assert g[1] == -1.0 and g[0] == 350 and g[2] == 850 and g[3] == 300        # strip (52 < 100) belongs to the wall


def test_route_leaves_the_strip_and_avoids_the_wall():
    t = ptype()
    poly = L.route(t, [100, 0], [1300, 90])
    assert poly[0] == [100, 0] and poly[-1] == [1300, 90]
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        assert ax == bx or ay == by
        assert not (L._seg_overlap((ax, ay), (bx, by), (350.0, 52.0, 850.0, 250.0)) > 0)     # never through the wall


def test_route_goes_north_when_the_strip_is_the_only_short_way():
    t = ptype()
    poly = L.route(t, [100, 0], [1300, 90])
    assert max(p[1] for p in poly) >= 300 or max(p[0] for p in poly[:3]) < 351      # north of the wall zone, or strip only west of it
    assert not any(p[1] == 0 and p[0] > 351 for p in poly[:-1])                     # no strip travel under the wall


def test_sites_hops_and_no_site_in_wall_zone():
    t = ptype()
    r = L.plan_entry(t, t["internal_stations"][0])
    assert r["max_hop_um"] <= 400 and r["stages_after"] >= 5
    zone = L.walls(t)[0][1]
    assert not any(L._inside(p, zone, eps=-1e-6) for p in r["regs_um"])
    rom = (899, 299, 1001, 401)
    assert not any(L._inside(p, rom, eps=-1e-6) for p in r["regs_um"])
    assert max(L.hops([100, 0], r["regs_um"], [1300, 90])) <= 400


def test_stage_count_grows_only_when_needed():
    t = ptype()
    e = t["internal_stations"][0]
    e["regs_um"] = e["regs_um"][:2]                                           # 2 stages cannot cover the route in hops <= 400
    r = L.plan_entry(t, e)
    assert r["stages_after"] > 2 and r["cycles_added"] == r["stages_after"] - 2 and r["max_hop_um"] <= 400


def test_needs_fix_flags_strip_stage_and_long_hop():
    t = ptype()
    assert L.needs_fix(t, t["internal_stations"][0])                          # stages at y 0 under the wall zone
    ok = dict(t["internal_stations"][0], regs_um=[[400, 305], [700, 320], [900, 305], [1100, 305], [1250, 330]])
    ok["from_um"], ok["to_um"] = [350, 320], [1300, 400]
    assert not L.needs_fix(t, ok)
    assert L.needs_fix(t, dict(ok, to_um=[1300, 900]))                        # a 600+ hop


def test_run_apply_edits_only_regs_and_note_and_is_idempotent():
    plan = {"partition_types": {"T": ptype(), "U": ptype()}}
    before = copy.deepcopy(plan["partition_types"]["U"])
    res = L.run_many(plan, "^T$", ["b"], apply=True)
    e = plan["partition_types"]["T"]["internal_stations"][0]
    assert e["regs_um"] == res["types"][0]["entries"][0]["regs_um"] and "S81-COLGEN-1" in e["note"]
    assert e["from_um"] == [100, 0] and e["to_um"] == [1300, 90]
    assert plan["partition_types"]["U"] == before                              # other types untouched
    again = L.run_many(plan, "^T$", ["b"], apply=False)
    assert not L.needs_fix(plan["partition_types"]["T"], e) and again["types"][0]["entries"][0]["max_hop_um"] <= 400


def test_all_mode_reports_unroutable_instead_of_failing():
    t = ptype()
    t["hard_cores"].append(core("u_w2", 600, 0, 100, 900))                   # a second wall across the whole die height
    plan = {"partition_types": {"T": t}}
    r = L.run(plan, "T", every=True)
    assert r["entries"] == [] and r["errors"] and "no wall-avoiding route" in r["errors"][0]["error"]
    with pytest.raises(L.RouteError):
        L.run(plan, "T", ["b"])


def test_missing_bus_is_an_error():
    with pytest.raises(L.RouteError, match="no internal_stations entry"):
        L.run({"partition_types": {"T": ptype()}}, "T", ["nope"])


def test_tap_group_one_group_per_lane_pad_pipeline():
    import re
    plan = {"partition_types": {"A": ptype(), "B": dict(ptype(), clock={"tap_group": {"re": "(x)"}}), "C": ptype()}}
    r = L.lane_pad_tap_group(plan, "^[AB]$")
    assert r["set"] == ["A"] and r["conflict"] == ["B"] and plan["partition_types"]["C"].get("clock") is None
    rx = plan["partition_types"]["A"]["clock"]["tap_group"]["re"]
    assert "(" in rx and not any(c in rx for c in "#$ \t\n")            # gen_phys.tap_group_exports rules
    names = [f"u_bound.u_lpad_frame_int_i1.r\\[{k}\\]\\[{b}\\]$_DFF_P_" for k in range(5) for b in (0, 476, 1264)]
    assert {re.search(rx, n).group(1) for n in names} == {"u_lpad_frame_int_i1"}      # every rank + bit: one key
    assert re.search(rx, "u_bound.u_lpad_frame_int_i0.r[0][1]").group(1) == "u_lpad_frame_int_i0"
    assert not re.search(rx, "u_bound.u_pd7_frame_int_i1_5")
    assert L.lane_pad_tap_group(plan, "^A$")["unchanged"] == ["A"]
    only = L.lane_pad_tap_group({"partition_types": {"A": ptype()}}, "^A$", ["frame_int_i1"])
    assert only["re"].count("frame_int_i1") == 1 and "u_lpad_(?:frame_int_i1)" in only["re"]
