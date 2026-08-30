"""The functional device's node dimension, and the collectives that need it.

A 32-node deployment is not one device with a bigger memory.  It is thirty-two
memories, each holding its own activations and its own state, and the only way
a byte crosses from one to another is a LINK instruction naming a COMMUNICATION
descriptor.  That is what these tests check, and they check it the way the
program itself works: a real ABI 3.0 deployment, admitted by the independent
verifier, executed on :class:`~runtime.sim.device.Device`.

The case that matters most is the last one.  A column-sharded contraction leaves
node *k* holding columns ``[k*S, (k+1)*S)`` of the result and nothing else; the
all-gather is what makes the whole row exist on every node.  An implementation
in which the collective quietly degenerated into a node-local copy would still
produce a plausible-looking buffer -- node zero's shard, and garbage or zeros
everywhere else -- so the test asserts the whole matrix on *every* node, and
then removes the collective and asserts that the answer is wrong without it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime.abi3.builder import DynamicTerm
from runtime.abi3.constants import (
    CompletionStatus,
    DType,
    Dma,
    Link,
    Major,
    NO_ID,
    Permission,
    TrapClass,
)
from runtime.abi3.descriptors import CollectiveOp, Symbol

from test_engines_link import Build, REMOTE, run  # noqa: E402

import runtime.sim.engines.dma  # noqa: F401,E402
import runtime.sim.engines.link  # noqa: F401,E402

# The capability the cluster profile declares admits exactly thirty-two nodes,
# and the verifier bounds a ``NODE_ID``-indexed view against that limit, so the
# case is the real one: thirty-two arenas, thirty-two shards, one all-gather.
NODES = 32
ROWS = 3
SHARD = 2
COLS = NODES * SHARD


def _matrix() -> np.ndarray:
    """A distinct value per (row, column), so a misplaced byte is visible."""
    return (np.arange(ROWS * COLS, dtype=np.uint32) + 1).reshape(ROWS, COLS)


def _sharded_build(*, gather: bool = True):
    """The exact three-step exchange the HBM backend emits for a shard.

    ``activation`` is the ``[ROWS, COLS]`` buffer every node holds a private
    copy of, with node *k* owning columns ``[k*SHARD, (k+1)*SHARD)``.
    ``exchange`` is the participant array: ``NODES`` slots of ``ROWS*SHARD``
    elements, of which node *k* fills slot *k*.

    Both DMAs present their operands column-major -- ``[SHARD, ROWS]`` and
    ``[NODES, SHARD, ROWS]`` -- which is what the backend does and for the same
    reason: the block is moved whole, and amendment A13's clamp of a leading
    token axis cannot make the two ends of one transfer disagree about how many
    rows there are.
    """
    build = Build(nodes=NODES)
    activation = build.scratch(ROWS * COLS * 4)
    exchange = build.scratch(NODES * ROWS * SHARD * 4, permissions=REMOTE)
    view = build.builder.tensor_view

    pack_source = view(
        object_id=activation,
        dtype=DType.U32,
        dims=[SHARD, ROWS],
        strides=[1, COLS],
        dynamic=[DynamicTerm.symbol(Symbol.NODE_ID, SHARD)],
    )
    pack_destination = view(
        object_id=exchange,
        dtype=DType.U32,
        dims=[SHARD, ROWS],
        strides=[1, SHARD],
        dynamic=[DynamicTerm.symbol(Symbol.NODE_ID, ROWS * SHARD)],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    schedule = build.builder.schedule(engine_family=Major.DMA, tile_rows=ROWS,
                                      tile_cols=SHARD, tile_depth=1)
    build.builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=build.builder.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[pack_source],
            outputs=[pack_destination],
            schedule_id=schedule,
        ),
    )

    if gather:
        comm = build.builder.communication(
            collective_op=CollectiveOp.ALL_GATHER,
            local_object_id=exchange,
            remote_object_id=exchange,
            byte_extent=ROWS * SHARD * 4,
            participant_count=NODES,
        )
        build.builder.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=comm)

    unpack_source = view(
        object_id=exchange,
        dtype=DType.U32,
        dims=[NODES, SHARD, ROWS],
        strides=[ROWS * SHARD, 1, SHARD],
    )
    unpack_destination = view(
        object_id=activation,
        dtype=DType.U32,
        dims=[NODES, SHARD, ROWS],
        strides=[SHARD, 1, COLS],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    build.builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=build.builder.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[unpack_source],
            outputs=[unpack_destination],
            schedule_id=schedule,
        ),
    )
    return build, activation, exchange


def _stage_shards(device, activation: int) -> np.ndarray:
    """Give node ``k`` its own column band and nothing else, as a shard is."""
    whole = _matrix()
    for node in range(NODES):
        private = np.zeros_like(whole)
        private[:, node * SHARD : (node + 1) * SHARD] = (
            whole[:, node * SHARD : (node + 1) * SHARD]
        )
        device.node_memories[node][activation].write(
            0, np.ascontiguousarray(private).tobytes()
        )
    return whole


def _read(device, node: int, oid: int, count: int) -> np.ndarray:
    return np.frombuffer(
        device.node_memories[node][oid].read(0, count * 4), dtype=np.uint32
    ).copy()


# ---------------------------------------------------------------------------
# the node dimension itself
# ---------------------------------------------------------------------------
def test_a_cluster_has_one_arena_per_node():
    build = Build(nodes=NODES)
    scratch = build.scratch(16)
    build.builder.emit(Major.CONTROL, 0)
    device = build.finish()
    assert device.node_count == NODES
    assert len(device.node_memories) == NODES
    assert device.memory is device.node_memories[0]
    # Distinct objects, so a write on one node is invisible on the others.
    identities = {id(device.node_memories[n][scratch]) for n in range(NODES)}
    assert len(identities) == NODES
    device.node_memories[1][scratch].write(0, b"\x01\x02\x03\x04")
    assert device.node_memories[0][scratch].read(0, 4) == b"\x00\x00\x00\x00"


def test_immutable_objects_are_shared_and_writable_ones_are_not():
    """Thirty-two copies of a 156 GB checkpoint is not a model of anything.

    An object with no write permission is the same bytes on every node, and each
    node addresses its own shard of it through the ``NODE_ID`` term of a view,
    so it is held once.  Anything writable is per node, because that is what
    makes an activation node-local.
    """
    build = Build(nodes=NODES)
    writable = build.scratch(16)
    immutable = build.scratch(16, permissions=int(Permission.READ))
    build.builder.emit(Major.CONTROL, 0)
    device = build.finish()
    assert all(
        device.node_memories[n][immutable] is device.node_memories[0][immutable]
        for n in range(NODES)
    )
    assert all(
        device.node_memories[n][writable] is not device.node_memories[0][writable]
        for n in range(1, NODES)
    )


def test_node_id_is_bound_per_node_and_zero_outside_an_issue():
    """Every node runs the program; the view's ``NODE_ID`` term is what differs."""
    build = Build(nodes=NODES)
    destination = build.scratch(NODES * 4)
    source = build.object_of(np.arange(NODES, dtype=np.uint32) + 100)
    view = build.builder.tensor_view
    build.builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=build.builder.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[
                view(
                    object_id=source,
                    dtype=DType.U32,
                    dims=[1],
                    strides=[1],
                    dynamic=[DynamicTerm.symbol(Symbol.NODE_ID, 1)],
                )
            ],
            outputs=[
                view(
                    object_id=destination,
                    dtype=DType.U32,
                    dims=[1],
                    strides=[1],
                    permissions=int(Permission.READ | Permission.WRITE),
                )
            ],
            schedule_id=build.builder.schedule(
                engine_family=Major.DMA, tile_rows=1, tile_cols=1, tile_depth=1
            ),
        ),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # Node k read element k of the shared source into its own destination.
    for node in range(NODES):
        assert _read(device, node, destination, 1)[0] == 100 + node


