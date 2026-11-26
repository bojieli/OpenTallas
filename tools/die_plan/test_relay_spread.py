"""relay_spread.py (CLASS-OWNERS-B C-RELAY-SEAT): stacked relay_sites spread over legal bit sites; default OFF, byte-identical when absent."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as A  # noqa: E402
import relay_spread as S  # noqa: E402

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def _plan(flag=None, bits=288, depth=None):
    rs = {f"u_bin_ca_i0/q[{b}]": [100.0, 80.0] for b in range(bits)}
    for b in range(40):                       # a 3-stage pipe per bit on another point
        for j in range(3):
            rs[f"u_lpad_x_i0.r[{j}][{b}]"] = [300.0, 40.0]
        rs[f"u_lpad_x_i0.q[{b}]"] = [300.0, 40.0]
    rs["u_single.q[0]"] = [500.0, 500.0]      # not a stack: untouched
    t = {"outline_um": [700.0, 700.0], "clock": {"taps": {"keep": 1}},
         "hard_cores": [{"inst": "u_a", "origin_um": [90.0, 90.0], "outline_um": [50.0, 50.0]}],   # just above the stack
         "relay_sites": rs}
    if depth:
        t["relay_depth"] = depth
    p = {"schema": "opentallas.die_plan.v1", "partition_types": {"bk_t": t, "other": {"outline_um": [1, 1], "relay_sites": {"a.q": [1, 1]}}}}
    if flag is not None:
        p["relay_spread"] = flag
    return p


def _run(tmp_path, plan, *extra):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    out = tmp_path / "out"
    assert S.main([str(p), str(out), "--out-plan", str(tmp_path / "new.json"), *extra]) == 0
    return p, out, tmp_path / "new.json"


def test_flag_absent_is_byte_identical_noop(tmp_path):
    p, out, newp = _run(tmp_path, _plan())
    assert newp.read_bytes() == p.read_bytes()
    assert not out.exists()
    p2, out2, newp2 = _run(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, _plan({"enable": 0}))
    assert newp2.read_bytes() == p2.read_bytes()


def test_library_does_not_mutate_and_off_returns_none():
    plan = _plan()
    assert S.flag_cfg(plan) is None
    before = json.dumps(plan, sort_keys=True)
    S.spread_plan(plan, S.flag_cfg(plan, True))
    assert json.dumps(plan, sort_keys=True) == before


def test_spread_clears_stacks_keeps_legs_and_cores(tmp_path):
    plan = _plan({"enable": 1})
    assert len(A.relay_seats(plan["partition_types"]["bk_t"])[1]) == 2
    p, out, newp = _run(tmp_path, plan)
    new = json.loads(newp.read_text())
    t0, t1 = plan["partition_types"]["bk_t"], new["partition_types"]["bk_t"]
    assert {k: v for k, v in t1.items() if k != "relay_sites"} == {k: v for k, v in t0.items() if k != "relay_sites"}
    assert new["partition_types"]["other"] == plan["partition_types"]["other"]
    assert set(t0["relay_sites"]) == set(t1["relay_sites"]) and t1["relay_sites"]["u_single.q[0]"] == [500.0, 500.0]
    assert A.relay_seats(t1)[1] == []                                   # the check is quiet
    assert A.relay_seats(t1)[0] == []                                   # nothing buried
    pts = [tuple(v) for v in t1["relay_sites"].values()]
    assert len(set(pts)) == len(pts)                                    # one seat per cell
    for k, v in t1["relay_sites"].items():
        assert L1(v, t0["relay_sites"][k]) <= 25.0 + 1e-6               # leg grows by <= max_um
        assert not (84.0 < v[0] < 146.0 and 84.0 < v[1] < 146.0)       # clear of u_a + halo
    rep = json.loads((out / "report.json").read_text())["types"]["bk_t"]
    assert rep["stack_points_before"] == 2 and rep["stack_points_after"] == 0 and rep["groups_kept"] == 0
    assert set(json.loads((out / "bk_t" / "relay_spread_sites.json").read_text())) <= set(t0["relay_sites"])


def test_bit_order_and_stage_adjacency():
    plan = _plan({"enable": 1})
    new, _ = S.spread_plan(plan, S.flag_cfg(plan))
    rs = new["partition_types"]["bk_t"]["relay_sites"]
    for b in range(40):
        pts = [rs[f"u_lpad_x_i0.r[{j}][{b}]"] for j in range(3)] + [rs[f"u_lpad_x_i0.q[{b}]"]]
        assert max(L1(pts[0], q) for q in pts) <= 12.0   # stages of a bit are neighbours (hop << 405)


def test_deterministic_and_idempotent():
    plan = _plan({"enable": 1})
    a, _ = S.spread_plan(plan, S.flag_cfg(plan))
    b, _ = S.spread_plan(plan, S.flag_cfg(plan))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    c, rep = S.spread_plan(a, S.flag_cfg(a))
    assert json.dumps(c, sort_keys=True) == json.dumps(a, sort_keys=True) and not rep


def test_leg_guard_keeps_type_without_margin():
    plan = _plan({"enable": 1}, depth=[{"inst": "x", "port": "p", "D": 1, "path_um": 800.0}])   # hop 400 um: 5 um margin
    new, rep = S.spread_plan(plan, S.flag_cfg(plan))
    assert new["partition_types"]["bk_t"]["relay_sites"] == plan["partition_types"]["bk_t"]["relay_sites"]
    assert rep["bk_t"]["groups_kept"] == 2


def test_group_that_cannot_fit_is_kept():
    plan = _plan({"enable": 1, "max_um": 6}, bits=2000)
    new, rep = S.spread_plan(plan, S.flag_cfg(plan))
    assert rep["bk_t"]["groups_kept"] >= 1
    assert new["partition_types"]["bk_t"]["relay_sites"]["u_bin_ca_i0/q[0]"] == [100.0, 80.0]


def test_schema_accepts_flag():
    import schema
    assert "relay_spread" in schema.SCHEMA["properties"]


def test_row_mode_is_always_on_and_drops_the_flag(tmp_path):
    plan = _plan({"enable": 0})
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps(plan))
    assert S.main(["--row", str(inp), str(tmp_path / "o.json"), str(tmp_path / "r.json"), "--types", "bk_t"]) == 0
    new = json.loads((tmp_path / "o.json").read_text())
    assert "relay_spread" not in new and A.relay_seats(new["partition_types"]["bk_t"])[1] == []
    assert new["partition_types"]["other"] == plan["partition_types"]["other"]
    rep = json.loads((tmp_path / "r.json").read_text())["types"]["bk_t"]
    assert rep["keys_moved"] > 0 and rep["stack_points_after"] == 0
    assert S.main(["--row", str(inp), str(tmp_path / "o2.json"), str(tmp_path / "r2.json"), "--types", "nope"]) == 0
    assert json.loads((tmp_path / "o2.json").read_text())["partition_types"] == plan["partition_types"]
