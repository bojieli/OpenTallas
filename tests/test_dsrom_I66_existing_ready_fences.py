import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_existing_ready_fences as M

EXPECTED=[(66,67,70),(67,68,70),(68,69,80),(69,72,80),
          (72,73,85),(73,79,85),(82,83,90),(83,84,90),
          (87,88,95),(88,89,95),(92,93,98),(93,94,98)]


def test_all_twelve_have_existing_later_ROM_ready_fence():
    p=M.proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=False)
    assert [(r['producer_pc'],r['first_later_ROM_ready_fence_pc'],r['first_consumer_pc']) for r in p['certificates']]==EXPECTED
    assert p['all_twelve_visibility_before_read']
    assert p['all_twelve_bank_credit_before_consumer']
    assert not p['actual_source_guard_implemented']
    assert p['numerical_service_upper_bound'] is None
    assert not p['actual_hazard_or_deadlock_observed']


def test_final_pair_has_I94_ready_fence_before_I98():
    d={r['pc']:r for r in M.descriptors()}
    assert [(pc,d[pc]['unit'],d[pc]['wait']) for pc in range(94,98)]==[(94,3,0),(95,2,0),(96,6,31),(97,3,0)]
    assert d[94]['decoded_fields']['qe_mode']==d[97]['decoded_fields']['qe_mode']==0
    assert d[94]['decoded_fields']['qe_nout']==d[97]['decoded_fields']['qe_nout']==1280
    assert d[95]['source_instruction']['_reads']==['GU4','WGT']
    assert d[98]['source_instruction']['_reads']==['GU5','WGT']
    last=M.find_fences(list(d.values()))[-1]
    assert last['all_later_ROM_ready_fences_before_consumer']==[94,97]
    assert last['alternate_collective_all_idle_fences']==[96]


def test_old_idle_or_dispatch_gap_does_not_itself_prove_new_visibility():
    p=M.proof(ready_holds_visibility_credit=False,idle_holds_visibility_credit=False)
    assert not any(c['visibility_before_read_proved'] for c in p['certificates'])
    assert not p['actual_hazard_or_deadlock_observed']


def test_collectives_alone_cover_ten_operands_not_first_two():
    p=M.proof(ready_holds_visibility_credit=False,idle_holds_visibility_credit=True)
    assert [c['visibility_before_read_proved'] for c in p['certificates']]==[False,False]+[True]*10
    assert not p['all_twelve_visibility_before_read']


def test_both_ready_and_idle_fences_preserve_proof():
    p=M.proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=True)
    assert p['all_twelve_visibility_before_read']
    assert not p['circular_policy']


def test_bank_generation_held_through_future_SU_read_is_incompatible_policy():
    p=M.proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=False,separate_VM_lease=False)
    assert p['circular_policy']
    assert not p['all_twelve_visibility_before_read']
    assert not p['actual_hazard_or_deadlock_observed']


def test_credits_can_rearm_on_same_postedge_but_issue_must_be_later():
    p=M.proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=False)
    edges=p['certificates'][0]['ordering_edges']
    assert next(e for e in edges if e['before']=='66.all_positive_credit_returns' and e['after']=='66.bank_rearm')['edge_relation']=='<='
    assert next(e for e in edges if e['before']=='66.bank_rearm' and e['after']=='67.core_ROM_issue')['edge_relation']=='<'


@pytest.mark.parametrize('value',[1,0,None,1.0])
def test_policy_types_cannot_forge_boolean_assumptions(value):
    with pytest.raises(ValueError):M.proof(ready_holds_visibility_credit=value,idle_holds_visibility_credit=False)


def release_case():
    o=M.D.source_model()['obligations'][0];p=o['phase_choices'][0]
    identity=dict(node=o['producer_node'],expert=0,rank=0,generation=7,user=0x1234ffff,xversion=2,
                  owner_stage=p['stage'],phase=p['phase'],key_word=p['source_key_word'])
    release=dict(identity=copy.deepcopy(identity),all_VM_visible=1,all_captured_credits=1,
                 all_packet_ACKs=1,source_retired=1,rearm_postNBA_edge=1,later_ROM_core_issue_preedge=2)
    return identity,release


def test_previous_owned_phase_release_not_next_selected_owner_idle():
    i,r=release_case()
    assert M.check_previous_owner_release(i,r)
    r['identity']['owner_stage']=1
    with pytest.raises(ValueError,match='previous owner'):M.check_previous_owner_release(i,r)


@pytest.mark.parametrize('mutation',['publication','credit','ACK','source','sameedge','highuser','generation','float','float_identity'])
def test_release_guard_rejects_weak_or_stale_receipt_without_mutation(mutation):
    i,r=release_case()
    if mutation=='publication':r['all_VM_visible']=0
    elif mutation=='credit':r['all_captured_credits']=0
    elif mutation=='ACK':r['all_packet_ACKs']=0
    elif mutation=='source':r['source_retired']=0
    elif mutation=='sameedge':r['later_ROM_core_issue_preedge']=1
    elif mutation=='highuser':r['identity']['user'] &=0xffff
    elif mutation=='generation':r['identity']['generation']+=1
    elif mutation=='float_identity':r['identity']['generation']=7.0
    else:r['all_VM_visible']=1.0
    before=copy.deepcopy((i,r))
    with pytest.raises(ValueError):M.check_previous_owner_release(i,r)
    assert (i,r)==before


@pytest.mark.parametrize('field',['unit','qe_mode','pred','wait','qe_nout'])
def test_patched_W2_cannot_silently_change_fencing_control(field,monkeypatch,tmp_path):
    rows=json.loads((M.OUT/'inputs/selected_range_QE_words.json').read_text())
    r=next(r for r in rows if r['node']=='L0.I94')
    offset,_=M.layout()[field]
    r['word_hex']=f"{int(r['word_hex'],16)^(1<<offset):0512x}"
    (tmp_path/'inputs').mkdir()
    (tmp_path/'inputs/selected_range_QE_words.json').write_text(json.dumps(rows))
    monkeypatch.setattr(M,'OUT',tmp_path)
    with pytest.raises(ValueError,match='outside address fields'):M.descriptors()


def test_exact_current_I66_word_and_scope():
    m=M.model()
    d=next(d for d in m['descriptors'] if d['pc']==66)
    assert d['intended_word_sha256']=='7d6b2b75445e34120a69fbe6fad3e6bffc7be53734200f3386f33fbe3c514dc5'
    assert m['unit_counts']=={'2':10,'3':17,'4':1,'6':5}
    assert not m['additional_SU_guard_selected']
    assert m['current_accepted_journal'] is None
    assert not m['actual_wrong_data_or_deadlock_claim']
    assert m['finite_successful_provider_bound'] is None
