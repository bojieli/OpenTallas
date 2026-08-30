"""LINK engine: the inter-node datapath of one logical accelerator.

ADR-003 section 8.8 makes communication a *first-class engine*, and section 3.3
makes the two physical realisations -- the 32-node conventional-chip cluster and
the wafer-scale logical device -- mandatory and non-interchangeable.  Both are
still **one device** from the host's point of view: the host submits one
program, and that program moves bytes between node-local memory objects itself.
There is no implicit coherent global address space here.  Every remote access is
an explicit, descriptor-named movement between two named objects, and an object
that a remote node may touch must carry :attr:`Permission.REMOTE`.  A model that
let an engine dereference a remote object without moving it would be modelling a
machine nobody is building.

Operand model
=============
A LINK instruction's ``descriptor_id`` names a **COMMUNICATION** descriptor, not
an OPERATOR (``runtime/abi3/verifier.py`` enforces that).  The descriptor names
two memory objects and a byte extent rather than tensor views, because a link
transfer is a byte movement: reinterpreting the payload is the receiving
engine's job under its own numeric contract.

``local_object_id`` / ``local_offset``
    The endpoint on this node.  It is *symmetric*: the same object at the same
    offset on every node, so a result that every participant must hold -- an
    all-reduce's reduced value, an all-gather's concatenation -- is written
    into every participant's own arena at that one offset.
``remote_object_id`` / ``remote_offset``
    The **participant array**.  For a point-to-point transfer it is the peer's
    buffer.  For MULTICAST, GATHER, SCATTER and COLLECTIVE it holds one slot per
    participant: participant ``k`` owns
    ``[remote_offset + k * byte_extent, + byte_extent)``.  Participants are
    ordered by ascending participant id (see :func:`_participants`), so slot
    order is a property of the descriptor and the admitted topology, never of
    arrival order.

    **Where that slot lives** depends on how many memories the device has, and
    that is the whole of the difference between a chip and a cluster here.  A
    single-node device -- a chip, and a wafer, which is one logical device and
    declares one node -- has one arena, so the whole array is materialised in
    it.  An N-node cluster has one arena per node, so under ``NODE`` scope the
    array is *distributed*: participant ``k`` is node ``k``, and its slot is
    that same offset in **node k's own arena**.  Every node holds the whole
    array and arrives with its own slot filled; the collective is what fills in
    the other thirty-one, out of the other thirty-one arenas.  ``RETICLE`` and
    ``TILE`` scopes always take the single-memory reading, because a wafer's
    reticles and tiles share the one node's memory.

    This is one rule with two realisations, not two rules, and the
    single-memory realisation is the behaviour that was frozen before there was
    a node dimension -- byte for byte, which is what keeps a single-chip Qwen
    deployment and the DeepSeek wafer unchanged.
``byte_extent``
    The **per-participant** slot size, never the whole-collective payload.
``participant_scope``
    What a participant *is*: a ``NODE``, a ``RETICLE`` or a ``TILE`` of the
    admitted topology (amendment A14, wire format section 12.5).  Zero is
    ``NODE``, which is what every program written before the amendment means.
``group_id``
    Selects the participant set out of the admitted TOPOLOGY descriptor.
``collective_op``
    The reduction or movement pattern for LINK.COLLECTIVE.
``reduction_numeric_id``
    The numeric contract of an arithmetic collective, including its
    ``reduction_order``.

Where the local endpoint is itself one of the participants (the root of a
multicast, gather or scatter) its slot is still written or read, but as a
node-local copy: it costs no message.

Determinism
===========
A collective whose result depends on arrival order is a correctness bug, not a
performance detail.  Two things make the result here order-free:

* the participant traversal order is ``sorted(members)`` -- computed from the
  TOPOLOGY descriptor and ``group_id`` before any byte moves, never from the
  order in which contributions "arrive";
* the reduction itself is
  :func:`runtime.sim.engines.reduction.ordered_sum` under the
  ``reduction_order`` of the profile named by ``reduction_numeric_id``, which is
  the same ordered reduction the REDUCTION engine uses.  ``MAX`` and ``MIN`` are
  order-free by construction and are still evaluated in the same slot order.

Counter model
=============
The functional model counts **architectural payload movement** and mirrors the
algorithms in :mod:`runtime.cycle.fabric` so that a message here is a message
there.  With ``P`` participants and ``E`` bytes per participant:

===================================== ============= ==========================
operation                             messages      payload bytes
===================================== ============= ==========================
SEND / RECEIVE / REMOTE_DMA           1             ``E``
MULTICAST (binomial tree broadcast)   ``P-1``       ``(P-1) * E``
GATHER (root gather)                  ``P-1``       ``(P-1) * E``
SCATTER (root scatter)                ``P-1``       ``(P-1) * E``
COLLECTIVE BROADCAST                  ``P-1``       ``(P-1) * E``
COLLECTIVE CONCAT                     ``P-1``       ``(P-1) * E``
COLLECTIVE ALL_GATHER (ring)          ``P(P-1)``    ``P(P-1) * E``
COLLECTIVE REDUCE_SCATTER (ring)      ``P(P-1)``    ``P(P-1) * E``
COLLECTIVE SUM / MAX / MIN (ring)     ``2P(P-1)``   ``2P(P-1) * ceil(E/P)``
BARRIER                               topology      ``0``
===================================== ============= ==========================

``link.messages_sent`` and ``link.messages_received`` both take the message
count, and ``link.bytes_sent`` and ``link.bytes_received`` both take the byte
count: exactly as :meth:`runtime.cycle.fabric.FabricTiming.counters` does, one
message is observed at each of its two endpoints, and both endpoints are inside
this device.  ``tests/sim/test_engines_link.py`` proves the equality against a
real :class:`~runtime.cycle.fabric.ClusterFabric` and
:class:`~runtime.cycle.fabric.WaferFabric` rather than against a copy of these
formulas.

A barrier is **not free**: it costs ``link.barriers`` plus the message count of
the fabric's barrier algorithm for the admitted topology class -- dissemination
(``ceil(log2 P)`` rounds of ``P`` messages) on a cluster, the hierarchical
up/down tree on a wafer.  It moves no architectural payload, because a barrier
carries no operand data; the protocol header bytes it does put on the wire are a
machine parameter (``packet_header_bytes``) that the architecture does not fix,
so they are billed by the cycle model in counter group ``0x0c`` and not here.

``link.credit_stalls`` is derived from the descriptor, not from a wire: a
transfer of ``ceil(byte_extent / chunk_bytes)`` chunks whose chunk count exceeds
``credit_bound`` cannot be launched inside one credit window and is counted as
one credit stall.  ``link.retries`` stays zero: a functional fabric loses
nothing, so no message is replayed.  ``retry_bound`` is still validated, because
a descriptor that declares an unusable retry bound is a descriptor fault whether
or not this model would ever use it.

Everything fails closed with trap class 11 (``LINK_OR_NOC``): a range violation,
a missing ``REMOTE`` permission, a participant set that disagrees with
``participant_count``, an unadmitted node id, an unsupported collective, or a
reduction dtype the profile cannot carry.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from runtime.abi3.constants import (
    DTYPE_BITS,
    NO_ID,
    NO_NODE,
    DType,
    Link,
    Major,
    Ordering,
    ParticipantScope,
    Permission,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.descriptors import (
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
)
from runtime.sim import formats
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.sim.engines.reduction import ordered_sum
from runtime.sim.memory import MemoryError_, MemoryObject

#: Storage classes and their architectural byte counters, read and write.
_MEMORY_COUNTERS: dict[str, tuple[str, str]] = {
    "HBM": ("hbm.bytes_read", "hbm.bytes_written"),
    "SRAM": ("sram.bytes_read", "sram.bytes_written"),
    "ROM": ("rom.bytes_read", "rom.bytes_read"),
    "HOST": ("host.bytes_read", "host.bytes_written"),
    "STATE": ("state.bytes_read", "state.bytes_written"),
}

#: Element storage formats an arithmetic collective may reduce.  A reduction
#: widens to binary32 and rounds once, so the format has to survive both.
_REDUCIBLE = frozenset(formats.WIDENABLE & formats.NARROWABLE)

#: Collectives that are pure movement and need no numeric contract.
_MOVEMENT_COLLECTIVES = frozenset(
    {
        int(CollectiveOp.BROADCAST),
        int(CollectiveOp.CONCAT),
        int(CollectiveOp.ALL_GATHER),
    }
)


def _require(
    condition: bool, message: str, trap_class: int = int(TrapClass.LINK_OR_NOC)
) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


# ---------------------------------------------------------------------------
# Descriptor decoding
# ---------------------------------------------------------------------------
def _communication(descriptor: Descriptor) -> Mapping[str, int]:
    _require(
        descriptor.descriptor_type == int(ExtendedDescriptorType.COMMUNICATION),
        f"LINK instruction names descriptor {descriptor.descriptor_id}, which is "
        f"type {descriptor.descriptor_type:#06x}; a LINK instruction names a "
        "COMMUNICATION descriptor",
        int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )
    payload = descriptor.payload
    _require(
        int(payload["ordering"]) in tuple(int(o) for o in Ordering),
        f"COMMUNICATION descriptor {descriptor.descriptor_id} declares ordering "
        f"{payload['ordering']}, which is not in the frozen registry",
        int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )
    _require(
        0 <= int(payload["retry_bound"]) <= 0xFFFF,
        f"COMMUNICATION descriptor {descriptor.descriptor_id} declares retry "
        f"bound {payload['retry_bound']}, which is not a usable bound",
    )
    return payload


def _topology(ctx: EngineContext) -> Mapping[str, int]:
    """The one admitted TOPOLOGY descriptor of this deployment."""
    ids = ctx.table.ids_of_type(int(ExtendedDescriptorType.TOPOLOGY))
    _require(
        len(ids) == 1,
        f"the deployment declares {len(ids)} TOPOLOGY descriptors; the LINK "
        "engine executes against exactly one admitted topology",
        int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )
    return ctx.table.get(ids[0], ExtendedDescriptorType.TOPOLOGY).payload


def _member_count(topology: Mapping[str, int], scope: int) -> tuple[int, str]:
    """How many participants ``scope`` names in the admitted topology.

    Amendment A14 (wire format section 12.5).  Until A14 the member set was
    derived from ``node_count`` alone, so a collective's participants were
    always nodes.  That is right for a cluster and unusable for a wafer: a
    ``WAFER_LOGICAL_DEVICE`` is presented to the host as one device -- that is
    what the topology class *means* -- so it declares one node, and every
    collective on it came out as a collective over a single participant, which
    the engine correctly refuses as degenerate.

    The descriptor already knew better than the engine did.  ``TOPOLOGY``
    carries ``reticle_count`` and ``tiles_per_reticle`` beside ``node_count``;
    only the participant derivation was node-only.  So::

        NODE     -> node_count
        RETICLE  -> reticle_count
        TILE     -> reticle_count * tiles_per_reticle

    A scope the admitted topology cannot support is refused here as well as at
    admission, because an engine that trusted admission for this would be
    trusting a field it can check itself.
    """
    try:
        participant_scope = ParticipantScope(int(scope))
    except ValueError:
        raise EngineError(
            f"communication declares participant scope {int(scope)}, which is "
            "not in the frozen registry",
            trap_class=int(TrapClass.DESCRIPTOR_OR_ADDRESS),
        ) from None
    reticles = int(topology["reticle_count"])
    tiles = int(topology["tiles_per_reticle"])
    if participant_scope is ParticipantScope.NODE:
        return int(topology["node_count"]), "node"
    if participant_scope is ParticipantScope.RETICLE:
        _require(
            reticles >= 1,
            "communication is RETICLE-scoped; the admitted topology declares "
            f"{reticles} reticles, so it has no reticle fabric to address",
        )
        return reticles, "reticle"
    _require(
        reticles >= 1 and tiles >= 1,
        "communication is TILE-scoped; the admitted topology declares "
        f"{reticles} reticles of {tiles} tiles, so it has no tile fabric to "
        "address",
    )
    return reticles * tiles, "tile"


def _participants(
    ctx: EngineContext, topology: Mapping[str, int], payload: Mapping[str, int]
) -> tuple[int, ...]:
    """The admitted participant set, in ascending participant order.

    ``participant_scope`` (amendment A14) says what a participant *is* -- a
    node, a reticle or a tile -- and :func:`_member_count` counts them out of
    the admitted topology.  ``route_group_count`` then partitions that set into
    equal contiguous groups and ``group_id`` selects one, exactly as it
    partitioned the node set before the amendment.  A deployment that declares
    no route groups, or a communication that names no group, addresses every
    participant.  The set is derived and then *checked* against
    ``participant_count``: a descriptor whose declared participant count does
    not match the topology it was admitted against is a fault, not a hint.
    """
    count, unit = _member_count(topology, int(payload["participant_scope"]))
    _require(count >= 1, f"the admitted topology declares {count} {unit}s")
    groups = int(topology["route_group_count"])
    group_id = int(payload["group_id"])
    if group_id == NO_ID or groups <= 1:
        members = tuple(range(count))
    else:
        _require(
            0 <= group_id < groups,
            f"communication names route group {group_id}; the admitted topology "
            f"declares {groups} route groups",
        )
        _require(
            count % groups == 0,
            f"the admitted topology partitions {count} {unit}s into {groups} "
            "route groups, which is not an equal contiguous partition",
        )
        size = count // groups
        members = tuple(range(group_id * size, (group_id + 1) * size))
    declared = int(payload["participant_count"])
    _require(
        declared == len(members),
        f"communication declares {declared} participants; route group "
        f"{group_id} of the admitted topology has {len(members)} {unit}s",
    )
    return members


def _member_index(members: Sequence[int], node: int, role: str) -> int:
    _require(
        node != NO_NODE,
        f"the collective needs a {role} node, but the descriptor declares none",
    )
    try:
        return list(members).index(int(node))
    except ValueError:
        raise EngineError(
            f"{role} node {node} is not in the admitted participant set "
            f"{tuple(members)}",
            trap_class=int(TrapClass.LINK_OR_NOC),
        ) from None


# ---------------------------------------------------------------------------
# Byte movement
# ---------------------------------------------------------------------------
def _object(
    ctx: EngineContext, object_id: int, role: str, node: int = 0
) -> MemoryObject:
    _require(
        object_id != NO_ID,
        f"communication names no {role} object",
        int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )
    try:
        return ctx.node_memory(node)[object_id]
    except MemoryError_ as exc:
        raise EngineError(str(exc), trap_class=int(TrapClass.LINK_OR_NOC)) from exc


def _remote(ctx: EngineContext, object_id: int, node: int = 0) -> MemoryObject:
    """Resolve the remote endpoint, refusing an object without REMOTE."""
    obj = _object(ctx, object_id, "remote", node)
    _require(
        bool(obj.permissions & int(Permission.REMOTE)),
        f"object {object_id} is addressed as a remote endpoint but does not "
        "carry REMOTE permission; there is no implicit coherent global cache, "
        "so a remote object must be explicitly exported",
    )
    return obj


# ---------------------------------------------------------------------------
# Distributed endpoints
# ---------------------------------------------------------------------------
def _read_slot(ctx: EngineContext, transfer: "_Transfer", index: int) -> bytes:
    """Participant ``index``'s contribution, out of the arena that holds it."""
    obj = _remote(
        ctx, int(transfer.payload["remote_object_id"]), transfer.nodes[index]
    )
    return _fetch(ctx, obj, transfer.slot(index), transfer.extent)


