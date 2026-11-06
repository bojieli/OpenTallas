"""KV-G3 10-24: kit_istations.py inserts len(regs_um) stations on an in bus, re-points the leaf reader, and writes
FIRM sites for the stations and sited plan cells."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_signed_hardcore_view_does_not_emit_soft_cell_guide(tmp_path):
    """Actual q_spb2 shape: contents lacks LEF; two explicit hard-core views own the cells."""
    sys.path.insert(0, str(HERE))
    import kit_istations
    t = dict(contents=[
        dict(inst='u_xc_Q2', module='xcal', origin_um=[682.56, 1244.16], outline_um=[138.24, 224.64]),
        dict(inst='u_xc_Q3', module='xcal', origin_um=[1321.92, 1244.16], outline_um=[138.24, 224.64]),
        dict(inst='fault_or', module='qkd_hp_or2', origin_um=[10, 20], outline_um=[4, 4])],
        hard_cores=[dict(inst=name, module='xcal', physical_inst='u_bound.u_'+name,
                         physical_master='xcal', lef=str(tmp_path/'xcal.lef'),
                         origin_um=at, outline_um=[241.92, 224.64])
                    for name, at in [('u_xc_Q2', [717.12, 1244.16]), ('u_xc_Q3', [1321.92, 1244.16])]])
    (tmp_path/'xcal.lef').write_text('MACRO xcal\nSIZE 241.92 BY 224.64 ;\nEND xcal\n')
    assert [c['inst'] for c in kit_istations.soft_plan_cells('q_spb2', t)] == ['fault_or']
    # Without the explicit view the logical cell remains soft; do not skip by module name.
    t['hard_cores'] = []
    assert len(kit_istations.soft_plan_cells('q_spb2', t)) == 3

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


def test_narrow_input_stations_preserve_payload_and_require_proof(tmp_path):
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="i_a", dir="in", width=3, kind="data")],
        internal_stations=[dict(conn="bus:i_a", regs_um=[[3, 0]])])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    for case in ("proved", "no_proof", "missing_bit"):
        kd = tmp_path / case
        kd.mkdir()
        bound = kd / "t_part_bound.sv"
        bound.write_text(BOUND)
        proof = dict(verdict="PASS") if case != "no_proof" else {}
        bits = ["i_a[1]", "i_a[2]"] if case != "missing_bit" else ["i_a[1]"]
        (kd / "kit_rtl.json").write_text(json.dumps(dict(
            bound_module="t_part_bound", files=[str(bound)],
            narrow_buses=[dict(port="i_a", plan=3, bound=1)],
            dead_inputs=dict(bits=bits, proof=proof))))
        r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                           capture_output=True, text=True)
        if case == "proved":
            assert r.returncode == 0, r.stderr
            assert "ot_dp_st #(.W(1)) u_ist_i_a_0" in bound.read_text()
            assert "ot_dp_st #(.W(3))" not in bound.read_text()
            report = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]
            assert (report["plan_width"], report["bound_width"]) == (3, 1)
            assert json.loads(pf.read_text()) == plan
        else:
            assert r.returncode != 0
            assert "complete dead-input proof required" in r.stderr
            assert bound.read_text() == BOUND


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


def test_core_h_classes_on_different_lane_subsets_pass(tmp_path):
    """DIE-S81-69 11-06 (kv_leaf t1/t3/t4/t5): hi sited on lanes {0,5,7,9}, ho on {0,5,7,8,9}; one depth per class
    on all lanes, sited lanes FIRM, the rest GPL; reported in h_lanes, no fail."""
    p = _core_plan(hi=1, ho=1)
    hi_l, ho_l = {0, 5, 7, 9}, {0, 5, 7, 8, 9}
    keep = []
    for e in p["partition_types"]["t"]["internal_stations"]:
        if "g_ln[" not in e["conn"]:
            keep.append(e)
            continue
        lane = int(e["conn"].split("g_ln[")[1].split("]")[0])
        if (".hq_d|" in e["conn"] and lane in hi_l) or (".hw_d|" in e["conn"] and lane in ho_l):
            keep.append(e)
    p["partition_types"]["t"]["internal_stations"] = keep
    r, kd = _run_core(tmp_path, p, "--apply", "--h-tree", "4,1,0")
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_leaf_bound.sv").read_text()
    assert ".CS_HI_D(1)" in sv and ".CS_HO_D(1)" in sv
    tcl = (kd / "istations.tcl").read_text()
    assert "g_ln\\[8\\]?u_cst_ho" in tcl and "g_ln\\[8\\]?u_cst_hi" not in tcl
    # shared hi stage (GS_IN 1): groups 0 (0..3), 1 (4..7), 2 (8..11) sited; group 3 (12..15) has no lane -> GPL
    assert "g_hig\\[1\\]" in tcl and "g_hig\\[3\\]" not in tcl
    r, _ = _run_core(tmp_path, p)
    assert r.returncode == 0, r.stderr


def test_core_unmapped_and_cs_fail(tmp_path):
    bad = dict(conn="core:u_lf.u_vq.xf|core:u_lf.u_vsw", launch="core:u_lf.u_vq.xf", capture="u_lf.u_vsw", bits=1,
               regs_um=[[1.0, 1.0]])
    r, _ = _run_core(tmp_path, _core_plan(extra=[bad]), "--apply")
    assert r.returncode != 0 and "matches no leaf station class" in r.stderr
    cs = dict(conn="core:u_lf.u_vn.u_a.c_s|core:u_lf.u_vn.u_b.c_s", launch="core:u_lf.u_vn.u_a.c_s",
              capture="u_lf.u_vn.u_b.c_s", bits=31, regs_um=[[1.0, 1.0]])
    r, _ = _run_core(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, _core_plan(extra=[cs]), "--apply")
    assert r.returncode != 0 and "c_s" in r.stderr


# ---- D-QC-FE-REACH (10-26): bit_route "chain" -> per-bit is_chain sites on each bit's in-pin -> landing route
def test_chain_route_emits_is_chain(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="i_a", dir="in", width=1, kind="data", face="W", window_um=[0.0, 2.0])], contents=[],
        internal_stations=[dict(conn="bus:i_a", from_um=[0, 1], to_um=[600, 300], regs_um=[[200, 100], [400, 200]],
                                bit_route="chain", core_glob="u_c0")])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert ".a(i_a_is1_q[0])" in sv
    tcl = (kd / "istations.tcl").read_text()
    assert "proc is_chain {bus W names face core_glob tag}" in tcl
    assert "is_chain i_a 1 {u_ist_i_a_0 u_ist_i_a_1} W {u_c0.} ist:i_a" in tcl
    assert "is_place {*u_ist_i_a_0" not in tcl          # per-bit sites only, no shared centroid site


# ---- DIE-KV-59 10-31: opt-in relay_sites = FIRM sites for existing RTL stage flops (no RTL change, 0 cycles)
def test_relay_sites(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    plan = dict(partition_types=dict(t=dict(buses=[dict(name="i_a", dir="in", width=1, kind="data")], contents=[],
                                            relay_sites={"u_bin_i_a/q[0]": [5.5, 7], "u_c0.q": [9, 1]})))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (kd / "t_part_bound.sv").read_text() == BOUND
    tcl = (kd / "istations.tcl").read_text()
    assert "proc rs_place_all" in tcl and "[$i getName]\\trelay" in tcl
    assert "rs_place_all [dict create {u_bin_i_a/q[0]} {5.5 7} {u_c0.q} {9 1}]" in tcl
    assert tcl.index("rs_place_all [dict") < tcl.index("close $is_fh")
    man = json.loads((kd / "kit_rtl.json").read_text())
    assert man["kit_relay_sites"] == 2 and all("stations" in e for e in man["kit_istations"])  # receipt rows stay station rows
    plan["partition_types"]["t"]["relay_sites"]["u_c0.q"] = [9]
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "relay_sites[u_c0.q]" in (r.stderr + r.stdout)


def test_relay_sites_only_tcl():
    # DIE-KV-60 11-01: bound kit without native stations (KV hard PHY wrappers) still gets FIRM relay sites
    import kit_istations as KI
    assert KI.relay_sites_only_tcl("t", {}) is None
    tcl = KI.relay_sites_only_tcl("t", {"relay_sites": {"u_bin_a/q": [432.0, 1440.0]}})
    assert "proc rs_place_all" in tcl and "rs_place_all [dict create {u_bin_a/q} {432 1440}]" in tcl
    assert tcl.index("set is_fh [open") < tcl.index("rs_place_all [dict") < tcl.index("close $is_fh")


def test_relay_sites_ring_keys_post_landing():
    # CODEX-PICKUP-KV 11-01: ring-flop keys (u_cland_*) leave the pre-landing call and run after the landing hook
    import kit_istations as KI
    t = {"relay_sites": {"u_slg.xe0[0]": [509.49, 970.11], "u_cland_i_e/u_ring.dch[0].u_dsel/y[0]": [619.46, 1501.74]}}
    tcl = KI.relay_sites_only_tcl("t", t)
    assert "rs_place_all [dict create {u_slg.xe0[0]} {509.49 970.11}]" in tcl and "u_cland_" not in tcl
    post = KI.relay_sites_post_tcl("t", t)
    assert post.startswith("uplevel #0 {") and "set is_fh [open" in post and post.rstrip().endswith("}")
    assert "rs_place_all [dict create {u_cland_i_e/u_ring.dch[0].u_dsel/y[0]} {619.46 1501.74}]" in post
    assert post.index("set is_fh [open") < post.index("rs_place_all") < post.index("close $is_fh")
    assert KI.relay_sites_post_tcl("t", {"relay_sites": {"u_slg.xe0[0]": [1, 2]}}) is None
    only_ring = KI.relay_sites_only_tcl("t", {"relay_sites": {"u_cland_a/y[0]": [1, 2]}})
    assert "proc rs_place_all" in only_ring and "rs_place_all [dict" not in only_ring
