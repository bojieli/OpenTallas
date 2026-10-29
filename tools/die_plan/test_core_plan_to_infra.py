import copy
import json

import pytest
import core_infra as CI
import core_plan_to_infra as C
import master_slice as MS

SW, SH = 0.054, 0.27
MASTERS = {"BUFx24_ASAP7_75t_R": (1.62, SH), "BUFx12f_ASAP7_75t_R": (0.972, SH), "BUFx8_ASAP7_75t_R": (0.648, SH),
           "BUFx4f_ASAP7_75t_R": (0.432, SH)}


def sites(tap_x=None, strap=(25.0, 25.12)):
    rows = [(4.32, 4.32 + k * SH, "R0" if k % 2 == 0 else "MX", 600) for k in range(120)]
    fixed = []
    if tap_x is not None:
        fixed = [(tap_x, r[1], tap_x + 0.108, r[1] + SH) for r in rows]
    return dict(row0=dict(x=4.32, y=4.32, site_w=SW, site_h=SH, nrows=len(rows), nsites=600), rows=rows, fixed=fixed,
                masters=dict(MASTERS), pg={"M5": [(strap[0], 4.31, strap[1], 36.73)], "M4": []})


def plan(stack=False, leaf_master="BUFx8_ASAP7_75t_R"):
    """root -> 2 branch -> 2 leaves (each 2 named sinks). stack=True puts both branch drivers on one xy."""
    b1 = [10.0, 20.0]; b2 = [10.0, 20.0] if stack else [30.0, 20.0]
    nodes = [["root", None, [20.0, 20.0], "BUFx24_ASAP7_75t_R", "entry"],
             ["T0_br", "root", b1, "BUFx12f_ASAP7_75t_R", "branch"],
             ["T1_br", "root", b2, "BUFx12f_ASAP7_75t_R", "branch"],
             ["T0", "T0_br", [10.0, 12.0], leaf_master, "leaf"],
             ["T1", "T1_br", [30.0, 12.0], leaf_master, "leaf"]]
    q = dict(mean=250.0, window=6.0, sink_min=245.0, sink_max=256.0, leaf_out_slew_max=50.0, leaf_slew_in_max=20.0)
    qf = dict(mean=200.0, window=6.0, sink_min=195.0, sink_max=206.0, leaf_out_slew_max=40.0, leaf_slew_in_max=15.0)
    return dict(name="t", entry=[20.0, 20.0], nodes_xy=nodes, frozen_masters={n[0]: n[3] for n in nodes},
                leaf_sinks={"T0": ["a/CLK", "b/CLK"], "T1": ["c/CLK"]}, TT=q, FF=qf)


def test_converts_and_compiles_through_core_infra():
    sl = C.convert(plan(), sites(), "tiny_core", outline=[37.8, 37.8])
    assert MS.validate(sl) == []
    p = CI.compile_slice(sl)
    t = p["core_tree"]
    assert [n["name"] for n in t["nodes"]] == ["mp_ck_root", "mp_ck_T0_br", "mp_ck_T1_br", "mp_ck_T0", "mp_ck_T1"]
    assert t["nodes"][0]["parent"] == "port:clk" and t["depth"] == 3
    assert sl["core_tree"]["load_balance"] == "joint_nldm_plan" and sl["clock_ndr"]["width_multiplier"] == 2
    tcl = CI.emit_tcl(sl)
    assert "ot_ci_clock_ndr {ot_core_ck_2w2s} 2 2" in tcl
    assert tcl.count("ot_ci_origin_assert") == 5 and "ot_ci_tree_sink {mp_ck_T1} {c/CLK}" in tcl
    assert CI.trunk_pg_clearance(sl, p)["verdict"] == "PASS"


def _boxes(sl):
    out = []
    for n, p in sl["cell_placements"].items():
        w = MASTERS[p["master"]][0]
        out.append((n, p["origin_um"][0], p["origin_um"][1], p["origin_um"][0] + w))
    return out


