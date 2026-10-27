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
