"""CLK-TOOL-6 tests for the ot_clk region MESH form (tools/clk/mesh_form.py + ot_clk region.form mesh).
Synthetic A0-quad fixture (no fleet inputs).  The byte-identity test against the earlier die-local pilot builder runs
when results/qc_mesh_pilot_1/qc_mesh_pilot.py is in the checkout (skipped in a sparse checkout without it)."""
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import mesh_form as MF   # noqa: E402
import ot_clk as O       # noqa: E402

CFG = HERE / "configs" / "qc_mesh_p1.yaml"
LEGACY = REPO / "results" / "qc_mesh_pilot_1" / "qc_mesh_pilot.py"
W, H = 1235.52, 2617.92
COLS = [68.064, 545.376, 690.144, 1167.456]
ROWS = [186.976, 560.992, 934.752, 1308.96, 1683.168, 2056.928, 2430.944]
MID = [154.46, 463.33, 772.19, 1081.06]


def mesh_cfg():
    return O.load_config(CFG)["region"]["mesh"]


def fixture(tmp):
    cores = [dict(inst=f"u_t{i}", module="tile", origin_um=o, outline_um=[457.92, 1157.76])
             for i, o in enumerate([[77.76, 69.12], [699.84, 69.12], [77.76, 1382.4], [699.84, 1382.4]])]
    plan = dict(partitions=[dict(name="c_X", type="cq", origin_um=[1000.0, 2000.0], orient="MX")],
                partition_types={"cq": dict(outline_um=[W, H], contents=cores)})
    taps, k = [], 0
    for y in ROWS:
        for x in (MID if y == ROWS[3] else COLS):
            taps.append(dict(port=f"t_c_X__clk_t{k}", part="c_X", tap=f"clk_t{k}", xy=[1000 + x, 2000 + y])); k += 1
    for j, (x, y) in enumerate([(535.2, 1880.7), (700.3, 1880.7), (535.2, 567.5), (700.3, 567.5)]):
        taps.append(dict(port=f"t_c_X__clk_c{j}", part="c_X", tap=f"clk_c{j}", xy=[1000 + x, 2000 + y]))
    (tmp / "plan.json").write_text(json.dumps(plan))
    (tmp / "tree.json").write_text(json.dumps(dict(taps=taps)))
    return tmp / "plan.json", tmp / "tree.json"


def built(tmp, m=None):
    p, t = fixture(tmp)
    MF.build(str(p), str(t), "c_X", str(tmp / "o"), m or mesh_cfg())
    return json.loads((tmp / "o" / "pilot.json").read_text())


def test_cells_in_glue_and_drivers_on_straps(tmp_path):
    J = built(tmp_path)
    g, cells = J["geom"], J["cells"]
    wid = mesh_cfg()["cell_w"]
    for n, c in cells.items():
        for x in (c["x"], c["x"] + wid[c["master"]]):
            assert not MF.in_core(x, c["y"], g["cores"]), n
    assert len(g["drivers"]) == 32 and len(g["mesh_loads"]) == 28
    for d in g["drivers"]:
        assert any(cells[d]["x"] <= vx <= cells[d]["x"] + 1.62 for vx in g["vx"]), d


def test_tree_equal_legs_by_construction(tmp_path):
    J = built(tmp_path)
    cells, nets = J["cells"], J["nets"]
    cen = lambda n: (cells[n]["x"] + 0.81, cells[n]["y"])
    legs = {}
    for n, v in nets.items():
        if v["kind"] != "tree" or v["drv"] == "port:root" or v["drv"].startswith(("E", "Q")):
            continue
        d = cen(v["drv"])
        for l in v["loads"]:
            p = cen(l)
            legs.setdefault(v["drv"][0], []).append(abs(p[0] - d[0]) + abs(p[1] - d[1]))
    for lvl, L in legs.items():
        assert max(L) - min(L) < 12.0 and max(L) <= 450.0, (lvl, min(L), max(L))


