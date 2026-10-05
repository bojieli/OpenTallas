import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_native_microop_adapter as A
import h3_deepseek_complete_native as DS
from qwen_hbm_complete_program import compile_program


def small():return dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,intermediate_size=16,vocab_size=16,num_hidden_layers=2,rms_norm_eps=1e-6,rope_theta=1000000)


def test_both_actual_microop_vms_same_explicit_arithmetic_and_finite_calendar():
    b=DS.Builder();x=b.load('x',(4,));v=b.op('FMUL',b.op('FADD',x,b.const(.25)),b.const(.5));b.output('out',v);p=b.finish()
    x=np.asarray([0,2**24,-1,.375],np.float32);got,r=A.execute_ds(p,{'x':x},(0,'v0',0,0,0))
    native=A.QW.compile_native(compile_program(small(),context=32,groups=16));m=A.QW.Machine(native)
    env={'x':x};m.nodes([A.QW.ins('FADD','v','x','f32(.25)'),A.QW.ins('FMUL','out','v','f32(.5)')],env,{'writes':[]})
    assert np.array_equal(got['out'].view(np.uint32),env['out'].view(np.uint32))
    for counts,traffic in [(r['opcode_evaluations'],r['provider']['events']['accepted']),(dict(m.primitive_counts),0)]:
        costs={k:3 for k in counts};costs.update(provider=5,frame=2);cal=A.finite_calendar(counts,costs,traffic)
        assert cal['end_cycle']>=sum(counts.values())*3;assert not cal['hardware_qualified']
        for event in cal['events']:assert event['end']>event['start']


def test_actual_qwen_recipe_program_with_provider_leases_two_tokens():
    native=A.QW.compile_native(compile_program(small(),context=32,groups=16));m=None
    for token,pos in [(3,0),(5,1)]:
        receipt,m=A.execute_qwen(native,token,pos,m)
        assert receipt['status']=='SOFTWARE_NATIVE_PROGRAM_COMPLETED';assert receipt['instructions_retired']==len(native['operations'])
        assert not receipt['hardware_or_timing_credit'];assert not m.live;assert not m.address_words
    assert m.primitive_counts['CONSUMER_DONE']>0
    cal=A.finite_calendar(dict(m.primitive_counts),{k:1 for k in m.primitive_counts})
    assert cal['end_cycle']==sum(m.primitive_counts.values())

@pytest.mark.parametrize('cost',[None,0,-1,1.0])
def test_common_calendar_never_gives_missing_or_invalid_cost_zero(cost):
    with pytest.raises(ValueError):A.finite_calendar({'FADD':1},{'FADD':cost})


def test_common_entrypoint_qwen_each_pc_numerical_vs_source_oracle():
    import copy
    from qwen_hbm_complete_executor import SoftwareGPUProvider,execute
    native=A.QW.compile_native(compile_program(small(),context=32,groups=16));oracle=SoftwareGPUProvider(native['source_program']);m=None;covered=set()
    for token,pos in [(3,0),(5,1)]:
        actual={};receipt,m=A.execute_qwen(native,token,pos,m,observer=lambda op,out:actual.update({op['id']:copy.deepcopy(out)}))
        def check(op,expected):
            covered.add(op['opcode'])
            if op['opcode'] in ('KV_WRITE','KV_FENCE'):return
            for got,want in zip(actual[op['id']],expected):
                if isinstance(want,dict):assert got==want
                elif isinstance(want,tuple):assert got==want
                elif np.asarray(want).dtype.kind=='f':assert np.array_equal(np.asarray(got,np.float32).view(np.uint32),np.asarray(want,np.float32).view(np.uint32))
                else:assert np.array_equal(got,want)
        execute(native['source_program'],oracle,token,pos,observer=check)
    assert len(covered)==21


def bound_op_fixture():
    b=DS.Builder();x=b.load('x',(4,));b.output('out',b.op('FMUL',x,b.const(.5)));p=b.finish()
    binding={'kind':'versioned_operand','version':'x_v4','native_address_view':'source_owned4'}
    op={'pc':0,'rank_bindings':[{'rank':0,'template':'t','buffer_programs':[]}],'provider_bindings':{'t':{'x':binding}},'writes':[{'version':'y_v5','home_indices':[7],'native_result_binding':{'result':'out','native_store_view':'source_owned4'}}]}
    program={'instructions':[op],'templates':{'t':p}}
    view={'kind':'versioned_operand','field':'x','rank':0,'generation':9,'version':'x_v4','view_contract':'source_owned4','provenance_certified':True,'data':np.arange(4,dtype=np.float32)}
    return program,view


