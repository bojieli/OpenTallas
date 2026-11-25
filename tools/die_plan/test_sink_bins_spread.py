"""TAPBINS pass 2: sink_bins_spread moves the excess of over-full bins outward to placeable bins, total unchanged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sink_bins_spread as SP  # noqa: E402


def test_cap_matches_compose_density():
    assert SP.bin_cap(10.8) == 201


def test_spread_keeps_total_and_caps_bins():
    bins = [[5.4, 5.4, 1000.0], [16.2, 5.4, 50.0]]
    nb, rep = SP.spread(bins, 10.8, (108.0, 108.0), cap=200)
    assert rep["n"] == 1050 and rep["stuck"] == 0 and rep["max_bin_before"] == 1000 and rep["max_bin_after"] == 200
    assert abs(sum(c for *_, c in nb) - 1050) < 1e-6
    assert all(0 <= x <= 108 and 0 <= y <= 108 for x, y, _ in nb)


def test_spread_avoids_macros_and_keeps_native():
    box = [(10.8, 0.0, 108.0, 108.0)]                 # everything right of x 10.8 is a macro: only the x 0..10.8 column
    nb, rep = SP.spread([[5.4, 5.4, 600.0]], 10.8, (108.0, 108.0), box, cap=200)
    assert all(x < 10.8 for x, _, _ in nb) and rep["max_bin_after"] == 200 and rep["n"] == 600
    nb, rep = SP.spread([[5.4, 5.4, 300.0]], 10.8, (108.0, 108.0), native=[[5.4, 5.4, 300.0]], cap=200)
    assert rep["moved"] == 0 and nb == [[5.4, 5.4, 300.0]]     # a native bin denser than the cap stays as placed


def test_spread_reports_stuck():
    nb, rep = SP.spread([[5.4, 5.4, 500.0]], 10.8, (10.8, 10.8), cap=200)
    assert rep["stuck"] == 300 and rep["n"] == 500
