"""rigid_refloor.py (S81-T2-REFLOOR 11-23): rigid moves, re-shape, seam re-site, packing, channels, layout findings."""
import copy

import pytest

import rigid_refloor as RR


def _plan():
    """three columns of one row on an 8.64 grid: A | B (abutted)  and  C over B; a channel 86.4 wide between A and D."""
    t = lambda w, h, **k: dict(outline_um=[w, h], buses=k.pop("buses", []), **k)  # noqa: E731
    types = {
        "ta": t(864.0, 864.0, buses=[dict(name="o0", dir="out", face="E", width=8, layers=["M6", "M4"],
                                          window_um=[100.0, 120.0])]),
        "tb": t(864.0, 864.0, buses=[dict(name="i0", dir="in", face="W", width=8, layers=["M6", "M4"],
                                          window_um=[100.0, 120.0])]),
        "tc": t(864.0, 864.0),
        "td": t(864.0, 864.0),
        "ts": t(864.0, 864.0, ft_slots=[
            dict(name="ft0", in_face="W", out_face="E", in_window_um=[500.0, 560.0], out_window_um=[500.0, 560.0],
                 width=8, layers=["M6", "M4"], stations=3, regs_um=[[0, 530], [432, 530], [864, 530]],
                 bit_sites_um=[[[1.0, 2.0]] * 9], bit_site_cell_um=[1.404, 0.27]),
            dict(name="ft1", in_face="W", out_face="E", in_window_um=[600.0, 660.0], out_window_um=[600.0, 660.0],
                 width=8, layers=["M6", "M4"], stations=3)]),
        "tt": t(864.0, 864.0, ft_slots=[
            dict(name="ft0", in_face="W", out_face="E", in_window_um=[500.0, 560.0], out_window_um=[500.0, 560.0],
                 width=8, layers=["M6", "M4"], stations=3),
            dict(name="ft1", in_face="W", out_face="E", in_window_um=[600.0, 660.0], out_window_um=[600.0, 660.0],
                 width=8, layers=["M6", "M4"], stations=3)]),
    }
    parts = [dict(name="A", type="ta", origin_um=[0.0, 0.0]), dict(name="B", type="tb", origin_um=[864.0, 0.0]),
             dict(name="C", type="tc", origin_um=[864.0, 864.0]), dict(name="D", type="td", origin_um=[1814.4, 0.0]),
             dict(name="S1", type="ts", origin_um=[0.0, 1728.0]), dict(name="S2", type="tt", origin_um=[864.0, 1728.0])]
    ports = [dict(id="p_ab", src=dict(part="A", bus="o0"), dst=dict(part="B", bus="i0"), kind="data", width=8),
             dict(id="p_bd", src=dict(part="B", bus="x"), dst=dict(part="D", bus="y"), kind="data", width=8,
                  face="E", layers=["M6", "M4"], window_um=[200.0, 220.0]),
             dict(id="p_s0", src=dict(part="S1", bus="ft0_o"), dst=dict(part="S2", bus="ft0_i"), kind="data", width=8,
                  face="E", layers=["M6", "M4"], window_um=[2228.0, 2288.0]),
             dict(id="p_s1", src=dict(part="S1", bus="ft1_o"), dst=dict(part="S2", bus="ft1_i"), kind="data", width=8,
                  face="E", layers=["M6", "M4"], window_um=[2328.0, 2388.0])]
    die = dict(name="t", outline_um=[4320.0, 4320.0], reach_um=405.0, grid_um=8.64,
               channels=[dict(between=["B", "D"], name="ch_bd", ports=["p_bd"], layers=["M6", "M4"],
                              rect_um=[1728.0, 0.0, 1814.4, 864.0], width_um=86.4)])
    return dict(die=die, partition_types=types, partitions=parts, ports=ports, lanes=[])


def _spec(parts, **k):
    return dict(schema=RR.SCHEMA, parts=parts, **k)


def test_rigid_pair_moves_window_and_no_repin():
    raw = _plan()
    new, rep = RR.apply(raw, _spec({"A": {"delta_um": [0, 8.64 * 300]}, "B": {"delta_um": [0, 8.64 * 300]},
                                    "C": {"delta_um": [0, 8.64 * 300]}, "S1": {"delta_um": [0, 8.64 * 300]},
                                    "S2": {"delta_um": [0, 8.64 * 300]}}))
    st = {r["id"]: r["status"] for r in rep["port_rows"]}
    assert st["p_ab"] == "RIGID" and st["p_s0"] == "RIGID"
    assert "ta" not in rep["repin_types"] and "tb" not in rep["repin_types"]
    assert raw["partitions"][0]["origin_um"] == [0.0, 0.0]          # input untouched
    assert {p["name"]: p["origin_um"] for p in new["partitions"]}["A"] == [0.0, 2592.0]


