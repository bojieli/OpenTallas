import pytest
from tools.w17_crom_warm_residency import build,valid_hit

@pytest.fixture(scope='module')
def record():return build()

def test_all_command_mapping_actual_values_and_extra_product(record):
    assert record['actual491command_logical_hits']==549760
    assert len(record['stages'])==41
    for v in record['retained_value_checks']:
        assert v['actual_retained_FP32_value_checks']==529280 and v['invalid_L1_words']==20480
    for s in record['stages']:
        assert s['gamma_and_other_capacity_pass']
        if s['layer'] in (1,14):assert s['extra_persistent_product_bits']==655360
    assert not record['hardware_admission'] and record['warm_tokens']['actual_warm_cycles'] is None

def test_capacity_does_not_prove_localports(record):
    normal=next(s for s in record['stages'] if s['layer']==0)
    assert normal['other_words']==2288 and normal['crosslane_other_delivery_edges']>0
    assert normal['regular_lane_local_other_depth_words']==17
    indexed=next(s for s in record['stages'] if s['layer']==2)
    assert indexed['regular_lane_local_other_depth_words']==19
    assert normal['actual_other_cache_ports_per_lane'] is None

def test_reset_image_lease_and_init_not_free():
    key=('image','rank','stage','generation','layout')
    assert valid_hit(key,key,True,True,True,True)
    for i in range(4):
        for x in (None,False,1,'X'):
            state=[True]*4;state[i]=x
            assert not valid_hit(key,key,*state)
    assert not valid_hit(key,('changed-image',),True,True,True,True)


def test_topologies_not_transferred_to_actual_replay(record):
    t=record['topology_cases']
    assert t['stage_local_candidate']['proposed_SU_owner_count']==164
    assert len(t['stage_local_candidate']['absolute_owner_keys'])==164
    assert t['stage_local_candidate']['aggregate164_SU_core_reserved_mm2']=='1960.784'
    assert t['stage_local_candidate']['actual_product_SU_instances_and_home_topology'] is None
    assert t['fourrank_sequential_SU']['extra_allstage_bits_per_rank']==(549760-14336)*32
    assert record['warm_tokens']['actual_RTL_cache_module'] is None
    assert not record['warm_tokens']['live_L0_L20_warm_hit_credit']
    assert record['cold_init']['actual_TTFT'] is None
