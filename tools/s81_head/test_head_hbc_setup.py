import copy
import hashlib
import json

import pytest

from head_entry_schedule import compile_entry, compile_hbc_setup, CODEC
from head_hbc_setup import compile_candidate
from test_head_entry_schedule import fixture as full_fixture

CID = 0x5ea21d11d55d4760


def fixture():
    inventory = dict(stages=81, TP=4, head_dies=4)
    job = dict(rank=0, tid=0, user=0, position=1048575, token=0, epoch=0, programme=0x12345678)
    timing = dict(reset_deassert_edge=8, host_counter_zero_edge=27, link_ready_edge=600,
                  peer_to_hbc_input=120, peer_frame_period=4, peer_launch_modulus=4,
                  peer_launch_residue=0)
    return inventory, job, timing


def test_measured_hbc_chain_does_not_require_csr_or_activation_timing():
    i, j, t = fixture()
    r = compile_hbc_setup(i, j, t, clock_reset_id=CID)
    assert r['host_params'] == dict(LOCAL_STAGE=81, LOCAL_RANK=0, PHASE_BOUND=1,
                                  CLOCK_RESET_ID=CID, BOOT_HEADER_EDGE=693, BOOT_COMMIT_EDGE=701)
    assert [(f['kind'], f['edge']) for f in r['frames']] == [
        ('HBC_LOAD', 600), ('HBC_BODY', 604), ('HBC_COMMIT', 608)]
    assert r['authority'] == dict(CSR=False, GO=False, START=False)
    assert not r['full_head_token'] and not r['production_transport_qualified']
    body = (r['frames'][1]['frame'] >> 16) & ((1 << 512) - 1)
    assert body >> 272 & 1023 == 417
    assert body >> 26 & ((1 << 21) - 1) == 1048575
    for f in (r['frames'][0], r['frames'][2]):
        payload = f['frame'] >> 16 & ((1 << 512) - 1)
        assert payload >> 114 & ((1 << 64) - 1) == CID
        assert payload >> 82 & ((1 << 32) - 1) == CODEC.crc(body)


def test_setup_records_match_full_compiler_with_the_same_explicit_identity():
    i, j, t = full_fixture()
    full = compile_entry(i, j, t)
    narrow = {k: v for k, v in t.items() if k not in
              ('peer_to_ctl_settled', 'commit_to_context_valid', 'ctl_start_offset')}
    setup = compile_hbc_setup(i, j, narrow, clock_reset_id=full['host_params']['CLOCK_RESET_ID'])
    assert setup['host_params'] == full['host_params']
    assert setup['frames'] == [f for f in full['frames'] if f['kind'].startswith('HBC_')]


@pytest.mark.parametrize('case,expected', [
    ('ar', '4e1600338384c007299dd1f17bb7375d2c2822f24ec91d540ec875f1b545ccb9'),
    ('activation', '1db046bdfe293682692ba85e567429eebf480eb71b8752fc94a26a2c67deaa51'),
    ('mtp', 'ac0e6d93ff873ab4e48a35820b164adb97f9d7f17008b6b706a85df112acb80a')])
def test_existing_full_compiler_output_is_byte_exact(case, expected):
    # Captured from unmodified 489bcf2396 full compiler, including its identity hash.
    i, j, t = full_fixture()
    if case == 'activation':
        j['activation_beats'] = list(range(80))
        t.update(xb_first_edge=400, xb_period=1, xb_pin_to_resident_edges=3)
    if case == 'mtp':
        j.update(mode='mtp', glen=6, mtp_result_mtag=0x4321)
    payload = json.dumps(compile_entry(i, j, t), sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(payload).hexdigest() == expected


@pytest.mark.parametrize('fault', ('zero_id', 'date', 'phase', 'words', 'rank', 'stage'))
def test_setup_refuses_invalid_protocol_bindings(fault):
    i, j, t = fixture(); identity = CID
    if fault == 'zero_id': identity = 0
    if fault == 'date': t['host_counter_zero_edge'] = 800
    if fault == 'phase': t['peer_launch_modulus'] = 3
    if fault == 'words': j['host_word_count'] = 80
    if fault == 'rank': j['rank'] = 4
    if fault == 'stage': i['stages'] = 241
    with pytest.raises(ValueError): compile_hbc_setup(i, j, t, clock_reset_id=identity)


def candidate_fixture():
    i, j, t = fixture()
    plan = dict(partition_types={'host': dict(module='actual_host_wrapper', contents=[
        dict(inst='u_core', module='ot_s81hd_host_ep_core', params={'EXISTING': 9})])},
        partitions=[dict(name='host', type='host')])
    profile = dict(source_event='actual_cohort', clock_profile='measured same-root peers',
                   scope='component candidate', source_plan_sha256='plan', source_sidecar_sha256='side',
                   root_reset_deassert_global_edge=8, host_boot_counter_zero_global_edge=27,
                   qualified_host0_launch_edges=[600,604,608], qualified_host0_input_edges=[720,724,728])
    digest = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).digest()
    identity = int.from_bytes(digest[:8], 'little') or 1
    record = dict(profile=profile, profile_sha256=digest.hex(), clock_reset_id=identity, phase_bound=1,
                  host_params_candidate=dict(LOCAL_STAGE=81, LOCAL_RANK=0, PHASE_BOUND=1, CLOCK_RESET_ID=identity))
    return plan, i, j, t, record


