import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_ds_checkpoint_provider_r33 as P
import h3_ds_checkpoint_provider_r32 as OLD
import ds_hbm_window_contract_r33 as W
import importlib.util
from importlib.machinery import SourceFileLoader
D=ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002'
_loader=SourceFileLoader('r33_source_native_machine',str(D/'inputs/native_machine_class.py.source'))
_spec=importlib.util.spec_from_loader(_loader.name,_loader)
N=importlib.util.module_from_spec(_spec);_loader.exec_module(N)

@pytest.fixture(scope='module')
def native():
    with gzip.open(D/'inputs/native_fixture_projection.json.gz','rt') as f:return json.load(f)

def setup_actor(tmp_path,native,module=P):
    m=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_bytes());m.update(journal_root=str(tmp_path),journal_capacity_bytes=16<<20)
    p=module.create_provider(m,native,{},[]);owner=(20,(),0,0,1);mem=p.scratch_memory(owner,p.workspace(0))
    mem.transact(('arena',*owner,0),write=True,payload=bytes(range(32)))
    return p,owner,mem

def pending(p,native):
    version=next(b['version'] for bs in native['instructions'][20]['provider_bindings'].values() for b in bs.values() if b['kind']=='versioned_operand')
    for r in range(96):p.pending_routes[20,r]=dict(ids=np.arange(6,dtype=np.int64),layer=0,generation=1,source_version=version)

@pytest.mark.parametrize('fault',['missing_rank','different_ids','stale_generation','wrong_version','wrong_layer'])
def test_refusal_has_no_memory_backing_journal_or_owner_side_effect(tmp_path,native,fault):
    p,owner,mem=setup_actor(tmp_path,native);pending(p,native)
    if fault=='missing_rank':del p.pending_routes[20,95]
    elif fault=='different_ids':p.pending_routes[20,95]['ids']=np.arange(1,7,dtype=np.int64)
    elif fault=='stale_generation':p.pending_routes[20,95]['generation']=2
    elif fault=='wrong_version':p.pending_routes[20,95]['source_version']='stale.route'
    else:p.pending_routes[20,95]['layer']=1
    summary=mem.p.events.summary();backing={k:bytes(v) for k,v in mem.p.backing.items()};used=mem.p.events.budget.used;owners=set(p.pending_routes)
    with pytest.raises(ValueError):p.retire_operation(20,1)
    assert p.memories[owner] is mem and not mem.p.events.closed
    assert mem.p.events.summary()==summary and mem.p.events.budget.used==used
    assert {k:bytes(v) for k,v in mem.p.backing.items()}==backing
    assert not p.retired_journals and set(p.pending_routes)==owners and not p.routes

def test_original_r32_failure_remains_reproducible(tmp_path,native):
    p,owner,mem=setup_actor(tmp_path,native,OLD);pending(p,native);del p.pending_routes[20,95]
    with pytest.raises(ValueError):p.retire_operation(20,1)
    assert owner not in p.memories and mem.p.events.closed and p.retired_journals

