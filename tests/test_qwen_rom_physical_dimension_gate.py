import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_physical_dimension_gate import size,generate


def test_tp4_8k_capacity_does_not_imply_all_layer_residence():
 r=size()
 assert r['local_words_per_tile']==44 and r['one_window_fits']
 assert r['useful_window_bytes_per_layer_die']==4*1024*1024
 assert r['useful_all_layer_bytes_per_die']==144*1024*1024
 assert r['local_macro_capacity_bytes_per_die']==12*1024*1024
 assert not r['all_layer_capacity_lower_bound_fits'] and not r['physical_build_ready']


def test_reload_lower_bound_is_conditional_not_a_context_zero_timing_claim():
 r=size()
 assert r['ideal_64B_fill_beats_per_layer']==65536
 assert r['ideal_fill_lanes_to_match_observed_layer_reference']==15
 assert r['ideal_data_bytes_per_cycle_at_that_lane_count']==960
 assert r['warm_update_bytes_per_token_die']==18432
 assert r['actual_tile_fill_port_bits_per_lane']==1032
 assert r['candidate_addressed_fill_payload_bits_per_lane']==1048
 assert not r['fill_transport_selected']
 assert r['candidate_addressed_payload_bits_per_cycle_at_that_lane_count']==15720
 assert 'not predict an 8K' in r['cycle_reference_scope']
 assert 'not assumed absent' in r['latency_scope']


def test_window_capacity_bound_and_tp_scaling():
 assert size(context=16384)['one_window_fits']
 assert not size(context=32768)['one_window_fits']
 assert size(tp=2)['useful_window_bytes_per_layer_die']==2*size()['useful_window_bytes_per_layer_die']


def test_macro_inventory_has_no_logic_or_physical_credit():
 r=generate()
 assert r['macro_count_per_die']=={'ROM':15360,'KV_SRAM':3072}
 assert r['macro_area_lower_bound_mm2_per_die']>100
 assert r['slot_fit'] is None and r['track_demand'] is None
 assert not r['physical_build_ready'] and not r['adoption']


@pytest.mark.parametrize('kw',[{'context':0},{'context':8191},{'groups':6143},{'groups':4},{'tp':3}])
def test_invalid_geometry_cannot_be_sized(kw):
 with pytest.raises(ValueError):size(**kw)
