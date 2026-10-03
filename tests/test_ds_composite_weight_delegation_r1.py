"""Constructor-free delegation/source-fit gates; owner receipts are fixtures."""
import copy
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_composite_weight_delegation_r1 as D

@pytest.fixture(scope='module')
def records():
    out=ROOT/D.OUT
    return tuple(json.loads((out/name).read_bytes()) for name in ['model-r1.json','selected-bound-native-r1.json','adapted-call-enrollment-r1.json'])


def fixture_receipts(policy):
    # Fixture ONLY. No checkpoint, state bytes, provider, engine, or proof created.
    identity=dict(source_sha256={'original_owner.py':'a'*64},manifest_sha256='a'*64,
        native_sha256=policy['native_sha256'],homes_sha256='b'*64,generation=1,revision='fixture')
    producer=dict(producer_seal=dict(state_sha256='c'*64,payload_sha256='d'*64,schema=D.V3.SCHEMA),actual_observations_sha256='e'*64)
    restored=dict(schema='DS_RESTORED_RUN_SCOPE_RECEIPT_V1',producer_checkpoint_receipt=producer,
        old_identity=identity,new_identity=identity,retired=list(range(11)),
        old_run_scope=dict(prefix_stop=10,journal_root='/old',journal_capacity_bytes=131072),
        new_run_scope=dict(prefix_stop=19,journal_root='/new',journal_capacity_bytes=131072),
        explicit_transition=None,role_proof={})
    restored['seal_sha256']=D.C.digest(restored)
    return identity,producer,restored


def test_actual_home_bound_source_fit_not_raw_c65_transfer(records):
    m,native,enrollment=records;fit=m['source_fit']
    assert fit['PCs']==2213 and fit['only_captured_write_home_indices_changed']
    assert fit['primitive_templates_byte_identity']
    assert fit['captured_native_canonical_sha256']=='9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d'
    assert fit['original_native_canonical_sha256']!=fit['captured_native_canonical_sha256']
    assert not fit['original_constructor_and_MRO_transfer']
    assert not m['admission'] and m['actual_checkpoint_receipt'] is None
    assert m['baseline_V3_restore_and_RAM_projection_reused_not_zero']
    assert m['additional_producer_state_or_checkpoint_payload_copy_bytes']==0
    plans=[]
    for op in native['instructions']:
        for owned in op['rank_bindings']:
            t=owned['template'];plans.append(D.C.resolve_call(native,enrollment,'weight',op['provider_bindings'][t]['weight'],owned,native['templates'][t]['providers']['weight']))
    assert len(plans)==288


@pytest.mark.parametrize('mutation',['tensor_order','rows','format','K','primitive_operand','home_type'])
def test_source_fit_rejects_arithmetic_and_identity_mutants(records,mutation):
    _,native,_=records;old=native['instructions'][0];new=copy.deepcopy(old)
    if mutation=='tensor_order':new['source_op']['w'].reverse()
    elif mutation=='rows':new['rank_bindings'][0]['row_interval'][1]+=1
    elif mutation=='format':new['source_op']['fmt']='fp8'
    elif mutation=='K':new['source_op']['k']-=1
    elif mutation=='primitive_operand':new['provider_bindings'][new['rank_bindings'][0]['template']]['weight']['logical_tensor'].reverse()
    else:new['writes'][0]['home_indices']=[True]
    with pytest.raises(ValueError):D.compare_operations(old,new)


def test_only_captured_home_indices_may_change(records):
    _,native,_=records;old=native['instructions'][0];new=copy.deepcopy(old)
    new['writes'][0]['home_indices']=[987654]
    assert D.compare_operations(old,new)==[dict(write=0,old=old['writes'][0]['home_indices'],captured=[987654])]
    # This is structural fit only, never legal-home admission; V3's captured
    # homes/source/backing verification remains mandatory in the actual gate.


def test_original_identity_owner_binding_positive_fixture_only(records):
    policy=records[0]['policy'];identity,producer,restored=fixture_receipts(policy)
    gate=D.verify_owner_binding(policy,captured_identity=identity,restored_identity=identity,
        checkpoint_receipt=producer,restore_receipt=restored)
    assert gate['next_PC']==11 and gate['class_and_MRO_unchanged']
    assert not gate['handler_payload_or_controller_admitted']
    assert 'actual_owner_verification' not in gate


@pytest.mark.parametrize('mutation',['MRO','native','receipt','seal','prefix_hole','prefix_repeat','future_PC'])
def test_owner_gate_refuses_source_changes_or_prefix_replay(records,mutation):
    policy=records[0]['policy'];old,producer,receipt=fixture_receipts(policy);new=copy.deepcopy(old)
    if mutation=='MRO':new['source_sha256']['new_mixin.py']='f'*64;receipt['new_identity']=new
    elif mutation=='native':old['native_sha256']='f'*64;new=copy.deepcopy(old);receipt['old_identity']=old;receipt['new_identity']=new
    elif mutation=='receipt':producer=copy.deepcopy(producer);producer['producer_seal']['payload_sha256']='f'*64
    elif mutation=='seal':receipt['seal_sha256']='f'*64
    elif mutation=='prefix_hole':receipt['retired'].remove(7)
    elif mutation=='prefix_repeat':receipt['retired']=list(range(10))
    else:receipt['retired']=list(range(12))
    if mutation!='seal':receipt['seal_sha256']=D.C.digest({k:v for k,v in receipt.items() if k!='seal_sha256'})
    with pytest.raises(ValueError):D.verify_owner_binding(policy,captured_identity=old,restored_identity=new,checkpoint_receipt=producer,restore_receipt=receipt)


def test_missing_actual_owner_receipts_is_not_admission(records):
    with pytest.raises(ValueError,match='actual sealed checkpoint'):
        D.verify_owner_binding(records[0]['policy'],captured_identity={},restored_identity={},checkpoint_receipt=None,restore_receipt=None)


def test_original_scope_guard_still_refuses_new_MRO(records):
    policy=records[0]['policy'];old,_,receipt=fixture_receipts(policy);new=copy.deepcopy(old);new['source_sha256']['new_mixin.py']='f'*64
    t=dict(schema='DS_EXPLICIT_RUN_SCOPE_TRANSITION_V1',old_identity=old,new_identity=new,
        old_run_scope=receipt['old_run_scope'],new_run_scope=receipt['new_run_scope'],next_pc=11,checkpoint_receipt={},role_proof={})
    t['seal_sha256']=D.C.digest(t)
    with pytest.raises(ValueError,match='data identity changed'):
        D.V3.validate_scope_transition(t,old_identity=old,new_identity=new,
            old_scope=t['old_run_scope'],new_scope=t['new_run_scope'],next_pc=11,role_proof={})
