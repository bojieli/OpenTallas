"""Python-only source/trace checks; no compiler, simulator, images or live getters."""
import sys,json,copy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import prepare_w17_connected_observation_driver as prep
import w17_connected_observation_model as m
from simulation_observation_api import encode

def frame(rank=0,cycle=1,mode='WINDOW',**fields):
    values=dict(epoch=1,cycle=cycle,rank=rank,ckv_available=int(mode=='CKV'));values.update(fields)
    return m.Frame(rank,cycle,False,0,0,0,encode(values))

def test_driver_inverse_exact_and_real_ports():
    before=(ROOT/prep.BASE).read_text();after,changes=prep.transform(before)
    assert after==(ROOT/prep.COPY).read_text() and prep.inverse(after,changes)==before
    assert after.count('d->observation_edge(uint64_t(cyc))')==1
    at=after.index('d->observation_edge(uint64_t(cyc))')
    assert after.index('pool.run(tot,',after.index('auto tick'))<at<after.index('link_step();',at)
    assert all(s in after for s in ['d->sim_obs_epoch = 1','d->sim_obs_packet','d->dbg_fs','W17_FULLTOKEN_OBSERVATION_OPT_IN'])
    assert 'd->eval();' not in changes[-1]['after']

def test_bad_transform_cannot_mutate_original():
    before=(ROOT/prep.BASE).read_text()
    with pytest.raises(ValueError):prep.transform(before.replace('    RtPool pool(threads);',''))
    assert (ROOT/prep.BASE).read_text()==before

@pytest.mark.parametrize('mode',['WINDOW','CKV'])
def test_real_abi_frames_drained_once(mode):
    s=m.Capture();s,events=m.feed(s,frame(mode=mode),mode)
    assert s.frames==1 and not events
    prior=s
    with pytest.raises(ValueError):m.feed(s,frame(mode=mode),mode)
    assert s==prior

@pytest.mark.parametrize('mutation',[
 lambda s:s.replace('OBS 0','OBS 4'),
 lambda s:s.replace('OBS 0 1 0','OBS 0 -1 0'),
 lambda s:s.replace('OBS 0 1 0','OBS 0 1 2'),
 lambda s:s[:-1],
 lambda s:s.replace('OBS 0','OBS 1'),
])
def test_trace_envelope_negative(mutation):
    line='OBS 0 1 0 00000000 00000000 0000000000000000 '+format(encode(dict(epoch=1,cycle=1,rank=0)),'0256x')
    with pytest.raises(ValueError):m.parse_frame(mutation(line))

def test_valid_real_trace_parse():
    p=encode(dict(epoch=1,cycle=1,rank=0));f=m.parse_frame('OBS 0 1 0 00000000 00000000 0000000000000000 '+format(p,'0256x'))
    assert f.packet==p

def test_fault_and_done_sameedge_sticky():
    from dataclasses import replace
    s,_=m.feed(m.Capture(),replace(frame(),done=True,fault=1),'WINDOW')
    assert s.done_seen[0] and s.sticky_faults[0]==1
    s,_=m.feed(s,frame(cycle=2),'WINDOW');assert s.sticky_faults[0]==1

def test_mode_unavailable_no_zero_qualification():
    before=m.Capture()
    with pytest.raises(ValueError):m.feed(before,frame(mode='CKV'),'WINDOW')
    assert before==m.Capture()

def test_native_request_then_qualified_reply_preserves_uncertified_scope():
    s,_=m.feed(m.Capture(),frame(window_prefetch_accept=1,window_prefetch_row=5,window_prefetch_user=2),'WINDOW')
    s,e=m.feed(s,frame(cycle=2,window_req_take=1,window_req_offer=1,window_req_ready=1,window_state=5,window_row=5,window_active_user=2,window_req_addr=42),'WINDOW')
    assert e[0].kind=='request'
    s,e=m.feed(s,frame(cycle=3,window_rsp_take=1,window_reply_ok=1,window_state=6,window_row=5,window_active_user=2),'WINDOW')
    assert e[0].kind=='reply' and not e[0].causal_certificate

def test_wrong_reply_owner_rejected_without_mutation():
    s=m.Capture()
    with pytest.raises(ValueError):m.feed(s,frame(window_rsp_take=1,window_reply_ok=1),'WINDOW')
    assert s==m.Capture()

def test_rank_starvation_not_hidden_by_other_rank_progress():
    guards=[m.accepted(m.Guard(0),('rank',r),0) for r in range(2)]
    guards[1]=m.retirement(guards[1],('rank',1),9,source_qualified=True,association_proven=True)
    starved,view=m.inspect_guard(guards[0],11,response_budget=10,scope='synthetic')
    assert 'RESPONSE_WINDOW_EXCEEDED' in view['diagnostics'] and starved.outstanding

def test_busy_pc_or_raw_reply_cannot_retire_or_renew():
    g=m.accepted(m.Guard(0),'owned',0)
    raw=m.retirement(g,'owned',9,source_qualified=True,association_proven=False)
    assert raw==g
    _,v=m.inspect_guard(g,11,response_budget=10,scope='synthetic')
    assert v['outstanding_ages']==(('owned',11),) and v['diagnostics']

