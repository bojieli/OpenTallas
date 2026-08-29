"""Round-trip and fail-closed tests for all fifteen ABI 3.0 descriptor types.

Descriptors are the only thing that names memory, shape, numerics, routes and
state, so a descriptor decoder that accepts a malformed record hands the engines
an unbounded address.  Every negative case below re-stamps the record CRC after
the edit, so the rejection has to come from the rule under test.
"""

from __future__ import annotations

from typing import Any

import pytest

from runtime.abi3.constants import (
    DESCRIPTOR_ALIGNMENT,
    DESCRIPTOR_HEADER_BYTES,
    DESCRIPTOR_PAYLOAD_OFFSET,
    NO_ID,
    Permission,
    PERMISSION_MASK,
    StorageClass,
)
from runtime.abi3.crc import record_crc
from runtime.abi3.deployment import DeploymentError, DescriptorTable
from runtime.abi3.descriptors import (
    DESCRIPTOR_HEADER,
    ENTRYPOINT_ENTRY,
    ENTRYPOINT_HEADER_PAYLOAD,
    MEMORY_OBJECT_PAYLOAD,
    PAYLOAD_LAYOUTS,
    TENSOR_VIEW_PAYLOAD,
    TYPE_MAJOR,
    TYPE_MINOR,
    Descriptor,
    ExtendedDescriptorType,
    decode_entrypoint_table,
    encode_entrypoint_table,
    make_entrypoint_table,
)
from runtime.abi3.layout import Layout, RecordError

from . import seal_descriptor

ALL_TYPES = sorted(int(t) for t in ExtendedDescriptorType)
FIXED_TYPES = sorted(int(t) for t in PAYLOAD_LAYOUTS)


def zero_payload(layout: Layout) -> dict[str, Any]:
    """A structurally valid payload: every declared field at its zero value."""
    payload: dict[str, Any] = {}
    for field in layout.fields:
        if field.kind == "uint":
            payload[field.name] = 0
        elif field.kind == "bytes":
            payload[field.name] = bytes(field.size)
    return payload


def descriptor_for(descriptor_type: int, **overrides: Any) -> Descriptor:
    if descriptor_type == ExtendedDescriptorType.ENTRYPOINT_TABLE:
        base: dict[str, Any] = {
            "payload": {},
            "raw_payload": encode_entrypoint_table(
                [
                    {
                        "entrypoint_id": 0,
                        "first_instruction": 0,
                        "phase": 0,
                        "generation_policy_id": NO_ID,
                    }
                ]
            ),
        }
    else:
        base = {"payload": zero_payload(PAYLOAD_LAYOUTS[descriptor_type])}
    base.update(overrides)
    return Descriptor(
        descriptor_id=0, descriptor_type=descriptor_type, **base
    )


def poke_header(record: bytes, field: str, value: int) -> bytes:
    spec = DESCRIPTOR_HEADER.field(field)
    edited = bytearray(record)
    edited[spec.offset : spec.end] = int(value).to_bytes(spec.size, "little")
    return seal_descriptor(bytes(edited))


# ---------------------------------------------------------------------------
# round trips
# ---------------------------------------------------------------------------
def test_the_registry_has_fifteen_types() -> None:
    assert len(ALL_TYPES) == 15
    assert len(FIXED_TYPES) == 14
    assert (
        set(ALL_TYPES) - set(FIXED_TYPES)
        == {int(ExtendedDescriptorType.ENTRYPOINT_TABLE)}
    )


