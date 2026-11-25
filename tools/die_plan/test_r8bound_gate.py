"""R8BOUND-1124 (COORD flow review #2): PRE reports (WARN, report-only) every direct R8 table member whose bound != the plan's
lane cycles, the strict-bind R8_STALE that C1m found after 7,185 s (6 dvs_E*.so_w flt members, table 2, plan 4)."""
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def _m(e, lane, bound, src="stm", sink="fw", port="st_dn_c[0:0]"):
    return {"id": f"dvs_{e}.u_fdn.{port}<-dvs_{e}.u_stm.so_w@0", "lane": lane, "bound": bound, "pad": 0,
            "src_part": f"sl_{e}_{src}", "sink_part": f"sl_{e}_{sink}"}


def tree(root, members, extra=None, flt_cycles=4):
    """C1m-shaped plan: per element E0..E5 a flt lane (cycles 4) and a data lane (cycles 2) stm -> fw, plus a forwarded member"""
    pd = root / "physical/die_plan/qc/plan_of_record"; pd.mkdir(parents=True)
    ports, lanes, lat = [], [], {}
    for k in range(6):
        for nm, cy in (("flt", flt_cycles), ("x_stm_fw", 2)):
            lid = f"sl_E{k}_stm__{nm}"
            ports.append({"id": lid + "__0", "src": {"part": f"sl_E{k}_stm", "bus": "o"}, "dst": {"part": f"sl_E{k}_fw", "bus": "i"}})
            lanes.append({"id": lid, "ports": [lid + "__0"]})
            lat[lid] = {"cycles": cy, "stations": 0}
    ab = {"land_r8": "physical/die_plan/qc/plan_of_record/r8.json"}
    (pd / "r8.json").write_text(json.dumps({"members": members}))
    if extra is not None:
        ab["land_r8_extra"] = ["physical/die_plan/qc/plan_of_record/r8_x.json"]
        (pd / "r8_x.json").write_text(json.dumps({"members": extra}))
    plan = {"ports": ports, "lanes": lanes, "latency": {"lanes": lat}, "asbuilt": ab}
    (pd / "plan.json").write_text(json.dumps(plan))
    return str(root), str(pd / "plan.json")


def c1m_members(flt_bound=2):
    ms = []
    for k in range(6):
        ms.append(_m(f"E{k}", f"sl_E{k}_stm__flt", flt_bound))
        ms.append(_m(f"E{k}", f"sl_E{k}_stm__x_stm_fw", 2, port="st_dn_c[1:544]"))
    ms.append(_m("E0", "sl_E0_stm__x_stm_fw", 23, src="ctl", port="b_tw[0:3]"))    # forwarded (src ctl != lane src stm): not judged
    return ms


def test_c1m_lists_the_six_flt_members(tmp_path):
    t, p = tree(tmp_path, c1m_members())
    f = G.check_r8bound(t, p)
    warn = [x for x in f if x.startswith("WARN R8BOUND")]
    assert len(warn) == 1 and "6 direct member(s)" in warn[0] and "report-only" in warn[0] and "r8_refresh.py" in warn[0]
    for k in range(6):
        assert f"dvs_E{k}.u_fdn.st_dn_c[0:0]<-dvs_E{k}.u_stm.so_w@0 lane sl_E{k}_stm__flt table 2 plan 4" in warn[0]
    assert "x_stm_fw table" not in warn[0]
    assert any(x.startswith("LIST R8BOUND members 13 judged 12 stale 6 not judged (forwarded / no cycles row) 1") for x in f)
    assert not any(x.startswith("FAIL") for x in f)                       # report-only


def test_fresh_table_is_silent_and_extra_is_authoritative(tmp_path):
    t, p = tree(tmp_path / "a", c1m_members(flt_bound=4))
    assert not any(x.startswith("WARN") for x in G.check_r8bound(t, p))
    fix = [_m(f"E{k}", f"sl_E{k}_stm__flt", 4) for k in range(6)]          # stale land_r8, fixed by the extra table (same ids)
    t, p = tree(tmp_path / "b", c1m_members(), extra=fix)
    assert not any(x.startswith("WARN") for x in G.check_r8bound(t, p))


def test_skippable_class_and_lane_less_plan_not_judged(tmp_path):
    t, p = tree(tmp_path, c1m_members())
    assert "R8BOUND" in G.CLASSES                                          # --skip R8BOUND
    f = G.check_r8bound(t, p, raw={"lanes": [], "asbuilt": {}})
    assert not any(x.startswith("WARN") for x in f) and "judged 0 stale 0" in f[0]
