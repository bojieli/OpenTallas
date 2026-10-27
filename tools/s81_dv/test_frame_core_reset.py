"""frame_band_plan.py (k) + frame_core_reset_plan.py (S81-UNBLOCK-1 10-27, COORD RULING S81-KITS-1 blocker C).
    python3 -m pytest -q tools/s81_dv/test_frame_core_reset.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frame_band_plan as FB  # noqa: E402
import frame_core_reset_plan as FP  # noqa: E402

BAND = """module col_h9_l4_lp_r2 #(
    parameter integer MUT = 0,
    parameter [11:0] LK = {4{3'd2}}
) (
    input  wire clk,
    output wire [3:0] frame_int_o0,
    input  wire [3:0] frame_int_i0
);
    wire lpr_c_u_e0;
    wire lpr_c_u_s0;
    ot_pl_pad #(.W(1), .N((MUT == 4) ? 400 : 0)) u_lprc_u_e0 (.ck(clk), .d(lpr_r2_leaves[(7)+8]), .q(lpr_c_u_e0));
    ot_pl_pad #(.W(1), .N(0)) u_lprc_u_s0 (.ck(clk), .d(lpr_r2_leaves[(7)+9]), .q(lpr_c_u_s0));
    ot_v41_rom_elem_q_qxpq_w10 u_e0 (.clk(clk), .rst_n(lpr_c_u_e0), .cfg_v(n1), .go(n2));
    ot_s81_cfg7_seq u_s0 (.clk(clk), .rst_n(lpr_c_u_s0), .go(n2));
endmodule
module other_mod (input wire a);
endmodule
"""


def test_core_reset_takes_partition_rst_n():
    out, log = FB.core_reset_wavefront(BAND)
    assert "    input  wire clk,\n    input  wire rst_n," in out
    assert "u_e0 (.clk(clk), .rst_n(rst_n)," in out
    assert "u_lprc_u_e0" not in out and "wire lpr_c_u_e0;" not in out
    # only the declared element cores move; other control state keeps the frame forest
    assert "u_s0 (.clk(clk), .rst_n(lpr_c_u_s0)" in out and "u_lprc_u_s0" in out
    assert "module other_mod (input wire a);" in out
    assert len(log) == 2
    again, log2 = FB.core_reset_wavefront(out)                 # idempotent
    assert again == out and log2 == []


def test_core_reset_keeps_a_shared_pad():
    """a pad that also feeds another load is not removed (only the core pin moves)."""
    txt = BAND.replace("ot_s81_cfg7_seq u_s0 (.clk(clk), .rst_n(lpr_c_u_s0)", "ot_s81_cfg7_seq u_s0 (.clk(clk), .rst_n(lpr_c_u_e0)")
    out, _ = FB.core_reset_wavefront(txt)
    assert "u_lprc_u_e0" in out and "wire lpr_c_u_e0;" in out and "u_e0 (.clk(clk), .rst_n(rst_n)," in out


def _plan():
    def t(mod, bind):
        return dict(sources=["rtl/x.sv", "rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h9_l4_lp_plan_kit.sv"],
                    contents=[dict(inst="u_r", module=mod, bind=dict(bind))])
    return {"partition_types": {
        "r0": t("col_h9_l4_lp_r0", {"clk": "clk", "rst_n": "rst_n"}),
        "r2": t("col_h9_l4_lp_r2", {"clk": "clk"}),
        "x": dict(sources=["rtl/y.sv"], contents=[dict(inst="u", module="leaf", bind={"clk": "clk"})])}}


def test_plan_delta_binds_rst_n_and_swaps_the_source():
    raw, log = FP.apply(_plan())
    T = raw["partition_types"]
    assert T["r2"]["contents"][0]["bind"]["rst_n"] == "rst_n"
    assert all(s.endswith("_plan_kit_cr.sv") for s in T["r2"]["sources"][1:]) and T["r0"]["sources"][0] == "rtl/x.sv"
    assert T["x"] == _plan()["partition_types"]["x"]              # non-frame types untouched
    raw2, log2 = FP.apply(raw)
    assert raw2 == raw and log2 == []


def test_plan_delta_refuses_a_foreign_rst_n_bind():
    p = _plan()
    p["partition_types"]["r2"]["contents"][0]["bind"]["rst_n"] = "net:other"
    with pytest.raises(SystemExit):
        FP.apply(p)
