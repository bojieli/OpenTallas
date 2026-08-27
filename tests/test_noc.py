from __future__ import annotations

from opentallas.noc import NoCConfig, collective, placement_service


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
