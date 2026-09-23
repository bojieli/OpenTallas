"""Route concentration bounds must not credit inactive groups or free reuse."""
import pytest
from tools.audit_v41_expert_groups import group_bound


def bound(size, users=1, experts=384):
    return group_bound(experts, 6, 18800640, size, users)


def test_distinct_experts_limit_one_user_concentration():
    assert bound(2)['max_expert_jobs_per_group'] == 2
    assert bound(64)['max_expert_jobs_per_group'] == 6
    assert bound(64)['max_group_ports_required'] == 678
    assert bound(1)['max_group_ports_required'] == 113


def test_partial_last_group_is_charged_at_its_actual_size():
    result = bound(6, experts=8)
    assert result['groups_per_layer'] == 2
    assert result['installed_ports_per_layer_for_arbitrary_routes'] == 678 + 226


def test_concentrated_users_do_not_receive_free_weight_reuse():
    assert bound(16, 4)['max_expert_jobs_per_group'] == 24
    assert bound(16, 4)['max_group_weight_TB_s_required'] == 4 * bound(16)['max_group_weight_TB_s_required']


def test_pooling_reduces_installed_ports_but_increases_capacity_per_group():
    assert bound(384)['installed_ports_per_layer_for_arbitrary_routes'] < bound(16)['installed_ports_per_layer_for_arbitrary_routes']
    assert bound(384)['max_group_rom_bytes'] > bound(16)['max_group_rom_bytes']


def test_invalid_service_is_rejected():
    with pytest.raises(ValueError):
        group_bound(384, 6, 18800640, 16, delivery=0)
