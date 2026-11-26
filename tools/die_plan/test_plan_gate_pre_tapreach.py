"""TAPREACH / STALETABLE wiring in plan_gate_pre (QC-INT-R2-TOOLS 11-26): classes known to --skip, checks return report-only lines."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402


def test_classes_registered():
    assert "TAPREACH" in G.CLASSES and "STALETABLE" in G.CLASSES


def test_check_functions_use_cached_tap_sites(tmp_path, monkeypatch):
    raw = {"die": {"name": "d"}, "partition_types": {"T": {"outline_um": [100, 100], "clock": {"tap_radius_um": 50.0,
           "landing_contract": {"collector_tree": {"relays": [{"name": "r", "xy": [90.0, 90.0]}]}}}}}}
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps(raw))
    calls = []
    import tap_reach as TR

    def fake(raw_, plan_, tns=None, mapper=None):
        calls.append(sorted(tns))
        return {"T": ({"clk": (10.0, 10.0)}, set(), None)}
    monkeypatch.setattr(TR, "solve_tap_sites", fake)
    G._TAPSITES_CACHE.clear()
    a = G.check_tapreach(str(plan))
    b = G.check_staletable(str(plan))
    assert calls == [["T"]]                                  # one solve for both checks
    assert a[0].startswith("WARN TAPREACH T: 1 of 1 FIRM seat(s)") and a[-1].startswith("LIST TAPREACH")
    assert b[-1].startswith("LIST STALETABLE die d")
