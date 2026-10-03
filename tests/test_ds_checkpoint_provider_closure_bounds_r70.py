import ast,hashlib,importlib.util,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_checkpoint_provider_closure_bounds_r70 as m

@pytest.fixture(scope='module')
def graphs():return m.source_schemas()

@pytest.fixture(scope='module')
def record():return m.read(m.D/'model.json')


def source_literal(name):
    tree=ast.parse((m.D/'inputs/ds_producer_checkpoint_resume_v3.py.source').read_bytes())
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    return ast.literal_eval(node.value)


def test_every_original_typed_provider_and_port_field_has_a_bound(graphs):
    g,e=graphs;s=g['snapshot']
    assert set(s['provider'])==set(source_literal('STATE'))
    assert set(s['ports']['rf'][0])==set(source_literal('PORT_STATE'))|{'compact_lifecycle'}
    assert e['publication_upper']==576 and e['RF_ports']==96
    assert e['RF_generations_per_port']==4
    assert len(s['ports']['rf'])==96 and s['ports']['state']=={}
    assert set(s)=={'provider','ports','immutable_published_keys','source_image_keys','retired','extra'}


def test_complete_future_keys_positive_source_input_counts_and_payloads_separate(graphs,record):
    g,e=graphs
    assert (record['full_native_PCs'],record['full_future_homes'])==(2213,290730)
    assert e['source_image_key_upper']==3840
    assert e['immutable_input_unique_paths']==119
    assert e['auxiliary_binding_records']==383 and e['history_input_records']==8
    assert e['published_array_occurrences_upper']==768
    assert e['published_array_copy_bytes_upper']==19671552
    assert record['raw_sector_and_array_payload_added_to_node_heap'] is False
    assert set(g['snapshot']['immutable_published_keys'])==set(g['snapshot']['source_image_keys'])


def test_source_witness_all576_keys_exact_r70(graphs):
    g,e=graphs;seen=g['actual_observations']['seen'];b=m.read(m.D/'inputs/witness_r70.json')
    raw=json.dumps(seen,sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(raw).hexdigest()==b['combined_seen_key_SHA256']
    assert len(raw)==b['combined_seen_key_canonical_bytes']
    assert sum(x[0]==0 for x in seen)==384 and sum(x[0]==1 for x in seen)==192


def test_node_header_envelope_exceeds_actual_metadata_heap(graphs):
    g,e=graphs
    def heap(x):
        n=sys.getsizeof(x)
        if type(x)is dict:n+=sum(heap(k)+heap(v) for k,v in x.items())
        elif type(x)in (list,tuple):n+=sum(heap(v) for v in x)
        return n
    for name in ('provenance','scope_role','journal_inventory','identity'):
        assert m.count(g[name])['unshared_python_object_heap_upper_bytes']>=heap(g[name])


def test_ordinary_and_typed_snapshot_node_profiles_replay(graphs,record):
    g,e=graphs
    for name,value in g.items():
        got=m.count(m.typed(value) if name=='snapshot' else value)
        if name in ('snapshot','closure'):got['nullable_integer_slots_upper']=192
        assert got==record['node_profiles'][name]
    assert not record['physical_admission'] and record['actual_constructor_runs']==0
    assert record['actual_payload_reads']==0


def test_guard_accepts_only_allocation_not_identity(graphs,record):
    g,e=graphs;r=m.verify_enrolled_metadata('provenance',g['provenance'],record)
    assert r['source_object_bounds_fit'] and not r['identity_accepted'] and not r['physical_admission']


@pytest.mark.parametrize('value',[{'unpriced_field':1},{'generation':2**4096},{'source_sha256':{'x':'x'*100000}}])
def test_unknown_or_enlarged_control_metadata_refused(value,record):
    with pytest.raises(ValueError):m.verify_enrolled_metadata('identity',value,record)


def test_untyped_object_refused():
    with pytest.raises(ValueError,match='unpriced shadow'):m.typed(object())


def test_original_writer_primitive_schema_matches_shadow():
    # Execute only exact original leaf/container writer, no provider constructor
    # or arithmetic callback. Small actual bytes here are regression fixtures.
    import io,numpy as np,types
    source=m.D/'inputs/ds_producer_checkpoint_resume_v3.py.source'
    tree=ast.parse(source.read_bytes());wanted={'Writer','SectorBacking','canonical'}
    env={'np':np,'json':json,'sys':sys,'os':__import__('os'),'SECTOR_RECORD':__import__('struct').Struct('<HQI32s')}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in wanted],type_ignores=[]),str(source),'exec'),env)
    payload=np.arange(4,dtype='<f4');payload.flags.writeable=False;value={'published':{('source',0):payload},'locations':{('source',0):{'shape':(4,),'dtype':payload.dtype,'pc':0}}}
    w=env['Writer'].__new__(env['Writer']);w.f=io.BytesIO();w.bytes=w.arrays=w.array_temporary_bytes=0
    actual=w.tree(value)
    shadow=m.typed({'published':{('source',0):m.array([4])},'locations':{('source',0):{'shape':(4,),'dtype':m.Leaf({'dtype':'<f4'}),'pc':0}}})
    def replace_offsets(x):
        if isinstance(x,dict) and set(x)=={'array'}:
            return {'array':[m.U,m.U]+x['array'][2:]}
        if isinstance(x,dict):return {k:replace_offsets(v) for k,v in x.items()}
        if isinstance(x,list):return [replace_offsets(v) for v in x]
        return x
    assert replace_offsets(actual)==shadow


