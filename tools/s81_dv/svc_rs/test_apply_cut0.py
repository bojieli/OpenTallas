"""SVC-CUT0-RSV09: apply_cut0.py (CUT_D 0 pass-through wrapper form, OT_SVC_CUT0 on the hi4 core)."""
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WRAP = ROOT / "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv"
spec = importlib.util.spec_from_file_location("apply_cut0", HERE / "apply_cut0.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def test_main_wrapper_has_cut0_form_and_default_1():
    w = WRAP.read_text()
    assert "parameter integer CUT_D = 1\n" in w
    assert w.count("if (CUT_D == 0) begin : g_cap0") == 1 and w.count("if (CUT_D == 0) begin : g_out0") == 1
    assert "localparam integer CDV = (CUT_D < 1) ? 1 : CUT_D;" in w
    # the CUT_D 0 branch is the registered branch with blocking copies: same assignments, no clock
    out0 = w[w.index("begin : g_out0"):w.index("end else begin : g_out\n")]
    outr = w[w.index("end else begin : g_out\n"):]
    assert "posedge" not in out0 and out0.count(" = a_") == outr[:outr.index("end endgenerate")].count(" <= a_") > 20


def test_wrapper_patch_refuses_a_second_pass():
    with pytest.raises(M.Anchor, match="already has the CUT_D 0 form"):
        M.patch_wrapper(WRAP.read_text())


CORE = ("`define OT_SVC_ATTCUT\nmodule dsdv_svc_rs_c_j7_hi4;\n`ifdef OT_SVC_ATTCUT\n    dsdv_svc_att_cut\n`else\n    dsdv_svc_att\n`endif\n"
        "                 #(.H(H)\n`ifdef OT_SVC_ATTCUT\n                   , .CUT_D(1 + CUT_KA)\n`endif\n                   ) u_att ();\nendmodule\n`undef OT_SVC_ATTCUT\n")


def test_core_patch_sets_cut_d_0_under_one_define():
    r = M.patch_core(CORE)
    assert r.startswith("`define OT_SVC_ATTCUT\n`define OT_SVC_CUT0")
    assert "`ifdef OT_SVC_CUT0\n                   , .CUT_D(0)\n`else\n                   , .CUT_D(1 + CUT_KA)\n`endif" in r
    assert r.endswith("`undef OT_SVC_ATTCUT\n`undef OT_SVC_CUT0\n")
    with pytest.raises(M.Anchor):
        M.patch_core(r)


def test_core_patch_refuses_nonzero_ka_kr():
    with pytest.raises(M.Anchor, match="KA = KR = 0"):
        M.patch_core("`define OT_SVC_ATTCUT\n`define OT_SVC_CUT_KA 4\n" + CORE.split("\n", 1)[1])
