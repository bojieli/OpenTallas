"""Do not promote partial checkpoint or analytical pricing to physical readiness."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_rom_completion_gate import assess


def inputs():
    exact = dict(completed_stages=[f'L{i}' for i in range(30)], checks={str(i): {} for i in range(120)},
                 full_token_exact_at_runtime_scope=False, current_source_joined=False)
    preflight = dict(missing_arithmetic_paths={'MUL_LAT': ['die_declared']})
    baseline = dict(selected_arithmetic_extra=54, program_sha256='a', body_plus_kv_prep_cycles=1000)
    successor = dict(selected_arithmetic_extra=55, program_sha256='a', body_plus_kv_prep_cycles=1217, model_price_joined=True)
    return exact, preflight, baseline, successor


def test_partial_exact_and_analytical_pass_cannot_enable_build():
    r = assess(*inputs(), True)
    assert r['analytical_successor_ready'] and r['exact_vector_count'] == 120
    assert r['missing_stages'] == [f'L{i}' for i in range(30, 36)] + ['head']
    assert not r['whole_36_layer_head_completion']
    assert not r['measured_plus55_latency_ready'] and not r['physical_build_ready'] and not r['adoption']


def test_model_program_mismatch_or_wrong_price_fails_analytical_join():
    for field, value in [('program_sha256', 'b'), ('selected_arithmetic_extra', 54), ('body_plus_kv_prep_cycles', 1216)]:
        args = copy.deepcopy(inputs())
        args[3][field] = value
        assert not assess(*args, True)['analytical_successor_ready']


def test_terminal_and_parameter_propagation_still_require_physical_models():
    args = inputs()
    args[0].update(completed_stages=[f'L{i}' for i in range(36)] + ['head'], full_token_exact_at_runtime_scope=True, current_source_joined=True)
    args[1]['missing_arithmetic_paths'] = {}
    r = assess(*args, False)
    assert r['whole_36_layer_head_completion'] and not r['missing_stages']
    assert not r['successor_record_generator_current'] and not r['physical_build_ready']
    assert all(not g['ready'] for g in r['gates'] if g['id'] in ('macro_local_kv', 'unified_physical_sizing', 'connected_measured_latency', 'element_context_ss_ff', 'spine_collective_die'))
