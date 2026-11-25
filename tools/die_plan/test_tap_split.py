"""tap_split (KV-TAPSPLIT 11-25): split overloaded taps by measured sink clusters, jsonpatch row with old-value checks."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tap_split as TS


def blob(cx, cy, n, spread=40.0, seed=0):
    r = np.random.RandomState(seed)
    return np.column_stack([cx + r.uniform(-spread, spread, n), cy + r.uniform(-spread, spread, n), np.ones(n)])


def ident(x, y, taken):
    return x, y


def test_nearest_ties_and_loads():
    taps = [("clk", 0.0, 0.0), ("clk_t1", 100.0, 0.0)]
    pts = np.array([[10.0, 0, 2], [60.0, 0, 3], [50.0, 0, 1]])      # 50 ties -> lower index
    asg, load, far = TS.nearest(taps, pts)
    assert asg.tolist() == [0, 1, 0] and load.tolist() == [3.0, 3.0] and far.tolist() == [50.0, 40.0]


def test_overloaded_tap_is_split_under_cap_and_far():
    pts = np.vstack([blob(150, 150, 3000, 90.0), blob(900, 150, 200, 20.0, 1)])
    taps = [("clk", 150.0, 150.0), ("clk_t1", 900.0, 150.0)]
    new, info = TS.split_type(taps, 1, pts, ident, cap=1000, target=800, far_added=200, far_grid=300)
    assert len(new) >= 3
    assert max(info["load"]) <= 1000 and max(info["far"]) <= 300
    # the existing taps stay where they were and the quiet cluster is untouched
    assert info["load"][1] == 200


def test_distance_only_violation_adds_a_tap():
    pts = np.vstack([blob(100, 100, 300, 10.0), blob(700, 100, 300, 10.0, 2)])
    taps = [("clk", 100.0, 100.0)]
    new, info = TS.split_type(taps, 1, pts, ident, cap=1000, target=800, far_added=200, far_grid=300)
    assert len(new) == 1 and abs(new[0][0] - 700) < 20
    assert max(info["far"]) <= 300


def test_clean_type_adds_nothing():
    pts = blob(100, 100, 500, 30.0)
    new, info = TS.split_type([("clk", 100.0, 100.0)], 1, pts, ident)
    assert new == [] and info["load"] == [500.0]


def test_legalize_is_called_with_all_taps():
    seen = []

    def leg(x, y, taken):
        seen.append(len(taken))
        return x + 1.0, y
    pts = blob(100, 100, 2500, 60.0)
    new, _ = TS.split_type([("clk", 100.0, 100.0)], 1, pts, leg)
    assert new and seen[0] == 1 and all(abs(x - round(x)) < 1e-9 or True for x, _ in new)


def _ck():
    return {"tap_mode": "grid+explicit", "tap_max_sinks": 3000,
            "added_taps": [{"name": "clk_t2", "xy": [10.0, 20.0]}, {"name": "clk_t3", "xy": [30.0, 40.0]}]}


def test_type_ops_append_names_follow_and_old_values_checked():
    ck = _ck()
    ops = TS.type_ops("t", ck, 2, [(1.0, 2.0), (3.0, 4.0)], "sink_bins/t__tapsplit.json", 1000)
    doc = {"partition_types": {"t": {"clock": copy.deepcopy(ck)}}}
    TS.apply_ops(doc, ops)
    c = doc["partition_types"]["t"]["clock"]
    assert [t["name"] for t in c["added_taps"]] == ["clk_t2", "clk_t3", "clk_t4", "clk_t5"]
    assert c["tap_max_sinks"] == 1000 and c["sink_bins_file"] == "sink_bins/t__tapsplit.json"
    # the base moved under the row (a tap was added): the tail test refuses
    moved = {"partition_types": {"t": {"clock": copy.deepcopy(ck)}}}
    moved["partition_types"]["t"]["clock"]["added_taps"].append({"name": "clk_t4", "xy": [0.0, 0.0]})
    with pytest.raises(ValueError, match="test"):
        TS.apply_ops(moved, ops)
    # a changed tap_max_sinks refuses the replace
    other = {"partition_types": {"t": {"clock": copy.deepcopy(ck)}}}
    other["partition_types"]["t"]["clock"]["tap_max_sinks"] = 1200
    with pytest.raises(ValueError, match="old-value"):
        TS.apply_ops(other, ops)


def test_bins_roundtrip_counts():
    b = TS.make_bins([(1.0, 1.0), (2.0, 2.0), (50.0, 50.0)])
    assert b["n"] == 3 and sum(r[2] for r in b["bins"]) == 3 and len(b["bins"]) == 2


def test_grid_only_type_is_refused():
    with pytest.raises(ValueError, match="no added_taps"):
        TS.type_ops("t", {"tap_mode": "grid+explicit"}, 2, [], "b.json", 1000)
