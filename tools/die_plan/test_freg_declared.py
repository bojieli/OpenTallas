"""FREG-DECL-1 (COORD 11-11): a FREG crossing whose +1 data cycle is not counted is an ERROR (fail closed).
count-aligned (landing_ring_wreg.freg): the bind sidecar port must declare "freg": 1 (its sched_lat includes the cycle),
checked by clock_landings (generation) AND count_align_bind.strap_ties (bind).  legacy (landing_input_freg): the +1 is
added by clock_landings itself; a sidecar added_cycles without it fails."""
import copy
import pytest
import clock_landings as CL
import count_align_bind as CAB
from test_count_straps import strap_vehicle
from test_legacy_input_freg import configured as legacy_configured


def freg_vehicle():
    p, t = strap_vehicle()
    base = CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    bus = next(iter(base.ins['b']))
    p['partition_types']['B'].setdefault('clock', {})['landing_ring_wreg'] = {'buses': [bus], 'dsrep': 1, 'freg': True}
    pids = sorted({x['port'] for x in base.rows if base.parts[x['dst']]['type'] == 'B' and x['dst_bus'] == bus})
    return p, t, pids


def declare(t, pids):
    for q in pids:
        c = t['count_aligned']['ports'][q]
        c.update(sched_lat=int(c['sched_lat']) + 1, freg=1)   # logical K unchanged: strap_ties applies K + 2


def test_undeclared_freg_cycle_fails_in_generator_and_binder():
    p, t, pids = freg_vehicle()
    with pytest.raises((CL.LandingError, CAB.BindError), match='does not declare'):
        CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    with pytest.raises(CAB.BindError, match='does not declare'):
        CAB.strap_ties(t['count_aligned'], p)


def test_declared_freg_cycle_passes_and_counts_once():
    p0, t0 = strap_vehicle(); base = CL.Landings(copy.deepcopy(p0), copy.deepcopy(t0))
    p, t, pids = freg_vehicle(); declare(t, pids)
    on = CL.Landings(p, t)
    lb, lo = base.manifest()['lane_added_cycles'], on.manifest()['lane_added_cycles']
    assert sum(lo.values()) - sum(lb.values()) == len(pids)          # the FREG cycle, exactly once per crossing
    assert '.FREG(1)' in on.type_rtl('B', __import__('test_clock_landings').B_BODY)
    p1, t1 = strap_vehicle()
    k0 = CAB.strap_ties(t1['count_aligned'], p1)['instances']
    k1 = CAB.strap_ties(t['count_aligned'], p)['instances']
    for inst, v in k1.items():                                         # WREG + FREG: physical K + 2, not + 3
        for port, val in v['values'].items():
            if port.startswith('strap_ca_k_') and val != k0[inst]['values'][port]:
                assert (val - k0[inst]['values'][port]) % 64 == 2


def test_stale_mark_without_freg_fails():
    p, t = strap_vehicle(); base = CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    pid = base.rows[0]['port']; t['count_aligned']['ports'][pid]['freg'] = 1
    with pytest.raises((CL.LandingError, CAB.BindError), match='stale sidecar'):
        CL.Landings(p, t)
    with pytest.raises(CAB.BindError, match='stale sidecar'):
        CAB.strap_ties(t['count_aligned'], p)


def test_legacy_input_freg_undercounted_sidecar_fails_and_absent_is_counted():
    p, t = legacy_configured(); t['ports'][0]['added_cycles'] = 3
    with pytest.raises(CL.LandingError, match='must be 4'):
        CL.Landings(p, t)
    p, t = legacy_configured(); t['ports'][0].pop('added_cycles', None)
    assert CL.Landings(p, t).manifest()['lane_added_cycles'] == {'L': 4}
