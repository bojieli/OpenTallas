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
    assert (tmp_path / "island_abstract.py").is_file() and json.loads((tmp_path / "infra_islands.json").read_text())["module"] == "m_big"
    assert cfg[-1].endswith("/work/infra_islands_gpl.tcl") and r["previous_gpl_hook"] == "/work/x.tcl"


LEF = """MACRO m_big
  SIZE 630.72 BY 1036.8 ;
  PIN VDD
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT  2 4 2.12 1032 ;
    END
  END VDD
  PIN VSS
    USE GROUND ;
    PORT
      LAYER M5 ;
        RECT  4 4 4.12 1032 ;
    END
  END VSS
  OBS
    LAYER M1 ;
     RECT  0 0 630.72 1036.8 ;
    LAYER M3 ;
     RECT  0 0 630.72 1036.8 ;
    LAYER M7 ;
     RECT  0 0 630.72 1036.8 ;
  END
END m_big
"""


def test_abstract_cuts_strip_and_windows_and_exposes_rails():
    import island_abstract as IA
    p = _plan()
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    e = II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["m_big"]
    s = e["strip_um"]
    rails = {"VDD": {"M1": [(s[0], 10.791, s[2], 10.809)]}, "VSS": {"M1": [(s[0], 10.521, s[2], 10.539)]}}
    new, st = IA.rewrite_lef(LEF, IA.cuts_for(e), rails)
    assert st["ports"] == {"VDD": 1, "VSS": 1}
    obs = new[new.index("  OBS"):]
    blocks = {}
    cur = None
    for ln in obs.split("\n"):
        t = ln.strip()
        if t.startswith("LAYER"):
            cur = t.split()[1]
            blocks[cur] = []
        elif t.startswith("RECT") and cur:
            blocks[cur].append(tuple(float(v) for v in t.split()[1:5]))
    area = lambda rs: sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)
    full = 630.72 * 1036.8
    assert abs(area(blocks["M1"]) - (full - (s[2] - s[0]) * (s[3] - s[1]))) < 1e-3     # strip cut on M1
    assert not any(IA.overlaps(r, s) for r in blocks["M1"])
    win = sum((w[2] - w[0]) * (w[3] - w[1]) for w in e["windows_um"])
    assert abs(area(blocks["M3"]) - (full - win)) < 1e-3                               # windows cut on M3
    assert not any(IA.overlaps(r, tuple(w)) for r in blocks["M3"] for w in e["windows_um"])
    assert blocks["M7"] == [(0.0, 0.0, 630.72, 1036.8)]                                # untouched above the windows
    vdd = new[new.index("  PIN VDD"):new.index("  END VDD")]
    assert vdd.count("PORT") == 2 and "LAYER M1" in vdd


def test_abstract_fails_closed_without_rails():
    import pytest
    import island_abstract as IA
    p = _plan()
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    e = II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["m_big"]
    with pytest.raises(SystemExit):
        IA.rewrite_lef(LEF, IA.cuts_for(e), {"VDD": {}, "VSS": {"M1": [(1, 1, 2, 2)]}})


def test_ip_macro_is_not_islanded():
    p = _plan()
    p["partition_types"]["q"]["hard_cores"][0]["module"] = "ot_pdie_serdes"
    mesh = dict(xs=[300.0], ys=[500.0], hole_drivers=[[0, 0, "hard_core", "A/u_c"]], meta={})
    assert II.design(p, mesh, 250.0, 8.64, 69.12, 4.32, 4.32)[0]["ot_pdie_serdes"]["action"] == "DRIVERLESS_IP"
