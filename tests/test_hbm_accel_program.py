"""HA5 source gates; synthetic operator tests never load a model checkpoint."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hbm_accel_program import compile_program, execute_layer, merge_audit, schedule_ops, selector_plan
from hbm_accel_program_model import selector_cost
import w19_hbm_tp96_isa as ISA


@pytest.fixture(scope='module')
def program():
    return json.loads((ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json').read_text())


def test_default_byte_semantics_and_no_input_mutation(program):
    saved=copy.deepcopy(program)
    assert compile_program(program)==program
    compile_program(program,True)
    assert program==saved


def test_all_40_layers_preserve_operations_head_collectives_and_sum(program):
    candidate=compile_program(program,True)
    for old,new in zip(program['layers'],candidate['layers']):
        def identities(layer):
            return sorted(json.dumps({k:v for k,v in o.items() if k!='id'},sort_keys=True) for o in layer['ops'])
        assert identities(old)==identities(new)
        assert [o for o in old['ops'] if o['unit']=='COLL']==[
            o for o in new['ops'] if o['unit']=='COLL']
        if old['layer']=='head':
            assert old==new
            continue
        ops=new['ops'];fetch=next(i for i,o in enumerate(ops) if o['kind']=='expert_fetch')
        assert ops[fetch+1]['w']==[6,'w1']
        assert ops[fetch+2]['w']==[6,'w3']
        assert ops[fetch+3]['fn']=='swiglu'
        assert ops[fetch-1]['fn']=='route'
        assert [o['w'][0] for o in ops if o['kind']=='mv' and isinstance(o.get('w'),list) and o['w'][1]=='w2']==[6,0,1,2,3,4,5]
        assert [o['id'] for o in ops]==list(range(len(ops)))


@pytest.mark.parametrize('positions',range(1,7))
def test_selector_positions_never_mix(program,positions):
    for replicas in range(1,positions+1):
        for plan in selector_plan(program,positions,replicas):
            tasks=plan['positions']
            assert sorted(t['position'] for t in tasks)==list(range(positions))
            assert len({(t['replica'],t['wave']) for t in tasks})==positions


def test_refuses_noncanonical_route_and_fetch(program):
    ops=copy.deepcopy(program['layers'][0]['ops'])
    fetch=next(i for i,o in enumerate(ops) if o['kind']=='expert_fetch')
    ops[fetch]['experts']=3
    with pytest.raises(ValueError):schedule_ops(ops,True)
    ops=copy.deepcopy(program['layers'][0]['ops'])
    ops[fetch-1]['fn']='hc_pre_norm'
    with pytest.raises(ValueError):schedule_ops(ops,True)


def test_original_executor_shared_intermediate_writes_commute_on_all_ranks():
    # Execute the actual unchanged SwiGLU on synthetic small operands. No model,
    # matvec, inference or golden regeneration. Catch ea allocation/overwrite.
    ex=ISA.Executor.__new__(ISA.Executor)
    ex.m=SimpleNamespace(k_exp=6,limit=10.)
    for rank in range(96):
        states=[]
        lo,hi=ISA.even(2304)[rank]
        for order in (list(range(7)),[6,0,1,2,3,4,5]):
            rk=ISA.Rank(rank)
            rk.put('route_w',np.array([.1,.2,.3,.4,.5,.6],np.float32))
            for slot in range(7):
                g=np.linspace(-4,4,hi-lo,dtype=np.float32)+slot/8
                rk.put(f'e{slot}.g',g,lo=lo,n=2304)
                rk.put(f'e{slot}.u',g[::-1],lo=lo,n=2304)
            for slot in order:ex.f_swiglu(rk,dict(slot=slot))
            states.append(rk)
        assert np.array_equal(states[0].mem['ea'].view(np.uint32),states[1].mem['ea'].view(np.uint32))
        assert np.array_equal(states[0].ok['ea'],states[1].ok['ea'])


def test_original_executor_sum_keeps_cancellation_order():
    ex=ISA.Executor.__new__(ISA.Executor);ex.m=SimpleNamespace(k_exp=6)
    # (2^24 + -2^24) + 1 = 1, while (2^24 + 1) + -2^24 = 0.
    values=[2**24,-2**24,1,0,0,0,0]
    for r in range(96):
        rk=ISA.Rank(r);lo,hi=ISA.even(5120)[r]
        for slot in [6,0,1,2,3,4,5]:
            rk.put(f'e{slot}.d',np.full(hi-lo,values[slot],np.float32),lo=lo,n=5120)
        ex.f_moe_sum(rk,{})
        assert np.all(rk.get('yf',lo,hi)==1)


def test_merge_audit_finds_no_safe_merges_in_real_program(program):
    audit=merge_audit(program)
    assert audit['opportunities']==[]
    assert audit['removed_collectives']==0
    assert all(row['intervening_ops']>0 or row['first_kind']!=row['second_kind']
               for row in audit['boundaries'])


def test_replication_prices_distinct_candidate_inputs():
    cost=selector_cost(6,6)
    assert cost['candidate_storage_bytes_total']==6*96*512*8
    assert cost['aggregate_load_bytes_per_cycle_if_independent']==384
    assert cost['minimum_load_cycles_per_position']==6144
    assert cost['routing_tracks_required'] is None
    assert cost['placement_lower_bound_mm2_at_util_07']>cost['incremental_candidate_cell_area_mm2']


def test_executor_adapter_preserves_original_gather_split_boundary(program):
    class Consumer:
        def __init__(self):self.events=[]
        def run(self,ops):self.events.append(('run',ops))
        def split_ea(self):self.events.append(('split',None))
    consumer=Consumer()
    execute_layer(consumer,program['layers'][0]['ops'],True)
    assert [x[0] for x in consumer.events]==['run','split','run']
    assert consumer.events[0][1][-1]['tag']=='expert_intermediate_gather'
    assert consumer.events[2][1][0]['w']==[6,'w2']
    assert sum(len(x[1]) for x in consumer.events if x[0]=='run')==len(program['layers'][0]['ops'])
    head=Consumer();execute_layer(head,program['layers'][-1]['ops'],True)
    assert head.events==[('run',program['layers'][-1]['ops'])]
