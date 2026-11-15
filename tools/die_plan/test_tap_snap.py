#!/usr/bin/env python3
"""DIE-ROUTE-ABS-1: python3 -m pytest tools/die_plan/test_tap_snap.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as D  # noqa: E402
import die_unit_obs as U  # noqa: E402


def test_snap_track_lands_on_m8_m9_tracks():
    for v in (2053.088, 11300.064, 1761.524, 0.0, 12.345):
        s = D.snap_track(v)
        k = (s - 0.04) / 0.08
        assert abs(k - round(k)) < 1e-6 and abs(s - v) <= 0.04 + 1e-9
    assert abs(D.snap_track(2053.088) - 2053.08) < 1e-6 and abs(D.snap_track(11300.064) - 11300.04) < 1e-6


def test_snap_is_off_by_default_and_flag_exists():
    import subprocess
    assert D.TAP_PIN_SNAP is False
    out = subprocess.run([sys.executable, "-I", str(Path(D.__file__)), "kit", "--help"], capture_output=True, text=True).stdout
    assert "--snap-tap-pins" in out and "--cut-max-boxes" in out


def test_snap_rect_dbu():
    # a 0.04 x 0.32 M9 pin centred at (2053.088, 11300.064) um moves to the track point, size kept
    r = U.snap_pin_rect((2053068, 11299904, 2053108, 11300224), 1000)
    assert r == (2053060, 11299880, 2053100, 11300200)
