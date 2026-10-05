import copy
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lower',ROOT/'tools/h3_versioned_lowering.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)

def fixture():
    b=L.Builder('Qwen');b.value('x',[128,128],external=True)
    b.op('RESIDUAL',['x'],[('y',[128,128],32,None)],0,{'path':'fixture'})
    L.allocate(b);return b

def test_complete_macro_graph_lowering():
    q,_=L.qwen();d,_=L.ds()
    assert len(q.operations)==1737 and len(d.operations)==2213
    assert len(d.values)>3165 # append mutations are now separate versions
    assert all(o['timeline']['duration_term'] for o in q.operations+d.operations)
    assert all(v['birth_pc']<o['pc'] for b in (q,d) for o in b.operations for v in [b.byid[i] for i in o['reads']])

def test_gather_uses_global_extent_not_dense_rank_replication():
    b,_=L.ds();g=next(o for o in b.operations if o['source']['op'].get('tag')=='expert_intermediate_gather')
    v=b.byid[g['writes'][0]];assert v['elements_per_rank']==[16128]*96

def test_append_readers_consume_produced_generation():
    b,_=L.ds();o=next(o for o in b.operations if o['opcode']=='index_scores')
    key=next(b.byid[v] for v in o['reads'] if b.byid[v]['name']=='index_keys.L2')
    assert key['birth_pc']>=0 and key['producer_extent']['append_global_group']==524287

def test_RF_alias_control():
    b=fixture();b.byid[b.operations[0]['writes'][0]]['homes'][0]['vector_slots']=b.values[0]['homes'][0]['vector_slots']
    with pytest.raises(ValueError,match='live RF alias'):L.verify(b)

def test_workspace_not_borrowed():
    b=fixture();b.values[0]['homes'][0]['vector_slots']=[0]
    with pytest.raises(ValueError,match='RF range'):L.verify(b)

def test_early_retirement_control():
    b=fixture();b.values[0]['retire_pc']=-1
    with pytest.raises(ValueError,match='early retirement'):L.verify(b)

def test_missing_duration_control():
    b=fixture();b.operations[0]['timeline']['duration_term']='0'
    with pytest.raises(ValueError,match='missing duration'):L.verify(b)

def test_tree_and_chunk_order_controls():
    for t,n in [('Qwen',128),('Qwen',4096),('DeepSeek',5120)]:
        k=L.norm_kernel(n,t);assert L.verify_tree(k)
        assert k['shared_tree_materialized_bytes']<=8192
        bad=copy.deepcopy(k);bad['tree'][0]['src'].reverse()
        with pytest.raises(ValueError,match='golden tree'):L.verify_tree(bad)
        bad=copy.deepcopy(k);bad['ordered_chunk_loop']['body'][1]['src'][0]='p0'
        with pytest.raises(ValueError,match='golden chunk'):L.verify_tree(bad)

def test_spill_alias_control():
    b=L.Builder('Qwen');b.value('x',[65536,65536],external=True)
    b.op('copy',['x'],[('y',[65536,65536],32,None)],0,{'path':'fixture'});L.allocate(b)
    assert all(v['homes'][0]['class']=='spill_arena' for v in b.values)
    b.values[1]['homes'][0]['byte_offset']=b.values[0]['homes'][0]['byte_offset']
    with pytest.raises(ValueError,match='live spill alias'):L.verify(b)

def test_native_instruction_path_has_no_oracle_latency():
    b=fixture();L.native(b);o=b.operations[0];path=o['native_lowering']
    assert path['measured_H1_alias_accept_cadence_cycles']==19
    assert path['qualified_cycles'] is None and path['RF_read_bits']==8192


def test_actual_H1_calibration_no_clock_or_token_transfer():
    c=L.calibration();assert c['cases'][3]['accepts']==512
    assert c['cases'][4]['actual_last_ACK_hold_cycles']==242
    assert c['alias_driver_cadence_cycles']==19
    assert not c['source_endpoint_hardware_clock_or_product_ns_credit'] and not c['full_token_credit']


def test_calibration_JSON_key_normalization():
    import json
    c=L.calibration();r=json.loads(json.dumps(c))
    assert r['cases']['3']['RF_fence_to_next_issue_cycles']==c['cases'][3]['RF_fence_to_next_issue_cycles']==9775
