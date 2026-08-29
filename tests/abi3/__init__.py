"""Independent ABI 3.0 conformance suite.

This package is written *against the contract*, not against the encoder.  It
never imports :mod:`runtime.abi3.builder` to decide what a record should look
like -- the expected layouts come from the normative wire-format document, and
the illegal artifacts are produced by editing encoded bytes and re-stamping the
integrity fields, which is exactly what a hostile or corrupted bundle looks
like from the device's side of the boundary.

The helpers here are shared by more than one test module:

``restamp``
    rebuild a deployment's program header so that a deliberately edited body,
    descriptor table or header field is *internally consistent*.  Without this,
    every negative test would stop at the digest chain and would never reach the
    proof under test.
``patched_table`` / ``patched_payload``
    edit one descriptor's bytes inside an encoded table and re-derive the table
    through the public decoder, so the resulting deployment is byte-legal but
    semantically illegal.
``probe_deployment``
    the smallest deployment that passes every proof, used as the base for the
    negative verifier tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    DESCRIPTOR_ALIGNMENT,
    INSTRUCTION_BYTES,
    NO_ID,
    PROGRAM_HEADER_BYTES,
    Control,
    DType,
    Feature,
    Major,
    Permission,
    Selection,
    StateClass,
    StorageClass,
    Tensor,
    TopologyClass,
)
from runtime.abi3.crc import record_crc, sha256
from runtime.abi3.deployment import Deployment, DescriptorTable, ObjectSource
from runtime.abi3.descriptors import DESCRIPTOR_HEADER, Phase, SelectionMode
from runtime.abi3.layout import Layout
from runtime.abi3.records import ProgramHeader

ROOT = Path(__file__).resolve().parents[2]
WIRE_FORMAT_DOC = ROOT / "docs" / "TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md"
ARCHITECTURE_DOC = (
    ROOT / "docs" / "TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md"
)
CHECKER = ROOT / "tools" / "check_abi3_deployment.py"

DESCRIPTOR_CRC_OFFSET = DESCRIPTOR_HEADER.crc_offset()


# ---------------------------------------------------------------------------
# byte surgery
# ---------------------------------------------------------------------------
def flip_byte(blob: bytes, index: int) -> bytes:
    """Return ``blob`` with one byte inverted (single-bit-class corruption)."""
    edited = bytearray(blob)
    edited[index] ^= 0xFF
    return bytes(edited)


def seal_descriptor(record: bytes) -> bytes:
    """Re-stamp a descriptor record's CRC32C after an edit."""
    edited = bytearray(record)
    edited[DESCRIPTOR_CRC_OFFSET : DESCRIPTOR_CRC_OFFSET + 4] = b"\x00\x00\x00\x00"
    crc = record_crc(bytes(edited), DESCRIPTOR_CRC_OFFSET)
    edited[DESCRIPTOR_CRC_OFFSET : DESCRIPTOR_CRC_OFFSET + 4] = crc.to_bytes(4, "little")
    return bytes(edited)


def descriptor_offsets(table: DescriptorTable) -> list[int]:
    """Byte offset of every descriptor record inside the encoded table."""
    blob = table.encode()
    offsets: list[int] = []
    cursor = 0
    while cursor < len(blob):
        offsets.append(cursor)
        cursor += int.from_bytes(blob[cursor + 8 : cursor + 12], "little")
    return offsets


def patched_table(
    table: DescriptorTable, descriptor_id: int, offset: int, data: bytes
) -> DescriptorTable:
    """Overwrite bytes inside one descriptor and re-decode the whole table.

    ``offset`` is relative to the descriptor record.  The record CRC is
    re-stamped, so the result fails only the check under test.
    """
    blob = bytearray(table.encode())
    base = descriptor_offsets(table)[descriptor_id]
    total = int.from_bytes(blob[base + 8 : base + 12], "little")
    record = bytearray(blob[base : base + total])
    record[offset : offset + len(data)] = data
    blob[base : base + total] = seal_descriptor(bytes(record))
    return DescriptorTable.decode(bytes(blob))


def patched_payload(
    table: DescriptorTable,
    descriptor_id: int,
    layout: Layout,
    field: str,
    value: int,
) -> DescriptorTable:
    """Overwrite one typed-payload field of one descriptor."""
    spec = layout.field(field)
    return patched_table(
        table,
        descriptor_id,
        DESCRIPTOR_ALIGNMENT + spec.offset,
        int(value).to_bytes(spec.size, "little"),
    )


def restamp(deployment: Deployment, **overrides: Any) -> Deployment:
    """Rebuild the program header so the deployment is internally consistent.

    Accepts ``body`` (raw instruction bytes) plus any :class:`ProgramHeader`
    field.  The deployment digest is a fixed point of the manifest, which itself
    quotes the header, so the header is stamped twice exactly as a conforming
    encoder must.
    """
    old = ProgramHeader.decode(deployment.program[:PROGRAM_HEADER_BYTES])
    body = overrides.pop("body", deployment.program[PROGRAM_HEADER_BYTES:])
    fields: dict[str, Any] = {
        "instruction_count": len(body) // INSTRUCTION_BYTES,
        "entrypoint_count": old.entrypoint_count,
        "required_features": old.required_features,
        "deployment_digest": bytes(32),
        "descriptor_table_digest": deployment.table.digest,
        "topology_digest": old.topology_digest,
        "body_digest": sha256(body),
        "max_retired_work": old.max_retired_work,
        "watchdog_class": old.watchdog_class,
        "entrypoint_table_descriptor": old.entrypoint_table_descriptor,
        "signature_metadata_descriptor": old.signature_metadata_descriptor,
    }
    fields.update(overrides)
    deployment.program = ProgramHeader(**fields).encode() + body
    fields["deployment_digest"] = deployment.deployment_digest
    deployment.program = ProgramHeader(**fields).encode() + body
    return deployment


