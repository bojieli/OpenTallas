#!/usr/bin/env python3
"""FAM-S81-LEPE-4 XG-1: the compiler, the cut replay and the token composer price the OT_S81SL_RSTOP_XMID1 stop
   edge with one helper (layer_prog/rstop_model.py) and agree (pure python, no die tree).
   python3 tools/s81_dv/test_rstop_xmid.py            (exit 0 = PASS)"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import dv_layer_compile as C  # noqa: E402
import dv_cut_replay as R  # noqa: E402
from layer_prog import rstop_model as RM  # noqa: E402


class FakeDie:
    """a two-tier line: tv<T>_seqhost, column links u_s_c -> u_s_c+-1 with age 4"""
    def __init__(self, xmid=()):
        self.rstop_xmid = frozenset(xmid)
        self.timing_contract = {'v_ctl_inject': 7}
        self.links = {'tvN_seqhost': dict(age_edges=10, stations=0, E=None, src=[], dst=[]),
                      'tvS_seqhost': dict(age_edges=10, stations=0, E=None, src=[], dst=[]),
                      'tvS_bk_sel': dict(age_edges=3, stations=0, E=None, src=[], dst=[])}
        for t in 'NS':
            for c in range(8):
                for n in (c - 1, c + 1):
                    if 0 <= n < 8:
                        self.links[f'xr_{c}{n}{t}'] = dict(age_edges=4, src=[(f'u_s_{c}{t}', 'ro')],
                                                           dst=[(f'u_s_{n}{t}', 'ri')])

    def slices(self):
        return {f'u_s_{c}{t}': dict(sid=c) for c in range(8) for t in 'NS'}


def test_plan_select():
    plan = dict(partition_types={'lepe_C': dict(verilog_defines=['OT_S81SL_RSTOP_XMID1']), 'lepe_LP': {},
                                 'c1x': dict(verilog_defines=['OT_X'])},
                partitions=[dict(name='s_7S_C', type='lepe_C'), dict(name='s_7S_LP', type='lepe_LP'),
                            dict(name='s_1N_C', type='c1x')])
    assert C.rstop_xmid_slices(plan) == {'u_s_7S'}
    bad = dict(plan, partitions=[dict(name='fW0_p1', type='lepe_C')])
    try:
        C.rstop_xmid_slices(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('XMID define on a non-slice partition must fail closed')
    return plan


def test_hop_and_paths():
    base, xm = FakeDie(), FakeDie({'u_s_7N', 'u_s_4S'})
    assert C.rstop_hop(base, 'u_s_7N') == C.RSTOP_HOP == 2 and C.rstop_hop(xm, 'u_s_7N') == 3
    assert C.rstop_hop(xm, 'u_s_6N') == 2
    for sl, d in (('u_s_7N', 1), ('u_s_6N', 0), ('u_s_5N', 0), ('u_s_4S', 1), ('u_s_5S', 0), ('u_s_0N', 0)):
        a, b = C.ctl_path(base, sl)['edges'], C.ctl_path(xm, sl)['edges']
        assert b - a == d, (sl, a, b)
    assert C._line_hop(xm, 'N', 6, 7) - C._line_hop(base, 'N', 6, 7) == 1
    assert C._line_hop(xm, 'N', 7, 6) == C._line_hop(base, 'N', 7, 6)


def test_bound_plan_resolve():
    plan = test_plan_select()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / 'physical/s81').mkdir(parents=True)
        (d / 'physical/s81/plan.json').write_text(json.dumps(plan))
        out = d / 'physical/s81/bind/out'
        out.mkdir(parents=True)
        xm, p = C.bound_rstop_xmid(out, 'physical/s81/plan.json')
        assert xm == {'u_s_7S'} and p == d / 'physical/s81/plan.json'
        try:
            C.bound_rstop_xmid(out, 'physical/s81/missing.json')
        except ValueError:
            pass
        else:
            raise AssertionError('an unresolved bound plan must fail closed')
        os.environ['OT_S81_RSTOP_XMID_PLAN'] = str(d / 'physical/s81/plan.json')
        try:
            assert C.bound_rstop_xmid(out, 'physical/s81/missing.json')[0] == {'u_s_7S'}
        finally:
            del os.environ['OT_S81_RSTOP_XMID_PLAN']


class FakeBuild:
    """dv_cut_replay DieBuild stand-in: line lanes with age 4 between neighbour columns"""
    def __init__(self, xmid=()):
        self.rstop_xmid = frozenset(xmid)
        self.links = {}
        for t in 'NS':
            for c in range(8):
                for n in (c - 1, c + 1):
                    if 0 <= n < 8:
                        self.links[f'xr_{c}{n}{t}'] = dict(age=4, src=[(f'u_s_{c}{t}', 'ro')], dst=[(f'u_s_{n}{t}', 'ri')])


def test_replay_agrees():
    S = dict(events=[dict(kind='CTL', dir='in', inst='u_s_4N', port='vi', cycle=100, payload='1', tag='t0')])
    at = lambda die: {(d['inst'], d['port']): d['cycle'] for d in R.derive_line_events(S, die)}
    a, b = at(FakeBuild()), at(FakeBuild({'u_s_7N'}))
    assert b[('u_s_7N', 'ri_w')] - a[('u_s_7N', 'ri_w')] == 1
    assert all(b[k] == a[k] for k in a if k != ('u_s_7N', 'ri_w'))
    # replay stop count per column == compiler ctl_path stop delta (same helper, same stops)
    for sl in ('u_s_7N', 'u_s_6N'):
        dc = C.ctl_path(FakeDie({'u_s_7N'}), sl)['edges'] - C.ctl_path(FakeDie(), sl)['edges']
        dr = b[(sl, 'ri_w')] - a[(sl, 'ri_w')]
        assert dc == dr, (sl, dc, dr)
    assert R.pin_offset(FakeBuild({'u_s_7N'}), 'CTL', 'u_s_7N') == -3 and R.pin_offset(FakeBuild(), 'CTL', 'u_s_7N') == -2
    assert R.pin_offset(FakeBuild({'u_s_7N'}), 'SVCJ', 'u_s_7N') == 0
    assert RM.programme_rstop_xmid(dict(rstop_xmid=['u_s_7N'])) == {'u_s_7N'}
    assert RM.programme_rstop_xmid({}) == frozenset() and RM.programme_rstop_xmid(dict(bound_data=None)) == frozenset()
    try:
        RM.programme_rstop_xmid(dict(bound_data=dict(verdict='PASS')))
    except ValueError:
        pass
    else:
        raise AssertionError('a bound programme without rstop_xmid must fail closed')


def test_token_leg():
    assert RM.leg_xmid_extra(frozenset()) == 0
    assert RM.leg_xmid_extra({'u_s_7N', 'u_s_7S'}) == 1            # the E-bound leg enters the column-7 stop
    assert RM.leg_xmid_extra({'u_s_7N', 'u_s_1N'}) == 2            # E-bound enters 1..7
    assert RM.leg_xmid_extra({'u_s_0S'}) == 1                      # W-bound enters 6..0
    assert RM.leg_xmid_extra({'u_s_7N', 'u_s_0S'}) == 1            # worst tier / direction, not the sum


if __name__ == '__main__':
    test_plan_select()
    test_hop_and_paths()
    test_bound_plan_resolve()
    test_replay_agrees()
    test_token_leg()
    print('TEST_RSTOP_XMID PASS')