# ---------------------------------------------------------------------------
# the exchange
# ---------------------------------------------------------------------------
def test_an_all_gather_assembles_a_column_sharded_result_on_every_node():
    build, activation, exchange = _sharded_build()
    device = build.finish()
    whole = _stage_shards(device, activation)
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    # Every node holds the whole matrix, and thirty-one thirty-seconds of it --
    # here three quarters -- came out of another node's arena.
    for node in range(NODES):
        assert np.array_equal(
            _read(device, node, activation, ROWS * COLS).reshape(ROWS, COLS), whole
        ), f"node {node}"
    assert result.counters["link.collectives"] == 1
    assert result.counters["link.messages_sent"] == NODES * (NODES - 1)


def test_without_the_collective_every_node_keeps_only_its_own_shard():
    """The case that says the gather is not a copy.

    The same two DMAs with the collective removed: the pack and the unpack are
    node-local, so each node reassembles its own shard and nothing else.  If the
    previous test could pass with this program, the collective would not be
    moving anything.
    """
    build, activation, _exchange = _sharded_build(gather=False)
    device = build.finish()
    whole = _stage_shards(device, activation)
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    for node in range(NODES):
        got = _read(device, node, activation, ROWS * COLS).reshape(ROWS, COLS)
        assert not np.array_equal(got, whole), f"node {node}"
        band = slice(node * SHARD, (node + 1) * SHARD)
        assert np.array_equal(got[:, band], whole[:, band])
        assert not got[:, :band.start].any()


