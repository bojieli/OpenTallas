import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('local',ROOT/'tools/dsrom_par2_local_ECC_calendar.py');M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
P=json.loads((ROOT/'results/uarch/dsrom_par2_local_ECC_calendar_20261002/provisional_parameters.json').read_text())

def test_exact_one_credit_hold_and_causal_decode():
    c=M.calendar((2,),P,trace=True)
    reads=[e['tick'] for e in c['event_trace'] if e['edge']=='local_read_accept']
    assert reads==[0,5]
    assert c['raw_prefetch_terminal_tick']==10 and c['earliest_compute_relative_to_authenticated_external_ready']==14
    assert c['incremental_prefetch_and_new_ECC_cycles']==12
    assert c['peak_read_debt']==1 and c['final_read_debt']==0

def test_shared_lane_contention_is_real():
    fast=M.calendar((4,4,4,4),P)
    q=dict(P,decoder_topology='shared',response_slots=1,decoder_lanes=1,delivery_lanes=1)
    slow=M.calendar((4,4,4,4),q)
    assert slow['raw_prefetch_terminal_tick']>fast['raw_prefetch_terminal_tick']
    assert slow['peak_reserved_response_slots']<=1

def test_delivery_backpressure_reserves_future_queue_capacity():
    q=dict(P,delivery_lanes=1,delivery_II=4,delivery_queue_slots=1)
    c=M.calendar((3,3,3,3),q)
    assert c['good_reads']==12 and c['final_read_debt']==0 and c['peak_delivery_queue_slots']<=1

def test_cancel_keeps_actual_accepted_debt_until_terminal():
    c=M.calendar((10,10),P,cancel_tick=1,trace=True)
    assert c['accepted_reads']==2 and c['good_reads']==2
    assert c['raw_prefetch_terminal_tick']==5 and c['final_read_debt']==0
    assert not c['compute_permission'] and c['earliest_compute_relative_to_authenticated_external_ready']=='REFUSED_ECC_OR_CANCEL'

def test_raw_ECC_fault_refuses_compute_and_drains():
    c=M.calendar((2,2),P,fault_read=0)
    assert c['fault_reads']==1 and c['good_reads']==3 and c['final_read_debt']==0
    assert not c['compute_permission']

def test_no_zero_or_unpriced_latency():
    for k in ('macro_capture_cycles','raw_decode_cycles','delivery_cycles','weight_ECC_cycles','first_main_codeword_capture_cycles','read_II'):
        q=dict(P);q[k]=0
        with pytest.raises(ValueError):M.calendar((1,),q)

def test_extra_credit_requires_area_reprice():
    with pytest.raises(ValueError):M.calendar((1,),dict(P,read_credits_per_leaf=2))

def test_actual_measurement_claim_without_receipt_refused():
    with pytest.raises(ValueError):M.calendar((1,),dict(P,latency_status='MEASURED'))

def test_deadline_delta_not_whole_token_rate():
    c=M.calendar((2,),P,deadline=12)
    assert c['exposed_deadline_delta']==2 and not c['hardware_no_token_loss_proven']
    assert M.calendar((2,),P)['exposed_deadline_delta']=='ORIGINAL_DEADLINE_UNBOUND'

@pytest.fixture(scope='module')
def product():return M.build(P)

def test_full_actual_phase_count_and_choices(product):
    m,r=product
    assert len(r)==46080 and m['full46080_FP4_phases_bound']
    assert m['provisional_selected_six_expert_work']['phase_calls']==720
    assert all(x['original_consumer_deadline']=='UNBOUND_NO_ZERO_COST_OR_OVERLAP_CREDIT' for x in r)

def test_exact_witness_addresses_and_terminal_order(product):
    m,r=product;w=m['witness']['calendar']
    assert w['accepted_reads']==800 and w['good_reads']==800 and w['raw_prefetch_terminal_tick']==2000
    assert w['earliest_compute_relative_to_authenticated_external_ready']==2004
    accepted={e['read_id']:e for e in w['event_trace'] if e['edge']=='local_read_accept'}
    for e in w['event_trace']:
        assert 0<=e['physical_row']<4096 and e['mirror_global_pair']>=2048
        assert e['original_global_pair']<2048 and e['same_protected256_plus10_identity']
        assert e['physical_row']==accepted[e['read_id']]['physical_row']
        assert e['tick']>=accepted[e['read_id']]['tick']

def test_zero_new_macros_and_no_admission(product):
    m,r=product
    assert m['new_macro_instances']==0
    assert m['current_physical_owner_join']['current_clearance_and_parity_construction_screen_mm2']==pytest.approx(732.9650770579258)
    assert m['current_physical_owner_join']['source_first_batch_conflict_rounds']==64
    assert m['existing_owner_authentication']['source_commit']=='24a072f17'
    assert not m['build_admitted'] and not m['no_token_loss_proven'] and not m['physical_area_route_and_SSFF_admitted']
    assert m['historical_storage_and_admission_proxies_not_current_wholebudget']['additive_macro_body_mm2']==0


def paired_owner_fixture():
    i=dict(candidate='DS4096-TP4-S58-PAR2-NP2048',stage=0,rank=0,shard=1,phase=12,generation=3,operation_sequence=12,owner_lease='synthetic-source-schema-test',request_nonce='read0')
    a=dict(stage=0,shard=1,local_site=25,mb=0,parity=0,physical_row=0)
    r=dict(identity=i,source_coordinate_receipt='synthetic-test-not-numerical-address-proof',mirror_manifest_sha256='a'*64,raw_address=a,mirrored_parity_address=a,parity_data_bit=0)
    t=dict(identity=dict(i),raw_address=a,mirrored_parity_address=a,mirror_manifest_sha256='a'*64,sidecar_SECDED_status='good',raw_ECC_status='good',status='good',paired_capture_consumed=True)
    return r,t


def test_existing_owner_terminal_stale_generation_cannot_authorize():
    r,t=paired_owner_fixture()
    assert M.owner_authorize(r,t)['arithmetic_authorized']
    t['identity']['generation']=2
    with pytest.raises(ValueError):M.owner_authorize(r,t)


def test_existing_owner_terminal_requires_both_decoders_and_consumption():
    r,t=paired_owner_fixture();t['raw_ECC_status']='poison';t['status']='poison'
    assert not M.owner_authorize(r,t)['arithmetic_authorized']
    t['paired_capture_consumed']=False
    with pytest.raises(ValueError):M.owner_authorize(r,t)
