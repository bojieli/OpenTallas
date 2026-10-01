import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_provider_resource_calendar import write_calendar


def request(i,pc=None,ready=0):
    return {'id':str(i),'producer_result_id':'writer:'+str(i),'payload_sha256':'source-bound-test-fixture',
        'epoch':1,'tag':i,'stack':0,'PC':i if pc is None else pc,'sector':i,
        'earliest_column_ps':0,'DRAM_eligibility_source_event':'fixture-open-row:'+str(i),
        'DRAM_eligibility_valid_until_ps':1000000,
        'ACK_ready_ps':ready,'byte_mask':(1<<32)-1}


def run(q,depth=4):return write_calendar(q,depth,1000,2000,7274,10000)


def test_independent_PC_wave_not_free_global_serialization():
    d=run([request(i) for i in range(32)],32)
    assert {e['pending_reserved_and_column_ps'] for e in d['calendar']}=={'0'}
    assert all(e['backing_visible_ps']=='8000' for e in d['calendar'])


def test_depth_four_stalls_before_column_and_holds_ACK():
    d=run([request(i) for i in range(5)])
    assert d['calendar'][4]['pending_reserved_and_column_ps']=='18000'
    assert max(e['pending_payload_slots_after_reservation'] for e in d['calendar'])==4


def test_ACK_ready_backpressure_retains_payload_not_just_acceptance():
    d=run([request(0,ready=50000),request(1)],1)
    assert d['calendar'][1]['pending_reserved_and_column_ps']=='50000'


def test_same_PC_column_spacing_and_address_visibility():
    a=request(0,pc=0);b=request(1,pc=0)
    assert run([a,b],32)['calendar'][1]['pending_reserved_and_column_ps']=='2000'
    b['sector']=a['sector']
    assert run([a,b],32)['calendar'][1]['pending_reserved_and_column_ps']=='8000'


def test_maskedwrite_and_missing_actual_eligibility_failclosed():
    q=request(0);q['byte_mask']=0x10001
    assert run([q])['calendar'] is None


def test_capacity_stall_cannot_reuse_expired_DRAM_eligibility():
    q=request(1);q['DRAM_eligibility_valid_until_ps']=1000
    d=run([request(0),q],1)
    assert d['calendar'] is None
    assert d['issues']==['capacity_stall_requires_fresh_row_bank_refresh_eligibility']
    q=request(0);q['DRAM_eligibility_source_event']=None
    assert run([q])['calendar'] is None
