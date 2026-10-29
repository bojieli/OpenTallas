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
