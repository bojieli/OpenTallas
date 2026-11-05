#!/usr/bin/env python3
"""Tests for b2o_fused_fragment.py: FUSED-only and mixed frames PASS the static checker with the candidate allow-list;
double booking, a non-FUSED group-0 client and a dq owner are refused; without the allow-list the checker FAILS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_fused_fragment as G  # noqa: E402
import b2o_cal_static_check as K  # noqa: E402

OTHER = [dict(edge=2, dir='r', owner=4, banks=list(range(8)), client='IDX'),
         dict(edge=3, dir='r', owner=3, banks=list(range(8)), client='COLL'),
         dict(edge=3, dir='w', owner=2, banks=list(range(8)), client='COLL kq'),
         dict(edge=2, dir='w', owner=1, banks=[0, 1], client='SM writer'),
         dict(edge=2, dir='r', owner=1, banks=[], client='none')]


def refused(**kw):
    try:
        G.build(4, [dict(edge=2, dir='r', owner=1, banks=[0], client='x', **kw)] if kw else [])
    except ValueError:
        return True
    return False


p = G.build(4)
assert K.run(G.manifest(p, 'NW.u_calendar_Q_q0'))['verdict'] == 'PASS'
r = K.run(G.manifest(G.build(4, OTHER), 'NE.u_calendar_Q_q0'))
assert r['verdict'] == 'PASS' and r['counts']['s_group0_read'] == 16 and r['counts']['s_group0_write'] == 16, r
assert K.run(dict(calendars=[dict(name='c', role='S', programme=p)]))['verdict'] == 'FAIL'
for bad in ([dict(edge=0, dir='r', owner=4, banks=[3], client='on FUSED edge')],
            [dict(edge=2, dir='r', owner=0, banks=[3], client='group0 not FUSED')],
            [dict(edge=2, dir='w', owner=6, banks=[3], client='dq')],
            [dict(edge=2, dir='r', owner=4, banks=[5], client='a'), dict(edge=2, dir='r', owner=3, banks=[5], client='b')],
            [dict(edge=7, dir='r', owner=4, banks=[0], client='edge out of frame')]):
    try:
        G.build(4, bad)
        raise SystemExit(f'accepted {bad}')
    except ValueError:
        pass
try:
    G.build(1)
    raise SystemExit('period 1 accepted')
except ValueError:
    pass
print('PASS 8 checks')
