"""KV-G3 10-24: kit_istations.py inserts len(regs_um) stations on an in bus, re-points the leaf reader, and writes
FIRM sites for the stations and sited plan cells."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [1:0] i_a, output wire q);
    wire [0:0] i_a_q;
    wire i_a_eq;
    ot_dp_st #(.W(1)) u_bin_i_a (.clk(clk), .rst_n(rst_n), .d(i_a[0:0]), .ea(i_a[1]), .q(i_a_q), .eq(i_a_eq));
    qkd_hp_or2 #(.MUT(0)) u_c0 (
        .a(i_a_q[0]),
        .b(1'b0),
        .ck(clk),
        .q(q)
    );
endmodule
"""


def test_inserts_and_sites(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="i_a", dir="in", width=1, kind="data")],
        contents=[dict(inst="c0", module="qkd_hp_or2", origin_um=[10.0, 20.0], outline_um=[4.0, 4.0])],
        internal_stations=[dict(conn="bus:i_a", from_um=[0, 0], to_um=[10, 20], regs_um=[[3, 0], [6, 0]])])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "u_ist_i_a_0 (.clk(clk), .rst_n(rst_n), .d(i_a_q)" in sv
    assert "u_ist_i_a_1 (.clk(clk), .rst_n(rst_n), .d(i_a_is0_q)" in sv
    assert ".a(i_a_is1_q[0])" in sv and ".a(i_a_q[0])" not in sv
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_ist_i_a_0[./]*} 3 0 ist:i_a" in tcl
    assert "is_place {*u_c0[./]*} 12 22 cell:c0" in tcl
    # re-application with more planned stations extends the chain after the last one (in bus)
    plan["partition_types"]["t"]["internal_stations"][0]["regs_um"].append([8, 0])
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "u_ist_i_a_2 (.clk(clk), .rst_n(rst_n), .d(i_a_is1_q)" in sv
    assert ".a(i_a_is2_q[0])" in sv and sv.count("u_ist_i_a_1 (") == 1 and ".q(i_a_is1_q)" in sv


# ---- S81-PLAN R3 (10-25): core<->core stations -> the leaf's CS_* station chains
LEAF_BOUND = """module t_leaf_bound (input wire clk, input wire rst_n);
    ot_s81sl_leaf #(.AQ_XMEM(2)) u_lf (.clk(clk), .rst_n(rst_n));
endmodule
"""


def _core_plan(hi=2, ho=1, extra=()):
    st = []
    for l in range(16):
        st.append(dict(conn=f"core:u_lf.u_vn.u_b.hq_d|core:u_lf.u_vp.g_ln[{l}].u_l", launch="core:u_lf.u_vn.u_b.hq_d",
                       capture=f"u_lf.u_vp.g_ln[{l}].u_l", bits=256, regs_um=[[100.0 + l, 10.0 * (j + 1)] for j in range(hi)]))
        st.append(dict(conn=f"core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[{l}].u_l", launch="core:u_lf.u_vn.u_a.hw_d",
                       capture=f"u_lf.u_vp.g_ln[{l}].u_l", bits=256, regs_um=[[200.0 + l, 5.0 * (j + 1)] for j in range(ho)]))
    st.append(dict(conn="core:u_lf.u_vn.u_b.y|core:u_lf.u_vq.y", launch="core:u_lf.u_vn.u_b.y", capture="u_lf.u_vq.y",
                   bits=64, regs_um=[[50.0, 60.0]]))
    st.append(dict(conn="core:u_lf.u_vn.u_b.y_v|core:u_lf.u_vq.y_v", launch="core:u_lf.u_vn.u_b.y_v",
                   capture="u_lf.u_vq.y_v", bits=1, regs_um=[[51.0, 61.0]]))
    st.extend(extra)
    return dict(partition_types=dict(t=dict(buses=[], contents=[], internal_stations=st)))


def _run_core(tmp_path, plan, *opts):
    kd = tmp_path / "kit"
    kd.mkdir(exist_ok=True)
    if not (kd / "t_leaf_bound.sv").exists():
        (kd / "t_leaf_bound.sv").write_text(LEAF_BOUND)
        (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_leaf_bound", files=[str(kd / "t_leaf_bound.sv")])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), *opts],
                       capture_output=True, text=True)
    return r, kd


def test_core_fails_closed_when_rtl_depth_differs(tmp_path):
    r, _ = _run_core(tmp_path, _core_plan())
    assert r.returncode != 0 and "CS_" in r.stderr and "fail closed" in r.stderr


def test_core_apply_sets_depths_and_sites(tmp_path):
    r, kd = _run_core(tmp_path, _core_plan(), "--apply", "--h-tree", "4,1,0")
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_leaf_bound.sv").read_text()
    for p in (".AQ_XMEM(2)", ".CS_HI_D(2)", ".CS_HI_GS(1)", ".CS_HO_D(1)", ".CS_HO_GS(0)", ".CS_H_G(4)", ".CS_Y_D(1)"):
        assert p in sv, p
    tcl = (kd / "istations.tcl").read_text()
    # hi: stage 0 shared per 4 lanes (centroid of lanes 4..7 at y 10), stage 1 per lane (y 20)
    assert "is_place {*u_lf?u_vp?g_hig\\[1\\]?u_cst?gd?s\\[0\\]?u[./]*} 105.5 10.0 cst:hi" in tcl
    assert "is_place {*u_lf?u_vp?g_ln\\[9\\]?u_cst_hi?gd?s\\[0\\]?u[./]*} 109.0 20.0 cst:hi" in tcl
    assert "is_place {*u_lf?u_vp?g_ln\\[9\\]?u_cst_ho?gd?s\\[0\\]?u[./]*} 209.0 5.0 cst:ho" in tcl
    assert "is_place {*u_lf?u_cst_y?gd?s\\[0\\]?u[./]*}" in tcl
    # verify-only re-run on the applied kit passes
    r, _ = _run_core(tmp_path, _core_plan())
    assert r.returncode == 0, r.stderr


def test_core_unequal_counts_fail(tmp_path):
    p = _core_plan()
    p["partition_types"]["t"]["internal_stations"][4]["regs_um"].append([1.0, 1.0])   # lane 2 hi: 3 stages
    r, _ = _run_core(tmp_path, p, "--apply")
    assert r.returncode != 0 and "unequal" in r.stderr


def test_core_unmapped_and_cs_fail(tmp_path):
    bad = dict(conn="core:u_lf.u_vq.xf|core:u_lf.u_vsw", launch="core:u_lf.u_vq.xf", capture="u_lf.u_vsw", bits=1,
               regs_um=[[1.0, 1.0]])
    r, _ = _run_core(tmp_path, _core_plan(extra=[bad]), "--apply")
    assert r.returncode != 0 and "matches no leaf station class" in r.stderr
    cs = dict(conn="core:u_lf.u_vn.u_a.c_s|core:u_lf.u_vn.u_b.c_s", launch="core:u_lf.u_vn.u_a.c_s",
              capture="u_lf.u_vn.u_b.c_s", bits=31, regs_um=[[1.0, 1.0]])
    r, _ = _run_core(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, _core_plan(extra=[cs]), "--apply")
    assert r.returncode != 0 and "c_s" in r.stderr
