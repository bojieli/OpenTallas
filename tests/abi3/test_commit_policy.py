"""Amendment A21: a state commit's row count is declared, not assumed.

Wire format section 12.11.  ``SPAN_TOKENS`` is a *request* symbol, and it is a
row count only where the resource's row axis is the token axis.  The three
claims checked here are the three the amendment makes:

1. the document publishes the registry the encoder implements;
2. the policy is *derived* from the finished descriptor table -- a resource no
   descriptor can stage declares ``UNSTAGED`` -- and the verifier re-derives it,
   so a declaration that disagrees with its own deployment is refused; and
3. the device commits nothing for an ``UNSTAGED`` resource, including one whose
   whole capacity is below the request's span, which is the wall both DeepSeek
   lanes stopped at.
"""

from __future__ import annotations

import re

import pytest

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CommitPolicy,
    Control,
    DType,
    Dma,
    Major,
    Permission,
    State,
    StateClass,
    StorageClass,
)
from runtime.abi3.deployment import (
    ObjectSource,
    ring_staged_objects,
    staged_objects,
)
from runtime.abi3.descriptors import (
    STATE_PAYLOAD,
    ExtendedDescriptorType,
    Symbol,
)
from runtime.abi3.verifier import verify_deployment
from runtime.sim.device import Device
from runtime.sim.engines import load_engines

from . import (
    WIRE_FORMAT_DOC,
    patched_payload,
    probe_capability,
    probe_deployment,
    restamp,
)


DOC_TEXT = WIRE_FORMAT_DOC.read_text(encoding="utf-8")

# The two device tests execute a real DMA, so the engine registry must be
# populated; the rest of this suite deliberately never loads it.
load_engines()

#: The unstaged resource is deliberately smaller than the span below, which is
#: the shape of the wall: eight rows against a hundred-and-four-token prefill.
WINDOW_ROWS = 8
WINDOW_ROW_BYTES = 16
#: Above the unstaged window's whole capacity and below the staged KV cache's,
#: so one transaction exercises both policies at once.
SPAN = 32


# ---------------------------------------------------------------------------
# 1. the document publishes the registry
# ---------------------------------------------------------------------------
def test_the_document_defines_the_policy_registry() -> None:
    assert "### 12.11 Amendment A21" in DOC_TEXT
    assert "| A21 |" in DOC_TEXT, "amendment index section 14 does not list A21"
    for policy in CommitPolicy:
        row = re.search(
            rf"^\|\s*{int(policy)}\s*\|\s*`{policy.name}`\s*\|", DOC_TEXT, re.M
        )
        assert row, f"the document publishes no row for {policy.name}"


def test_the_field_is_the_one_the_frozen_payload_already_carried() -> None:
    """A21 assigns a registry to a named field; it moves no other byte."""
    field = STATE_PAYLOAD.field("commit_policy")
    assert (field.offset, field.size) == (1, 1)
    assert STATE_PAYLOAD.size == 128


# ---------------------------------------------------------------------------
# 2. the policy is derived and checked, not chosen
# ---------------------------------------------------------------------------
def _two_state_deployment() -> tuple[Capability, object, dict[str, int]]:
    """One staged resource and one unstaged resource, in one transaction.

    The probe's own KV resource becomes staged by giving it a destination view
    and a ``DMA.TRANSFER`` that writes it -- which is what a real lane emits.
    The window resource beside it is named by no descriptor's destination, and
    its eight-row capacity is far below the span the transaction runs at.
    """
    captured: dict[str, int] = {}

    def program(builder, ids):
        window_bytes = WINDOW_ROWS * WINDOW_ROW_BYTES
        committed = builder.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=window_bytes,
            source=ObjectSource.zeros(window_bytes),
            permissions=int(Permission.READ | Permission.STATE_COMMIT),
        )
        prepared = builder.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=window_bytes,
            source=ObjectSource.zeros(window_bytes),
            permissions=int(Permission.READ | Permission.STATE_PREPARE),
        )
        window_view = builder.tensor_view(
            object_id=prepared,
            dtype=DType.BF16,
            dims=[WINDOW_ROWS, WINDOW_ROW_BYTES // 2],
            permissions=int(Permission.READ | Permission.WRITE),
        )
        window = builder.state(
            state_class=StateClass.SCRATCH,
            committed_object_id=committed,
            prepared_object_id=prepared,
            row_bytes=WINDOW_ROW_BYTES,
            capacity_rows=WINDOW_ROWS,
            element_dtype=DType.BF16,
            view_descriptor_id=window_view,
        )
        # The probe's KV resource gets a real destination, so it is staged.
        kv_view = builder.tensor_view(
            object_id=ids["kv_prepared"],
            dtype=DType.BF16,
            dims=[8, 8],
            permissions=int(Permission.READ | Permission.WRITE),
        )
        dma_schedule = builder.schedule(
            engine_family=Major.DMA, tile_rows=8, tile_cols=8, tile_depth=1
        )
        stage = builder.operator(
            engine_family=Major.DMA,
            engine_sub=Dma.TRANSFER,
            inputs=[ids["activation_view"]],
            outputs=[kv_view],
            numeric_profile_id=ids["numeric"],
            schedule_id=dma_schedule,
        )
        captured["kv_state"] = ids["state"]
        captured["window_state"] = window
        captured["window_prepared"] = prepared

        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=window)
        builder.emit(Major.DMA, Dma.TRANSFER, descriptor_id=stage)
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=ids["state"])
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=window)
        builder.emit(Major.CONTROL, Control.COMPLETE)

    capability = probe_capability()
    deployment = probe_deployment(capability, program=program)
    return capability, deployment, captured