def test_mesh_def_one_special_net(tmp_path):
    built(tmp_path)
    d = (tmp_path / "o" / "pilot.def").read_text()
    sn = d[d.index("SPECIALNETS"):d.index("END SPECIALNETS")]
    assert sn.count("- ck_mesh") == 1 and sn.count("VIA89") == 28 and "USE CLOCK" in sn


@pytest.mark.skipif(not LEGACY.is_file(), reason="legacy pilot builder not in this checkout")
def test_byte_identical_to_the_legacy_pilot_builder(tmp_path):
    spec = importlib.util.spec_from_file_location("legacy_pilot", LEGACY)
    QP = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(QP)
    p, t = fixture(tmp_path)
    for adj in (0.4, 0.7):
        m = dict(mesh_cfg(), adjust=adj)
        QP.build(str(p), str(t), "c_X", str(tmp_path / f"old{adj}"), adj)
        MF.build(str(p), str(t), "c_X", str(tmp_path / f"new{adj}"), m)
        for f in O.MESH_FILES:
            assert (tmp_path / f"old{adj}" / f).read_bytes() == (tmp_path / f"new{adj}" / f).read_bytes(), (adj, f)


def test_every_mesh_key_is_required(tmp_path):
    m = mesh_cfg()
    for k in MF.REQUIRED:
        bad = {x: v for x, v in m.items() if x != k}
        with pytest.raises(MF.MeshConfigError):
            MF.params(bad)


def test_grid_shape_mismatch_and_unwired_trunk_fail_closed(tmp_path):
    p, t = fixture(tmp_path)
    with pytest.raises(MF.MeshConfigError):
        MF.build(str(p), str(t), "c_X", str(tmp_path / "o"), dict(mesh_cfg(), rows=8))
    with pytest.raises(MF.MeshConfigError):
        MF.params(dict(mesh_cfg(), cols=8))


def test_edges_both_adds_the_ot_edges_readout_default_rise_does_not(tmp_path):
    built(tmp_path)
    assert "OT_EDGES" not in (tmp_path / "o" / "run.tcl").read_text()
    m = dict(mesh_cfg(), edges="both")
    p, t = fixture(tmp_path)
    MF.build(str(p), str(t), "c_X", str(tmp_path / "b"), m)
    tcl, ff = (tmp_path / "b" / "run.tcl").read_text(), (tmp_path / "b" / "run_ff.tcl").read_text()
    assert "# OT_EDGES v1" in tcl and "edges grt TT" in tcl and "edges drt TT" in tcl
    assert "proc edges" in ff and "edges drt FF" in ff and "arrival_max_fall" in ff
    with pytest.raises(MF.MeshConfigError):
        MF.build(str(p), str(t), "c_X", str(tmp_path / "c"), dict(mesh_cfg(), edges="fall"))


def _mesh_config(tmp, ref=None):
    p, t = fixture(tmp)
    c = O.load_config(CFG)
    c["inputs"] = dict(plan=str(p), tree=str(t))
    c["region"]["parts"] = ["c_X"]
    c["event"]["reference_mesh_dirs"] = {"c_X": str(ref)} if ref else {}
    return c


def test_ot_clk_mesh_kit_replay_identical_then_mutant_different(tmp_path):
    c = _mesh_config(tmp_path)
    O.mesh_kit(c, tmp_path / "ref")
    c["event"]["reference_mesh_dirs"] = {"c_X": str(tmp_path / "ref" / "mesh" / "c_X")}
    O.mesh_kit(c, tmp_path / "new")
    assert O.compare_mesh(c, "cfg", tmp_path / "new")["replay"] == "IDENTICAL"
    c2 = copy.deepcopy(c)
    c2["region"]["mesh"]["strap_w"] = 0.2
    O.mesh_kit(c2, tmp_path / "mut")
    v = O.compare_mesh(c, "cfg", tmp_path / "mut")
    assert v["replay"] == "DIFFERENT" and not v["parts"]["c_X"]["files"]["pilot.def"]["identical"]
    c["event"]["reference_mesh_dirs"] = {}
    assert O.compare_mesh(c, "cfg", tmp_path / "new")["replay"] == "DIFFERENT"


