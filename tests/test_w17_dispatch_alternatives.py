import importlib.util,itertools,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('dispatch_alternatives',ROOT/'tools/w17_dispatch_alternatives.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.fixture(scope='module')
def model():return m.build()
def test_actual_resident_capacity_limits_worst_selection():
    stages=[(0,4,1),(1,1,2),(2,3,3)]
    cost=lambda d,k: (400+80*k)*d
    actual,trace=m.worst_selection(stages,cost,6)
    possible=[]
    for takes in itertools.product(range(5),range(2),range(4)):
        if sum(takes)==6:possible.append(sum(cost(s[2],k) for s,k in zip(stages,takes) if k))
    assert actual==max(possible)
    assert sum(k for _,k,_ in trace)==6
    assert all(k<=dict((s,n) for s,n,_ in stages)[sid] for sid,k,_ in trace)
def test_width_costs_add_to_occupied_corridor(model):
    rows=model['candidates']
    assert all(not r['tracks']['single_existing_corridor_fits'] for r in rows)
    a=next(r for r in rows if r['link_bits_per_rank_source_cycle']==1024 and r['policy']=='compact_stage_activation_reuse')
    assert a['tracks']['additional_corridors']==2
    assert a['tracks']['total']==832+2*(1024+64)
    assert a['credits']['landing_bits']>=2*(5120*16+6*256+1280*16+256)
def test_group_reuse_pays_same_order_results_and_local_owners(model):
    for width in (256,512,1024,2048):
        by={r['policy']:r for r in model['candidates'] if r['link_bits_per_rank_source_cycle']==width}
        assert by['compact_stage_activation_reuse']['source_order_worst_six_distinct_expert_partial_transport_ticks']<by['compact_per_expert_activation']['source_order_worst_six_distinct_expert_partial_transport_ticks']
        assert by['central_expanded_config']['source_order_worst_six_distinct_expert_partial_transport_ticks']>by['compact_per_expert_activation']['source_order_worst_six_distinct_expert_partial_transport_ticks']
        for r in by.values():
            assert r['local_owner']['expert_stage_slot_table_replicas']==724
            assert all(sum(k for _,k,_ in t['selected_stage_counts'])==6 for t in r['layer_worst_selections'])
            assert not r['adopt']
def test_partial_calendar_preserves_admission_gates(model):
    assert model['baseline_preserved']['expert_dispatch_serialization_us']==440
    assert model['route_model']['registered_route_cycles_per_hop']==75
    assert model['CDC_model']['fast_to_slow_ticks']==16
    assert model['CDC_model']['slow_to_fast_ticks']==15
    assert sum(model['frame_proposal']['fields_bits'].values())<=model['frame_proposal']['bits']
    assert not model['accepted_performance'] and not model['engine_RTL_build_ready']
