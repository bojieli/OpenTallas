import os
"""KV-G3 10-24: kit_istations.py inserts len(regs_um) stations on an in bus, re-points the leaf reader, and writes
FIRM sites for the stations and sited plan cells."""
import json
import pytest
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


def test_soft_bus_channel_changes_station_sites_without_changing_rtl(tmp_path):
    entry = dict(conn="bus:i_a", from_um=[0, 10], to_um=[80, 55], regs_um=[[40, 10]],
                 bit_route="per_bit", leaf_um=[80, 55])
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="i_a", dir="in", width=1, kind="data", face="W")],
        internal_stations=[entry])))
    pf = tmp_path / "plan.json"
    proof = {}
    for form in ("ordinary", "channel", "missing per-bit route"):
        kd = tmp_path / form
        kd.mkdir()
        bound = kd / "t_part_bound.sv"
        bound.write_text(BOUND)
        (kd / "kit_rtl.json").write_text(json.dumps(dict(
            bound_module="t_part_bound", files=[str(bound)])))
        pf.write_text(json.dumps(plan))
        result = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                                capture_output=True, text=True)
        if form == "missing per-bit route":
            assert result.returncode != 0
            assert "requires a per-bit bus chain" in result.stderr
            continue
        assert result.returncode == 0, result.stderr
        proof[form] = (bound.read_text(), (kd / "istations.tcl").read_text())
        if form == "ordinary":
            entry.update(leg_order="channel", channel_um=[24, 48])
        else:
            del entry["bit_route"]
    assert proof["channel"][0] == proof["ordinary"][0]
    assert "is_bits u_ist_i_a_0 i_a W 1 80 55 0 1 in ist:i_a 0" in proof["ordinary"][1]
    assert "is_chan_bits u_ist_i_a_0 i_a W 1 80 55 0 1 in ist:i_a 24.0000 48.0000 0" in proof["channel"][1]


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
    assert r.returncode != 0 and "CS_" in r.stderr and "--apply sets" in r.stderr


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


def test_core_unequal_counts_take_the_deepest(tmp_path):
    """KW-FIX-27: one interface is one chain; its depth is the deepest entry, sited from the deepest entries"""
    p = _core_plan()
    p["partition_types"]["t"]["internal_stations"][4]["regs_um"].append([1.0, 1.0])   # lane 2 hi: 3 stages
    r, kd = _run_core(tmp_path, p, "--apply")
    assert r.returncode == 0, r.stderr
    rows = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    core = next(x for x in rows if "core_classes" in x)
    assert core["core_classes"]["hi"]["stages"] == 3 and "merged_depths" in core


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
    assert r.returncode == 0, r.stderr     # KW-FIX-27: reported, no RTL stage to site; sign-off judges the hop
    rows = json.loads((tmp_path / "kit" / "kit_rtl.json").read_text())["kit_istations"]
    assert any(x.get("core_unmapped") == [bad["conn"]] for x in rows)
    (tmp_path / "kit" / "istations.tcl").unlink()
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


# ---- DIE-S81-70 11-06: flat native kv_leaf binds (stations bound at the slice LF_CS_* depths, counted, flat globs)
def _flat_bound(hi=1, ho=1, y=1, extra=""):
    regs = []
    for l in range(16):
        regs.append(f"    wire [1:0] w_u_vp_g_ln_{l}_u_cst_hi_0_Y;")
        regs.append(f"    wire [1:0] w_u_vp_g_ln_{l}_u_cst_ho_0_Y;")
        for j in range(hi):
            regs.append(f"    always @(posedge clk) g_u_vp_g_ln_{l}_u_cst_hi_gd_s_{j}_u_q <= 1'b0;")
        for j in range(ho):
            regs.append(f"    always @(posedge clk) g_u_vp_g_ln_{l}_u_cst_ho_gd_s_{j}_u_q <= 1'b0;")
    for j in range(y):
        regs.append(f"    always @(posedge clk) g_u_cst_y_gd_s_{j}_u_q <= 1'b0;")
    return "module t_leaf_bound (input wire clk, input wire rst_n);\n" + "\n".join(regs) + extra + "\nendmodule\n"


def _run_native(tmp_path, plan, bound, *opts):
    kd = tmp_path / "kit"
    kd.mkdir(exist_ok=True)
    (kd / "t_leaf_bound.sv").write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_leaf_bound", files=[str(kd / "t_leaf_bound.sv")])))
    return _run_core(tmp_path, plan, *opts)


def test_native_flat_bind_depths_match_and_flat_sites(tmp_path):
    bound = _flat_bound(hi=1, ho=1, y=1)
    r, kd = _run_native(tmp_path, _core_plan(hi=1, ho=1), bound, "--apply")
    assert r.returncode == 0, r.stderr
    assert (kd / "t_leaf_bound.sv").read_text() == bound          # native: never re-parameterised
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_vp_g_ln_9_u_cst_hi_gd_s_0_u_*} 109.0 10.0 cst:hi" in tcl
    assert "is_place {*u_vp_g_ln_9_u_cst_ho_gd_s_0_u_*} 209.0 5.0 cst:ho" in tcl
    assert "is_place {*u_cst_y_gd_s_0_u_*} 50.015 60.015 cst:y" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert any(x.get("bind") == "native_flat" for x in rep)


