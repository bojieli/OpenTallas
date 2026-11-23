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
    # LOO p95: clk predicted by clk_t1 -> |err| 30 / 23 and back: p95 = 30.0 > the copied tols
    assert tab["clk_t2"] == {"TT": -20.0, "FF": -15.0, "tol": 30.0} and tab["clk_t3"] == {"TT": 10.0, "FF": 8.0, "tol": 30.0}
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
    assert len(out) == 1 and out[0].startswith("FAIL TAPOFF-MISSING t: 1 ") and "tap_offset_cover.py fill" in out[0]


def test_loo_p95_single_tap_is_zero():
    assert TF.loo_p95({"clk": {"TT": 1.0, "FF": 1.0, "tol": 2.0}}, {"clk": (0.0, 0.0)}) == 0.0


def test_missing_records_unsolvable_type(monkeypatch):
    def tg(P, tn):
        raise ValueError("explicit tap clk_t9 violates outline")
    monkeypatch.setattr(schema, "tap_grid", tg)
    err = {}
    assert TF.missing(_raw(), P=object(), errors=err) == {} and "clk_t9" in err["t"]


def test_pre_check_tapoff_covers_window_form_and_grid_explicit(monkeypatch, tmp_path):
    """TAPOFF-ALL (TAP-GRID-R6): PRE reads every tap mode and the window form, and names added taps of an unsolvable grid."""
    import json
    import plan_gate_pre as PG
    raw = {"clock": {"tap_window": {"per_port_ps": {"w": {"clk": 40, "clk_t1": 30}}}},
           "partition_types": {"w": {"clock": {"tap_mode": "grid+explicit"}},
                               "x": {"clock": {"tap_mode": "grid", "added_taps": [{"name": "clk_t9", "xy": [1, 1]}]}}}}
    raw["clock"]["tap_window"]["per_port_ps"]["x"] = {"clk": 20}

    def tg(P, tn):
        if tn == "x":
            raise ValueError("added tap clk_t9 violates spacing")
        return [("clk", 0.0, 0.0), ("clk_t1", 100.0, 0.0), ("clk_t2", 50.0, 0.0)]
    monkeypatch.setattr(schema, "tap_grid", tg)
    monkeypatch.setattr(schema, "core_taps", lambda P, tn: [])
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: object())
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw))
    out = PG.check_tapoff(str(p))
    fails = sorted(o for o in out if o.startswith("FAIL"))
    assert len(fails) == 2, out
    assert fails[0].startswith("FAIL TAPOFF-MISSING w: 1 grid+explicit-mode") and "tap_window" in fails[0]
    assert fails[1].startswith("FAIL TAPOFF-MISSING x: 1 grid-mode") and "lower bound" in fails[1]
