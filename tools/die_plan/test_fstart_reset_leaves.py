"""FSTART per-face reset leaves (fstart_reset_leaves.py): nearest same-depth raw, generator transform, depth fail-closed."""
import pytest
import fstart_reset_leaves as F
from clock_landings import LandingError

RTL = """module t (input wire clk, input wire arst_n);
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
    wire rst_rl_0;
    ot_dp_head_raw_export_pair u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0), .export_q(rst_start_raw_0));  // raw pad tap 1 depth 1 @ (10.0, 5.0)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 2 depth 2 @ (10.0, 10.0)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_root_n), .q(rst_rl_2));  // raw pad tap 3 depth 1 @ (10.0, 900.0)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw tap tap 4 depth 2 @ (90.0, 950.0)
    wire cland_start_d, cland_start_raw;  // D-side + raw reset of cland_start (FSTART face flops)
    ot_dp_landing_relay u_cland_fstart_n_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(fs_n));
    ot_dp_landing_relay u_cland_fstart_s_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(fs_s));
    wire cland_reset_a_i;
    ot_dp_rrelay u_cland_rst_a_i (.clk(clk), .d(rst_rl_3), .q(cland_reset_a_i));
    assign cland_start_raw = cland_reset_a_i;
endmodule
"""
TCL = """set cland_groups {
  {u_cland_fstart_n_o {96.00000 991.36000 104.64000 1000.00000} writer-face:n_o}
  {u_cland_fstart_s_o {16.00000 0.00000 24.64000 8.64000} writer-face:s_o}
}
"""


def test_nearest_same_depth_raw_and_midpoint_site():
    e = F.plan_entries(RTL, TCL, (200.0, 1000.0))
    assert [(x['name'], x['raw'], x['consumers']) for x in e] == [
        ('fstart_face_n_o', 'rst_rl_3', ['u_cland_fstart_n_o']), ('fstart_face_s_o', 'rst_rl_1', ['u_cland_fstart_s_o'])]
    assert e[1]['xy_um'] == [15.16, 7.16]


def test_apply_is_the_generator_transform_and_keeps_every_release_edge():
    e = F.plan_entries(RTL, TCL, (200.0, 1000.0))
    rtl, tcl, rec = F.apply_kit(RTL, TCL, e, 't')
    assert '(* keep = "true" *) ot_dp_rrelay u_cland_lrst_fstart_face_s_o (.clk(clk), .d(rst_rl_1), ' \
           '.q(cland_lrst_fstart_face_s_o));  // local same-cycle reset copy (depth 3)' in rtl
    assert 'u_cland_fstart_s_o (.clk(clk), .rst_raw_n(cland_lrst_fstart_face_s_o),' in rtl
    assert 'u_cland_fstart_n_o (.clk(clk), .rst_raw_n(cland_lrst_fstart_face_n_o),' in rtl
    assert rtl.index('u_cland_lrst_fstart_face_s_o (') < rtl.index('u_cland_fstart_n_o (')
    assert all(r['depth'] == 3 and r['added_cycles'] == 0 for r in rec)
    # untouched: the original export pair, the old shared relay and its alias
    assert 'export_q(rst_start_raw_0));' in rtl and 'assign cland_start_raw = cland_reset_a_i;' in rtl
    assert '  {u_cland_lrst_fstart_face_s_o {13.00000 5.00000 17.32000 9.32000} local-reset}\n' in tcl


def test_wrong_depth_raw_fails_closed():
    e = F.plan_entries(RTL, TCL, (200.0, 1000.0))
    e[1]['raw'] = 'rst_rl_0'
    with pytest.raises(LandingError, match='release edge would move'):
        F.apply_kit(RTL, TCL, e, 't')


def test_unshared_reset_needs_no_leaf():
    one = RTL.replace("    ot_dp_landing_relay u_cland_fstart_s_o (.clk(clk), .rst_raw_n(cland_start_raw), "
                      ".d(cland_start_d), .q(fs_s));\n", "")
    assert F.plan_entries(one, TCL, (200.0, 1000.0)) == []
