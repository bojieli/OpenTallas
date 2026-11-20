"""S81-SVC-H8W 11-20: svc_width_gate fails on an H16 lane bound into an H8 core and on an H16 die gather net; the
netlist H stage is exact (identity at H16)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svc_width_gate as G  # noqa: E402
import svc_h_netlist as N  # noqa: E402

CORE = """`ifndef OT_SVC_HV
`ifdef OT_SVC_H8
`define OT_SVC_HV 8
`else
`define OT_SVC_HV 16
`endif
`endif
module dsdv_svc_rs_c #(parameter logic [39:0] FM = {40{1'b1}}, parameter integer H = `OT_SVC_HV) (
    input wire [4*(H*132+20)-1:0] gi_d, output wire [4*(H*132+20)-1:0] go_d);
endmodule
"""
OLD = """module dsdv_svc_rs_fv_0001 #(parameter bit SMT = 1) (input wire [2131:0] gi_d_n, output wire [2131:0] go_d_n);
    wire [8527:0] c_gi_d; wire [8527:0] c_go_d;
    assign c_gi_d[2131:0] = gi_d_n;
    dsdv_svc_rs_c #(.FM(40'h1)) u (.gi_d(c_gi_d), .go_d(c_go_d));
    assign go_d_n = c_go_d[2131:0];
endmodule
"""
NEW = """module dsdv_svc_rs_fv_0001 #(parameter bit SMT = 1, parameter integer H = `OT_SVC_HV) (
    input wire [H*132+19:0] gi_d_n, output wire [H*132+19:0] go_d_n);
    wire [4*(H*132+20)-1:0] c_gi_d; wire [4*(H*132+20)-1:0] c_go_d;
    assign c_gi_d[(H*132+20)*0 +: (H*132+20)] = gi_d_n;
    dsdv_svc_rs_c #(.FM(40'h1), .H(H)) u (.gi_d(c_gi_d), .go_d(c_go_d));
    assign go_d_n = c_go_d[(H*132+20)*0 +: (H*132+20)];
endmodule
"""
NET = """module dv_die ();
  wire [2132:0] w_sg_00_01_src, w_sg_00_01_dst;
  wire [2132:0] w_sg_00_01_lnd;
  dsdv_svc_rs_fv_0001 u_rsv_00 (.gi_d_n(w_sg_00_01_lnd[2132:1]), .go_d_n(w_sg_00_01_src[2132:1]));
  dsdv_svc_busland_2133 ld_sg_00_01 (.i(w_sg_00_01_src), .o(w_sg_00_01_lnd));
endmodule
"""
LAND = """module dsdv_svc_busland_2133 (input wire [2132:0] i, output wire [2132:0] o); endmodule
module dsdv_svc_busland_1077 (input wire [1076:0] i, output wire [1076:0] o); endmodule
"""


def _run(tmp, fv, defines, net=None):
    for n, t in (("core.sv", CORE), ("fv.sv", fv), ("land.sv", LAND)):
        (tmp / n).write_text(t)
    nl = None
    if net is not None:
        nl = tmp / "net.v"
        nl.write_text(net)
    return G.run(tmp, defines, ["core.sv", "fv.sv", "land.sv"], [r"dsdv_svc_rs_fv_\w+"], nl)


def test_old_portfix_fails_at_h8_only(tmp_path):
    assert _run(tmp_path, OLD, ["OT_SVC_H8"])["width_mismatch"] == 2
    assert _run(tmp_path, OLD, [])["verdict"] == "PASS"


def test_h_form_passes_both(tmp_path):
    assert _run(tmp_path, NEW, ["OT_SVC_H8"])["verdict"] == "PASS"
    assert _run(tmp_path, NEW, [])["verdict"] == "PASS"


def test_netlist_lane_follows_h(tmp_path):
    r = _run(tmp_path, NEW, ["OT_SVC_H8"], NET)
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 2
    n8, rep = N.transform(NET, 8, 1)
    assert rep["to_lane"] == 1076 and "dsdv_svc_busland_1077 ld_sg_00_01" in n8
    assert _run(tmp_path, NEW, ["OT_SVC_H8"], n8)["verdict"] == "PASS"
    assert N.transform(NET, 16, 1)[0] == NET