def test_stacked_drivers_get_distinct_legal_sites():
    sl = C.convert(plan(stack=True), sites(), "tiny_core", outline=[37.8, 37.8])
    b = _boxes(sl)
    for i, (n, x0, y, x1) in enumerate(b):
        assert abs((x0 - 4.32) / SW - round((x0 - 4.32) / SW)) < 1e-6          # site grid
        assert abs((y - 4.32) / SH - round((y - 4.32) / SH)) < 1e-6            # row grid
        for m, a0, yy, a1 in b[:i]:
            assert yy != y or x1 <= a0 + 1e-9 or a1 <= x0 + 1e-9, (n, m)
    assert sl["plan_conversion"]["displacement_um"]["max"] < 2.0


def test_avoids_fixed_tap_cells_and_m5_straps():
    sl = C.convert(plan(), sites(tap_x=9.936, strap=(29.9, 30.1)), "tiny_core", outline=[37.8, 37.8])
    for n, x0, y, x1 in _boxes(sl):
        assert x1 <= 9.936 + 1e-9 or x0 >= 9.936 + 0.108 - 1e-9, n
        cx = sl["cell_placements"][n]["centre_um"][0]
        assert not (29.9 - 0.024 <= cx <= 30.1 + 0.024), n


def test_deterministic():
    a = C.convert(plan(stack=True), sites(tap_x=9.936), "tiny_core", outline=[37.8, 37.8])
    b = C.convert(plan(stack=True), sites(tap_x=9.936), "tiny_core", outline=[37.8, 37.8])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_actual_hard_blockages_are_occupied_without_extra_halo(tmp_path):
    p = tmp_path / "sites.txt"
    p.write_text("ROW0 0 0 site_w .054 site_h .27 nrows 1 nsites 100 orient0 R0\n"
                 "ROW 0 0 R0 100\nMASTER BUFx8_ASAP7_75t_R .648 .27\n"
                 "BLOCKAGE 7 1.08 0 2.16 .27\n")
    data = C.read_sites(p)
    assert data["blockages"] == [(1.08, 0., 2.16, .27)]
    sm = C.SiteMap(data)
    # Exact touching remains legal. There is no macro-halo inflation.
    assert sm.free(0, 8, 12) and sm.free(0, 40, 12)
    assert not sm.free(0, 9, 12) and not sm.free(0, 39, 12)
    placed = sm.place("new", "BUFx8_ASAP7_75t_R", 1.62, .135)
    x = placed["origin_um"][0]
    assert x+.648 <= 1.08+1e-6 or x >= 2.16-1e-6
    # Mutant: dropping the record recreates the overlap at the desired site.
    data["blockages"] = []
    x0 = C.SiteMap(data).place("new", "BUFx8_ASAP7_75t_R", 1.62, .135)["origin_um"][0]
    assert x0 < 2.16 and x0+.648 > 1.08


@pytest.mark.parametrize("rect", ["0 0 1", "0 nan 1 2", "1 0 0 2"])
def test_bad_hard_blockage_fails_closed(tmp_path, rect):
    p = tmp_path / "sites.txt"
    p.write_text("BLOCKAGE 7 "+rect+"\n")
    with pytest.raises(C.ConvertError, match="BLOCKAGE"):
        C.read_sites(p)


def test_envelope_refused_unless_calibration():
    with pytest.raises(C.ConvertError, match="envelope"):
        C.convert(plan(leaf_master="BUFx4f_ASAP7_75t_R"), sites(), "tiny_core", outline=[37.8, 37.8])
    sl = C.convert(plan(leaf_master="BUFx4f_ASAP7_75t_R"), sites(), "tiny_core", outline=[37.8, 37.8], calibration=True)
    assert sl["plan_conversion"]["calibration"] is True


def test_refuses_unfrozen_or_changed_master():
    p = plan(); p["frozen_masters"]["T0"] = "BUFx24_ASAP7_75t_R"
    with pytest.raises(C.ConvertError, match="frozen"):
        C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])
    p = plan(); p["frozen_masters"] = None
    with pytest.raises(C.ConvertError, match="frozen"):
        C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])


