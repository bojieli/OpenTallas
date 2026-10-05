"""LINK engine conformance: movement, collectives, permission and counters.

Every case builds a real ABI 3.0 deployment through :class:`DeploymentBuilder`,
admits it through the independent verifier and executes it on the functional
device.  Nothing calls an engine with hand-made Python state: if the descriptors
cannot express the case, the case is not executable on the device either.

Two topologies are exercised, because ADR-003 section 3.3 makes them
non-interchangeable: a two-node cluster for point-to-point movement and an
eight-node cluster for the collectives.  The traffic accounting is checked
against a real :class:`~runtime.cycle.fabric.ClusterFabric` and
:class:`~runtime.cycle.fabric.WaferFabric` rather than against a second copy of
the engine's formulas, so the functional model and the cycle model cannot drift
on what a message is.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    DType,
    Feature,
    Link,
    Major,
    NO_ID,
    NO_NODE,
    Permission,
    ReductionOrder,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import CollectiveOp, Phase
from runtime.cycle.fabric import ClusterFabric, WaferFabric
from runtime.cycle.machine import ClusterFabricParams, WaferFabricParams
from runtime.sim.device import Device
from runtime.sim.engines.link import barrier_messages, collective_traffic

# Importing the engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.link  # noqa: F401


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
REMOTE = int(Permission.READ | Permission.WRITE | Permission.REMOTE)
LOCAL = int(Permission.READ | Permission.WRITE)


def capability(nodes: int = 32) -> Capability:
    # Validate the real CLUSTER_32 profile first.  These functional engine
    # cases then specialize only its node cardinality so their intentionally
    # tiny two- and eight-node topologies can still exercise the independent
    # verifier's exact topology binding.  Production capability validation
    # continues to require all 32 nodes.
    profile_nodes = max(nodes, 32)
    cap = Capability(
        capability_id="",
        topology_class=int(TopologyClass.CLUSTER_32),
        features=tuple(
            int(f)
            for f in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
                Feature.INTER_CHIP_ENDPOINT,
                Feature.INTEGRITY_RETRY,
            )
        ),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 16,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 4096,
            "max_expert_ids": 1024,
            "max_topk": 64,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": profile_nodes,
        },
        numeric_contracts=("bf16_add_rne_v1",),
        engines={"link": {"queues": 1}, "dma": {"queues": 1}},
        memory={"sram": {"bytes": 1 << 24}},
        technology_view="engine-conformance",
    )
    cap.validate()
    cap.limits["max_nodes"] = nodes
    return cap


class Build:
    """A minimal single-transaction LINK deployment."""

    def __init__(self, *, nodes: int, local_node: int = 0, route_groups: int = 0):
        self.capability = capability(nodes)
        self.builder = DeploymentBuilder(
            target_id="link-test",
            model_id="link-test",
            backend="test",
            capability=self.capability,
        )
        self.builder.require(Feature.INTER_CHIP_ENDPOINT)
        self.builder.topology(
            topology_class=TopologyClass.CLUSTER_32,
            node_count=nodes,
            local_node_id=local_node,
            route_group_count=route_groups,
            link_count=nodes,
            hbm_bytes_per_node=1 << 24,
            sram_bytes_per_node=1 << 24,
        )
        self._initial: dict[int, bytes] = {}
        self._staged: list[tuple[int, int, int, bytes]] = []

    def object_of(self, values: np.ndarray, *, permissions: int = LOCAL) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self.scratch(len(data), permissions=permissions)
        self._initial[oid] = data
        return oid

    def scratch(self, nbytes: int, *, permissions: int = LOCAL) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=permissions,
        )

    def participants(
        self, slots: np.ndarray, members: Sequence[int] | None = None
    ) -> int:
        """A participant array whose slot ``k`` is staged in node ``k``'s arena.

        This is what makes these cases prove something.  The engine must reach
        the contribution where the contributing node actually holds it; an
        implementation that read every slot out of one arena would see slot
        zero and seven zeroed slots, and every assertion below would fail.
        """
        members = list(range(len(slots))) if members is None else list(members)
        oid = self.scratch(len(slots) * SLOT_BYTES, permissions=REMOTE)
        for index, node in enumerate(members):
            self._staged.append(
                (node, oid, index * SLOT_BYTES, np.ascontiguousarray(slots[index]).tobytes())
            )
        return oid

    def finish(self) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL
        )
        device = Device(self.builder.finish(), self.capability)
        for oid, data in self._initial.items():
            # A local endpoint is symmetric: the same object at the same offset
            # on every node, so initial content is staged on every node.
            device.host_write(oid, 0, data)
        for node, oid, offset, data in self._staged:
            device.node_memories[node][oid].write(offset, data)
        return device


def run(device: Device):
    return device.run_transaction(device.create_session(), entrypoint_id=0, symbols={})


def read_object(
    device: Device, oid: int, dtype, count: int, offset: int = 0, node: int = 0
):
    itemsize = np.dtype(dtype).itemsize
    return np.frombuffer(
        device.node_memories[node][oid].read(offset, count * itemsize), dtype=dtype
    ).copy()


def read_slots(device: Device, oid: int, count: int, members: Sequence[int]):
    """Slot ``k`` of the participant array, out of the arena that holds it."""
    return np.stack(
        [
            read_object(device, oid, np.float32, count, offset=index * SLOT_BYTES, node=node)
            for index, node in enumerate(members)
        ]
    )


def fp32_numeric(build: Build, order: ReductionOrder) -> int:
    return build.builder.numeric(
        contract="bf16_add_rne_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
        reduction_order=order,
    )


def cluster_fabric(nodes: int) -> ClusterFabric:
    return ClusterFabric(
        ClusterFabricParams(
            nodes=nodes,
            links_per_node=2,
            link_bytes_per_cycle=8.0,
            link_hop_latency_cycles=4,
            switch_latency_cycles=6,
            switch_levels=2,
            switch_radix=8,
            packet_bytes=256,
            packet_header_bytes=32,
            credits=8,
            credit_return_cycles=12,
            retry_interval_packets=4096,
            retry_cycles=20,
            barrier_round_cycles=5,
            endpoint_latency_cycles=10,
        )
    )


def wafer_fabric() -> WaferFabric:
    return WaferFabric(
        WaferFabricParams(
            reticle_rows=1,
            reticle_cols=1,
            tile_rows=2,
            tile_cols=4,
            tile_link_bytes_per_cycle=32.0,
            stitch_bytes_per_cycle=8.0,
            tile_hop_cycles=1,
            stitch_hop_cycles=4,
            router_latency_cycles=1,
            packet_bytes=256,
            packet_header_bytes=32,
            credits=16,
            credit_return_cycles=6,
            virtual_channels=2,
            barrier_level_cycles=3,
            endpoint_latency_cycles=6,
        )
    )


# ---------------------------------------------------------------------------
# point to point
# ---------------------------------------------------------------------------
def build_point_to_point(
    sub: Link,
    *,
    payload: np.ndarray,
    remote_permissions: int = REMOTE,
    byte_extent: int | None = None,
    remote_bytes: int | None = None,
    source_node: int = 0,
    destination_node: int = 1,
    credit_bound: int = 8,
    chunk_bytes: int = 4096,
):
    build = Build(nodes=2)
    nbytes = payload.nbytes
    if sub is Link.RECEIVE:
        local = build.scratch(nbytes)
        remote = build.object_of(payload, permissions=remote_permissions)
    else:
        local = build.object_of(payload)
        remote = build.scratch(
            remote_bytes if remote_bytes is not None else nbytes,
            permissions=remote_permissions,
        )
    comm = build.builder.communication(
        collective_op=CollectiveOp.POINT_TO_POINT,
        local_object_id=local,
        remote_object_id=remote,
        source_node=source_node,
        destination_node=destination_node,
        byte_extent=nbytes if byte_extent is None else byte_extent,
        participant_count=2,
        credit_bound=credit_bound,
        chunk_bytes=chunk_bytes,
    )
    build.builder.emit(Major.LINK, sub, descriptor_id=comm)
    return build, local, remote


def test_send_moves_bytes_and_reconciles_counters():
    payload = np.arange(64, dtype=np.uint32)
    build, _, remote = build_point_to_point(Link.SEND, payload=payload)
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read_object(device, remote, np.uint32, 64), payload)

    counters = result.counters
    assert counters["link.messages_sent"] == 1
    assert counters["link.messages_received"] == 1
    assert counters["link.bytes_sent"] == payload.nbytes
    assert counters["link.bytes_received"] == payload.nbytes
    assert counters["engine.link.descriptors"] == 1
    # A lossless functional fabric replays nothing and stalls on no credit.
    assert counters.get("link.retries", 0) == 0
    assert counters.get("link.credit_stalls", 0) == 0
    assert counters.get("link.remote_dma_bytes", 0) == 0
    # The movement is real memory traffic on both endpoints.
    assert counters["sram.bytes_read"] == payload.nbytes
    assert counters["sram.bytes_written"] == payload.nbytes


def test_receive_pulls_from_the_remote_endpoint():
    payload = np.arange(16, dtype=np.uint32) * 7
    build, local, _ = build_point_to_point(Link.RECEIVE, payload=payload)
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read_object(device, local, np.uint32, 16), payload)
    assert result.counters["link.bytes_received"] == payload.nbytes


def test_remote_dma_pushes_from_the_local_node_and_is_billed_separately():
    payload = np.arange(32, dtype=np.uint32)
    build, _, remote = build_point_to_point(
        Link.REMOTE_DMA, payload=payload, source_node=0, destination_node=1
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read_object(device, remote, np.uint32, 32), payload)
    assert result.counters["link.remote_dma_bytes"] == payload.nbytes
    assert result.counters["link.bytes_sent"] == payload.nbytes


def test_remote_dma_that_names_neither_local_endpoint_is_refused():
    payload = np.arange(8, dtype=np.uint32)
    build, _, _ = build_point_to_point(
        Link.REMOTE_DMA, payload=payload, source_node=1, destination_node=1
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "neither endpoint" in result.message


def test_a_remote_object_without_remote_permission_is_refused():
    payload = np.arange(8, dtype=np.uint32)
    build, _, _ = build_point_to_point(
        Link.SEND, payload=payload, remote_permissions=LOCAL
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "REMOTE permission" in result.message


def test_an_out_of_range_byte_extent_is_refused():
    payload = np.arange(8, dtype=np.uint32)
    build, _, _ = build_point_to_point(
        Link.SEND, payload=payload, byte_extent=payload.nbytes + 4
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "exceeds" in result.message


def test_a_transfer_larger_than_its_credit_window_is_a_credit_stall():
    payload = np.arange(64, dtype=np.uint32)  # 256 bytes
    build, _, _ = build_point_to_point(
        Link.SEND, payload=payload, credit_bound=2, chunk_bytes=32
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.SUCCESS, result.message
    # 256 / 32 = 8 chunks against a two-credit window.
    assert result.counters["link.credit_stalls"] == 1


# ---------------------------------------------------------------------------
# collectives over eight nodes
# ---------------------------------------------------------------------------
NODES = 8
SLOT = 4  # binary32 elements per participant slot
SLOT_BYTES = SLOT * 4


def build_collective(
    sub: Link,
    *,
    op: CollectiveOp,
    slots: np.ndarray | None,
    local: np.ndarray | None,
    local_slots: int,
    source_node: int = NO_NODE,
    destination_node: int = NO_NODE,
    reduction_order: ReductionOrder | None = None,
    nodes: int = NODES,
    participant_count: int | None = None,
    group_id: int = NO_ID,
    route_groups: int = 0,
    members: Sequence[int] | None = None,
):
    build = Build(nodes=nodes, route_groups=route_groups)
    remote_bytes = nodes * SLOT_BYTES if slots is None else slots.nbytes
    if slots is None:
        remote = build.scratch(remote_bytes, permissions=REMOTE)
    else:
        remote = build.participants(slots, members)
    if local is None:
        local_object = build.scratch(max(local_slots * SLOT_BYTES, 4))
    else:
        local_object = build.object_of(local)
    numeric = (
        NO_ID if reduction_order is None else fp32_numeric(build, reduction_order)
    )
    comm = build.builder.communication(
        collective_op=op,
        local_object_id=local_object,
        remote_object_id=remote,
        source_node=source_node,
        destination_node=destination_node,
        byte_extent=SLOT_BYTES,
        participant_count=nodes if participant_count is None else participant_count,
        group_id=group_id,
        reduction_numeric_id=numeric,
    )
    build.builder.emit(Major.LINK, sub, descriptor_id=comm)
    return build, local_object, remote


def test_multicast_reaches_every_participant_slot():
    source = np.arange(SLOT, dtype=np.float32) + 1.0
    build, _, remote = build_collective(
        Link.MULTICAST,
        op=CollectiveOp.BROADCAST,
        slots=None,
        local=source,
        local_slots=1,
        source_node=0,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # Every participant's slot carries the payload, and every participant's
    # slot is in that participant's own arena.
    arrived = read_slots(device, remote, SLOT, range(NODES))
    assert np.array_equal(arrived, np.broadcast_to(source, (NODES, SLOT)))
    messages, moved = collective_traffic(
        int(CollectiveOp.BROADCAST), NODES, SLOT_BYTES
    )
    assert result.counters["link.messages_sent"] == messages == NODES - 1
    assert result.counters["link.bytes_sent"] == moved


def test_gather_and_scatter_are_mirror_images():
    slots = (np.arange(NODES * SLOT, dtype=np.float32) + 1.0).reshape(NODES, SLOT)
    build, local, _ = build_collective(
        Link.GATHER,
        op=CollectiveOp.CONCAT,
        slots=slots,
        local=None,
        local_slots=NODES,
        destination_node=3,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # The root holds the concatenation; a node that is not the root does not.
    assert np.array_equal(
        read_object(device, local, np.float32, NODES * SLOT, node=3).reshape(
            NODES, SLOT
        ),
        slots,
    )
    assert not np.any(read_object(device, local, np.float32, NODES * SLOT, node=0))
    assert result.counters["link.messages_sent"] == NODES - 1

    build, _, remote = build_collective(
        Link.SCATTER,
        op=CollectiveOp.CONCAT,
        slots=None,
        local=slots,
        local_slots=NODES,
        source_node=3,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read_slots(device, remote, SLOT, range(NODES)), slots)
    assert result.counters["link.messages_sent"] == NODES - 1


def test_a_root_outside_the_participant_set_is_refused():
    source = np.arange(SLOT, dtype=np.float32)
    build, _, _ = build_collective(
        Link.MULTICAST,
        op=CollectiveOp.BROADCAST,
        slots=None,
        local=source,
        local_slots=1,
        source_node=NODES + 1,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "not in the admitted participant set" in result.message


def test_a_participant_count_that_contradicts_the_topology_is_refused():
    source = np.arange(SLOT, dtype=np.float32)
    build, _, _ = build_collective(
        Link.MULTICAST,
        op=CollectiveOp.BROADCAST,
        slots=None,
        local=source,
        local_slots=1,
        source_node=0,
        participant_count=NODES - 1,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "participants" in result.message


def test_a_route_group_selects_a_contiguous_participant_set():
    group = list(range(NODES // 2, NODES))
    slots = (np.arange(len(group) * SLOT, dtype=np.float32) + 1.0).reshape(
        len(group), SLOT
    )
    build, local, _ = build_collective(
        Link.GATHER,
        op=CollectiveOp.CONCAT,
        slots=slots,
        local=None,
        local_slots=NODES,
        destination_node=5,
        participant_count=NODES // 2,
        group_id=1,
        route_groups=2,
        members=group,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # Group 1 of two over eight nodes is nodes 4..7, and its slots are the
    # first four slots of the participant array, in ascending participant order.
    gathered = read_object(device, local, np.float32, (NODES // 2) * SLOT, node=5)
    assert np.array_equal(gathered.reshape(NODES // 2, SLOT), slots)
    assert result.counters["link.messages_sent"] == NODES // 2 - 1


# ---------------------------------------------------------------------------
# COLLECTIVE arithmetic and determinism
# ---------------------------------------------------------------------------
def sequential_sum(stack: np.ndarray) -> np.ndarray:
    """An independent ascending binary32 reduction: no shared engine code."""
    total = np.zeros(stack.shape[1], dtype=np.float32)
    for row in stack:
        total = np.add(total, row, dtype=np.float32)
    return total


def pairwise_sum(stack: np.ndarray) -> np.ndarray:
    level = np.ascontiguousarray(stack, dtype=np.float32)
    while level.shape[0] > 1:
        count = level.shape[0]
        half = count // 2
        folded = np.add(level[: 2 * half : 2], level[1 : 2 * half : 2], dtype=np.float32)
        if count % 2:
            folded = np.concatenate((folded, level[-1:]), axis=0)
        level = folded
    return level[0]


def order_sensitive_slots() -> np.ndarray:
    """Contributions whose binary32 sum genuinely depends on the order."""
    slots = np.full((NODES, SLOT), np.float32(2.0**-24), dtype=np.float32)
    slots[0] = np.float32(1.0)
    return slots


def test_collective_sum_is_the_declared_ascending_reduction():
    slots = order_sensitive_slots()
    build, local, remote = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.SUM,
        slots=slots,
        local=None,
        local_slots=1,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = sequential_sum(slots)
    # The case is not vacuous: the reversed order is a different binary32 value.
    assert not np.array_equal(expected, sequential_sum(slots[::-1]))

    # An all-reduce leaves the result in every node's local buffer and in
    # every participant's own slot.
    for node in range(NODES):
        assert np.array_equal(
            read_object(device, local, np.float32, SLOT, node=node), expected
        )
    everywhere = read_slots(device, remote, SLOT, range(NODES))
    assert np.array_equal(everywhere, np.broadcast_to(expected, (NODES, SLOT)))
    assert result.counters["link.collectives"] == 1


def test_collective_sum_does_not_depend_on_the_order_the_slots_were_filled():
    """The result is a function of the slots, never of arrival order.

    The same contributions are placed into the participant array in ascending
    and in descending physical write order.  A model that reduced in arrival
    order would disagree on the second run; this one cannot, because the
    traversal order comes from the participant set, not from the writes.
    """
    slots = order_sensitive_slots()
    results = []
    for order in (range(NODES), reversed(range(NODES))):
        build = Build(nodes=NODES)
        remote = build.scratch(NODES * SLOT_BYTES, permissions=REMOTE)
        local = build.scratch(SLOT_BYTES)
        comm = build.builder.communication(
            collective_op=CollectiveOp.SUM,
            local_object_id=local,
            remote_object_id=remote,
            byte_extent=SLOT_BYTES,
            participant_count=NODES,
            reduction_numeric_id=fp32_numeric(
                build, ReductionOrder.SEQUENTIAL_ASCENDING
            ),
        )
        build.builder.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=comm)
        device = build.finish()
        for slot in order:
            device.node_memories[slot][remote].write(
                slot * SLOT_BYTES, np.ascontiguousarray(slots[slot]).tobytes()
            )
        outcome = run(device)
        assert outcome.status == CompletionStatus.SUCCESS, outcome.message
        results.append(read_object(device, local, np.float32, SLOT))
    assert np.array_equal(results[0], results[1])
    assert np.array_equal(results[0], sequential_sum(slots))


def test_the_numeric_profile_selects_the_reduction_order():
    slots = order_sensitive_slots()
    build, local, _ = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.SUM,
        slots=slots,
        local=None,
        local_slots=1,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    tree = pairwise_sum(slots)
    assert np.array_equal(read_object(device, local, np.float32, SLOT), tree)
    assert not np.array_equal(tree, sequential_sum(slots))


@pytest.mark.parametrize(
    "op, reduce",
    [
        (CollectiveOp.MAX, np.max),
        (CollectiveOp.MIN, np.min),
    ],
)
def test_max_and_min_reduce_over_the_participant_slots(op, reduce):
    rng = np.random.default_rng(5)
    slots = rng.uniform(-4.0, 4.0, size=(NODES, SLOT)).astype(np.float32)
    build, local, _ = build_collective(
        Link.COLLECTIVE,
        op=op,
        slots=slots,
        local=None,
        local_slots=1,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(
        read_object(device, local, np.float32, SLOT), reduce(slots, axis=0)
    )


def test_all_gather_concatenates_in_ascending_participant_order():
    slots = (np.arange(NODES * SLOT, dtype=np.float32) + 1.0).reshape(NODES, SLOT)
    build, local, _ = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.ALL_GATHER,
        slots=slots,
        local=None,
        local_slots=NODES,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # Every node ends holding every participant's contribution, and each one
    # came out of a different arena.
    for node in range(NODES):
        assert np.array_equal(
            read_object(device, local, np.float32, NODES * SLOT, node=node).reshape(
                NODES, SLOT
            ),
            slots,
        )
    assert result.counters["link.messages_sent"] == NODES * (NODES - 1)


def test_broadcast_copies_the_root_slot_everywhere():
    slots = (np.arange(NODES * SLOT, dtype=np.float32) + 1.0).reshape(NODES, SLOT)
    build, local, remote = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.BROADCAST,
        slots=slots,
        local=None,
        local_slots=1,
        source_node=2,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    for node in range(NODES):
        assert np.array_equal(
            read_object(device, local, np.float32, SLOT, node=node), slots[2]
        )
    assert np.array_equal(
        read_slots(device, remote, SLOT, range(NODES)),
        np.broadcast_to(slots[2], (NODES, SLOT)),
    )


def test_reduce_scatter_requires_a_divisible_extent():
    slots = order_sensitive_slots()
    build, _, _ = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.REDUCE_SCATTER,
        slots=slots,
        local=None,
        local_slots=1,
        destination_node=6,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "shards" in result.message


def test_reduce_scatter_over_two_nodes_shards_the_reduced_vector():
    slots = np.array([[1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0]], dtype=np.float32)
    build, local, remote = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.REDUCE_SCATTER,
        slots=slots,
        local=None,
        local_slots=1,
        destination_node=1,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        nodes=2,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    reduced = sequential_sum(slots)
    shard = SLOT // 2
    array = read_slots(device, remote, SLOT, range(2))
    assert np.array_equal(array[0, :shard], reduced[:shard])
    assert np.array_equal(array[1, :shard], reduced[shard:])
    # Each node keeps the shard of the participant it is.
    assert np.array_equal(
        read_object(device, local, np.float32, shard, node=0), reduced[:shard]
    )
    assert np.array_equal(
        read_object(device, local, np.float32, shard, node=1), reduced[shard:]
    )


def test_collective_point_to_point_is_refused():
    slots = order_sensitive_slots()
    build, _, _ = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.POINT_TO_POINT,
        slots=slots,
        local=None,
        local_slots=1,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "POINT_TO_POINT" in result.message


def test_an_arithmetic_collective_without_a_numeric_contract_is_refused():
    slots = order_sensitive_slots()
    build, _, _ = build_collective(
        Link.COLLECTIVE,
        op=CollectiveOp.SUM,
        slots=slots,
        local=None,
        local_slots=1,
        reduction_order=None,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "reduction_numeric_id" in result.message


# ---------------------------------------------------------------------------
# BARRIER
# ---------------------------------------------------------------------------
def build_barrier(*, nodes: int, byte_extent: int = 0):
    build = Build(nodes=nodes)
    marker = build.scratch(4, permissions=REMOTE)
    comm = build.builder.communication(
        collective_op=CollectiveOp.POINT_TO_POINT,
        local_object_id=marker,
        remote_object_id=marker,
        byte_extent=byte_extent,
        participant_count=nodes,
    )
    build.builder.emit(Major.LINK, Link.BARRIER, descriptor_id=comm)
    return build


def test_a_barrier_is_counted_and_is_never_free():
    build = build_barrier(nodes=NODES)
    result = run(build.finish())
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert result.counters["link.barriers"] == 1
    expected = barrier_messages(int(TopologyClass.CLUSTER_32), NODES)
    assert expected > 0
    assert result.counters["link.messages_sent"] == expected
    assert result.counters["link.messages_received"] == expected
    # A barrier carries no operand payload.
    assert "link.bytes_sent" not in result.counters


def test_a_barrier_that_declares_a_payload_is_refused():
    build = build_barrier(nodes=NODES, byte_extent=4)
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)
    assert "carries no operand payload" in result.message


# ---------------------------------------------------------------------------
# agreement with the cycle model's fabric
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "op, whole_payload",
    [
        (CollectiveOp.BROADCAST, False),
        (CollectiveOp.CONCAT, True),
        (CollectiveOp.ALL_GATHER, True),
        (CollectiveOp.REDUCE_SCATTER, True),
        (CollectiveOp.SUM, False),
        (CollectiveOp.MAX, False),
        (CollectiveOp.MIN, False),
    ],
)
@pytest.mark.parametrize("participants", [2, 4, 8])
def test_collective_traffic_matches_the_cycle_model_fabric(op, whole_payload, participants):
    extent = 4096
    fabric = cluster_fabric(32)
    nbytes = participants * extent if whole_payload else extent
    timing = fabric.collective(int(op), list(range(participants)), nbytes)
    messages, moved = collective_traffic(int(op), participants, extent)
    assert messages == timing.messages
    assert moved == timing.bytes_moved


@pytest.mark.parametrize("participants", [1, 2, 3, 8, 32])
def test_barrier_messages_match_the_cycle_model_fabric(participants):
    cluster = cluster_fabric(32)
    assert barrier_messages(
        int(TopologyClass.CLUSTER_32), participants
    ) == cluster.barrier(list(range(participants))).messages
    if participants <= 8:
        wafer = wafer_fabric()
        assert barrier_messages(
            int(TopologyClass.WAFER_LOGICAL_DEVICE), participants
        ) == wafer.barrier(list(range(participants))).messages


def test_unicast_traffic_matches_the_cycle_model_fabric():
    fabric = cluster_fabric(32)
    timing = fabric.unicast(0, 5, 8192)
    from runtime.sim.engines.link import unicast_traffic

    messages, moved = unicast_traffic(8192)
    assert messages == timing.messages
    assert moved == timing.bytes_moved
