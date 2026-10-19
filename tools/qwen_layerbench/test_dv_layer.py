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