def test_refuses_duplicate_sink_and_unknown_leaf():
    p = plan(); p["leaf_sinks"]["T1"] = ["a/CLK"]
    with pytest.raises(C.ConvertError, match="two leaves"):
        C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])
    p = plan(); p["leaf_sinks"]["T9"] = ["z/CLK"]
    with pytest.raises(C.ConvertError, match="not a plan node"):
        C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])


def test_out_of_band_model_refused_by_core_infra():
    p = plan(); p["TT"] = dict(p["TT"], sink_max=290.0)
    sl = C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])
    with pytest.raises(CI.InfraError, match="model target"):
        CI.emit_tcl(sl)


def test_pg_bands_block_a_rail_trunk():
    s = sites()
    pg = C.pg_obstructions(s)
    assert len(pg["M4"]) == len(s["rows"]) + 1 and pg["M5"] == [[25.0, 4.31, 25.12, 36.73]]
    sl = C.convert(plan(), s, "tiny_core", outline=[37.8, 37.8])
    sl2 = copy.deepcopy(sl)
    # move a branch centre exactly onto a row boundary (rail) and onto the strap: no clear L -> FAIL
    sl2["core_tree"]["nodes"][1]["xy_um"] = [25.06, 4.32 + 30 * SH]
    sl2["core_tree"]["nodes"][0]["xy_um"] = [10.0, 4.32 + 30 * SH]
    del sl2["cell_placements"]
    assert CI.trunk_pg_clearance(sl2, CI.compile_slice(sl2))["verdict"] == "FAIL"


# S81-CORE-LAT-R10: 12.3a v5.0 band = INFO (opt-in band_policy); window <= 20 + slew <= 80 still gate
def _oob(policy=None, **tt):
    p = plan(); p["TT"] = dict(p["TT"], **tt)
    sl = C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])
    if policy is not None:
        sl["core_tree"]["model_qualification"]["band_policy"] = policy
    return sl


def test_band_info_builds_out_of_band_and_reports_it():
    tcl = CI.emit_tcl(_oob("info", sink_min=268.0, sink_max=276.0, window=8.0))
    assert "# core latency band INFO TT: model leaf 268..276 window 8 (target 230..270: OUT; not a gate, 12.3a)" in tcl
    assert "# core latency band INFO FF: model leaf 195..206 window 6 (target 182.5..222.5: IN; not a gate, 12.3a)" in tcl
    assert "ot_ci_tree_begin" in tcl


def test_band_info_still_gates_window_and_slew():
    with pytest.raises(CI.InfraError, match="model target"):
        CI.emit_tcl(_oob("info", window=21.0))
    with pytest.raises(CI.InfraError, match="model target"):
        CI.emit_tcl(_oob("info", leaf_out_slew_max=81.0))
    p = plan(); p["FF"] = dict(p["FF"], window=20.5)
    sl = C.convert(p, sites(), "tiny_core", outline=[37.8, 37.8])
    sl["core_tree"]["model_qualification"]["band_policy"] = "info"
    with pytest.raises(CI.InfraError, match="model target FAIL/NOT RUN at FF"):
        CI.emit_tcl(sl)


def test_band_default_gate_unchanged_and_byte_identical():
    with pytest.raises(CI.InfraError, match="model target"):
        CI.emit_tcl(_oob(None, sink_max=290.0))
    with pytest.raises(CI.InfraError, match="model target"):
        CI.emit_tcl(_oob("gate", sink_max=290.0))
    base = CI.emit_tcl(_oob(None))
    assert "band INFO" not in base and base == CI.emit_tcl(_oob("gate"))
    info = CI.emit_tcl(_oob("info")).splitlines(keepends=True)
    assert sum("band INFO" in l for l in info) == 2
    assert "".join(l for l in info if "band INFO" not in l) == base


def test_band_unknown_policy_refused():
    with pytest.raises(CI.InfraError, match="band_policy"):
        CI.emit_tcl(_oob("off"))


