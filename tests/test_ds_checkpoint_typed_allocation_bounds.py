import ast,hashlib,importlib.util,json,os,struct,sys,types
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounds',ROOT/'tools/ds_checkpoint_typed_allocation_bounds.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
SOURCE=ROOT/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003/inputs/V3_source.py'


def base():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==m.V3_SHA
    tree=ast.parse(raw);wanted={'canonical','SectorBacking','Writer','read_tree'}
    env={'np':np,'sys':sys,'json':json,'os':os,'SECTOR_RECORD':struct.Struct('<HQI32s')}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in wanted],type_ignores=[]),'<EXACT_V3_TYPED_SOURCE>', 'exec'),env)
    jtree=ast.parse((ROOT/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003/inputs/journal_source.py').read_bytes())
    c=next(n for n in jtree.body if isinstance(n,ast.ClassDef) and n.name=='CompactSectors');js={};exec(compile(ast.Module(body=[c],type_ignores=[]),'<EXACT_COMPACT_SECTORS>','exec'),js)
    out=types.SimpleNamespace(__file__=str(SOURCE),np=np,SECTOR_RECORD=env['SECTOR_RECORD'],CompactSectors=js['CompactSectors'])
    for name in wanted:setattr(out,name,env[name])
    return out


def heap(value):
    # No sharing credit: even repeated key/scalar references are charged again.
    n=sys.getsizeof(value)
    if isinstance(value,dict):n+=sum(heap(k)+heap(v) for k,v in value.items())
    elif isinstance(value,(list,tuple,set)):n+=sum(heap(v) for v in value)
    return n


def encoded(b,value):
    class Sink:
        def write(self,data):return len(data)
    w=b.Writer.__new__(b.Writer);w.f=Sink();w.bytes=w.arrays=w.array_temporary_bytes=0
    return w.tree(value),w.bytes


@pytest.mark.parametrize('value',[{},[],(),set(),{'a':[0,1,True,None,-0.0,'α'],(1,'k'):(4,)},list(range(1000)),{'a':np.arange(128,dtype='<u4')[::3],'bytes':b'actual','dtype':np.dtype('<i8')}])
def test_exact_virtual_metadata_node_and_byte_counts(value):
    b=base();tree,payload=encoded(b,value);p=m.profile_typed_value(b,value,enabled=True)
    J=m.JsonCounts(m.layout());J.walk(tree)
    assert p['typed_JSON']==J.result()
    assert p['typed_JSON']['unshared_python_object_heap_upper_bytes']>=heap(tree)
    assert p['counts']['metadata_bytes']==len(b.canonical(tree))
    assert p['counts']['payload_bytes']==payload


def test_array_aliases_do_not_discount_cold_copies():
    a=np.arange(128,dtype=np.float32);p=m.profile_typed_value(base(),[a,a,a[::2]],enabled=True)
    assert p['array_object_aliases']==1 and p['counts']['array_copy_bytes']==a.nbytes*2+a[::2].nbytes
    assert p['counts']['max_contiguity_copy_bytes']==a[::2].nbytes
    assert p['source_array_alias_discount_for_restore_bytes']==0
    assert len(p['arrays'])==3


def test_all_saved_port_table_copies_stay_alive():
    b=base();ports=[]
    for rank,n in [(0,8),(1,11),(2,5)]:
        backing=b.CompactSectors()
        for sector in range(n):backing['DeepSeek',rank,sector]=[None if j%3 else j for j in range(32)]
        ports.append(b.SectorBacking(types.SimpleNamespace(backing=backing,extents={('DeepSeek',rank):[{'base':0,'bytes':n*32}]})))
    p=m.profile_typed_value(b,ports,enabled=True);c=p['counts']
    assert c['sector_backing_records']==24 and c['sector_tables']==3
    assert c['all_restore_table_copy_upper']>c['largest_restore_table_copy_upper']
    assert c['sector_partial_records']==24


def test_full_sectors_compact_and_masks_counted():
    b=base();v=b.SectorBacking(types.SimpleNamespace(backing={('DeepSeek',0,0):bytearray(range(32))},extents={('DeepSeek',0):[{'base':0,'bytes':32}]}))
    p=m.profile_typed_value(b,v,enabled=True)
    assert p['counts']['sector_full_records']==1 and p['counts']['payload_bytes']==46


def test_source_frame_heap_and_file_buffers_priced_without_graph_multiplier():
    p=m.profile_typed_value(base(),{'a':np.arange(16,dtype=np.float32)},enabled=True)
    v=m.phase_object_bounds(p,closure_heap_upper=1000,state_file_bytes=200,observation_heap_upper=300,observation_file_bytes=50,identity_and_journal_workspace_upper=400,constructor_heap_upper=5000)
    assert v['cold_restore']['decoded_state_and_all_port_copies_upper']>=64
    assert v['cold_restore']['logical_sum_upper']>=5000+1000+5*200
    assert v['allocator_pages_upper'] is None and not v['physical_admission']


@pytest.mark.parametrize('n',[0,1,2,3,7,8,9,31,32,99,1000,10000])
def test_builtin_container_capacity_envelopes(n):
    L=m.layout();a=[]
    for i in range(n):a.append(i)
    assert m.list_bytes(n,L)>=sys.getsizeof(a)
    assert m.dict_bytes(n,L)>=sys.getsizeof({i:i for i in range(n)})


def test_ordinary_metadata_count_matches_canonical_without_dump():
    b=base();v={'identity':{'generation':1,'name':'α'},'journal':[{'stamp':[1,2,3],'sha':'a'*64}]}
    p=m.profile_json_metadata(b,v,enabled=True)
    assert p['encoded_bytes']==len(b.canonical(v)) and p['unshared_python_object_heap_upper_bytes']>=heap(json.loads(b.canonical(v)))
    assert not p['full_json_text_or_bytes_created']


@pytest.mark.parametrize('value',[np.array([object()],dtype=object),object()])
def test_unknown_source_kind_rejected(value):
    with pytest.raises(ValueError):m.profile_typed_value(base(),value,enabled=True)


def test_defaultoff_and_cycle_failclosed():
    with pytest.raises(ValueError,match='default off'):m.profile_typed_value(base(),{})
    a=[];a.append(a)
    with pytest.raises(ValueError,match='cyclic'):m.profile_typed_value(base(),a,enabled=True)


def test_unknown_phase_cost_is_not_zero():
    p=m.profile_typed_value(base(),{},enabled=True)
    with pytest.raises(ValueError,match='complete counted'):m.phase_object_bounds(p,closure_heap_upper=None,state_file_bytes=0,observation_heap_upper=0,observation_file_bytes=0,identity_and_journal_workspace_upper=0,constructor_heap_upper=0)


def test_actual_source_compact_copy_preserves_keys_values_and_all_tables():
    b=base();saved=[];copies=[]
    for rank in range(3):
        old=b.CompactSectors()
        for sector in range(17):old['DeepSeek',rank,sector]=[None]*32
        saved.append(old);copies.append(b.CompactSectors(old))
    for old,new in zip(saved,copies):
        assert old is not new
        assert len(old)==len(new)==17
        for key in old:
            assert new[key] is old[key]
    assert sum(sys.getsizeof(x) for x in copies)>max(sys.getsizeof(x) for x in copies)


def test_r69_correction_exact_existing_bounds_no_runtime_grant():
    d=ROOT/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003'
    p=m.frozen_r69_restore_correction(d)
    assert p['restored_sector_upper']==738048 and p['restored_port_upper']==96
    assert p['all_table_entries_upper_bytes']==738048*352
    assert p['missing_copy_increment_upper_bytes']>257086720
    assert p['full_runtime_upper_bytes'] is None and not p['complete_source_phase_bounds']
    assert not p['physical_admission'] and not p['existing_guard_changed']
    assert p['full_native_PCs']==2213 and p['full_homes']==290730


def test_exact_v3_decode_arrays_partial_full_sectors_and_copy_heap(monkeypatch):
    import io
    b=base();mod=types.ModuleType('hbm_bound_event_journal_r30');mod.CompactSectors=b.CompactSectors
    monkeypatch.setitem(sys.modules,'hbm_bound_event_journal_r30',mod)
    port=types.SimpleNamespace(backing=b.CompactSectors(),extents={('DeepSeek',0):[{'base':0,'bytes':64}]})
    port.backing['DeepSeek',0,0]=list(range(32));port.backing['DeepSeek',0,1]=[None,5]*16
    value={'array':np.arange(32,dtype='<u4')[::2],'ports':[b.SectorBacking(port)],'bytes':b'produced'}
    w=b.Writer.__new__(b.Writer);w.f=io.BytesIO();w.bytes=w.arrays=w.array_temporary_bytes=0
    tree=w.tree(value);raw=w.f.getvalue();decoded=b.read_tree(tree,np.frombuffer(raw,dtype=np.uint8))
    assert np.array_equal(decoded['array'],value['array']) and decoded['bytes']==value['bytes']
    saved=decoded['ports'][0];new=b.CompactSectors(saved)
    assert new['DeepSeek',0,1] is saved['DeepSeek',0,1]
    assert new['DeepSeek',0,0] is saved['DeepSeek',0,0]
    p=m.profile_typed_value(b,value,enabled=True)
    costs=m.phase_object_bounds(p,closure_heap_upper=0,state_file_bytes=0,observation_heap_upper=0,observation_file_bytes=0,identity_and_journal_workspace_upper=0,constructor_heap_upper=0)
    assert costs['cold_restore']['decoded_state_and_all_port_copies_upper']>=heap(decoded)+sys.getsizeof(new)
    assert not costs['complete_source_phase_bounds']


def test_frozen_audit_replay_and_phase_incompleteness():
    d=ROOT/'results/uarch/ds_checkpoint_typed_allocation_bounds_20261003'
    assert m.audit_record(d)==json.loads((d/'model.json').read_bytes())
    a=m.audit_record(d)
    assert all(a['phases'][name]['required_counts'] for name in ('project','capture','atomic_verify','cold_restore','physical'))
    assert a['phases']['physical']['pagecache_release_credit_bytes']==0
    assert a['full_runtime_upper_bytes'] is None