def test_native_flat_bind_depth_differs_is_reported(tmp_path):
    """KW-FIX-27: a flat bind's depth is the bound RTL; its count cannot stop a build (hash-renamed regs count 0)"""
    r, kd = _run_native(tmp_path, _core_plan(hi=2, ho=1), _flat_bound(hi=1, ho=1, y=1), "--apply")
    assert r.returncode == 0, r.stderr
    core = next(x for x in json.loads((kd / "kit_rtl.json").read_text())["kit_istations"] if "core_classes" in x)
    assert core["native_depth_differs"]["CS_HI_D"] == dict(plan=2, counted=1)


def test_native_flat_mark_takes_the_leaf_instance_prefix():
    sys.path.insert(0, str(HERE))
    import kit_istations
    assert kit_istations.NATIVE_MARK.search("wire w_u_lf3_u_vp_g_ln_9_u_cst_hi_0_Y;")
    assert kit_istations.NATIVE_MARK.search("wire w_u_vp_g_ln_9_u_cst_ho_0_Y;")


OUT_BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire a, output wire [1:0] o);
    wire o_ea;
    ot_dp_st #(.W(1)) u_bout_o (.clk(clk), .rst_n(rst_n), .d(a), .ea(o_ea), .q(o[0]), .eq(o[1]));
endmodule
"""


def _bus_run(tmp_path, bus_dir, bound, entries):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(dict(partition_types=dict(t=dict(
        buses=[dict(name="o", dir=bus_dir, width=1, kind="data")], internal_stations=entries)))))
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)], capture_output=True, text=True)
    return kd, r


def test_out_bus_deeper_later_entry_is_one_chain(tmp_path):
    """KW-FIX-27 (S81 leafup_o0 depths 1,1,2): one chain at the deepest entry, stage 0 sited on the leaf side"""
    far = dict(conn="bus:o", launch="face bus o", bits=4, regs_um=[[10, 0], [20, 0]])
    near = dict(conn="bus:o", launch="face bus o", bits=1, regs_um=[[99, 99]])
    kd, r = _bus_run(tmp_path, "out", OUT_BOUND, [near, near, far, near])
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert sv.count("u_ist_o_0 (") == 1 and sv.count("u_ist_o_1 (") == 1 and ".d(o_is1_q)" in sv and ".d(o_is0_q)" in sv
    rows = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert len(rows) == 1 and rows[0]["planned"] == 2 and rows[0]["stations"] == ["u_ist_o_0", "u_ist_o_1"]
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_ist_o_0[./]*} 20.0 0.0 ist:o" in tcl and "is_place {*u_ist_o_1[./]*} 10.0 0.0 ist:o" in tcl


def test_native_flat_bind_unplanned_station_is_reported(tmp_path):
    bound = _flat_bound(hi=1, ho=1, y=1, extra="\n    always @(posedge clk) g_u_cst_sw_gd_s_0_u_q <= 1'b0;")
    r, kd = _run_native(tmp_path, _core_plan(hi=1, ho=1), bound)
    assert r.returncode == 0, r.stderr
    core = next(x for x in json.loads((kd / "kit_rtl.json").read_text())["kit_istations"] if "core_classes" in x)
    assert core["native_depth_differs"]["CS_SW_D"] == dict(plan=0, counted=1)


# DIE-S81-71 11-06: col_h9/h10 st -> t0 stations (A1) are realised by the col RTL (cst_st_s* reset chain) and only
# counted + sited here; a bound text without the chain (or with another depth) is reported (KW-FIX-27).
COL_BOUND = """module col_part_bound (input wire ck_r0, input wire lpr_c_u_t0, input wire [1:0] st, output wire [1:0] so);
    reg [1:0] u_r0_cst_st_s0; always @(posedge ck_r0 or negedge lpr_c_u_t0) if (!lpr_c_u_t0) u_r0_cst_st_s0 <= 2'b00; else u_r0_cst_st_s0 <= st;
    reg [1:0] u_r0_cst_st_s1; always @(posedge ck_r0 or negedge lpr_c_u_t0) if (!lpr_c_u_t0) u_r0_cst_st_s1 <= 2'b00; else u_r0_cst_st_s1 <= u_r0_cst_st_s0;
    assign so = u_r0_cst_st_s1;
