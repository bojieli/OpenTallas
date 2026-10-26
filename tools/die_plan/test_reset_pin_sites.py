"""Physical collision controls: no shared entry/output, clocks or macro interiors."""
from types import SimpleNamespace

import pytest

import reset_pin_sites as R


def fixture(monkeypatch, boxes=()):
    p = SimpleNamespace(types={"t": {"outline_um": [100, 100]}})
    monkeypatch.setattr(R.RT, "_snap", lambda _p, x, y: (x, y))
    monkeypatch.setattr(R.RT, "blockages", lambda _t: list(boxes))
    return p


def test_entry_output_and_clock_sites_are_distinct(monkeypatch):
    p = fixture(monkeypatch)
    pins = [("arst_n", 50, 50), ("rst_o_0", 50, 50), ("clk", 47.84, 50)]
    q = R.choose_entry(p, "t", pins)
    assert q != (50, 50) and q != (47.84, 50)
    assert R.conflicts([pins[1], pins[2], ("arst_n", *q)]) == []
    assert R.conflicts(pins) == [("arst_n", "rst_o_0")]


def test_entry_never_moves_into_macro(monkeypatch):
    p = fixture(monkeypatch, [(0, 0, 49, 100)])
    q = R.choose_entry(p, "t", [("arst_n", 50, 50), ("rst_o_0", 50, 50)])
    assert q[0] >= 49


def test_fully_blocked_neighborhood_is_error(monkeypatch):
    p = fixture(monkeypatch, [(0, 0, 100, 100)])
    with pytest.raises(R.RT.ResetError, match="no clear separate"):
        R.choose_entry(p, "t", [("arst_n", 50, 50), ("rst_o_0", 50, 50)])


def test_missing_reset_entry_is_error(monkeypatch):
    p = fixture(monkeypatch)
    with pytest.raises(R.RT.ResetError, match="no reset entry"):
        R.choose_entry(p, "t", [("clk", 50, 50)])
