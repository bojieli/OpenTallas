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
    assert tcl.count("dbObstruction_create") == 2 + 3 * e["n_windows"]       # strip M1/M2 + windows M3-M5
    assert "ot_clear_keepout_physical" in tcl


def test_ip_macro_is_not_islanded():
    p = _plan()
    p["partition_types"]["q"]["hard_cores"][0]["module"] = "ot_pdie_serdes"
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    assert II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["ot_pdie_serdes"]["action"] == "DRIVERLESS_IP"