def test_source_pc_provider_version_home_join_is_executable():
    native,view=bound_op_fixture();stores,r=A.execute_bound_ds_operation(native,0,0,{'x':view},9,31)
    assert len(stores)==1;assert stores[0]['version']=='y_v5';assert stores[0]['home_indices']==[7]
    assert np.array_equal(stores[0]['data'],np.arange(4,dtype=np.float32)*.5)
    assert not stores[0]['causal_visibility_certified'];assert r['source_PC']==0

@pytest.mark.parametrize('field,value',[('version','x_v3'),('generation',8),('rank',1),('field','weight'),('provenance_certified',False),('view_contract','wrong_partition')])
def test_source_pc_join_rejects_wrong_typed_valid_provider_identity(field,value):
    native,view=bound_op_fixture();view[field]=value
    with pytest.raises(ValueError):A.execute_bound_ds_operation(native,0,0,{'x':view},9,31)


def test_multibuffer_collective_preserves_independent_read_write_versions():
    p=DS.recipe('all_gather',{'n':4,'ranks':2},{})
    binding={'parts':{'kind':'versioned_operand','version':'a_v0','native_address_view':'owned_masks','additional_versions':['a_v0','b_v0']},'ownership_mask':{'kind':'explicit_auxiliary_provider','identity_from_versions':['a_v0','b_v0']}}
    op={'pc':0,'rank_bindings':[{'rank':0,'template':'t','buffer_programs':[{'template':'t','read_version':'a_v0','write_version':'a_v1'},{'template':'t','read_version':'b_v0','write_version':'b_v1'}]}],'provider_bindings':{'t':binding},'writes':[{'version':v,'home_indices':[i],'native_result_binding':{'result':'out'}} for i,v in enumerate(['a_v1','b_v1'])]}
    native={'instructions':[op],'templates':{'t':p}};views={}
    for out,src,offset in [('a_v1','a_v0',0),('b_v1','b_v0',10)]:
        owners=np.asarray([[1,1,0,0],[0,0,1,1]],np.uint32);data=np.asarray([[1,2,0,0],[0,0,3,4]],np.float32);data=np.where(owners,data+offset,0).astype(np.float32)
        views[out]={'parts':{'kind':'versioned_operand','field':'parts','rank':0,'generation':3,'version':src,'view_contract':'owned_masks','provenance_certified':True,'data':data},'ownership_mask':{'kind':'explicit_auxiliary_provider','field':'ownership_mask','rank':0,'generation':3,'source_binding':{'kind':'explicit_auxiliary_provider','identity_from_versions':[src]},'provenance_certified':True,'data':owners}}
    stores,r=A.execute_bound_ds_operation(native,0,0,views,3,0)
    assert [s['version'] for s in stores]==['a_v1','b_v1'];assert r['source_result_stores']==2
    assert np.array_equal(stores[0]['data'],np.arange(1,5,dtype=np.float32))
    assert np.array_equal(stores[1]['data'],np.arange(11,15,dtype=np.float32))
    views['b_v1']['parts']['version']='a_v0'
    with pytest.raises(ValueError,match='operand version'):A.execute_bound_ds_operation(native,0,0,views,3,0)

@pytest.mark.parametrize('family',sorted(DS.FAMILIES))
def test_all_families_actual_forward_dispatch_is_not_scalar_recompute(family):
    import importlib.util
    spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
    p=DS.recipe(family,F.TOY,F.ATTR);p.update(family=family,source_attributes=F.ATTR);m=F.fixture(p)
    expected=DS.Machine(p,m,DS.primitive_div).run();got,r=A.execute_ds(p,m,(0,'native_v0',0,0,2))
    assert r['status'] in A.PASS_STATUSES;assert r.get('execution_path')!='REFERENCE_ONLY_SCALAR_FALLBACK'
    assert r['recomputed_dependency_scalars']==0
    for key in expected:assert np.array_equal(got[key].reshape(-1).view(np.uint8),expected[key].reshape(-1).view(np.uint8))
