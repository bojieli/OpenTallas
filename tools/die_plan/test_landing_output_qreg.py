"""CLAND-QREG-1: landing_output_qreg is explicit hardware (QREG=1 on the ring) and exactly one extra data cycle."""
import copy
import re
import pytest
import clock_landings as CL
from test_clock_landings import ca_vehicle, vehicle, B_BODY
from test_count_straps import strap_vehicle
from test_legacy_input_freg import body as legacy_body


def test_legacy_ring_qreg_emits_stage_and_prices_once():
    p, t = vehicle()
    p['partition_types']['B']['clock'] = {'landing_output_qreg': ['y']}
    t['ports'][0]['added_cycles'] = 4
    c = CL.Landings(p, t)
    text = c.type_rtl('B', legacy_body())
    assert 'ot_dp_clk_landing #(.W(5), .QREG(1)) u_cland_y' in text
    assert c.manifest()['lane_added_cycles'] == {'L': 4}
    assert c.manifest()['ports'][0]['output_qreg_cycles'] == 1
    req = CL.requirements(p, t)
    assert req['lane_added_cycles'] == {'L': 4}
    assert req['added_live_data_storage_flops'] == 25 + p['ports'][0]['width']   # W stage flops


def test_legacy_qreg_and_freg_stack():
    p, t = vehicle()
    p['partition_types']['B']['clock'] = {'landing_output_qreg': ['y'], 'landing_input_freg': ['y']}
    t['ports'][0]['added_cycles'] = 5
    c = CL.Landings(p, t)
    assert 'ot_dp_clk_landing #(.W(5), .FREG(1), .QREG(1)) u_cland_y' in c.type_rtl('B', legacy_body())
    assert c.manifest()['lane_added_cycles'] == {'L': 5}


def test_legacy_unpriced_or_stale_fails():
    p, t = vehicle()
    p['partition_types']['B']['clock'] = {'landing_output_qreg': ['y']}
    t['ports'][0]['added_cycles'] = 3
    with pytest.raises(CL.LandingError, match='must be 4'):
        CL.Landings(p, t)
    p, t = vehicle(); t['ports'][0]['ring_params'] = {'QREG': 1}
    with pytest.raises(CL.LandingError, match='explicit plan selection'):
        CL.Landings(p, t)


@pytest.mark.parametrize('form', ['ca', 'strap'])
def test_count_aligned_qreg_cycle_in_sched_lat_ring_k_unchanged(form):
    p, t = {'ca': ca_vehicle, 'strap': strap_vehicle}[form]()
    base = CL.Landings(copy.deepcopy(p), copy.deepcopy(t)); baseline = base.type_rtl('B', B_BODY)
    bus = next(iter(base.ins['b'])); row = base.ins['b'][bus]; pid = row['port']
    p['partition_types']['B'].setdefault('clock', {})['landing_output_qreg'] = [bus]
    with pytest.raises(CL.LandingError, match='output_qreg disagree'):      # stale sidecar: cycle not declared
        CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    pids = {x['port'] for x in base.rows if base.parts[x['dst']]['type'] == 'B' and x['dst_bus'] == bus}
    for q in pids:
        c = t['count_aligned']['ports'][q]
        c.update(sched_lat=int(c['sched_lat']) + 1, K=int(c['K']) + 1, output_qreg=1)
    on = CL.Landings(p, t); text = on.type_rtl('B', B_BODY)
    assert '.QREG(1)' in text
    assert re.sub(r",\s*\.QREG\(1\)", "", text) == baseline              # ring (incl. strap K tie) unchanged
    r = on.ins['b'][bus]
    assert r['ring_k'] == row['ring_k'] and r['added_cycles'] == row['added_cycles'] + 1
    assert r['output_qreg_cycles'] == 1
    lb, lo = base.manifest()['lane_added_cycles'], on.manifest()['lane_added_cycles']
    assert sum(lo.values()) - sum(lb.values()) == len(pids)
    assert on.manifest()['reset_placements']['B'][bus]['output_qreg_added_data_cycles'] == 1


@pytest.mark.parametrize('form', ['ca', 'strap'])
def test_count_aligned_qreg_priced_by_sched_lat_not_legacy_ring(form):
    # QC N46R: a re-planned count-aligned QREG port at sched_lat != 3 + QREG carries that sched_lat on its row
    p, t = {'ca': ca_vehicle, 'strap': strap_vehicle}[form]()
    base = CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    bus = next(iter(base.ins['b']))
    p['partition_types']['B'].setdefault('clock', {})['landing_output_qreg'] = [bus]
    pids = {x['port'] for x in base.rows if base.parts[x['dst']]['type'] == 'B' and x['dst_bus'] == bus}
    for lat in (2, 3, 5):
        p2, t2 = copy.deepcopy(p), copy.deepcopy(t)
        for q in pids:
            t2['count_aligned']['ports'][q].update(sched_lat=lat, output_qreg=1)
        for r in t2['ports']:
            if r['port'] in pids:
                r['added_cycles'] = lat
        on = CL.Landings(copy.deepcopy(p2), copy.deepcopy(t2))
        assert on.ins['b'][bus]['added_cycles'] == lat
        for r in t2['ports']:
            if r['port'] in pids:
                r['added_cycles'] = lat + 1
        with pytest.raises(CL.LandingError, match='!= bind sidecar sched_lat'):
            CL.Landings(copy.deepcopy(p2), copy.deepcopy(t2))


@pytest.mark.parametrize('form', ['ca', 'strap'])
def test_count_aligned_plain_row_stale_added_cycles_priced_by_sched_lat(form):
    # HEAD-CROSSING-1119: a count-aligned row WITHOUT QREG keeps the sidecar sched_lat price and ignores a stale
    # ports[].added_cycles (s81_head NF15 chE0_o0__0: row 3 vs sched_lat 2 failed every HEAD kit bootstrap GEN)
    p, t = {'ca': ca_vehicle, 'strap': strap_vehicle}[form]()
    base = CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    bus = next(iter(base.ins['b']))
    pids = {x['port'] for x in base.rows if base.parts[x['dst']]['type'] == 'B' and x['dst_bus'] == bus}
    lat = {q: int(t['count_aligned']['ports'][q]['sched_lat']) for q in pids}
    for r in t['ports']:
        if r['port'] in pids:
            r['added_cycles'] = lat[r['port']] + 1
    on = CL.Landings(copy.deepcopy(p), copy.deepcopy(t))
    priced = {x['port']: x['added_cycles'] for x in on.rows if x['port'] in pids}
    assert priced == lat
    assert on.manifest()['lane_added_cycles'] == base.manifest()['lane_added_cycles']


@pytest.mark.parametrize('bad', [True, ['y', 'y'], [1], ['y[0]']])
def test_bad_selection_rejected(bad):
    p, t = vehicle(); p['partition_types']['B']['clock'] = {'landing_output_qreg': bad}
    with pytest.raises(CL.LandingError):
        CL.Landings(p, t)


def test_schema():
    import schema as S
    cs = S.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['clock']
    e = []; S._check({'landing_output_qreg': ['y']}, cs, '$.clock', e); assert not e
    S._check({'landing_output_qreg': ['bad bus']}, cs, '$.clock', e); assert any('landing_output_qreg' in x for x in e)