@pytest.mark.parametrize("descriptor_type", ALL_TYPES)
def test_every_descriptor_type_round_trips(descriptor_type: int) -> None:
    descriptor = descriptor_for(
        descriptor_type,
        flags=0,
        primary_object_id=3,
        secondary_object_id=NO_ID,
        numeric_profile_id=NO_ID,
        schedule_id=NO_ID,
        permissions=int(Permission.READ),
        owner_scope_id=2,
    )
    record = descriptor.encode()
    assert len(record) % DESCRIPTOR_ALIGNMENT == 0
    assert len(record) >= DESCRIPTOR_HEADER_BYTES + 1
    assert record[0:4] == b"TA3D"
    decoded = Descriptor.decode(record, 0)
    assert decoded.descriptor_type == descriptor_type
    assert decoded.permissions == int(Permission.READ)
    assert decoded.primary_object_id == 3
    assert decoded.owner_scope_id == 2
    assert decoded.type_major == TYPE_MAJOR and decoded.type_minor == TYPE_MINOR
    if descriptor_type in PAYLOAD_LAYOUTS:
        assert decoded.payload == descriptor.payload
        assert decoded.raw_payload is None
    else:
        assert decoded.raw_payload == descriptor.raw_payload


@pytest.mark.parametrize("descriptor_type", ALL_TYPES)
def test_header_fields_match_the_frozen_rules(descriptor_type: int) -> None:
    record = descriptor_for(descriptor_type).encode()
    header = DESCRIPTOR_HEADER.decode(record[:DESCRIPTOR_HEADER_BYTES])
    assert header["payload_offset"] == DESCRIPTOR_PAYLOAD_OFFSET == 64
    assert header["total_bytes"] == len(record)
    assert header["total_bytes"] % DESCRIPTOR_ALIGNMENT == 0
    assert header["payload_bytes"] <= header["total_bytes"] - DESCRIPTOR_HEADER_BYTES
    assert header["record_crc"] == record_crc(record, DESCRIPTOR_HEADER.crc_offset())
    assert header["type_major"] == TYPE_MAJOR


