import copy,gzip,json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_checkpoint_payloads_r35 as P
import ds_hbm_payload_manifest_r35 as M
from ds_hbm_source_inputs_r34 import codecs,load
from h3_ds_checkpoint_provider_r30 import LockedCheckpoint
D=ROOT/'results/uarch/ds_hbm_checkpoint_payloads_r35_20261002'
D30=ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002'
D33=ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002'
@pytest.fixture(scope='module')
def ck():
    m=json.loads((D30/'checkpoint_input_manifest.json').read_bytes());return LockedCheckpoint(m['checkpoint_path'],m['checkpoint_revision'],m['checkpoint_index_sha256'])
@pytest.fixture(scope='module')
def native():return json.loads(gzip.decompress((D/'inputs/native_payload_projection.json.gz').read_bytes()))
@pytest.fixture(scope='module')
def eng(ck):
    c=json.loads((D33/'inputs/inference_config.json').read_bytes());ref,_,_,_=codecs();return P.engram_payloads(ck,c,ck.path/'tokenizer.json',ref['token_history'])
def machine():return load('r35_test_machine',D33/'inputs/native_machine_class.py.source').Machine

def test_actual_PC20_provider_and_native_descriptor_selection(ck,native,tmp_path):
    from h3_ds_checkpoint_provider_r34 import create_provider
    o=next(o for o in native['instructions'] if o['pc']==20);rb=o['rank_bindings'][0];key=rb['template'];table,ls=P.expert_descriptors(ck,0)
    assert len(ls)==1152
    ids=np.asarray([0,3,8,17,255,383],np.int64);path=tmp_path/'descriptors.npy';np.save(path,table,allow_pickle=False)
    b=o['provider_bindings'][key];r=dict(path=str(path),sha256=P.sha(path),shape=[384,3,4],dtype='I64',source_binding=b['expert_descriptor_table'],generation=1,checkpoint_revision=ck.path.name)
    m=json.loads((D30/'checkpoint_input_manifest.json').read_bytes());m.update(journal_root=str(tmp_path/'journal'),journal_capacity_bytes=16<<20,view_bindings={f'20/{key}/expert_descriptor_table':r})
    p=create_provider(m,native,{},[]);p.published[b['route_ids']['version'],0]=ids
    views=p.read_views(o,rb,1);actual=machine()(native['templates'][key],{k:v['data'] for k,v in views.items()},None).run()['descriptors']
    assert np.array_equal(actual,table[ids])
    for i in ids:
        for j in range(3):
            loc=ls[int(i)*3+j];assert actual[list(ids).index(i),j].tolist()==loc['descriptor']
            assert loc['code']['checkpoint_file_byte_base']==int(table[i,j,0])
    p.release_views(20,0,1,views)

@pytest.mark.parametrize('layer',[1,14])
def test_actual_engram_native_primitives_against_pinned_decoder(native,eng,layer):
    o=next(o for o in native['instructions'] if o['family']=='engram_fetch' and o['source_op']['layer']==layer);key=o['rank_bindings'][0]['template'];t=native['templates'][key];_,_,V,_=codecs();inputs=dict(eng[layer],E4M3_decode=V.E4M3.astype(np.float32))
    result=machine()(t,inputs,None).run();expected=V.decode_engram_rows(inputs['selected_codes'].astype(np.uint8),inputs['selected_exp'],np.arange(24)).reshape(-1)
    assert np.array_equal(result['row_ids'],inputs['selected_row_ids'])
    assert np.array_equal(result['eg_rows'].view(np.uint32),expected.view(np.uint32))
    assert np.all(np.isfinite(result['eg_rows']))
    wrong=copy.deepcopy(inputs);wrong['selected_row_ids'][0]+=1
    with pytest.raises((AssertionError,ValueError)):machine()(t,wrong,None).run()

def test_minimal_worker_manifest_is_refused_for_runtime_composition(tmp_path):
    minimal=json.loads((D30/'checkpoint_input_manifest.json').read_bytes())
    with pytest.raises(ValueError):M.compose(minimal,minimal,{},tmp_path/'journal')

@pytest.mark.parametrize('flag',['full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'])
def test_inherited_admission_flag_never_survives_composition(tmp_path,flag):
    base=json.loads((D30/'provider_manifest.json').read_bytes());base[flag]=True;patch=dict(base,native_program_sha256='derived',initial_versions=[],view_bindings={})
    out=M.compose(base,patch,{},tmp_path/'journal')
    assert all(out[k] is False for k in ('full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'))
    assert out['persistent_fragment_extent']==base['persistent_fragment_extent'] and out['journal_capacity_bytes']==base['journal_capacity_bytes']
    assert out['checkpoint_initial_embedding']['initializer_sha256']==base['checkpoint_initial_embedding']['initializer_sha256']
    assert out['provider_module_sha256']==M.sha(ROOT/'tools/h3_ds_checkpoint_provider_r34.py')

def test_streamed_entering_state_matches_exact_source_class_fixture(tmp_path):
    import types
    import ds_hbm_entering_state_r35 as E
    ref,G,V,init=codecs()
    module=load('r35_state_source',D/'inputs/source_state_class.py.source');module.V=V;module.LC=init
    class Model:
        L=3;window=128;hd=512;ihd=128;kv_src=[2];kv_of={2:2};ratio={2:2}
        def lw(self,layer,tensor):return np.ones(128 if 'indexer' in tensor else 512,np.float32)
    m=Model();source=module.State(m,16,20260930,[0,1,2]);windows=[]
    for layer,a in source.win.items():
        p=tmp_path/f'w{layer}.npy';np.save(p,a,allow_pickle=False);windows.append(dict(path=str(p),sha256=P.sha(p)))
    class Checkpoint:
        receipts=[]
        def tensor(self,name):return np.ones(128 if 'indexer' in name else 512,np.float32),'BF16'
    receipt=E.materialize(Checkpoint(),windows,tmp_path/'state',ctx=16,sources=(2,),expected=source.state_sha256)
    assert receipt['actual_state_sha256']==source.state_sha256
    for name,a in [('ckv',source.ckv[2][:-1]),('ik',source.ik[2][:-1])]:
        b=np.load(tmp_path/'state'/f'{name}_L2.npy',allow_pickle=False)
        assert np.array_equal(a.view(np.uint32),b.view(np.uint32))
    assert receipt['full_token_run'] is False

def test_full_entering_state_inventory_does_not_relabel_scratch():
    import ds_hbm_entering_state_r35 as E
    p=E.preflight();assert p['historical_payload_bytes']==6710876160
    assert p['window_payload_bytes']==10403840 and p['source_chunk_rows']==65536

def test_actual_source_open_group_identity_and_refusal(tmp_path):
    import ds_hbm_open_state_bindings_r35 as O
    path=tmp_path/'open.npy';a=np.arange(1024,dtype=np.float32).reshape(1,2,512);np.save(path,a,allow_pickle=False)
    required=dict(kind='explicit_auxiliary_provider',layer=2,position=1048575)
    n=dict(instructions=[dict(pc=121,provider_bindings={'t':{'open_group':required}})],templates={'t':{'providers':{'open_group':dict(shape=[1,2,512],dtype='F32')}}})
    records=[dict(layer=2,kind=3,path=str(path),file_sha256=P.sha(path),logical_positions=[1048574])]
    b=O.bindings(n,records);assert b['121/t/open_group']['source_binding']==required
    assert np.array_equal(np.load(b['121/t/open_group']['path']),a)
    records[0]['logical_positions']=[1048573]
    with pytest.raises(ValueError):O.bindings(n,records)