endmodule
"""
# 9615a697f7/c62b845496: _col_chain resolves a chain only between the actual source and target instances
# (their .st / .c0 expressions), never from globally named cst_st_s* registers: the fixtures carry both.
COL_BOUND_NO_INST = COL_BOUND
COL_BOUND = COL_BOUND.replace("    assign so = u_r0_cst_st_s1;\n",
    "    assign so = u_r0_cst_st_s1;\n    ot_src u_u_r0_u_s0 (.st(st));\n    ot_tgt u_u_r0_u_t0 (.c0(u_r0_cst_st_s1));\n")


def _col_run(tmp_path, depth, bound):
    regs = [[648.108, 172.812], [933.228, 172.812]][:depth]
    ent = [dict(conn="core:u_r0.u_s0.st|core:u_r0.u_t0", launch="u_r0.u_s0.st", capture=cap, regs_um=regs,
                from_um=[362.988, 172.812], to_um=[1140.588, 250.572]) for cap in ("u_r0.u_t0", "u_r0.u_t0.c0")]
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(dict(partition_types=dict(col=dict(buses=[], internal_stations=ent)))))
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "col_part_bound.sv").write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="col_part_bound", files=[str(kd / "col_part_bound.sv")])))
    return kd, subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "col", str(kd)],
                              capture_output=True, text=True)


def test_col_st_stations_counted_and_sited(tmp_path):
    kd, r = _col_run(tmp_path, 2, COL_BOUND)
    assert r.returncode == 0, r.stderr
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_r0_cst_st_s0*} 648.108 172.812 cst:st" in tcl
    assert "is_place {*u_r0_cst_st_s1*} 933.228 172.812 cst:st" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert rep == [dict(col_st=dict(stages=2, entries=2, regs=["u_r0_cst_st_s0", "u_r0_cst_st_s1"],
                                  sites=[[648.108, 172.812], [933.228, 172.812]]))]
    assert (kd / "col_part_bound.sv").read_text() == COL_BOUND


def _col_receipt(kd):
    return json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]["col_st"]


def test_col_st_stations_depth_differs_is_reported(tmp_path):
    kd, r = _col_run(tmp_path, 1, COL_BOUND)
    assert r.returncode == 0, r.stderr
    assert _col_receipt(kd)["bound_stages"] == 2


def test_col_st_stations_missing_rtl_is_reported(tmp_path):
    """an older bind without the chain: builds as bound, sign-off judges the hop"""
    kd, r = _col_run(tmp_path, 2, COL_BOUND_NO_INST.replace("cst_st_s", "xx_s"))
    assert r.returncode == 0, r.stderr
    assert _col_receipt(kd)["bound_stages"] == 0


# As bound: the bind re-expresses the stages as src-hash regs; the depth is counted along the chain into u_t0.c0.
COL_BOUND_B = """module col_part_bound (input wire ck, input wire rs, input wire [1:0] w_u_r0_u_s0_st, output wire [1:0] so);
    wire [1:0] w_u_r0_src_bbb_Q;
    wire [1:0] w_u_r0_src_aaa_Q;
    reg [1:0] g_u_r0_src_aaa_q;
    assign w_u_r0_src_aaa_Q = g_u_r0_src_aaa_q;
    always @(posedge ck or negedge rs)
        if (!rs) g_u_r0_src_aaa_q <= {2{1'b0}}; else g_u_r0_src_aaa_q <= w_u_r0_src_bbb_Q[1:0];  // x.sv:2.302
    reg [1:0] g_u_r0_src_bbb_q;
    assign w_u_r0_src_bbb_Q = g_u_r0_src_bbb_q;
    always @(posedge ck or negedge rs)
        if (!rs) g_u_r0_src_bbb_q <= {2{1'b0}}; else g_u_r0_src_bbb_q <= w_u_r0_u_s0_st[1:0];  // x.sv:2.162
    ot_src u_u_r0_u_s0 (.st(w_u_r0_u_s0_st[1:0]));
    ot_s81_sstn_base566 u_u_r0_u_t0 (
        .c0(w_u_r0_src_aaa_Q[1:0]),
        .so(so)
    );
endmodule
"""


def test_col_st_stations_bound_chain(tmp_path):
    kd, r = _col_run(tmp_path, 2, COL_BOUND_B)
    assert r.returncode == 0, r.stderr
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*g_u_r0_src_bbb_q*} 648.108 172.812 cst:st" in tcl
    assert "is_place {*g_u_r0_src_aaa_q*} 933.228 172.812 cst:st" in tcl


def test_col_st_stations_bound_chain_depth_differs_is_reported(tmp_path):
    kd, r = _col_run(tmp_path, 1, COL_BOUND_B)
    assert r.returncode == 0, r.stderr
    assert _col_receipt(kd)["bound_stages"] == 2


def _packed_txt(w, d):
    return (f"module m(input clk, input rst_n);\n"
            f"    ot_dp_st #(.W({w})) u_bin_a (.clk(clk), .rst_n(rst_n), .d(x), .ea(y), .q(a_b), .eq(a_eb));\n"
            f"    ot_dp_dly #(.W({w + 1}), .D({d})) u_lpad_a (.clk(clk), .d({{a_eb, a_b}}), .q({{a_eq, a_q}}));\n"
            f"endmodule\n")


def test_packed_channel_seats_existing_depth(tmp_path):
    kt = tmp_path / "k"
    kt.mkdir()
    bound = kt / "m.sv"
    rtl = _packed_txt(8, 3)
    bound.write_text(rtl)
    (kt / "kit_rtl.json").write_text(json.dumps(dict(bound_module="m", files=[str(bound)])))
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="a", dir="in", width=8, kind="data", face="E")],
        internal_stations=[dict(conn="bus:a", from_um=[180, 30], to_um=[64, 80], regs_um=[[110, 30]],
                                bit_route="per_bit", leaf_um=[64, 80], leg_order="channel", channel_um=[85, 120])])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kt)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert bound.read_text() == rtl
    tcl = (kt / "istations.tcl").read_text()
    assert "is_chan_packed_bits u_lpad_a a E 8 64 80 3 ist:a 85.0000 120.0000" in tcl
    receipt = json.loads((kt / "kit_rtl.json").read_text())["kit_istations"][0]
    assert (receipt["bound_pads"], receipt["channel_stages"], receipt["inserted"]) == (3, 3, 0)


def test_packed_delay_deeper_than_plan_pins_first_sites_only():
    import kit_istations as K
    bus = dict(name="a", dir="in", width=8)
    got = K.packed_input_delay("T", bus, _packed_txt(8, 9), 8, 7)
    assert got["depth"] == 9 and len(got["stage_registers"]) == 9
    assert K.packed_input_delay("T", bus, _packed_txt(8, 7), 8, 7)["depth"] == 7


def test_packed_delay_wrong_width_still_fails():
    import kit_istations as K
    bus = dict(name="a", dir="in", width=8)
    for txt in (_packed_txt(9, 9), _packed_txt(8, 0)):
        try:
            K.packed_input_delay("T", bus, txt, 8, 7)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_packed_delay_shallower_than_plan_is_the_bound_depth():
    # DIE-HBM-91-KCLS 11-08 (class l): HBM q_hub L12s_i D12 vs 34 planned; the bound, priced depth wins
    import kit_istations as K
    bus = dict(name="a", dir="in", width=8)
    got = K.packed_input_delay("T", bus, _packed_txt(8, 6), 8, 7)
    assert got["depth"] == 6 and len(got["stage_registers"]) == 6


def test_packed_sites_respread():
    import kit_istations as K
    regs = [[float(i), 0.0] for i in range(34)]
    sites = K.packed_sites(regs, 12)
    ks = [k for _, k in sites]
    assert [j for j, _ in sites] == list(range(12))
    assert ks == sorted(set(ks)) and 0 <= ks[0] and ks[-1] < 34      # strictly increasing, on planned sites
    gaps = [b - a for a, b in zip([-1] + ks, ks + [34])]
    assert max(gaps) - min(gaps) <= 1                                 # near-equal hop groups
    assert K.packed_sites(regs[:7], 9) == [(j, j) for j in range(7)]  # deeper: first sites in order (KW-FIX-27)
    assert K.packed_sites(regs[:8], 6) == [(0, 0), (1, 2), (2, 3), (3, 4), (4, 5), (5, 7)]


def test_per_bit_station_places_scalar_payload_and_epoch(tmp_path):
    import shutil
    import kit_istations as K

    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    start = K.TCL_HEAD.index("proc is_bits ")
    end = K.TCL_HEAD.index("# D-QC-FE-REACH", start)
    f = tmp_path / "scalar.tcl"
    f.write_text(K.TCL_HEAD[start:end] + r"""
proc ff_put_near {i x y} { return [list $x $y] }
proc is_knee_site {x y args} { return [list $x $y] }
proc cell_a {arg} { if {$arg eq "getName"} { return {u_bound.u_ist_arm_eo_3/q$_DFF_P_} }; return master }
proc cell_b {arg} { if {$arg eq "getName"} { return {u_bound.u_ist_arm_eo_3/eq$_DFF_PN0_} }; return master }
proc master {arg} { return DFFHQNx1 }
proc block {arg} { return {cell_a cell_b} }
set ff_blk block; set ff_dbu 1000; set is_fh stdout; set is_miss {}; set is_n 0
is_bits u_ist_arm_eo_3 arm_eo W 1 300 600 3 4 out ist:arm_eo 0 {0 7 10 1 8 20}
if {$is_n != 2 || [llength $is_miss]} { error "failed to place both scalar station bits: $is_miss" }
""")
    result = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True)
    assert [row.split("\t")[2:4] for row in result.stdout.splitlines()] == [["7.0", "10.0"], ["8.0", "20.0"]]


RELAY_SEP_MOCK = r"""
proc ff_put_near {i x y} { return [list $x $y] }
set ::insts {}; set n 0
foreach nm {{u_bound.u_twb.q\[3\]$_DFF_P_} {u_bound.u_a/q\[0\]$_DFF_P_} {u_bound.u_x.r\[1\]$_DFF_P_} {u_bound.u_amb.q$_DFF_P_}} {
  set c ::ins[incr n]
  proc $c {cmd} [format {if {$cmd eq "getName"} { return %s }; return ::mas} [list $nm]]
  lappend ::insts $c
}
proc ::blk {cmd} { return $::insts }
proc ::mas {cmd} { return DFFHQNx1 }
set ff_blk ::blk; set ff_dbu 1000; set is_fh stdout; set is_miss {}
"""


def test_relay_sites_match_separator_blind_when_the_exact_name_is_absent(tmp_path):
    """RELAY-SEP (FABLE-FIX-QC 11-18): QC su_c x3 plan keys u_u_suvm_u_vm8q_u_twb/q[N] against flops u_bound.u_u_suvm_u_vm8q_u_twb.q[N]:
    1,034 of 1,034 keys matched nothing.  '/' and '.' are one separator when the exact name finds no key; exact names still win and an
    ambiguous separator-blind name is not used."""
    import shutil
    import kit_istations as KI
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    assert "string map {/ .} $k" in KI.RELAY_TCL and "RELAY-SEP" in KI.RELAY_TCL
    f = tmp_path / "t.tcl"
    f.write_text(RELAY_SEP_MOCK + KI.RELAY_TCL +
                 "\nrs_place_all [dict create {u_twb/q[3]} {1 2} {u_a/q[0]} {3 4} {u_x/r[1]} {5 6} {u_amb/q} {7 8} {u_amb.q} {9 9} {u_gone/q} {0 0}]\n")
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout
    got = {r[0]: (float(r[2]), float(r[3])) for r in (ln.split("\t") for ln in out.splitlines()) if len(r) > 3 and r[1] == "relay"}
    assert got[r"u_bound.u_twb.q\[3\]$_DFF_P_"] == (1.0, 2.0)          # '/' key, '.' flop
    assert got[r"u_bound.u_a/q\[0\]$_DFF_P_"] == (3.0, 4.0)            # exact, as before
    assert got[r"u_bound.u_x.r\[1\]$_DFF_P_"] == (5.0, 6.0)
    assert got[r"u_bound.u_amb.q$_DFF_P_"] == (9.0, 9.0)               # the exact key wins over the separator-blind one
    assert "plan keys unmatched: 2 of 6" in out                            # u_gone/q and the unused u_amb/q


RELAY_IDX_MOCK = r"""
proc ff_put_near {i x y} { return [list $x $y] }
# netlist: name master {pin dir net ...}
set ::nl {
  {u_bound.u_g.u_crg.g_rl.r\[0\]$_DFF_PN0_} DFFASRHQNx1 {D in nd QN out n1}
  i1 INVx1 {A in n1 Y out n2}
  {u_bound.u_g.u_crg.q$_DFF_PN0_} DFFASRHQNx1 {D in n2 QN out n3}
  {u_bound.u_k.x$_DFF_P_} DFFHQNx1 {D in n3 QN out n4}
  g1 NAND2x1 {A in n3 B in n4 Y out n5}
  {u_bound.u_h.r\[0\]$_DFF_P_} DFFHQNx1 {D in n6 QN out n7}
  {u_bound.u_h.s0$_DFF_P_} DFFHQNx1 {D in n7 QN out n8}
  {u_bound.u_h.s1$_DFF_P_} DFFHQNx1 {D in n7 QN out n9}
}
set ::insts {}; set ::nets [dict create]; set n 0
foreach {nm m pins} $::nl {
  set c ::ins[incr n]; set its {}
  foreach {p d w} $pins {
    set t ::it[incr n]
    proc $t {cmd} [format {switch -- $cmd { isOutputSignal {return %d} isInputSignal {return %d} getNet {return ::net_%s} getInst {return %s} }} [expr {$d eq "out"}] [expr {$d eq "in"}] $w $c]
    lappend its $t; dict lappend ::nets $w $t
  }
  proc $c {cmd} [format {switch -- $cmd { getName {return %s} getMaster {return ::m_%s} getITerms {return %s} }} [list $nm] $m [list $its]]
  proc ::m_$m {cmd} [format {return %s} $m]
  lappend ::insts $c
}
dict for {w ts} $::nets { proc ::net_$w {cmd} [format {return %s} [list $ts]] }
proc ::blk {cmd} { return $::insts }
set ff_blk ::blk; set ff_dbu 1000; set is_fh stdout; set is_miss {}
"""


def test_relay_sites_index_key_sites_the_aliased_last_stage(tmp_path):
    """RELAY-IDX (FABLE-FIX-S81-LEPE 11-20): S81 lep u_crg `reg [1:0] r; assign q = r[1]` synthesises to flops g_rl.r[0] and u_crg.q,
    so the plan key u_crg.g_rl.r[1] matched nothing.  NAME[k] now sites the only flop NAME[k-1] reaches through buffers / inverters;
    a stage that also feeds logic, or two flops, is not a shift stage and stays unmatched."""
    import shutil
    import kit_istations as KI
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    f = tmp_path / "t.tcl"
    f.write_text(RELAY_IDX_MOCK + KI.RELAY_TCL + "\nrs_place_all [dict create {u_g.u_crg.g_rl.r[0]} {1 2} {u_g.u_crg.g_rl.r[1]} {3 4} "
                 "{u_g.u_crg.g_rl.r[2]} {5 6} {u_h.r[0]} {7 8} {u_h.r[1]} {9 9} {u_k.x} {2 2}]\n")
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout
    got = {r[0]: (float(r[2]), float(r[3])) for r in (ln.split("\t") for ln in out.splitlines()) if len(r) > 3 and r[1] == "relay"}
    assert got[r"u_bound.u_g.u_crg.g_rl.r\[0\]$_DFF_PN0_"] == (1.0, 2.0)      # exact name, as before
    assert got[r"u_bound.u_g.u_crg.q$_DFF_PN0_"] == (3.0, 4.0)                # r[1] = the stage after r[0] (through an inverter)
    assert got[r"u_bound.u_k.x$_DFF_P_"] == (2.0, 2.0)                        # placed by its own key: r[2] never re-sites it
    assert r"u_bound.u_h.s0$_DFF_P_" not in got and r"u_bound.u_h.s1$_DFF_P_" not in got   # r[0] fans to two flops: no stage
    assert "RELAY-IDX: 1 keys" in out and "plan keys unmatched: 2 of 6" in out


def test_counted_receiver_delay_preserves_payload_and_epoch_sites():
    import kit_istations as K

    text = (_packed_txt(8, 6).split("    ot_dp_dly", 1)[0]
            + "    ot_dp_dly_cnt #(.W(9), .DMAX(6)) u_lpad_a "
              "(.clk(clk), .strap_cnt(strap_r8pad_lane_a), .d({a_eb, a_b}), .q(a_lane_pad_q));\n"
              "    assign {a_eq, a_q} = a_lane_pad_q;\nendmodule\n")
    bus = dict(name="a", dir="in", width=8)
    packed = K.packed_input_delay("T", bus, text, 8, 2)
    assert packed["master"] == "ot_dp_dly_cnt"
    assert packed["stage_registers"] == [f"u_lpad_a.r[{i}]" for i in range(6)]
    with pytest.raises(ValueError, match="expected payload and epoch"):
        K.packed_input_delay("T", bus, text.replace("{a_eq, a_q}", "{a_q, a_eq}"), 8, 2)


RELAY_INST_MOCK = r"""
proc ff_put_near {i x y} { return [list $x $y] }
set ::insts {}; set n 0
foreach nm {{u_bound.u_y_xd_u_bn8_e_r0_0_0.q\[0\]$_DFF_P_} {u_bound.u_y_xd_u_bn8_e_r0_0_0.q\[26\]$_DFF_P_} {u_bound.u_y_xd_u_bn8_e_r0_0_0.u_deep.r\[0\]$_DFF_P_}
            {u_bound.u_lpad_i1.q\[5\]$_DFF_P_} {u_bound.u_lpad_i1.q\[6\]$_DFF_P_} {u_bound.u_other.q\[0\]$_DFF_P_}} {
  set c ::ins[incr n]
  proc $c {cmd} [format {if {$cmd eq "getName"} { return %s }; return ::mas} [list $nm]]
  lappend ::insts $c
}
proc ::blk {cmd} { return $::insts }
proc ::mas {cmd} { return DFFHQNx1 }
set ff_blk ::blk; set ff_dbu 1000; set is_fh stdout; set is_miss {}
"""


def test_relay_sites_instance_key_seats_every_register_of_the_station(tmp_path):
    """RELAY-INST (FABLE-FIX-S81-COLROM-R5 11-21): S81 J7 col plan rows key a whole stage station (u_y_xd_u_bn8_e_r0_0_0), the flops are
    <station>.q[N]: 140 of 166 keys matched nothing on col_h10_r1 and relay_mid.tcl moved 27 stations up to 409 um off the seat.
    An instance key seats all registers directly in it; a flop-name key still wins; deeper instances and other stations are untouched."""
    import shutil
    import kit_istations as KI
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    assert "RELAY-INST" in KI.RELAY_TCL
    f = tmp_path / "t.tcl"
    f.write_text(RELAY_INST_MOCK + KI.RELAY_TCL +
                 "\nrs_place_all [dict create {u_y_xd_u_bn8_e_r0_0_0} {365.064 943.84} {u_lpad_i1} {1 1} {u_lpad_i1.q[5]} {7 8} {u_gone} {0 0}]\n")
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout
    got = {r[0]: (float(r[2]), float(r[3])) for r in (ln.split("\t") for ln in out.splitlines()) if len(r) > 3 and r[1] == "relay"}
    assert got[r"u_bound.u_y_xd_u_bn8_e_r0_0_0.q\[0\]$_DFF_P_"] == (365.064, 943.84)
    assert got[r"u_bound.u_y_xd_u_bn8_e_r0_0_0.q\[26\]$_DFF_P_"] == (365.064, 943.84)
    assert r"u_bound.u_y_xd_u_bn8_e_r0_0_0.u_deep.r\[0\]$_DFF_P_" not in got          # one level only
    assert got[r"u_bound.u_lpad_i1.q\[5\]$_DFF_P_"] == (7.0, 8.0)                      # its own flop key wins
    assert got[r"u_bound.u_lpad_i1.q\[6\]$_DFF_P_"] == (1.0, 1.0)                      # the rest of the instance: the instance key
    assert r"u_bound.u_other.q\[0\]$_DFF_P_" not in got
    assert "RELAY-INST: 3 flops of 2 instance keys" in out
    assert "plan keys unmatched: 1 of 4" in out                                        # u_gone


RELAY_NORM_MOCK = r"""
proc ff_put_near {i x y} { return [list $x $y] }
set ::insts {}; set n 0
foreach nm {{u_bound.u_u_lf0_u_crr_rxsb/q$_DFF_PN0_} {u_bound.u_u_lf0_u_vp_u_rr.rst_n\[10\]$_DFF_PN0_} {u_bound.u_u_fab_u_x_2_2.u_st.g_seg\[0\].run$_DFF_P_}
            {u_bound.u_u_fab_u_x_2_2.u_st.g_seg\[0\].cap\[0\]$_DFF_P_} {u_bound.u_u_fab_u_x_2_2.u_st.g_seg\[1\].cap\[0\]$_DFF_P_} {u_bound.u_u_plain.q$_DFF_P_}} {
  set c ::ins[incr n]
  proc $c {cmd} [format {if {$cmd eq "getName"} { return %s }; return ::mas} [list $nm]]
  lappend ::insts $c
}
proc ::blk {cmd} { return $::insts }
proc ::mas {cmd} { return DFFHQNx1 }
set ff_blk ::blk; set ff_dbu 1000; set is_fh stdout; set is_miss {}
"""


def _relay_tcl(tmp_path, mock, call, **env):
    import kit_istations as KI
    f = tmp_path / "t.tcl"
    f.write_text(mock + KI.RELAY_TCL + "\n" + call + "\n")
    e = dict(os.environ); e.pop("OT_RELAY_SITES_UNMATCHED_MAX", None); e.pop("RESULTS_DIR", None); e.update(env)
    return subprocess.run(["tclsh", str(f)], capture_output=True, text=True, env=e)


def test_relay_sites_normalised_names_leaf_prefix_and_generate_scope(tmp_path):
    """RELAY-NORM (FABLE-FIX-S81-COLROM-R5 11-21): S81 ot_s81sl_leaf keys u_u_crr_rxsb/q against flops u_u_lf0_u_crr_rxsb/q (25 of 25 keys
    unmatched on 20 placed kits); QC cb keys u_st.run against u_st.g_seg[0].run.  A normalised name shared by two flops (g_seg[0].cap[0] and
    g_seg[1].cap[0] against the key u_st.cap[0]) is no RELAY-NORM match; RELAY-SEG seats both copies at the key's site."""
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    r = _relay_tcl(tmp_path, RELAY_NORM_MOCK, "rs_place_all [dict create {u_u_crr_rxsb/q} {1 2} {u_u_vp_u_rr.rst_n[10]} {3 4} "
                   "{u_u_fab_u_x_2_2.u_st.run} {5 6} {u_u_fab_u_x_2_2.u_st.cap[0]} {7 8} {u_u_plain.q} {9 9}]")
    assert r.returncode == 0, r.stderr
    got = {x[0]: (float(x[2]), float(x[3])) for x in (ln.split("\t") for ln in r.stdout.splitlines()) if len(x) > 3 and x[1] == "relay"}
    assert got[r"u_bound.u_u_lf0_u_crr_rxsb/q$_DFF_PN0_"] == (1.0, 2.0)
    assert got[r"u_bound.u_u_lf0_u_vp_u_rr.rst_n\[10\]$_DFF_PN0_"] == (3.0, 4.0)
    assert got[r"u_bound.u_u_fab_u_x_2_2.u_st.g_seg\[0\].run$_DFF_P_"] == (5.0, 6.0)
    assert got[r"u_bound.u_u_plain.q$_DFF_P_"] == (9.0, 9.0)
    assert sum("cap" in k for k in got) == 2 and "RELAY-SEG: 2 segment registers of 1 keys" in r.stdout
    assert "RELAY-NORM: 3 keys" in r.stdout and "plan keys unmatched: 0 of 5" in r.stdout and "SEAT-MISS" not in r.stdout


def _seat_mock(names):
    body = " ".join("{" + n.replace("[", "\\[").replace("]", "\\]") + "$_DFF_P_}" for n in names)
    return RELAY_NORM_MOCK.replace(RELAY_NORM_MOCK[RELAY_NORM_MOCK.index("foreach nm {") + 12:RELAY_NORM_MOCK.index("} {\n  set c")], body)


def _seats(r):
    return {x[0].replace("\\", "").split("$")[0]: (float(x[2]), float(x[3]))
            for x in (ln.split("\t") for ln in r.stdout.splitlines()) if len(x) > 3 and x[1] == "relay"}


def test_relay_seg_slices_and_copies_of_a_segmented_station(tmp_path):
    """SEAT-MATCH-AUDIT 11-24: QC cb stations became ot_qfd_xcst_rep (4 g_seg): cap[0..7] of 4 x 2-bit segments = slices, cnt / run = one
    copy per segment at the key's site (10 types, 276 keys each matched nothing)."""
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    names = [f"u_bound.u_x.u_st.g_seg[{g}].{r}" for g in range(4) for r in ("cap[0]", "cap[1]", "cnt[0]", "cnt[1]", "run", "tag[0]")]
    rows = " ".join([f"{{u_x.u_st.cap[{i}]}} {{{i} 1}}" for i in range(8)] + ["{u_x.u_st.cnt[0]} {50 2}", "{u_x.u_st.cnt[1]} {51 2}",
                                                                              "{u_x.u_st.run} {60 3}"])
    r = _relay_tcl(tmp_path, _seat_mock(names), f"rs_place_all [dict create {rows}]")
    assert r.returncode == 0, r.stderr
    got = _seats(r)
    assert all(got[f"u_bound.u_x.u_st.g_seg[{i // 2}].cap[{i % 2}]"] == (i, 1) for i in range(8))
    assert all(got[f"u_bound.u_x.u_st.g_seg[{g}].cnt[1]"] == (51, 2) and got[f"u_bound.u_x.u_st.g_seg[{g}].run"] == (60, 3) for g in range(4))
    assert not any("tag" in k for k in got) and "plan keys unmatched: 0 of 11" in r.stdout
    # key family wider than the segments hold: not understood, stays a miss
    r = _relay_tcl(tmp_path, _seat_mock(names), "rs_place_all [dict create {u_x.u_st.cap[0]} {0 1} {u_x.u_st.cap[8]} {8 1}]")
    assert "plan keys unmatched: 2 of 2" in r.stdout and not _seats(r)


def test_relay_cnt_last_stage_and_pruned_bit(tmp_path):
    """SEAT-MATCH-AUDIT 11-24: sle_ctl u_lpad_x_su_l0_i became ot_dp_dly_cnt (r[0..5], no q register): q[b] seats r[5][b].  A live line
    whose one q bit synthesis pruned keeps its miss."""
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    names = [f"u_bound.u_lpad_c/r[{j}][{b}]" for j in range(6) for b in (3, 4)] + ["u_bound.u_lpad_d.q[0]", "u_bound.u_lpad_d.r[0][1]"]
    r = _relay_tcl(tmp_path, _seat_mock(names), "rs_place_all [dict create {u_lpad_c.q[3]} {1 2} {u_lpad_c.q[4]} {3 4} {u_lpad_d.q[0]} {5 6} {u_lpad_d.q[3]} {7 8}]")
    assert r.returncode == 0, r.stderr
    got = _seats(r)
    assert got == {"u_bound.u_lpad_c/r[5][3]": (1, 2), "u_bound.u_lpad_c/r[5][4]": (3, 4), "u_bound.u_lpad_d.q[0]": (5, 6)}
    assert "RELAY-CNT: 2 keys" in r.stdout and "SEAT-MISS WARNING 1 of 4 plan seat keys match no register (stop off): u_lpad_d.q[3]" in r.stdout


def test_relay_twin_spelling_is_not_a_miss(tmp_path):
    """SEAT-MATCH-AUDIT 11-24: QC st_a plans carry P/q AND P.q for the same 128 registers: one seat, no miss."""
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    r = _relay_tcl(tmp_path, _seat_mock(["u_bound.u_lob.q"]), "rs_place_all [dict create {u_lob/q} {1 2} {u_lob.q} {1 2}]")
    assert r.returncode == 0, r.stderr
    assert len(_seats(r)) == 1 and "plan keys unmatched: 0 of 2" in r.stdout and "SEAT-MISS" not in r.stdout


def test_relay_sites_unmatched_key_warns_by_default_and_stops_only_on_request(tmp_path):
    """SEAT-MISS (COORD 11-21, ruling: no new gate): a plan seat key that matches no register is listed and counted in the kit log, and the
    kit goes on (S81 J7 col: 140 of 166 keys were silently unseated; QC / bk_sel plans still carry rows for absent registers).
    OT_RELAY_SITES_UNMATCHED_STOP=1 makes it a stop above OT_RELAY_SITES_UNMATCHED_MAX (default 0); all matched = no line."""
    import shutil
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    call = "rs_place_all [dict create {u_u_plain.q} {9 9} {u_gone.q} {1 1} {u_gone2.q} {2 2}]"
    res = tmp_path / "res"; res.mkdir()
    r = _relay_tcl(tmp_path, RELAY_NORM_MOCK, call, RESULTS_DIR=str(res))
    assert r.returncode == 0, r.stderr                                                   # default: warning, the kit continues
    assert "SEAT-MISS WARNING 2 of 3 plan seat keys match no register (stop off): u_gone.q u_gone2.q" in r.stdout
    assert (res / "ot_relay_sites_unmatched.txt").read_text().split() == ["u_gone.q", "u_gone2.q"]
    assert "OT_RELAY_SITES BANK u_gone.q matched 0 unmatched 1" in r.stdout
    assert "CLASS SEAT-MISS: 2 of 3 plan seats (66.7 %) seat NOTHING, 2 banks, 2 wholly unseated" in r.stdout
    b = _relay_tcl(tmp_path, RELAY_NORM_MOCK, "rs_place_all [dict create {u_u_plain.q} {9 9} {u_pd11_x_fw_i_236.r[3]} {1 1} {u_pd11_x_fw_i_7.r[0]} {1 1} {u_k/q[4]} {2 2}]")
    assert b.returncode == 0, b.stderr                                                  # report only
    assert "BANK u_pd11_x_fw_i.r matched 0 unmatched 2" in b.stdout and "BANK u_k.q matched 0 unmatched 1" in b.stdout
    assert "CLASS SEAT-MISS: 3 of 4 plan seats (75.0 %) seat NOTHING, 2 banks, 2 wholly unseated; worst u_pd11_x_fw_i.r 0 2" in b.stdout
    import signoff as SO
    kit = tmp_path / "kit"; (kit / "run/results/asap7/d/base").mkdir(parents=True)
    assert SO.relay_sites_unmatched(kit) is None
    (kit / "run/results/asap7/d/base/ot_relay_sites_unmatched.txt").write_text("u_gone.q\nu_gone2.q\nu_gone.q\n")
    assert SO.relay_sites_unmatched(kit) == {"n": 2, "keys": ["u_gone.q", "u_gone2.q"]}
    r = _relay_tcl(tmp_path, RELAY_NORM_MOCK, call, OT_RELAY_SITES_UNMATCHED_STOP="1")
    assert r.returncode != 0
    assert "OT_RELAY_SITES SEAT-MISS: 2 of 3 plan relay_sites keys match no register (first: u_gone.q)" in r.stderr + r.stdout
    assert _relay_tcl(tmp_path, RELAY_NORM_MOCK, call, OT_RELAY_SITES_UNMATCHED_STOP="1", OT_RELAY_SITES_UNMATCHED_MAX="1").returncode != 0
    r = _relay_tcl(tmp_path, RELAY_NORM_MOCK, call, OT_RELAY_SITES_UNMATCHED_STOP="1", OT_RELAY_SITES_UNMATCHED_MAX="2")
    assert r.returncode == 0 and "SEAT-MISS WARNING 2 of 3" in r.stdout and "stop on, limit 2" in r.stdout
    r = _relay_tcl(tmp_path, RELAY_NORM_MOCK, "rs_place_all [dict create {u_u_plain.q} {9 9}]", OT_RELAY_SITES_UNMATCHED_STOP="1")
    assert r.returncode == 0 and "SEAT-MISS" not in r.stdout and "OT_RELAY_SITES BANK" not in r.stdout


def test_relay_seat_stop_gen_env_reaches_tcl_through_make(tmp_path, monkeypatch):
    import shutil
    import gen_phys as GP
    import kit_istations as KI

    if shutil.which("make") is None or shutil.which("tclsh") is None:
        pytest.skip("make and tclsh")

    stop = "OT_RELAY_SITES_UNMATCHED_STOP"
    limit = "OT_RELAY_SITES_UNMATCHED_MAX"
    for key in (stop, limit):
        monkeypatch.delenv(key, raising=False)
    flow_env = dict(os.environ)
    flow_env.pop("RESULTS_DIR", None)
    callback = tmp_path / "relay.tcl"
    callback.write_text(RELAY_NORM_MOCK + KI.RELAY_TCL
                        + "\nrs_place_all [dict create {u_u_plain.q} {9 9} {u_gone.q} {1 1}]\n")
    makefile = tmp_path / "Makefile"
    config = tmp_path / "config.mk"
    makefile.write_text("include config.mk\nall:\n\ttclsh relay.tcl\n")

    def run():
        config.write_text("\n".join(GP.gen_knob_cfg([])) + "\n")
        return subprocess.run(["make", "-s"], cwd=tmp_path, env=flow_env, capture_output=True, text=True)

    default = run()
    assert stop not in config.read_text() and limit not in config.read_text()
    assert default.returncode == 0 and "stop off" in default.stdout
    monkeypatch.setenv(stop, "1")
    strict = run()
    assert strict.returncode != 0 and "SEAT-MISS: 1 of 2" in strict.stderr
    assert GP.kit_effective_env()[stop] == "1"
    monkeypatch.setenv(limit, "1")
    tolerated = run()
    assert tolerated.returncode == 0 and "stop on, limit 1" in tolerated.stdout
    assert GP.kit_effective_env()[limit] == "1"
