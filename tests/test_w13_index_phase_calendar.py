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
