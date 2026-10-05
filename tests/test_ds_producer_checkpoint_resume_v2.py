"""Actual r30 writer/sector/read endpoints + original native primitive VM.
Small component operands are inputs, never saved expected outputs. No R45 run.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_producer_checkpoint_resume_v2 as C
from h3_ds_checkpoint_provider_r34 import Provider
from h3_deepseek_complete_native import Builder, Machine
from h3_ds_query_provider_r36 import SizedRF
from h3_ds_query_provider_r36 import QueryMixin
from h4_hbm_w19_pc10_endpoints import ProductionSharedFactory


class QueryProvider(QueryMixin,Provider):pass


class Groups:
    def __init__(self,budget):
        self.failed=False;self.completed=set();self.shared=ProductionSharedFactory(budget)


class Engine:
    def __init__(self,p):
        self.provider=p;self.native=p.native;self.dispatch={'arithmetic':'original native FADD/FMUL'}
        self.generation=p.generation;self.retired=set();self.last_use={'v0':1,'v1':2}
    def execute_operation(self,op):
        pc=op['pc']
        if pc in self.retired:raise ValueError('duplicate original execution')
        x=np.arange(32,dtype=np.float32) if pc==0 else self.provider.restore('v'+str(pc-1),0)
        b=Builder();v=b.load('x',(32,));v=b.op('FADD' if pc!=2 else 'FMUL',v,b.const(1.25))
        b.output('out',v);data=Machine(b.finish(),{'x':x}).run()['out']
        self.provider.publish({'PC':pc,'rank':0,'generation':1,'version':'v'+str(pc),'home_indices':[pc]}, {'data':data},{'result':'out'})
        self.provider.retire_operation(pc,1);self.retired.add(pc)


def constructor(root, journal, *, query=False, shared=False, query_exp_dtype='U32',run_stop=None,journal_capacity=None):
    snapshot=root/'revision';snapshot.mkdir(exist_ok=True)
    idx=snapshot/'model.safetensors.index.json'
    if not idx.exists():idx.write_text(json.dumps({'weight_map':{}}))
    count=11 if shared else 3
    ops=[{'pc':pc,'family':'component_native','source_op':{'layer':0},'writes':[{'version':'v'+str(pc)}]} for pc in range(count)]
    homes=[{'version':'v'+str(pc),'rank_group':[0],'SM':0,'partition':'linear', 'word_count':32,
            'home':{'class':'RF','slot_first':pc,'vectors':1}} for pc in range(count)]
    manifest={'journal_root':str(root/journal),'journal_capacity_bytes':8388608,'generation':1,
        'checkpoint_revision':'revision','checkpoint_path':str(snapshot),
        'checkpoint_index_sha256':C.sha(idx),'initial_versions':[]}
    if run_stop is not None:manifest['prefix_stop']=run_stop
    if journal_capacity is not None:manifest['journal_capacity_bytes']=journal_capacity
    if (root/'future.npy').exists():
        manifest['initial_versions']=[{'version':'future','rank':0,'generation':1,
            'path':str(root/'future.npy'),'sha256':C.sha(root/'future.npy')}]
    if query:
        # Finite component campaign <=4096 transactions, including all
        # mirrored writes, field readbacks and resumed RF reads. Source
        # journal reserves metadata before admission; no host process cap.
        manifest['journal_capacity_bytes']=4096*65536
        ops[0]['family']='index_q';ops[0]['writes'][0]['native_result_binding']={'result':'iqf'}
        homes=[dict(version='v0',rank_group=[0],SM=sm,partition='linear',word_count=256,
            home={'class':'RF','slot_first':0,'vectors':2}) for sm in range(16)]
        manifest['query_field_homes']={'original_reserved_bytes_per_rank':{'0':0},'rows':[
            dict(version='v0',rank=0,field='query_codes',PC=0,generation=1,dtype='U32',shape=[32,64],
                base=33554432,bytes=8192,reservation_bytes=8192),
            dict(version='v0',rank=0,field='query_exp',PC=0,generation=1,dtype=query_exp_dtype,shape=[32,4],
                base=33562624,bytes=1024 if query_exp_dtype=='I64' else 512,
                reservation_bytes=1024 if query_exp_dtype=='I64' else 512)]}
    p=(QueryProvider if query else Provider)(manifest,{'instructions':ops}, {}, homes);p.rf=SizedRF(p.rf);e=Engine(p)
    if shared:e.groups=Groups(p.journal_budget)
    witness=SimpleNamespace(failed=False,seen=set(),expected={(pc,'v'+str(pc),0,1,'data'):{} for pc in range(count)},
        initialization_provenance={'source':'component input arange; no oracle stimulus'},events=SimpleNamespace(summary=lambda:{'actual_journal':str(p.journal_budget.path)}))
    return p,e,witness


def captured(tmp_path):
    p,e,w=constructor(tmp_path,'first');e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
    contract={'identity':C.identity(p,e)};dest=tmp_path/'checkpoint'
    receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=contract)
    return p,e,w,contract,dest,receipt


def test_actual_provider_native_operators_continuous_vs_restored_byteexact(tmp_path):
    p,e,w,c,d,r=captured(tmp_path)
    for op in e.native['instructions'][1:]:e.execute_operation(op)
    continuous=p.restore('v2',0).tobytes()
    p2,e2,w2=constructor(tmp_path,'resumed')
    verified=C.verify_checkpoint(d,source_contract=c,next_pc=1,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    result=C.restore_quiescent(verified,e2,p2,w2)
    assert result['retired']==[0] and w2.seen=={(0,'v0',0,1,'data')}
    C.execute_remaining(e2,stop_after=2)
    assert p2.restore('v2',0).tobytes()==continuous
    assert all(not getattr(port,f) for port in p2.rf.values() for f in ('live','queue','calendar','resident'))
    assert p2.rf[0].accept_sequence>0 and p2.rf[0].now>0


@pytest.mark.parametrize('field',['views','memories','pending_routes','history_view_leases'])
def test_live_owners_refuse_capture(tmp_path,field):
    p,e,w=constructor(tmp_path,'live');e.retired={0};setattr(p,field,{'live':'accepted'})
    with pytest.raises(ValueError,match='live'):C.project_checkpoint(e,p,w,boundary_pc=0,destination=tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_pending_reverse_partial_append_and_retired_gap_refuse(tmp_path):
    p,e,w,c,d,r=captured(tmp_path);p.rf[0].queue.append('accepted')
    with pytest.raises(ValueError,match='debt'):C.quiescent(p,e)
    p.rf[0].queue.clear();p.history=SimpleNamespace(pending={'half':'row'},leases={})
    with pytest.raises(ValueError,match='partial'):C.quiescent(p,e)
    del p.history;e.retired={0,2}
    with pytest.raises(ValueError,match='prefix'):C.quiescent(p,e)


@pytest.mark.parametrize('file',['payload.bin','state.json','actual_observations.json'])
def test_tampered_checkpoint_refuses_before_constructor_mutation(tmp_path,file):
    p,e,w,c,d,r=captured(tmp_path);f=d/file;raw=f.read_bytes();f.write_bytes(bytes([raw[0]^1])+raw[1:])
    with pytest.raises(ValueError):C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':c['identity'],'checkpoint_receipt':r})


def test_stale_generation_source_and_partial_checkpoint_refuse(tmp_path):
    p,e,w,c,d,r=captured(tmp_path);p2,e2,w2=constructor(tmp_path,'cold')
    p2.generation=2;e2.generation=2
    with pytest.raises(ValueError,match='contract'):C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    with pytest.raises(ValueError,match='next PC'):C.verify_checkpoint(d,source_contract=c,next_pc=2,constructor_contract={'identity':c['identity'],'checkpoint_receipt':r})
    (d/'RUNNER_COMPLETE.json').unlink()
    with pytest.raises(FileNotFoundError):C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':c['identity'],'checkpoint_receipt':r})


def test_resume_loop_defaultoff_and_no_expected_stimulus(tmp_path):
    p,e,w,c,d,r=captured(tmp_path)
    with pytest.raises(ValueError,match='verified'):C.execute_remaining(e,stop_after=2)
    with pytest.raises(ValueError,match='default-off'):C.save(p,e,tmp_path/'disabled')
    raw=(d/'state.json').read_bytes()
    assert b'expected_outputs' not in raw and b'golden' not in raw
    assert C.project_checkpoint(e,p,w,boundary_pc=0,destination=tmp_path/'sized')['payload_bytes']>0


def test_unknown_and_missing_actual_backing_fail_closed(tmp_path):
    p,e,w,c,d,r=captured(tmp_path)
    p.new_unpriced_owner=True
    with pytest.raises(ValueError,match='unknown'):C.quiescent(p,e)
    del p.new_unpriced_owner
    del p.rf[0].backing[next(iter(p.rf[0].backing))]
    with pytest.raises(ValueError,match='missing'):C.save(p,e,tmp_path/'badbacking',enabled=True)


def test_future_locked_file_identity_not_copied_and_mutation_refused(tmp_path):
    np.save(tmp_path/'future.npy',np.arange(32,dtype=np.float32))
    p,e,w,c,d,r=captured(tmp_path)
    closure=json.loads((d/'state.json').read_text())
    assert closure['payload_bytes']==384  # 128 actual produced + two 128-byte RF copies
    np.save(tmp_path/'future.npy',np.arange(32,dtype=np.float32)+1)
    with pytest.raises(ValueError,match='drift'):C.verify_inputs(p)


def test_retired_set_reference_survives_restore_for_PC10_gate(tmp_path):
    p,e,w,c,d,r=captured(tmp_path);p2,e2,w2=constructor(tmp_path,'resume2');retired=e2.retired
    v=C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    assert e2.retired is retired and retired=={0}


def test_consumed_source_window_is_not_resurrected_by_coldconstructor(tmp_path):
    np.save(tmp_path/'future.npy',np.arange(32,dtype=np.float32))
    p,e,w=constructor(tmp_path,'initialretired');e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
    p.release_version('future',1)
    c={'identity':C.identity(p,e)};d=tmp_path/'savedretired'
    r=C.capture_quiescent(e,p,w,boundary_pc=0,destination=d,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'retiredresume')
    v=C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    assert not p2.source_images and ('future',0) not in p2.published


def test_layout_and_missing_actual_observer_refuse(tmp_path):
    p,e,w,c,d,r=captured(tmp_path);p2,e2,w2=constructor(tmp_path,'wronglayout')
    p2.homes[0]['home']['slot_first']=7
    with pytest.raises(ValueError,match='contract'):C.verify_checkpoint(d,source_contract=c,next_pc=1,constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    w.seen.clear()
    with pytest.raises(ValueError,match='observation'):C.project_checkpoint(e,p,w,boundary_pc=0,destination=tmp_path/'unobserved')


def test_partial_sector_validity_survives_typed_capture(tmp_path):
    p,e,w,c,d,r=captured(tmp_path)
    p.rf[0].backing['DeepSeek',0,9999]=[3]+[None]*31
    c={'identity':C.identity(p,e)};dest=tmp_path/'partialunused'
    r=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'partialresume')
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=1,constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    assert p2.rf[0].backing['DeepSeek',0,9999]==[3]+[None]*31


def state_constructor(root,journal):
    p,e,w=constructor(root,journal)
    p.homes[0].update(home={'class':'HBM_NATIVE_STATE'},binding={
        'PC':0,'version':'v0','rank':0,'source_result':'out','shape':[32],
        'dtype':'F32','base':33554432,'reservation_bytes':128})
    return p,e,w


def test_actual_state_without_cached_publication_resume_and_native_consumer(tmp_path):
    p,e,w=state_constructor(tmp_path,'statefirst')
    e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
    assert ('v0',0) not in p.published
    c={'identity':C.identity(p,e)};dest=tmp_path/'statecheckpoint'
    receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    for op in e.native['instructions'][1:]:e.execute_operation(op)
    continuous=p.restore('v2',0).tobytes()
    p2,e2,w2=state_constructor(tmp_path,'statecold')
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=1,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':receipt})
    C.restore_quiescent(v,e2,p2,w2)
    assert ('v0',0) not in p2.published
    C.execute_remaining(e2,stop_after=2)
    assert p2.restore('v2',0).tobytes()==continuous


@pytest.mark.parametrize('mutant',['missing_byte','binding_identity','aperture','extent'])
def test_state_owned_bytes_and_exact_home_negatives(tmp_path,mutant):
    import copy
    p,e,w=state_constructor(tmp_path,'statenegative');e.execute_operation(e.native['instructions'][0])
    loc=p.locations['v0',0];loc['binding']=copy.deepcopy(loc['binding'])
    if mutant=='missing_byte':
        p.state[0].backing['DeepSeek',0,33554432//32]=[None]*32
    elif mutant=='binding_identity':loc['binding']['version']='different'
    elif mutant=='aperture':loc['binding']['base']=0
    else:loc['shape']=(64,)
    with pytest.raises(ValueError):C.validate_backing(p)


def test_complete_future_program_and_fullgraph_state_bound(tmp_path):
    p,e,w=constructor(tmp_path,'fullgraph');e.execute_operation(e.native['instructions'][0])
    w.seen.add((0,'v0',0,1,'data'))
    p.fullgraph_source_sha=hashlib.sha256(C.canonical(p.native)).hexdigest()
    p.fullgraph_source_failed=False
    c={'identity':C.identity(p,e)};dest=tmp_path/'fullgraphcheckpoint'
    r=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'fullgraphcold')
    p2.fullgraph_source_sha=p.fullgraph_source_sha;p2.fullgraph_source_failed=False
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=1,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    assert p2.fullgraph_source_sha==p.fullgraph_source_sha
    # A change confined to an unexecuted future PC must refuse enrollment.
    p2.native['instructions'][2]['source_op']['layer']=1
    assert C.identity(p2,e2)!=c['identity']
    with pytest.raises(ValueError,match='source identity'):C.quiescent(p2,e2)
    p2.fullgraph_source_sha=hashlib.sha256(C.canonical(p2.native)).hexdigest()
    p2.fullgraph_source_failed=True
    with pytest.raises(ValueError,match='failed'):C.quiescent(p2,e2)


def test_future_use_alias_visibility_and_generation_counters_preserved(tmp_path):
    p,e,w=constructor(tmp_path,'aliases');e.execute_operation(e.native['instructions'][0])
    w.seen.add((0,'v0',0,1,'data'))
    # Addressed alias is produced through the actual publisher, not copied
    # from expected values; the existing distinct RF home is retained.
    alias=p.restore('v0',0)
    p.publish({'PC':1,'rank':0,'generation':1,'version':'v1','home_indices':[1]},
        {'data':alias},{'result':'out'})
    p.retire_operation(1,1);e.retired.add(1);w.seen.add((1,'v1',0,1,'data'))
    e.last_use={'v0':2212,'v1':2212};e.unconsumed_plan={'future_aliases':['v0','v1'],'last_PC':2212}
    c={'identity':C.identity(p,e)};dest=tmp_path/'aliascheckpoint'
    r=C.capture_quiescent(e,p,w,boundary_pc=1,destination=dest,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'aliascold')
    e2.last_use=dict(e.last_use);e2.unconsumed_plan=dict(e.unconsumed_plan)
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=2,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    assert set(p2.locations)==set(p.locations)
    assert p2.rf[0].generations==p.rf[0].generations
    assert p2.restore('v0',0).tobytes()==p2.restore('v1',0).tobytes()==alias.tobytes()
    assert e2.last_use==e.last_use and e2.unconsumed_plan==e.unconsumed_plan


def test_storage_join_never_hides_checkpoint_or_doublecharges_existing_journal(tmp_path):
    p,e,w,c,d,r=captured(tmp_path)
    projection=C.project_checkpoint(e,p,w,boundary_pc=0,destination=tmp_path/'projection')
    n=projection['filesystem_reservation_bytes'];future=913249523376
    failed=C.join_storage_projection(projection,continuation_new_bytes=future,
        other_new_bytes=100,available_bytes=891025633280)
    assert failed['status']=='REFUSE_STORAGE_HEADROOM'
    passed=C.join_storage_projection(projection,continuation_new_bytes=future,
        other_new_bytes=100,available_bytes=future+n+100)
    assert passed['headroom_bytes']==0 and passed['required_new_bytes']==future+n+100
    for invalid in (None,True,0,-1):
        with pytest.raises(ValueError):C.join_storage_projection(projection,
            continuation_new_bytes=invalid,other_new_bytes=0,available_bytes=future)


def test_capture_projection_bounds_all_committed_files_including_source_metadata(tmp_path):
    p,e,w=constructor(tmp_path,'metadata');e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
    c={'identity':C.identity(p,e),'reviewed_metadata':'x'*100000};dest=tmp_path/'metadatacapture'
    C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    projection=json.loads((dest/'actual_observations.json').read_text())['projection']
    assert sum(f.stat().st_size for f in dest.iterdir())<=projection['filesystem_reservation_bytes']


def test_actual_PC10_shared_memory_payload_counters_and_continuation(tmp_path):
    p,e,w=constructor(tmp_path,'sharedfirst',shared=True)
    for op in e.native['instructions']:
        e.execute_operation(op);w.seen.add((op['pc'],'v'+str(op['pc']),0,1,'data'))
    owner=dict(PC=10,rank=0,SM=3,generation=1,tile=7,template='source_component')
    e.groups.completed.add((10,0,1))
    memory=e.groups.shared(owner);payload=np.arange(128,dtype=np.uint32).tobytes()
    memory.transact(0,write=True,payload=payload,length=512)
    # Re-read via actual endpoint before capture, preserving its next serial.
    assert memory.transact(0,write=False,payload=b'',length=512)==payload
    serial=memory.serial;generations=list(memory.p.generations);now=memory.p.now
    c={'identity':C.identity(p,e)};dest=tmp_path/'sharedcapture'
    receipt=C.capture_quiescent(e,p,w,boundary_pc=10,destination=dest,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'sharedcold',shared=True)
    factory=e2.groups.shared
    completed=e2.groups.completed
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=11,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':receipt})
    C.restore_quiescent(v,e2,p2,w2)
    assert e2.groups.shared is factory
    assert e2.groups.completed is completed and completed=={(10,0,1)}
    restored=factory.memories[0,3]
    assert restored.extent==memory.extent and restored.owner==owner
    assert restored.serial==serial and restored.p.now==now and restored.p.generations==generations
    for field in C.PORT_STATE:
        assert getattr(restored.p,field)==getattr(memory.p,field)
    assert len(restored.p.events)==0  # no synthetic transaction/ACK replay
    assert restored.transact(0,write=False,payload=b'',length=512)==payload
    assert restored.serial==serial+16
    assert C.inventory(p2,e2)['retained_shared_homes']==1


@pytest.mark.parametrize('mutant',['queue','resident','generation','extent','serial','allocation','unknown','wrong_address'])
def test_shared_live_identity_and_home_refusals(tmp_path,mutant):
    p,e,w=constructor(tmp_path,'sharedbad',shared=True);e.retired=set(range(11))
    memory=e.groups.shared(dict(PC=10,rank=0,SM=0,generation=1,tile=0,template='actual'))
    if mutant=='queue':memory.p.queue.append('accepted')
    elif mutant=='resident':memory.p.resident=1
    elif mutant=='generation':memory.owner['generation']=2
    elif mutant=='extent':memory.extent['bytes']=8192
    elif mutant=='serial':memory.serial=1
    elif mutant=='allocation':memory.p.allocation_identity['SM']=1
    elif mutant=='unknown':memory.unpriced_lease=True
    else:memory.p.backing['DeepSeek',0,0]=[1]*32
    reason={'queue':'live shared','resident':'live shared','generation':'owner identity',
        'extent':'finite extent','serial':'accepted sequence','allocation':'allocation identity',
        'unknown':'unknown shared','wrong_address':'backing address'}[mutant]
    with pytest.raises(ValueError,match=reason):C.quiescent(p,e)


def test_shared_owner_cannot_capture_before_source_PC_retired(tmp_path):
    p,e,w=constructor(tmp_path,'sharedunretired',shared=True);e.retired=set(range(10))
    e.groups.shared(dict(PC=10,rank=0,SM=0,generation=1,tile=0,template='actual'))
    with pytest.raises(ValueError,match='unretired'):C.quiescent(p,e)


def query_publication(tmp_path,journal,query_exp_dtype='U32'):
    from ds_hbm_history_codec_r36 import decode
    p,e,w=constructor(tmp_path,journal,query=True,query_exp_dtype=query_exp_dtype)
    codes=np.full((32,64),0x22,np.uint32);codes[0,0]=0x88
    exp=np.full((32,4),0xffffffff,np.uint32)
    signed=exp.view(np.int32).astype(np.int64)
    data=decode(codes,signed,'FP4E8')
    if query_exp_dtype=='I64':exp=signed
    p.publish(dict(PC=0,rank=0,generation=1,version='v0',home_indices=list(range(16))),
        {'data':data,'query_codes':codes,'query_exp':exp},{'result':'iqf'})
    p.retire_operation(0,1);e.retired.add(0);w.seen.add((0,'v0',0,1,'data'))
    return p,e,w


@pytest.mark.parametrize('query_exp_dtype',['U32','I64'])
def test_actual_compound_query_fields_signed_exponent_capture_restore(tmp_path,query_exp_dtype):
    p,e,w=query_publication(tmp_path,'queryfirst',query_exp_dtype)
    before=len(p.state[0].events);C.validate_backing(p)
    assert len(p.state[0].events)==before  # checkpoint checker never manufactures ACKs
    identity=p.query_visible['v0',0]
    expected={f:p._query_access(identity,f).tobytes() for f in ('query_codes','query_exp')}
    c={'identity':C.identity(p,e)};dest=tmp_path/'querycapture'
    r=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    p2,e2,w2=constructor(tmp_path,'querycold',query=True,query_exp_dtype=query_exp_dtype)
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=1,
        constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':r})
    C.restore_quiescent(v,e2,p2,w2)
    identity2=p2.query_visible['v0',0]
    assert {f:p2._query_access(identity2,f).tobytes() for f in expected}==expected
    a=p2._query_access(identity2,'query_exp')
    assert np.all((a.view(np.int32) if query_exp_dtype=='U32' else a)==-1)
    assert p2.restore('v0',0).tobytes()==p.restore('v0',0).tobytes()


@pytest.mark.parametrize('mutant',['byte','missing','home','identity','parent'])
def test_compound_query_codec_home_visibility_refusals(tmp_path,mutant):
    p,e,w=query_publication(tmp_path,'querybad')
    if mutant=='byte':
        key=('DeepSeek',0,33554432//32);data=list(p.state[0].backing[key]);data[0]^=1;p.state[0].backing[key]=data
    elif mutant=='missing':del p.state[0].backing['DeepSeek',0,33554432//32]
    elif mutant=='home':
        import copy
        p.query_homes=copy.deepcopy(p.query_homes);p.query_homes['v0',0,'query_codes']['base']+=32
    elif mutant=='identity':p.query_visible['v0',0]['generation']=2
    else:p.locations.pop(('v0',0))
    with pytest.raises(ValueError):C.validate_backing(p)


def scoped_capture(tmp_path):
    p,e,w=constructor(tmp_path,'scopeold',run_stop=0)
    e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
    c={'identity':C.identity(p,e)};dest=tmp_path/'scopecapture'
    receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=c)
    return p,e,w,c,dest,receipt


def test_explicit_authorized_run_scope_extension_same_data_and_actual_ports(tmp_path):
    p,e,w,c,dest,receipt=scoped_capture(tmp_path)
    for op in e.native['instructions'][1:]:e.execute_operation(op)
    continuous=p.restore('v2',0).tobytes()
    p2,e2,w2=constructor(tmp_path,'scopenew',run_stop=2,journal_capacity=16777216)
    with pytest.raises(ValueError,match='contract'):
        C.verify_checkpoint(dest,source_contract=c,next_pc=1,
            constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':receipt})
    transition=C.plan_run_scope_transition(dest,source_contract=c,checkpoint_receipt=receipt,provider=p2,engine=e2,next_pc=1)
    contract={'identity':C.identity(p2,e2),'run_scope':C.run_scope(p2),
        'run_scope_transition':transition,'checkpoint_receipt':receipt}
    verified=C.verify_checkpoint(dest,source_contract=c,next_pc=1,constructor_contract=contract)
    restored=C.restore_quiescent(verified,e2,p2,w2)
    assert json.loads((p2.journal_budget.root/'checkpoint_restore_scope.json').read_text())==restored['run_scope_receipt']
    assert p2.journal_budget.cap==16777216 and str(p2.journal_budget.root)==str(tmp_path/'scopenew')
    assert p2.rf[0].qd==p.rf[0].qd and p2.rf[0].tags==p.rf[0].tags
    assert transition['old_run_scope']['prefix_stop']==0 and transition['new_run_scope']['prefix_stop']==2
    C.execute_remaining(e2,stop_after=2)
    assert p2.restore('v2',0).tobytes()==continuous
    with pytest.raises(ValueError,match='run scope'):C.execute_remaining(e2,stop_after=3)


@pytest.mark.parametrize('mutant',['generation','homes','last_use','native','inputs','manifest_resource','retention','source_role','boundary'])
def test_run_scope_extension_never_relaxes_data_or_owner_identity(tmp_path,mutant):
    p,e,w,c,dest,receipt=scoped_capture(tmp_path)
    p2,e2,w2=constructor(tmp_path,'scopebad',run_stop=2,journal_capacity=16777216)
    if mutant=='generation':p2.generation=2;e2.generation=2
    elif mutant=='homes':p2.homes[0]['home']['slot_first']=7
    elif mutant=='last_use':e2.last_use['v0']=0
    elif mutant=='native':p2.native['instructions'][2]['source_op']['layer']=1
    elif mutant=='inputs':p2.manifest['initial_versions']=[{'version':'fake'}]
    elif mutant=='manifest_resource':p2.manifest['provider_tags']=8
    elif mutant=='retention':e2.unconsumed_plan={'dropped':'future'}
    elif mutant=='source_role':p2.journal_budget.cap=123456
    else:p2.manifest['prefix_stop']=0
    with pytest.raises(ValueError):C.plan_run_scope_transition(dest,source_contract=c,
        checkpoint_receipt=receipt,provider=p2,engine=e2,next_pc=1)


def test_run_scope_transition_tamper_and_stale_scope_refuse(tmp_path):
    import copy
    p,e,w,c,dest,receipt=scoped_capture(tmp_path)
    p2,e2,w2=constructor(tmp_path,'scopevalid',run_stop=2,journal_capacity=16777216)
    t=C.plan_run_scope_transition(dest,source_contract=c,checkpoint_receipt=receipt,provider=p2,engine=e2,next_pc=1)
    contract={'identity':C.identity(p2,e2),'run_scope':C.run_scope(p2),'checkpoint_receipt':receipt}
    bad=copy.deepcopy(t);bad['new_run_scope']['journal_capacity_bytes']+=1
    with pytest.raises(ValueError,match='seal'):C.verify_checkpoint(dest,source_contract=c,next_pc=1,
        constructor_contract=dict(contract,run_scope_transition=bad))
    bad=copy.deepcopy(t);bad['old_run_scope']['journal_root']='wrong'
    bad['seal_sha256']=__import__('hashlib').sha256(C.canonical({k:v for k,v in bad.items() if k!='seal_sha256'})).hexdigest()
    with pytest.raises(ValueError,match='binding'):C.verify_checkpoint(dest,source_contract=c,next_pc=1,
        constructor_contract=dict(contract,run_scope_transition=bad))
    v=C.verify_checkpoint(dest,source_contract=c,next_pc=1,constructor_contract=dict(contract,run_scope_transition=t))
    p2.manifest['prefix_stop']=1
    with pytest.raises(ValueError):C.restore_quiescent(v,e2,p2,w2)


class CapacityCoupledProvider(Provider):
    def __init__(self,manifest,*args):
        super().__init__(manifest,*args)
        # Deliberately forbidden test source: metadata cap drives a native
        # architecture resource, so that cap cannot be treated as evidence.
        self.physical_tags=manifest['journal_capacity_bytes']//131072


def test_evidence_role_refuses_capacity_that_drives_architecture(tmp_path):
    p,e,w=constructor(tmp_path,'role');p.__class__=CapacityCoupledProvider
    with pytest.raises(ValueError,match='unreviewed run-scope use'):C.scope_role_proof(p,e)


def test_explicit_helper_selection_default_legacy_and_pinned_successor():
    from ds_producer_checkpoint_helper_select import select_checkpoint_helper
    import ds_producer_checkpoint_resume as legacy
    assert select_checkpoint_helper() is legacy
    assert select_checkpoint_helper('quiescent_v2',expected_sha256=C.sha(C.__file__)) is C
    assert C.SCHEMA!=legacy.SCHEMA
    with pytest.raises(ValueError,match='source pin'):select_checkpoint_helper('quiescent_v2')
    with pytest.raises(ValueError,match='source mismatch'):select_checkpoint_helper('quiescent_v2',expected_sha256='0'*64)
    with pytest.raises(ValueError,match='known'):select_checkpoint_helper('automatic')