def test_one_end_moves_keeps_costlier_frame_and_reports_repin():
    raw = _plan()
    raw["partition_types"]["tb"]["hard_cores"] = [dict(inst="h0")]   # B is the heavier type: its pins stay
    new, rep = RR.apply(raw, _spec({"A": {"delta_um": [0, 86.4]}}))
    row = next(r for r in rep["port_rows"] if r["id"] == "p_ab")
    assert row["status"] == "KEEP-B" and row["new"] == [100.0, 120.0]
    assert list(rep["repin_types"]) == ["ta"]
    assert new["partition_types"]["ta"]["buses"][0]["window_um"] == [13.6, 33.6]
    assert new["partition_types"]["tb"]["buses"][0]["window_um"] == [100.0, 120.0]


def test_reshape_slides_on_grid_packs_and_rebuilds_slots():
    raw = _plan()
    raw["partition_types"]["ts"]["clock"] = dict(tap_mode="explicit", taps=[dict(name="clk", xy=[432.0, 800.0])],
                                                 band_fixed_um=dict(ft0_o=dict(rect_um=[820.0, 500.0, 860.0, 560.0])))
    raw["partition_types"]["ts"]["reset"] = dict(local_taps_um=[[432.0, 860.0]])
    y0 = 1728.0 + 8.64 * 75             # both stations lose their bottom 648 um: chain at 500-660 must re-site
    new, rep = RR.apply(raw, _spec({"S1": {"rect_um": [0.0, y0, 864.0, 2592.0]},
                                    "S2": {"rect_um": [864.0, y0, 1728.0, 2592.0]}},
                                   remap_internal=["S1", "S2"]))
    rows = {r["id"]: r for r in rep["port_rows"]}
    a, b = rows["p_s0"]["new"], rows["p_s1"]["new"]
    assert rows["p_s0"]["status"] == "SLIDE" and a[0] >= y0 and b[1] <= 2592.0 and a[1] < b[0]
    for r in (rows["p_s0"], rows["p_s1"]):
        d = r["new"][0] - r["old"][0]
        assert abs(d / 8.64 - round(d / 8.64)) < 1e-6           # whole grid steps keep the pin tracks
    s = new["partition_types"]["ts"]
    assert s["outline_um"] == [864.0, 864.0 - 648.0]
    ft0 = s["ft_slots"][0]
    assert "bit_sites_um" not in ft0 and len(ft0["regs_um"]) == 3
    assert all(0 <= p[1] <= 216.0 for p in ft0["regs_um"])
    assert ft0["out_window_um"] == [round(a[0] - y0, 6), round(a[1] - y0, 6)]
    assert 0 <= ft0["in_window_um"][0] and ft0["in_window_um"][1] <= 216.0      # portless end clamped onto its face
    assert "ts.ft0.in_window_um" in rep["windows_clamped"]
    assert s["clock"]["band_fixed_um"]["ft0_o"]["rect_um"] == [820.0, ft0["out_window_um"][0], 860.0,
                                                             ft0["out_window_um"][1]]
    assert s["clock"]["taps"][0] == dict(name="clk", xy=[432.0, 200.0])          # explicit taps: scaled, not renamed
    assert s["reset"]["local_taps_um"] == [[432.0, round(216.0 - 4.33, 6)]]      # scaled, then held off the edge
    # both stations hold the same frame window for the shared seam
    assert new["partition_types"]["tt"]["ft_slots"][0]["in_window_um"] == ft0["out_window_um"]


def test_channel_closes_when_gap_goes_to_zero_and_overlap_found():
    raw = _plan()
    new, rep = RR.apply(raw, _spec({"D": {"delta_um": [-86.4, 0]}}))
    assert [c["name"] for c in rep["channels"]["closed"]] == ["ch_bd"]
    assert all(c.get("name") != "ch_bd" for c in new["die"]["channels"])
    _, rep2 = RR.apply(raw, _spec({"D": {"delta_um": [-172.8, 0]}}))
    assert any(f.startswith("OVERLAP D") for f in rep2["layout_findings"])


def test_shared_type_reshape_refused():
    raw = _plan()
    raw["partitions"].append(dict(name="A2", type="ta", origin_um=[0.0, 3456.0]))
    with pytest.raises(ValueError, match="shared"):
        RR.new_layout(raw, _spec({"A": {"rect_um": [0.0, 0.0, 432.0, 864.0]}}))


