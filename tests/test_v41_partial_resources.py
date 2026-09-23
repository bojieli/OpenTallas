"""Finite service and schedule evidence are separate feasibility requirements."""
import pytest
from tools.audit_v41_partial_resources import screen, batch_schedule


def test_inventory_reconciles_packed_scales_and_partial_traffic():
    r = screen(524288, 16384, 1024)
    assert sum(p['macs'] for p in r['phases']) == 212336640
    assert sum(p['partials'] for p in r['phases']) == 6635520
    assert sum(p['packed_weight_bytes'] for p in r['phases']) == 112803840
    assert sum(p['partial_materialization_bytes'] for p in r['phases']) == 26542080


def test_more_compute_cannot_remove_rom_limit():
    r = screen(524288, 16384, 678)
    assert 999 < r['necessary_layer_cycles'] < 1000
    assert screen(1048576, 32768, 678)['necessary_layer_cycles'] == r['necessary_layer_cycles']


def test_ordered_add_capacity_is_independent_constraint():
    assert screen(524288, 4096, 1024)['necessary_layer_cycles'] > 1000
    assert screen(524288, 16384, 1024)['necessary_layer_cycles'] < 1000


def test_explicit_barrier_schedule_does_not_claim_average_service_rate():
    r = batch_schedule(2048)
    assert r['peak_partial_engines'] == 327680
    assert r['layer_cycles'] == 4248
    assert batch_schedule(32768, 3)['layer_cycles'] == 888


def test_invalid_resources_rejected():
    with pytest.raises(ValueError):
        screen(0, 16384, 678)
