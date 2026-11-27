"""pytest: ADV-STALE-EXPORT-TAP (C-FWDCLK-WRONG-TAP): v6ne pattern (exports kept on a renumbered far tap) + clean control."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_stale_export_tap as A  # noqa: E402

GRID = {"clk": (0.0, 0.0), "clk_t1": (100.0, 100.0), "clk_t82": (1900.0, 1900.0), "clk_t99": (700.0, 1500.0)}


def pin(name, src, xy):
    return {"kind": "clock", "dir": "out", "name": name, "source_clock_port": src, "source_clock_tap": src, "xy_um": xy}


def test_evidence_case_far_renumbered_tap_is_stale():
    # v6ne: exports at the SW corner still sourced from clk_t82 (NE, 1.8 mm); two sourced from the near tap (clean)
    pins = [pin("fclk_out_ft44_o", "clk_t82", [150.0, 120.0]), pin("fclk_out_ft53_o", "clk_t82", [160.0, 120.0]),
            pin("fclk_out_ft10_o", "clk_t1", [150.0, 120.0]), pin("fclk_out_ft11_o", "clk_t99", [660.0, 1518.0])]
    c = A.classify(pins, GRID)
    assert [x[1] for x in c["stale"]] == ["fclk_out_ft44_o", "fclk_out_ft53_o"] or sorted(x[1] for x in c["stale"]) == ["fclk_out_ft44_o", "fclk_out_ft53_o"]
    assert c["stale"][0][3] == "clk_t1" and c["stale"][0][0] > 1500 and not c["dangling"] and not c["nofix"] and c["n"] == 4


def test_clean_control_has_no_hits():
    pins = [pin("a", "clk_t1", [150.0, 120.0]), pin("b", "clk_t99", [700.0, 1400.0]), pin("c", "clk_t82", [1800.0, 1850.0])]
    c = A.classify(pins, GRID)
    assert not c["stale"] and not c["dangling"] and not c["nofix"]


def test_dangling_and_nofix():
    g = {"clk_t1": (0.0, 0.0), "clk_t2": (2000.0, 0.0)}
    c = A.classify([pin("gone", "clk_t77", [50.0, 0.0]), pin("far", "clk_t1", [1000.0, 0.0])], g)
    assert [x[0] for x in c["dangling"]] == ["gone"] and c["dangling"][0][2] == "clk_t1"
    assert [x[1] for x in c["nofix"]] == ["far"]          # clk_t1 and clk_t2 both 1000 um: already nearest (tie -> name), no repoint


def test_limit_boundary_not_flagged():
    c = A.classify([pin("e", "clk_t1", [300.0, 0.0])], {"clk_t1": (0.0, 0.0), "clk_t2": (299.0, 0.0)})
    assert not c["stale"]


def test_findings_end_to_end(monkeypatch, tmp_path):
    import schema as S
    monkeypatch.setattr(S, "Plan", lambda raw, p: object())
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: [(n, x, y) for n, (x, y) in GRID.items()])
    raw = {"partition_types": {
        "bad": {"clock": {"landing_contract": {"pins": [pin("f0", "clk_t82", [150.0, 120.0]), pin("f1", "clk_t1", [150.0, 120.0])]}}},
        "ok": {"clock": {"landing_contract": {"pins": [pin("f0", "clk_t1", [150.0, 120.0])]}}},
        "noexp": {"clock": {}}},
        "partitions": [{"type": "bad"}, {"type": "bad"}, {"type": "ok"}]}
    out = A.findings(raw, str(tmp_path / "p.json"))
    assert out[0].startswith("WARN ADV-STALE-EXPORT-TAP bad: 1 of 2") and "x2 placed" in out[0]
    assert "1 of 2 export types hit; 1 of 3 forwarded-clock export pins" in out[-1] and "2 of 5 per placed instance" in out[-1]
    assert "C-FWDCLK-WRONG-TAP" in out[-1] and all(x.startswith("WARN ") for x in out)


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-STALE-EXPORT-TAP")


# ---- PERF (R3-STALETAP follow-up): geometry-only tap positions, same numbers as schema.tap_grid, plus the calibration pin ----
def _plan(mode, hard=False):
    import types
    return types.SimpleNamespace(types={"t": {"clock": {"tap_mode": mode}, "hard": hard}})


def test_tap_positions_skips_kit_split_validation_for_explicit_modes(monkeypatch):
    import schema as S
    import taps
    rows = [("clk", 1.0, 2.0), ("clk_t1", 3.0, 4.0)]
    monkeypatch.setattr(S, "bare_hard_single_tap", lambda t: False)
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: (_ for _ in ()).throw(AssertionError("full tap_grid must not run")))
    monkeypatch.setattr(taps, "explicit_tap_sites", lambda P, tn: rows, raising=False)
    monkeypatch.setattr(taps, "grid_explicit_sites", lambda P, tn: rows, raising=False)
    for mode in ("explicit", "grid+explicit"):
        assert A.tap_positions(S, _plan(mode), "t") == {"clk": (1.0, 2.0), "clk_t1": (3.0, 4.0)}


def test_tap_positions_other_modes_use_tap_grid(monkeypatch):
    import schema as S
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: [("clk", 5.0, 6.0), ("clk_t1", 7.0, 8.0, 9, 9)][:1] + [("clk_t1", 7.0, 8.0)])
    for mode in ("density", "grid+sinks", None):
        assert A.tap_positions(S, _plan(mode), "t") == {"clk": (5.0, 6.0), "clk_t1": (7.0, 8.0)}


# Calibration pin: (types hit, pins over, per placed instance) of the live plans of 11-27 (sha-verified against the seal trees).
CAL = {"qc_77f2cc98f662": (72, 174, 315), "kv_5bee15cebae2": (72, 534, 688), "s81_c085ccb76d2e": (23, 72, 73), "head_607dd5dd5c82": (0, 0, 0)}


def test_calibration_pin_on_live_plans():
    """OT_STALE_TAP_CAL=<plan.json>:<tree>:<key>[,...] (key in CAL); skipped where the live plans are not on disk."""
    import json
    import re
    spec = os.environ.get("OT_STALE_TAP_CAL")
    if not spec:
        import pytest
        pytest.skip("OT_STALE_TAP_CAL not set")
    for item in spec.split(","):
        plan, tree, key = item.split(":")
        out = A.findings(json.load(open(plan)), plan, tree or None)
        m = re.search(r"(\d+) of \d+ export types hit; (\d+) of \d+ forwarded-clock export pins .*?; (\d+) of \d+ per placed", out[-1])
        assert m, out[-1]
        assert tuple(int(x) for x in m.groups()) == CAL[key], (key, out[-1])


def test_forked_workers_give_the_serial_result(monkeypatch, tmp_path):
    import schema as S
    monkeypatch.setattr(S, "Plan", lambda raw, p: object())
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: [(n, x, y) for n, (x, y) in GRID.items()])
    names = [f"t{i}" for i in range(9)]
    raw = {"partition_types": {n: {"clock": {"landing_contract": {"pins": [pin("f", "clk_t82" if i % 2 else "clk_t1", [150.0, 120.0])]}}}
                               for i, n in enumerate(names)}, "partitions": [{"type": "t1"}, {"type": "t1"}]}
    monkeypatch.setenv("OT_ADV_STALE_TAP_JOBS", "1")
    serial = A.findings(raw, str(tmp_path / "p.json"))
    monkeypatch.setenv("OT_ADV_STALE_TAP_JOBS", "4")
    assert A.findings(raw, str(tmp_path / "p.json")) == serial
    assert "4 of 9 export types hit; 4 of 9 forwarded-clock export pins" in serial[-1]
