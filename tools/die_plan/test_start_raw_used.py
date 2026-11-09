"""A plan START stage naming rr_t<i> gets the raw copy of a gated (mission) tap; without a request nothing changes."""
import json
from pathlib import Path

import reset_tree as RT
import schema as S

HERE = Path(__file__).parent


def plan():
    p = json.loads((HERE / "examples/tiny_plan.json").read_text())
    p["reset"].update(release="wavefront", start="broadcast")
    for ty in p["partition_types"].values():
        ty.pop("sources", None)
    return p


def relays(p):
    return {r["q"]: r for r in RT.start_relays(RT.for_type(S.Plan(p), "mid"))}


def test_requested_raw_tap_has_same_d_and_depth_as_gated_tap():
    base = plan()
    gated = relays(base)["rst_n_t0"]
    assert gated["role"] == "gated" and "rr_t0" not in relays(base)
    p = plan()
    p["partition_types"]["mid"].setdefault("clock", {})["landing_writer_start"] = {
        "branches": {"x": {"stages": [{"xy_um": [1, 1], "raw_reset": "rr_t0"}]}}}
    got = relays(p)
    assert got["rr_t0"]["role"] == "raw" and "run" not in got["rr_t0"]
    assert got["rr_t0"]["d"] == got["rst_n_t0"]["d"] and got["rr_t0"]["depth"] == got["rst_n_t0"]["depth"]
    assert got["rst_n_t0"]["role"] == "gated"


def test_request_scan_ignores_ordinary_tap_names():
    t = {"clock": {"landing_reader_start": {"branches": {"a": {"stages": [{"raw_reset": "rst_n_t3"}, {"raw_reset": "rr_t7"}]}}}}}
    assert RT.start_raw_requests(t) == ["rr_t7"]
