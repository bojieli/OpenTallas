"""Amendment A14 on the LINK engine: what a collective's participants are.

The pre-amendment engine derived a collective's member set from ``node_count``
alone.  A ``WAFER_LOGICAL_DEVICE`` is presented to the host as one device --
that is what the topology class means -- so it declares one node, and every
collective on a wafer came out as a collective over a single participant, which
the engine refuses as degenerate.  These cases run that failure and then the
fix, on a real deployment executed by the functional device.

The wafer fabric here is deliberately tiny (4 reticles of 8 tiles).  What is
under test is the *derivation*, and a derivation is proved by running it, not
by running it at scale.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    Feature,
    Link,
    Major,
    NO_ID,
    ParticipantScope,
    Permission,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import (
    CollectiveOp,
    ExtendedDescriptorType,
    Phase,
)
from runtime.abi3.verifier import VerificationError
from runtime.sim.device import Device

# The LINK engine harness lives beside this file.  pytest puts this directory
# on ``sys.path`` for a non-package test tree; the explicit insertion keeps a
# direct ``python -m pytest <this file>`` and an IDE runner working too.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engines_link import (  # noqa: E402  (path set above)
    LOCAL,
    REMOTE,
    read_object,
    run,
)

# Importing the engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.link  # noqa: F401


SLOT_BYTES = 16


def wafer_capability(nodes: int = 1) -> Capability:
    """A wafer-scale logical device: bit 9, and one node unless told otherwise."""
    cap = Capability(
        capability_id="",
        topology_class=int(TopologyClass.WAFER_LOGICAL_DEVICE),
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
                Feature.WAFER_ENDPOINT,
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
            "max_nodes": nodes,
        },
        numeric_contracts=("bf16_add_rne_v1",),
        engines={"link": {"queues": 1}, "dma": {"queues": 1}},
        memory={"sram": {"bytes": 1 << 24}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class WaferBuild:
    """A one-transaction deployment on a wafer-scale logical device."""

    def __init__(
        self,
        *,
        reticles: int,
        tiles_per_reticle: int,
        route_groups: int = 0,
        node_count: int = 1,
    ):
        self.capability = wafer_capability(nodes=node_count)
        self.builder = DeploymentBuilder(
            target_id="wafer-link-test",
            model_id="wafer-link-test",
            backend="test",
            capability=self.capability,
            topology_class=int(TopologyClass.WAFER_LOGICAL_DEVICE),
        )
        self.builder.require(Feature.WAFER_ENDPOINT)
        self.builder.topology(
            topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
            # One node: that is what "presented to the host as one device"
            # means, and it is exactly why the pre-A14 derivation failed here.
            node_count=node_count,
            reticle_count=reticles,
            tiles_per_reticle=tiles_per_reticle,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            route_group_count=route_groups,
            link_count=max(reticles * tiles_per_reticle, 1),
            hbm_bytes_per_node=1 << 24,
            sram_bytes_per_node=1 << 24,
        )
        self._initial: dict[int, bytes] = {}

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

    def finish(self, *, verify: bool = True, mutate=None) -> Device:
        """Activate the deployment.

        ``verify=False`` skips admission so that a case can reach the *engine*
        with a descriptor the verifier would refuse; ``mutate`` edits the
        decoded table first.  Both exist to prove the engine checks what it
        needs rather than trusting admission to have checked it.
        """
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL
        )
        deployment = self.builder.finish()
        if mutate is not None:
            mutate(deployment)
        device = Device(deployment, self.capability, verify=verify)
        for oid, data in self._initial.items():
            device.memory[oid].write(0, data)
        return device


def multicast_on(
    *,
    reticles: int,
    tiles_per_reticle: int,
    scope: ParticipantScope,
    participant_count: int,
    route_groups: int = 0,
    group_id: int = NO_ID,
    node_count: int = 1,
    slots: int | None = None,
):
    """One tile/reticle/node-scoped broadcast, ready to execute."""
    build = WaferBuild(
        reticles=reticles,
        tiles_per_reticle=tiles_per_reticle,
        route_groups=route_groups,
        node_count=node_count,
    )
    payload = np.arange(SLOT_BYTES // 4, dtype=np.uint32) + 1
    local = build.object_of(payload)
    array_slots = participant_count if slots is None else slots
    remote = build.scratch(
        max(array_slots, 1) * SLOT_BYTES, permissions=REMOTE
    )
    comm = build.builder.communication(
        collective_op=CollectiveOp.BROADCAST,
        local_object_id=local,
        remote_object_id=remote,
        source_node=0,
        byte_extent=SLOT_BYTES,
        participant_count=participant_count,
        participant_scope=scope,
        group_id=group_id,
        chunk_bytes=SLOT_BYTES,
    )
    build.builder.emit(Major.LINK, Link.MULTICAST, descriptor_id=comm)
    return build, remote, payload


# ---------------------------------------------------------------------------
# the failure the amendment exists to remove
# ---------------------------------------------------------------------------
def test_a_node_scoped_collective_on_a_wafer_is_degenerate():
    """The pre-A14 behaviour, reproduced exactly.

    Counting participants in nodes on a one-node wafer gives a collective over
    one participant, and a one-endpoint transfer is ``LINK.SEND``.
    """
    build, _remote, _payload = multicast_on(
        reticles=4,
        tiles_per_reticle=8,
        scope=ParticipantScope.NODE,
        participant_count=1,
        slots=1,
    )
    result = run(build.finish())
    assert result.status != CompletionStatus.SUCCESS
    assert "a collective over 1 participant(s) is degenerate" in result.message
    assert result.trap_class == int(TrapClass.LINK_OR_NOC)


# ---------------------------------------------------------------------------
# the derivation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "scope,reticles,tiles,expected",
    [
        (ParticipantScope.RETICLE, 4, 8, 4),
        (ParticipantScope.TILE, 4, 8, 32),
        (ParticipantScope.TILE, 6, 2, 12),
        (ParticipantScope.RETICLE, 2, 1, 2),
    ],
)
def test_the_member_count_follows_the_scope(scope, reticles, tiles, expected):
    """``RETICLE`` -> ``reticle_count``; ``TILE`` -> reticles times tiles."""
    build, remote, payload = multicast_on(
        reticles=reticles,
        tiles_per_reticle=tiles,
        scope=scope,
        participant_count=expected,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # Every participant's slot carries the broadcast, and no slot beyond them
    # exists: the array is exactly ``expected`` slots wide.
    for index in range(expected):
        assert np.array_equal(
            read_object(
                device, remote, np.uint32, len(payload), offset=index * SLOT_BYTES
            ),
            payload,
        )
    # A binomial-tree broadcast is P-1 messages, so the count observes the
    # derived member set rather than the descriptor's declaration.
    assert result.counters["link.messages_sent"] == expected - 1


def test_a_node_scope_still_counts_nodes():
    """The amendment adds a scope; it does not move the one that existed."""
    build, remote, payload = multicast_on(
        reticles=4,
        tiles_per_reticle=8,
        scope=ParticipantScope.NODE,
        participant_count=4,
        node_count=4,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert result.counters["link.messages_sent"] == 3
    # A NODE-scoped participant is a node, so with four nodes its slot lives in
    # its own arena rather than in a four-slot array on node zero.
    assert np.array_equal(
        read_object(
            device,
            remote,
            np.uint32,
            len(payload),
            offset=3 * SLOT_BYTES,
            node=3,
        ),
        payload,
    )


def test_a_declared_count_that_disagrees_with_the_scope_is_refused():
    """``participant_count`` is checked against the derivation, not trusted."""
    build, _remote, _payload = multicast_on(
        reticles=4,
        tiles_per_reticle=8,
        scope=ParticipantScope.TILE,
        participant_count=8,
        slots=32,
    )
    result = run(build.finish())
    assert result.status != CompletionStatus.SUCCESS
    assert "declares 8 participants" in result.message
    assert "32 tiles" in result.message


def test_a_route_group_partitions_the_scoped_set():
    """``group_id`` partitions the members exactly as it did for nodes."""
    build, remote, payload = multicast_on(
        reticles=4,
        tiles_per_reticle=8,
        scope=ParticipantScope.TILE,
        participant_count=8,
        route_groups=4,
        group_id=0,
        slots=8,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert result.counters["link.messages_sent"] == 7
    assert np.array_equal(
        read_object(device, remote, np.uint32, len(payload), offset=7 * SLOT_BYTES),
        payload,
    )


# ---------------------------------------------------------------------------
# still degenerate, at any scope
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "scope,reticles,tiles",
    [
        (ParticipantScope.RETICLE, 1, 8),
        (ParticipantScope.TILE, 1, 1),
    ],
)
def test_one_participant_is_degenerate_at_every_scope(scope, reticles, tiles):
    """The refusal is unchanged: a one-endpoint transfer is ``LINK.SEND``."""
    build, _remote, _payload = multicast_on(
        reticles=reticles,
        tiles_per_reticle=tiles,
        scope=scope,
        participant_count=1,
        slots=1,
    )
    result = run(build.finish())
    assert result.status != CompletionStatus.SUCCESS
    assert "a collective over 1 participant(s) is degenerate" in result.message


# ---------------------------------------------------------------------------
# a fabric that is not there
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "reticles,tiles,scope,message",
    [
        (0, 8, ParticipantScope.RETICLE, "no reticle fabric to address"),
        (4, 0, ParticipantScope.TILE, "no tile fabric to address"),
    ],
)
def test_a_scope_the_topology_cannot_support_is_refused_twice(
    reticles, tiles, scope, message
):
    """Once at admission and again in the engine.

    The admission rule is the one that matters in practice -- a deployment
    that cannot run its own collectives should never be activated -- but an
    engine that trusted admission for this would be trusting a field it can
    check itself against the topology it is already holding.
    """
    build, _remote, _payload = multicast_on(
        reticles=reticles,
        tiles_per_reticle=tiles,
        scope=scope,
        participant_count=4,
        slots=4,
    )
    with pytest.raises(VerificationError, match=message):
        build.finish()
    result = run(build.finish(verify=False))
    assert result.status != CompletionStatus.SUCCESS
    assert message in result.message


def test_a_scope_outside_the_frozen_registry_is_refused():
    """The engine checks the registry itself rather than trusting admission."""
    build, _remote, _payload = multicast_on(
        reticles=4,
        tiles_per_reticle=8,
        scope=ParticipantScope.TILE,
        participant_count=32,
    )

    def rewrite(deployment):
        did = deployment.table.ids_of_type(
            int(ExtendedDescriptorType.COMMUNICATION)
        )[0]
        deployment.table[did].payload["participant_scope"] = 9

    result = run(build.finish(verify=False, mutate=rewrite))
    assert result.status != CompletionStatus.SUCCESS
    assert "not in the frozen registry" in result.message
