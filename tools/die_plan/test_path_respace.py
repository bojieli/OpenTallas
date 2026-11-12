"""SEAM-HOP-1: path_respace.py one-pass relay station re-spacing."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import gen  # noqa: E402
import path_respace as PR  # noqa: E402
import schema  # noqa: E402
import seam_hop  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _bunched(xs, stations=3):
    p = copy.deepcopy(EX)
    P = schema.Plan(p)
    y = check.lane_geometry(P, "x")[1][1][1]
    for s in p["partition_types"]["mid"]["ft_slots"]:
        s["regs_um"] = [[x, y] for x in xs]
    return p


def _hops(raw):
    P = schema.Plan(raw)
    geo = {l: check.lane_geometry(P, l) for l in P.lanes}
    return max(r["hop_um"] for r in seam_hop.seam_hops(P, geo)), P


def test_clean_plan_has_no_delta():
    raw2, ops, rep = PR.run(copy.deepcopy(EX))
    assert ops == [] and rep["summary"]["lanes_over"] == 0 and raw2["partition_types"] == EX["partition_types"]


def test_bunched_stations_are_respaced_in_zero_cycles():
    p = _bunched([100.0, 200.0, 300.0])
    assert _hops(p)[0] > 405
    raw2, ops, rep = PR.run(p)
    assert rep["summary"]["by_status"].get("fixed", 0) >= 1 and rep["summary"]["plus_cycle_lanes"] == 0
    assert _hops(raw2)[0] <= 405
    assert {s["stations"] for s in raw2["partition_types"]["mid"]["ft_slots"]} == {3}      # same count, 0 cycles
    assert raw2["latency"] == p["latency"]
    assert all(o[1] == "set" and o[0][0] in ("partition_types", "latency") for o in ops)
    # the delta only edits slot sites: pins, windows and parts are untouched
    assert raw2["ports"] == p["ports"] and raw2["partitions"] == p["partitions"]


def test_too_long_path_adds_one_station_and_a_latency_row_unless_no_add():
    p = copy.deepcopy(EX)
    for s in p["partition_types"]["mid"]["ft_slots"]:
        s["stations"] = 1
    p["latency"]["lanes"] = gen.latency_table(schema.Plan(p))
    P = schema.Plan(p)
    assert max(max(Lane_h) for Lane_h in [PR.Lane.hops(PR.Lane(P, l).start, PR.Lane(P, l).end, PR.Lane(P, l).cross,
                                                       PR.Lane(P, l).stations_now()) for l in P.lanes]) > 405
    raw2, ops, rep = PR.run(copy.deepcopy(p))
    assert rep["summary"]["plus_cycle_lanes"] >= 1 and rep["latency_changed"]
    assert all(v["new_cycles"] == v["old_cycles"] + 1 or v["new_cycles"] > v["old_cycles"] for v in rep["latency_changed"].values())
    _, _, rep0 = PR.run(copy.deepcopy(p), allow_add=False)
    assert rep0["summary"]["plus_cycle_lanes"] == 0 and rep0["summary"]["by_status"].get("needs_add", 0) >= 1
