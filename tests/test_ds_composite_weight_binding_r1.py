"""Constructor-free real native call metadata gates; no trained payload read."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h3_ds_composite_weight_binding_r1 as C
import ds_composite_weight_enrollment_r1 as E
from h3_ds_checkpoint_provider_r33 import Provider as R33
from h3_ds_checkpoint_provider_r34 import Provider as R34

@pytest.fixture(scope='module')
def fixture():
    native=json.loads(gzip.decompress((ROOT/E.NATIVE).read_bytes()))
    enrollment,sha=C.load_enrollment()
    cls=C.provider_class()
    manifest=dict(checkpoint_revision=enrollment['checkpoint_revision'],
        checkpoint_index_sha256=enrollment['checkpoint_index_sha256'],
        composite_weight_binding=dict(schema='DS_COMPOSITE_BF16_OPT_IN_R1',enabled=True,
            enrollment_sha256=sha,payload_reads_admitted=False))
    return native,enrollment,cls,manifest


def call(native,pc,tid=None):
    op=native['instructions'][pc]
    owned=next(r for r in op['rank_bindings'] if tid is None or r['template']==tid)
    tid=owned['template']
    return op,owned,op['provider_bindings'][tid]['weight'],native['templates'][tid]['providers']['weight']


def test_all_actual_caller_order_and_component_coverage(fixture):
    native,enrollment,_,_=fixture
    plans=[]
    for pc in C.PCS:
        op=native['instructions'][pc]
        for owned in op['rank_bindings']:
            tid=owned['template']
            plans.append(C.resolve_call(native,enrollment,'weight',op['provider_bindings'][tid]['weight'],owned,native['templates'][tid]['providers']['weight']))
        chosen=plans[-96:]
        assert [p['rank'] for p in chosen]==[r['rank'] for r in op['rank_bindings']]
        for ordinal in (0,1):
            intervals=[s['rows'] for p in chosen for s in p['segments'] if s['component_ordinal']==ordinal]
            assert intervals[0][0]==0 and intervals[-1][1]==512
            assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
        assert sum(p['selected_checkpoint_bytes'] for p in chosen)==1024*5120*2
    census=json.loads((ROOT/C.OUT/'call-census-r1.json').read_text())
    assert plans==census['plans'] and len(plans)==288
    assert census['max_temporary_and_output_bound_bytes']==450560


def test_all_six_original_rejections_are_preserved(fixture):
    native,_,_,_=fixture
    source_only=type('SourceOnly',(),{'native':native,'_weight_op':R33._weight_op})()
    count=0
    for pc in C.PCS:
        for tid in native['instructions'][pc]['provider_bindings']:
            _,owned,required,spec=call(native,pc,tid)
            with pytest.raises(ValueError,match='exact native weight call identity required'):
                R33.weight_view(source_only,'weight',required,owned,spec)
            count+=1
    assert count==6


def test_actual_read_one_dispatch_accepts_metadata_before_closed_payload_gate(fixture,monkeypatch):
    native,enrollment,cls,manifest=fixture
    def forbidden(*a,**kw):raise AssertionError('constructor/payload must not run')
    monkeypatch.setattr(R33,'__init__',forbidden)
    # __new__ creates no provider backing, journal, source image or constructor.
    provider=object.__new__(cls);provider.native=native;provider.manifest=manifest
    provider.checkpoint=type('NoPayload',(),{'tensor':forbidden})()
    for pc in C.PCS:
        for tid in native['instructions'][pc]['provider_bindings']:
            op,owned,required,spec=call(native,pc,tid)
            with pytest.raises(C.PayloadNotAdmitted) as result:
                R34._read_one(provider,op,owned,tid,{'weight':required},1)
            assert result.value.plan==C.resolve_call(native,enrollment,'weight',required,owned,spec)
    assert 'views' not in vars(provider)


@pytest.mark.parametrize('mutation',['component_order','rows','K','format','caller_order','family'])
def test_native_source_mutants_fail_before_payload(fixture,mutation):
    native,enrollment,_,_=fixture
    # Shallow full graph with only the selected operation copied: bounded metadata.
    wrong=dict(native,instructions=list(native['instructions']))
    op=copy.deepcopy(native['instructions'][115]);wrong['instructions'][115]=op
    if mutation=='component_order':op['source_op']['w'].reverse()
    elif mutation=='rows':op['rank_bindings'][0]['row_interval'][1]+=1
    elif mutation=='K':op['source_op']['k']-=1
    elif mutation=='format':op['source_op']['fmt']='fp8'
    elif mutation=='caller_order':op['rank_bindings'].reverse()
    else:op['family']='linear_q'
    _,owned,required,spec=call(wrong,115)
    with pytest.raises(ValueError):C.resolve_call(wrong,enrollment,'weight',required,owned,spec)


@pytest.mark.parametrize('mutation',['dtype','layout','scale','span'])
def test_component_header_mutants_are_not_assumed_composites(fixture,mutation):
    native,enrollment,_,_=fixture;wrong=copy.deepcopy(enrollment)
    h=wrong['components']['layers.2.attn.compressor.wkv.weight']
    if mutation=='dtype':h['dtype']='F32'
    elif mutation=='layout':h['layout']='transposed'
    elif mutation=='scale':h['scale_tensor']='invented.scale'
    else:h['data_offsets'][1]-=2
    _,owned,required,spec=call(native,115)
    with pytest.raises(ValueError,match='checkpoint dtype/layout/scale/span'):
        C.resolve_call(native,wrong,'weight',required,owned,spec)


def test_structurally_equal_foreign_owner_and_binding_spec_fail(fixture):
    native,enrollment,_,_=fixture;_,owned,required,spec=call(native,115)
    with pytest.raises(ValueError,match='call identity'):
        C.resolve_call(native,enrollment,'weight',required,copy.deepcopy(owned),spec)
    for r,s in [(dict(required,logical_tensor=list(reversed(required['logical_tensor']))),spec),
                (required,dict(spec,dtype='U32'))]:
        with pytest.raises(ValueError,match='binding/template/spec'):
            C.resolve_call(native,enrollment,'weight',r,owned,s)


def test_default_off_checkpoint_and_MRO_enrollment_exact(fixture):
    native,enrollment,cls,manifest=fixture
    assert C.validate_enrollment(native,manifest,cls,check_full_native=False)==enrollment
    for change in [{},dict(manifest,checkpoint_revision='foreign'),
        dict(manifest,composite_weight_binding=dict(manifest['composite_weight_binding'],enrollment_sha256='0'*64))]:
        with pytest.raises(ValueError):C.validate_enrollment(native,change,cls,check_full_native=False)
    class Unenrolled(cls):pass
    with pytest.raises(ValueError,match='MRO identity'):
        C.validate_enrollment(native,manifest,Unenrolled,check_full_native=False)


def test_unchanged_scope_guard_rejects_source_class_change():
    import ds_producer_checkpoint_resume_v3 as V
    old={'source_sha256':{'old.py':'a'},'manifest_sha256':'old'}
    new={'source_sha256':{'new.py':'b'},'manifest_sha256':'new'}
    scopes=[dict(prefix_stop=10,journal_root='/old',journal_capacity_bytes=131072),
            dict(prefix_stop=19,journal_root='/new',journal_capacity_bytes=131072)]
    transition=dict(schema='DS_EXPLICIT_RUN_SCOPE_TRANSITION_V1',old_identity=old,new_identity=new,
        old_run_scope=scopes[0],new_run_scope=scopes[1],next_pc=11,checkpoint_receipt={},role_proof={})
    transition['seal_sha256']=hashlib.sha256(V.canonical(transition)).hexdigest()
    with pytest.raises(ValueError,match='data identity changed'):
        V.validate_scope_transition(transition,old_identity=old,new_identity=new,
            old_scope=scopes[0],new_scope=scopes[1],next_pc=11,role_proof={})


def test_existing_expert_and_single_tensor_handlers_delegate_without_new_enrollment(fixture,monkeypatch):
    _,_,cls,_=fixture
    sentinel=object();seen=[]
    def inherited(self,name,required,owned,spec):
        seen.append(required['logical_tensor']);return sentinel
    monkeypatch.setattr(R33,'weight_view',inherited)
    provider=object.__new__(cls)
    for tensor in ([0,'w1'],[6,'w2'],'layers.0.attn.wo_a.weight','layers.0.attn.wq_a.weight'):
        assert provider.weight_view('weight',{'logical_tensor':tensor},{},{}) is sentinel
    assert len(seen)==4 and vars(provider)=={}


def test_constructor_enrollment_guard_precedes_all_backing(fixture,monkeypatch):
    native,_,cls,_=fixture
    def forbidden(*args,**kwargs):raise AssertionError('base constructor was reached')
    monkeypatch.setattr(R33,'__init__',forbidden)
    # Exercise the pure preflight called first by the successor constructor;
    # do not invoke any __init__, allocate backing, journal, or source arrays.
    with pytest.raises(ValueError,match='enrollment absent'):
        C.validate_enrollment(native,{},cls,check_full_native=False)