def test_the_gather_reads_the_contribution_from_the_node_that_made_it():
    """Slot ``k`` is read out of node ``k``'s arena, not out of node zero's."""
    build, activation, exchange = _sharded_build()
    device = build.finish()
    whole = _stage_shards(device, activation)
    # Corrupt node zero's copy of a slot it does not own.  Node zero contributes
    # only slot zero, so a correct gather never reads this and the result is
    # unchanged; an implementation that materialised the whole participant array
    # in one arena would read it and produce the corruption.
    poison = np.full(ROWS * SHARD, 0xDEADBEEF, dtype=np.uint32)
    device.node_memories[0][exchange].write(
        2 * ROWS * SHARD * 4, np.ascontiguousarray(poison).tobytes()
    )
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    for node in range(NODES):
        assert np.array_equal(
            _read(device, node, activation, ROWS * COLS).reshape(ROWS, COLS), whole
        ), f"node {node}"


# ---------------------------------------------------------------------------
# one program, thirty-two nodes: control flow and the token may not diverge
# ---------------------------------------------------------------------------
def test_a_predicate_that_reads_differently_on_two_nodes_is_a_trap():
    """Control flow is one program, so it has one answer for the whole device.

    A boolean object is node-local like everything else writable, so nothing
    stops two nodes reading it differently -- except that if they did, thirty-one
    of them would be executing a different program from the one that produced the
    token, and the transaction would be reporting a computation that never
    happened.  So every node is asked and disagreement is a trap, not a vote.
    """
    from runtime.abi3.descriptors import PredicateKind

    build = Build(nodes=NODES)
    flag = build.scratch(4)
    destination = build.scratch(4)
    source = build.object_of(np.array([7], dtype=np.uint32))
    view = build.builder.tensor_view
    predicate = build.builder.predicate(
        kind=PredicateKind.BOOLEAN_OBJECT, object_id=flag, element_index=0
    )
    build.builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=build.builder.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[view(object_id=source, dtype=DType.U32, dims=[1], strides=[1])],
            outputs=[
                view(
                    object_id=destination,
                    dtype=DType.U32,
                    dims=[1],
                    strides=[1],
                    permissions=int(Permission.READ | Permission.WRITE),
                )
            ],
            schedule_id=build.builder.schedule(
                engine_family=Major.DMA, tile_rows=1, tile_cols=1, tile_depth=1
            ),
        ),
        predicate_id=predicate,
    )
    device = build.finish()
    device.node_memories[5][flag].write(0, b"\x01\x00\x00\x00")
    result = run(device)
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.INTERNAL_INVARIANT)
    assert "cannot diverge across nodes" in result.message


def test_nodes_that_select_different_tokens_poison_the_transaction():
    """The check that says the collectives delivered the same activations.

    Every node runs the vocabulary projection and every node selects.  They can
    only agree if the all-gathers actually put the same logits on all of them,
    so a disagreement is reported as a fault rather than resolved by taking node
    zero's answer -- which would be a token from a computation thirty-one nodes
    did not perform.
    """
    build = Build(nodes=NODES)
    build.builder.emit(Major.CONTROL, 0)
    device = build.finish()
    assert device._node_agreement([[5]] * NODES, [{"token": 5}] * NODES) is None
    disagree = [[5]] * NODES
    disagree[7] = [6]
    fault = device._node_agreement(disagree, [{"token": 5}] * NODES)
    assert fault is not None
    assert "node 0 produced [5] and node 7 produced [6]" in fault
    assert "the collectives did not deliver the same activations" in fault