def test_cut_rows_use_their_own_origin_width_and_fixed_occupancy():
    ss=sites(strap=(200,200.12))
    ss["rows"]=[(4.32,4.32,"R0",20),(20.52,4.32,"R0",40),(4.32,4.59,"MX",600)]
    ss["row0"].update(nsites=20,nrows=3)
    ss["fixed"]=[(20.52,4.32,20.628,4.59)]
    sm=C.SiteMap(ss)
    assert not sm.free(0,20,1) and sm.free(2,100,20)
    assert not sm.free(1,0,2) and sm.free(1,3,2)
    p=sm.place("upper","BUFx8_ASAP7_75t_R",15.0,4.725)
    assert abs(p["centre_um"][0]-15)<.03 and p["origin_um"][1]==4.59
    p=sm.place("right","BUFx8_ASAP7_75t_R",21.7,4.455)
    assert p["origin_um"][0]>=20.628 and p["origin_um"][1]==4.32


def test_converter_uses_plan_core_extent_instead_of_cut_row_count():
    p=plan();p["core"]=[4.32,4.32,36.72,36.72]
    ss=sites();ss["row0"]["nsites"]=20
    s=C.convert(p,ss,"tiny_core")
    assert s["outline_um"]==[41.04,41.04]


def _icg_plan():
    """root -> hub driver -> 2 ICG parts of RTL gate g (first = the RTL instance, second = clone_of copy) + 1 ungated
    BUF part, each -> its branch -> one leaf (form C, CORES-EARLY-6)."""
    nodes = [["root", None, [20.0, 20.0], "BUFx24_ASAP7_75t_R", "entry"],
             ["T0_g", "root", [12.0, 20.0], "ICGx1_ASAP7_75t_R", "icg"],
             ["T0_br", "T0_g", [12.0, 21.08], "BUFx12f_ASAP7_75t_R", "branch"],
             ["T1_g", "root", [20.0, 25.0], "ICGx1_ASAP7_75t_R", "icg"],
             ["T1_br", "T1_g", [20.0, 26.08], "BUFx12f_ASAP7_75t_R", "branch"],
             ["T2_g", "root", [28.0, 20.0], "BUFx12f_ASAP7_75t_R", "gbuf"],
             ["T2_br", "T2_g", [28.0, 21.08], "BUFx12f_ASAP7_75t_R", "branch"],
             ["T0", "T0_br", [10.0, 12.0], "BUFx8_ASAP7_75t_R", "leaf"],
             ["T1", "T1_br", [20.0, 30.0], "BUFx8_ASAP7_75t_R", "leaf"],
             ["T2", "T2_br", [30.0, 12.0], "BUFx8_ASAP7_75t_R", "leaf"]]
    q = dict(mean=250.0, window=6.0, sink_min=245.0, sink_max=256.0, leaf_out_slew_max=50.0, leaf_slew_in_max=20.0)
    qf = dict(mean=200.0, window=6.0, sink_min=195.0, sink_max=206.0, leaf_out_slew_max=40.0, leaf_slew_in_max=15.0)
    return dict(name="t", entry=[20.0, 20.0], nodes_xy=nodes, frozen_masters={n[0]: n[3] for n in nodes},
                leaf_sinks={"T0": ["a/CLK", "b/CLK"], "T1": ["c/CLK"], "T2": ["d/CLK"]}, TT=q, FF=qf,
                icg_copies=[dict(edge="T0", node="T0_g", gate="u.cg", master="ICGx1_ASAP7_75t_R", first=True, members=["a/CLK", "b/CLK"]),
                            dict(edge="T1", node="T1_g", gate="u.cg", master="ICGx1_ASAP7_75t_R", first=False, members=["c/CLK"])])


def _icg_sites():
    s = sites()
    s["masters"]["ICGx1_ASAP7_75t_R"] = (0.972, SH)
    return s


