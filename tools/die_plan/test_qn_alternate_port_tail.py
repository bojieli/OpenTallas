"""C-FACE-SHARED-LOAD / C-RELAYBAY-QNALT (QC-INT-R2-FEFW 11-26): OT_ST_QNALT keeps the last stage of a port-driving chain plain."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402

HEAD = """module t_bound (
    input wire clk,
    input wire rst_n,
    input wire [8:0] a_i,
    output wire [7:0] a_o,
    output wire a_eo
);
    wire [7:0] a_s0;
    wire a_s0e;
    wire [7:0] a_s1;
    wire a_s1e;
    wire [7:0] a_s2;
    wire a_s2e;
"""
CHAIN = """    ot_dp_st #(.W(8)) u_ft_a_o_0 (.clk(clk), .rst_n(rst_n), .d(a_i[7:0]), .ea(a_i[8]), .q(a_s0[7:0]), .eq(a_s0e));
    ot_dp_st #(.W(8)) u_ft_a_o_1 (.clk(clk), .rst_n(rst_n), .d(a_s0[7:0]), .ea(a_s0e), .q(a_s1[7:0]), .eq(a_s1e));
    ot_dp_st #(.W(8)) u_ft_a_o_2 (.clk(clk), .rst_n(rst_n), .d(a_s1[7:0]), .ea(a_s1e), .q(a_s2[7:0]), .eq(a_s2e));
    ot_dp_st #(.W(8)) u_ft_a_o_3 (.clk(clk), .rst_n(rst_n), .d(a_s2[7:0]), .ea(a_s2e), .q(%s[7:0]), .eq(%s));
"""
PORT = HEAD + CHAIN % ("a_o", "a_eo") + "endmodule\n"
INTERNAL = HEAD + "    wire [7:0] a_x;\n    wire a_xe;\n" + CHAIN % ("a_x", "a_xe") + "    assign a_o = a_x;\n    assign a_eo = a_xe;\nendmodule\n"
# the relay_bay pattern for the last station of a lane (tools/die_plan/relay_bay.py)
RB = r"ot_dp_st #\(\.W\((\d+)\)\) u_ft_a_o_3 \(([^;]*)\.q\(a_o\[(\d+):0\]\), \.eq\(a_eo\)\);"


def _run(tmp_path, text):
    f = tmp_path / "rtl" / "t_bound.sv"
    f.parent.mkdir()
    f.write_text(text)
    assert G.qn_alternate_stations(f.parent, ["OT_ST_QNALT"]) == ["t_bound.sv"]
    return f.read_text()


def test_even_port_chain_keeps_plain_tail_for_relay_bay_and_face_guard(tmp_path):
    out = _run(tmp_path, PORT)
    assert re.search(RB, out), out                                   # relay_bay finds the last station
    assert "ot_dp_st #(.W(8)) u_ft_a_o_2" in out                     # k-2 stn + 2 plain
    assert "ot_dp_stn #(.W(8)) u_ft_a_o_0" in out and "ot_dp_stn #(.W(8)) u_ft_a_o_1" in out
    assert not re.search(r"\.qn\(a_o", out)                          # no stn QN (kept q[b] inverter) on the face port: face_guard shared


def test_internal_even_chain_unchanged(tmp_path):
    out = _run(tmp_path, INTERNAL)
    assert "ot_dp_stn #(.W(8)) u_ft_a_o_3" in out                    # a chain that drives no port converts fully, as before
