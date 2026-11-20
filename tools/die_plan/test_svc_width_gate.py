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


MEM = """module dsdv_svc_mem_ar #(parameter integer W = 256, parameter integer AW = 6) (
    input wire [AW-1:0] ra,
    output wire [W-1:0] rd);
endmodule
"""
USERS = """module dsdv_svc_u1 (input wire ck);
    wire [5:0] a1;
    wire [255:0] d1;
    dsdv_svc_mem_ar #(.W(256), .AW(6)) m1 (.ra(a1), .rd(d1));
endmodule
module dsdv_svc_u2 (input wire ck);
    wire [2:0] a2;
    wire [340:0] d2;
    dsdv_svc_mem_ar #(.W(341), .AW(3)) m2 (.ra(a2), .rd(d2));
endmodule
"""


def test_shared_blackbox_fails_at_every_h():
    """COORD 11-20: a slang empty blackbox shared by differently-parameterised svc instances (dsdv_svc_mem_ar W 256 /
    341 / 512) is a finding at H16 and H8 alike; listing it as parameterised clears it."""
    lib = G.library([G.prep(MEM, []), G.prep(USERS, [])])
    assert G.shared_blackbox_widths(lib, {"dsdv_svc_mem_ar"}, set())
    assert not G.shared_blackbox_widths(lib, {"dsdv_svc_mem_ar"}, {"dsdv_svc_mem_ar"})
    hook = (Path(__file__).resolve().parent / "bind_elab.py").read_text()
    assert 'r["H"] == 16 and only_shared' not in hook
    assert 'if r["verdict"] != "PASS":' in hook


def test_portfix_overlays_are_fresh():
    """FRESH: the bind178 PORTFIX svc overlays are exactly what svc_rs_faces.py --portfix writes (no hand copy)."""
    import subprocess
    root = Path(__file__).resolve().parents[2]
    gen = root / "tools" / "s81_dv" / "svc_rs" / "svc_rs_faces.py"
    r = subprocess.run([sys.executable, "-I", str(gen), "--root", str(root), "--check", "--only-portfix"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
