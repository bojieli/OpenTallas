"""QC-FW-CAP 11-23 phase 2: gen_phys.qn_alternate_stations is gated by the type define OT_ST_QNALT and idempotent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402

BOUND = """module t_bound (input wire clk, input wire rst_n, input wire [8:0] a_i, output wire [7:0] a_o);
    wire [7:0] a0_q; wire a0_eq; wire [7:0] a1_q; wire a1_eq; wire [7:0] a2_q; wire a2_eq;
    ot_dp_st #(.W(8)) u_ist_a_0 (.clk(clk), .rst_n(rst_n), .d(a_i[7:0]), .ea(a_i[8]), .q(a0_q), .eq(a0_eq));
    ot_dp_st #(.W(8)) u_ist_a_1 (.clk(clk), .rst_n(rst_n), .d(a0_q), .ea(a0_eq), .q(a1_q), .eq(a1_eq));
    ot_dp_st #(.W(8)) u_ist_a_2 (.clk(clk), .rst_n(rst_n), .d(a1_q), .ea(a1_eq), .q(a2_q), .eq(a2_eq));
    assign a_o = a2_q;
endmodule
"""


def test_absent_define_is_byte_identical(tmp_path):
    f = tmp_path / "rtl" / "t_bound.sv"
    f.parent.mkdir()
    f.write_text(BOUND)
    assert G.qn_alternate_stations(f.parent, ["OT_DLY_CPL"]) == [] and f.read_text() == BOUND


def test_define_pairs_chain_and_is_idempotent(tmp_path):
    f = tmp_path / "rtl" / "t_bound.sv"
    f.parent.mkdir()
    f.write_text(BOUND)
    assert G.qn_alternate_stations(f.parent, ["-DOT_ST_QNALT"]) == ["t_bound.sv"]
    out = f.read_text()
    assert "ot_dp_stn #(.W(8)) u_ist_a_0" in out and "ot_dp_stn #(.W(8)) u_ist_a_1" in out
    assert "ot_dp_st #(.W(8)) u_ist_a_2" in out and "module ot_dp_stn" in out
    assert (tmp_path / "qn_alternate_t_bound.json").is_file()
    assert G.qn_alternate_stations(f.parent, ["OT_ST_QNALT"]) == [] and f.read_text() == out
