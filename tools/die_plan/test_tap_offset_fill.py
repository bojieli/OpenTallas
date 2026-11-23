"""TAPOFF-FILL (TAP-GRID-R5 11-23): appended taps get the nearest listed tap's clock.tap_offset row; PRE TAPOFF-MISSING."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402
import tap_offset_fill as TF  # noqa: E402


def _raw():
    return {"clock": {"tap_offset": {"per_port_ps": {"t": {
        "clk": {"TT": 10.0, "FF": 8.0, "tol": 5.0}, "clk_t1": {"TT": -20.0, "FF": -15.0, "tol": 6.0},
        "clk_c0": {"TT": 300.0, "FF": 200.0, "tol": 4.0}}}}},
        "partition_types": {"t": {"clock": {}}, "u": {"clock": {}}}}


def _grid(monkeypatch, sites):
    monkeypatch.setattr(schema, "tap_grid", lambda P, tn: list(sites[tn]))


def test_missing_and_fill_nearest_listed_glue_tap(monkeypatch):
    _grid(monkeypatch, {"t": [("clk", 0.0, 0.0), ("clk_t1", 500.0, 0.0), ("clk_t2", 450.0, 10.0), ("clk_t3", 20.0, 5.0),
                              ("clk_c0", 100.0, 100.0)], "u": [("clk", 0.0, 0.0), ("clk_t1", 9.0, 9.0)]})
    raw = _raw()
    assert TF.missing(raw, P=object()) == {"t": ["clk_t2", "clk_t3"]}      # u has no row: window form, not checked
    done = TF.fill(raw, P=object())
    assert done["t"]["clk_t2"]["from"] == "clk_t1" and done["t"]["clk_t3"]["from"] == "clk"
    tab = raw["clock"]["tap_offset"]["per_port_ps"]["t"]
    assert tab["clk_t2"] == {"TT": -20.0, "FF": -15.0, "tol": 6.0} and tab["clk_t3"] == {"TT": 10.0, "FF": 8.0, "tol": 5.0}
    assert tab["clk_c0"]["TT"] == 300.0 and TF.missing(raw, P=object()) == {}


def test_fill_without_live_glue_rows_uses_zero_and_min_tol(monkeypatch):
    _grid(monkeypatch, {"t": [("clk_t7", 1.0, 1.0)], "u": []})
    raw = _raw()
    done = TF.fill(raw, P=object())
    assert done["t"]["clk_t7"] == {"TT": 0.0, "FF": 0.0, "tol": 4.0, "from": None}


def test_no_table_is_a_noop(monkeypatch):
    _grid(monkeypatch, {"t": [("clk", 0.0, 0.0)]})
    raw = {"clock": {}, "partition_types": {"t": {}}}
    assert TF.missing(raw, P=object()) == {} and TF.fill(raw, P=object()) == {}


def test_pre_check_tapoff_fails_on_missing(monkeypatch, tmp_path):
    import json
    import plan_gate_pre as PG
    _grid(monkeypatch, {"t": [("clk", 0.0, 0.0), ("clk_t1", 500.0, 0.0), ("clk_t2", 450.0, 10.0)], "u": []})
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: object())
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(_raw()))
    out = PG.check_tapoff(str(p))
    assert len(out) == 1 and out[0].startswith("FAIL TAPOFF-MISSING t: 1 ") and "tap_offset_fill.py fill" in out[0]
