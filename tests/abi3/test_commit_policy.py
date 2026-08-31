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
from runtime.abi3.deployment import ObjectSource, staged_objects
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