def test_ot_clk_mesh_is_not_a_die_trial_form_and_needs_no_stage_model():
    c = O.load_config(CFG)
    with pytest.raises(O.ConfigError):
        O.kit_argv(c, "OUT")
    assert O.stage_check(c, O.load_registry())[0]
    assert O.mesh_parts(c) == ["c_E3_bf_11", "c_W2_bn_01"]


def test_ot_clk_mesh_refit_refuses(tmp_path):
    with pytest.raises(O.ConfigError):
        O.main(["refit", str(CFG), "--tree", "t", "--arr-prefix", "a", "--id", "x", "--tap", "1", "2", "-o",
                str(tmp_path / "c.json")])


def test_no_die_names_in_mesh_form():
    src = (HERE / "mesh_form.py").read_text().lower()
    assert not re.search(r"\b(qwen|qc|s81|hbm|kv|head)\b", src)


LEGACY_REC = REPO / "results" / "qc_mesh_pilot_1" / "pilot_signoff.py"


@pytest.mark.skipif(not LEGACY_REC.is_file(), reason="legacy pilot sign-off not in this checkout")
def test_rec_equals_the_legacy_pilot_rec(tmp_path):
    sys.path.insert(0, str(REPO / "tools" / "die_plan"))
    import explicit_mesh_signoff as EMS
    spec = importlib.util.spec_from_file_location("legacy_signoff", LEGACY_REC)
    PS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PS)
    J = built(tmp_path)
    for d in ("a", "b"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "pilot.json").write_text((tmp_path / "o" / "pilot.json").read_text())
        rows = [f"{pin} {n} {10 + i} {9 + i} {20 + i % 7}" for i, n in enumerate(sorted(J["cells"])) for pin in ("A", "Y")]
        (tmp_path / d / "tree_grt_TT.txt").write_text("\n".join(rows) + "\n")
    PS.cmd_rec(str(tmp_path / "a"), "grt")
    MF.rec(str(tmp_path / "b"), "grt", mesh_cfg(), EMS.mesh_rc)
    a, b = (json.loads((tmp_path / d / "rec_grt.json").read_text()) for d in ("a", "b"))
    a.pop("source"); b.pop("source")
    assert a == b


def test_strap_keepout_opt_in_bands_both_sides_default_unchanged(tmp_path):
    """DIE-QC-31 A3 keep-out form: strap_keepout_um adds a strap-layer band each side of every strap; absent = same DEF"""
    for d in "azbn":
        (tmp_path / d).mkdir()
    built(tmp_path / "a")
    base = (tmp_path / "a" / "o" / "pilot.def").read_text()
    built(tmp_path / "z", dict(mesh_cfg(), strap_keepout_um=0))
    assert (tmp_path / "z" / "o" / "pilot.def").read_text() == base
    J = built(tmp_path / "b", dict(mesh_cfg(), strap_keepout_um=0.32))
    d = (tmp_path / "b" / "o" / "pilot.def").read_text()
    n0 = int(re.search(r"BLOCKAGES (\d+) ;", base).group(1))
    n1 = int(re.search(r"BLOCKAGES (\d+) ;", d).group(1))
    g = J["geom"]
    assert n1 - n0 == 2 * (len(g["vx"]) + len(g["hy"])) == 2 * (4 + 7)
    U = lambda v: int(round(v * 1000))
    x = g["vx"][1]
    y0, y1 = (U(v) for v in g["y_span"])
    assert f"- LAYER M9 RECT ( {U(x - 0.08 - 0.32)} {y0} ) ( {U(x - 0.08)} {y1} ) ;" in d
    assert f"- LAYER M9 RECT ( {U(x + 0.08)} {y0} ) ( {U(x + 0.08 + 0.32)} {y1} ) ;" in d
    y = g["hy"][0]
    x0, x1 = (U(v) for v in g["x_span"])
    assert f"- LAYER M8 RECT ( {x0} {U(y + 0.08)} ) ( {x1} {U(y + 0.4)} ) ;" in d
    # only the BLOCKAGES section changes (straps stay the special net ck_mesh)
    cut = lambda t: t.replace(t[t.index("BLOCKAGES"):t.index("END BLOCKAGES")], "")
    assert cut(d) == cut(base)
    with pytest.raises(MF.MeshConfigError):
        built(tmp_path / "n", dict(mesh_cfg(), strap_keepout_um=-1))


