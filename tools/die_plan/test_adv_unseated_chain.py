"""pytest: ADV-UNSEATED-CHAIN on the QC cbf_q11 delay pipes (ot_dp_dly #(.W(514), .D(10)) against an 89 um pin window)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_unseated_chain as A  # noqa: E402

BODY = """module m(input clk);
    ot_dp_dly #(.W(516), .D(6)) u_d6_u_fab_u_x_2_2_a_d (.clk(clk), .d(w), .q(q));
    ot_dp_dly #(.W(514), .D(10)) u_d10_u_t_3_2_n_y (.clk(clk), .d(w2), .q(q2));
    ot_dp_dly #(.W(8), .D(1)) u_d1_small (.clk(clk), .d(a), .q(b));
endmodule
"""


def test_dly_chain_parse_skips_single_stage():
    ch = A.dly_chains(BODY)
    assert ("u_d10_u_t_3_2_n_y", 514, 10) in ch and all(d >= 2 for _, _, d in ch) and len(ch) == 2


def test_cbf_q11_pipe_flagged_against_89um_window():
    af, nf, need, win = A.judge(514 * 10, 89.088)
    assert af and need > 4000 and win < 1600


def test_small_pipe_fits():
    assert A.judge(8 * 2, 89.0)[:2] == (False, False)


def test_not_run_without_bound_rtl_and_never_raises():
    assert "NOT-RUN" in A.findings({"partition_types": {}}, "/nonexistent/p.json", None)[0]
    assert A.findings(None, "p")[0].startswith("WARN ADV-UNSEATED-CHAIN not checked")
