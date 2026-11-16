"""FSTART reset leaves as a plan delta (fstart_reset_delta.py): face groups, same-depth raw, generator accepts the rows."""
import copy
import pytest
import fstart_reset_delta as D
import fstart_reset_leaves as F
import reset_anchor as A
from clock_landings import LandingError

RTL = """module t (input wire clk, input wire arst_n);
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 1 depth 1 @ (10.0, 5.0)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (10.0, 10.0)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_root_n), .q(rst_rl_2));  // raw pad tap 3 depth 1 @ (10.0, 900.0)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 4 depth 2 @ (90.0, 950.0)
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_2), .q(rst_rl_4));  // raw tap tap 5 depth 2 @ (100.0, 990.0)
    assign rst_o_n = rst_rl_4;
    wire cland_start_d, cland_start_raw;  // D-side + raw reset of cland_start (FSTART face flops)
    ot_dp_landing_relay u_cland_fstart_n_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(fs_n));
    ot_dp_landing_relay u_cland_fstart_n2_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(fs_n2));
    ot_dp_landing_relay u_cland_fstart_s_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(fs_s));
    wire cland_reset_a_i;
    ot_dp_rrelay u_cland_rst_a_i (.clk(clk), .d(rst_rl_3), .q(cland_reset_a_i));
    assign cland_start_raw = cland_reset_a_i;
endmodule
"""


def typ():
    return dict(module="t", outline_um=[200.0, 1000.0], clock=dict(landing_contract=dict(pins=[
        dict(name="cland_fstart_out_n_o", xy_um=[100.0, 997.3]), dict(name="cland_fstart_out_n2_o", xy_um=[140.0, 997.3]),
        dict(name="cland_fstart_out_s_o", xy_um=[20.0, 2.7])])))


def test_groups_per_face_same_depth_raw_never_a_ported_relay():
    t = typ()
    rows, rep = D.type_delta("t", t, RTL, A, ".", span=200.0)
    assert [(r["name"], r["raw"], r["consumers"]) for r in rows] == [
        ("fstart_0", "rst_rl_3", ["u_cland_fstart_n_o", "u_cland_fstart_n2_o"]),
        ("fstart_1", "rst_rl_1", ["u_cland_fstart_s_o"])]          # rst_rl_4 is nearer the N face but drives rst_o
    assert rows[0]["xy_um"] == [120.0, 997.3] and rep[0]["depth"] == 3 and rep[0]["was"] == "cland_reset_a_i"
    assert t["clock"]["landing_local_resets"] == rows
    assert t["clock"][A.KEY]["relays"] == {"rst_rl_1": {"depth": 2, "xy": [10.0, 10.0]},
                                           "rst_rl_3": {"depth": 2, "xy": [90.0, 950.0]}}


def test_span_splits_a_face_and_existing_rows_are_kept():
    t = typ()
    rows, _ = D.type_delta("t", t, RTL, A, ".", span=30.0)
    assert [r["consumers"] for r in rows] == [["u_cland_fstart_n_o"], ["u_cland_fstart_n2_o"], ["u_cland_fstart_s_o"]]
    t2 = typ()
    t2["clock"]["landing_local_resets"] = [dict(name="fstart_0", raw="rst_rl_1", xy_um=[20.0, 4.0],
                                                 consumers=["u_cland_fstart_s_o"])]
    rows2, _ = D.type_delta("t", t2, RTL, A, ".", span=200.0)
    assert [(r["name"], r["consumers"]) for r in rows2] == [("fstart_1", ["u_cland_fstart_n_o", "u_cland_fstart_n2_o"])]
    assert len(t2["clock"]["landing_local_resets"]) == 2


def test_generator_accepts_the_rows_and_far_leaf_fails_closed():
    t = typ()
    rows, _ = D.type_delta("t", t, RTL, A, ".", span=200.0)
    tcl = "set cland_groups {\n}\n"
    rtl, _, rec = F.apply_kit(RTL, tcl, copy.deepcopy(rows), "t")
    assert "u_cland_fstart_n_o (.clk(clk), .rst_raw_n(cland_lrst_fstart_0)," in rtl
    assert "u_cland_fstart_s_o (.clk(clk), .rst_raw_n(cland_lrst_fstart_1)," in rtl
    assert [r["depth"] for r in rec] == [3, 3] and all(r["added_cycles"] == 0 for r in rec)
    bad = copy.deepcopy(rows)
    bad[0]["raw"] = "rst_rl_0"                                     # depth 1: the release edge would move
    with pytest.raises(LandingError):
        F.apply_kit(RTL, tcl, bad, "t")
    with pytest.raises(D.DeltaError):
        D.type_delta("t", typ(), RTL, A, ".", span=200.0, reach=30.0)