# ---------------------------------------------------------------------------
# a minimal legal deployment
# ---------------------------------------------------------------------------
def probe_capability(**limit_overrides: int) -> Capability:
    """A capability that admits :func:`probe_deployment` and little else."""
    from runtime.abi3.fixture import fixture_capability

    capability = fixture_capability()
    if limit_overrides:
        capability.limits = {**capability.limits, **limit_overrides}
    return capability


def probe_deployment(
    capability: Capability | None = None,
    *,
    program: Callable[[Any, dict[str, int]], None] | None = None,
    entrypoints: Sequence[dict[str, int]] | None = None,
    generative: bool = False,
    max_retired_work: int | None = None,
) -> Deployment:
    """Build the smallest deployment that passes every admission proof.

    ``program`` receives the builder and a mapping of descriptor IDs so a test
    can emit its own -- usually illegal -- instruction sequence.  This is the
    one place the suite uses the encoder: producing a *legal* baseline is not
    the thing under test, and hand-assembling one would only test the test.
    """
    from runtime.abi3.builder import DeploymentBuilder

    capability = capability or probe_capability()
    builder = DeploymentBuilder(
        target_id="probe", model_id="probe", backend="test", capability=capability
    )
    builder.require(Feature.BF16_TENSOR)
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    ids: dict[str, int] = {}
    ids["weights"] = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=128,
        source=ObjectSource.zeros(128),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
    )
    ids["activations"] = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=128,
        source=ObjectSource.zeros(128),
        permissions=int(Permission.READ | Permission.WRITE),
    )
    ids["tokens"] = builder.memory_object(
        storage_class=StorageClass.HOST,
        size_bytes=256,
        source=ObjectSource.zeros(256),
        permissions=int(
            Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
        ),
    )
    ids["kv_committed"] = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=1024,
        source=ObjectSource.zeros(1024),
        permissions=int(Permission.READ | Permission.STATE_COMMIT),
    )
    ids["kv_prepared"] = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=1024,
        source=ObjectSource.zeros(1024),
        permissions=int(Permission.READ | Permission.STATE_PREPARE),
    )
    ids["weight_view"] = builder.tensor_view(
        object_id=ids["weights"], dtype=DType.BF16, dims=[8, 8]
    )
    ids["activation_view"] = builder.tensor_view(
        object_id=ids["activations"],
        dtype=DType.BF16,
        dims=[8, 8],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    ids["token_view"] = builder.tensor_view(
        object_id=ids["tokens"],
        dtype=DType.U32,
        dims=[64],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    ids["numeric"] = builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    ids["loop"] = builder.loop_control(lower_bound=0, upper_bound=4, step=1)
    ids["matmul"] = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[ids["activation_view"], ids["weight_view"]],
        outputs=[ids["activation_view"]],
        numeric_profile_id=ids["numeric"],
    )
    ids["argmax"] = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[ids["activation_view"]],
        outputs=[ids["token_view"]],
        numeric_profile_id=ids["numeric"],
    )
    ids["append"] = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[ids["token_view"]],
        outputs=[ids["token_view"]],
        numeric_profile_id=ids["numeric"],
    )
    ids["state"] = builder.state(
        state_class=StateClass.KV_CACHE,
        committed_object_id=ids["kv_committed"],
        prepared_object_id=ids["kv_prepared"],
        row_bytes=16,
        capacity_rows=64,
        element_dtype=DType.BF16,
    )
    ids["policy"] = builder.generation_policy(
        eos_token_ids=[15],
        max_new_tokens=8,
        vocabulary_size=16,
        token_ring_object_id=ids["tokens"],
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
    )
    if program is not None:
        program(builder, ids)
    else:
        builder.emit(Major.STATE, 1, descriptor_id=ids["state"])  # PREPARE
        event = builder.new_event()
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            signal_event_id=event,
        )
        wait = builder.wait_set([event])
        builder.emit(
            Major.SELECTION,
            Selection.ARGMAX,
            descriptor_id=ids["argmax"],
            wait_set_id=wait,
        )
        builder.emit(
            Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=ids["append"]
        )
        builder.emit(Major.STATE, 2, descriptor_id=ids["state"])  # COMMIT
        builder.emit(Major.CONTROL, Control.COMPLETE)
    if entrypoints is None:
        builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=Phase.PREFILL,
            generation_policy_id=ids["policy"] if generative else NO_ID,
        )
    else:
        for entry in entrypoints:
            builder.entrypoint(**entry)
    deployment = builder.finish(max_retired_work=max_retired_work)
    deployment.notes["probe_ids"] = dict(ids)
    return restamp(deployment)