def test_a_resource_no_descriptor_can_stage_declares_unstaged() -> None:
    _, deployment, ids = _two_state_deployment()
    table = deployment.table
    staged = staged_objects(table)

    kv = table[ids["kv_state"]]
    window = table[ids["window_state"]]
    assert int(kv.payload["prepared_object_id"]) in staged
    assert int(window.payload["prepared_object_id"]) not in staged
    assert kv.payload["commit_policy"] == int(CommitPolicy.REQUEST_SPAN)
    assert window.payload["commit_policy"] == int(CommitPolicy.UNSTAGED)


def test_the_declaration_survives_encoding() -> None:
    """The derivation runs after the descriptors were encoded, so the record
    the digest binds must carry it and not only the in-memory payload."""
    _, deployment, ids = _two_state_deployment()
    reloaded = deployment.table.decode(deployment.table.encode())
    assert reloaded[ids["window_state"]].payload["commit_policy"] == int(
        CommitPolicy.UNSTAGED
    )
    assert reloaded[ids["kv_state"]].payload["commit_policy"] == int(
        CommitPolicy.REQUEST_SPAN
    )


@pytest.mark.parametrize("declared", [int(CommitPolicy.REQUEST_SPAN), 2])
def test_a_declaration_that_disagrees_with_the_deployment_is_refused(
    declared: int,
) -> None:
    capability, deployment, ids = _two_state_deployment()
    deployment.table = patched_payload(
        deployment.table,
        ids["window_state"],
        STATE_PAYLOAD,
        "commit_policy",
        declared,
    )
    report = verify_deployment(restamp(deployment), capability)
    assert not report.admitted
    assert report.checks["commit_policy_declared"] is False
    assert any("commit policy" in error for error in report.errors)


# ---------------------------------------------------------------------------
# 3. the device commits what the policy says
# ---------------------------------------------------------------------------
def test_an_unstaged_resource_smaller_than_the_span_commits_nothing() -> None:
    """The wall, reproduced and cleared.

    Before A21 this transaction failed with `committing 104 rows at cursor 0
    with 0 already staged exceeds capacity 8`, whatever a backend did, because
    the count came from the request rather than from the resource.
    """
    capability, deployment, ids = _two_state_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    result = device.run_transaction(
        session,
        entrypoint_id=0,
        symbols={int(Symbol.SPAN_TOKENS): SPAN},
    )

    assert result.message is None or "exceeds capacity" not in result.message
    assert result.trap_class == 0, result.message
    counters = result.counters
    assert counters["state.commits"] == 2
    assert counters["state.unstaged_commits"] == 1
    # Only the staged resource contributes rows, and it contributes the span.
    assert counters["state.rows_committed"] == SPAN

    window = session.states[ids["window_state"]]
    kv = session.states[ids["kv_state"]]
    assert window.cursor_rows == 0
    assert kv.cursor_rows == SPAN
    # Both took part in the one architectural transition ADR-003 8.6 requires.
    assert window.generation == kv.generation == 1
    assert not window.open_prepare and not kv.open_prepare


