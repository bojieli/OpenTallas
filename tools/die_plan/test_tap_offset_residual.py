"""R-CLOCK-7 tap_offset_table: the T/2 bound applies to a core tap's RESIDUAL (offset + insertion - common), not its raw offset."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402


class FakeP:
    def __init__(self, rows, seam=True):
        self.die = {"period_ps": 833}
        self.clock = {"seam_hold": {"x": 1}} if seam else {}
        self.clock["tap_offset"] = {"per_port_ps": {"t": rows}}


def _patch(monkeypatch, core_ins):
    monkeypatch.setattr(G.S, "core_taps", lambda P, tn: [(n, 0, 0, {"name": n, "ins": v}) for n, v in core_ins.items()])
    monkeypatch.setattr(G.S, "core_tap_insertion_ps", lambda tp, corner="TT": tp["ins"][0 if corner == "TT" else 1])
    monkeypatch.setattr(G.S, "common_latency_ps", lambda P, corner="TT", t=None: 250.0 if corner == "TT" else 200.0)


def test_core_tap_beyond_half_period_raw_ok_when_residual_small(monkeypatch):
    _patch(monkeypatch, {"clk_c0": (848.98, 671.43)})
    P = FakeP({"clk_c0": {"TT": -550.2, "FF": -490.8, "tol": 0.0}})
    out = G.tap_offset_table(P, "t")
    assert out["clk_c0"]["TT"] == -550.2   # residual TT = -550.2 + 598.98 = +48.8 ; FF = -490.8 + 471.43 = -19.4


def test_core_tap_residual_too_large_fails(monkeypatch):
    _patch(monkeypatch, {"clk_c0": (848.98, 671.43)})
    P = FakeP({"clk_c0": {"TT": 100.0, "FF": 0.0, "tol": 0.0}})   # residual TT = 698.98 > 416.5
    with pytest.raises(ValueError, match="residual"):
        G.tap_offset_table(P, "t")


def test_glue_port_keeps_raw_bound(monkeypatch):
    _patch(monkeypatch, {"clk_c0": (848.98, 671.43)})
    P = FakeP({"clk_t5": {"TT": -450.0, "FF": 0.0, "tol": 0.0}})
    with pytest.raises(ValueError):
        G.tap_offset_table(P, "t")
    P2 = FakeP({"clk_t5": {"TT": -300.0, "FF": 0.0, "tol": 5.0}})
    assert G.tap_offset_table(P2, "t")["clk_t5"]["tol"] == 5.0


def test_span_uses_core_tap_residual_cbx_q10(monkeypatch):
    """QC-CBX-CLOCK 11-24: cbx_q10__cl89936551 (plan f418c1b290f3) clk_c1 raw row -449.95 (early delivery TT 524.38 / FF 408.09)
    gave W = 45.05 - (-465.1) = 510.2 on every port without a row (core taps early -1078.3): setup -520 / hold -534 at CTS.
    The span is over residuals: clk_c1 TT +74.43 (+-15.15) -> W = 89.58 - (-23.4) = 113.0 (122.3 with all 140 rows of the plan)."""
    _patch(monkeypatch, {"clk_c1": (774.38, 610.59)})
    monkeypatch.setattr(G.S, "common_latency_ps", lambda P, corner="TT", t=None: 250.0 if corner == "TT" else 202.5)
    rows = {"clk_c1": {"TT": -449.95, "FF": -387.55, "tol": 15.15}, "clk_t57": {"TT": -11.45, "FF": -10.1, "tol": 11.95},
            "clk_t18": {"TT": 19.35, "FF": 19.3, "tol": 25.7}, "clk_t24": {"TT": 17.15, "FF": 23.25, "tol": 26.35}}
    P = FakeP(rows)
    w = G.tap_offset_span_ps(P, "t")
    assert w == pytest.approx(113.0, abs=0.1)
    assert w < 150.0                                              # was 510.2 with the raw core-tap row
    assert G.tap_offset_table(P, "t")["clk_c1"]["TT"] == -449.95  # the emitted row stays raw (o - u, o + u)


def test_span_without_core_rows_unchanged(monkeypatch):
    _patch(monkeypatch, {"clk_c0": (848.98, 671.43)})
    P = FakeP({"clk_t1": {"TT": -12.5, "FF": -14.0, "tol": 10.0}, "clk_t2": {"TT": 20.0, "FF": 18.0, "tol": 15.0}})
    assert G.tap_offset_span_ps(P, "t") == 57.5


def test_span_never_wider_than_raw(monkeypatch):
    """a core tap the spine does not deliver early (raw row ~0, residual = its early delivery): W stays the raw span."""
    _patch(monkeypatch, {"clk_c0": (450.0, 364.5)})
    P = FakeP({"clk_c0": {"TT": 5.0, "FF": 4.0, "tol": 10.0}, "clk_t1": {"TT": -12.5, "FF": -14.0, "tol": 10.0}})
    assert G.tap_offset_span_ps(P, "t") == 38.0     # raw FF 14 - (-24); residual span would be 237.5
