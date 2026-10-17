"""Fail closed on unconstrained timing and impossible FF hold windows."""
import math
import pytest
from relay_reach_bench import finite_float, read_slk, hold_min, class_reach

@pytest.mark.parametrize('value', ['inf', '-inf', 'nan', 'unconstrained'])
def test_unconstrained_rejected(value):
    with pytest.raises(ValueError):
        finite_float(value)

def test_partial_invalid_slack_preserves_failure(tmp_path):
    p = tmp_path / 'slk'
    p.write_text('B/i[0] inf 12\nB/i[1] 7 13\n')
    assert read_slk(p)['B/i[0]'][0] is None
    assert read_slk(p)['B/i[1]'][0] == 7

def test_no_hold_window_is_not_zero_length_permission():
    rows = [(100, 100, -3, 'B/i[0]', 'o->i'), (200, 200, -1, 'B/i[0]', 'o->i')]
    assert hold_min(rows)['hold_min_um'] is None

def test_setup_reach_stops_at_first_failing_short_point():
    rows = [(100, 100, 4, 'B/i[0]', 'o->i'), (200, 200, -1, 'B/i[0]', 'o->i'),
            (300, 300, 1, 'B/i[0]', 'o->i')]
    assert class_reach(rows, 'unused')['reach_um'] == 100


def test_hold_does_not_claim_untested_short_wire_is_safe():
    rows = [(100, 100.1, 4, 'B/i[0]', 'o->i'), (200, 200, 5, 'B/i[0]', 'o->i')]
    assert hold_min(rows)['hold_min_um'] == 100.1