def test_landing_relays_follow_rigid_pair_and_drop_when_split():
    raw = _plan()
    raw["clock"] = dict(landing_network=dict(edges=[
        dict(id="m1", src=dict(part="A", bus="a"), dst=dict(part="B", bus="b"), relays=[dict(id="r", xy_um=[900, 50])]),
        dict(id="m2", src=dict(part="A", bus="a"), dst=dict(part="C", bus="b"), relays=[dict(id="r", xy_um=[900, 50])])]))
    new, rep = RR.apply(raw, _spec({"A": {"delta_um": [0, 8.64]}, "B": {"delta_um": [0, 8.64]}}))
    e = {x["id"]: x for x in new["clock"]["landing_network"]["edges"]}
    assert e["m1"]["relays"][0]["xy_um"] == [900, 58.64] and "relays" not in e["m2"]
    assert rep["landing_relays"] == dict(translated=["m1"], dropped=["m2"])


def test_frame_conversions_are_inverse_for_all_orients():
    r = (100.0, 200.0, 964.0, 1064.0)
    for o in ("R0", "MX", "MY", "R180"):
        for f in "NSEW":
            w = [300.0, 340.0]
            assert RR.from_frame(r, o, f, RR.to_frame(r, o, f, copy.copy(w))) == w


def test_grid_explicit_added_taps_renumbered_after_regrid():
    raw = _plan()
    raw["budgets"] = dict(tap_pitch_um=432.0)
    t = raw["partition_types"]["tc"]
    t["clock"] = dict(tap_mode="grid+explicit", added_taps=[dict(name="clk_t4", xy=[10.0, 10.0])],
                      landing=dict(src="clk_t4", other="clk_t3"))
    raw["clock"] = dict(tap_window=dict(per_port_ps=dict(tc={"clk": 10, "clk_t3": 20, "clk_t4": 30})))
    new, rep = RR.apply(raw, _spec({"C": {"rect_um": [864.0, 864.0, 864.0 + 1296.0, 1728.0]}}))
    c = new["partition_types"]["tc"]["clock"]
    assert c["added_taps"][0]["name"] == "clk_t6" and c["landing"]["src"] == "clk_t6"   # grid 2x2 -> 3x2
    assert c["landing"]["other"] in ("clk_t4", "clk_t5")                               # nearest new grid tap
    assert new["clock"]["tap_window"]["per_port_ps"]["tc"]["clk_t6"] == 30


def test_grid_explicit_expansion_resolves_colliding_nearest_grid_taps():
    old = {"t": dict(outline_um=[864.0, 864.0], clock=dict(
        tap_mode="grid+explicit", added_taps=[dict(name="clk_t4", xy=[10.0, 10.0])]))}
    new = copy.deepcopy(old)
    new["t"]["outline_um"] = [1296.0, 864.0]
    ren = RR.tap_renames(old, new, dict(partition_types=new, budgets=dict(tap_pitch_um=432.0)),
                        "t", (864.0, 0.0))
    assert ren["clk_t4"] == "clk_t6"
    before = ["clk", "clk_t1", "clk_t2", "clk_t3"]
    assert len({ren.get(name, name) for name in before}) == len(before)


def _lane_plan():
    """SRC | S1 | channel 172.8 | S2 | DST in one row; one lane SRC.o0 -> S1.ft0 -> S2.ft0 -> DST.i0 at y 400-420."""
    ft = lambda: [dict(name="ft0", in_face="W", out_face="E", in_window_um=[400.0, 420.0],  # noqa: E731
                       out_window_um=[400.0, 420.0], width=8, layers=["M6", "M4"], stations=4,
                       regs_um=[[0.0, 410.0], [216.0, 410.0], [432.0, 410.0], [648.0, 410.0]])]
    types = {"tsrc": dict(outline_um=[864.0, 864.0], buses=[dict(name="o0", dir="out", face="E", width=8,
                                                                 layers=["M6", "M4"], window_um=[400.0, 420.0])]),
             "tdst": dict(outline_um=[864.0, 864.0], buses=[dict(name="i0", dir="in", face="W", width=8,
                                                                 layers=["M6", "M4"], window_um=[400.0, 420.0])]),
             "t1": dict(outline_um=[864.0, 864.0], buses=[], ft_slots=ft()),
             "t2": dict(outline_um=[864.0, 864.0], buses=[], ft_slots=ft())}
    parts = [dict(name="SRC", type="tsrc", origin_um=[0.0, 0.0]), dict(name="S1", type="t1", origin_um=[864.0, 0.0]),
             dict(name="S2", type="t2", origin_um=[1900.8, 0.0]), dict(name="DST", type="tdst", origin_um=[2764.8, 0.0])]
    port = lambda i, s, sb, d, db: dict(id=i, src=dict(part=s, bus=sb), dst=dict(part=d, bus=db), kind="data",  # noqa
                                        width=8, face="E", layers=["M6", "M4"], window_um=[400.0, 420.0])
    ports = [port("p0", "SRC", "o0", "S1", "ft0_i"), port("p1", "S1", "ft0_o", "S2", "ft0_i"),
             port("p2", "S2", "ft0_o", "DST", "i0")]
    die = dict(name="t", outline_um=[8640.0, 4320.0], reach_um=405.0, grid_um=8.64,
               channels=[dict(between=["S1", "S2"], name="ch12", ports=["p1"], layers=["M6", "M4"],
                              rect_um=[1728.0, 0.0, 1900.8, 864.0], width_um=172.8)])
    return dict(die=die, partition_types=types, partitions=parts, ports=ports,
                lanes=[dict(id="ln", ports=["p0", "p1", "p2"])])


