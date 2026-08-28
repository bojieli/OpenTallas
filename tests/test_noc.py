from __future__ import annotations

import pytest

from opentallas.noc import (
    NoCConfig,
    collective,
    placement_service,
    spatial_allreduce,
)
from opentallas.schema import WaferCommunicationProfile


def test_collective_is_above_serialization_lower_bound() -> None:
    result = collective(NoCConfig(), activation_bytes=8192, partial_sum_bytes=16384)
    assert result.collective_cycles >= result.serialization_lower_bound_cycles
    assert 0 < result.critical_link_utilization <= 1


def test_collective_grows_with_payload_and_wire_delay() -> None:
    base = collective(NoCConfig(mesh_wire_cycles=1), 8192, 16384)
    batch = collective(NoCConfig(mesh_wire_cycles=1), 8 * 8192, 8 * 16384)
    slow_wire = collective(NoCConfig(mesh_wire_cycles=4), 8192, 16384)
    assert batch.collective_cycles > base.collective_cycles
    assert slow_wire.collective_cycles > base.collective_cycles


def test_interleaving_engages_more_tiles_and_reduces_service_time() -> None:
    common = dict(
        total_tiles=4096,
        num_layers=64,
        weight_bytes=1e11,
        operations=1e11,
        rom_bytes_per_tile_cycle=256,
        ops_per_tile_cycle=4096,
        trace_load_balance_efficiency=0.1,
    )
    interleaved = placement_service(placement="interleaved", **common)
    local = placement_service(placement="layer_local", **common)
    expert = placement_service(placement="expert_local", **common)
    assert interleaved.active_tile_fraction == 1
    assert interleaved.service_cycles < local.service_cycles < expert.service_cycles


def test_spatial_allreduce_separates_propagation_and_serialization() -> None:
    profile = WaferCommunicationProfile(
        topology="nearest_neighbor_mesh",
        rows=950,
        cols=950,
        frequency_hz=1e9,
        link_payload_bytes_per_cycle=2,
        hop_cycles=1,
        bisection_links=950,
        payload_efficiency=0.5,
        allreduce_events_per_layer=2,
    )
    one = spatial_allreduce(profile, elements=8192)
    eight = spatial_allreduce(profile, elements=8 * 8192)
    assert one.global_path_hops == 1898
    assert one.propagation_cycles_per_direction == pytest.approx(1898)
    assert one.reduction_payload_bytes == 8192 * 4
    assert one.result_payload_bytes == 8192 * 2
    assert one.layer_service_time_s == pytest.approx(2 * one.event_latency_s)
    assert eight.event_cycles > one.event_cycles


def test_wider_bisection_reduces_only_serialization_term() -> None:
    narrow = WaferCommunicationProfile(
        topology="hierarchical_mesh",
        rows=64,
        cols=64,
        frequency_hz=1e9,
        link_payload_bytes_per_cycle=16,
        hop_cycles=2,
        bisection_links=16,
    )
    wide = WaferCommunicationProfile(
        **{
            **narrow.__dict__,
            "bisection_links": 64,
        }
    )
    narrow_result = spatial_allreduce(narrow, elements=64 * 8192)
    wide_result = spatial_allreduce(wide, elements=64 * 8192)
    assert (
        narrow_result.propagation_cycles_per_direction
        == wide_result.propagation_cycles_per_direction
    )
    assert narrow_result.event_cycles > wide_result.event_cycles
