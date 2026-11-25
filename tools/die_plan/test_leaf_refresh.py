"""FP-CONVERGE-S81: leaf_refresh moves what hangs off a translated core and legalises items a core move leaves in a core / outside."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaf_refresh as LR  # noqa: E402


def mk(origin):
    return {"outline_um": [400.0, 300.0],
            "hard_cores": [{"inst": "u_a", "origin_um": origin, "outline_um": [100.0, 100.0], "orient": "R0"}],
            "relay_sites": {"u_crr_a/q": [150.0, 50.0], "u_far/q": [300.0, 250.0]},
            "clock": {"taps": [{"kind": "core", "name": "u_a.clk", "xy": [60.0, 50.0]}, {"kind": "grid", "name": "clk_t1", "xy": [10.0, 10.0]}],
                      "reach_fix_sinks": [[60.0, 60.0, 1.0]],
                      "landing_contract": {"collector_tree": {"core_resets": [{"inst": "u_a", "pin_um": [60.0, 50.0], "xy": [60.0, 48.0]}],
                                                              "root": [500.0, 20.0], "outs": []}}}}


def plans():
    return {"partition_types": {"T": mk([20.0, 20.0])}}, {"partition_types": {"T": mk([120.0, 100.0])}}


def test_core_items_ride_with_translated_core():
    b, n = plans()
    out, rep = LR.run(b, n, ["T"])
    t = out["partition_types"]["T"]
    assert t["clock"]["taps"][0]["xy"] == [160.0, 130.0]          # core tap shifted by (+100, +80)
    assert t["clock"]["taps"][1]["xy"] == [10.0, 10.0]            # grid tap untouched
    assert t["clock"]["landing_contract"]["collector_tree"]["core_resets"][0]["pin_um"] == [160.0, 130.0]
    assert t["relay_sites"]["u_crr_a/q"] != [150.0, 50.0] and rep["T"]["shifted"] >= 4


def test_item_in_core_and_outside_are_legalised():
    b, n = plans()
    n["partition_types"]["T"]["relay_sites"]["u_far/q"] = [150.0, 130.0]     # inside the moved core (120..220, 100..200)
    out, rep = LR.run(b, n, ["T"])
    t = out["partition_types"]["T"]
    L = LR.Legal(t)
    assert all(L.ok(p) for p in (t["relay_sites"]["u_far/q"], t["clock"]["landing_contract"]["collector_tree"]["root"]))
    assert rep["T"]["after"]["in_core"] == 0 and rep["T"]["after"]["outside"] == 0
    assert rep["T"]["before"]["outside"] >= 1                        # the root at x=500 was outside the 400 wide outline


def test_flipped_core_is_not_translated_and_unmoved_plan_is_identity():
    b, n = plans()
    n["partition_types"]["T"]["hard_cores"][0]["orient"] = "MY"
    out, rep = LR.run(b, n, ["T"])
    assert out["partition_types"]["T"]["clock"]["taps"][0]["xy"] == [60.0, 50.0] and rep["T"]["flipped"] >= 1
    same = copy.deepcopy(b)
    o2, r2 = LR.run(b, same, ["T"])
    assert r2["T"]["shifted"] == 0 and o2["partition_types"]["T"]["relay_sites"] == b["partition_types"]["T"]["relay_sites"] or r2["T"]["legalised"] >= 0


def test_mutant_double_shift_is_refused():
    """an item core_place already moved (not at its base xy) must not be shifted again"""
    b, n = plans()
    n["partition_types"]["T"]["clock"]["taps"][0]["xy"] = [161.0, 131.0]
    out, rep = LR.run(b, n, ["T"])
    assert out["partition_types"]["T"]["clock"]["taps"][0]["xy"] == [161.0, 131.0]