def test_reshape_refits_broken_lane_and_only_adds_stations():
    import check as C
    import schema as S
    raw = _lane_plan()
    P0 = S.Plan(raw)
    assert max(C.lane_pin_hops(P0, "ln", C.lane_geometry(P0, "ln")[1])) <= 405.0
    grow = 8.64 * 150                                  # S1 grows 1296 um east; S2 and DST ride along
    new, rep = RR.apply(raw, _spec({"S1": {"rect_um": [864.0, 0.0, 1728.0 + grow, 864.0]},
                                    "S2": {"delta_um": [grow, 0.0]}, "DST": {"delta_um": [grow, 0.0]}},
                                   keep_internal=["S1"]))
    P1 = S.Plan(new)
    hops = C.lane_pin_hops(P1, "ln", C.lane_geometry(P1, "ln")[1])
    assert max(hops) <= 405.0
    fit = rep["free_slots_fit"]
    assert fit["stations"]["t1.ft0"][0] == 4 and fit["stations"]["t1.ft0"][1] > 4 and not fit["unfixable_leads"]
    s1 = new["partition_types"]["t1"]["ft_slots"][0]
    assert s1["stations"] == len(s1["regs_um"]) and all(0 < p[0] < 864.0 + grow for p in s1["regs_um"])


def test_stale_die_relays_dropped_when_wavefront_parent_changes(monkeypatch):
    import reset_tree as RT
    raw = _plan()
    raw["reset"] = dict(die_relays={"B": dict(parent="A", site=3, sites_um=[[900.0, 10.0]]),
                                    "D": dict(parent="C", site=1, sites_um=[[1800.0, 10.0]])})
    monkeypatch.setattr(RT, "wf_solve", lambda P: dict(parent={"B": ("A", 3, 0.0), "D": ("B", 0, 0.0)}))
    out = RR.drop_stale_die_relays(raw)
    assert out == {"D": ["C", 1, "B", 0]} and list(raw["reset"]["die_relays"]) == ["B"]


def test_pack_treats_kept_windows_as_obstacles():
    class _P:
        ports = {"k": dict(src=dict(part="A"), dst=dict(part="B")), "m": dict(src=dict(part="A"), dst=dict(part="B"))}
    rows = [dict(id="k", ends=["A", "B"], face="E", status="KEEP-A", old=[0.0, 100.0], new=[10.0, 110.0],
                 lo=0.0, hi=300.0),
            dict(id="m", ends=["A", "B"], face="E", status="SLIDE", old=[120.0, 220.0], new=[20.0, 120.0],
                 lo=0.0, hi=300.0)]
    RR._pack(rows, _P(), 1.2)
    assert rows[1]["status"] == "SLIDE" and rows[1]["new"][0] >= 111.2      # stepped over the kept window
    rows[1].update(status="SLIDE", new=[20.0, 120.0], hi=200.0)
    rows[0]["hi"] = 200.0
    RR._pack(rows, _P(), 1.2)
    assert rows[1]["status"] == "NO-ROOM"                                     # no room left beside it