def _write_slot(
    ctx: EngineContext, transfer: "_Transfer", index: int, data: bytes
) -> None:
    """Deliver ``data`` into participant ``index``'s own slot."""
    obj = _remote(
        ctx, int(transfer.payload["remote_object_id"]), transfer.nodes[index]
    )
    _store(ctx, obj, transfer.slot(index), data)


def _read_local(
    ctx: EngineContext, transfer: "_Transfer", offset: int, node: int
) -> bytes:
    obj = _object(ctx, int(transfer.payload["local_object_id"]), "local", node)
    return _fetch(ctx, obj, offset, transfer.extent)


def _write_local_everywhere(
    ctx: EngineContext, transfer: "_Transfer", offset: int, data: bytes
) -> None:
    """Land ``data`` in the local buffer of every node the collective spans.

    The local endpoint is symmetric -- the same object at the same offset on
    every node -- so a result that every participant must hold is written into
    every participant's own arena.  On a single-node device that is the one
    write it has always been.
    """
    for node in transfer.endpoints():
        obj = _object(ctx, int(transfer.payload["local_object_id"]), "local", node)
        _store(ctx, obj, offset, data)


def _account_memory(ctx: EngineContext, obj: MemoryObject, nbytes: int, write: bool) -> None:
    read_key, write_key = _MEMORY_COUNTERS[obj.storage_class.name]
    ctx.counters.add(write_key if write else read_key, int(nbytes))


