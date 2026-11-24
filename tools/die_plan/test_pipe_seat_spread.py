"""pipe_seat_spread.py (QC-CB-PIPESEAT 11-24): column-stacked delay-pipe seats spread over their street, hops and order kept."""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_seat_spread as S  # noqa: E402

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def _plan(bits=200):
    # two cores 100 um apart: street x 300..400 (grown by 6: 306..394); a 4-deep pipe climbs the street on ONE x column
    rs = {"u_bin_x/q[0]": [10.0, 10.0]}
    for b in range(bits):
        for j in range(4):
            rs[f"u_d4_u_t_0_0_n_y.r[{j}][{b}]"] = [393.5, 200.0 + 150.0 * j + b * 0.2]
        rs[f"u_d4_u_t_0_0_n_y.q[{b}]"] = [393.5, 800.0 + b * 0.2]
    # a stage buried inside core u_a (cleared against a stale box)
    for b in range(bits):
        rs[f"u_d1_u_t_1_0_n_y.r[0][{b}]"] = [250.0, 500.0 + b * 0.2]
        rs[f"u_d1_u_t_1_0_n_y.q[{b}]"] = [250.0, 600.0 + b * 0.2]
    t = {"outline_um": [700.0, 1000.0],
         "hard_cores": [{"inst": "u_a", "origin_um": [0.0, 0.0], "outline_um": [300.0, 1000.0]},
                        {"inst": "u_b", "origin_um": [400.0, 0.0], "outline_um": [300.0, 1000.0]}],
         "relay_sites": rs, "clock": {"taps": {"keep": 1}}}
    return {"partition_types": {"cbn_t": t, "other": {"outline_um": [1, 1], "relay_sites": {}}}}


def _run(tmp_path, plan, *extra):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    out = tmp_path / "out"
    assert S.main([str(p), str(out), "--out-plan", str(tmp_path / "new.json"), *extra]) == 0
    return json.loads((tmp_path / "new.json").read_text()), json.loads((out / "report.json").read_text())


def _cell_max(pts, cell=10.0):
    return max(collections.Counter((int(x // cell), int(y // cell)) for x, y in pts).values())


def test_spread_keeps_hops_order_and_fields(tmp_path):
    plan = _plan()
    new, rep = _run(tmp_path, plan)
    old_t, new_t = plan["partition_types"]["cbn_t"], new["partition_types"]["cbn_t"]
    assert set(rep["types"]) == {"cbn_t"}                      # default set: cb* types with pipe seats
    assert {k: v for k, v in new_t.items() if k != "relay_sites"} == {k: v for k, v in old_t.items() if k != "relay_sites"}
    o, n = old_t["relay_sites"], new_t["relay_sites"]
    assert set(o) == set(n) and n["u_bin_x/q[0]"] == o["u_bin_x/q[0]"]
    pipe = [k for k in o if k.startswith("u_d4_")]
    assert _cell_max([n[k] for k in pipe]) < _cell_max([o[k] for k in pipe]) / 4
    assert len({n[k][0] for k in pipe}) > 10                  # an x grid, not one column
    for k in pipe:
        assert 306.0 <= n[k][0] <= 394.0                      # inside the free street
    for b in range(200):
        ks = [f"u_d4_u_t_0_0_n_y.r[{j}][{b}]" for j in range(4)] + [f"u_d4_u_t_0_0_n_y.q[{b}]"]
        for a, z in zip(ks, ks[1:]):
            assert L1(n[a], n[z]) <= max(405.0, L1(o[a], o[z])) + 1e-6
            assert n[z][1] > n[a][1]                          # stage order along the street kept
    assert len({tuple(n[k]) for k in pipe}) == len(pipe)      # distinct seats


def test_buried_stage_moves_to_street(tmp_path):
    new, rep = _run(tmp_path, _plan())
    n = new["partition_types"]["cbn_t"]["relay_sites"]
    for b in range(200):
        x = n[f"u_d1_u_t_1_0_n_y.r[0][{b}]"][0]
        assert 306.0 <= x <= 394.0
    assert rep["types"]["cbn_t"]["buried_before"] == 400 and rep["types"]["cbn_t"]["buried_after"] == 0


def test_reach_holds_a_group(tmp_path):
    # a 50-um reach: the spread may not lengthen any hop past max(reach, old hop); the stage moves only as far as that allows
    plan = _plan(bits=64)
    new, rep = _run(tmp_path, plan, "--reach", "50", "--types", "cbn_t")
    o = plan["partition_types"]["cbn_t"]["relay_sites"]
    n = new["partition_types"]["cbn_t"]["relay_sites"]
    for b in range(64):
        ks = [f"u_d4_u_t_0_0_n_y.r[{j}][{b}]" for j in range(4)] + [f"u_d4_u_t_0_0_n_y.q[{b}]"]
        for a, z in zip(ks, ks[1:]):
            assert L1(n[a], n[z]) <= max(50.0, L1(o[a], o[z])) + 1e-6
