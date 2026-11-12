"""LF-CS-GATE: plan station depth per (leaf type, class) == bound RTL depth; kit_istations u_lf<k>_ prefix count."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as KI   # noqa: E402
import leaf_cs_depth as LCD  # noqa: E402


def _bound(pfx="", hig=2, y=0, sw=0):
    r = ["module m (input wire clk);"]
    for g in range(4):
        for j in range(hig):
            r.append(f"    always @(posedge clk) g_{pfx}u_vp_g_hig_{g}_u_cst_gd_s_{j}_u_src_ab12_q <= 1'b0;")
            r.append(f"    always @(posedge clk) g_{pfx}u_vp_g_hog_{g}_u_cst_gd_s_{j}_u_src_cd34_q <= 1'b0;")
    for j in range(y):
        r.append(f"    always @(posedge clk) g_{pfx}u_cst_y_gd_s_{j}_u_src_ee_q <= 1'b0;")
    for j in range(sw):
        r.append(f"    always @(posedge clk) g_{pfx}u_cst_sw_gd_s_{j}_u_src_ff_q <= 1'b0;")
        r.append(f"    always @(posedge clk) g_{pfx}u_cst_swr_gd_s_{j}_u_src_ff_q <= 1'b0;")   # swr must not count as sw twice
    return "\n".join(r + ["endmodule"]) + "\n"


def test_native_params_counts_the_image_flat_lf_prefix():
    for pfx in ("", "u_lf1_", "u_lf12_"):
        have = KI.native_params(_bound(pfx, hig=2, y=1, sw=1))
        assert have["CS_HI_D"] == 2 and have["CS_HI_GS"] == 2 and have["CS_HO_D"] == 2, (pfx, have)
        assert have["CS_Y_D"] == 1 and have["CS_SW_D"] == 1 and have["CS_SWR_D"] == 1 and have["CS_U_D"] == 0, (pfx, have)
        assert have["CS_H_G"] == 4


def test_native_params_does_not_match_inside_another_name():
    txt = "always @(posedge clk) xg_u_lf1_u_cst_y_gd_s_0_u_q <= 1'b0;\n"
    assert KI.native_params(txt)["CS_Y_D"] == 0


def _st(launch, capture, n):
    return dict(conn=f"{launch}|core:{capture}", launch=launch, capture=capture, regs_um=[[1.0, 2.0]] * n, bits=1,
                from_um=[0, 0], to_um=[1, 1])


def _plan(rows):
    return dict(partition_types={"ot_s81sl_leaf__t8": dict(hard_cores=[dict(inst="u_lf.u_vq")], internal_stations=rows)})


ROWS_OK = [_st("core:u_lf.u_vn.u_a.hq_d", "u_lf.u_vp.g_ln[3].u_l", 2),
           _st("core:u_lf.u_vn.u_a.hw_d", "u_lf.u_vp.g_ln[3].u_l", 2),
           _st("core:u_lf.u_vn.u_b.y", "u_lf.u_vq.y", 1),
           _st("core:u_lf.u_vn.u_a.y_i", "u_lf.u_vq.y_i", 1)]


def test_gate_passes_when_plan_equals_bound(tmp_path):
    (tmp_path / "s81p_ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=2, y=1))
    errors, rows = LCD.check(_plan(ROWS_OK), tmp_path)
    assert errors == [], errors
    assert {(r["cls"], r["plan"], r["bound"]) for r in rows} == {("hi", 2, 2), ("ho", 2, 2), ("y", 1, 1)}


def test_gate_fails_when_the_rtl_lacks_a_planned_stage(tmp_path):
    (tmp_path / "s81p_ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=2, y=0))
    errors, _ = LCD.check(_plan(ROWS_OK), tmp_path)
    assert errors == ["LF_CS_DEPTH ot_s81sl_leaf__t8 y: plan 1 stage(s) (deepest row), bound RTL 0"]


def test_gate_fails_on_an_unplanned_rtl_stage_and_takes_the_deepest_row(tmp_path):
    rows = ROWS_OK + [_st("core:u_lf.u_vn.u_b.y_v", "u_lf.u_vq.y_v", 2)]
    (tmp_path / "s81p_ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=2, y=1, sw=1))
    errors, rows_ = LCD.check(_plan(rows), tmp_path)
    assert "LF_CS_DEPTH ot_s81sl_leaf__t8 y: plan 2 stage(s) (deepest row), bound RTL 1" in errors
    assert "LF_CS_DEPTH ot_s81sl_leaf__t8 sw: plan 0 stage(s) (deepest row), bound RTL 1" in errors
    assert next(r for r in rows_ if r["cls"] == "y")["disagree"] == [1, 2]


def test_gate_reports_cs_rows_and_missing_files(tmp_path):
    plan = _plan(ROWS_OK + [_st("core:u_lf.u_vn.u_a.c_s", "u_lf.u_vn.u_b", 1)])
    errors, _ = LCD.check(plan, tmp_path)
    assert errors == [f"LF_CS_DEPTH ot_s81sl_leaf__t8: no bound module file in {tmp_path}"]
    (tmp_path / "ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=2, y=1))     # clone form: no s81p_ prefix
    errors, _ = LCD.check(plan, tmp_path)
    assert len(errors) == 1 and errors[0].startswith("LF_CS_DEPTH ot_s81sl_leaf__t8 cs: 1 planned")


def test_bind_gate_fails_unstaged_and_passes_staged(tmp_path):
    """the r12ng form (bound leaf at the old literals: no y stage) fails; the staged form (plan depths) passes"""
    (tmp_path / "rtl").mkdir()
    f = tmp_path / "rtl" / "s81p_ot_s81sl_leaf__t8.sv"
    f.write_text(_bound("u_lf1_", hig=2, y=0))
    errs = []
    s = LCD.bind_gate(_plan(ROWS_OK), tmp_path, errs)
    assert s["verdict"] == "FAIL" and errs and json.loads((tmp_path / "bind_leaf_cs_depth.json").read_text())["errors"]
    f.write_text(_bound("u_lf1_", hig=2, y=1))
    errs = []
    assert LCD.bind_gate(_plan(ROWS_OK), tmp_path, errs)["verdict"] == "PASS" and errs == []


R12NG = Path("/srv/opentallas-scratch2/claude/s87bind/out_r12ng")
R12PLAN = Path("/srv/opentallas-scratch2/claude/s81-leaf-floor-2/data/plan_ready12ng.json")


def test_real_r12ng_bind_fails_the_gate(tmp_path):
    import pytest
    if not (R12NG / "rtl").is_dir() or not R12PLAN.is_file():
        pytest.skip("r12ng bind not on this host")
    errs, rows = LCD.check(json.loads(R12PLAN.read_text()), R12NG / "rtl")
    assert len(errs) >= 300 and any(" sw: plan 1 stage(s) (deepest row), bound RTL 0" in e for e in errs)


def test_bind_py_calls_the_gate_when_the_manifest_asks():
    src = (HERE / "bind.py").read_text()
    assert 'B.ab.get("leaf_cs_depth_gate")' in src and "LCD.bind_gate(raw, out, B.errors)" in src
    assert src.index("LCD.bind_gate") < src.index('rep["errors"], rep["n_errors"] = B.errors[:2000]')


def test_cli_exit_status(tmp_path):
    (tmp_path / "s81p_ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=2, y=1))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(_plan(ROWS_OK)))
    assert LCD.main([str(pf), str(tmp_path)]) == 0
    (tmp_path / "s81p_ot_s81sl_leaf__t8.sv").write_text(_bound("u_lf1_", hig=0, y=1))
    assert LCD.main([str(pf), str(tmp_path), "--json", str(tmp_path / "r.json")]) == 1
    assert json.loads((tmp_path / "r.json").read_text())["errors"]
