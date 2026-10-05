import pytest
from tools.w17_D1_descriptor_provenance import validate_descriptor, legacy_descriptor_status


def packets():
    s = dict(time_ps=141500, phase=0, rn=1, life_state=0, last_gen=0,
             desc_v=1, kvd_v=1, retain_l0=1, hbm_attention=1, start_ready=1,
             service_busy=0, service_fault=0, stage_v=0, beat_v=0, beat_ready=0,
             wrap_drained=1, user=0, pos=127, tiles=4, k=512, nout=128,
             wbase=0, ts=512, ks=1, js=0, hg=1, mmode=1, window_region_ok=1)
    e = dict(time_ps=141500, phase=0, generation=1, rows=128, user=0, pos=127)
    return s, e


def test_source_descriptor_control_is_not_core_issue_or_deadline():
    s, e = packets()
    r = validate_descriptor(s, e)
    assert r['core_ME_admission'] == 'NOT_IMPLIED'
    assert r['service_bound'] == 'BOUND_MISSING' and not r['fulltoken']


@pytest.mark.parametrize('key,value', [('rn',0), ('life_state',1), ('kvd_v',0),
    ('desc_v',0), ('start_ready',0), ('service_fault',1), ('stage_v',1),
    ('mmode',0), ('pos',126), ('nout',127), ('window_region_ok',0),
    ('phase',1), ('time_ps',140500), ('last_gen',2), ('rn',True), ('pos',1.5),
    ('last_gen',-1), ('last_gen',65536)])
def test_source_guard_identity_and_stale_phase_rejected_before_mutation(key,value):
    s,e = packets();s[key]=value;before=s.copy()
    with pytest.raises(ValueError): validate_descriptor(s,e)
    assert s == before


@pytest.mark.parametrize('key,value', [('generation',2), ('generation',0),
    ('rows',127), ('user',1), ('pos',128), ('phase',1), ('time_ps',142500)])
def test_wrong_event_generation_or_phase(key,value):
    s,e=packets();e[key]=value
    with pytest.raises(ValueError):validate_descriptor(s,e)


def test_wrap_requires_drained_and_wraps_to_one():
    s,e=packets();s['last_gen']=65535
    validate_descriptor(s,e)
    s['wrap_drained']=0
    with pytest.raises(ValueError):validate_descriptor(s,e)


def test_accepted_beat_priority_over_acceptance():
    s,e=packets();s.update(beat_v=1,beat_ready=1)
    with pytest.raises(ValueError):validate_descriptor(s,e)


def test_all_false_and_stale_legacy_gate_cannot_bind_descriptor():
    for gate in ['time=142000 kvd_v=0 me_ready=0 kv_ok=0 win_idle=0',
                 'time=141000 kvd_v=1 me_ready=1 kv_ok=0 win_idle=1']:
        with pytest.raises(ValueError):legacy_descriptor_status(
            'D1_REAL_GATE '+gate+'\nD1_REAL_DESCRIPTOR time=142000 generation=1 rows=128')


def test_same_edge_legacy_marker_still_cannot_prove_generation_association():
    r=legacy_descriptor_status('D1_REAL_GATE time=142000 kvd_v=1 kv_ok=0\n'
        'D1_REAL_DESCRIPTOR time=142000 generation=1 rows=128')
    assert r['status']=='UNBOUND_DESCRIPTOR_CAUSAL_PROVENANCE'


def strict_trace():
    def healthy():
        lines=['D1_RESET_ACCEPT time_ps=6000 rn=1']
        lines += [f'D1_QUALIFIED_PRIME time_ps={7501+row*1000} row={row} rn=1 valid=1 active=1 tag={row} user=0 blocks=ffff' for row in range(128)]
        return '\n'.join(lines+['D1_ALL128_PRIMED time_ps=134501 accepted=128 rn=1',
            'D1_REAL_GATE time=140000 pc=0 me_ready=1 kv_ok=1 kvd_v=0 win_idle=1 waited=1 q_gate=1 m0_gate=1',
            'D1_REAL_DESCRIPTOR time=142000 generation=1 rows=128',
            'D1_REAL_ACCEPT time=145000 address=262144 tag=7 write=0',
            'D1_REAL_RESPONSE time=200000 tag=7 beat=0',
            'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY reads=1 returns=1 writes=0 acks=0',
            'D1_TERMINAL_PREFIX_ONLY evals=400 time_ps=200501 cycles=197'])
    s,e=packets()
    text=healthy().replace('time=140000 pc=0 me_ready=1 kv_ok=1 kvd_v=0',
        'time=141500 pc=0 me_ready=1 kv_ok=0 kvd_v=1').replace(
        'D1_REAL_DESCRIPTOR time=142000','D1_REAL_DESCRIPTOR time=141500')
    read=dict(time_ps=145000, generation=1,user=0,pos=127,address=262144,tag=7,write=0,phase=0)
    return text,s,e,read


def test_strict_entrypoint_model_control_not_actual_packet_claim():
    from tools.w17_D1_descriptor_provenance import verify_causal_first_return
    r=verify_causal_first_return(strict_trace()[0],0,*strict_trace()[1:])
    assert r['service_bound']=='BOUND_MISSING' and not r['fulltoken']


@pytest.mark.parametrize('key,value',[('generation',2),('user',1),('pos',128),
    ('tag',8),('time_ps',145500),('phase',1),('write',1)])
def test_first_return_requires_descriptor_read_generation_and_same_edge(key,value):
    from tools.w17_D1_descriptor_provenance import verify_causal_first_return
    text,s,e,read=strict_trace();read[key]=value
    with pytest.raises(ValueError):verify_causal_first_return(text,0,s,e,read)
