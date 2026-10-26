"""HBM-CORE-LAT: infra island design + kit hook (opt-in)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import infra_islands as II  # noqa: E402
import gen_core_kit_hbm as G  # noqa: E402


def _plan():
    core = dict(inst="u_c", module="m_big", origin_um=[0.0, 0.0], outline_um=[630.72, 1036.8], obs_max="M5")
    t = dict(outline_um=[1000.0, 1100.0], hard_cores=[core])
    return dict(partition_types=dict(q=t), partitions=[dict(name="A", type="q", origin_um=[0.0, 0.0], orient="R0"),
                                                       dict(name="B", type="q", origin_um=[2000.0, 0.0], orient="MY")],
                clock=dict(common_latency_ps=250, insertion_tol_ps=40))


def test_strip_covers_every_interior_point():
    p = _plan()
    # intersections deep inside both instances (R0 and MY): x 300 um from the core edge
    mesh = dict(xs=[300.0, 2000.0 + 1000.0 - 300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"], [1, 0, "hard_core", "B/u_c"]],
                meta={})
    isl, checks = II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)
    e = isl["m_big"]
    assert e["action"] == "ISLAND" and e["all_legal"] and e["instances"] == 2
    assert abs((e["strip_um"][0] + e["strip_um"][2]) / 2 - 315.36) < 1e-6      # mirror-invariant x-centre
    assert all(c["slide_um"] < 20 for c in checks)
    assert e["worst_jog_um"] <= 69.12 / 2


def test_kit_tcl_has_blockage_and_window_obstructions():
    p = _plan()
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    e = II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["m_big"]
    tcl = G.infra_islands_tcl(e, 630.72, 1036.8)
    assert tcl.count("dbBlockage_create") == 1
    assert tcl.count("dbObstruction_create") == 2                            # strip M1/M2 only (after PDN: rails kept)
    assert "ot_clear_keepout_physical" in tcl
    assert "OT_INFRA_ISLANDS FAIL: no VDD/VSS followpin rails" in tcl and "window_pg_shapes" in tcl
    pdn = G.infra_islands_pdn_tcl(e, 630.72, 1036.8)                         # windows M3-M5 BEFORE pdngen
    assert pdn.count("dbObstruction_create") == 3 * e["n_windows"]
    assert "findLayer M1" not in pdn and "findLayer M2" not in pdn


def test_kit_hook_writes_pdn_prefix_and_abstract_inputs(tmp_path):
    import json
    p = _plan()
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    e = II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["m_big"]
    isl = tmp_path / "isl.json"
    isl.write_text(json.dumps(dict(islands=dict(m_big=e))))
    (tmp_path / "pdn.tcl").write_text("pdngen\n")
    cfg = ["export PRE_GLOBAL_PLACE_TCL = /work/x.tcl"]
    r = G.infra_islands_hook(tmp_path, cfg, isl, "m_big", 630.72, 1036.8)
    pdn = (tmp_path / "pdn.tcl").read_text()
    assert pdn.index("dbObstruction_create") < pdn.index("\npdngen\n")
    assert not (tmp_path / "island_abstract.py").exists() and json.loads((tmp_path / "infra_islands.json").read_text())["module"] == "m_big"
    assert cfg[-1].endswith("/work/infra_islands_gpl.tcl") and r["previous_gpl_hook"] == "/work/x.tcl"
