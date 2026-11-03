import json

import pytest

import astk_native_faces as A


def leaf(n=572, fault="qkd_astk_fault_join m0 (", alias_ok=True):
    qo = ", ".join(f"q{b}" for b in reversed(range(n)))
    lines = ["module kv3_astk__leaf (", "    output wire [571:0] u_strip_u_strip_u_ctl__qo", ");", "    wire n0;",
             f"    {fault}.a(n0), .b(b));",
             "    qkd_astk_zn m2 (.ck({ck}), .zc({1'b0, 1'b1, strap_corner[1], strap_corner[0]}), .fi({n0}));",
             "    qkd_astk_zn m3 (.ck({ck}), .zc({1'b1, 1'b0, strap_corner[1], strap_corner[0]}), .fi({n0}));",
             f"    qkd_astk_ctl_s_g0 #(.Z_STRIDE(4)) m5 (.af({{n0}}), .qo({{{qo}}}), .st({{strap_corner[1], strap_corner[0]}}), .ck({{ck}}));"]
    for b in range(572):
        lines.append(f"    assign u_strip_u_strip_u_ctl__qo[{b}] = {'q%d' % b if alias_ok or b else 'zz'};")
    return "\n".join(lines + ["endmodule", ""])


def test_leaf_transform():
    t = A.leaf_transform(leaf())
    assert "qkd_astk_fault_join #(.PORT_REGS(1)) m0 (" in t
    assert "qkd_astk_ctl_s_g0 #(.Z_STRIDE(4), .PORT_REGS(1)) m5 (.qo_face(astk_qo_face), " in t
    assert "assign u_strip_u_strip_u_ctl__qo[571] = astk_qo_face[571];" in t
    assert "wire [571:0] astk_qo_face;" in t
    with pytest.raises(ValueError):
        A.leaf_transform(t)


def test_leaf_transform_refuses_wrong_alias_and_width():
    with pytest.raises(ValueError):
        A.leaf_transform(leaf(alias_ok=False))
    with pytest.raises(ValueError):
        A.leaf_transform(leaf(n=571))


def test_dead_bits_only_unreferenced_stale_inputs():
    w = "\n".join(["module kv3_astk (", "    input wire [1:0] a__tc,", "    input wire [1:0] used,", "    input wire [0:0] rst_n,",
                   ");", "    x u (.u(used));", "endmodule"])
    cj = dict(pin_class={"a__tc[0]": "stale_in", "a__tc[1]": "stale_in", "used[0]": "stale_in", "rst_n[0]": "stale_in",
                         "a__tc[5]": "stale_in"})
    assert A.dead_bits(w, cj) == ["a__tc[0]", "a__tc[1]"]


ZN = """module qkd_astk_zn (
    input  wire [3:0]    zc,
    (* keep *) reg [3:0]   zc_q;
    always @(posedge ck) begin zc_q <= zc; tq[14:1] <= tc[14:1]; end
    wire [1:0]  S = zc_q[1:0], L = zc_q[3:2];
endmodule
"""
CTL = """module qkd_astk_ctl_s_g0 #(parameter integer PORT_REGS=0) (
    input  wire [1:0]    st,
    (* keep *) reg [1:0]   st_q;
    always @(posedge ck) begin
        st_q <= st; aq_q[20:1] <= aq[20:1];
    end
    wire [13:0]  base_s = {5'd0, st_q, 7'd0};
endmodule
"""


def test_strap_direct():
    lv, cf, zones = A.strap_direct(A.leaf_transform(leaf()), ZN, CTL)
    assert zones == ["m2", "m3"]
    assert "reg [3:2]   zc_q;" in lv and "zc_q[3:2] <= zc[3:2];" in lv and "S = zc[1:0], L = zc_q[3:2];" in lv
    assert "st_q" not in cf and "base_s = {5'd0, st, 7'd0};" in cf and "        aq_q[20:1] <= aq[20:1];" in cf
    with pytest.raises(ValueError):
        A.strap_direct(A.leaf_transform(leaf()), lv, cf)       # already applied


def test_strap_direct_refuses_non_strap_zone():
    t = A.leaf_transform(leaf()).replace("strap_corner[1], strap_corner[0]}), .fi", "n7, n8}), .fi", 1)
    with pytest.raises(ValueError):
        A.strap_direct(t, ZN, CTL)


def test_apply_kit(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "qkd_astk_leaves.sv").write_text(ZN)
    (tmp_path / "rtl" / "qkd_astk_ctl_s_g0.sv").write_text(CTL)
    (tmp_path / "rtl" / "abc__leaf.sv").write_text(leaf())
    (tmp_path / "rtl" / "kv3_astk.sv").write_text("module kv3_astk (\n    input wire [1:0] a__tc,\n);\nendmodule\n")
    bits = A.apply_kit(tmp_path, "kv3_astk", dict(pin_class={"a__tc[0]": "stale_in", "a__tc[1]": "stale_in"}))
    assert bits == ["a__tc[0]", "a__tc[1]"]
    d = json.loads((tmp_path / "dead_inputs.json").read_text())
    assert d["schema"] == "opentallas.kit_dead_inputs.v1" and d["proof"]["verdict"] == "PASS"
    delta = json.loads((tmp_path / "astk_native_face_delta.json").read_text())
    assert delta["command_cycles"] == 0 and delta["strap_direct"]["dropped_flops"] == 6
    assert "st_q" not in (tmp_path / "rtl" / "qkd_astk_ctl_s_g0.sv").read_text()
    with pytest.raises(SystemExit):
        A.apply_kit(tmp_path, "kv3_astk_EN", {})
