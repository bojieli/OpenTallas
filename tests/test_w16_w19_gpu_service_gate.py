import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w16_w19_gpu_service_gate as G


def test_working_set_is_arithmetic_not_fit():
    result = G.residency_arithmetic({'coefficients':1966080, 'activations':40960, 'scalar':82688}, 32, 65536)
    assert result['sum_bytes'] == 2089728
    assert result['remaining_bytes_arithmetic'] == 7424
    assert result['ideal_even_split_bytes_per_sm'] == 65304
    assert not result['fit']
    assert result['actual_liveness'] is None


@pytest.mark.parametrize('sizes', [{}, {'unknown':None}, {'zero':0}, {'bool':True}])
def test_unknown_workspace_refused(sizes):
    with pytest.raises(G.B.Refusal):
        G.residency_arithmetic(sizes, 32, 65536)


def test_copy_replication_is_explicit():
    assert [G.copy_port_arithmetic(1966080, n) for n in (1,4,16)] == [15360,3840,960]
    with pytest.raises(G.B.Refusal):
        G.copy_port_arithmetic(1966080, 0)


def test_missing_gpu_schedule_refused():
    with pytest.raises(G.B.Refusal):
        G.require_gpu_schedule({'dedicated_HCP':False})
    result = G.build()
    with pytest.raises(G.B.Refusal):
        G.require_gpu_schedule(result['required_gpu_schedule'])
    assert result['allocation']['max_stack_bytes'] == 3175215616
    assert result['unified_work']['HC_operators'] == 80
    assert result['GPU_budget']['modeled_SIMT_lanes_per_die'] == 4096
    assert result['candidate_composed_latency_us'] is None
    assert result['candidate_rate'] is None
    assert not result['model_ready_to_build'] and not result['hardware_adopted']


def test_roundtrip_and_current_scope_drift():
    result = json.loads(json.dumps(G.build()))
    G.check(result)
    result['pins'][G.SCOPE] = '0' * 64
    with pytest.raises(G.B.Refusal, match='pin drift'):
        G.check(result)
