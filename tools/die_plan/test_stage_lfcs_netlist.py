"""LF-CS stage: plan leaf depths -> #(.LF_CS_*) on the die slice instances (nibble k = leaf u_lf<k>)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_lfcs_netlist as SN  # noqa: E402

CL = SN.CL


def _rtl(d, mod, defaults):
    d.mkdir(parents=True, exist_ok=True)
    decl = ", ".join(f"parameter [19:0] LF_CS_{x} = {defaults.get(x, "20'h0")}" for x in CL)
    (d / f"{mod}.sv").write_text(f"module {mod} #({decl}) (input wire clk);  // c\nendmodule\n")
    return d


def _st(launch, capture, n):
    return dict(conn=f"{launch}|core:{capture}", launch=launch, capture=capture, regs_um=[[0, 0]] * n)


PLAN = dict(partition_types={
    "ot_s81sl_leaf__t8": dict(hard_cores=[1], internal_stations=[
        _st("core:u_lf.u_vn.u_b.y", "u_lf.u_vq.y", 1), _st("core:u_lf.u_vn.u_a.y_i", "u_lf.u_vq.y_i", 2),
        _st("core:u_lf.u_vn.u_a.hq_d", "u_lf.u_vp.g_ln[3].u_l", 2)]),
    "ot_s81sl_leaf__t9": dict(hard_cores=[1], internal_stations=[_st("core:u_lf.u_vs.sw_d", "u_lf.u_vsw.i_d", 1)])},
    partitions=[dict(name="s_0N_L1", type="ot_s81sl_leaf__t8"), dict(name="s_0N_L3", type="ot_s81sl_leaf__t9")])
NET = ("module dv_die (input wire clk);\n"
       "    ot_s81sl_slice_x #(.HBC_ENABLE(0)) u_s_0N (.clk(clk));\n"
       "    ot_s81sl_slice_y u_s_1N (.clk(clk));\nendmodule\n")


def test_stage_sets_plan_nibbles_and_keeps_module_defaults(tmp_path):
    rtl = _rtl(tmp_path / "rtl", "ot_s81sl_slice_x", {"HI_D": "20'h22222", "HI_GS": "20'h22222", "HO_D": "20'h22222",
                                              "HO_GS": "20'h22222", "H_G": "20'h44444"})
    out, rep = SN.stage(PLAN, NET, rtl)
    line = next(ln for ln in out.splitlines() if "u_s_0N" in ln)
    assert line.startswith("    ot_s81sl_slice_x #(.HBC_ENABLE(0), .LF_CS_HI_D(")
    assert ".LF_CS_Y_D(20'h00020)" in line                    # leaf 1: deepest y row (2); others 0 (module default)
    # leaf 1 hi 2 (GS = D); leaf 3 is a plan leaf with no hi rows -> 0 (the gate's plan depth); leaves 0, 2, 4 default 2
    assert ".LF_CS_HI_D(20'h20222)" in line and ".LF_CS_HI_GS(20'h20222)" in line
    assert ".LF_CS_SW_D(20'h01000)" in line and ".LF_CS_H_G(20'h44444)" in line
    assert "u_s_1N (.clk(clk));" in out and "ot_s81sl_slice_y u_s_1N" in out        # no plan leaf: untouched
    r8 = next(r for r in rep if r.get("type") == "ot_s81sl_leaf__t8")
    assert r8["k"] == 1 and r8["disagree"] == {"y": [1, 2]}


def test_stage_fails_on_an_unforwarded_slice_or_a_preset_lf_cs(tmp_path):
    d = tmp_path / "rtl"
    d.mkdir()
    (d / "ot_s81sl_slice_x.sv").write_text("module ot_s81sl_slice_x #(parameter HBC_ENABLE = 0) (input wire clk);\nendmodule\n")
    with pytest.raises(SystemExit, match="no LF_CS_HI_D parameter"):
        SN.stage(PLAN, NET, d)
    rtl = _rtl(tmp_path / "b", "ot_s81sl_slice_x", {})
    with pytest.raises(SystemExit, match="already sets LF_CS"):
        SN.stage(PLAN, NET.replace("#(.HBC_ENABLE(0))", "#(.LF_CS_Y_D(20'h1))"), rtl)