def test_candidate_binds_only_actual_host_and_preserves_inputs():
    p, i, j, t, profile = candidate_fixture(); old = copy.deepcopy(p)
    candidate, setup = compile_candidate(p, i, j, t, profile, plan_sha256='plan', sidecar_sha256='side')
    assert p == old
    params = candidate['partition_types']['host']['contents'][0]['params']
    assert params == dict(EXISTING=9, **setup['host_params'])
    assert len(setup['frames']) == 3 and setup['scope'] == 'HBC_SETUP_ONLY'
    assert setup['binding']['part'] == 'host'


@pytest.mark.parametrize('fault', ('digest', 'identity', 'phase', 'plan', 'sidecar', 'origin', 'chain', 'binding'))
def test_candidate_refuses_unmeasured_or_mismatched_authority(fault):
    p, i, j, t, profile = candidate_fixture(); plan_sha, side_sha = 'plan', 'side'
    if fault == 'digest': profile['profile_sha256'] = 'wrong'
    if fault == 'identity': profile['clock_reset_id'] = 0
    if fault == 'phase': profile['phase_bound'] = 0
    if fault == 'plan': plan_sha = 'other'
    if fault == 'sidecar': side_sha = 'other'
    if fault == 'origin': t['host_counter_zero_edge'] += 1
    if fault == 'chain': t['peer_to_hbc_input'] += 1
    if fault == 'binding': profile['host_params_candidate']['LOCAL_RANK'] = 1
    with pytest.raises(ValueError):
        compile_candidate(p, i, j, t, profile, plan_sha256=plan_sha, sidecar_sha256=side_sha)


def native_fixture():
    p, i, j, t, record = candidate_fixture()
    t.pop('host_counter_zero_edge'); t.pop('peer_to_hbc_input')
    t.update(reset_deassert_edge=64, hbc_arrival_boot_edges=[635,639,643])
    profile=record['profile']
    profile.pop('host_boot_counter_zero_global_edge'); profile.pop('qualified_host0_input_edges')
    profile.update(root_reset_deassert_global_edge=64,period_ps=833,
        host_boot_counter_zero_time_ps='69421.624',
        qualified_host0_input_time_ps=['598376.624','601708.624','605040.624'],
        qualified_host0_input_boot_edges=[635,639,643])
    digest=hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':')).encode()).digest()
    identity=int.from_bytes(digest[:8],'little') or 1
    record.update(profile_sha256=digest.hex(),clock_reset_id=identity)
    record['host_params_candidate']['CLOCK_RESET_ID']=identity
    return p,i,j,t,record


def test_native_counter_ages_do_not_invent_integer_global_counter_origin():
    p,i,j,t,profile=native_fixture()
    candidate,r=compile_candidate(p,i,j,t,profile,plan_sha256='plan',sidecar_sha256='side')
    assert r['host_params']['BOOT_HEADER_EDGE']==635
    assert r['host_params']['BOOT_COMMIT_EDGE']==643
    assert [f['edge'] for f in r['frames']]==[600,604,608]
    assert 'host_counter_zero_edge' not in r['timing']
    assert 'peer_to_hbc_input' not in r['timing']
    assert r['authority']==dict(CSR=False,GO=False,START=False)


@pytest.mark.parametrize('fault',('nonaffine','mixed','missing_timestamp','timestamp_age','profile_age','full_entry'))
def test_native_boot_age_refusals(fault):
    p,i,j,t,profile=native_fixture()
    if fault=='nonaffine':t['hbc_arrival_boot_edges'][1]+=1
    if fault=='mixed':t['host_counter_zero_edge']=83
    if fault=='missing_timestamp':profile['profile'].pop('host_boot_counter_zero_time_ps')
    if fault=='timestamp_age':
        profile['profile']['qualified_host0_input_time_ps'][0]='598377.624'
        digest=hashlib.sha256(json.dumps(profile['profile'],sort_keys=True,separators=(',',':')).encode()).digest()
        profile.update(profile_sha256=digest.hex(),clock_reset_id=int.from_bytes(digest[:8],'little') or 1)
        profile['host_params_candidate']['CLOCK_RESET_ID']=profile['clock_reset_id']
    if fault=='profile_age':t['hbc_arrival_boot_edges']=[636,640,644]
    with pytest.raises(ValueError):
        if fault=='full_entry':compile_entry(i,j,t)
        else:compile_candidate(p,i,j,t,profile,plan_sha256='plan',sidecar_sha256='side')