def test_deadlock_and_long_healthy_refill_distinguished_in_synthetic_model():
    healthy=m.accepted(m.Guard(0),'sector',0)
    healthy=m.retirement(healthy,'sector',9,source_qualified=True,association_proven=True,response_budget=10,operation_budget=20,scope='synthetic')
    _,v=m.inspect_guard(healthy,19,operation_budget=20,response_budget=10,scope='synthetic');assert not v['diagnostics'] and not v['completion']
    dead=m.accepted(m.Guard(0),'sector',0)
    _,v=m.inspect_guard(dead,19,operation_budget=20,response_budget=10,scope='synthetic');assert v['diagnostics']==('RESPONSE_WINDOW_EXCEEDED',)

def test_late_completion_cannot_clear_sticky_violation():
    g=m.accepted(m.Guard(0),'sector',0)
    g=m.retirement(g,'sector',11,source_qualified=True,association_proven=True,response_budget=10,scope='synthetic')
    assert not g.outstanding and g.sticky_violations==('RESPONSE_WINDOW_EXCEEDED',)

def test_deadline_absolute_accept_not_restarted_by_retirement():
    g=m.accepted(m.Guard(0),'s0',0)
    g=m.retirement(g,'s0',19,source_qualified=True,association_proven=True,operation_budget=20,scope='synthetic')
    _,v=m.inspect_guard(g,21,operation_budget=20,scope='synthetic')
    assert v['operation_age']==21 and 'OPERATION_WINDOW_EXCEEDED' in v['diagnostics']

def test_no_causal_bounds_cannot_admit_universal_deadline():
    with pytest.raises(ValueError):m.inspect_guard(m.Guard(0),1,operation_budget=125727)
    _,v=m.inspect_guard(m.Guard(0),125727,operation_budget=125727,scope='conditional')
    assert not v['completion'] and not v['universal_timeout_admitted'] and v['causal_service']=='BOUND_MISSING'

def test_layeronly_or_template_cannot_gain_fulltoken_credit():
    required=[f'layer{i}' for i in range(40)]+['final_norm','vocabulary_head']
    for coverage,captures in [(['layer0'],{'layer0':m.Capture()}),(required,{s:m.Capture() for s in required})]:
        v=m.fulltoken_verdict(coverage,captures,{'claimed':'quiescent'},True)
        assert not v['numeric_or_fulltoken_credit'] and 'SOURCE_OWNER_PROVIDER_QUIESCENCE_UNAVAILABLE' in v['blockers']

def test_header_exact_trace_limit_and_no_inferred_retirement():
    text=(ROOT/prep.HEADER).read_text()
    assert 'uint64_t(4) << 30' in text and 'std::fopen(path,"wx")' in text
    assert 'pc' not in text and 'deadline' not in text and 'LIMIT-bytes' in text

def test_offline_trace_reports_no_fulltoken_credit():
    from check_w17_connected_observation_trace import check
    p=encode(dict(epoch=1,cycle=1,rank=0))
    trace=['W17_CAUSAL_TRACE_V1 layer0 WINDOW\n','OBS 0 1 0 00000000 00000000 0000000000000000 '+format(p,'0256x')+'\n']
    result=check(trace)
    assert result['frames']==1 and not result['fulltoken']['numeric_or_fulltoken_credit']
    assert result['physical_owner_quiescence']=='UNAVAILABLE'

def test_PC24_conditional_service_model_refuses_actual_completion():
    out=ROOT/'results/rtl/w17_connected_observation_fulltoken_preparation_20261002'
    review=json.loads((out/'PC24_review.json').read_bytes());scalar=json.loads((out/'PC24_owner_scalar.json').read_bytes())
    assert review['conditional_elapsed_cycles']==[123964,125727]
    assert review['conditional_end_cycles']==[136671,138146]
    assert review['conditional_watchdog_trigger_if_no_further_PC_change']==[112202,112401]
    assert all(c['reads']==2176 and c['elapsed_cycles']>100000 for c in scalar['cases'])
    for case in scalar['cases']:
        _,view=m.inspect_guard(m.Guard(case['start_cycle']),case['end_cycle'],operation_budget=125727,scope='conditional')
        assert not view['diagnostics'] and not view['completion'] and not view['universal_timeout_admitted']
    g=m.accepted(m.Guard(0),'actual_unreturned_sector',0)
    _,view=m.inspect_guard(g,125728,operation_budget=125727,scope='conditional')
    assert view['diagnostics'] and g.outstanding and not view['completion']

def test_actual_successor_manifest_preserves_fullshape_and_field_clock_binding():
    from plan_w17_connected_observation import build_plan
    plan=build_plan(ROOT)
    assert not plan['launch_allowed'] and not plan['commands_executed']
    for mode in plan['modes']:
        p=mode['parameters'];assert p['SUN']==256 and p['SUM']==64 and p['CL_DEPTH']==512 and p['ROM_PHW']==6
        for entry in mode['future_rank_commands']:
            cmd=entry['frontend_argv_template'];assert '--cc' in cmd and '--build' not in cmd and '--lint-only' not in cmd
            assert '-GRANK='+str(entry['rank']) in cmd and '--prefix' in cmd
    assert plan['causal_deadlines']=='BOUND_MISSING'
