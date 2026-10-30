"""Uniform reader START transport preserves count indices through K-R ties."""
import copy
import pytest
import count_align_bind as CAB
import landing_place as LP
from clock_landings import Landings, LandingError
from test_clock_landings import ca_vehicle, A_BODY, B_BODY
from test_count_straps import strap_vehicle, TOP


def enable(p):
    p['partition_types']['B'].setdefault('clock', {})['landing_reader_start'] = dict(
        depth=2, branches={'y': {'stages': [
            dict(xy_um=[3., 3.], raw_reset='cland_reset_y'),
            dict(xy_um=[6., 3.], raw_reset='cland_reset_y')]}})


def test_reader_only_reset_and_parameter_K_are_compensated():
    p, t = ca_vehicle(k=-2)
    enable(p)
    c = Landings(p, t)
    out = c.type_rtl('B', B_BODY)
    assert '.K(-4)' in out
    assert '.t_rst_n(cland_fstart_in_y), .clk(clk), .rst_n(cland_reader_start_y_1)' in out
    assert 'u_cland_reader_start_y_0 (.clk(clk), .rst_raw_n(cland_reset_y), .d(cland_start)' in out
    assert 'u_cland_reader_start_y_1 (.clk(clk), .rst_raw_n(cland_reset_y), .d(cland_reader_start_y_0)' in out
    assert '.start(cland_start)' in out  # original mission/source origin unchanged
    r = c.manifest()['reset_placements']['B']['y']['reader_start']
    assert r['K_adjustment'] == -2 and r['boot_extra_cycles'] == 2 and r['steady_data_cycles_added'] == 0
    assert c.rows[0]['added_cycles'] == t['count_aligned']['ports']['P']['sched_lat']


def test_parent_ties_audit_and_parameter_reference_share_effective_K():
    p, t = strap_vehicle(k_b=-2, k_c=3)
    enable(p)
    st = CAB.strap_ties(t['count_aligned'], p)
    assert st['instances']['b']['values']['strap_ca_k_y'] == 60  # -4 mod64
    assert st['instances']['c']['values']['strap_ca_k_y'] == 1
    c = Landings(p, t)
    out = c.type_rtl('B', B_BODY)
    assert '.strap_k(strap_ca_k_y)' in out and '.rst_n(cland_reader_start_y_1)' in out
    c.type_rtl('A', A_BODY)
    top = c.top_rtl(TOP)
    assert '.strap_ca_k_y(6\'b111100)' in top and '.strap_ca_k_y(6\'b000001)' in top
    pp, tt = copy.deepcopy(p), copy.deepcopy(t)
    tt['count_aligned'].pop('strap_form')
    ref = Landings(pp, tt, ca_variants=True).type_rtl('B', B_BODY, inst='b', depth={'y': 4})
    assert '.K(-4)' in ref


def test_declared_relay_stages_enter_existing_firm_placement():
    p, _ = ca_vehicle();enable(p)
    groups = LP._reader_start_groups(p['partition_types']['B'])
    assert [r[0] for r in groups] == ['u_cland_reader_start_y_0', 'u_cland_reader_start_y_1']
    assert groups[0][1] == pytest.approx([.84,.84,5.16,5.16])
    assert LP._reader_start_groups({}) == []
    p['partition_types']['B']['clock']['landing_reader_start']['origin_rect_um'] = [1,2,5,6]
    assert LP._reader_start_groups(p['partition_types']['B'])[0] == ('u_cland_origin',[1,2,5,6],'reader-start-origin')


@pytest.mark.parametrize('edit,reason', [
    (lambda c: c.update(depth=True), 'integer'),
    (lambda c: c['branches'].clear(), 'exactly every input ring'),
    (lambda c: c['branches']['y']['stages'].pop(), 'exactly 2 physical stages'),
    (lambda c: c['branches']['y']['stages'][0].update(raw_reset='invented'), 'registered wavefront driver'),
    (lambda c: c['branches']['y']['stages'][0].update(xy_um=[float('nan'),3]), 'finite xy_um'),
])
def test_incomplete_or_unsafe_contract_fails_closed(edit, reason):
    p, t = ca_vehicle();enable(p)
    edit(p['partition_types']['B']['clock']['landing_reader_start'])
    with pytest.raises((LandingError, CAB.BindError), match=reason):
        Landings(p, t).type_rtl('B', B_BODY)
