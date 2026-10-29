"""Reader segmentation preserves actual action dates and the fixed PRIME gap."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent / 'layer_prog'))
from xs_calendar_pack import split_intervals, END, ACTION_MASK


def fixture(last=228, accept=None):
    # Real failing boundary: previous final action228/end230, launch229.
    raw = [(0, 1), (last, 2), (229, 4), (300, 8), (400, 16)]
    return dict(op='attn.wq_b', packed=[(t << 75) | a for t, a in raw] + [(402 << 75) | END],
                phases=[dict(launch=0, accept=0),
                        dict(launch=229, accept=last if accept is None else accept),
                        dict(launch=400, accept=300)]), raw


def replay(chunks):
    return [(c['start'] + (w >> 75), w & ACTION_MASK)
            for c in chunks for w in c['rows'] if not w & END]


def test_dense_boundary_keeps_reader_active_without_retiming():
    cal, raw = fixture()
    chunks = split_intervals(cal)
    assert [c['start'] for c in chunks] == [0, 228, 300, 400]
    assert replay(chunks) == raw
    assert chunks[0]['end'] < chunks[1]['start'] - 20


def test_existing_idle_boundary_still_rebases():
    cal, raw = fixture(200)
    chunks = split_intervals(cal)
    assert [c['start'] for c in chunks] == [0, 200, 229, 300, 400]
    assert replay(chunks) == raw


def test_zero_action_accept_is_retained():
    cal, raw = fixture()
    raw[1] = (228, 0)
    cal['packed'][1] = 228 << 75
    assert replay(split_intervals(cal)) == raw


def test_accept_outside_reader_still_refused():
    # An accept edge cannot silently disappear into the idle re-prime gap.
    cal, _ = fixture(200, accept=228)
    with pytest.raises(AssertionError):
        split_intervals(cal)


def test_real_idle_inside_phase_is_usable_even_with_adjacent_launch():
    cal, raw = fixture()
    chunks = split_intervals(cal)
    assert 229 not in [c['start'] for c in chunks]
    assert 228 in [c['start'] for c in chunks]
    assert replay(chunks) == raw
