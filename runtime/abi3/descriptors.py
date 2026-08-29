"""ABI 3.0 typed descriptor records.

Section 5 of ``TA-ABI3-WIRE-1`` freezes the 64-byte descriptor header and the
type registry.  The typed payloads are frozen here, at ``TA-A3-ARCH-0``, under
the header's own versioning fields (``type_major`` / ``type_minor``).

Three amendments were made when the contract was frozen; each is recorded in
``docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md``:

``TA-A3-ARCH-0-A3``
    Descriptor type ``PREDICATE = 0x000f`` is assigned.  ADR-003 section 5.2
    requires architectural predicates and the instruction record already
    carries a predicate ID, but the original registry had no descriptor for
    one.  Assigning a previously unused type value is additive.

``TA-A3-ARCH-0-A4``
    A tensor view may carry up to four *dynamic index terms*.  Each term adds
    ``selector_value * element_stride`` elements to the view's element offset,
    where the selector is either a loop induction variable or a bound runtime
    symbol.  Without this, ABI 3.0 could not express the loop-compressed
    programs that ADR-003 section 5.1 mandates: a loop over tiles must be able
    to move the tile window without one descriptor per tile.

``TA-A3-ARCH-0-A5``
    The frozen runtime-symbol registry (:class:`Symbol`) names the request-bound
    scalars that loop bounds, predicates and dynamic terms may read.  ADR-003
    section 5.2 lists these by prose; the registry gives them stable numbers.

Every payload is a whole number of 64-byte units so that the header rule
"total size is a positive multiple of 64 bytes" holds by construction.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field as dc_field
from typing import Any, ClassVar, Mapping, Sequence

from .constants import (
    DESCRIPTOR_ALIGNMENT,
    DESCRIPTOR_HEADER_BYTES,
    DESCRIPTOR_MAGIC,
    DESCRIPTOR_PAYLOAD_OFFSET,
    NO_ID,
    NO_NODE,
    DescriptorType,
    Permission,
    PERMISSION_MASK,
)
from .crc import record_crc
from .layout import Field, Layout, RecordError

TYPE_MAJOR = 1
TYPE_MINOR = 0

MAX_RANK = 6
MAX_DYNAMIC_TERMS = 4
MAX_WAIT_PRODUCERS = 12
MAX_EOS_TOKENS = 8
MAX_COUNTERS_PER_CLASS = 12
MAX_LOOP_DEPTH = 4


# ---------------------------------------------------------------------------
# Amendment A3: predicate descriptor type
# ---------------------------------------------------------------------------
PREDICATE_TYPE = 0x000F


class ExtendedDescriptorType(enum.IntEnum):
    """Registry of section 5 plus amendment A3."""

    MEMORY_OBJECT = DescriptorType.MEMORY_OBJECT
    TENSOR_VIEW = DescriptorType.TENSOR_VIEW
    NUMERIC = DescriptorType.NUMERIC
    SCHEDULE = DescriptorType.SCHEDULE
    TOPOLOGY = DescriptorType.TOPOLOGY
    COMMUNICATION = DescriptorType.COMMUNICATION
    STATE = DescriptorType.STATE
    EVENT_WAIT_SET = DescriptorType.EVENT_WAIT_SET
    LOOP_CONTROL = DescriptorType.LOOP_CONTROL
    OPERATOR = DescriptorType.OPERATOR
    GENERATION_POLICY = DescriptorType.GENERATION_POLICY
    COUNTER_CLASS = DescriptorType.COUNTER_CLASS
    ENTRYPOINT_TABLE = DescriptorType.ENTRYPOINT_TABLE
    SIGNATURE_METADATA = DescriptorType.SIGNATURE_METADATA
    PREDICATE = PREDICATE_TYPE


# ---------------------------------------------------------------------------
# Amendment A5: frozen runtime-symbol registry
# ---------------------------------------------------------------------------
class Symbol(enum.IntEnum):
    """Request-bound scalars readable by loops, predicates and dynamic terms."""

    SPAN_TOKENS = 0
    POSITION_START = 1
    POSITION_END = 2
    CONTEXT_LENGTH = 3
    PHASE = 4
    GENERATION_INDEX = 5
    MAX_NEW_TOKENS = 6
    BATCH = 7
    NODE_ID = 8
    NODE_COUNT = 9
    ACTIVE_EXPERT_COUNT = 10
    SPARSE_INDEX_COUNT = 11
    LAYER_COUNT = 12
    VOCABULARY_PARTITIONS = 13


class Phase(enum.IntEnum):
    PREFILL = 0
    DECODE = 1


class SelectorKind(enum.IntEnum):
    """How a dynamic tensor-view term or loop bound resolves its value."""

    LOOP_INDUCTION = 0
    RUNTIME_SYMBOL = 1
    CONSTANT = 2


class PredicateKind(enum.IntEnum):
    ALWAYS = 0
    PHASE_IS = 1
    COMPARE_SYMBOL = 2
    ENGINE_STATUS = 3
    ROUTE_VALID = 4
    EOS_MEMBER = 5
    LOOP_FIRST = 6
    LOOP_LAST = 7
    BOOLEAN_OBJECT = 8
    COMPARE_LOOP = 9


class Comparison(enum.IntEnum):
    EQ = 0
    NE = 1
    LT = 2
    LE = 3
    GT = 4
    GE = 5


class CollectiveOp(enum.IntEnum):
    POINT_TO_POINT = 0
    SUM = 1
    MAX = 2
    MIN = 3
    CONCAT = 4
    BROADCAST = 5
    ALL_GATHER = 6
    REDUCE_SCATTER = 7


class SelectionMode(enum.IntEnum):
    GREEDY_ARGMAX_LOWEST_ID = 0
    SAMPLE = 1


class LayoutClass(enum.IntEnum):
    DENSE = 0
    TILED = 1
    BLOCK_SCALED = 2


class SignatureScheme(enum.IntEnum):
    UNSIGNED_PUBLIC_BUILD = 0
    ED25519 = 1


# ---------------------------------------------------------------------------
# Common 64-byte descriptor header (wire format section 5)
# ---------------------------------------------------------------------------
DESCRIPTOR_HEADER = Layout(
    "descriptor_header",
    DESCRIPTOR_HEADER_BYTES,
    [
        Field("magic", 0, 4, "magic", DESCRIPTOR_MAGIC),
        Field("descriptor_type", 4, 2),
        Field("type_major", 6, 1),
        Field("type_minor", 7, 1),
        Field("total_bytes", 8, 4),
        Field("flags", 12, 4),
        Field("primary_object_id", 16, 4),
        Field("secondary_object_id", 20, 4),
        Field("numeric_profile_id", 24, 4),
        Field("schedule_id", 28, 4),
        Field("permissions", 32, 4),
        Field("owner_scope_id", 36, 4),
        Field("payload_offset", 40, 4),
        Field("payload_bytes", 44, 4),
        Field("record_crc", 48, 4),
        Field("reserved", 52, 12, "reserved"),
    ],
    crc_field="record_crc",
)


def _pad(fields: list[Field], offset: int, total: int, index: int = 0) -> list[Field]:
    if offset < total:
        fields.append(
            Field(f"pad_{index}" if index else "pad", offset, total - offset, "reserved")
        )
    return fields


def _u32_array(prefix: str, offset: int, count: int) -> list[Field]:
    return [Field(f"{prefix}{i}", offset + 4 * i, 4) for i in range(count)]


# ---------------------------------------------------------------------------
# Typed payload layouts
# ---------------------------------------------------------------------------
MEMORY_OBJECT_PAYLOAD = Layout(
    "memory_object",
    64,
    [
        Field("storage_class", 0, 1),
        Field("integrity_mode", 1, 1),
        Field("alignment_log2", 2, 1),
        Field("reserved_0", 3, 1, "reserved"),
        Field("node_id", 4, 2),
        Field("bank_or_tile", 6, 2),
        Field("base_address", 8, 8),
        Field("size_bytes", 16, 8),
        Field("replica_group_id", 24, 4),
        Field("reserved_1", 28, 4, "reserved"),
        Field("content_digest", 32, 32, "bytes"),
    ],
)

TENSOR_VIEW_PAYLOAD = Layout(
    "tensor_view",
    128,
    [
        Field("dtype", 0, 1),
        Field("rank", 1, 1),
        Field("layout_class", 2, 1),
        Field("dynamic_term_count", 3, 1),
        Field("scale_object_id", 4, 4),
        Field("scale_block_elements", 8, 4),
        Field("edge_mask_id", 12, 4),
        Field("element_offset", 16, 8),
        *[Field(f"dim{i}", 24 + 4 * i, 4) for i in range(MAX_RANK)],
        *[Field(f"stride{i}", 48 + 4 * i, 4) for i in range(MAX_RANK)],
        *[
            item
            for i in range(MAX_DYNAMIC_TERMS)
            for item in (
                Field(f"term{i}_kind", 72 + 8 * i, 2),
                Field(f"term{i}_index", 74 + 8 * i, 2),
                Field(f"term{i}_stride", 76 + 8 * i, 4),
            )
        ],
        Field("reserved", 104, 24, "reserved"),
    ],
)

NUMERIC_PAYLOAD = Layout(
    "numeric",
    64,
    [
        Field("input_dtype", 0, 1),
        Field("second_input_dtype", 1, 1),
        Field("accumulator_dtype", 2, 1),
        Field("output_dtype", 3, 1),
        Field("rounding_mode", 4, 1),
        Field("reduction_order", 5, 1),
        Field("saturate", 6, 1),
        Field("nan_policy", 7, 1),
        Field("epsilon_bits", 8, 4),
        Field("scale_bits", 12, 4),
        Field("flags", 16, 4),
        Field("reserved_0", 20, 4, "reserved"),
        Field("reserved_1", 24, 8, "reserved"),
        Field("contract_digest", 32, 32, "bytes"),
    ],
)

SCHEDULE_PAYLOAD = Layout(
    "schedule",
    64,
    [
        Field("engine_family", 0, 1),
        Field("queue_index", 1, 1),
        Field("issue_window", 2, 2),
        Field("tile_rows", 4, 4),
        Field("tile_cols", 8, 4),
        Field("tile_depth", 12, 4),
        Field("bank_mask", 16, 4),
        Field("port_mask", 20, 4),
        Field("noc_route_class", 24, 4),
        Field("resource_bound", 28, 4),
        Field("max_outstanding", 32, 4),
        Field("priority", 36, 4),
        Field("reserved", 40, 24, "reserved"),
    ],
)

TOPOLOGY_PAYLOAD = Layout(
    "topology",
    192,
    [
        Field("topology_class", 0, 1),
        Field("reserved_0", 1, 1, "reserved"),
        Field("node_count", 2, 2),
        Field("reticle_count", 4, 2),
        Field("tiles_per_reticle", 6, 2),
        Field("local_node_id", 8, 2),
        Field("local_reticle_id", 10, 2),
        Field("local_tile_id", 12, 2),
        Field("link_class_count", 14, 2),
        Field("active_resource_count", 16, 4),
        Field("quarantined_resource_count", 20, 4),
        Field("hbm_bytes_per_node", 24, 8),
        Field("sram_bytes_per_node", 32, 8),
        Field("link_count", 40, 4),
        Field("route_group_count", 44, 4),
        Field("epoch", 48, 4),
        Field("bisection_link_count", 52, 4),
        Field("reserved_1", 56, 8, "reserved"),
        Field("active_resource_digest", 64, 32, "bytes"),
        Field("quarantine_digest", 96, 32, "bytes"),
        Field("route_table_digest", 128, 32, "bytes"),
        Field("health_digest", 160, 32, "bytes"),
    ],
)

COMMUNICATION_PAYLOAD = Layout(
    "communication",
    128,
    [
        Field("collective_op", 0, 1),
        Field("ordering", 1, 1),
        Field("integrity_mode", 2, 1),
        Field("virtual_channel", 3, 1),
        Field("source_node", 4, 2),
        Field("destination_node", 6, 2),
        Field("group_id", 8, 4),
        Field("route_class", 12, 4),
        Field("local_object_id", 16, 4),
        Field("remote_object_id", 20, 4),
        Field("local_offset", 24, 8),
        Field("remote_offset", 32, 8),
        Field("byte_extent", 40, 8),
        Field("credit_bound", 48, 4),
        Field("retry_bound", 52, 4),
        Field("timeout_class", 56, 4),
        Field("completion_event_id", 60, 4),
        Field("reduction_numeric_id", 64, 4),
        Field("counter_class_id", 68, 4),
        Field("participant_count", 72, 4),
        Field("chunk_bytes", 76, 4),
        Field("reserved", 80, 48, "reserved"),
    ],
)

STATE_PAYLOAD = Layout(
    "state",
    128,
    [
        Field("state_class", 0, 1),
        Field("commit_policy", 1, 1),
        Field("element_dtype", 2, 1),
        Field("reserved_0", 3, 1, "reserved"),
        Field("session_binding_id", 4, 4),
        Field("committed_object_id", 8, 4),
        Field("prepared_object_id", 12, 4),
        Field("row_bytes", 16, 8),
        Field("capacity_rows", 24, 8),
        Field("initial_cursor_rows", 32, 8),
        Field("generation_bits", 40, 4),
        Field("counter_class_id", 44, 4),
        Field("view_descriptor_id", 48, 4),
        Field("node_id", 52, 4),
        Field("reserved_1", 56, 8, "reserved"),
        Field("initial_digest", 64, 32, "bytes"),
        Field("reserved_2", 96, 32, "reserved"),
    ],
)

EVENT_WAIT_SET_PAYLOAD = Layout(
    "event_wait_set",
    64,
    [
        Field("condition", 0, 1),
        Field("ordering", 1, 1),
        Field("scope", 2, 1),
        Field("producer_count", 3, 1),
        Field("timeout_class", 4, 4),
        *_u32_array("producer_", 8, MAX_WAIT_PRODUCERS),
        Field("required_count", 56, 4),
        Field("reserved", 60, 4, "reserved"),
    ],
)

LOOP_CONTROL_PAYLOAD = Layout(
    "loop_control",
    64,
    [
        Field("loop_index", 0, 1),
        Field("bound_selector_kind", 1, 1),
        Field("reserved_0", 2, 2, "reserved"),
        Field("lower_bound", 4, 4),
        Field("upper_bound", 8, 4),
        Field("step", 12, 4),
        Field("max_iterations", 16, 4),
        Field("predicate_id", 20, 4),
        Field("bound_symbol_id", 24, 4),
        Field("body_start", 28, 4),
        Field("body_end", 32, 4),
        Field("counter_class_id", 36, 4),
        Field("bound_divisor", 40, 4),
        Field("reserved_1", 44, 20, "reserved"),
    ],
)

OPERATOR_PAYLOAD = Layout(
    "operator",
    64,
    [
        Field("engine_family", 0, 1),
        Field("engine_sub", 1, 1),
        Field("flags", 2, 2),
        Field("source_graph_operation_id", 4, 4),
        Field("source_kernel_id", 8, 4),
        Field("counter_class_id", 12, 4),
        Field("numeric_profile_id", 16, 4),
        Field("schedule_id", 20, 4),
        *_u32_array("input_view_", 24, 4),
        *_u32_array("output_view_", 40, 2),
        *_u32_array("aux_id_", 48, 4),
    ],
)

GENERATION_POLICY_PAYLOAD = Layout(
    "generation_policy",
    64,
    [
        Field("selection_mode", 0, 1),
        Field("tie_rule", 1, 1),
        Field("eos_count", 2, 2),
        Field("max_new_tokens", 4, 4),
        Field("vocabulary_size", 8, 4),
        Field("token_ring_object_id", 12, 4),
        *_u32_array("eos_token_", 16, MAX_EOS_TOKENS),
        Field("rng_seed_lo", 48, 4),
        Field("rng_seed_hi", 52, 4),
        Field("counter_class_id", 56, 4),
        Field("reserved", 60, 4, "reserved"),
    ],
)

COUNTER_CLASS_PAYLOAD = Layout(
    "counter_class",
    64,
    [
        Field("group", 0, 1),
        Field("event_count", 1, 1),
        Field("reserved_0", 2, 2, "reserved"),
        Field("reserved_1", 4, 4, "reserved"),
        *_u32_array("counter_", 8, MAX_COUNTERS_PER_CLASS),
        Field("reserved_2", 56, 8, "reserved"),
    ],
)

PREDICATE_PAYLOAD = Layout(
    "predicate",
    64,
    [
        Field("predicate_kind", 0, 1),
        Field("comparison", 1, 1),
        Field("selector_kind", 2, 1),
        Field("reserved_0", 3, 1, "reserved"),
        Field("selector_index", 4, 4),
        Field("immediate", 8, 8),
        Field("object_id", 16, 4),
        Field("element_index", 20, 4),
        Field("reserved_1", 24, 40, "reserved"),
    ],
)

SIGNATURE_METADATA_PAYLOAD = Layout(
    "signature_metadata",
    128,
    [
        Field("scheme", 0, 1),
        Field("reserved_0", 1, 1, "reserved"),
        Field("signature_bytes", 2, 2),
        Field("key_id", 4, 4),
        Field("manifest_digest", 8, 32, "bytes"),
        Field("signature", 40, 64, "bytes"),
        Field("reserved_1", 104, 24, "reserved"),
    ],
)

ENTRYPOINT_HEADER_PAYLOAD = Layout(
    "entrypoint_table_header",
    16,
    [
        Field("entrypoint_count", 0, 4),
        Field("reserved_0", 4, 4, "reserved"),
        Field("reserved_1", 8, 8, "reserved"),
    ],
)

ENTRYPOINT_ENTRY = Layout(
    "entrypoint_entry",
    16,
    [
        Field("entrypoint_id", 0, 4),
        Field("first_instruction", 4, 4),
        Field("phase", 8, 4),
        Field("generation_policy_id", 12, 4),
    ],
)


PAYLOAD_LAYOUTS: dict[int, Layout] = {
    ExtendedDescriptorType.MEMORY_OBJECT: MEMORY_OBJECT_PAYLOAD,
    ExtendedDescriptorType.TENSOR_VIEW: TENSOR_VIEW_PAYLOAD,
    ExtendedDescriptorType.NUMERIC: NUMERIC_PAYLOAD,
    ExtendedDescriptorType.SCHEDULE: SCHEDULE_PAYLOAD,
    ExtendedDescriptorType.TOPOLOGY: TOPOLOGY_PAYLOAD,
    ExtendedDescriptorType.COMMUNICATION: COMMUNICATION_PAYLOAD,
    ExtendedDescriptorType.STATE: STATE_PAYLOAD,
    ExtendedDescriptorType.EVENT_WAIT_SET: EVENT_WAIT_SET_PAYLOAD,
    ExtendedDescriptorType.LOOP_CONTROL: LOOP_CONTROL_PAYLOAD,
    ExtendedDescriptorType.OPERATOR: OPERATOR_PAYLOAD,
    ExtendedDescriptorType.GENERATION_POLICY: GENERATION_POLICY_PAYLOAD,
    ExtendedDescriptorType.COUNTER_CLASS: COUNTER_CLASS_PAYLOAD,
    ExtendedDescriptorType.PREDICATE: PREDICATE_PAYLOAD,
    ExtendedDescriptorType.SIGNATURE_METADATA: SIGNATURE_METADATA_PAYLOAD,
}
"""Fixed-payload descriptor types.  ``ENTRYPOINT_TABLE`` is variable length."""


@dataclass(slots=True)
class Descriptor:
    """One typed descriptor: common header plus decoded payload fields."""

    descriptor_id: int
    descriptor_type: int
    payload: dict[str, Any]
    flags: int = 0
    primary_object_id: int = NO_ID
    secondary_object_id: int = NO_ID
    numeric_profile_id: int = NO_ID
    schedule_id: int = NO_ID
    permissions: int = 0
    owner_scope_id: int = 0
    type_major: int = TYPE_MAJOR
    type_minor: int = TYPE_MINOR
    raw_payload: bytes | None = None

    def _payload_bytes(self) -> bytes:
        if self.raw_payload is not None:
            return self.raw_payload
        try:
            layout = PAYLOAD_LAYOUTS[self.descriptor_type]
        except KeyError:
            raise RecordError(
                f"descriptor type {self.descriptor_type:#06x} has no fixed payload; "
                "supply raw_payload"
            ) from None
        return bytes(layout.encode(self.payload))

    def encode(self) -> bytes:
        ExtendedDescriptorType(self.descriptor_type)
        if self.permissions & ~PERMISSION_MASK:
            raise RecordError("permission bits 8..31 are reserved and must be zero")
        immutable = bool(self.permissions & Permission.IMMUTABLE)
        writable = bool(self.permissions & (Permission.WRITE | Permission.STATE_COMMIT))
        if immutable and writable:
            raise RecordError("a descriptor cannot be both IMMUTABLE and writable")
        payload = self._payload_bytes()
        total = DESCRIPTOR_HEADER_BYTES + len(payload)
        padded = (total + DESCRIPTOR_ALIGNMENT - 1) // DESCRIPTOR_ALIGNMENT
        padded *= DESCRIPTOR_ALIGNMENT
        header = DESCRIPTOR_HEADER.encode(
            {
                "descriptor_type": self.descriptor_type,
                "type_major": self.type_major,
                "type_minor": self.type_minor,
                "total_bytes": padded,
                "flags": self.flags,
                "primary_object_id": self.primary_object_id,
                "secondary_object_id": self.secondary_object_id,
                "numeric_profile_id": self.numeric_profile_id,
                "schedule_id": self.schedule_id,
                "permissions": self.permissions,
                "owner_scope_id": self.owner_scope_id,
                "payload_offset": DESCRIPTOR_PAYLOAD_OFFSET,
                "payload_bytes": len(payload),
                "record_crc": 0,
            }
        )
        record = bytearray(padded)
        record[:DESCRIPTOR_HEADER_BYTES] = header
        record[DESCRIPTOR_HEADER_BYTES : DESCRIPTOR_HEADER_BYTES + len(payload)] = payload
        crc = record_crc(bytes(record), DESCRIPTOR_HEADER.crc_offset())
        offset = DESCRIPTOR_HEADER.crc_offset()
        record[offset : offset + 4] = crc.to_bytes(4, "little")
        return bytes(record)

    @classmethod
    def decode(cls, record: bytes, descriptor_id: int = NO_ID) -> "Descriptor":
        if len(record) < DESCRIPTOR_HEADER_BYTES:
            raise RecordError("descriptor shorter than its header")
        values = DESCRIPTOR_HEADER.decode(record[:DESCRIPTOR_HEADER_BYTES])
        total = values["total_bytes"]
        if total != len(record):
            raise RecordError(
                f"descriptor total_bytes {total} does not match record length "
                f"{len(record)}"
            )
        if total % DESCRIPTOR_ALIGNMENT or total < DESCRIPTOR_HEADER_BYTES + 1:
            raise RecordError("descriptor size is not a positive multiple of 64")
        expected = record_crc(record, DESCRIPTOR_HEADER.crc_offset())
        if values["record_crc"] != expected:
            raise RecordError("descriptor CRC32C mismatch")
        if values["payload_offset"] != DESCRIPTOR_PAYLOAD_OFFSET:
            raise RecordError("descriptor payload_offset is not 64 in version 3.0")
        if values["type_major"] != TYPE_MAJOR:
            raise RecordError(
                f"unsupported descriptor type_major {values['type_major']}"
            )
        if values["type_minor"] > TYPE_MINOR:
            raise RecordError(
                f"descriptor requires type_minor {values['type_minor']}"
            )
        dtype = values["descriptor_type"]
        ExtendedDescriptorType(dtype)
        payload_bytes = values["payload_bytes"]
        start = DESCRIPTOR_PAYLOAD_OFFSET
        end = start + payload_bytes
        if end > total:
            raise RecordError("descriptor payload runs past the record")
        if any(record[end:total]):
            raise RecordError("descriptor padding is not zero")
        blob = record[start:end]
        layout = PAYLOAD_LAYOUTS.get(dtype)
        payload = layout.decode(blob) if layout is not None else {}
        if layout is not None and payload_bytes != layout.size:
            raise RecordError(
                f"descriptor type {dtype:#06x} payload is {payload_bytes} bytes, "
                f"expected {layout.size}"
            )
        if values["permissions"] & ~PERMISSION_MASK:
            raise RecordError("permission bits 8..31 are reserved")
        return cls(
            descriptor_id=descriptor_id,
            descriptor_type=dtype,
            payload=payload,
            flags=values["flags"],
            primary_object_id=values["primary_object_id"],
            secondary_object_id=values["secondary_object_id"],
            numeric_profile_id=values["numeric_profile_id"],
            schedule_id=values["schedule_id"],
            permissions=values["permissions"],
            owner_scope_id=values["owner_scope_id"],
            type_major=values["type_major"],
            type_minor=values["type_minor"],
            raw_payload=blob if layout is None else None,
        )

    @property
    def type_name(self) -> str:
        return ExtendedDescriptorType(self.descriptor_type).name


def encode_entrypoint_table(
    entries: Sequence[Mapping[str, int]],
) -> bytes:
    """Encode the variable-length entrypoint-table payload."""
    if not entries:
        raise RecordError("entrypoint table must contain at least one entry")
    blob = bytearray(ENTRYPOINT_HEADER_PAYLOAD.encode({"entrypoint_count": len(entries)}))
    for entry in entries:
        blob += ENTRYPOINT_ENTRY.encode(entry)
    return bytes(blob)


def decode_entrypoint_table(blob: bytes) -> list[dict[str, int]]:
    """Decode the variable-length entrypoint-table payload, failing closed."""
    if len(blob) < ENTRYPOINT_HEADER_PAYLOAD.size:
        raise RecordError("entrypoint table payload is too short")
    head = ENTRYPOINT_HEADER_PAYLOAD.decode(blob[: ENTRYPOINT_HEADER_PAYLOAD.size])
    count = head["entrypoint_count"]
    expected = ENTRYPOINT_HEADER_PAYLOAD.size + count * ENTRYPOINT_ENTRY.size
    if count == 0:
        raise RecordError("entrypoint table declares zero entries")
    if len(blob) != expected:
        raise RecordError(
            f"entrypoint table is {len(blob)} bytes, expected {expected}"
        )
    out = []
    offset = ENTRYPOINT_HEADER_PAYLOAD.size
    for _ in range(count):
        out.append(ENTRYPOINT_ENTRY.decode(blob[offset : offset + ENTRYPOINT_ENTRY.size]))
        offset += ENTRYPOINT_ENTRY.size
    return out


def make_entrypoint_table(
    descriptor_id: int, entries: Sequence[Mapping[str, int]]
) -> Descriptor:
    return Descriptor(
        descriptor_id=descriptor_id,
        descriptor_type=ExtendedDescriptorType.ENTRYPOINT_TABLE,
        payload={},
        raw_payload=encode_entrypoint_table(entries),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
    )
