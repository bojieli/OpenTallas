import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import type_safe_event as E  # noqa: E402


def _raw():
    return {"partition_types": {
        "two": {"clock": {"taps": [{"name": "clk_t0"}, {"name": "clk_t1"}], "tap_radius_um": 200.0}},
        "one": {"clock": {"taps": [{"name": "clk_t0"}]}},
        "has": {"clock": {"taps": [{"name": "a"}, {"name": "b"}], "tap_pair_affinity": {"pair_um": 40}}},
        "hard": {"hard": True, "clock": {"taps": [{"name": "a"}, {"name": "b"}]}},
        "skip": {"clock": {"taps": [{"name": "a"}, {"name": "b"}]}},
        "bad": {"clock": {"taps": [{"name": "a"}, {"name": "b"}], "tap_radius_um": -1.0}},
    }}


def test_tap_pair_adds_only_where_missing():
    raw = _raw()
    added, refused = E.tap_pair(raw, {"skip"})
    assert added == ["two"]
    assert [r["type"] for r in refused] == ["bad"]
    T = raw["partition_types"]
    assert T["two"]["clock"]["tap_pair_affinity"] == {}
    assert T["has"]["clock"]["tap_pair_affinity"] == {"pair_um": 40}      # existing config kept
    for tn in ("one", "hard", "skip", "bad"):
        assert "tap_pair_affinity" not in T[tn]["clock"]


def test_style_roundtrip():
    P = {"a": [1, 2], "b": {"c": 1}}
    for text in (json.dumps(P, separators=(",", ":")) + "\n", json.dumps(P) + "\n", json.dumps(P, indent=1) + "\n"):
        assert E._style(text.encode(), P)(P) == text