def test_qc_mesh_p2_is_p1_plus_strap_keepout(tmp_path):
    """DIE-QC-34: the QC die mesh config carries the A3 keep-out 0.32; otherwise identical mesh keys to qc_mesh_p1"""
    p2 = O.load_config(HERE / "configs" / "qc_mesh_p2.yaml")["region"]["mesh"]
    p1 = mesh_cfg()
    assert p2["strap_keepout_um"] == 0.32
    assert {k: v for k, v in p2.items() if k not in ("strap_keepout_um", "run")} == {k: v for k, v in p1.items() if k != "run"}
    assert {k: v for k, v in p2["run"].items() if k != "name_prefix"} == {k: v for k, v in p1["run"].items() if k != "name_prefix"}
    (tmp_path / "a").mkdir()
    d = (built(tmp_path / "a", p2), (tmp_path / "a" / "o" / "pilot.def").read_text())[1]
    assert "- LAYER M9 RECT" in d[d.index("BLOCKAGES"):d.index("END BLOCKAGES")]


# ------------------------------------------------------------------------------------------- grid topology (opt-in)
GW, GH = 2400.0, 1200.0


def grid_cfg(**kw):
    m = copy.deepcopy(O.load_config(HERE / "configs" / "hbm_hubmesh_a.yaml")["region"]["mesh"])
    m["grid"].update(dict(v_straps=4, h_straps=4, drivers_per_col=4), **kw)
    return m


def grid_fixture(tmp, orient="R0"):
    cores = [dict(inst="u_big", module="m", origin_um=[500.0, 300.0], outline_um=[400.0, 300.0]),
             dict(inst="u_s", module="m", origin_um=[1700.0, 100.0], outline_um=[200.0, 200.0])]
    plan = dict(partitions=[dict(name="hub_X", type="ht", origin_um=[1000.0, 2000.0], orient=orient)],
                partition_types={"ht": dict(outline_um=[GW, GH], contents=cores, clock=dict(tap_um=[1300.0, 500.0]))})
    taps = [dict(port=f"t_hub_X__clk_t{k}", part="hub_X", tap=f"clk_t{k}", xy=[1000 + x, 2000 + y])
            for k, (x, y) in enumerate([(37.1, 55.3), (1210.0, 610.4), (2300.2, 1111.1), (700.0, 450.0), (1800.0, 200.0),
                                        (120.0, 1000.0), (2000.0, 700.0)])]
    taps.append(dict(port="t_hub_X__clk_c0", part="hub_X", tap="clk_c0", xy=[1000 + 705.0, 2000 + 462.0]))
    (tmp / "plan.json").write_text(json.dumps(plan))
    (tmp / "tree.json").write_text(json.dumps(dict(taps=taps)))
    return tmp / "plan.json", tmp / "tree.json"


def grid_built(tmp, m=None, orient="R0"):
    p, t = grid_fixture(tmp, orient)
    r = MF.build(str(p), str(t), "hub_X", str(tmp / "o"), m or grid_cfg())
    return r, json.loads((tmp / "o" / "pilot.json").read_text())


def _paths(J):
    cells, nets = J["cells"], J["nets"]
    par = {}
    for v in nets.values():
        if v["kind"] == "tree" and v["drv"] != "port:root":
            for l in v["loads"]:
                par[l] = v["drv"]
    cen = lambda n: (cells[n]["x"], cells[n]["y"])
    out = {}
    for d in J["geom"]["drivers"]:
        L, n, sn = 0.0, d, 0.0
        while n in par:
            L += abs(cen(n)[0] - cen(par[n])[0]) + abs(cen(n)[1] - cen(par[n])[1])
            sn += J["geom"]["snake_um"].get(n, 0.0)
            n = par[n]
        out[d] = (L, sn, n)
    return out


