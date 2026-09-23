import pytest
from tools.audit_v41_expert_striping import service


def test_striping_trades_reads_for_return_traffic():
    a,b=service(1),service(4)
    assert b['expert_weight_read_us']==a['expert_weight_read_us']/4
    assert b['fp32_partial_return_bytes_per_layer']==a['fp32_partial_return_bytes_per_layer']*4
    assert b['active_chips_for_six_disjoint_experts']==24


def test_more_shards_can_be_slower():
    assert service(4)['nonoverlapped_read_plus_fabric_us'] < service(2)['nonoverlapped_read_plus_fabric_us']
    assert service(16)['nonoverlapped_read_plus_fabric_us'] > service(4)['nonoverlapped_read_plus_fabric_us']


def test_multicast_does_not_erase_return_cost():
    a,b=service(4),service(4,multicast=True)
    assert a['fp32_partial_return_bytes_per_layer']==b['fp32_partial_return_bytes_per_layer']
    assert b['dispatch_bytes_per_layer']==10240
    assert b['optimistic_read_fabric_overlap_floor_us'] <= b['nonoverlapped_read_plus_fabric_us']


def test_faster_local_service_can_favor_fewer_shards():
    assert service(1,72)['nonoverlapped_read_plus_fabric_us'] < service(4,72)['nonoverlapped_read_plus_fabric_us']


def test_native_intermediate_partition_must_be_integral():
    with pytest.raises(ValueError): service(7)