def test_icg_parts_become_planned_gates_and_copies():
    sl = C.convert(_icg_plan(), _icg_sites(), "tiny_core", outline=[37.8, 37.8])
    g = sl["core_tree"]["gates"]
    assert [x["inst"] for x in g] == ["u.cg", "mp_ck_T1_icg"] and all(x["domain"] == "planned" for x in g)
    assert g[1]["clone_of"] == "u.cg" and g[1]["members"] == ["c/CLK"] and "members" not in g[0]
    assert "mp_ck_T0_g" not in sl["cell_placements"] and "mp_ck_T2_g" in sl["cell_placements"]
    p = CI.compile_slice(sl)
    t = p["core_tree"]
    assert t["under_gate"]["mp_ck_T0_br"] == "u.cg" and t["under_gate"]["mp_ck_T1"] == "mp_ck_T1_icg"
    tcl = CI.emit_tcl(sl)
    assert "ot_ci_tree_gate {u.cg} ICGx1_ASAP7_75t_R {mp_ck_root}" in tcl
    assert "ot_ci_tree_gate_copy {mp_ck_T1_icg} ICGx1_ASAP7_75t_R {u.cg} {mp_ck_root}" in tcl and "{{c/CLK}}" in tcl
    assert tcl.index("ot_ci_tree_gate_planned {u.cg}") < tcl.index("ot_ci_tree_node {mp_ck_T0_br} {u.cg}")
    assert "ot_ci_lec_netlist /work/core_infra_post.v" in tcl


def test_icg_rows_must_match_icg_nodes():
    r = _icg_plan(); r["icg_copies"] = r["icg_copies"][:1]
    with pytest.raises(C.ConvertError):
        C.convert(r, _icg_sites(), "tiny_core", outline=[37.8, 37.8])


def test_icg_copy_members_must_equal_its_leaves():
    r = _icg_plan(); r["icg_copies"][1]["members"] = ["c/CLK", "a/CLK"]
    sl = C.convert(r, _icg_sites(), "tiny_core", outline=[37.8, 37.8])
    with pytest.raises(CI.InfraError):
        CI.compile_slice(sl)


def test_split_rows_cannot_silently_inflate_default_outline():
    s=sites()
    s['rows'].append((30.,s['rows'][0][1],"R0",20))
    with pytest.raises(C.ConvertError,match="split/nonuniform placement rows"):
        C.convert(plan(),s,"tiny_core")
    # The same actual fragments remain legal with the owner's physical canvas.
    a=C.convert(plan(),s,"tiny_core",outline=[37.8,37.8])
    assert a['outline_um']==[37.8,37.8]


def test_nonuniform_single_fragments_need_explicit_core_bounds():
    s=sites();r=list(s['rows'][0]);r[3]-=10;s['rows'][0]=tuple(r)
    with pytest.raises(C.ConvertError,match="explicit --outline"):
        C.convert(plan(),s,"tiny_core")
    p=plan();p['core']=[4.32,4.32,33.48,33.48]
    assert C.convert(p,s,"tiny_core")['outline_um']==[37.8,37.8]


def test_outline_is_the_source_die_area_not_row_truncated_core(tmp_path):
    """DIE-S81-30 (BF TAG16): CORE_AREA 4.32..445.848 is not a whole number of 0.054 sites; ODB rows (= plan core,
    getCoreArea) end at 445.824, so core + mirrored margin gave 450.144 != kit DIE 450.168.  The sites dump carries the
    floorplan die area and the converter takes it exactly."""
    p = plan(); p["core"] = [4.32, 4.32, 445.824, 194.4]
    s = sites(); s["die"] = (0.0, 0.0, 450.168, 198.72)
    assert C.convert(p, s, "tiny_core")["outline_um"] == [450.168, 198.72]
    f = tmp_path / "sites.txt"
    f.write_text("DIE 0.0000 0.0000 450.1680 198.7200\n"
                 "ROW0 4.32 4.32 site_w .054 site_h .27 nrows 1 nsites 8176 orient0 R0\n"
                 "ROW 4.32 4.32 R0 8176\nMASTER BUFx8_ASAP7_75t_R .648 .27\n")
    assert C.read_sites(f)["die"] == (0.0, 0.0, 450.168, 198.72)
    # explicit outline still wins; a sites file without DIE keeps the plan-core rule (default unchanged)
    assert C.convert(p, s, "tiny_core", outline=[37.8, 37.8])["outline_um"] == [37.8, 37.8]
    s.pop("die")
    assert C.convert(p, s, "tiny_core")["outline_um"] == [450.144, 198.72]