def test_grid_cells_off_cores_and_counts(tmp_path):
    r, J = grid_built(tmp_path)
    g, cells = J["geom"], J["cells"]
    wid = grid_cfg()["cell_w"]
    for n, c in cells.items():
        for x in (c["x"], c["x"] + wid[c["master"]]):
            assert not MF.in_core(x, c["y"], g["cores"]), n
    assert r["drivers"] == 16 and r["loads"] == 8 and len(g["drivers"]) == 16
    assert g["core_loads"] == ["K_clk_c0"] and "K_clk_c0" not in cells
    assert g["slides"], "the fixture puts drivers/nodes on u_big: some cells must slide"
    assert all(c["y"] in g["hy"] for c in (g["tap_node"][l] and {"y": g["tap_node"][l][1]} for l in g["mesh_loads"]))


def test_grid_tree_zero_skew_by_construction_and_rep_spacing(tmp_path):
    r, J = grid_built(tmp_path)
    P = _paths(J)
    assert {v[2] for v in P.values()} == {"R"}
    tot = [L + sn for L, sn, _ in P.values()]
    # equal path + recorded snake (site/overlap rounding <= a few um per level)
    assert max(tot) - min(tot) < 20.0, (min(tot), max(tot))
    cells, nets = J["cells"], J["nets"]
    for v in nets.values():
        if v["kind"] != "tree" or v["drv"] == "port:root":
            continue
        for l in v["loads"]:
            d = abs(cells[l]["x"] - cells[v["drv"]]["x"]) + abs(cells[l]["y"] - cells[v["drv"]]["y"])
            assert d <= 360.0 + 10.0, (v["drv"], l, d)


def test_grid_rec_runs_and_stubs_slid_drivers(tmp_path):
    sys.path.insert(0, str(REPO / "tools" / "die_plan"))
    import explicit_mesh_signoff as EMS
    r, J = grid_built(tmp_path)
    rows = [f"{pin} {n} {10 + i} {9 + i} {20}" for i, n in enumerate(sorted(J["cells"])) for pin in ("A", "Y")]
    (tmp_path / "o" / "tree_grt_TT.txt").write_text("\n".join(rows) + "\n")
    out, warn = MF.rec(str(tmp_path / "o"), "grt", grid_cfg(), EMS.mesh_rc)
    assert warn and len(out["taps"]) == 8
    k = [t for t in out["taps"] if t["kind"] == "native_core_clock"]
    assert len(k) == 1 and k[0]["load_ff"] == 2.94 and k[0]["jog_um"] > 0 and k[0]["node"].endswith(":705.0000:462.0000")
    assert all(t["jog_um"] == 0.0 for t in out["taps"] if t["kind"] == "published_grid_clock")
    ends = {s_[0] for s_ in out["segs"]} | {s_[1] for s_ in out["segs"]}
    assert all(t["node"] in ends for t in out["taps"]), "every tap node is on the conductor graph"
    assert all(n["anchor"][0] + ":" + ":".join(f"{float(v):.4f}" for v in n["anchor"][1:]) in ends
               for n in out["nodes"] if n["driver"])
    assert sum(n["driver"] for n in out["nodes"]) == 16
    slid = [d for d in J["geom"]["drivers"] if d in J["geom"]["slides"]]
    assert out["graph"]["edges"] >= 4 * 5 + 4 * 5 + len(slid)


def test_grid_keys_required_and_early_fail_closed(tmp_path):
    for k in ("v_straps", "rep_max_um", "early"):
        m = grid_cfg()
        del m["grid"][k]
        with pytest.raises(MF.MeshConfigError):
            MF.params(m)
    with pytest.raises(MF.MeshConfigError):
        MF.params(grid_cfg(early="branch"))
    with pytest.raises(MF.MeshConfigError):
        MF.params(grid_cfg(drivers_per_col=3))
    m = grid_cfg()
    m["topology"] = "ring"
    with pytest.raises(MF.MeshConfigError):
        MF.params(m)


