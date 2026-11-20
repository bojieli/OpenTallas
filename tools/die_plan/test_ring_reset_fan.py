"""RING-RSTFAN-1 (HEAD-CROSSING-1119, FABLE-PD-HEAD-2040 D3): the ring reset relay u_cland_rst_<bus> keeps its loads
within REACH_UM (405 um).

HEAD hd_serdes r8b a2 place: u_cland_rst_coll_i0/q drove 28 loads over 554.6 um (bbox x 1470.7..1977.8): the ring band
(x 1824.88..2030.08, 19 RSTREP reader-START copies) plus the count origin, whose p_start pin cland_tstart_in sits at
(1452.0, 77.728), ~470 um from the band.  The generator now gives the far load group a kept same-D copy
u_cland_rfan_<bus>_<k> (same depth = same release edge, 0 cycles); loads within reach keep byte-identical RTL.
    python3 -m pytest -q tools/die_plan/test_ring_reset_fan.py"""
import re

import count_align_bind as CAB
import clock_landings as CL
from clock_landings import Landings
from test_clock_landings import B_BODY
from test_count_straps import strap_vehicle

W, H = 2885.76, 1226.88                                   # hd_serdes outline
BAND = [1824.88, 17.28, 2030.08, 62.64]                   # coll_i0 landing band (r11 plan)
TAP19 = [1923.2, 31.1]                                    # tap 19: u_rrl_61 / u_cland_rst_coll_i0 site
ORIGIN = [1447.68, 73.44, 1456.32, 82.08]                 # origin home around cland_tstart_in (1452.0, 77.728)


def hd_serdes_vehicle(far_origin=True):
    """the strap vehicle's type B shaped as hd_serdes coll_i0: 513-bit ring (W 515 + status = ring 576), band, tap 19"""
    p, t = strap_vehicle()
    for x in p["ports"] + t["ports"]:
        x["width"] = 513
    B = p["partition_types"]["B"]
    B["outline_um"] = [W, H]
    org = {"b": 10.0, "c": 3000.0}
    for q in p["partitions"]:
        if q["name"] in org:
            q["origin_um"] = [org[q["name"]], 0]
    for r in t["regions"]:
        if r["tag"] in ("r1", "r2"):
            x0 = org["b" if r["tag"] == "r1" else "c"]
            r["box_um"] = [x0, 0, x0 + W, H]
    for b in B["buses"]:
        b["face"], b["window_um"] = "S", [BAND[0], BAND[2]]
    ck = B.setdefault("clock", {})
    ck["landing_contract"] = dict(bands=dict(y=dict(ring_width=576, rect_um=list(BAND))))
    ck["taps"] = [dict(name="clk", xy=list(TAP19))]
    if far_origin:
        ck["landing_origin_rect_um"] = list(ORIGIN)
    return p, t, B_BODY.replace("[4:0] y", "[513:0] y")


def loads_of(rtl, net):
    """instances whose reset pin (or an alias of net) takes net"""
    out = set(re.findall(r"\b(u_\w+)\s*\([^;]*?\.(?:rst_n|rst_raw_n)\(\s*" + re.escape(net) + r"\s*\)", rtl, re.S))
    for a in re.findall(r"assign\s+(\w+)\s*=\s*" + re.escape(net) + r"\s*;", rtl):
        out.add("assign:" + a)
    return out


