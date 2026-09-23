import pytest
from tools.audit_v41_fabric_feasibility import payload, fabric_us


def test_expert_payload_does_not_include_local_weights_or_residual_copies():
    p = payload()
    assert p['endpoint_bytes_per_layer'] == 122880
    assert p['endpoint_bytes_per_token'] == 4915200


def test_multicast_saves_source_injection_not_leaf_delivery():
    a,b = payload(),payload(multicast=True)
    assert a['leaf_delivered_bytes_per_layer'] == b['leaf_delivered_bytes_per_layer']
    assert b['endpoint_bytes_per_layer'] == 71680


def test_serial_latency_is_not_hidden_by_high_bandwidth():
    assert fabric_us(122880,40,.5,400) == pytest.approx(52.288)
    assert fabric_us(122880,40,2,1e9) > 160


def test_return_precision_is_charged():
    assert payload(output_bytes=4)['endpoint_bytes_per_layer'] == 184320