def test_payload_is_padded_with_zeros_to_the_alignment() -> None:
    descriptor = make_entrypoint_table(
        0,
        [
            {
                "entrypoint_id": i,
                "first_instruction": i,
                "phase": 0,
                "generation_policy_id": NO_ID,
            }
            for i in range(2)
        ],
    )
    record = descriptor.encode()
    payload_bytes = ENTRYPOINT_HEADER_PAYLOAD.size + 2 * ENTRYPOINT_ENTRY.size
    total = DESCRIPTOR_HEADER_BYTES + payload_bytes
    expected = -(-total // DESCRIPTOR_ALIGNMENT) * DESCRIPTOR_ALIGNMENT
    assert len(record) == expected > total  # the record really is padded
    assert record[64 + payload_bytes :] == bytes(len(record) - 64 - payload_bytes)


# ---------------------------------------------------------------------------
# type and version
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_type", [0x0000, 0x0010, 0x0011, 0x00FF, 0xFFFF])
def test_unknown_descriptor_types_fail_closed(bad_type: int) -> None:
    assert bad_type not in ALL_TYPES
    with pytest.raises(ValueError):
        Descriptor(
            descriptor_id=0, descriptor_type=bad_type, payload={}, raw_payload=bytes(64)
        ).encode()
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    with pytest.raises(ValueError):
        Descriptor.decode(poke_header(record, "descriptor_type", bad_type), 0)


@pytest.mark.parametrize("bad_major", [0, TYPE_MAJOR + 1, 255])
def test_unknown_type_major_fails_closed(bad_major: int) -> None:
    record = descriptor_for(ExtendedDescriptorType.SCHEDULE).encode()
    with pytest.raises(RecordError, match="type_major"):
        Descriptor.decode(poke_header(record, "type_major", bad_major), 0)


@pytest.mark.parametrize("bad_minor", [TYPE_MINOR + 1, 255])
def test_a_newer_type_minor_fails_closed(bad_minor: int) -> None:
    record = descriptor_for(ExtendedDescriptorType.SCHEDULE).encode()
    with pytest.raises(RecordError, match="type_minor"):
        Descriptor.decode(poke_header(record, "type_minor", bad_minor), 0)


def test_bad_descriptor_magic_fails_closed() -> None:
    record = bytearray(descriptor_for(ExtendedDescriptorType.NUMERIC).encode())
    record[0:4] = b"TA3E"
    with pytest.raises(RecordError, match="magic"):
        Descriptor.decode(seal_descriptor(bytes(record)), 0)


# ---------------------------------------------------------------------------
# size, payload extent, padding
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("total", [65, 100, 127, 129, 191])
def test_size_that_is_not_a_multiple_of_sixty_four_fails_closed(total: int) -> None:
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    padded = record + bytes(max(0, total - len(record)))
    padded = padded[:total]
    edited = poke_header(padded, "total_bytes", total)
    with pytest.raises(RecordError):
        Descriptor.decode(edited, 0)


def test_total_bytes_must_equal_the_record_length() -> None:
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    with pytest.raises(RecordError, match="total_bytes"):
        Descriptor.decode(poke_header(record, "total_bytes", 192), 0)
    with pytest.raises(RecordError, match="total_bytes"):
        Descriptor.decode(poke_header(record, "total_bytes", 64), 0)
    with pytest.raises(RecordError, match="shorter than its header"):
        Descriptor.decode(record[:32], 0)


def test_a_header_only_descriptor_carries_no_typed_payload_and_is_rejected() -> None:
    """64 bytes is a positive multiple of 64, but ``payload_offset`` is frozen at
    64, so such a record declares a type and then supplies nothing to type."""
    header = DESCRIPTOR_HEADER.encode(
        {
            "descriptor_type": int(ExtendedDescriptorType.NUMERIC),
            "type_major": TYPE_MAJOR,
            "type_minor": TYPE_MINOR,
            "total_bytes": 64,
            "flags": 0,
            "primary_object_id": NO_ID,
            "secondary_object_id": NO_ID,
            "numeric_profile_id": NO_ID,
            "schedule_id": NO_ID,
            "permissions": int(Permission.READ),
            "owner_scope_id": 0,
            "payload_offset": DESCRIPTOR_PAYLOAD_OFFSET,
            "payload_bytes": 0,
            "record_crc": 0,
        }
    )
    with pytest.raises(RecordError):
        Descriptor.decode(seal_descriptor(bytes(header)), 0)


@pytest.mark.parametrize("payload_bytes", [65, 129, 1 << 20, 0xFFFFFFFF])
def test_payload_running_past_the_record_fails_closed(payload_bytes: int) -> None:
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    with pytest.raises(RecordError, match="past the record"):
        Descriptor.decode(poke_header(record, "payload_bytes", payload_bytes), 0)


def test_payload_shorter_than_its_type_fails_closed() -> None:
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    with pytest.raises(RecordError):
        Descriptor.decode(poke_header(record, "payload_bytes", 32), 0)
    with pytest.raises(RecordError):
        Descriptor.decode(poke_header(record, "payload_bytes", 0), 0)


def test_payload_offset_other_than_sixty_four_fails_closed() -> None:
    record = descriptor_for(ExtendedDescriptorType.NUMERIC).encode()
    for offset in (0, 32, 128):
        with pytest.raises(RecordError, match="payload_offset"):
            Descriptor.decode(poke_header(record, "payload_offset", offset), 0)


def test_nonzero_padding_fails_closed() -> None:
    descriptor = make_entrypoint_table(
        0,
        [
            {
                "entrypoint_id": 0,
                "first_instruction": 0,
                "phase": 0,
                "generation_policy_id": NO_ID,
            }
        ],
    )
    record = bytearray(descriptor.encode())
    payload_end = 64 + ENTRYPOINT_HEADER_PAYLOAD.size + ENTRYPOINT_ENTRY.size
    assert payload_end < len(record)
    for index in range(payload_end, len(record)):
        edited = bytearray(record)
        edited[index] = 0x01
        with pytest.raises(RecordError, match="padding is not zero"):
            Descriptor.decode(seal_descriptor(bytes(edited)), 0)


@pytest.mark.parametrize("index", range(52, 64))
def test_nonzero_header_reserved_bytes_fail_closed(index: int) -> None:
    record = bytearray(descriptor_for(ExtendedDescriptorType.SCHEDULE).encode())
    record[index] = 0x7F
    with pytest.raises(RecordError, match="reserved"):
        Descriptor.decode(seal_descriptor(bytes(record)), 0)


RESERVED_PAYLOADS = sorted(
    (
        (int(descriptor_type), layout)
        for descriptor_type, layout in PAYLOAD_LAYOUTS.items()
        if any(field.kind == "reserved" for field in layout.fields)
    ),
    key=lambda item: item[0],
)


def test_most_payload_types_declare_a_reserved_span() -> None:
    """OPERATOR is fully assigned; every other payload keeps room to grow."""
    without = {
        ExtendedDescriptorType(dtype).name
        for dtype in PAYLOAD_LAYOUTS
        if not any(f.kind == "reserved" for f in PAYLOAD_LAYOUTS[dtype].fields)
    }
    assert without == {"OPERATOR"}


@pytest.mark.parametrize(
    "descriptor_type,layout", RESERVED_PAYLOADS, ids=lambda item: getattr(item, "name", item)
)
def test_nonzero_payload_reserved_bytes_fail_closed(
    descriptor_type: int, layout: Layout
) -> None:
    reserved = [f for f in layout.fields if f.kind == "reserved"]
    record = bytearray(descriptor_for(descriptor_type).encode())
    record[64 + reserved[0].offset] = 0x01
    with pytest.raises(RecordError, match="reserved"):
        Descriptor.decode(seal_descriptor(bytes(record)), 0)


def test_descriptor_crc_covers_every_byte_of_the_record() -> None:
    record = descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT).encode()
    crc_offset = DESCRIPTOR_HEADER.crc_offset()
    for index in range(len(record)):
        if crc_offset <= index < crc_offset + 4:
            continue
        edited = bytearray(record)
        edited[index] ^= 0xFF
        with pytest.raises(ValueError):
            Descriptor.decode(bytes(edited), 0)


