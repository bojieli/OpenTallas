import pytest
from tools.audit_v41_speedup_conditions import expert_only_speedup, common_budget_ratio


def test_expert_only_acceleration_cannot_speed_unchanged_dense_service():
    dense, routed = 8522921408, 4512153600
    assert expert_only_speedup(dense, routed, 1) == 1
    assert expert_only_speedup(dense, routed, 10) == pytest.approx(1.4525157511)
    assert expert_only_speedup(dense, routed, 1e9) < 1.53


def test_common_work_budget_actually_reaches_target():
    for r in (3, 4, 5, 10, 100):
        c = common_budget_ratio(r)
        assert (1+c)/(1/r+c) == pytest.approx(3)
    assert common_budget_ratio(2) < 0


def test_no_dense_external_reads_does_not_limit_expert_service_speedup():
    assert expert_only_speedup(0, 4512153600, 10) == pytest.approx(10)
