import ast,hashlib,io,json,struct,sys,types
from pathlib import Path
import numpy as np
import pytest
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stream',ROOT/'tools/ds_checkpoint_streamed_state.py');stream=importlib.util.module_from_spec(s);s.loader.exec_module(stream)
SOURCE=ROOT/'results/uarch/ds_checkpoint_streamed_state_20261003/inputs/V3_source.py'

def pinned_leaf_module():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==stream.V3_SHA256
    wanted={'canonical','SectorBacking','Writer','deep_metadata_bytes'}
    tree=ast.parse(raw)
    kept=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in wanted]
    m=types.SimpleNamespace(__file__=str(SOURCE),np=np)
    env={'json':json,'np':np,'sys':sys,'os':__import__('os'),'SECTOR_RECORD':struct.Struct('<HQI32s')}
    exec(compile(ast.Module(body=kept,type_ignores=[]),'<PINNED_LEAF_WRITER_ONLY>','exec'),env)
    for k in wanted:setattr(m,k,env[k])
    return m


def writer(m,root):
    root.mkdir();return m.Writer(root)


def compare(m,value,tmp):
    a=writer(m,tmp/'legacy');b=writer(m,tmp/'streamed')
    encoded=m.canonical(a.tree(value));sink=io.BytesIO()
    stats=stream.stream_typed_state(m,value,b,sink,enabled=True)
    a.close();b.close()
    assert sink.getvalue()==encoded
    assert (tmp/'legacy/payload.bin').read_bytes()==(tmp/'streamed/payload.bin').read_bytes()
    assert stats['metadata_bytes']==len(encoded) and not stats['full_encoded_container_tree_created']
    return stats


def test_exact_nested_actual_types_and_aliases(tmp_path):
    m=pinned_leaf_module();array=np.arange(24,dtype='<u4').reshape(4,6);array.flags.writeable=False
    value={'provider':{('v',95):array,'alias':array,'str':'α\n','int':2**64-1,'float':-0.0,'scalar':np.int64(3),'bytes':b'\x00\xff','mutable':bytearray(b'actual')},'retired':{0,1},'dtype':np.dtype('<f4'),'extra':(None,True,[False])}
    compare(m,value,tmp_path)


def test_original_strided_array_copy_and_flags_preserved(tmp_path):
    m=pinned_leaf_module();compare(m,{'a':np.arange(128,dtype=np.float32)[::3]},tmp_path)


def test_sector_owner_address_mask_and_payload_parity(tmp_path):
    m=pinned_leaf_module();port=types.SimpleNamespace(backing={('DeepSeek',0,4):[None if i%3 else i for i in range(32)],('DeepSeek',0,5):list(range(32))},extents={('DeepSeek',0):[{'base':128,'bytes':64}]})
    compare(m,{'ports':{'rf':{0:m.SectorBacking(port)}}},tmp_path)


def test_empty_and_nonfinite_legacy_encoding_exact(tmp_path):
    compare(pinned_leaf_module(),{'a':{},'b':[],'c':set(),'d':(float('nan'),float('inf'),float('-inf'))},tmp_path)


def test_metadata_container_count_scales_but_live_frames_do_not(tmp_path):
    m=pinned_leaf_module();value={'retired':list(range(10000))}
    stats=compare(m,value,tmp_path)
    assert stats['leaves']==10001 and stats['max_live_container_frames']==2
    assert stats['max_leaf_metadata_bytes']<10 and stats['metadata_bytes']>40000


def test_defaultoff_no_write(tmp_path):
    m=pinned_leaf_module();w=writer(m,tmp_path/'payload');sink=io.BytesIO()
    with pytest.raises(ValueError,match='default off'):stream.stream_typed_state(m,{},w,sink)
    assert w.bytes==0 and not sink.getvalue();w.close()

@pytest.mark.parametrize('value',[np.array([object()],dtype=object),object()])
def test_reject_unknown_or_object_dtype(tmp_path,value):
    m=pinned_leaf_module();w=writer(m,tmp_path/'payload')
    with pytest.raises(ValueError):stream.stream_typed_state(m,value,w,io.BytesIO(),enabled=True)
    w.close()


def test_cycle_refuses_and_partial_evidence_retained(tmp_path):
    m=pinned_leaf_module();w=writer(m,tmp_path/'payload');v=[];v.append(v);sink=io.BytesIO()
    with pytest.raises(ValueError,match='cyclic'):stream.stream_typed_state(m,v,w,sink,enabled=True)
    assert sink.getvalue();w.close();assert (tmp_path/'payload/payload.bin').exists()


def test_source_tamper_refuses(tmp_path):
    m=pinned_leaf_module();p=tmp_path/'bad.py';p.write_bytes(SOURCE.read_bytes()+b'\n');m.__file__=str(p)
    w=writer(m,tmp_path/'payload')
    with pytest.raises(ValueError,match='exact V3'):stream.stream_typed_state(m,{},w,io.BytesIO(),enabled=True)
    w.close()


def test_short_metadata_write_refuses(tmp_path):
    m=pinned_leaf_module();w=writer(m,tmp_path/'payload')
    class Short:
        def write(self,data):return 0
    with pytest.raises(ValueError,match='short'):stream.stream_typed_state(m,{},w,Short(),enabled=True)
    w.close()


def test_whole_closure_and_payload_byteidentity_without_producer_stub(tmp_path):
    m=pinned_leaf_module();state={'provider':{'actual':np.arange(256,dtype=np.float32)},'retired':{0,1}}
    a=writer(m,tmp_path/'legacy');b=writer(m,tmp_path/'streamed')
    tree=a.tree(state)
    old={'schema':'DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3','identity':{'full':2213},'state':tree,'payload_sha256':'a'*64,'payload_bytes':a.bytes}
    new=dict(old,state=stream._TypedSnapshot(state));sink=io.BytesIO()
    stream._ordinary_json(m,new,sink,b)
    a.close();b.close()
    assert sink.getvalue()==m.canonical(old)
    assert (tmp_path/'legacy/payload.bin').read_bytes()==(tmp_path/'streamed/payload.bin').read_bytes()


def test_ordinary_metadata_unknown_key_rejected():
    with pytest.raises(ValueError,match='string keys'):stream._ordinary_json(pinned_leaf_module(),{1:'bad'},io.BytesIO(),None)


def test_actual_save_defaultoff_before_any_provider_or_write(tmp_path):
    with pytest.raises(ValueError,match='default off'):stream.save_streamed(pinned_leaf_module(),None,None,tmp_path/'forbidden')
    assert not (tmp_path/'forbidden').exists()


def test_source_save_preserves_validation_and_durability_calls():
    code=ast.parse((ROOT/'tools/ds_checkpoint_streamed_state.py').read_text())
    function=next(n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='save_streamed')
    calls=[ast.unparse(n.func) for n in ast.walk(function) if isinstance(n,ast.Call)]
    for required in ('base.quiescent','base.inventory','base.validate_backing','base.snapshot_state','base.identity','base.scope_role_proof','base.journal_inventory','base.checkpoint_shards','os.fsync'):
        assert required in calls
    assert calls.count('base.quiescent')==2
    assert 'base.read_tree' not in calls # no restore/oracle shortcut
    assert 'base.canonical' in calls # small seals/scalars; no whole closure canonical
    assert 'base.canonical(closure)' not in ast.unparse(function)


def test_profile_defaultoff_has_no_provider_side_effect():
    with pytest.raises(ValueError,match='default off'):stream.profile_streamed_state(pinned_leaf_module(),None,None)
