"""TOK-S81-4: reader intervals start on each phase's own launch ROW (Q launch advance OT_XS_Q_CPR=1)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'layer_prog'))
import xs_calendar_pack as XP  # noqa: E402
import xs_field_calendar as XF  # noqa: E402

FP8 = ['attn.wq_b', 'attn.wo_b', 'ffn.shared_gu', 'ffn.experts_gu', 'ffn.down']


def cal(op, qcpr, nb=None):
    old = os.environ.get('OT_XS_Q_CPR')
    os.environ['OT_XS_Q_CPR'] = qcpr
    try:
        ph, st = XF._synthetic(op, 6, **({} if nb is None else dict(nb=nb)))
        return XF.op_calendar(op, ph, st, range(6))
    finally:
        if old is None:
            os.environ.pop('OT_XS_Q_CPR', None)
        else:
            os.environ['OT_XS_Q_CPR'] = old


def replay(chunks):
    return [(c['start'] + (w >> 75), w & XP.ACTION_MASK) for c in chunks for w in c['rows'] if not w & XP.END]


def raw(c):
    return [(w >> 75, w & XP.ACTION_MASK) for w in c['packed'] if not w & XP.END]


def split(c, qcpr):
    old = os.environ.get('OT_XS_Q_CPR')
    os.environ['OT_XS_Q_CPR'] = qcpr
    try:
        return XP.split_intervals(c)
    finally:
        if old is None:
            os.environ.pop('OT_XS_Q_CPR', None)
        else:
            os.environ['OT_XS_Q_CPR'] = old


def test_q_advance_interval_starts_on_launch_row_all_fp8_ops():
    for op in FP8:
        c = cal(op, '1')
        ch = split(c, '1')
        assert [x['start'] for x in ch][1:] == [p['launch'] - 1 for p in c['phases'][1:]], op
        assert replay(ch) == raw(c), op
        assert all(a['end'] < b['start'] - 20 for a, b in zip(ch, ch[1:])), op
        # each interval's first row is its phase's launch row (relative 0)
        assert all(x['rows'][0] >> 75 == 0 for x in ch[1:]), op


def test_default_q_no_advance_byte_identical_starts():
    for op in FP8 + ['attn.wo_a', 'ffn.router']:
        c = cal(op, '0')
        ch = split(c, '0')
        assert [x['start'] for x in ch][1:] == [p['launch'] for p in c['phases'][1:]], op
        assert replay(ch) == raw(c), op


def test_bf16_unaffected_by_q_cpr():
    for op in ['attn.wo_a', 'ffn.router']:
        c = cal(op, '1')
        assert [x['start'] for x in split(c, '1')][1:] == [p['launch'] for p in c['phases'][1:]], op


def test_old_launch_boundary_mutant_faults():
    # control: the pre-fix boundary (launch_n) under Q advance reproduces the real fault class
    c = cal('attn.wq_b', '1')
    mut = dict(c, fam='bf16')         # lead 0 -> interval starts at launch_n, launch row at launch_n-1 stays behind
    try:
        split(mut, '1')
    except AssertionError as e:
        assert 'no fixed PRIME gap' in str(e)
    else:
        raise AssertionError('old launch boundary not caught')


def test_layer_pack_q_advance():
    old = os.environ.get('OT_XS_CAL_SEGMENT')
    os.environ['OT_XS_CAL_SEGMENT'] = '1'
    os.environ['OT_XS_Q_CPR'] = '1'
    try:
        lc = XF.layer_calendar([cal('attn.wo_b', '1'), cal('ffn.down', '1')])
        assert lc['PASS']
    finally:
        os.environ.pop('OT_XS_Q_CPR', None)
        if old is None:
            os.environ.pop('OT_XS_CAL_SEGMENT', None)
        else:
            os.environ['OT_XS_CAL_SEGMENT'] = old


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); n += 1; print('PASS', k)
    print('ALL PASS', n)
