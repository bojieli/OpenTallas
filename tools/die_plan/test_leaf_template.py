"""LEAF-TEMPLATE: the seed satisfies the template rules on a synthetic leaf row; mutants each break one rule."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_template as LT  # noqa: E402


def core(inst, w, h, o=(0, 0), orient="R0"):
    return {"inst": inst, "outline_um": [w, h], "origin_um": list(o), "orient": orient}


def row():
    hc = [core("u_lf.u_vn.u_b", 356.4, 172.8), core("u_lf.u_vn.u_a", 356.4, 164.2), core("u_lf.u_ve.u_m", 172.8, 345.6),
          core("u_lf.u_ve.u_s", 172.8, 345.6), core("u_lf.u_vs", 172.8, 172.8), core("u_lf.u_vsw", 224.6, 224.6),
          core("u_lf.u_vq", 172.8, 129.6), core("u_lf.u_rxsb", 140.4, 140.4), core("u_lf.u_rxsf", 140.4, 140.4),
          core("u_lf.u_vp.u_b0", 169.4, 29.2), core("u_lf.u_vp.u_b1", 169.4, 29.2)]
    hc += [core("u_lf.u_vp.g_ln[%d].u_l" % i, 114.5, 114.5) for i in range(16)]
    return {"outline_um": [1443.0, 1226.88], "hard_cores": hc}


def apply(t, seed):
    t = copy.deepcopy(t)
    for h in t["hard_cores"]:
        h["origin_um"] = seed[h["inst"]]["origin_um"]
    return t


def test_seed_meets_rules():
    t = row()
    seed, notes = LT.build_seed(t)
    assert len(seed) == len(t["hard_cores"])
    r = LT.check_type(apply(t, seed))
    assert not r["OVERLAP"] and not r["OUTSIDE"] and not r["LANE-STREET"] and not r["HUB-DIST"], r
    assert not r["SLOT"], r["SLOT"]


def test_mutants_are_caught():
    t = apply(row(), LT.build_seed(row())[0])
    m = copy.deepcopy(t)
    m["hard_cores"][-1]["origin_um"] = list(m["hard_cores"][-2]["origin_um"])      # two lanes on one spot
    assert LT.check_type(m)["OVERLAP"]
    m = copy.deepcopy(t)
    m["hard_cores"][3]["origin_um"][0] += 8.64                                      # ve_m|ve_s slot of 8.64 um
    assert LT.check_type(m)["SLOT"]
    m = copy.deepcopy(t)
    m["hard_cores"][1]["origin_um"][1] += 400                                       # vn_a far from vn_b
    assert LT.check_type(m)["HUB-DIST"]
    m = copy.deepcopy(t)
    m["hard_cores"][3]["origin_um"][0] = 1400                                       # outside the outline
    assert LT.check_type(m)["OUTSIDE"]
    m = copy.deepcopy(t)
    m["internal_stations"] = [{"regs_um": [[-5.0, 10.0]]}, {"regs_um": [list(map(lambda v: v + 5, m["hard_cores"][0]["origin_um"]))]}]
    r = LT.check_type(m)
    assert r["ITEM-OUTSIDE"] and r["ITEM-IN-CORE"]


def test_infeasible_outline_raises():
    t = row()
    t["outline_um"] = [700.0, 500.0]
    try:
        LT.build_seed(t)
    except ValueError:
        return
    raise AssertionError("a 700 x 500 outline cannot hold the template")


def test_optimize_skips_infeasible_and_writes(tmp_path, capsys):
    """optimize: an outline that cannot hold the template is reported INFEASIBLE (no model load) and the seed file is still written"""
    import json
    t = row()
    t["outline_um"] = [700.0, 500.0]
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"partition_types": {"ot_s81sl_leaf__t99": t, "other__t1": {"hard_cores": []}}}))
    out = tmp_path / "seed.json"
    assert LT.main(["optimize", str(plan), "--out", str(out)]) == 0
    assert "INFEASIBLE" in capsys.readouterr().out
    assert json.loads(out.read_text()) == {}