def test_publish_routes_only_after_successful_source_fence(tmp_path,native):
    p,owner,mem=setup_actor(tmp_path,native);pending(p,native)
    # Actual outstanding source sector prevents retirement/route publication.
    from hbm_provider_microvm_r21 import Identity
    mem.p.submit(Identity('DeepSeek',0,1,20,1,mem.workspace_extent['base']//32),True,bytes(32))
    with pytest.raises(ValueError):p.retire_operation(20,1)
    assert owner in p.memories and not p.routes and len(p.pending_routes)==96
    transaction=mem.p.queue[0]
    while transaction.state!='held':mem.p.step()
    mem.p.finish(transaction);p.retire_operation(20,1)
    assert mem.p.events.closed and owner not in p.memories and len(p.routes)==96

def test_later_live_actor_does_not_close_earlier_drained_actor(tmp_path,native):
    p,owner,first=setup_actor(tmp_path,native);pending(p,native)
    second_owner=(20,(),1,0,1);second=p.scratch_memory(second_owner,p.workspace(1))
    from hbm_provider_microvm_r21 import Identity
    transaction=second.p.submit(Identity('DeepSeek',1,1,20,1,second.workspace_extent['base']//32),True,bytes(32))
    before=first.p.events.summary()
    with pytest.raises(ValueError):p.retire_operation(20,1)
    assert p.memories[owner] is first and p.memories[second_owner] is second
    assert not first.p.events.closed and first.p.events.summary()==before and not p.retired_journals
    assert not p.routes and len(p.pending_routes)==96 and second.p.live[transaction.tag] is transaction

def movement_subgraph(t):
    # Extract exact source movement ancestors, replacing only computed current
    # row with a typed test LOAD. This is a row-order test, not q_norm arithmetic.
    node=t['outputs']['window'];by={n['dst']:n for n in t['code']};commit=by[node];concat=by[commit['src'][0]];sl=by[concat['src'][0]];load=by[sl['src'][0]]
    current=concat['src'][1]
    code=[copy.deepcopy(load),dict(dst=current,op='LOAD',src=[],shape=[1,512],attrs=dict(name='current',dtype='F32')),copy.deepcopy(sl),copy.deepcopy(concat),copy.deepcopy(commit)]
    return dict(code=code,outputs={'window':node},providers={'window':t['providers']['window'],'current':dict(shape=[1,512],dtype='F32')})

@pytest.mark.parametrize('position',[0,1,126,127,128,129,1048575])
def test_source_window_read_order_first_and_long_positions(native,position):
    template=native['templates'][native['instructions'][5]['rank_bindings'][0]['template']]
    results=[]
    for rep in ['pretrimmed127','full_ring128']:
        lowered,c=W.lower_template(template,position,rep)
        ids=np.asarray(c['input_positions'],np.float32)
        old=np.repeat(ids[:,None],512,axis=1);current=np.full((1,512),position,np.float32)
        vm=N.Machine(movement_subgraph(lowered),{'window':old,'current':current},None)
        actual=vm.run()['window'];expected=np.concatenate([old,current])[-128:]
        assert np.array_equal(actual.view(np.uint32),expected.view(np.uint32))
        assert actual[:,0].astype(np.int64).tolist()==c['output_positions']
        results.append(actual)
    assert np.array_equal(results[0].view(np.uint32),results[1].view(np.uint32))

def test_original_drop_on_pretrimmed_input_is_rejected_by_contract(native):
    t=native['templates'][native['instructions'][5]['rank_bindings'][0]['template']]
    assert t['providers']['window']['shape']==[128,512]
    assert W.row_contract(1048575,'pretrimmed127')['drop_rows']==0
    assert W.row_contract(1048575,'full_ring128')['drop_rows']==1
    with pytest.raises(ValueError):W.row_contract(127,'implicit_padding')

def test_all40_long_position_joins_and_initial_home_disjointness(native):
    lowered,witness=W.lower_full_native(native,1048575,'pretrimmed127')
    assert len(witness)==40
    for row in witness:
        old=native['templates'][row['old_template']];new=lowered['templates'][row['new_template']]
        assert new['providers']['window']['shape']==[127,512]
        for a,b in zip(old['code'],new['code']):
            if a['op'] not in ('LOAD','SLICE') or (a['op']=='LOAD' and a['attrs'].get('name')!='window'):
                assert a==b
        assert old['outputs']==new['outputs']
    produced=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/finite_state_homes.json').read_bytes())
    homes=W.initial_home_directory(native,produced,1048575,'pretrimmed127')
    assert len(homes['rows'])==3840 and max(homes['per_rank_total_reserved_bytes'].values())==29285888
    for rank in range(96):
        rows=sorted([r for r in homes['rows'] if r['rank']==rank],key=lambda r:r['base'])
        assert rows[0]['base']>=33554432+produced['per_rank_reserved_bytes'][str(rank)]
        assert all(a['base']+a['reservation_bytes']<=b['base'] for a,b in zip(rows,rows[1:]))
        assert rows[-1]['base']+rows[-1]['reservation_bytes']<=67108864

def test_source_RoPE_images_are_typed_and_provider_binding_exact(tmp_path,native):
    from ds_hbm_window_rope_prepare_r33 import rope_bindings
    lowered,_=W.lower_full_native(native,1048575,'pretrimmed127')
    cfg=json.loads((D/'inputs/inference_config.json').read_bytes())
    selected=dict(lowered,instructions=[o for o in lowered['instructions'] if 'provider_bindings' in o])
    refs=rope_bindings(selected,cfg,D/'inputs/source_rope_functions.py.source',tmp_path/'rope')
    # Projection includes q_norm templates and their actual coefficient requests.
    assert len(refs)==80
    for ref in refs.values():
        from h3_ds_checkpoint_provider_r30 import LockedArray
        data=LockedArray(ref).check();assert data.shape==(32,) and data.dtype==np.float32 and not data.flags.writeable
        assert np.all(np.isfinite(data))

def test_committed_root_relative_RoPE_images_through_actual_provider(tmp_path,native):
    lowered,_=W.lower_full_native(native,1048575,'pretrimmed127')
    op=lowered['instructions'][5];owned=op['rank_bindings'][0];key=owned['template']
    m=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_bytes())
    m.update(journal_root=str(tmp_path),journal_capacity_bytes=16<<20,view_bindings=json.loads(gzip.decompress((D/'source_owned_rope_bindings.json.gz').read_bytes())))
    p=P.create_provider(m,lowered,{},[])
    bs={name:b for name,b in op['provider_bindings'][key].items() if name in ('rope_cos','rope_sin')}
    views=p._read_one(op,owned,key,bs,1)
    assert set(views)=={'rope_cos','rope_sin'}
    for name,value in views.items():
        assert value['source_binding']==bs[name] and value['data'].shape==(32,)
        assert value['data'].dtype==np.float32 and not value['data'].flags.writeable
    p.release_views(5,0,1,views);assert not p.views