def _fetch(ctx: EngineContext, obj: MemoryObject, offset: int, nbytes: int) -> bytes:
    _require(
        obj.readable,
        f"object {obj.object_id} is not readable by the link engine",
    )
    try:
        payload = obj.read(int(offset), int(nbytes))
    except MemoryError_ as exc:
        raise EngineError(
            f"link read of object {obj.object_id}: {exc}",
            trap_class=int(TrapClass.LINK_OR_NOC),
        ) from exc
    _account_memory(ctx, obj, nbytes, write=False)
    return payload


def _store(
    ctx: EngineContext, obj: MemoryObject, offset: int, payload: bytes
) -> None:
    _require(
        obj.writable,
        f"object {obj.object_id} ({obj.storage_class.name}) is not writable by "
        "the link engine",
    )
    try:
        obj.write(int(offset), payload)
    except MemoryError_ as exc:
        raise EngineError(
            f"link write of object {obj.object_id}: {exc}",
            trap_class=int(TrapClass.LINK_OR_NOC),
        ) from exc
    _account_memory(ctx, obj, len(payload), write=True)


# ---------------------------------------------------------------------------
# Traffic accounting
# ---------------------------------------------------------------------------
def _account_link(ctx: EngineContext, messages: int, nbytes: int) -> None:
    """One message is observed at both of its endpoints, and so are its bytes."""
    ctx.counters.add("link.messages_sent", int(messages))
    ctx.counters.add("link.messages_received", int(messages))
    ctx.counters.add("link.bytes_sent", int(nbytes))
    ctx.counters.add("link.bytes_received", int(nbytes))


