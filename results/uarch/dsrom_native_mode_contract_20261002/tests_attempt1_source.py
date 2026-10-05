import copy,gzip,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_native_mode_contract as M
import dsrom_native_weight_address_join as J


def demand():return json.load(gzip.open(J.D/'inputs/demand-r5.json.gz','rt'))


def test_seven_exact_bf_producers_and_retirement_dependencies():
    ps=[M.prove_input(demand(),n) for n in M.COMPRESSORS+['Lhead.I5']]
    assert [p['producer'] for p in ps]==['L2.I6','L2.I6','L8.I6','L8.I6','L14.I16','L14.I16','Lhead.I4']
    assert all(p['VM_elements']==[46464,51584] and p['descriptor_round_bit_unchanged']==0 and p['result_format']=='FP32' for p in ps)
    assert all(p['physical_VM_delivery_visibility_and_same_generation_required'] for p in ps)


def test_all65536_bf_words_rne_idempotent_and_fp32_counterexample():
    assert all(M.bf_round_bits(hi<<16)==hi for hi in range(65536))
    assert M.bf_round_bits(0x3f808001)==0x3f81 # arbitraryFP32 input changes; blanket round0 illegal


@pytest.mark.parametrize('field,value',[('rnd',0),('su_nin',5119),('o_si',2),('pred',1)])
def test_bad_producer_rejects_round0(field,value):
    d=demand();next(n for n in d['nodes'] if n['id']=='L2.I6')['instruction'][field]=value
    with pytest.raises(ValueError,match='producer'):M.prove_input(d,'L2.I24')


def test_round0_requires_delivery_lease_and_authenticated_phase():
    p=M.prove_input(demand(),'L2.I24')
    assert M.allowed_mode('L2.I24',p,True,True,True)
    for flags in [(False,True,True),(True,False,True),(True,True,False)]:assert not M.allowed_mode('L2.I24',p,*flags)
    assert not M.allowed_mode('Lhead.I5',p,True,True,True)


def test_intervening_writer_and_wait_removal_negative():
    d=demand();next(n for n in d['nodes'] if n['id']=='L2.I8')['instruction']['qe_obase']=46464
    with pytest.raises(ValueError,match='intervening'):M.prove_input(d,'L2.I24')
    d=demand()
    for n in d['nodes']:
        if n['scope']==2 and n.get('instruction_index',-1) in range(7,25):n['instruction']['wait']=0
    with pytest.raises(ValueError,match='dependency'):M.prove_input(d,'L2.I24')


def test_alias_negatives_fullwidth_before_truncate():
    base=1<<21
    assert (base+512*4096)&((1<<30)-1)==2<<21
    assert (base+262144*4096)&((1<<30)-1)==base
    for x in [-1,384,512,262144,2**32-1,1.0]:
        with pytest.raises(ValueError):M.effective_key(base,4096,x)
    assert M.effective_key(base,4096,383)==base+383*4096


def test_invalid_terminal_faults_before_owner_even_ready():
    a=M.Admission();a.step(start=True,indexed=True,vm_accept=True)
    x=a.step(rsp=(0,512,False),owner_ready=True)
    assert a.fault and x['VM_credits']==0 and x['owner_credits']==0 and not x['owner_valid']
    assert x['local_cancel_ack']


def test_held_owner_request_actual_accept_edge_only():
    a=M.Admission();x=a.step(start=True)
    assert x['owner_valid'] and x['owner_credits']==0
    for _ in range(5):assert a.step()['owner_credits']==0
    assert a.step(owner_ready=True)['owner_credits']==1
    assert not a.pending


def test_same_edge_cancel_response_or_owner_accept_priority():
    a=M.Admission();a.step(start=True,indexed=True,vm_accept=True)
    x=a.step(rsp=(0,3,False),owner_ready=True,cancel=True)
    assert x['local_cancel_ack'] and x['owner_credits']==0
    a=M.Admission();a.step(start=True)
    assert a.step(owner_ready=True,cancel=True)['owner_credits']==0
    a=M.Admission();assert a.step(start=True,indexed=True,vm_accept=True,known_fault=True)['VM_credits']==0


def test_cancel_after_owner_accept_ack_does_not_remove_owner():
    a=M.Admission();a.step(start=True);a.step(owner_ready=True)
    x=a.step(cancel=True)
    assert x['local_cancel_ack'] and not x['all_accepted_owner_credits_drained'] and x['owner_credits']==1
    with pytest.raises(ValueError):a.rearm(source_ack=True,owner_retired=True,delivery_fence=True,causal_visibility=True,provenance=True)
    a.step(owner_retire=True)
    a.rearm(source_ack=True,owner_retired=True,delivery_fence=True,causal_visibility=True,provenance=True)
    assert a.era==1


def test_held_poison_stale_duplicate_and_rearm_fences():
    a=M.Admission();a.step(start=True,indexed=True,vm_accept=True);a.step(cancel=True)
    for _ in range(8):assert not a.step()['local_cancel_ack']
    assert not a.step(rsp=(1,0,False))['local_cancel_ack'] # stale does not retire currentera
    assert a.step(rsp=(0,0,True))['local_cancel_ack'] # matchingpoison drains withoutready
    a.step(rsp=(0,0,False));assert a.fault
    with pytest.raises(ValueError):a.rearm(source_ack=True,owner_retired=True,delivery_fence=True,causal_visibility=False,provenance=True)
    a.rearm(source_ack=True,owner_retired=True,delivery_fence=True,causal_visibility=True,provenance=True)
    assert a.era==1


def test_head_exact_source_storage_coordinates_and_ties():
    a=M.head_address(0,0,0);z=M.head_address(3,32319,5119)
    assert a['pair']==2525 and a['physical_row']==0
    assert z['pair']==5049 and z['mb']==1 and z['physical_row']==2047 and z['bit_range']==[240,256]
    assert z['global_vocab_ID']==129279 and not z['native_ME_provider_adapter_implemented']
    assert M.argmax_pair([(32320,1.),(0,1.)])==(0,1.)
    assert M.argmax_pair([(8,-0.),(2,0.)])[0]==2
    with pytest.raises(ValueError):M.argmax_pair([(0,float('nan'))])
    with pytest.raises(ValueError):M.head_address(4,0,0)


def test_composed_cost_no_physical_no_loss_or_latency_transfer():
    x=M.model();cost=x['composition_cost'];h=x['dedicated_head']
    assert cost['new_FF_bits_per_adapter']==6 and cost['uniform_policy_bits_all58x4']==237568
    assert cost['healthy_added_compressor_cycles_if_producer_and_cfg_fences_already_satisfied']==0
    assert h['weight_storage_pairs_global']==2525 and h['existing_source_tree_price']['total_owned_source_argmax_bits']==6951
    assert not x['expert_spatial_split']['single_token_no_loss_proved']
    assert x['expert_spatial_split']['six_selected_result_bits_per_rank']==245760
    assert not x['readiness']['RTL_ready_before_provider_event_calendar']
