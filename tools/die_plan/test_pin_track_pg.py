"""pytest: C-PIN-TRACK-PG (pin_track_pg): default off, PG pitch snap, blocked pins, report-only findings."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pin_track_pg as P  # noqa: E402


def _t(origin, n=20):
    return {"hard_cores": [{"inst": "c", "origin_um": origin, "outline_um": [100.0, 100.0], "orient": "R0", "pins_file": "p"}]}


def _pins(c):   # M4 pins every 0.108 um along x from the W face region (horizontal pins ending at x)
    return [("M4", 2.16 + 0.108 * i, 10.0) for i in range(40)]


def test_flag_default_off():
    assert P.enabled({}) is False and P.enabled({"pin_track_pg": {"pg": 0}}) is False
    assert P.findings({"partition_types": {"T": _t([2.592, 0.0])}}, pins_for=_pins) == []
    assert P.enabled({"pin_track_pg": {"pg": 1}})


def test_snap_and_pitch():
    assert P.on_pitch(4.32) and P.on_pitch(8.64) and not P.on_pitch(2.592)
    assert P.snap_origin([2.592, 4.4]) == [2.16 * 2 if False else 4.32, 4.32]
    assert P.snap_origin([2.592, 4.4], "down") == [0.0, 4.32]
    assert P.snap_origin([2.592, 4.4], "up") == [4.32, 8.64]


def test_free_tracks_excludes_pg_bands():
    xs = [2.16, 2.3, 3.0, 4.32 + 2.16]
    assert P.pin_blocked("M5", 2.16) and not P.pin_blocked("M5", 3.0)
    assert P.free_tracks("M4", xs) == [x for x in xs if not P.pin_blocked("M4", x)]
    assert 2.16 not in P.free_tracks("M4", xs)


def test_census_and_findings_report_off_pitch():
    raw = {"partition_types": {"T": _t([2.592, 0.0])}, "pin_track_pg": {"pg": 1}}
    a = P.census(raw["partition_types"]["T"], _pins)
    assert a["cores"] == 1 and a["off_pitch"] == 1 and a["pdn_0110_est"] == a["blocked"]
    b = P.census(raw["partition_types"]["T"], _pins, snap=True)
    assert b["off_pitch"] == 0 and b["pdn_0110_est"] == 0
    out = P.findings(raw, pins_for=_pins)
    assert out[0].startswith("WARN ADV-PIN-TRACK-PG T:") and out[-1].startswith("WARN ADV-PIN-TRACK-PG summary 1")


def test_clean_on_pitch_type_not_flagged():
    raw = {"partition_types": {"T": _t([4.32, 8.64])}, "pin_track_pg": {"pg": 1}}
    assert not [x for x in P.findings(raw, pins_for=_pins) if " T:" in x]


def test_malformed_never_raises():
    raw = {"partition_types": {"bad": {"hard_cores": [{"origin_um": "x", "outline_um": [1, 1]}]}}, "pin_track_pg": {"pg": 1}}
    assert P.findings(raw, pins_for=_pins)[-1].startswith("WARN ADV-PIN-TRACK-PG summary")


def test_preflight_resolves_pin_tables_from_exact_tree(tmp_path):
    import json
    import plan_advisory

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "p").write_text(json.dumps([{"layer": "M4", "x": 1.0, "y": 10.0}]))
    plan = tmp_path / "detached" / "die_plan.json"
    raw = {"partition_types": {"T": _t([2.592, 0.0])}, "pin_track_pg": {"pg": 1}}
    pre = plan_advisory.run(raw, plan, tree=tree, checks=["PIN-TRACK-PG"], jobs=1)
    assert any("T: 1/1 hard core origin(s)" in line for line in pre)
    assert any("0 declared pin table uses unavailable or empty" in line for line in pre)
    missing = plan_advisory.run(raw, plan, checks=["PIN-TRACK-PG"], jobs=1)
    assert any("1 declared pin table uses unavailable or empty" in line for line in missing)


def test_absolute_pin_table_does_not_need_plan_path(tmp_path):
    import json

    f = tmp_path / "pins.json"
    f.write_text(json.dumps([{"layer": "M4", "x": 1.0, "y": 10.0}]))
    t = _t([2.592, 0.0])
    t["hard_cores"][0]["pins_file"] = str(f)
    report = P.findings({"partition_types": {"T": t}, "pin_track_pg": {"pg": True}})
    assert "T: 1/1 hard core origin(s)" in report[0]