def test_move_and_grow_keeps_internals_inside_only_with_ride_internal():
    raw = _plan()
    raw["partition_types"]["tc"]["hard_cores"] = [dict(inst="h", origin_um=[700.0, 10.0], outline_um=[160.0, 100.0])]
    sp = {"C": {"rect_um": [864.0 - 172.8, 864.0, 1728.0 - 172.8, 1900.8]}}
    _, bad = RR.apply(raw, _spec(sp))
    assert "tc" in bad["content_outside"]                           # die position kept: the core leaves the outline
    new, ok = RR.apply(raw, _spec(sp, ride_internal=["C"]))
    assert ok["content_outside"] == {} and new["partition_types"]["tc"]["hard_cores"][0]["origin_um"] == [700.0, 10.0]


def test_new_hop_over_limit_is_reported():
    raw = _lane_plan()
    worse = copy.deepcopy(raw)
    worse["partition_types"]["t1"]["ft_slots"][0]["regs_um"] = [[0.0, 410.0]]
    worse["partition_types"]["t1"]["ft_slots"][0]["stations"] = 1
    assert RR.new_hop_overs(raw, raw, 405.0) == {} and "ln" in RR.new_hop_overs(raw, worse, 405.0)


def test_relayer_shrinks_both_ends_and_refuses_a_slot_end():
    raw = _lane_plan()
    raw["ports"].append(dict(id="pb", src=dict(part="SRC", bus="o0"), dst=dict(part="DST", bus="i0"), kind="data",
                             width=8, face="E", layers=["M6", "M4"], window_um=[400.0, 420.0]))
    rows = RR.relayer(raw, {"pb": ["M6", "M4", "M8"]})
    assert rows["pb"]["new"] == [400.0, round(400.0 + 20.0 * 2 / 3, 6)]
    b = raw["partition_types"]["tsrc"]["buses"][0]
    assert b["layers"] == ["M6", "M4", "M8"] and abs(b["window_um"][1] - b["window_um"][0] - 40.0 / 3) < 1e-5
    with pytest.raises(ValueError):
        RR.relayer(_lane_plan(), {"p1": ["M6", "M4", "M8"]})        # ft slot ends
    with pytest.raises(ValueError):
        RR.relayer(_lane_plan(), {"p0": ["M6"]})                    # not an increase


def test_dodge_cores_leaves_abutted_cores_on_one_axis():
    t = dict(outline_um=[864.0, 864.0], hard_cores=[
        dict(inst="a", origin_um=[100.0, 100.0], outline_um=[200.0, 200.0]),
        dict(inst="b", origin_um=[100.0, 300.0], outline_um=[200.0, 200.0])])
    (x, y), = RR.dodge_cores(t, [[290.0, 310.0]])
    assert not (100.0 < x < 300.0 and 100.0 < y < 500.0) and (x == 290.0 or y == 310.0)


def test_relayer_refuses_follow_pin_layers():
    with pytest.raises(ValueError):
        RR.relayer(_lane_plan(), {"p0": ["M6", "M4", "M2"]})


def test_two_kept_windows_from_different_frames_do_not_overlap():
    raw = _lane_plan()
    raw["ports"] += [
        dict(id="pa", src=dict(part="SRC", bus="o0"), dst=dict(part="S1", bus="xa"), kind="data", width=8, face="E",
             layers=["M6", "M4"], window_um=[600.0, 620.0]),
        dict(id="pb", src=dict(part="SRC", bus="o0"), dst=dict(part="S1", bus="xb"), kind="data", width=8, face="E",
             layers=["M6", "M4"], window_um=[621.2, 641.2])]
    rows = [dict(id="pa", face="E", ends=["SRC", "S1"], old=[600.0, 620.0], new=[600.0, 620.0], status="KEEP-S1",
                 lo=0.0, hi=864.0),
            dict(id="pb", face="E", ends=["SRC", "S1"], old=[621.2, 641.2], new=[610.0, 630.0], status="KEEP-SRC",
                 lo=0.0, hi=864.0)]
    import schema as S
    RR._pack(rows, S.Plan(raw), 1.2)
    (a0, a1), (b0, b1) = sorted(r["new"] for r in rows)
    assert b0 >= a1 + 1.1 and rows[1]["status"] == "SLIDE"


def test_tap_renames_never_give_two_taps_one_name():
    old = {"t": dict(outline_um=[1440.0, 1440.0], clock=dict(tap_mode="grid", taps=[
        dict(name="clk", xy=[1.0, 1.0]), dict(name="clk_t1", xy=[2.0, 2.0])]))}
    new = {"t": dict(outline_um=[400.0, 400.0], clock=dict(tap_mode="grid", taps=[
        dict(name="clk", xy=[1.0, 1.0]), dict(name="clk_t1", xy=[2.0, 2.0])]))}
    assert RR.tap_renames(old, new, dict(partition_types=new), "t", (0.0, 0.0)) == {}
