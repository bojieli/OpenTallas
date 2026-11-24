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
