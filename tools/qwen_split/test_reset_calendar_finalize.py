#!/usr/bin/env python3
"""Exercise the actual GEN post-tree strap transform, including refusal atomicity."""
import copy
from types import SimpleNamespace
from reset_calendar_audit import finalize_model


def model():
    return dict(insts=[SimpleNamespace(name='s',master='qfd_rst_rep'),
                       SimpleNamespace(name='r',master='qfd_rst_rep_p8')],
                buses=[('root_s','reset',1,[('external','s'),('s','d')]),
                       ('root_r','reset',1,[('external','r'),('r','d')]),
                       ('source','reset',1,[('s','q0'),('first','en')]),
                       ('dest','reset',1,[('r','q0'),('last','rs')]),
                       ('ftk_x_hi','constant',1,[('last','tie_hi'),('last','k1')]),
                       ('ftk_x_lo','constant',1,[('last','tie_lo'),('last','k0'),('last','k2')])],
                fwd_lanes=dict(lanes=[dict(bid='x',lane='data',E=2,E_sta=2,K=2,
                                          stations=['first'],landing='last')]))

m=model(); before=copy.deepcopy(m['buses'])
try:
    finalize_model(m)
except ValueError as e:
    assert 'undeclared reset-root relationship' in str(e)
else:
    raise AssertionError('missing root calendar was accepted')
assert m['buses']==before
finalize_model(m,{'external.s':16,'external.r':20})
r=m['fwd_lanes']['lanes'][0]
assert (r['G_reset_tree'],r['R0_reset_tree'],r['K'],r['cal'])==(18,30,6,-12)
straps={pol:[p for _,_,_,eps in m['buses'] if eps[0]==('last','tie_'+pol) for p in eps[1:]] for pol in ('hi','lo')}
assert straps=={'hi':[('last','k1'),('last','k2')],'lo':[('last','k0')]}
finalize_model(m,{'external.s':16,'external.r':20})
assert len(m['buses'])==6
print('RESET_FINALIZE PASS: exact taps/straps, unknown-root refusal, idempotence')
