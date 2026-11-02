"""QW-CLAYER 10-18: dv_layer composition + dv_lower_vec row-order AR landing."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_layer as L        # noqa: E402
import dv_lower_vec as V    # noqa: E402


def test_row_order_windows():
    lw = V.lower_vec('resid', ar_order='row')
    cal = lw['ar_return']
    assert [a['edge'] - lw['ar_r0'] for a in cal] == list(range(256))          # io_collective message order
    assert [a['block'] for a in cal[::8]] == list(range(32))
    ports = [c for c in lw['commands'] if c['label'].startswith('PORTS')]
    assert len(ports) == 64 and not lw['collisions']
    slice_major = V.lower_vec('resid')
    assert slice_major['ar_order'] == 'slice' and len([c for c in slice_major['commands']
                                                       if c['label'].startswith('PORTS')]) == 24


def test_compose_layer():
    r = L.compose(stage=1)
    c = r['composition']
    names = [s['stage'] for s in c['stages']]
    assert len(names) == 13 and names[0].startswith('rmsnorm1') and names[-1].startswith('residual 2')
    for a, b in zip(c['stages'], c['stages'][1:]):
        assert b['start'] >= a['start']
    assert r['calendar']['model']['ok'] and not r['calendar']['clashes'] and not r['calendar']['occupancy_clashes']
    assert c['chained_period'] > 0 and c['l0_cold'] > c['chained_period']
    assert r['capacity']['fits'] is False and any(g.startswith('IMAGE CAPACITY') for g in r['gaps'])
    fams = r['calendar']['families']
    assert all(fams[k] > 0 for k in ('ssq', 'mat', 'qk', 'attn', 'resid1', 'silu', 'resid2'))
    ret = next(s for s in c['stages'] if s['stage'].startswith('attention return'))   # QW-ATTNRET measured span
    att = next(s for s in c['stages'] if s['stage'].startswith('attention (KV'))
    assert ret['start'] == att['end'] and ret['cycles'] == 98
    assert not any(g.startswith(('ATTENTION OUTPUT PATH', 'ATTENTION RETURN')) for g in r['gaps'])
    assert not any(g.startswith('XC ORDER') for g in r['gaps'])                # lowered XC precedes word 0
    assert any(n.startswith('XC ORDER: CLOSED') for n in r['notes'])


def test_die_edges_fold():
    """TOKSIM-QW2 10-20: PRICED die edges inserted at stage boundaries move the chain by exactly their sum"""
    import pytest
    base = L.compose(stage=1)['composition']
    de = {'pre_qkv': [dict(label='a', cycles=4)], 'pre_attn': [dict(label='b', cycles=5)],
          'pre_r2': [dict(label='c', cycles=33), dict(label='zero', cycles=0)]}
    c = L.compose(stage=1, die_edges=de)['composition']
    assert c['chained_period'] == base['chained_period'] + 42 and c['l0_cold'] == base['l0_cold'] + 42
    rows = [s for s in c['stages'] if s.get('die_edge')]
    assert [s['cycles'] for s in rows] == [4, 5, 33] and all(s['grade'] == 'PRICED' for s in rows)
    assert len(c['stages']) == len(base['stages']) + 3
    with pytest.raises(ValueError):
        L.compose(stage=1, die_edges={'nowhere': [dict(label='x', cycles=1)]})


def test_native_second_residual_uses_PS2_without_moving_calendar():
    """Regression: reusing residual timing must not reuse the first post-scale."""
    import dv_lower as D
    fixed=L.compose(stage=1)
    legacy=L.compose(stage=1,correct_residual2=False)
    def residual_calls(rec,phase):
        return [D.decode_cmd(int(e['cmd'],16)) for e in rec['events']
                if e['label'].startswith(phase+':') and D.decode_cmd(int(e['cmd'],16))['kind']==1
                and D.decode_cmd(int(e['cmd'],16))['pidx'] in (1,2)]
    first=residual_calls(fixed,'resid1');second=residual_calls(fixed,'resid2')
    assert len(first)==len(second)==12
    assert {d['pidx'] for d in first}=={1} and {d['pidx'] for d in second}=={2}
    assert fixed['composition']==legacy['composition']
    changes=[(a,b) for a,b in zip(fixed['events'],legacy['events']) if a['cmd']!=b['cmd']]
    assert len(changes)==12 and all(a['edge_w5']==b['edge_w5'] for a,b in changes)