def unicast_traffic(extent: int) -> tuple[int, int]:
    """Messages and payload bytes of one point-to-point transfer."""
    return 1, max(int(extent), 0)


def collective_traffic(op: int, participants: int, extent: int) -> tuple[int, int]:
    """Messages and payload bytes of one collective over ``participants``.

    Mirrors the algorithm :mod:`runtime.cycle.fabric` runs for the same
    ``CollectiveOp``: a binomial tree for BROADCAST, a root gather for CONCAT,
    a ring for ALL_GATHER and REDUCE_SCATTER, and a ring reduce-scatter followed
    by a ring all-gather for SUM, MAX and MIN.  ``extent`` is the per-participant
    slot size; the fabric's ``nbytes`` argument is the whole-collective payload,
    which is ``participants * extent`` for the gather-shaped collectives and
    ``extent`` for the reduce- and broadcast-shaped ones.
    """
    count = int(participants)
    extent = max(int(extent), 0)
    collective = CollectiveOp(int(op))
    if collective in (CollectiveOp.BROADCAST, CollectiveOp.CONCAT):
        messages = count - 1
        return messages, messages * extent
    if collective in (CollectiveOp.ALL_GATHER, CollectiveOp.REDUCE_SCATTER):
        messages = count * (count - 1)
        return messages, messages * extent
    if collective in (CollectiveOp.SUM, CollectiveOp.MAX, CollectiveOp.MIN):
        messages = 2 * count * (count - 1)
        per_step = max(1, math.ceil(extent / count)) if extent else 0
        return messages, messages * per_step
    raise EngineError(
        f"collective {collective.name} is not an executable LINK.COLLECTIVE",
        trap_class=int(TrapClass.LINK_OR_NOC),
    )


