import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_program import compile_program,coverage

def small(layers=2):return dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,intermediate_size=16,vocab_size=16,num_hidden_layers=layers,rms_norm_eps=1e-6,rope_theta=1000000)

def test_shipped_36_layers_head_and_all_semantic_lowerings():
    p=compile_program();c=coverage(p)
    assert c['layers']==36 and c['all_semantics_lowered']
    assert len(p['weight_descriptors'])==36*4*2+2
    assert len([x for x in p['instructions'] if x['opcode']=='KV_WRITE'])==72
    assert p['instructions'][-1]['opcode']=='ARGMAX_REDUCE'
    assert p['weight_descriptors']['L0.qkv.d0']['split']==256
    assert p['weight_descriptors']['L0.gu.d0']['split']==64
    assert p['weight_descriptors']['head.d1']['rows']==75968
    assert p['weight_descriptors']['head.d1']['row_tiles_256_per_SM']==10
    assert p['modeled_token_cycles'] is None and c['token_rate'] is None

def test_every_read_has_producer_dependency_and_no_dynamic_oracle_input():
    p=compile_program();producer={};available=set(p['input_registers'])
    assert available=={'token','position'}
    for op in p['instructions']:
        assert set(op['inputs'])<=available
        for name in op['inputs']:
            if name in producer:assert producer[name] in op['dependencies']
        assert op['GPU_instructions'] and op['provider_key']
        assert all(x is None for x in op['cost_cycles'].values())
        for output in op['outputs']:assert output not in available;available.add(output);producer[output]=op['id']

def test_address_allocations_are_disjoint_full_capacity_and_still_unqualified():
    p=compile_program()
    for rank in p['memory_allocation']:
        assert rank['capacity_fit'] and not rank['residence_qualified']
        previous=0
        for e in rank['extents']:
            assert e['base']>=previous and e['base']%128==0;previous=e['base']+e['bytes']
        assert len([e for e in rank['extents'] if e['role'].startswith('persistent_')])==72

def test_invalid_TP_or_context_rejected():
    with pytest.raises(ValueError):compile_program(tp=4)
    with pytest.raises(ValueError):compile_program(context=17)