def test_the_span_is_still_bounded_for_a_staged_resource() -> None:
    """A21 removes no guard from ``REQUEST_SPAN``: an overflowing append still
    traps, and the trap still names the resource."""
    capability, deployment, ids = _two_state_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    capacity = session.states[ids["kv_state"]].capacity_rows
    result = device.run_transaction(
        session,
        entrypoint_id=0,
        symbols={int(Symbol.SPAN_TOKENS): capacity + 1},
    )
    assert result.trap_class == 4
    assert "exceeds capacity" in result.message
    assert str(ids["kv_state"]) in result.message


def test_every_state_descriptor_in_the_suite_declares_a_registered_policy() -> None:
    _, deployment, _ = _two_state_deployment()
    for state_id in deployment.table.ids_of_type(
        int(ExtendedDescriptorType.STATE)
    ):
        assert deployment.table[state_id].payload["commit_policy"] in {
            int(member) for member in CommitPolicy
        }


# ---------------------------------------------------------------------------
# 4. amendment A25: a ring is both a KV cache and a fixed window
# ---------------------------------------------------------------------------
#: The saturating window, and a span more than twice as long as it: the shape
#: of the wall ``TA-DS-CTX-129-1`` reached, where the span exceeds the ring and
#: the ring wraps more than once.
RING_ROWS = 8
RING_ROW_BYTES = 16
RING_SPAN = 21


