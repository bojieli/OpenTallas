import gzip
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_complete_native as N
import h3_deepseek_bounded_tiles as T
spec=importlib.util.spec_from_file_location('native_fixtures',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)

@pytest.mark.parametrize('family',sorted(N.FAMILIES))
def test_bounded_tiles_preserve_native_family_bits(family):
    p=N.recipe(family,F.TOY,F.ATTR);inputs=F.fixture(p)
    expected=N.Machine(p,inputs,N.primitive_div).run()
    provider=T.ArrayProvider(p,inputs,(1,'operand_v0',0,1,0));vm=T.TileExecutor(p,provider)
    got,receipt=vm.run()
    assert receipt['status']=='PASS_BOUNDED_NATIVE_TILES';assert receipt['tensor_scratch_bytes']==0
    assert receipt['max_cache_entries']<=T.CACHE;assert receipt['max_continuation_frames']<=T.FRAME_CAP
    assert receipt['provider']['outstanding']==0;assert not receipt['physical_provider_qualified']
    for key,value in expected.items():
        assert got[key].dtype==value.dtype
        assert np.array_equal(got[key].reshape(-1).view(np.uint8),value.reshape(-1).view(np.uint8)),key

@pytest.mark.parametrize('invalid',[-512,1,(1<<27)-512])
def test_workspace_lease_rejects_alias_alignment_overflow(invalid):
    with pytest.raises(ValueError):T.bind_workspace(invalid)
    with pytest.raises(ValueError):T.bind_workspace(0,[(0,512)])
    with pytest.raises(ValueError):T.bind_workspace(0,aw=34)


def test_actual_full_schedule_is_bounded_and_preserves_all_rank_bindings():
    p=json.loads(gzip.decompress((ROOT/T.PROGRAM).read_bytes()));s=T.compile_schedule(p)
    assert len(s['PC_rank_SM_bindings'])==2213;assert len(s['coverage']['families'])==30
    assert s['workspace']['rank_bytes']==33554432;assert s['workspace']['AW']==27
    assert s['workspace']['base'] is None;assert not s['hardware_admitted']
    for old,new in zip(p['instructions'],s['PC_rank_SM_bindings']):
        assert old['rank_bindings']==new['rank_bindings'];assert old['provider_bindings']==new['provider_bindings']
    assert max(t['continuation_depth_bound'] for t in s['templates'].values())==2053


def test_work_budget_failure_and_exact_fault_no_publication():
    b=N.Builder();v=b.op('DIV',b.load('x',(2,)),b.load('d',(2,)));b.output('out',v);p=b.finish();m={'x':np.asarray([1,2],np.float32),'d':np.asarray([0,0],np.float32)}
    provider=T.ArrayProvider(p,m,(0,'v',0,0,0));got,r=T.TileExecutor(p,provider).run()
    assert got=={};assert r['status']=='FAULT_NO_OUTPUT_PUBLICATION';assert r['output_fragment_bytes']==0
    assert r['error_events'][0]['error']==1
    with pytest.raises(RuntimeError,match='work budget'):T.TileExecutor(p,T.ArrayProvider(p,m,(0,'v',0,0,0)),work_limit=1).run()


def test_selected_row_identity_guard_is_not_skipped_by_demand_scheduling():
    p=N.recipe('kv_gather',F.TOY,F.ATTR);m=F.fixture(p);m['selected_row_ids'][0]+=1
    with pytest.raises(ValueError,match='selected KV row descriptor identity'):T.TileExecutor(p,T.ArrayProvider(p,m,(0,'v',0,0,0))).run()

@pytest.mark.parametrize('family,attrs',[('linear_q',{'fmt':'fp4'}),('compressor',{'closes':False}),('compressor',{'ratio':1}),('index_q',{})])
def test_conversion_expert_index_compressor_tile_boundaries(family,attrs):
    p=N.recipe(family,F.TOY,{**F.ATTR,**attrs});m=F.fixture(p);expected=N.Machine(p,m,N.primitive_div).run()
    got,r=T.TileExecutor(p,T.ArrayProvider(p,m,(13,'v3',1,31,4))).run()
    for key in expected:assert np.array_equal(got[key].reshape(-1).view(np.uint8),expected[key].reshape(-1).view(np.uint8))
    assert r['frame_push_commands']==r['frame_pop_commands'];assert r['memo_write_commands']>0


def test_held_provider_obligation_prevents_execution_and_credit_reuse():
    b=N.Builder();b.output('out',b.load('x',(1,)));p=b.finish();provider=T.ArrayProvider(p,{'x':np.ones(1,np.float32)},(0,'v1',0,0,8))
    key=('other_owner',);provider.memory.preload(key,b'abcd');ticket=provider.memory.submit(key)
    with pytest.raises(RuntimeError):T.TileExecutor(p,provider).run()
    assert provider.memory.pending[ticket.tag]==ticket
    provider.memory.actual_backend_event(ticket);provider.memory.consume(ticket)
    with pytest.raises(ValueError,match='stale/duplicate'):provider.memory.actual_backend_event(ticket)
    got,r=T.TileExecutor(p,provider).run();assert got['out'][0]==1;assert r['provider']['outstanding']==0


def test_memo_corruption_cannot_masquerade_as_same_source_identity():
    b=N.Builder();b.output('out',b.load('x',(1,)));p=b.finish();provider=T.ArrayProvider(p,{'x':np.ones(1,np.float32)},(0,'v1',0,0,8));vm=T.TileExecutor(p,provider)
    root=p['outputs']['out'];vm.value(root,0);slot=vm.slots[root,0];key=('tile_memo',*provider.owner,slot)
    raw=bytearray(provider.memory.values[key]);raw[0]^=1;provider.memory.values[key]=bytes(raw);vm.hot.clear()
    with pytest.raises(ValueError,match='memo generation identity'):vm.value(root,0)


def test_late_overflow_has_no_early_output_publication():
    b=N.Builder();v=b.op('FMUL',b.load('x',(129,)),b.const(2.));b.output('out',v);p=b.finish()
    m={'x':np.ones(129,np.float32)};m['x'][-1]=np.finfo(np.float32).max
    got,r=T.TileExecutor(p,T.ArrayProvider(p,m,(0,'v',0,0,0))).run()
    assert got=={};assert r['output_fragment_bytes']==0;assert r['status']=='FAULT_NO_OUTPUT_PUBLICATION'
