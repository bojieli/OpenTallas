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
