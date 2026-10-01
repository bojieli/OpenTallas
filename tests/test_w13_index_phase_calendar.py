import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_phase_calendar import audit,intake

def event():
 return dict(id='x',op='IADD',dependencies=[],sm=0,partition=0,warp_slot=0,RF_read_tick=0,issue_tick=8,writeback_tick=36,RF_register_reads=[0,1],RF_register_writes=[2],RF_write_copy_count=2)

def lease():
 return {**{k:40 for k in ['raw_decode_consumer_done','packer_scratch_consumer_done','decoded_store_visible','old_generation_return_drained','score_scratch_first_store']},'payload_WR_visible':0,'descriptor_WR_visible':3,'reverse_CDC_ack':6,'read_lease_acquired':9,'consumer_done':40,'credit_return':43,'physical_provider_source_pin':None}

def test_no_software_completion_clock_credit():
 d=intake();assert 'ordinary_runtime_events_missing' in d['issues'];assert 'actual_phase_leases_missing' in d['issues'];assert not d['physical_admission']

def test_alias_early_and_three_read_negative():
 e=event();e['RF_register_reads']=[0,1,2];l=lease();l['score_scratch_first_store']=39
 d=audit([e],[l],{'x':{'op':'IADD','dependencies':[]}})
 assert 'RF_2R1W_register_aperture' in d['issues'];assert 'score_alias_before_consumers_drained' in d['issues']

def test_bank_collision_and_copywrite_negative():
 e=event();e.update(shared_write_words=[0,32],shared_service_tick=8,shared_store_visible_tick=8,RF_write_copy_count=1)
 d=audit([e],[lease()],{'x':{'op':'IADD','dependencies':[]}})
 assert 'shared_bank_write_collision' in d['issues'];assert 'physical_RF_readcopy_write_missing' in d['issues']

def test_authoritative_edge_omission_and_ACK_future_negative():
 e=event();l=lease();l['descriptor_WR_visible']=99
 d=audit([e],[l],{'x':{'op':'IADD','dependencies':['producer']}})
 assert 'authoritative_source_event_mismatch:x' in d['issues'];assert 'publication_lease_event_order' in d['issues']

def version_fixture(overwrite_tick=76,consumer_read=80):
    events=[];source={}
    for name,read,finish,rr,producer in [('A',0,36,[0,1],None),('B',40,overwrite_tick,[0,1],None),('consumer_A',consumer_read,consumer_read+36,[2,0],'A')]:
        e=event();e.update(id=name,RF_read_tick=read,issue_tick=read+8,writeback_tick=finish,RF_register_reads=rr,RF_register_writes=[3] if producer else [2],phase_entry_RF_visible_ticks={'0':0,'1':0})
        operands=[dict(operand_index=j,register=v,producer_event='A' if producer and j==0 else 'phase_input:'+str(v),result_id='A.result' if producer and j==0 else 'input.'+str(v)) for j,v in enumerate(rr)]
        results=[dict(register=e['RF_register_writes'][0],result_id=name+'.result')]
        e.update(dependencies=[producer] if producer else [],operand_register_bindings=operands,result_register_bindings=results)
        source[name]=dict(op='IADD',dependencies=e['dependencies'],operand_register_bindings=operands,result_register_bindings=results)
        events.append(e)
    l=lease();l['physical_provider_source_pin']={'synthetic_test_only':True}
    return events,[l],source

def test_exact_parent_stale_register_version_negative():
    d=audit(*version_fixture())
    assert not d['candidate_event_constraints_pass']
    assert 'stale_register_version:consumer_A' in d['issues']
    assert 'register_overwrite_before_last_consumer:A' in d['issues']

def test_delayed_overwrite_after_consumer_positive():
    events,leases,source=version_fixture(overwrite_tick=116,consumer_read=40)
    events[1].update(RF_read_tick=80,issue_tick=88)
    d=audit(events,leases,source)
    assert d['issues']==[] and d['candidate_event_constraints_pass']
    assert not d['physical_admission']

def test_source_identity_ignored_or_mutated_is_rejected():
    events,leases,source=version_fixture()
    events[-1]['operand_register_bindings']=[dict(operand_index=0,register=2,producer_event='B',result_id='B.result'),events[-1]['operand_register_bindings'][1]]
    d=audit(events,leases,source)
    assert 'callback_operand_result_identity_mismatch:consumer_A' in d['issues']
    del source['A']['result_register_bindings']
    assert 'source_operand_result_identity_unbound:A' in audit(events,leases,source)['issues']
