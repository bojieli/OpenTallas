"""FABLE-FIX-KV-PV class T (11-19): clock.added_taps on a density type.   python3 -m pytest -q tools/die_plan/test_density_added_taps.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import taps  # noqa: E402
from test_density_taps import _no_pins, _plan  # noqa: E402

SITES = [[40.0 + 7.0 * (i % 80), 400.0 + 6.0 * (i // 80), 20.0] for i in range(1600)]


def _base(monkeypatch):
    _no_pins(monkeypatch)
    monkeypatch.setenv("OT_BIND_GATE_CACHE", "off")
    taps._clear_density_cache()
    P = _plan(SITES, tap_max_sinks=1500)
    return P, taps.density_taps(P, "hd")


def test_added_taps_append_and_keep_density_rows(monkeypatch):
    P, base = _base(monkeypatch)
    P.types["hd"]["clock"]["added_taps"] = [dict(name=f"clk_t{len(base)}", xy=[352.0, 420.16]),
                                            dict(name=f"clk_t{len(base) + 1}", xy=[352.0, 460.16])]
    got = taps.density_taps(P, "hd")
    assert got[:len(base)] == base
    assert [r[:3] for r in got[len(base):]] == [(f"clk_t{len(base)}", 352.0, 420.16), (f"clk_t{len(base) + 1}", 352.0, 460.16)]
    assert taps.density_taps(P, "hd", control=False)[:len(base)] == taps._density_base(P, "hd", False)


def test_added_tap_names_continue_density_numbering(monkeypatch):
    P, base = _base(monkeypatch)
    P.types["hd"]["clock"]["added_taps"] = [dict(name=f"clk_t{len(base) + 1}", xy=[352.0, 420.16])]
    with pytest.raises(ValueError, match="names/order"):
        taps.density_taps(P, "hd")


@pytest.mark.parametrize("xy", [[100.0, 100.0],        # on hard core u_a
                                [2.0, 420.0]])         # outside the outline clearance
def test_added_tap_illegal_site_refused(monkeypatch, xy):
    P, base = _base(monkeypatch)
    P.types["hd"]["clock"]["added_taps"] = [dict(name=f"clk_t{len(base)}", xy=xy)]
    with pytest.raises(ValueError, match="violates"):
        taps.density_taps(P, "hd")


def test_added_tap_on_a_density_tap_refused(monkeypatch):
    P, base = _base(monkeypatch)
    P.types["hd"]["clock"]["added_taps"] = [dict(name=f"clk_t{len(base)}", xy=[base[0][1] + 1.0, base[0][2]])]
    with pytest.raises(ValueError, match="violates"):
        taps.density_taps(P, "hd")
