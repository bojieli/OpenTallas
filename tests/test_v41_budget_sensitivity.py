import pytest
from tools.audit_v41_budget_sensitivity import inventory, rates


def test_three_matrices_six_selected_experts_and_row_scales():
    r = inventory(5120, 2304, 6, 40)
    assert r['bytes_per_expert'] == 18800640
    assert r['routed_bytes_per_token'] == 4512153600
    assert r['routed_ops_per_token'] == 16986931200
    assert r['e8m0_scale_bytes_per_expert'] * 16 == r['fp4_payload_bytes_per_expert']


def test_bandwidth_is_conditional_on_expert_budget():
    r = inventory(5120, 2304, 6, 40)
    assert rates(r, 40)['aggregate_local_weight_TB_s'] == pytest.approx(112.80384)
    assert rates(r, 1000)['aggregate_local_weight_TB_s'] == pytest.approx(4.5121536)
    assert rates(r, 100)['aggregate_local_weight_TB_s'] / rates(r, 1000)['aggregate_local_weight_TB_s'] == pytest.approx(10)
