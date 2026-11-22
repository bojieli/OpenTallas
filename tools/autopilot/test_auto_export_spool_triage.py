"""FLOW-FLEET-R1 11-22 (FABLE-FLOW-0000 F9): the hub's own spool is read; a spool item over 2 h old is retried once, then set aside with
its reason; canary / test runs are set aside at once; already-exported items are dropped."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auto_export as AE  # noqa: E402

H2 = 3 * 3600


def u(name, age, **kw):
    d = dict(host='h1', via='spool', spool='%016x.json' % abs(hash(name)), signoff='/k/%s/signoff.json' % name,
             odb='/k/%s/6_final.odb' % name, spool_age_s=age)
    d.update(kw)
    return d


def test_intel2_is_a_spool_host():
    assert 'intel2' in AE.HOSTS


def test_retry_once_then_aside_with_reason():
    L = dict(units={'h1:/k/old/6_final.odb': dict(state='err', tries=3, err='agi push refused')})
    old, fresh = u('old', H2), u('fresh', 60)
    keep, aside, drop = AE.spool_triage(L, [old, fresh], now=1000.0)
    assert {x['signoff'] for x in keep} == {old['signoff'], fresh['signoff']} and not aside and not drop
    assert L['units']['h1:/k/old/6_final.odb']['tries'] == 2                  # one more export try
    keep, aside, drop = AE.spool_triage(L, [old], now=1000.0 + 60)
    assert keep == [old] and not aside                                       # the retry gets a drain first
    keep, aside, drop = AE.spool_triage(L, [old], now=1000.0 + AE.SPOOL_ASIDE_AFTER_S + 1)
    assert keep == [] and aside == {'h1': [(old['spool'], aside['h1'][0][1])]} and 'agi push refused' in aside['h1'][0][1]


def test_gone_signoff_reason_and_canary_and_done():
    L = dict(units={'h1:/k/done/6_final.odb': dict(state='skip')})
    gone = dict(u('gone', H2), err='signoff.json gone')
    gone.pop('odb')
    can = u('x', 10, signoff='/srv/opentallas-scratch2/claude/flow-canary/runs/r1/gen/t/signoff/signoff.json')
    done = u('done', 10)
    AE.spool_triage(L, [gone], now=0.0)
    keep, aside, drop = AE.spool_triage(L, [gone, can, done], now=AE.SPOOL_ASIDE_AFTER_S + 1.0)
    reasons = dict(aside['h1'])
    assert 'signoff.json gone' in reasons[gone['spool']] and 'canary' in reasons[can['spool']]
    assert drop == {'h1': [done['spool']]} and keep == []


def test_scan_units_pass_through():
    s = dict(host='h1', via='scan', odb='/k/s/6_final.odb')
    assert AE.spool_triage(dict(units={}), [s])[0] == [s]
