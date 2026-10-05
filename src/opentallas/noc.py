"""Cycle-approximate hierarchical collective and placement simulator.

The model deliberately operates at the architectural level: it simulates the
serialization, router, and wire cycles on a deterministic broadcast/reduction
tree. It is not a sign-off interconnect model and does not invent physical wire
lengths that require a floorplan/PDK.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from .schema import WaferCommunicationProfile


@dataclass(frozen=True)
class NoCConfig:
    reticle_rows: int = 8
    reticle_cols: int = 8
    tiles_per_reticle: int = 64
    local_topology: str = "exchange"
    frequency_hz: float = 1.0e9
    local_link_bytes_per_cycle: int = 128
    mesh_link_bytes_per_cycle: int = 256
    router_cycles: int = 2
    local_wire_cycles: int = 1
    mesh_wire_cycles: int = 1

    def __post_init__(self) -> None:
        if self.local_topology not in {"exchange", "mesh"}:
            raise ValueError("local_topology must be exchange or mesh")
        for name in (
            "reticle_rows",
            "reticle_cols",
            "tiles_per_reticle",
            "frequency_hz",
            "local_link_bytes_per_cycle",
            "mesh_link_bytes_per_cycle",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class CollectiveResult:
    broadcast_cycles: int
    reduction_cycles: int
    collective_cycles: int
    collective_latency_s: float
    serialization_lower_bound_cycles: int
    local_depth: int
    wafer_mesh_depth: int
    tiles_total: int
    critical_link_utilization: float

    def to_dict(self) -> dict:
        return asdict(self)


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


def collective(config: NoCConfig, activation_bytes: int, partial_sum_bytes: int) -> CollectiveResult:
    """Simulate one static activation broadcast followed by a reduction."""

    if activation_bytes <= 0 or partial_sum_bytes <= 0:
        raise ValueError("collective payloads must be positive")
    mesh_depth = (config.reticle_rows - 1) + (config.reticle_cols - 1)
    if config.local_topology == "exchange":
        # A nonblocking local exchange broadcasts in one network traversal; a
        # deterministic reduction tree needs log2 fan-in stages.
        local_broadcast_depth = 1
        local_reduce_depth = math.ceil(math.log2(config.tiles_per_reticle))
    else:
        side = math.ceil(math.sqrt(config.tiles_per_reticle))
        local_broadcast_depth = 2 * (side - 1)
        local_reduce_depth = local_broadcast_depth

    broadcast_serial_local = _ceil_div(activation_bytes, config.local_link_bytes_per_cycle)
    broadcast_serial_mesh = _ceil_div(activation_bytes, config.mesh_link_bytes_per_cycle)
    reduction_serial_local = _ceil_div(partial_sum_bytes, config.local_link_bytes_per_cycle)
    reduction_serial_mesh = _ceil_div(partial_sum_bytes, config.mesh_link_bytes_per_cycle)
    local_hop = config.router_cycles + config.local_wire_cycles
    mesh_hop = config.router_cycles + config.mesh_wire_cycles
    broadcast_cycles = (
        max(broadcast_serial_local, broadcast_serial_mesh)
        + local_broadcast_depth * local_hop
        + mesh_depth * mesh_hop
    )
    reduction_cycles = (
        max(reduction_serial_local, reduction_serial_mesh)
        + local_reduce_depth * local_hop
        + mesh_depth * mesh_hop
    )
    lower_bound = (
        _ceil_div(activation_bytes, config.mesh_link_bytes_per_cycle)
        + _ceil_div(partial_sum_bytes, config.mesh_link_bytes_per_cycle)
    )
    total = broadcast_cycles + reduction_cycles
    return CollectiveResult(
        broadcast_cycles=broadcast_cycles,
        reduction_cycles=reduction_cycles,
        collective_cycles=total,
        collective_latency_s=total / config.frequency_hz,
        serialization_lower_bound_cycles=lower_bound,
        local_depth=max(local_broadcast_depth, local_reduce_depth),
        wafer_mesh_depth=mesh_depth,
        tiles_total=config.reticle_rows * config.reticle_cols * config.tiles_per_reticle,
        critical_link_utilization=lower_bound / total,
    )


@dataclass(frozen=True)
class SpatialAllReduceResult:
    """Batch service time for one distributed reduction and result fan-out.

    This is a physical lower-bound style model, not a claim that an arbitrary
    mapping attains bisection bandwidth.  It charges both traversal directions,
    endpoint/barrier work, and the critical-cut serialization for the actual
    batch payload.  Architecture efficiency/imbalance derates remain separate in
    the analytical simulator.
    """

    topology: str
    global_path_hops: int
    local_path_hops: int
    propagation_cycles_per_direction: float
    critical_cut_payload_bytes_per_cycle: float
    reduction_payload_bytes: float
    result_payload_bytes: float
    reduction_serialization_cycles: int
    result_serialization_cycles: int
    event_cycles: float
    event_latency_s: float
    allreduce_events_per_layer: int
    layer_service_time_s: float

    def to_dict(self) -> dict:
        return asdict(self)


def spatial_allreduce(
    config: WaferCommunicationProfile,
    *,
    elements: int,
) -> SpatialAllReduceResult:
    """Derive one layer's communication from topology and tensor elements.

    ``elements`` is the number of hidden-state elements in the whole active
    microbatch.  DeepSeek converts row-parallel partial sums to FP32 before each
    all-reduce, then returns BF16 activations; those byte widths are configuration
    inputs so another exact implementation can be represented without changing
    the equation.
    """

    if elements <= 0:
        raise ValueError("all-reduce elements must be positive")
    global_hops = (config.rows - 1) + (config.cols - 1)
    propagation = (
        global_hops * config.hop_cycles
        + config.local_path_hops * config.local_hop_cycles
    )
    cut_bytes_per_cycle = (
        config.bisection_links
        * config.link_payload_bytes_per_cycle
        * config.payload_efficiency
    )
    reduction_bytes = elements * config.reduction_bytes_per_element
    result_bytes = elements * config.result_bytes_per_element
    reduction_serial = math.ceil(reduction_bytes / cut_bytes_per_cycle)
    result_serial = math.ceil(result_bytes / cut_bytes_per_cycle)
    event_cycles = (
        2 * propagation
        + reduction_serial
        + result_serial
        + 2 * config.endpoint_cycles
        + config.barrier_cycles
    )
    event_s = event_cycles / config.frequency_hz
    return SpatialAllReduceResult(
        topology=config.topology,
        global_path_hops=global_hops,
        local_path_hops=config.local_path_hops,
        propagation_cycles_per_direction=propagation,
        critical_cut_payload_bytes_per_cycle=cut_bytes_per_cycle,
        reduction_payload_bytes=reduction_bytes,
        result_payload_bytes=result_bytes,
        reduction_serialization_cycles=reduction_serial,
        result_serialization_cycles=result_serial,
        event_cycles=event_cycles,
        event_latency_s=event_s,
        allreduce_events_per_layer=config.allreduce_events_per_layer,
        layer_service_time_s=event_s * config.allreduce_events_per_layer,
    )


@dataclass(frozen=True)
class PlacementResult:
    placement: str
    active_tile_fraction: float
    weight_stream_cycles: int
    compute_cycles: int
    service_cycles: int
    imbalance_multiplier: float

    def to_dict(self) -> dict:
        return asdict(self)


def placement_service(
    *,
    placement: str,
    total_tiles: int,
    num_layers: int,
    weight_bytes: float,
    operations: float,
    rom_bytes_per_tile_cycle: float,
    ops_per_tile_cycle: float,
    trace_load_balance_efficiency: float = 1.0,
) -> PlacementResult:
    """Compare interleaved versus layer/expert-local tile engagement."""

    if placement not in {"interleaved", "layer_local", "expert_local"}:
        raise ValueError("unsupported placement")
    if placement == "interleaved":
        active_fraction = 1.0
        imbalance = 1.0
    elif placement == "layer_local":
        active_fraction = min(1.0, 1.0 / num_layers)
        imbalance = 1.0
    else:
        active_fraction = min(1.0, 1.0 / num_layers)
        imbalance = 1.0 / max(trace_load_balance_efficiency, 1e-6)
    active_tiles = max(1.0, total_tiles * active_fraction)
    weight_cycles = math.ceil(weight_bytes / (active_tiles * rom_bytes_per_tile_cycle))
    compute_cycles = math.ceil(operations / (active_tiles * ops_per_tile_cycle))
    service = math.ceil(max(weight_cycles, compute_cycles) * imbalance)
    return PlacementResult(
        placement=placement,
        active_tile_fraction=active_fraction,
        weight_stream_cycles=weight_cycles,
        compute_cycles=compute_cycles,
        service_cycles=service,
        imbalance_multiplier=imbalance,
    )