def test_hd_serdes_coll_i0_far_origin_gets_same_cycle_copy():
    p, t, body = hd_serdes_vehicle()
    k0 = CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"]
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", body)
    ring = next(ln for ln in rtl.splitlines() if "u_cland_y (" in ln)
    assert ring.endswith(", .WREG(1), .DSREP(8), .WRITE_CHUNK(16), .RSTREP(19), .PLACEREP(1)) u_cland_y ("), ring
    # the ring reset relay keeps the ring (reader START relay + its 19 copies); the origin + its raw alias move
    assert "    ot_dp_rrelay u_cland_rst_y (.clk(clk), .d(rr_parent), .q(cland_reset_y));" in rtl
    assert ('    (* keep = "true" *) ot_dp_rrelay u_cland_rfan_y_1 (.clk(clk), .d(rr_parent), .q(cland_rfan_y_1));'
            in rtl), rtl
    assert loads_of(rtl, "cland_reset_y") == {"u_cland_reader_start_y_0"}
    assert loads_of(rtl, "cland_rfan_y_1") == {"u_cland_origin", "assign:cland_start_raw"}
    rec = lg.reset_placements["B"]["y"]["ring_reset_fan"]
    assert rec["spread_before_um"] > 405 and rec["spread_home_um"] <= 405 and rec["added_cycles"] == 0
    (c,) = rec["copies"]
    assert c["instance"] == "u_cland_rfan_y_1" and c["d"] == "rr_parent" and c["loads"] == ["cland_start_raw", "u_cland_origin"]
    assert c["d_hop_um"] <= 405 and c["load_reach_um"] <= 405          # copy at the midpoint: both hops within reach
    assert lg.reset_placements["B"]["count_origin"]["raw_reset"] == "cland_rfan_y_1"
    # data and control cycles unchanged: same strap K, same reader START depth, same ring parameters
    assert CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"] == k0
    assert lg.reset_placements["B"]["y"]["reader_start"]["depth"] == 1
    # deterministic
    p2, t2, body2 = hd_serdes_vehicle()
    assert Landings(p2, t2).type_rtl("B", body2) == rtl


def test_loads_within_reach_are_byte_identical(monkeypatch):
    p, t, body = hd_serdes_vehicle(far_origin=False)          # origin at its p_start pin on the band
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", body)
    assert "u_cland_rfan_" not in rtl and "ring_reset_fan" not in lg.reset_placements["B"]["y"]
    monkeypatch.setattr(Landings, "_ring_reset_fan", lambda self, tn, key, logic, body="": None)   # pre-rule generator
    p2, t2, body2 = hd_serdes_vehicle(far_origin=False)
    assert Landings(p2, t2).type_rtl("B", body2) == rtl
    p3, t3, body3 = hd_serdes_vehicle()                      # and the far case differs from it only by the copy
    far_off = Landings(p3, t3).type_rtl("B", body3)
    assert "u_cland_rfan_" not in far_off and ".rst_raw_n(cland_reset_y), .p_start(cland_fstart_in_y)" in far_off


def test_reach_rule_reports_the_fan():
    import reach_rules as RR
    p, t, _ = hd_serdes_vehicle()
    B = p["partition_types"]["B"]
    B["clock"]["landing_contract"]["pins"] = [dict(name="cland_fstart_in_y", dir="in", kind="ctl", xy_um=[1936.032, 2.656])]
    row, fs = RR.ring_reset_fan_findings(B, "B")
    assert row["ring"] == "y" and row["copies"] == 1 and row["residual_um"] <= 405
    assert [f["kind"] for f in fs] == ["ring_reset_fan"] and fs[0]["rule"] == "6" and fs[0]["warn"]
    assert "u_cland_rfan_y_1 <- origin" in fs[0]["msg"]
    del B["clock"]["landing_origin_rect_um"]
    assert RR.ring_reset_fan_findings(B, "B")[1] == []      # origin on its tree-bus pin at the band: within reach


def test_cluster_rule_hd_serdes_r11_geometry():
    # r11 plan sites: band + tap 19 (home), origin at cland_tstart_in with the FSTART face flop at cland_fstart_out_coll_o0,
    # monitor output collect at cland_up_ready_coll_o0
    home = [tuple(BAND[:2]), tuple(BAND[2:]), tuple(TAP19)]
    groups = [("origin", [(1452.0, 77.728), (1714.4, 2.656)]), ("u_cland_up_coll_o0", [(1710.048, 2.656)])]
    before, kept, far = CL.reset_fan_clusters(home, groups)
    assert round(before, 1) == 653.2 and kept == ["u_cland_up_coll_o0"]
    assert [n for n, _p in far] == [["origin"]] and CL._bbox_spread(far[0][1]) <= 405
    assert CL.reset_fan_clusters(home, groups[1:]) == (CL._bbox_spread(home + groups[1][1]), ["u_cland_up_coll_o0"], [])