def test_a_stale_descriptor_crc_fails_closed() -> None:
    record = bytearray(descriptor_for(ExtendedDescriptorType.STATE).encode())
    record[DESCRIPTOR_HEADER.crc_offset()] ^= 0x01
    with pytest.raises(RecordError, match="CRC32C mismatch"):
        Descriptor.decode(bytes(record), 0)


# ---------------------------------------------------------------------------
# permissions
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "permissions",
    [
        int(Permission.IMMUTABLE | Permission.WRITE),
        int(Permission.IMMUTABLE | Permission.STATE_COMMIT),
        int(Permission.READ | Permission.IMMUTABLE | Permission.WRITE),
    ],
)
def test_encoding_conflicting_permissions_fails_closed(permissions: int) -> None:
    with pytest.raises(RecordError, match="IMMUTABLE"):
        descriptor_for(
            ExtendedDescriptorType.MEMORY_OBJECT, permissions=permissions
        ).encode()


@pytest.mark.parametrize("bit", range(8, 32))
def test_reserved_permission_bits_fail_closed(bit: int) -> None:
    permissions = int(Permission.READ) | (1 << bit)
    assert permissions & ~PERMISSION_MASK
    with pytest.raises(RecordError, match="reserved"):
        descriptor_for(
            ExtendedDescriptorType.MEMORY_OBJECT, permissions=permissions
        ).encode()
    record = descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT).encode()
    with pytest.raises(RecordError, match="reserved"):
        Descriptor.decode(poke_header(record, "permissions", permissions), 0)


def test_every_documented_permission_bit_is_encodable_on_its_own() -> None:
    for permission in Permission:
        if not permission.value:
            continue
        descriptor = descriptor_for(
            ExtendedDescriptorType.MEMORY_OBJECT, permissions=int(permission)
        )
        assert Descriptor.decode(descriptor.encode(), 0).permissions == int(permission)


@pytest.mark.parametrize(
    "descriptor_type",
    [
        int(ExtendedDescriptorType.TENSOR_VIEW),
        int(ExtendedDescriptorType.STATE),
        int(ExtendedDescriptorType.COMMUNICATION),
    ],
)
def test_decoding_conflicting_permissions_fails_closed(descriptor_type: int) -> None:
    record = descriptor_for(descriptor_type).encode()
    conflicted = poke_header(
        record, "permissions", int(Permission.IMMUTABLE | Permission.WRITE)
    )
    with pytest.raises(RecordError):
        Descriptor.decode(conflicted, 0)


