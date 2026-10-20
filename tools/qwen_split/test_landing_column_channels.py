"""Actual hard-body movement and reticle accounting for GEN3 landing channels."""
import copy
import math
import pytest
from qwen_split.dv_case import landing_column_channels


def fixture():
    return {'insts': [dict(n=n, x=x, y=y, w=w, h=h)
        for n, x, y, w, h in [
            ('io_collective', 0, 0, 500, 500),
            ('dvs_W0', 1000, 1000, 2462.4, 2592),
            ('c16_W0_0', 1000, 0, 2445.12, 900),
            ('dvs_E0', 3592, 1000, 2462.4, 2592),
            ('c16_E0_0', 3592, 0, 2445.12, 900),
            ('dvs_E1', 6054.4, 1000, 2462.4, 2592),
            ('c16_E1_0', 6054.4, 0, 2445.12, 900)]]}


def test_disabled_is_identical():
    d = fixture(); old = copy.deepcopy(d)
    assert landing_column_channels(d, 0) == []
    assert d == old


def test_real_bodies_follow_column_with_no_resize():
    d = fixture(); old = copy.deepcopy(d)
    rows = landing_column_channels(d, 86.4)
    assert len(rows) == 2
    for before, after in zip(old['insts'], d['insts']):
        column = after['n'][4:].split('_')[0]
        delta = {'W0': 0, 'E0': 86.4, 'E1': 172.8}.get(column, 0)
        assert after['x'] == pytest.approx(before['x'] + delta)
        assert all(after[k] == before[k] for k in ('n', 'y', 'w', 'h'))
    assert min(r['rect'][2] - r['rect'][0] for r in rows) == pytest.approx(86.4)
    assert d['insts'][0] == old['insts'][0]


@pytest.mark.parametrize('gap', [-43.2, 60.48, math.inf, math.nan])
def test_invalid_gap_refused(gap):
    with pytest.raises(ValueError, match='multiple'):
        landing_column_channels(fixture(), gap)


def test_missing_column_fails_closed():
    d = fixture(); d['insts'].append(dict(n='c16_E9_0', x=500, y=4000, w=100, h=100))
    with pytest.raises(ValueError, match='no slice column'):
        landing_column_channels(d, 86.4)
