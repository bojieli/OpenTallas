import copy

import pytest

from head_static_programme import compile_programme
from test_head_boot_recipe import PARAMS, fixture as boot_fixture
from test_head_entry_schedule import fixture as entry_fixture


def fixture():
    plan, offsets, _ = boot_fixture()
    inventory, job, timing = entry_fixture()
    # The current transport families retain mission operators while their
    # HOST bootstrap buses run on raw reset.
    for old, new in (('l', 'hd_serdes'), ('s', 'hd_spn')):
        plan['partition_types'][new] = plan['partition_types'].pop(old)
        plan['partition_types'][new]['reset']['start_role'] = 'mission'
        for part in plan['partitions']:
            if part['type'] == old:
                part['type'] = new
                offsets['parts'][part['name']]['type'] = new
    plan['partition_types']['hd_serdes']['contents'] = [dict(inst='u_phy', module='ot_s81hd_serdes_link')]
    for bus in plan['ports'][:2]:
        bus['src']['bus'] = 'coll_o0'
    for bus in plan['ports'][2:]:
        for side in ('src', 'dst'):
            if bus[side]['part'] == 'sp':
                bus[side]['bus'] = 'hu_i' if side == 'dst' else 'hu_o'
    plan['partition_types']['hd_spn']['contents'] = [dict(inst='u_spo', module='ot_s81hd_spo'),
                                                    dict(inst='u_spr', module='ot_s81hd_spr')]
    for name in ('hd_st_k5', 'hd_spn_end'):
        plan['partition_types'][name] = copy.deepcopy(plan['partition_types']['hd_spn'])
        if name == 'hd_st_k5':
            plan['partition_types'][name]['contents'] = []
    offsets['start']['bootstrap_types'] = ['c', 'h']
    job['activation_records'] = [dict(index=n, edge=400+n, payload=n) for n in range(80)]
    timing.update(clock_reset_id=0x123456789, phase_bound=7,
                  start_producer='package_boot_controller.start_o',
                  activation_source='s81_final_norm/K_XB',
                  ctl_start_offset=12, peer_to_host_frame=3,
                  xb_pin_to_resident_edges=3)
    return plan, offsets, inventory, job, timing


def test_native_calendar_roundtrips_into_plan_recipe():
    p, o, i, j, t = fixture()
    original = copy.deepcopy(p)
    candidate, programme, recipe = compile_programme(p, o, i, j, t, PARAMS)
    assert p == original
    assert recipe['status'] == 'SOURCE_RECIPE_READY'
    assert recipe['host_params']['LOCAL_STAGE'] == 81
    assert recipe['host_params']['LOCAL_RANK'] == 3
    assert recipe['host_params']['CLOCK_RESET_ID'] == t['clock_reset_id']
    assert recipe['host_params']['PHASE_BOUND'] == 7
    assert len(recipe['frames']) == 11 and len(recipe['activation_records']) == 80
    assert recipe['activation_resident_global_edge'] == 482
    assert recipe['start']['producer'] == t['start_producer']
    assert not recipe['production_transport_qualified']
    assert not recipe['blockers']
    assert candidate['partition_types']['hd_spn']['reset']['start_role'] == 'mission'


@pytest.mark.parametrize('fault', ('identity', 'phase', 'source', 'start', 'offset', 'age', 'activation'))
def test_missing_or_incompatible_actual_authorities_are_refused(fault):
    p, o, i, j, t = fixture()
    if fault == 'identity': t['clock_reset_id'] = 0
    if fault == 'phase': t['phase_bound'] = 0
    if fault == 'source': del t['activation_source']
    if fault == 'start': t['start_producer'] = 'ctl.job_active'
    if fault == 'offset': t['ctl_start_offset'] = 11
    if fault == 'age': t['peer_to_ctl_settled'] = 4
    if fault == 'activation': del j['activation_records']
    with pytest.raises(ValueError):
        compile_programme(p, o, i, j, t, PARAMS)


def test_l48x_host_strip_transport_scope_is_narrow_and_preserves_prior_scope():
    from head_bootstrap_delta import apply
    p, _, _, _, _ = fixture()
    p['partition_types']['hd_host_n'] = dict(contents=[], reset=dict(bootstrap_buses=['existing']))
    candidate = apply(p)
    reset = candidate['partition_types']['hd_host_n']['reset']
    assert reset['bootstrap_buses'] == ['existing', 'h_rx_ft_i', 'h_rx_ft_o']
    assert reset.get('start_role', 'mission') == 'mission'
    p['partition_types']['hd_host_n']['contents'] = [dict(inst='operator', module='new_operator')]
    with pytest.raises(ValueError, match='operators'):
        apply(p)


def test_mtp_programme_writes_actual_result_tag_before_run():
    p, o, i, j, t = fixture()
    j.update(mode='mtp', glen=6, mtp_result_mtag=0x4321)
    _, programme, recipe = compile_programme(p, o, i, j, t, PARAMS)
    assert programme['config']['mtp_result_mtag'] == 0x4321
    frames = [r for r in recipe['frames'] if 'csr_address' in r]
    assert len(frames) == 9
    assert frames[-1]['csr_address'] == 8
    assert next(r['csr_value'] for r in frames if r['csr_address'] == 5) == 0x4321
