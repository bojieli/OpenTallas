import copy
import json
from pathlib import Path
import sys
from collections import Counter
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_gpu_hc_vector_costs as C
import hdc_golden_v41 as G


def test_640leaf_tree_matches_golden_with20contiguous_SMpartials():
    rng=np.random.default_rng(160640)
    x=G.to_bf16(rng.normal(size=5120).astype(np.float32))
    products=G.mul(x,x)
    partials=np.array([G.csum(products[i*256:(i+1)*256]) for i in range(20)],np.float32)
    tree=np.pad(partials,(0,12))
    for _ in range(5):tree=G.add(tree[0::2],tree[1::2])
    assert G.bits(tree[0])==G.bits(G.csum(products))


def test_halfword_RMW_preserves_neighbor_and_exact_BF16_bits():
    rng=np.random.default_rng(1616)
    f=rng.normal(size=5120).astype(np.float32)
    rounded=G.bits(G.to_bf16(f));lo=rounded[0::2]>>16;hi=rounded[1::2]
    initial=rng.integers(0,2**32,size=2560,dtype=np.uint32)
    even=(initial&np.uint32(0xffff0000))|lo
    assert np.array_equal(even&np.uint32(0xffff0000),initial&np.uint32(0xffff0000))
    odd=(even&np.uint32(0xffff))|hi
    packed=lo|hi
    assert np.array_equal(odd,packed)


def test_odd_RMW_read_follows_even_write_retirement():
    p=C.inputs()['profile'];program=C.masked_store_program(C.N.vector_program('post'))
    code=C.D.address_program(program)
    read_pc=[i for i,x in enumerate(code) if x['op']=='LOAD' and x['attributes'].get('source')=='output BF16 pair word']
    store_pc=[i for i,x in enumerate(code) if x['op']=='STS_PARTIAL']
    r,trace=C.D.replay(program,32,p)
    for w in range(32):
        events={x['pc']:x for x in trace if x['warp']==w}
        assert events[read_pc[1]]['cycle']>=events[store_pc[0]]['retire']
    assert r['allocation']['spills']==0 and r['allocation']['peak_value_registers']<=28


def test_shared_regions_no_alias_or_gain_credit():
    for post in (False,True):
        layout=C.layout(post);end=0
        for region in layout['regions']:
            assert region['base']>=end and region['base']%128==0
            end=region['base']+region['bytes']
        assert end<=65536
    assert 'gain_BF16' in [r['name'] for r in C.layout()['regions']]


def test_bank_and_scalar_broadcast_costs_positive():
    r,_=C.replay(C.N.vector_program('pre'),8,C.inputs()['profile'])
    assert any(x['serialized_accesses']==32 for x in r['bank_accesses'])
    assert any(x['serialized_accesses']==2 and x['packed_half_extract_cycles']>0 for x in r['bank_accesses'])
    assert r['conditional_cycles']>r['cycles']


def test1372phases_composed_with_HC22_and_remaining_refused():
    r,_,g,S=C.build()
    assert len(r['node_costs'])==1372 and r['operations']==dict(hc_pre_norm=80,hc_post=80,final_norm=1)
    merged=copy.deepcopy(r);merged['node_costs'].update(r['HC_rebound_scenario_costs'])
    assert len(merged['node_costs'])==3132
    result=S.schedule(g,merged,evidence_reader=lambda commit,path:(C.ROOT/path).read_bytes())
    assert result['status']=='BLOCKED_MISSING_KERNEL_OR_SERVICE_COSTS'
    assert len(result['missing_costs'])==13629-3132
    assert not any(m['node'] in merged['node_costs'] for m in result['missing_costs'])
    sub=copy.deepcopy(g);sub['nodes']=[n for n in sub['nodes'] if n['id'] in merged['node_costs']]
    for i,n in enumerate(sub['nodes']):n['depends_on']=[] if i==0 else [sub['nodes'][i-1]['id']]
    complete=S.schedule(sub,merged,evidence_reader=lambda commit,path:(C.ROOT/path).read_bytes())
    assert complete['status']=='COMPLETE_MODELED_SCHEDULE_NOT_CONNECTED_RTL'
    assert r['new_burst_input']['physical_storage_bytes_rank']==5494288
    assert not r['new_burst_input']['old_HC22_repriced']
    assert r['graph_rebind']['preserved_transpose_cycles']==35248
    assert sum(x['added_serial_cycles'] for x in r['HC_response_tail_rebind'])==80*720
    assert all(c['progress_deadline_validated'] is False for c in r['HC_rebound_scenario_costs'].values())
    assert not r['hardware_adopted'] and r['headline_rate'] is None


def test_latency_and_finite_HBM_allocation_sensitivity():
    p=C.inputs()['profile'];slow=copy.deepcopy(p);slow['add_latency']*=2
    a,_=C.replay(C.N.vector_program('pre'),8,p)
    b,_=C.replay(C.N.vector_program('pre'),8,slow)
    assert b['conditional_cycles']>a['conditional_cycles']
    r,_,_,_=C.build()
    assert all(t['lines_per_controller']<=4096 for t in r['transfer_assumptions'].values() if isinstance(t,dict))


def test_progress_scope_and_delivery_anchor_refuse_bound():
    r,_,_,_=C.build()
    assert r['bound_admission']=='REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES'
    assert r['Euler_credit_qualification']['credit450_is_validated_upper_bound'] is False
    with pytest.raises(ValueError,match='REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES'):C.require_progress_bound(r)
    for key in ('pre','post'):
        transfer=r['transfer_assumptions'][key]
        assert transfer['delivery_tail_after_last_controller_response_cycles']==4+transfer['lines_to_same_SM']-1
        assert not transfer['progress_deadline_validated']
    assert r['transfer_assumptions']['post_bytes']==4*4*5120*2+4*5120*2+20*80
