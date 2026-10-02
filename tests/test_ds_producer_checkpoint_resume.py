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
import ds_producer_checkpoint_resume as C
from h3_ds_checkpoint_provider_r34 import Provider
from h3_deepseek_complete_native import Builder, Machine
from h3_ds_query_provider_r36 import SizedRF


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


def constructor(root, journal):
    snapshot=root/'revision';snapshot.mkdir(exist_ok=True)
    idx=snapshot/'model.safetensors.index.json'
    if not idx.exists():idx.write_text(json.dumps({'weight_map':{}}))
    ops=[{'pc':pc,'family':'component_native','source_op':{'layer':0},'writes':[{'version':'v'+str(pc)}]} for pc in range(3)]
    homes=[{'version':'v'+str(pc),'rank_group':[0],'SM':0,'partition':'linear', 'word_count':32,
            'home':{'class':'RF','slot_first':pc,'vectors':1}} for pc in range(3)]
    manifest={'journal_root':str(root/journal),'journal_capacity_bytes':8388608,'generation':1,
        'checkpoint_revision':'revision','checkpoint_path':str(snapshot),
        'checkpoint_index_sha256':C.sha(idx),'initial_versions':[]}
    if (root/'future.npy').exists():
        manifest['initial_versions']=[{'version':'future','rank':0,'generation':1,
            'path':str(root/'future.npy'),'sha256':C.sha(root/'future.npy')}]
    p=Provider(manifest,{'instructions':ops}, {}, homes);p.rf=SizedRF(p.rf);e=Engine(p)
    witness=SimpleNamespace(failed=False,seen=set(),expected={(pc,'v'+str(pc),0,1,'data'):{} for pc in range(3)},
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
