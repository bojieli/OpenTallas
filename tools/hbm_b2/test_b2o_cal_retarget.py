#!/usr/bin/env python3
"""Tests for b2o_cal_retarget.py: identity on SW, owner renumbering on SE/NW/NE, unmapped owners refused,
other fields bit-exact, and the static checker's verdict on a retargeted SW image."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_cal_retarget as R  # noqa: E402
import b2o_cal_static_check as K  # noqa: E402

F = K.field_layout()


def word(pc, **v):
    w = (0xc7a1 << 240) | (pc << 224)
    for n, val in v.items():
        lo, bits = F[n]
        w |= val << lo
    return dict(addr=pc, data=f'{w:064x}')


def slots(d):
    v = o = 0
    for b, own in d.items():
        v |= 1 << b
        o |= own << (3 * b)
    return v, o


def prog(words):
    return dict(configuration_writes=words, start=dict(base=0, limit=len(words), loops=1))


def dec(p, i, name):
    return K.get(int(p['configuration_writes'][i]['data'], 16), F, name)


rv, rs = slots({0: 4, 1: 3, 2: 5})
wv, ws = slots({0: 1, 3: 6})
src = prog([word(0, rslot_v=rv, rslot=rs, wslot_v=wv, wslot=ws, client_seq=0x2a5, response_seq=0x155)])

# SW identity, target NW_hub q0 S
o = R.retarget('SW', src)
assert o['configuration_writes'] == src['configuration_writes'] and o['b2o_target']['tgt'] == 0x60
assert o['b2o_target']['role'] == 'S' and not o['b2o_retarget_errors']

# SE packet 4 -> 5
rv2, rs2 = slots({1: 4})
o = R.retarget('SE', prog([word(0, rslot_v=rv2, rslot=rs2)]))
assert dec(o, 0, 'rslot') >> 3 & 7 == 5 and o['b2o_target']['instance'] == 'NE_hub'

# NW: COLL read 4 -> 3, write 3..7 -> 2..6, other fields bit-exact
rv3, rs3 = slots({5: 4})
wv3, ws3 = slots({6: 7, 2: 3})
o = R.retarget('NW', prog([word(0, rslot_v=rv3, rslot=rs3, wslot_v=wv3, wslot=ws3, client_seq=0x3ff)]))
assert dec(o, 0, 'rslot') >> 15 & 7 == 3 and dec(o, 0, 'wslot') >> 18 & 7 == 6 and dec(o, 0, 'wslot') >> 6 & 7 == 2
assert dec(o, 0, 'client_seq') == 0x3ff and o['b2o_target']['role'] == 'N'

# NE: HC engine read 3 and write 2 have no B2o owner -> refused
rv4, rs4 = slots({0: 3})
wv4, ws4 = slots({1: 2})
o = R.retarget('NE', prog([word(0, rslot_v=rv4, rslot=rs4, wslot_v=wv4, wslot=ws4)]))
assert sorted(e['kind'] for e in o['b2o_retarget_errors']) == ['UNMAPPED_READ', 'UNMAPPED_WRITE'], o['b2o_retarget_errors']

# retargeted SW image with a group-0 read: the checker flags it unless allowed as FUSED
rv5, rs5 = slots({3: 0})
o = R.retarget('SW', prog([word(0, rslot_v=rv5, rslot=rs5)]))
m = dict(calendars=[dict(name='NW.u_calendar_Q_q0', role='S', programme=o)])
assert K.run(m)['findings'][0]['kind'] == 'S_GROUP0_READ'
m['calendars'][0]['allow_group0'] = dict(read=[0])
assert K.run(m)['verdict'] == 'PASS'
print('PASS 5 checks')