def barrier_messages(topology_class: int, participants: int) -> int:
    """Messages of one barrier on ``topology_class``.

    The cluster fabric runs a dissemination barrier (``ceil(log2 P)`` rounds of
    ``P`` messages); the wafer fabric runs a hierarchical up/down tree.  Both are
    bounded and neither is zero, which is what ADR-003 section 9 requires.
    """
    count = int(participants)
    if count <= 0:
        raise EngineError(
            "a barrier needs at least one participant",
            trap_class=int(TrapClass.LINK_OR_NOC),
        )
    levels = max(1, math.ceil(math.log2(count))) if count > 1 else 1
    if int(topology_class) == int(TopologyClass.WAFER_LOGICAL_DEVICE):
        messages = 0
        for _phase in range(2):
            for level in range(levels):
                stride = 1 << level
                messages += sum(
                    1
                    for index in range(0, count, stride * 2)
                    if index + stride < count
                )
        return messages
    return levels * count


def _credit_stalls(ctx: EngineContext, payload: Mapping[str, int], extent: int) -> None:
    """Charge a credit stall when the transfer cannot fit one credit window."""
    chunk = int(payload["chunk_bytes"])
    credits = int(payload["credit_bound"])
    if extent <= 0 or chunk <= 0 or credits <= 0:
        return
    if math.ceil(extent / chunk) > credits:
        ctx.counters.add("link.credit_stalls")


# ---------------------------------------------------------------------------
# Reduction
# ---------------------------------------------------------------------------
def _reduction_profile(
    ctx: EngineContext, payload: Mapping[str, int], extent: int
) -> tuple[NumericProfile, int]:
    """Decode the arithmetic contract of a collective and its element width."""
    profile_id = int(payload["reduction_numeric_id"])
    _require(
        profile_id != NO_ID,
        "an arithmetic collective needs the numeric contract named by "
        "reduction_numeric_id",
        int(TrapClass.DESCRIPTOR_OR_ADDRESS),
    )
    profile = ctx.numeric(profile_id)
    _require(
        profile.input_dtype == profile.output_dtype,
        f"numeric profile {profile_id} reduces {DType(profile.input_dtype).name} "
        f"into {DType(profile.output_dtype).name}; a collective's result occupies "
        "the same participant slot as its contributions, so the two storage "
        "formats must be the same",
        int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
    )
    _require(
        int(profile.input_dtype) in _REDUCIBLE,
        f"numeric profile {profile_id} reduces "
        f"{DType(profile.input_dtype).name}, which the link engine cannot widen "
        "to binary32 and round back",
        int(TrapClass.CAPABILITY_OR_RESOURCE),
    )
    width = DTYPE_BITS[DType(profile.input_dtype)]
    itemsize = width // 8
    _require(
        extent % itemsize == 0,
        f"byte extent {extent} is not a whole number of "
        f"{DType(profile.input_dtype).name} elements",
    )
    return profile, itemsize


def _decode(payload: bytes, dtype: int) -> np.ndarray:
    """Widen one participant slot's codes to binary32."""
    from runtime.sim.memory import NUMPY_DTYPE

    codes = np.frombuffer(payload, dtype=NUMPY_DTYPE[DType(dtype)])
    try:
        return formats.widen(dtype, codes)
    except formats.FormatError as exc:
        raise EngineError(
            f"collective contribution: {exc}",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        ) from exc