def test_unpriceable_python_or_pointer_layout_refuses(monkeypatch):
    monkeypatch.setattr(m.peer.sys,'version_info',(3,11,0))
    with pytest.raises(ValueError,match='CPython'):m.peer.layout()


def test_tampered_source_schema_refused_before_traversal(tmp_path):
    import shutil
    shutil.copytree(m.D/'inputs',tmp_path/'inputs');shutil.copyfile(m.D/'input_sha256.json',tmp_path/'input_sha256.json')
    p=tmp_path/'inputs/PC01_slice.json.gz';p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='source input changed'):m.source_schemas(tmp_path)


def test_path_enrollment_is_positive_and_explicit(graphs,record):
    g,e=graphs
    assert e['path_char_upper']==223 and len(g['journal_inventory']['root'])==223
    too_long=dict(g['provenance']);too_long['status']='x'*224
    with pytest.raises(ValueError):m.verify_enrolled_metadata('provenance',too_long,record)


def test_source_allowed_nullable_lifecycle_capacity_is_priced(graphs,record):
    import copy
    snapshot=copy.deepcopy(graphs[0]['snapshot'])
    for p in snapshot['ports']['rf'].values():
        p['compact_lifecycle']['tag_capacity']=None;p['compact_lifecycle']['write_capacity']=None
    result=m.verify_enrolled_metadata('snapshot',m.typed(snapshot),record)
    assert result['source_object_bounds_fit']
    assert record['node_profiles']['snapshot']['nullable_integer_slots_upper']==192


def test_counters_are_finite_source_prices_not_elapsed_time(record):
    p=record['counter_source_proof']
    assert p['PC01_source_sector_requests_upper']==1608288
    assert p['serial_prefix_tick_upper']==205860864
    assert p['serial_prefix_tick_upper']<p['metadata_counter_price_upper']==2**64-1
    assert p['no_wall_clock_or_idle_timer']


def test_decoded_node_forms_and_restored_class_headers_are_priced(graphs,record):
    p=m.decoded_metadata_count(graphs[0]['snapshot'])
    assert p==record['decoded_state_metadata']
    assert p['source_object_kind_occurrences']['array']==768
    assert p['source_object_kind_occurrences']['sector_backing']==96
    assert p['source_object_kind_occurrences']['dtype']==576
    assert p['decoded_nonpayload_heap_upper_bytes']>0
    assert p['restored_RF_port_instance_and_vars_upper_bytes']>96*23*8
    assert not p['ndarray_sector_payload_added'] and p['alias_discount_bytes']==0


def test_decoded_unknown_leaf_is_not_zero():
    with pytest.raises(ValueError):m.decoded_metadata_count(m.Leaf({'unknown':[]}))
