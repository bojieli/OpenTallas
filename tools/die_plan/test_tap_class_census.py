"""pytest: C-TAP-LOAD census reads the kit's per-type tap gate (gen_phys._tap_cap) and reports UNDER-LOAD taps."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tap_class_census as C  # noqa: E402


def _tile(**clock):
    return {"outline_um": [100.0, 100.0], "clock": {"tap_mode": "explicit", **clock}}


def test_gate_is_plan_cap_not_constant(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    assert C.kit_gate(_tile(tap_max_sinks=800))[0] == 800
    assert C.kit_gate(_tile(tap_max_sinks=3000))[0] == 3000
    assert C.kit_gate(_tile())[0] == 3000                                   # grid default
    assert C.kit_gate(_tile(tap_mode="density"))[0] == 1500                 # density default
    assert C.kit_gate(_tile(tap_max_sinks=3000, tap_grid={"pitch_um": 300}))[0] == 1000   # bank_sinks clamp


def test_gen_env_overrides_plan_cap(monkeypatch):
    monkeypatch.setenv("OT_TAP_MAX_SINKS", "1500")
    assert C.kit_gate(_tile(tap_max_sinks=3000))[0] == 1500


def test_under_floor_sources(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    assert C.kit_gate(_tile(tap_max_sinks=1000)) == (1000, 50)              # cap // 20
    assert C.kit_gate(_tile(tap_max_sinks=1000, tap_min_sinks=7))[1] == 7
    assert C.kit_gate(_tile(tap_max_sinks=1000, tap_min_sinks=7, tap_post_merge_min_sinks=16))[1] == 16


def test_placement_counts_under_and_over(monkeypatch):
    plan = types.SimpleNamespace(types={"T": _tile(tap_max_sinks=1000)})
    sites = [("a", 0, 0), ("b", 50, 50), ("c", 99, 99)]
    monkeypatch.setattr(C.taps, "explicit_tap_sites", lambda p, tn: sites)
    placed = {"die_um": [100.0, 100.0], "bins": [[0, 0, 1500], [50, 50, 10], [99, 99, 400]], "kit": "k"}
    r = C.placement_load(plan, "T", placed, floor=50)
    assert r["predicted_max_sinks"] == 1500 and r["predicted_min_sinks"] == 10
    assert r["predicted_under_taps"] == 1 and r["predicted_taps"] == 3


def test_census_tallies_use_per_type_gate(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    mk = lambda cap: _tile(tap_max_sinks=cap)  # noqa: E731
    plan = types.SimpleNamespace(name="D", path="p", types={"A": mk(1000), "B": mk(3000)},
                                 parts={"i": {"type": "A"}, "j": {"type": "B"}})
    meas = {"A": {"max_sinks": 1200}, "B": {"max_sinks": 1200}}
    res = C.census(plan, {}, meas)
    assert res["measured"] == {"samples": 2, "over_cap": 1}                 # A over its 1000 gate, B under 3000
    assert res["gates"] == {1000: 1, 3000: 1}
    assert C.census(plan, {}, meas, cap=5000)["measured"]["over_cap"] == 0   # old constant gate still selectable
