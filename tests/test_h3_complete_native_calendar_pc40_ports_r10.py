import importlib.util
import json
import copy
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dewey_pc40_ports_r10',ROOT/'tools/h3_complete_native_calendar_pc40_ports_r10.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_actual_three_reads_five_writes_no_assumed_credit():
    c=m.compile_ports()
    assert c['RF_read_pairs']==3 and c['RF_read_bits']==24576
    assert c['RF_writes']==5 and c['RF_physical_mirror_write_bits']==40960
    assert c['physical_RF_transaction_credits']==1 and not c['read_write_simultaneous']
    assert c['W2_HBM_commands']==0 and not c['parent55_fabricated']
    home=next(e for e in c['events'] if e['phase']=='HOME_RD')
    assert home['read_a']==home['read_b']==38 and home['physical_read_copies']==2
    assert home['logical_unique_vectors']==1
    assert c['live_workspace_scope']=='REFUSED_MISSING_ENTERING_LEASES'
    assert c['finite_production_upper'] is None and c['whole_token_ns'] is None
    assert c['W6_ACK_and_request_deduplicated']
    fence=c['events'][-1]
    assert fence['end_min_edge']-fence['start_min_edge']==17


@pytest.mark.parametrize('slot',[17,18,19])
def test_live_workspace_collisions(slot):
    with pytest.raises(ValueError,match='workspace alias'):
        m.compile_ports(entering_live_leases=[{'slot':slot,'lease':'already_live'}])


@pytest.mark.parametrize('bound',[0,-1,False,1.0])
def test_no_zero_or_implicit_finite_bounds(bound):
    with pytest.raises(ValueError):m.compile_ports(service_wait_bound=bound)


def test_conditional_bound_does_not_become_installed():
    c=m.compile_ports(service_wait_bound=4,entering_live_leases=[{'slot':16,'lease':'caller'}])
    assert c['external_service_wait_bound_assumed']==4
    assert not c['external_service_wait_bound_installed'] and c['finite_production_upper'] is None
    assert c['conditional_extra_wait_edges']==75
    assert c['conditional_source_reservation_edges']==c['source_min_edge_obligations']+75


def test_changed_actual_read_contract_refuses(monkeypatch):
    src=m.inputs();src['RF.sv']=src['RF.sv'].replace('!read_pending && !rsp_valid && !ack_valid','1')
    monkeypatch.setattr(m,'inputs',lambda:src)
    with pytest.raises(ValueError,match='held transaction'):m.compile_ports()


def test_exact_caller_gate_replacement_and_remote_up():
    caller=json.loads(m.inputs()['caller.json']);joined=m.compose_caller(m.compile_ports(),caller)
    assert joined['total_caller_callee_RF_read_pairs']==4
    assert joined['source_up_RF']['SM']==24 and joined['source_up_RF']['slot']==32
    assert joined['gate_read_replacement']['both_physical_copies_still_paid']
    assert joined['caller_retained_slot_admission']=='REFUSED_UNBOUND'
    assert joined['NoC_and_CDC_min_edge_inputs'] is None
    assert not joined['production_admitted']


@pytest.mark.parametrize('mutation',['slot','lease','remote','HBM'])
def test_wrong_caller_cannot_deduct_gate_service(mutation):
    caller=json.loads(m.inputs()['caller.json'])
    if mutation=='slot':caller['source_gate_home']['RFslot9']=39
    elif mutation=='lease':caller['source_gate_home']['lease']='stale'
    elif mutation=='remote':caller['source_up_home']['storage_SM']=0
    elif mutation=='HBM':caller['source_up_home']['parent55']=17
    with pytest.raises(ValueError):m.compose_caller(m.compile_ports(),caller)
