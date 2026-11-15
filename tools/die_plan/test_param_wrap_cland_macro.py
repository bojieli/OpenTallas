"""CLAND-MACRO-1 11-14 (FABLE-WAVE-REVIEW fix 7, hard clock-landing macro family): param_wrap wrappers for signed
landing-ring children.  (1) the strap ring declares rst_xn exactly when RSTREP > 0 (the bind connects .rst_xn then; a
wrapper without the port does not elaborate in the parent); (2) the plain forwarded-clock ring ot_dp_clk_landing (S81
stations / leaves) has a port table, and wrap_bound renames the bind's exact instance text.
    python3 -m pytest -q tools/die_plan/test_param_wrap_cland_macro.py"""
import pytest

import param_wrap


def _decl(txt):
    return [ln.strip().rstrip(",") for ln in txt.splitlines() if ln.strip().startswith(("input", "output"))]


def test_cas_rst_xn_follows_rstrep():
    p = dict(W=515, DEPTH=4, STATUS_REG=1, WFALL=1, WREG=1, DSREP=8, RSTREP=10, PLACEREP=1)
    d = _decl(param_wrap.wrapper_sv("m", "ot_dp_clk_landing_cas", p))
    assert "input  wire [9:0] rst_xn" in d and ".rst_xn(rst_xn)" in param_wrap.wrapper_sv("m", "ot_dp_clk_landing_cas", p)
    p0 = dict(W=67, DEPTH=4, WREG=1)
    txt = param_wrap.wrapper_sv("m0", "ot_dp_clk_landing_cas", p0)
    assert "rst_xn" not in txt and "input  wire [5:0] strap_k" in _decl(txt)


def test_plain_ring_wrapper_and_bind_rename():
    p = {"W": 515, "DSREP": 8, "LOCAL": 1, "WNEG": 1}
    txt = param_wrap.wrapper_sv("s81_cland_w515", "ot_dp_clk_landing", p)
    assert _decl(txt) == ["input  wire fclk", "input  wire clk", "input  wire rst_n", "input  wire [514:0] d",
                          "output wire [514:0] q", "output wire ready", "output wire fault"]
    assert "ot_dp_clk_landing #(.W(515), .DSREP(8), .LOCAL(1), .WNEG(1)) u_w (" in txt
    bound = ("module t;\n    wire [514:0] cland_x_i;\n"
             "    ot_dp_clk_landing #(.W(515), .DSREP(8), .LOCAL(1), .WNEG(1)) u_cland_x_i (\n"
             "        .fclk(fclk_in_x_i), .clk(clk), .rst_n(rst_n_t0), .d(x_i), .q(cland_x_i),\n"
             "        .ready(landing_ready_x_i), .fault(landing_fault_x_i));\nendmodule\n")
    hc = [dict(inst="cl_x", module="s81_cland_w515", physical_master="s81_cland_w515", physical_inst="u_bound.u_cland_x_i",
               param_wrap=dict(base="ot_dp_clk_landing", params=p))]
    out, receipt, srcs = param_wrap.wrap_bound(bound, hc)
    assert "    s81_cland_w515 u_cland_x_i (" in out and receipt[0]["cycles_changed"] == 0
    with pytest.raises(ValueError, match="plan says"):
        param_wrap.wrap_bound(bound, [dict(hc[0], param_wrap=dict(base="ot_dp_clk_landing", params=dict(p, DSREP=4)))])