def _encode(values: np.ndarray, dtype: int) -> bytes:
    """Round one binary32 result back into the participant slot's format."""
    if not bool(np.all(np.isfinite(values))):
        raise EngineError(
            "collective result is NaN or infinite",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    try:
        codes, _ = formats.narrow(dtype, values)
    except formats.FormatError as exc:
        raise EngineError(
            f"collective result: {exc}",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        ) from exc
    return np.ascontiguousarray(codes).tobytes()


def _reduce(
    slots: Sequence[bytes], op: int, profile: NumericProfile
) -> bytes:
    """Reduce contributions in ascending participant order, then round once."""
    stack = np.stack([_decode(slot, profile.input_dtype) for slot in slots], axis=0)
    collective = CollectiveOp(int(op))
    previous = np.seterr(over="raise", invalid="raise")
    try:
        if collective is CollectiveOp.SUM or collective is CollectiveOp.REDUCE_SCATTER:
            total = ordered_sum(stack, int(profile.reduction_order))
        elif collective is CollectiveOp.MAX:
            total = np.maximum.reduce(stack, axis=0)
        elif collective is CollectiveOp.MIN:
            total = np.minimum.reduce(stack, axis=0)
        else:  # pragma: no cover - guarded by the caller
            raise EngineError(
                f"collective {collective.name} is not a reduction",
                trap_class=int(TrapClass.LINK_OR_NOC),
            )
    except FloatingPointError as exc:
        raise EngineError(
            f"collective reduction overflowed binary32: {exc}",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        ) from exc
    finally:
        np.seterr(**previous)
    return _encode(np.ascontiguousarray(total, dtype=np.float32), profile.output_dtype)


# ---------------------------------------------------------------------------
# Shared preamble
# ---------------------------------------------------------------------------
class _Transfer:
    """One decoded LINK transfer: descriptor, topology and participant set.

    Where a participant's slot *lives* is the one thing that changes when the
    device has more than one node.  The participant array has one slot per
    participant either way; the question is whether those slots are laid out
    consecutively in one memory or held one per memory.

    * On a **single-node** device -- a chip, and a wafer, which is presented to
      the host as one logical device and declares one node -- there is one
      arena, so the whole array is materialised in it and participant ``k``
      owns ``[remote_offset + k*byte_extent, +byte_extent)``.  That is also the
      case for every ``RETICLE``- and ``TILE``-scoped collective, because a
      wafer's reticles and tiles share the one node's memory.
    * On an **N-node cluster** each node has its own arena, so the array is
      distributed: participant ``k`` is a node, and its slot is that same
      offset ``remote_offset + k*byte_extent`` *in node k's own arena*.  Each
      node holds the whole participant array and arrives with its own slot
      filled; the collective is what fills in the rest.

    One rule, and the single-node case of it is the behaviour that was already
    frozen, byte for byte.
    """

    __slots__ = (
        "payload",
        "topology",
        "members",
        "extent",
        "count",
        "nodes",
        "distributed",
    )

    def __init__(self, ctx: EngineContext, descriptor: Descriptor, *, collective: bool):
        self.payload = _communication(descriptor)
        self.extent = int(self.payload["byte_extent"])
        _require(
            self.extent >= 0,
            f"communication declares byte extent {self.extent}",
        )
        if collective:
            self.topology = _topology(ctx)
            self.members = _participants(ctx, self.topology, self.payload)
            self.count = len(self.members)
            _require(
                self.count >= 2,
                f"a collective over {self.count} participant(s) is degenerate; a "
                "one-endpoint transfer is LINK.SEND",
            )
            scope = int(self.payload["participant_scope"])
            self.distributed = (
                ctx.node_count > 1 and scope == int(ParticipantScope.NODE)
            )
            # Under NODE scope a member *is* a node id, so the participant set
            # is the node set of this route group.  Otherwise every participant
            # lives on the one node this program is running as.
            self.nodes = (
                tuple(int(m) for m in self.members)
                if self.distributed
                else (0,) * self.count
            )
        else:
            self.topology = {}
            self.members = ()
            self.count = 0
            self.nodes = ()
            self.distributed = False

    def slot(self, index: int) -> int:
        return int(self.payload["remote_offset"]) + index * self.extent

    def endpoints(self) -> tuple[int, ...]:
        """The nodes that hold a copy of this collective's local buffer."""
        if not self.distributed:
            return (0,)
        return tuple(sorted(set(self.nodes)))


# ---------------------------------------------------------------------------
# LINK.SEND / RECEIVE / REMOTE_DMA
# ---------------------------------------------------------------------------
def _point_to_point(
    ctx: EngineContext, descriptor: Descriptor, *, push: bool, sub: Link
) -> None:
    transfer = _Transfer(ctx, descriptor, collective=False)
    payload = transfer.payload
    local = _object(ctx, int(payload["local_object_id"]), "local")
    remote = _remote(ctx, int(payload["remote_object_id"]))
    extent = transfer.extent
    if push:
        data = _fetch(ctx, local, int(payload["local_offset"]), extent)
        _store(ctx, remote, int(payload["remote_offset"]), data)
    else:
        data = _fetch(ctx, remote, int(payload["remote_offset"]), extent)
        _store(ctx, local, int(payload["local_offset"]), data)
    messages, moved = unicast_traffic(extent)
    _account_link(ctx, messages, moved)
    _credit_stalls(ctx, payload, extent)
    if sub is Link.REMOTE_DMA:
        ctx.counters.add("link.remote_dma_bytes", moved)


@register(Major.LINK, Link.SEND)
def send(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Push ``byte_extent`` bytes from the local object into the remote one."""
    _point_to_point(ctx, descriptor, push=True, sub=Link.SEND)


@register(Major.LINK, Link.RECEIVE)
def receive(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Pull ``byte_extent`` bytes from the remote object into the local one."""
    _point_to_point(ctx, descriptor, push=False, sub=Link.RECEIVE)


@register(Major.LINK, Link.REMOTE_DMA)
def remote_dma(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """One endpoint-initiated remote transfer.

    ``source_node`` and ``destination_node`` name the two endpoints, and the
    local node -- ``local_node_id`` of the admitted topology -- decides which of
    them this instruction drives: a remote DMA whose local node is the source is
    a push, one whose local node is the destination is a pull.  A remote DMA
    that names neither the local node as source nor as destination is refused:
    an endpoint cannot initiate a transfer it is not part of.
    """
    payload = _communication(descriptor)
    topology = _topology(ctx)
    local_node = int(topology["local_node_id"])
    source = int(payload["source_node"])
    destination = int(payload["destination_node"])
    if source == local_node:
        push = True
    elif destination == local_node:
        push = False
    else:
        raise EngineError(
            f"REMOTE_DMA moves node {source} to node {destination}; the local "
            f"node is {local_node}, which is neither endpoint",
            trap_class=int(TrapClass.LINK_OR_NOC),
        )
    _point_to_point(ctx, descriptor, push=push, sub=Link.REMOTE_DMA)


# ---------------------------------------------------------------------------
# LINK.MULTICAST / GATHER / SCATTER
# ---------------------------------------------------------------------------
@register(Major.LINK, Link.MULTICAST)
def multicast(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """One local buffer to every participant slot of the remote array.

    ``source_node`` names the root, which must be a participant.  The root's own
    slot is written as a node-local copy and costs no message.
    """
    transfer = _Transfer(ctx, descriptor, collective=True)
    payload = transfer.payload
    root = _member_index(transfer.members, int(payload["source_node"]), "source")
    data = _read_local(
        ctx, transfer, int(payload["local_offset"]), transfer.nodes[root]
    )
    for index in range(transfer.count):
        _write_slot(ctx, transfer, index, data)
    messages, moved = collective_traffic(
        int(CollectiveOp.BROADCAST), transfer.count, transfer.extent
    )
    _account_link(ctx, messages, moved)
    _credit_stalls(ctx, payload, transfer.extent)


@register(Major.LINK, Link.GATHER)
def gather(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Every participant slot of the remote array into the local slot array.

    ``destination_node`` names the root, which must be a participant.  The local
    object holds ``participant_count`` slots of ``byte_extent`` bytes starting at
    ``local_offset``, in ascending participant order.
    """
    transfer = _Transfer(ctx, descriptor, collective=True)
    payload = transfer.payload
    root = _member_index(
        transfer.members, int(payload["destination_node"]), "destination"
    )
    local = _object(
        ctx, int(payload["local_object_id"]), "local", transfer.nodes[root]
    )
    base = int(payload["local_offset"])
    for index in range(transfer.count):
        data = _read_slot(ctx, transfer, index)
        _store(ctx, local, base + index * transfer.extent, data)
    messages, moved = collective_traffic(
        int(CollectiveOp.CONCAT), transfer.count, transfer.extent
    )
    _account_link(ctx, messages, moved)
    _credit_stalls(ctx, payload, transfer.extent)


@register(Major.LINK, Link.SCATTER)
def scatter(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """The local slot array out to every participant slot of the remote array.

    ``source_node`` names the root, which must be a participant.  Slot ``k`` of
    the local array is delivered to participant ``k``.
    """
    transfer = _Transfer(ctx, descriptor, collective=True)
    payload = transfer.payload
    root = _member_index(transfer.members, int(payload["source_node"]), "source")
    local = _object(
        ctx, int(payload["local_object_id"]), "local", transfer.nodes[root]
    )
    base = int(payload["local_offset"])
    for index in range(transfer.count):
        data = _fetch(ctx, local, base + index * transfer.extent, transfer.extent)
        _write_slot(ctx, transfer, index, data)
    messages, moved = collective_traffic(
        int(CollectiveOp.CONCAT), transfer.count, transfer.extent
    )
    _account_link(ctx, messages, moved)
    _credit_stalls(ctx, payload, transfer.extent)


# ---------------------------------------------------------------------------
# LINK.COLLECTIVE
# ---------------------------------------------------------------------------
@register(Major.LINK, Link.COLLECTIVE)
def collective(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """One collective over the admitted participant set.

    The remote object is the participant array.  Which slots are read, which are
    written and where the local buffer sits depends on the pattern:

    ``SUM`` / ``MAX`` / ``MIN``
        All-reduce.  Every slot contributes; the reduced value is written back
        to every slot and to the local buffer.
    ``REDUCE_SCATTER``
        The same reduction, then shard ``k`` of the result (``byte_extent /
        participant_count`` bytes) is written to the head of slot ``k``, and the
        shard of ``destination_node`` is written to the local buffer.
    ``BROADCAST``
        The slot of ``source_node`` is copied to every other slot and to the
        local buffer.
    ``ALL_GATHER`` / ``CONCAT``
        The slots are concatenated, in ascending participant order, into the
        ``participant_count``-slot local array at ``local_offset``.
    """
    transfer = _Transfer(ctx, descriptor, collective=True)
    payload = transfer.payload
    op = int(payload["collective_op"])
    _require(
        op != int(CollectiveOp.POINT_TO_POINT),
        "LINK.COLLECTIVE names POINT_TO_POINT; a point-to-point transfer is "
        "LINK.SEND, LINK.RECEIVE or LINK.REMOTE_DMA",
    )
    collective_op = CollectiveOp(op)
    base = int(payload["local_offset"])
    extent = transfer.extent
    count = transfer.count

    if op in _MOVEMENT_COLLECTIVES:
        if collective_op is CollectiveOp.BROADCAST:
            root = _member_index(transfer.members, int(payload["source_node"]), "source")
            data = _read_slot(ctx, transfer, root)
            for index in range(count):
                if index != root:
                    _write_slot(ctx, transfer, index, data)
            _write_local_everywhere(ctx, transfer, base, data)
        else:
            # Read every contribution before writing any of it.  The
            # participant array and the local buffer are allowed to be the same
            # object -- a symmetric receive buffer that a node arrives at with
            # its own slot already filled is the ordinary way to post an
            # all-gather -- and a read-after-write over an aliased buffer would
            # make the result depend on traversal order.
            slots = [_read_slot(ctx, transfer, index) for index in range(count)]
            for index, data in enumerate(slots):
                _write_local_everywhere(ctx, transfer, base + index * extent, data)
    else:
        profile, itemsize = _reduction_profile(ctx, payload, extent)
        slots = [_read_slot(ctx, transfer, index) for index in range(count)]
        reduced = _reduce(slots, op, profile)
        if collective_op is CollectiveOp.REDUCE_SCATTER:
            _require(
                extent % (count * itemsize) == 0,
                f"REDUCE_SCATTER shards {extent} bytes across {count} "
                "participants, which is not a whole number of elements each",
            )
            shard = extent // count
            for index in range(count):
                _write_slot(
                    ctx,
                    transfer,
                    index,
                    reduced[index * shard : (index + 1) * shard],
                )
            if transfer.distributed:
                # Each node keeps the shard of the participant it *is*.
                for index in range(count):
                    local = _object(
                        ctx,
                        int(payload["local_object_id"]),
                        "local",
                        transfer.nodes[index],
                    )
                    _store(
                        ctx,
                        local,
                        base,
                        reduced[index * shard : (index + 1) * shard],
                    )
            else:
                mine = _member_index(
                    transfer.members, int(payload["destination_node"]), "destination"
                )
                local = _object(ctx, int(payload["local_object_id"]), "local")
                _store(ctx, local, base, reduced[mine * shard : (mine + 1) * shard])
        else:
            for index in range(count):
                _write_slot(ctx, transfer, index, reduced)
            _write_local_everywhere(ctx, transfer, base, reduced)

    messages, moved = collective_traffic(op, count, extent)
    _account_link(ctx, messages, moved)
    _credit_stalls(ctx, payload, extent)
    ctx.counters.add("link.collectives")


# ---------------------------------------------------------------------------
# LINK.BARRIER
# ---------------------------------------------------------------------------
@register(Major.LINK, Link.BARRIER)
def barrier(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Check the participant set against the admitted topology and record it.

    A barrier is an event, not a transfer: it names no payload and moves none.
    It is still counted, in ``link.barriers`` and in the message traffic of the
    fabric's barrier algorithm, because a global barrier that costs nothing is
    exactly the thing ADR-003 section 9 forbids a model from claiming.
    """
    payload = _communication(descriptor)
    _require(
        int(payload["byte_extent"]) == 0,
        f"LINK.BARRIER declares a {payload['byte_extent']}-byte extent; a "
        "barrier carries no operand payload",
    )
    topology = _topology(ctx)
    members = _participants(ctx, topology, payload)
    _require(
        len(members) >= 1,
        "a barrier needs at least one participant",
    )
    source = int(payload["source_node"])
    if source != NO_NODE:
        _member_index(members, source, "source")
    messages = barrier_messages(int(topology["topology_class"]), len(members))
    _account_link(ctx, messages, 0)
    ctx.counters.add("link.barriers")


__all__ = [
    "barrier",
    "barrier_messages",
    "collective",
    "collective_traffic",
    "gather",
    "multicast",
    "receive",
    "remote_dma",
    "scatter",
    "send",
    "unicast_traffic",
]
