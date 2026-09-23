import pytest
from tools.audit_v41_array_mapping import mapping


def point(depth):
    return mapping(80,4,depth,4595955000,[170055128]*40,18800640)


def test_small_stage_cannot_claim_six_disjoint_islands():
    assert point(1) is None
    r=point(2)
    assert r['expert_islands_per_stage']==1
    assert not r['six_disjoint_selected_islands_possible']
    assert r['expert_read_us_best_route']==pytest.approx(250.6752)


def test_layer_sharing_changes_reachable_active_islands():
    assert point(20)['six_disjoint_selected_islands_possible']
    assert point(20)['expert_read_us_best_route']==pytest.approx(41.7792)
    assert point(20)['expert_read_us_worst_route']==pytest.approx(250.6752)


def test_capacity_is_checked_at_peak_chip_not_only_aggregate():
    r=point(40)
    assert r['used_backbone_chips']<=80
    assert r['backbone_capacity_fits']
    r=mapping(80,4,40,1000000,[170055128]*40,18800640)
    assert not r['backbone_capacity_fits']


def test_layers_cannot_be_fractionally_assigned_to_stages():
    with pytest.raises(ValueError): point(3)
