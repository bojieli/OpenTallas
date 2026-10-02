import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_native_address_calendar_join as J

@pytest.fixture(scope='module')
def inputs():return J.load()
@pytest.fixture(scope='module')
def joined(inputs):return J.join(inputs)

def test_exact_native_weight_nonweight_and_head_census(joined):
    c=joined['native_address_join_census']
    assert c==dict(native_instructions=4778,weight_descriptors=1150,layer_weights_bound=1149,QE=1010,ME=140,nonweight_and_runtime_nodes=3737,head_unbound=1,unique_physical_phase_ordinals=46509,actual_runtime_indexed_calls=720,existing_words_validated_without_encoder=1149,phase_choice_matches=276909)
    assert len(joined['events'])==19548
    assert joined['templates']['Lhead.I5']['dedicated_head_provider_unbound']

def test_uses_producer_interfaces_no_address_compiler_or_allocator(inputs,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('duplicate compiler/encoder executed')
    monkeypatch.setattr(J.C,'compose',forbidden)
    monkeypatch.setattr(J.C.B,'encode_instruction',forbidden)
    monkeypatch.setattr(J.C.E,'emitted_owner_keys',forbidden)
    r=J.join(inputs)
    assert not r['address_compiler_or_allocator_rerun']
    assert r['descriptor_address_and_native_admission']['authoritative_commit'].startswith('d66047e51')

def test_native_control_hazards_and_costs_not_erased(joined):
    g=joined['native_entry_control_gate']
    assert not g['source_bad_EID_guard_present']
    assert g['fault_does_not_suppress_S_LOOK_to_S_GO']
    assert len(joined['descriptor_address_and_native_admission']['model']['native_admission_failures'])==7
    assert joined['whole_area_ledger_mm2']['conservative_no_containment_credit_die_total']==924.2886185238459
    assert joined['known_call_costs']['generic_cfg_work_cycles_per_rank']==31023
    assert not joined['build_admitted'] and not joined['schedule_costs_complete']
    with pytest.raises(ValueError,match='endpoint profiles'):J.price(joined,{}, {}, {})

def test_runtime_actual_VM_path_retained(joined):
    a=joined['templates']['L0.I66']['authoritative_native_address_binding']
    assert a['selector_VM_element_address']==366688
    assert a['selector_slot']==0
    assert a['address_patches']['qe_istride']=={'old':1,'new':4096}
    assert a['consumer_X_FP32_VM_elements']==[46464,51584]
    assert not a['actual_stage_dispatch_implemented']

@pytest.mark.parametrize('fault',['missing_node','class','semantic','patch','word','VM','EID','phase','physical','fault'])
def test_join_identity_coverage_optimism_refused(inputs,fault):
    # Copy only the changed sequence/record; immutable receipts are otherwise shared.
    x=dict(inputs)
    if fault=='missing_node':x['node_bindings.jsonl.gz']=inputs['node_bindings.jsonl.gz'][1:]
    elif fault in ('class','semantic','patch','VM','EID','phase'):
        rows=list(inputs['node_bindings.jsonl.gz'])
        idx=next(i for i,b in enumerate(rows) if b.get('selector_slot') is not None)
        b=copy.deepcopy(rows[idx]);rows[idx]=b;x['node_bindings.jsonl.gz']=rows
        if fault=='class':b['classification']='NOT_WEIGHT_PHASE'
        elif fault=='semantic':b['source_node_semantic_sha256']='wrong'
        elif fault=='patch':b['address_patches']['qe_istride']['new']=1
        elif fault=='VM':b['selector_VM_element_address']+=1
        elif fault=='EID':b['phase_choices'].pop()
        else:b['phase_choices'][0]['phase']+=1
    elif fault=='word':
        rows=list(inputs['patched_weight_words.jsonl.gz']);rows[0]=dict(rows[0],word_hex='0');x['patched_weight_words.jsonl.gz']=rows
    elif fault=='physical':
        rows=list(inputs['physical_address_boundaries.jsonl.gz']);rows[0]=dict(rows[0],stage=57);x['physical_address_boundaries.jsonl.gz']=rows
    else:
        x['model.json']=dict(inputs['model.json'],native_admission_failures=inputs['model.json']['native_admission_failures'][:-1])
    with pytest.raises(ValueError):J.join(x)

@pytest.mark.parametrize('key',['entry_refusal_before_GO_receipts','generation_lease_and_fault_drain_receipts','code_scale_ECC_delivery_receipts','root_and_consumer_visibility_receipts','actual_selected_EID_VM_read_receipts'])
def test_native_calendar_requires_each_causal_endpoint_gate(key,monkeypatch):
    j={'events':[{'id':'x.R0','template':'x'}],'templates':{'x':{'kind':'field_adapter','authoritative_native_address_binding':{'selector_slot':0,'selector_VM_element_address':366688}}},
       'descriptor_address_and_native_admission':{'model':{'native_admission_failures':[]}}}
    b={k:['synthetic-schema-only'] for k in ('entry_refusal_before_GO_receipts','generation_lease_and_fault_drain_receipts','code_scale_ECC_delivery_receipts','root_and_consumer_visibility_receipts','actual_selected_EID_VM_read_receipts')}
    b['selector_VM_element_address']=366688;b[key]=[]
    def forbidden(*args):raise AssertionError('unbound endpoint reached calendar')
    monkeypatch.setattr(J.C,'price',forbidden)
    with pytest.raises(ValueError):J.price(j,{'x.R0':b},{},{})
