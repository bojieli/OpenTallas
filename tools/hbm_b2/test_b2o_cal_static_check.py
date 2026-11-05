#!/usr/bin/env python3
"""Tests for b2o_cal_static_check.py: clean images PASS; each planted violation is caught (mutants)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_cal_static_check as K  # noqa: E402

F = K.field_layout()


def word(pc, **v):
    w = (0xc7a1 << 240) | (pc << 224)
    for n, val in v.items():
        lo, bits = F[n]
        assert 0 <= val < 1 << bits
        w |= val << lo
    return dict(addr=pc, data=f'{w:064x}')


def grants(owner_by_bank, bits=3):
    v = o = 0
    for b, own in owner_by_bank.items():
        v |= 1 << b
        o |= own << (b * bits)
    return v, o


def prog(words):
    return dict(configuration_writes=words, start=dict(base=0, limit=len(words), loops=1))


def clean_s():
    rv, rs = grants({0: 4, 3: 5})          # IDX read + packet
    wv, ws = grants({1: 3, 2: 4, 5: 5})    # cw, packet, ccw
    return [word(0, rslot_v=rv, rslot=rs, wslot_v=wv, wslot=ws), word(1)]


def m(cals=(), qctl=()):
    return dict(calendars=list(cals), qctl=list(qctl))


def S(words, allow=None):
    e = dict(name='NW.u_calendar_Q_q0', role='S', programme=prog(words))
    if allow:
        e['allow_group0'] = allow
    return e


def t_clean():
    r = K.run(m([S(clean_s())], [dict(name='q0', role='S', nkeys=0, base=0)]))
    assert r['verdict'] == 'PASS', r


def t_group0_read():
    rv, rs = grants({2: 0})
    r = K.run(m([S(clean_s() + [word(2, rslot_v=rv, rslot=rs)])]))
    assert [x['kind'] for x in r['findings']] == ['S_GROUP0_READ'], r


def t_group0_write():
    wv, ws = grants({7: 0})
    r = K.run(m([S([word(0, wslot_v=wv, wslot=ws)])]))
    assert [x['kind'] for x in r['findings']] == ['S_GROUP0_WRITE'], r


def t_fused_allowed():
    rv, rs = grants({2: 0})
    wv, ws = grants({2: 0})
    r = K.run(m([S([word(0, rslot_v=rv, rslot=rs, wslot_v=wv, wslot=ws)], dict(read=[0], write=[0]))]))
    assert r['verdict'] == 'PASS' and r['counts']['s_group0_read'] == 1, r


def t_dq():
    wv, ws = grants({4: K.DQ_OWNER})
    r = K.run(m([S([word(0, wslot_v=wv, wslot=ws)])]))
    assert [x['kind'] for x in r['findings']] == ['S_DQ_FILL'], r


def t_lg():
    r = K.run(m([S([word(0, lg_local_read=1)])]))
    assert [x['kind'] for x in r['findings']] == ['S_LG_LOCAL'], r


def t_qctl():
    r = K.run(m(qctl=[dict(name='q0', role='S', nkeys=5, base=0)]))
    assert r['findings'][0]['kind'] == 'S_QCTL_NQ' and r['findings'][0]['nq'] == 5, r
    assert K.run(m(qctl=[dict(name='q0', role='S', nkeys=5, base=5)]))['verdict'] == 'PASS'


def t_n_role_free():
    rv, rs = grants({0: 0})
    wv, ws = grants({0: K.DQ_OWNER})
    r = K.run(m([dict(name='NW.u_calendar_Q_q1', role='N', programme=prog([word(0, rslot_v=rv, rslot=rs, wslot_v=wv, wslot=ws)]))]))
    assert r['verdict'] == 'PASS', r


def t_header():
    w = word(0)
    w['data'] = '0' + w['data'][1:]
    r = K.run(m([S([w])]))
    assert r['findings'][0]['kind'] == 'HEADER', r


def t_unused_allow():
    r = K.run(m([S(clean_s(), dict(read=[9]))]))
    assert r['findings'][0]['kind'] == 'ALLOW_UNUSED_PC', r


def t_outside_start_range():
    rv, rs = grants({0: 0})
    p = prog([word(0), word(1, rslot_v=rv, rslot=rs)])
    p['start']['limit'] = 1
    assert K.run(m([dict(name='c', role='S', programme=p)]))['verdict'] == 'PASS'


def t_empty():
    try:
        K.run(m())
    except ValueError:
        return
    raise AssertionError('empty manifest accepted')


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('t_')]
    for t in tests:
        t()
    print(f'PASS {len(tests)} tests')