# ---------------------------------------------------------------------------
# entrypoint table
# ---------------------------------------------------------------------------
def test_entrypoint_table_round_trips() -> None:
    entries = [
        {
            "entrypoint_id": 0,
            "first_instruction": 0,
            "phase": 0,
            "generation_policy_id": NO_ID,
        },
        {
            "entrypoint_id": 1,
            "first_instruction": 4,
            "phase": 1,
            "generation_policy_id": 9,
        },
    ]
    blob = encode_entrypoint_table(entries)
    assert len(blob) == ENTRYPOINT_HEADER_PAYLOAD.size + 2 * ENTRYPOINT_ENTRY.size
    assert decode_entrypoint_table(blob) == entries


def test_entrypoint_table_fails_closed() -> None:
    with pytest.raises(RecordError, match="at least one entry"):
        encode_entrypoint_table([])
    blob = encode_entrypoint_table(
        [
            {
                "entrypoint_id": 0,
                "first_instruction": 0,
                "phase": 0,
                "generation_policy_id": NO_ID,
            }
        ]
    )
    with pytest.raises(RecordError, match="too short"):
        decode_entrypoint_table(blob[:8])
    with pytest.raises(RecordError, match="expected"):
        decode_entrypoint_table(blob + bytes(16))
    zeroed = bytearray(blob)
    zeroed[0:4] = b"\x00\x00\x00\x00"
    with pytest.raises(RecordError, match="zero entries"):
        decode_entrypoint_table(bytes(zeroed))
    lying = bytearray(blob)
    lying[0:4] = (99).to_bytes(4, "little")
    with pytest.raises(RecordError, match="expected"):
        decode_entrypoint_table(bytes(lying))


def test_entrypoint_table_header_reserved_bytes_are_checked() -> None:
    blob = bytearray(
        encode_entrypoint_table(
            [
                {
                    "entrypoint_id": 0,
                    "first_instruction": 0,
                    "phase": 0,
                    "generation_policy_id": NO_ID,
                }
            ]
        )
    )
    blob[4] = 1
    with pytest.raises(RecordError, match="reserved"):
        decode_entrypoint_table(bytes(blob))


# ---------------------------------------------------------------------------
# descriptor tables
# ---------------------------------------------------------------------------
def build_table(*types: int) -> DescriptorTable:
    table = DescriptorTable()
    for descriptor_type in types:
        table.add(descriptor_for(descriptor_type, permissions=int(Permission.READ)))
    return table


def test_descriptor_table_round_trips_and_ids_are_indices() -> None:
    table = build_table(
        int(ExtendedDescriptorType.MEMORY_OBJECT),
        int(ExtendedDescriptorType.TENSOR_VIEW),
        int(ExtendedDescriptorType.NUMERIC),
    )
    decoded = DescriptorTable.decode(table.encode())
    assert len(decoded) == 3
    assert decoded.digest == table.digest
    for index in range(3):
        assert decoded[index].descriptor_id == index
        assert decoded[index].descriptor_type == table[index].descriptor_type
    assert decoded.ids_of_type(int(ExtendedDescriptorType.NUMERIC)) == (2,)


def test_descriptor_table_fails_closed_on_structure() -> None:
    table = build_table(int(ExtendedDescriptorType.NUMERIC))
    blob = table.encode()
    with pytest.raises(DeploymentError, match="empty"):
        DescriptorTable.decode(b"")
    with pytest.raises(DeploymentError, match="truncated"):
        DescriptorTable.decode(blob + bytes(32))
    lying = bytearray(blob)
    lying[8:12] = (192).to_bytes(4, "little")
    with pytest.raises(DeploymentError, match="past the table"):
        DescriptorTable.decode(bytes(lying))
    lying[8:12] = (100).to_bytes(4, "little")
    with pytest.raises(DeploymentError, match="invalid size"):
        DescriptorTable.decode(bytes(lying))
    lying[8:12] = (0).to_bytes(4, "little")
    with pytest.raises(DeploymentError, match="invalid size"):
        DescriptorTable.decode(bytes(lying))