def _ring_deployment(
    *, capacity_rows: int = RING_ROWS, modulus: int = RING_ROWS
) -> tuple[Capability, object, dict[str, int]]:
    """One state resource staged by a scatter through a ring index table.

    This is the DeepSeek sliding window's shape, reduced: a ring table of
    ``position mod modulus``, a ``DMA.SCATTER`` that writes the resource's
    prepared image through it, and a capacity that is a whole number of rings.
    """
    from runtime.sim.generators import digest_of, generate

    captured: dict[str, int] = {}

    def program(builder, ids):
        rows = capacity_rows
        window_bytes = rows * RING_ROW_BYTES
        parameters = {"count": 4 * RING_SPAN, "modulus": modulus}
        payload = generate("ring_indices_v1", parameters)
        index_object = builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=int(payload.nbytes),
            source=ObjectSource.generated(
                "ring_indices_v1", parameters, int(payload.nbytes), digest_of(
                    "ring_indices_v1", parameters
                )
            ),
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        source_object = builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=RING_SPAN * RING_ROW_BYTES,
            source=ObjectSource.zeros(RING_SPAN * RING_ROW_BYTES),
            permissions=int(Permission.READ | Permission.WRITE),
        )
        committed = builder.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=window_bytes,
            source=ObjectSource.zeros(window_bytes),
            permissions=int(Permission.READ | Permission.STATE_COMMIT),
        )
        prepared = builder.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=window_bytes,
            source=ObjectSource.zeros(window_bytes),
            permissions=int(Permission.READ | Permission.STATE_PREPARE),
        )
        index_view = builder.tensor_view(
            object_id=index_object, dtype=DType.U32, dims=[RING_SPAN]
        )
        source_view = builder.tensor_view(
            object_id=source_object,
            dtype=DType.BF16,
            dims=[RING_SPAN, RING_ROW_BYTES // 2],
            permissions=int(Permission.READ | Permission.WRITE),
        )
        window_view = builder.tensor_view(
            object_id=prepared,
            dtype=DType.BF16,
            dims=[rows, RING_ROW_BYTES // 2],
            permissions=int(Permission.READ | Permission.WRITE),
        )
        window = builder.state(
            state_class=StateClass.KV_CACHE,
            committed_object_id=committed,
            prepared_object_id=prepared,
            row_bytes=RING_ROW_BYTES,
            capacity_rows=rows,
            element_dtype=DType.BF16,
            view_descriptor_id=window_view,
        )
        dma_schedule = builder.schedule(
            engine_family=Major.DMA, tile_rows=8, tile_cols=8, tile_depth=1
        )
        stage = builder.operator(
            engine_family=Major.DMA,
            engine_sub=Dma.SCATTER,
            inputs=[index_view, source_view],
            outputs=[window_view],
            numeric_profile_id=ids["numeric"],
            schedule_id=dma_schedule,
        )
        captured["window_state"] = window
        captured["window_prepared"] = prepared
        captured["index_object"] = index_object

        builder.emit(Major.STATE, State.PREPARE, descriptor_id=window)
        builder.emit(Major.DMA, Dma.SCATTER, descriptor_id=stage)
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=window)
        builder.emit(Major.CONTROL, Control.COMPLETE)

    capability = probe_capability()
    deployment = probe_deployment(capability, program=program)
    return capability, deployment, captured


def test_the_document_defines_the_saturating_policy() -> None:
    assert "### 12.16 Amendment A25" in DOC_TEXT
    assert "| A25 |" in DOC_TEXT, "amendment index section 14 does not list A25"


def test_a_ring_staged_resource_declares_saturating() -> None:
    """The policy is derived, not chosen: the ring table is a fact about the
    deployment, and a scatter's index names its *destination* rows."""
    _, deployment, ids = _ring_deployment()
    rings = ring_staged_objects(deployment.table, deployment.objects)
    window = deployment.table[ids["window_state"]]
    assert rings[ids["window_prepared"]] == frozenset({RING_ROWS})
    assert window.payload["commit_policy"] == int(CommitPolicy.SATURATING)


def test_a_ring_that_does_not_divide_its_capacity_is_refused() -> None:
    """Amendment A25 describes a row axis that is a whole number of rings.  A
    modulus that is not one leaves the row axis undefined, and the builder
    refuses rather than picking whichever of the two numbers it prefers."""
    from runtime.abi3.builder import BuildError

    with pytest.raises(BuildError, match="whole divisor"):
        _ring_deployment(capacity_rows=RING_ROWS, modulus=RING_ROWS - 3)


def test_an_absolute_index_is_not_a_ring() -> None:
    """A KV cache whose row axis genuinely is the token axis keeps
    ``REQUEST_SPAN``: the discriminator is the ring, not the merge or the
    capacity."""
    _, deployment, ids = _two_state_deployment()
    assert ring_staged_objects(deployment.table, deployment.objects) == {}
    assert deployment.table[ids["kv_state"]].payload["commit_policy"] == int(
        CommitPolicy.REQUEST_SPAN
    )


def test_a_span_longer_than_the_ring_commits_the_ring_and_does_not_trap() -> None:
    """The wall ``TA-DS-CTX-129-1`` reached, reduced and cleared.

    Before A25 this transaction failed with `committing 21 rows at cursor 0
    with 0 already staged exceeds capacity 8`, whatever a backend did, because
    the count came from the request rather than from the resource's ring.
    """
    capability, deployment, ids = _ring_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    result = device.run_transaction(
        session,
        entrypoint_id=0,
        symbols={int(Symbol.SPAN_TOKENS): RING_SPAN},
    )

    assert result.trap_class == 0, result.message
    counters = result.counters
    assert counters["state.commits"] == 1
    assert counters["state.saturated_commits"] == 1
    # The ring publishes its own rows and says how many it did not.
    assert counters["state.rows_committed"] == RING_ROWS
    assert counters["state.rows_clipped"] == RING_SPAN - RING_ROWS

    window = session.states[ids["window_state"]]
    # The cursor is the ring head: the slot the next absolute position writes.
    assert window.cursor_rows == RING_SPAN % RING_ROWS
    assert window.generation == 1
    assert not window.open_prepare


def test_below_the_ring_a_saturating_commit_is_the_pre_a25_commit() -> None:
    """A25 changes nothing below the window, which is why no run before
    ``TA-DS-CTX-129-1`` could have found the defect: with a span the ring does
    not clip, the published rows, the bytes and the cursor are what
    ``REQUEST_SPAN`` produced."""
    capability, deployment, ids = _ring_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    span = RING_ROWS - 3
    result = device.run_transaction(
        session,
        entrypoint_id=0,
        symbols={int(Symbol.SPAN_TOKENS): span},
    )
    assert result.trap_class == 0, result.message
    assert result.counters["state.rows_committed"] == span
    assert result.counters.get("state.rows_clipped", 0) == 0
    assert session.states[ids["window_state"]].cursor_rows == span


def test_a_saturating_commit_publishes_the_ring_in_slot_order() -> None:
    """Which rows survive and where they land.

    ``runtime/reference/kv_window.py`` is the authority: a fresh prefill longer
    than the window "retains only the final ``W`` input rows in circular slot
    order", absolute position ``p`` at slot ``p mod W``.  The committed image
    must therefore equal the prepared image slot for slot over the whole ring,
    and the two runs the wrap splits the copy into must reassemble it.
    """
    capability, deployment, ids = _ring_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    resource = session.states[ids["window_state"]]
    memory = device.node_memories[0]
    # Distinguish every slot of the prepared image before the commit.
    prepared = memory[resource.prepared_object_id]
    prepared.write(0, bytes(range(1, RING_ROWS * RING_ROW_BYTES + 1)))

    device.run_transaction(
        session,
        entrypoint_id=0,
        symbols={int(Symbol.SPAN_TOKENS): RING_SPAN},
    )
    committed = memory[resource.committed_object_id]
    total = RING_ROWS * RING_ROW_BYTES
    assert bytes(committed.read(0, total)) == bytes(prepared.read(0, total))


@pytest.mark.parametrize("window", [4, 8, 128])
def test_the_published_slots_are_the_reference_operators(window: int) -> None:
    """A25 describes what the reference already does, and this is the check.

    ``runtime/reference/kv_window.py`` is the frozen reading of the pinned
    ``inference/model.py``.  Its ``_write_plan`` returns, for a fresh prefill of
    ``S`` tokens and for a decode step at absolute position ``N``, the exact
    destination slot ranges the released model assigns.  The device's commit
    runs must be those ranges, in that order, for every sequence length either
    side of the window and for a decode step at every slot -- otherwise the ABI
    has invented a rule beside the operator rather than described it.
    """
    from runtime.reference.kv_window import _write_plan
    from runtime.sim.device import Device, PendingCommit, StateResource

    def runs_for(cursor: int, span: int) -> list[tuple[int, int]]:
        resource = StateResource(
            descriptor_id=0,
            state_class=int(StateClass.KV_CACHE),
            committed_object_id=0,
            prepared_object_id=1,
            row_bytes=2,
            capacity_rows=window,
            commit_policy=int(CommitPolicy.SATURATING),
            cursor_rows=cursor,
        )
        commit = PendingCommit(resource, min(span, window), span)
        return [
            (slot, slot + count)
            for _source, slot, count in Device._commit_runs(commit)
        ]

    for length in range(1, 3 * window + 2):
        _mode, segments, _rows, _a, _b = _write_plan(
            start_pos=0, sequence_length=length, window_size=window
        )
        expected = [
            (segment.destination_slot_start, segment.destination_slot_stop)
            for segment in segments
        ]
        assert runs_for(0, length) == expected, f"prefill of {length}"

    for position in range(1, 2 * window + 3):
        _mode, segments, _rows, _a, _b = _write_plan(
            start_pos=position, sequence_length=1, window_size=window
        )
        expected = [
            (segment.destination_slot_start, segment.destination_slot_stop)
            for segment in segments
        ]
        # The cursor a prefill of ``position`` tokens leaves behind is the ring
        # head the reference's decode branch computes independently.
        assert runs_for(position % window, 1) == expected, f"decode at {position}"


def test_the_ring_head_survives_across_transactions() -> None:
    """The cursor is session state, and a ring's cursor is a slot.

    A prefill of twenty-one positions into an eight-slot ring leaves the head at
    ``21 mod 8 = 5``; the next transaction's single position must publish slot 5
    and leave the head at 6.  That is the released model's decode rule --
    ``start_pos % win`` -- reached by advancing the cursor rather than by a
    separate decode case, and it only holds if the modular advance persists
    past the transaction that made it.
    """
    capability, deployment, ids = _ring_deployment()
    device = Device(deployment, capability, verify=False)
    session = device.create_session()
    device.run_transaction(
        session, entrypoint_id=0, symbols={int(Symbol.SPAN_TOKENS): RING_SPAN}
    )
    window = session.states[ids["window_state"]]
    assert window.cursor_rows == RING_SPAN % RING_ROWS

    result = device.run_transaction(
        session, entrypoint_id=0, symbols={int(Symbol.SPAN_TOKENS): 1}
    )
    assert result.trap_class == 0, result.message
    assert result.counters["state.rows_committed"] == 1
    assert result.counters.get("state.rows_clipped", 0) == 0
    assert window.cursor_rows == (RING_SPAN + 1) % RING_ROWS
    assert window.generation == 2