def test_grid_mirror_my_flips_cores_and_entry(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    _, A = grid_built(tmp_path / "a", orient="R0")
    _, B = grid_built(tmp_path / "b", orient="MY")
    ra = A["geom"]["cores"][0]["rect"]; rb = B["geom"]["cores"][0]["rect"]
    assert rb == [GW - ra[2], ra[1], GW - ra[0], ra[3]]
    assert abs(B["cells"]["R"]["x"] - (GW - 1300.0)) < 5 and abs(A["cells"]["R"]["x"] - 1300.0) < 5


def test_quad_part_geom_still_refuses_my():
    with pytest.raises(MF.MeshConfigError):
        import tempfile, os
        d = Path(tempfile.mkdtemp())
        p, _ = grid_fixture(d, "MY")
        MF.part_geom(str(p), "hub_X")


# ------------------------------------------------------------------------------- grid v2: balance delay (opt-in)
def grid_v2_cfg(**kw):
    a2 = O.load_config(HERE / "configs" / "hbm_hubmesh_a2.yaml")["region"]["mesh"]["grid"]
    v2 = {k: copy.deepcopy(a2[k]) for k in ("balance", "equal_stages", "first_um", "pocket_um", "stage_model")}
    v2.update(kw)
    return grid_cfg(**v2)


def test_grid_v2_keys_fail_closed():
    with pytest.raises(MF.MeshConfigError):
        MF.params(grid_cfg(balance="skew"))
    with pytest.raises(MF.MeshConfigError):
        MF.params(grid_cfg(balance="delay"))                 # no stage_model
    with pytest.raises(MF.MeshConfigError):
        MF.params(grid_cfg(equal_stages=True))               # v2 key without balance: delay
    MF.params(grid_v2_cfg())


def test_grid_v2_equal_stages_and_model_balanced(tmp_path):
    r, J = grid_built(tmp_path, grid_v2_cfg())
    v2 = J["geom"]["v2"]
    assert r["balance"] == "delay" and r["stages"][0] == r["stages"][1], r["stages"]
    assert v2["model_spread_ps"] < 10.0, v2["model_spread_ps"]
    assert set(v2["leg_model_ps"]) >= set(J["geom"]["drivers"])
    for n, c in J["cells"].items():                          # still off every core
        for x in (c["x"], c["x"] + grid_cfg()["cell_w"][c["master"]]):
            assert not MF.in_core(x, c["y"], J["geom"]["cores"]), n


def test_grid_v2_rebalance_zero_error_is_identity(tmp_path):
    (tmp_path / "a").mkdir()
    r, J = grid_built(tmp_path / "a", grid_v2_cfg())
    # a measured dump that equals the model exactly -> every correction 0 -> the same tree
    par = {l: v["drv"] for v in J["nets"].values() if v["kind"] == "tree" for l in v["loads"]}
    lm, arr = J["geom"]["v2"]["leg_model_ps"], {"R": 0.0}

    def a(n):
        if n not in arr:
            u = par[n]
            while u.startswith("P"):
                u = par[u]
            arr[n] = a(u) + lm[n] if n in lm else a(par[n]) + 1.0
        return arr[n]
    for n in J["cells"]:
        if n in par:
            a(n)
    dump = tmp_path / "tree.txt"
    dump.write_text("".join(f"A {n} {v} {v} 20\n" for n, v in arr.items()))
    corr = MF.rebalance_corr(dict(pilot=str(tmp_path / "a" / "o" / "pilot.json"), tree=str(dump)))
    assert corr and max(abs(v) for v in corr.values()) < 1e-3


def test_grid_v2_pocket_rule():
    cores = [[0, 0, 100, 200], [140, 0, 240, 200], [100, 140, 140, 200]]     # a 40 x 140 um dead-end pocket
    cores = [dict(inst=f"c{i}", rect=c) for i, c in enumerate(cores)]
    assert MF.boxed(120.0, 100.0, cores, 60.0)               # cores within 60 um on 3 sides
    assert not MF.boxed(120.0, 100.0, cores, 10.0)
    assert not MF.boxed(300.0, 100.0, cores, 60.0)
