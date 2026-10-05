import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_hbm_finite_service_join as H

def test_actual_stack_maximum_not_balanced_mean():
    r=H.build()
    assert len(r['writers'])==144
    assert all(w['mixed_command_floor_cycles']==144 for w in r['writers'])
    assert all(w['mean_command_count_per_stack']==132 for w in r['writers'])
    assert r['total_packed_KV_port_bytes']==2433024
    assert r['total_packed_KV_mixed_commands']==76032
    assert r['lock_context_allocation']['contexts_per_quad']==16
    assert r['lock_context_allocation']['contexts_per_quad']*4==64
    assert not r['hardware_build_ready'] and r['full_token_ticks'] is None

def test_ordinary_instruction_and_visibility_edges_fail_closed():
    r=H.build()
    assert r['ordinary_GPU_cost_basis']['candidate_latencies']['INT_ADD_FCMP']['RF_to_writeback']==9
    assert r['ordinary_GPU_cost_basis']['candidate_latencies']['SHFL']['RF_to_writeback']==7
    assert r['lock_scenario']['total_ticks']==4431
    assert all(w['finite_instruction_and_visibility_events'] is None for w in r['writers'])
    assert 'backend_WRvisible' in r['obligatory_resource_edges']