def test_descriptor_table_get_enforces_the_expected_type() -> None:
    table = build_table(
        int(ExtendedDescriptorType.MEMORY_OBJECT),
        int(ExtendedDescriptorType.NUMERIC),
    )
    assert table.get(1, int(ExtendedDescriptorType.NUMERIC)).descriptor_id == 1
    with pytest.raises(DeploymentError, match="expected"):
        table.get(1, int(ExtendedDescriptorType.MEMORY_OBJECT))
    with pytest.raises(DeploymentError, match="out of range"):
        table.get(9)


# ---------------------------------------------------------------------------
# typed payload widths that the rest of the ABI depends on
# ---------------------------------------------------------------------------
def test_memory_object_addresses_and_sizes_are_sixty_four_bit() -> None:
    assert MEMORY_OBJECT_PAYLOAD.field("base_address").size == 8
    assert MEMORY_OBJECT_PAYLOAD.field("size_bytes").size == 8
    descriptor = descriptor_for(
        ExtendedDescriptorType.MEMORY_OBJECT,
        payload={
            **zero_payload(MEMORY_OBJECT_PAYLOAD),
            "storage_class": int(StorageClass.HBM),
            "base_address": (1 << 64) - 1,
            "size_bytes": (1 << 64) - 1,
        },
    )
    decoded = Descriptor.decode(descriptor.encode(), 0)
    assert decoded.payload["size_bytes"] == (1 << 64) - 1


def test_tensor_view_dynamic_terms_are_addressable_by_slot() -> None:
    payload = zero_payload(TENSOR_VIEW_PAYLOAD)
    payload.update(
        {"dtype": 0x10, "rank": 2, "dim0": 4, "dim1": 8, "stride0": 8, "stride1": 1}
    )
    for slot in range(4):
        payload[f"term{slot}_kind"] = slot % 3
        payload[f"term{slot}_index"] = slot
        payload[f"term{slot}_stride"] = 1 << slot
    payload["dynamic_term_count"] = 4
    descriptor = descriptor_for(ExtendedDescriptorType.TENSOR_VIEW, payload=payload)
    decoded = Descriptor.decode(descriptor.encode(), 0)
    assert decoded.payload == payload


def test_payload_values_wider_than_their_field_fail_closed() -> None:
    payload = zero_payload(MEMORY_OBJECT_PAYLOAD)
    payload["size_bytes"] = 1 << 64
    with pytest.raises(RecordError):
        descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT, payload=payload).encode()
    payload = zero_payload(MEMORY_OBJECT_PAYLOAD)
    payload["storage_class"] = 256
    with pytest.raises(RecordError):
        descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT, payload=payload).encode()


def test_encoding_rejects_unknown_and_missing_payload_fields() -> None:
    payload = zero_payload(MEMORY_OBJECT_PAYLOAD)
    payload["not_a_field"] = 1
    with pytest.raises(RecordError, match="unknown field"):
        descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT, payload=payload).encode()
    payload = zero_payload(MEMORY_OBJECT_PAYLOAD)
    del payload["size_bytes"]
    with pytest.raises(RecordError, match="missing field"):
        descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT, payload=payload).encode()


def test_encoding_rejects_a_nonzero_reserved_payload_value() -> None:
    payload = zero_payload(MEMORY_OBJECT_PAYLOAD)
    payload["reserved_0"] = 1
    with pytest.raises(RecordError, match="reserved"):
        descriptor_for(ExtendedDescriptorType.MEMORY_OBJECT, payload=payload).encode()


def test_a_type_without_a_fixed_payload_needs_raw_bytes() -> None:
    with pytest.raises(RecordError, match="raw_payload"):
        Descriptor(
            descriptor_id=0,
            descriptor_type=int(ExtendedDescriptorType.ENTRYPOINT_TABLE),
            payload={},
        ).encode()
