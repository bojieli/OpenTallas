import pytest
from tools.audit_v41_layer_local_arrays import layer_placement, expert_read_floor


def test_layer_dense_data_changes_two_chip_capacity_fit():
    payload=400*9379500*.98
    assert 384*18800640 < 2*payload
    assert layer_placement(170055128,384,18800640,payload)['chips']==3
    assert layer_placement(170055128,384,18800640,500*9379500*.98)['chips']==2


def test_inactive_expert_chips_do_not_improve_best_case_past_six():
    assert expert_read_floor(6)['expert_only_read_floor_us_best_route']==pytest.approx(167.1168)
    assert expert_read_floor(84)['expert_only_read_floor_us_best_route']==expert_read_floor(6)['expert_only_read_floor_us_best_route']


def test_concentrated_routes_are_bounded_by_experts_on_one_chip():
    assert expert_read_floor(84)['worst_max_selected_experts_on_one_chip']==5
    assert expert_read_floor(384)['worst_max_selected_experts_on_one_chip']==1
    assert expert_read_floor(3)['expert_only_read_floor_us_concentrated_route']==pytest.approx(1002.7008)


def test_bandwidth_scaling_is_explicit():
    assert expert_read_floor(3,delivered_bytes_s=9e12)['expert_only_read_floor_us_best_route']==pytest.approx(167.1168)
