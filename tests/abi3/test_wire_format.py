"""Every ABI 3.0 offset, size and constant, checked against the normative doc.

``docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md`` is the contract; the layouts in
``runtime/abi3/records.py`` and ``runtime/abi3/descriptors.py`` are one
implementation of it.  These tests parse the document's own tables and prose
registries and compare them mechanically with the encoder, so that a change to
either side that is not mirrored in the other fails here rather than in the
field.  Hand-copied expectations would drift with the code they are supposed to
police, so the only hand-written data below is the map from the document's
English field names to the encoder's Python identifiers.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from dataclasses import dataclass

import pytest

from runtime.abi3 import constants as C
from runtime.abi3 import descriptors as D
from runtime.abi3 import records as R
from runtime.abi3 import request as Q
from runtime.abi3.crc import CRC32C_POLY_REFLECTED, crc32c

from . import ROOT, WIRE_FORMAT_DOC

DOC_TEXT = WIRE_FORMAT_DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# markdown parsing
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DocTable:
    section: str
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


_SEPARATOR = re.compile(r"^:?-{3,}:?$")


def parse_tables(text: str) -> list[DocTable]:
    """Every markdown table in ``text``, tagged with its enclosing heading."""
    tables: list[DocTable] = []
    section = ""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            section = line.lstrip("#").strip()
        elif line.startswith("|") and index + 1 < len(lines):
            header = _cells(line)
            separator = _cells(lines[index + 1])
            if len(separator) == len(header) and all(
                _SEPARATOR.match(cell) for cell in separator
            ):
                rows = []
                cursor = index + 2
                while cursor < len(lines) and lines[cursor].startswith("|"):
                    rows.append(_cells(lines[cursor]))
                    cursor += 1
                tables.append(DocTable(section, header, tuple(rows)))
                index = cursor
                continue
        index += 1
    return tables


TABLES = parse_tables(DOC_TEXT)


def section_text(prefix: str) -> str:
    """The body of the ``## <prefix> ...`` section, up to the next heading."""
    pattern = re.compile(
        rf"^#+\s+{re.escape(prefix)}[^\n]*\n(.*?)(?=^#+\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(DOC_TEXT)
    assert match is not None, f"wire-format document has no section {prefix!r}"
    return match.group(1)


def table_for(prefix: str, first_column: str) -> DocTable:
    found = [
        table
        for table in TABLES
        if table.section.startswith(prefix) and table.header[0] == first_column
    ]
    assert len(found) == 1, (
        f"expected exactly one {first_column!r} table in section {prefix!r}, "
        f"found {len(found)}"
    )
    return found[0]


def normalise(field: str) -> str:
    """The document's English field name as a comparable identifier."""
    field = re.split(r"[,;]", field)[0]
    field = field.replace("`", "")
    return re.sub(r"[^0-9A-Za-z]+", "_", field).strip("_").lower()


def registry(text: str, pattern: str) -> dict[str, int]:
    return {
        name: int(value, 0)
        for name, value in re.findall(pattern, text)
    }


# ---------------------------------------------------------------------------
# section 1 -- common encoding rules
# ---------------------------------------------------------------------------
def test_common_encoding_constants_match_the_document() -> None:
    text = section_text("1.")
    assert re.search(r"`NO_ID` is `0xffffffff`", text)
    assert C.NO_ID == 0xFFFFFFFF
    poly = re.search(r"polynomial `(0x[0-9a-f]+)`", text)
    assert poly is not None and int(poly.group(1), 16) == CRC32C_POLY_REFLECTED
    assert re.search(r"initial state `0xffffffff`", text)
    assert re.search(r"final XOR `0xffffffff`", text)
    # The frozen CRC32C check value pins the reflected/init/final combination.
    assert crc32c(b"123456789") == 0xE3069283
    assert crc32c(b"") == 0x00000000
    digest = re.search(r"SHA-256 digests are (\d+) raw bytes", text)
    assert digest is not None and int(digest.group(1)) == 32
    hexchars = re.search(r"(\d+) lowercase\s+hexadecimal characters", text)
    assert hexchars is not None and int(hexchars.group(1)) == 64


# ---------------------------------------------------------------------------
# record layout tables
# ---------------------------------------------------------------------------
PROGRAM_HEADER_NAMES = {
    "magic": "magic",
    "abi_major": "abi_major",
    "abi_minor": "abi_minor",
    "header_bytes": "header_bytes",
    "instruction_bytes": "instruction_bytes",
    "flags": "flags",
    "instruction_count": "instruction_count",
    "entrypoint_count": "entrypoint_count",
    "required_feature_bits": "required_features",
    "deployment_digest": "deployment_digest",
    "descriptor_table_digest": "descriptor_table_digest",
    "topology_health_digest": "topology_digest",
    "body_digest": "body_digest",
    "maximum_retired_work": "max_retired_work",
    "watchdog_class": "watchdog_class",
    "entrypoint_table_descriptor_id": "entrypoint_table_descriptor",
    "signature_metadata_descriptor_id": "signature_metadata_descriptor",
    "header_crc32c": "header_crc",
}

INSTRUCTION_NAMES = {
    "major_opcode": "major",
    "subopcode": "sub",
    "flags": "flags",
    "predicate_id": "predicate_id",
    "descriptor_id": "descriptor_id",
    "wait_set_id": "wait_set_id",
    "signal_event_id": "signal_event_id",
    "control_id_or_branch_target": "control_id",
    "source_operation_id": "source_operation_id",
    "instruction_crc32c": "instruction_crc",
}

DESCRIPTOR_HEADER_NAMES = {
    "magic": "magic",
    "descriptor_type": "descriptor_type",
    "type_major": "type_major",
    "type_minor": "type_minor",
    "total_record_bytes": "total_bytes",
    "flags": "flags",
    "primary_object_id": "primary_object_id",
    "secondary_object_id": "secondary_object_id",
    "numeric_profile_id": "numeric_profile_id",
    "schedule_id": "schedule_id",
    "access_permissions": "permissions",
    "owner_scope_id": "owner_scope_id",
    "payload_offset": "payload_offset",
    "payload_bytes": "payload_bytes",
    "record_crc32c": "record_crc",
}

REQUEST_DESCRIPTOR_HEADER_NAMES = {
    "magic": "magic",
    "abi_major": "abi_major",
    "abi_minor": "abi_minor",
    "type_major": "type_major",
    "type_minor": "type_minor",
    "header_bytes": "header_bytes",
    "entry_bytes": "entry_bytes",
    "total_record_bytes": "total_bytes",
    "request_descriptor_id": "request_descriptor_id",
    "symbol_count": "symbol_count",
    "deployment_id": "deployment_id",
    "deployment_generation": "deployment_generation",
    "session_id": "session_id",
    "session_generation": "session_generation",
    "transaction_id": "transaction_id",
    "payload_bytes": "payload_bytes",
    "flags": "flags",
    "content_digest": "content_digest",
    "record_crc32c": "record_crc",
}

REQUEST_SYMBOL_ENTRY_NAMES = {
    "symbol_id": "symbol_id",
    "value": "value",
}

SUBMISSION_NAMES = {
    "magic": "magic",
    "abi_major": "abi_major",
    "abi_minor": "abi_minor",
    "host_opcode": "host_opcode",
    "flags": "flags",
    "record_bytes": "record_bytes",
    "deployment_id": "deployment_id",
    "deployment_generation": "deployment_generation",
    "session_id_or_no_id": "session_id",
    "session_generation_or_zero": "session_generation",
    "request_descriptor_id": "request_descriptor_id",
    "transaction_id": "transaction_id",
    "idempotency_key": "idempotency_key",
    "input_memory_window_id": "input_window_id",
    "output_memory_window_id": "output_window_id",
    "input_offset": "input_offset",
    "input_bytes": "input_bytes",
    "output_offset": "output_offset",
    "output_capacity_bytes": "output_capacity_bytes",
    "entrypoint_id": "entrypoint_id",
    "generation_policy_descriptor_id": "generation_policy_id",
    "watchdog_class": "watchdog_class",
    "deadline_in_device_cycles": "deadline_cycles",
    "record_crc32c": "record_crc",
}

COMPLETION_NAMES = {
    "magic": "magic",
    "abi_major": "abi_major",
    "abi_minor": "abi_minor",
    "completion_status": "status",
    "flags": "flags",
    "record_bytes": "record_bytes",
    "trap_class": "trap_class",
    "deployment_id": "deployment_id",
    "deployment_generation": "deployment_generation",
    "session_id_or_no_id": "session_id",
    "session_generation": "session_generation",
    "engine_fault_class": "engine_fault_class",
    "transaction_id": "transaction_id",
    "committed_token_position": "committed_token_position",
    "produced_token_count": "produced_token_count",
    "committed_state_generation": "committed_state_generation",
    "output_bytes_written": "output_bytes_written",
    "first_fault_instruction_index_or_no_id": "first_fault_instruction",
    "fault_descriptor_id_or_no_id": "fault_descriptor_id",
    "counter_snapshot_id_or_no_id": "counter_snapshot_id",
    "trace_id_or_no_id": "trace_id",
    "completion_timestamp_in_device_cycles": "completion_timestamp",
    "echoed_idempotency_key": "idempotency_key",
    "final_selected_token_id": "final_token_id",
    "eos_reason": "eos_reason",
    "retired_work": "retired_work",
    "record_crc32c": "record_crc",
}

RECORD_TABLES = {
    "program_header": ("2.", "Offset", R.PROGRAM_HEADER, PROGRAM_HEADER_NAMES),
    "instruction": ("3.", "Offset", R.INSTRUCTION, INSTRUCTION_NAMES),
    "descriptor_header": (
        "5.",
        "Offset",
        D.DESCRIPTOR_HEADER,
        DESCRIPTOR_HEADER_NAMES,
    ),
    "submission": ("6. Host submission", "Offset", R.SUBMISSION, SUBMISSION_NAMES),
    "completion": ("7.", "Offset", R.COMPLETION, COMPLETION_NAMES),
    "request_descriptor_header": (
        "6.1.1",
        "Offset",
        Q.REQUEST_DESCRIPTOR_HEADER,
        REQUEST_DESCRIPTOR_HEADER_NAMES,
    ),
    "request_symbol_entry": (
        "6.1.2",
        "Offset",
        Q.REQUEST_SYMBOL_ENTRY,
        REQUEST_SYMBOL_ENTRY_NAMES,
    ),
}


def check_record_layout(name: str) -> None:
    prefix, column, layout, names = RECORD_TABLES[name]
    table = table_for(prefix, column)
    documented = [
        (int(row[0]), int(row[1]), normalise(row[2])) for row in table.rows
    ]
    encoded = [(field.offset, field.size, field.name) for field in layout.fields]
    assert len(documented) == len(encoded), (
        f"{name}: document declares {len(documented)} fields, encoder declares "
        f"{len(encoded)}"
    )
    for (offset, size, doc_name), field in zip(documented, layout.fields):
        assert (offset, size) == (field.offset, field.size), (
            f"{name}: document places {doc_name!r} at offset {offset} size "
            f"{size}, encoder has {field.name!r} at offset {field.offset} size "
            f"{field.size}"
        )
        if doc_name.startswith("reserved"):
            assert field.kind == "reserved", (
                f"{name}: byte {offset} is reserved in the document but "
                f"{field.name!r} ({field.kind}) in the encoder"
            )
            continue
        assert field.kind != "reserved", (
            f"{name}: {doc_name!r} is an assigned field in the document but "
            f"reserved in the encoder"
        )
        assert doc_name in names, (
            f"{name}: the document declares an unmapped field {doc_name!r}; the "
            "wire format changed and this conformance test was not updated"
        )
        assert names[doc_name] == field.name, (
            f"{name}: document field {doc_name!r} maps to {names[doc_name]!r} "
            f"but the encoder calls byte {offset} {field.name!r}"
        )
    # Every byte accounted for, no overlap: the layout engine proves this at
    # import time, so re-assert it against the document's own record size.
    assert encoded[-1][0] + encoded[-1][1] == layout.size


@pytest.mark.parametrize("record", sorted(RECORD_TABLES))
def test_record_layout_matches_the_document(record: str) -> None:
    check_record_layout(record)


def test_declared_record_sizes_match_the_document() -> None:
    header = re.search(r"program header is exactly (\d+) bytes", section_text("2."))
    assert header is not None
    assert int(header.group(1)) == C.PROGRAM_HEADER_BYTES == R.PROGRAM_HEADER.size
    instruction = re.search(
        r"instruction is exactly (\d+) bytes", section_text("3.")
    )
    assert instruction is not None
    assert int(instruction.group(1)) == C.INSTRUCTION_BYTES == R.INSTRUCTION.size
    descriptor = section_text("5.")
    boundary = re.search(r"begins on a (\d+)-byte boundary", descriptor)
    assert boundary is not None
    assert int(boundary.group(1)) == C.DESCRIPTOR_ALIGNMENT
    head = re.search(r"begins with this (\d+)-byte header", descriptor)
    assert head is not None
    assert (
        int(head.group(1))
        == C.DESCRIPTOR_HEADER_BYTES
        == D.DESCRIPTOR_HEADER.size
        == C.DESCRIPTOR_PAYLOAD_OFFSET
    )
    for prefix, size in (("6.", C.SUBMISSION_BYTES), ("7.", C.COMPLETION_BYTES)):
        ring = re.search(
            r"fixed (\d+)-byte records aligned to (\d+) bytes", section_text(prefix)
        )
        assert ring is not None
        assert int(ring.group(1)) == int(ring.group(2)) == size
    request_descriptor = section_text("6.1")
    request_header = re.search(r"has a (\d+)-byte header", request_descriptor)
    request_entry = re.search(r"fixed (\d+)-byte symbol entries", request_descriptor)
    assert request_header is not None and request_entry is not None
    assert int(request_header.group(1)) == C.REQUEST_DESCRIPTOR_HEADER_BYTES
    assert int(request_entry.group(1)) == C.REQUEST_SYMBOL_ENTRY_BYTES


def test_magic_values_match_the_document() -> None:
    assert re.search(r"ASCII `OTTA3PG\\0`", section_text("2."))
    assert C.PROGRAM_MAGIC == b"OTTA3PG\x00"
    for prefix, magic, constant in (
        ("5.", "TA3D", C.DESCRIPTOR_MAGIC),
        ("6.", "TA3S", C.SUBMISSION_MAGIC),
        ("6.1.1", "TA3R", C.REQUEST_DESCRIPTOR_MAGIC),
        ("7.", "TA3C", C.COMPLETION_MAGIC),
    ):
        assert f"ASCII `{magic}`" in section_text(prefix)
        assert constant == magic.encode("ascii")


def test_abi_version_fields_are_three_zero() -> None:
    assert (C.ABI_MAJOR, C.ABI_MINOR) == (3, 0)
    header = table_for("2.", "Offset")
    versions = {
        normalise(row[2]): row[3] for row in header.rows if "ABI" in row[2]
    }
    assert versions["abi_major"].strip("`") == str(C.ABI_MAJOR)
    assert versions["abi_minor"].strip("`") == str(C.ABI_MINOR)


# ---------------------------------------------------------------------------
# section 3 -- instruction flags
# ---------------------------------------------------------------------------
def test_instruction_flag_registry_matches_the_document() -> None:
    table = table_for("3.", "Bit")
    documented: dict[int, str] = {}
    reserved: list[str] = []
    for bit, name, _meaning in table.rows:
        clean = name.strip("`")
        if "reserved" in clean.lower():
            reserved.append(bit)
            continue
        documented[int(bit)] = clean
    assert documented == {
        int(flag.value).bit_length() - 1: flag.name
        for flag in C.InstructionFlag
        if flag.value
    }
    assert reserved == ["8–15"], reserved
    assert C.INSTRUCTION_FLAG_MASK == 0x00FF
    for flag in C.InstructionFlag:
        assert int(flag) & ~C.INSTRUCTION_FLAG_MASK == 0


# ---------------------------------------------------------------------------
# section 4 -- opcode registry
# ---------------------------------------------------------------------------
def documented_opcodes() -> dict[int, dict[str, int]]:
    table = table_for("4.", "Major")
    registry_map: dict[int, dict[str, int]] = {}
    for major, _family, subs in table.rows:
        value = int(major.strip("`"), 16)
        registry_map[value] = {
            name: int(number, 16)
            for name, number in re.findall(r"`([A-Z_0-9]+)=0x([0-9a-f]+)`", subs)
        }
    return registry_map


def test_opcode_registry_matches_the_document() -> None:
    documented = documented_opcodes()
    encoded = {
        int(major): {member.name: int(member) for member in enum}
        for major, enum in C.SUBOPCODES.items()
    }
    assert encoded == documented


def test_major_opcode_family_names_match_the_document() -> None:
    table = table_for("4.", "Major")
    documented = {
        int(major.strip("`"), 16): family.strip().upper().replace(" ", "_")
        for major, family, _subs in table.rows
    }
    assert {int(m): m.name for m in C.Major} == documented


def test_engine_families_exclude_control_observation_and_recovery() -> None:
    """Only engine families issue asynchronous work (section 4 prose)."""
    assert C.Major.CONTROL not in C.ENGINE_FAMILIES
    assert C.Major.OBSERVATION not in C.ENGINE_FAMILIES
    assert C.Major.RECOVERY not in C.ENGINE_FAMILIES
    assert len(C.ENGINE_FAMILIES) == len(C.Major) - 3


def test_mandatory_selection_subopcodes_exist() -> None:
    prose = section_text("4.")
    assert "`SAMPLE` is optional" in prose
    assert "`ARGMAX`, `TOKEN_APPEND`" in prose
    assert C.Selection.ARGMAX == 0x00 and C.Selection.TOKEN_APPEND == 0x01


# ---------------------------------------------------------------------------
# section 5 -- descriptor registry and permissions
# ---------------------------------------------------------------------------
def test_descriptor_type_registry_matches_the_document() -> None:
    documented = registry(section_text("5."), r"`([A-Z_]+)=(0x[0-9a-f]+)`")
    encoded = {member.name: int(member) for member in D.ExtendedDescriptorType}
    assert encoded == documented
    assert len(documented) == 15


def test_narrow_descriptor_type_enum_is_a_subset_of_the_registry() -> None:
    """``constants.DescriptorType`` predates amendment A3 and omits PREDICATE.

    Both enums are exported, so a decoder that reaches for the wrong one silently
    loses a frozen type.  The registry the codec actually uses is the extended
    one; this test pins the relationship rather than letting it rot.
    """
    narrow = {member.name: int(member) for member in C.DescriptorType}
    wide = {member.name: int(member) for member in D.ExtendedDescriptorType}
    assert set(narrow) < set(wide)
    assert set(wide) - set(narrow) == {"PREDICATE"}
    for name, value in narrow.items():
        assert wide[name] == value
    assert D.PREDICATE_TYPE == 0x000F


def test_access_permission_bits_match_the_document() -> None:
    documented = registry(section_text("5."), r"`([A-Z_]+)=bit(\d+)`")
    encoded = {
        member.name: int(member).bit_length() - 1
        for member in C.Permission
        if member.value
    }
    assert encoded == documented
    reserved = re.search(r"Bits (\d+) through (\d+) are reserved", section_text("5."))
    assert reserved is not None
    low, high = int(reserved.group(1)), int(reserved.group(2))
    assert C.PERMISSION_MASK == (1 << low) - 1
    assert high == 31


def test_document_requires_conflicting_permissions_to_fail_admission() -> None:
    assert "Conflicting permissions" in section_text("5.")
    assert "fail admission" in section_text("5.")


# ---------------------------------------------------------------------------
# sections 6 and 7 -- host queue registries
# ---------------------------------------------------------------------------
def test_host_opcode_registry_matches_the_document() -> None:
    documented = registry(section_text("6."), r"`([A-Z_]+)=(0x[0-9a-f]+)`")
    encoded = {member.name: int(member) for member in C.HostOpcode}
    assert encoded == documented


def test_completion_status_and_eos_reason_match_the_document() -> None:
    text = section_text("7.")
    status = registry(text, r"`([A-Z_]+)=(\d+)`")
    encoded = {member.name: int(member) for member in C.CompletionStatus}
    eos = {
        name: value
        for name, value in status.items()
        if name in {"NONE", "OFFICIAL_EOS", "MAX_NEW_TOKENS", "TERMINATED_BY_TRAP", "HOST_BOUND"}
    }
    assert {k: v for k, v in status.items() if k not in eos} == encoded
    assert eos == {
        name: getattr(R.EosReason, name)
        for name in vars(R.EosReason)
        if name.isupper()
    }


# ---------------------------------------------------------------------------
# section 8 -- trap, scope, topology and ordering
# ---------------------------------------------------------------------------
TRAP_CLASS_NAMES = {
    0: "NONE",
    1: "ADMISSION_OR_VERSION",
    2: "AUTHENTICATION_OR_INTEGRITY",
    3: "DESCRIPTOR_OR_ADDRESS",
    4: "CAPABILITY_OR_RESOURCE",
    5: "ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW",
    6: "NUMERIC_OR_EXCEPTIONAL_VALUE",
    7: "MEMORY_SUBSYSTEM",
    8: "ENGINE",
    9: "STATE_TRANSACTION",
    10: "TIMEOUT_OR_WATCHDOG",
    11: "LINK_OR_NOC",
    12: "POWER_RESET_OR_THERMAL",
    13: "INTERNAL_INVARIANT",
}


def test_trap_class_registry_matches_the_document() -> None:
    table = table_for("8.", "Value")
    documented = {int(value): text for value, text in table.rows}
    assert set(documented) == {int(member) for member in C.TrapClass}
    assert {int(m): m.name for m in C.TrapClass} == TRAP_CLASS_NAMES
    # The English text is the contract for what each stable number means; pin a
    # few so a renumbering cannot pass by keeping the count.
    assert documented[0].startswith("none")
    assert "control flow" in documented[5]
    assert "state transaction" in documented[9]


def test_topology_scope_and_ordering_registries_match_the_document() -> None:
    """Section 8 publishes four registries and the code assigns exactly those.

    ``NodeClass`` joined the section with amendment AM-R1.  Its ``WAFER`` is
    deliberately not spelled ``WAFER_LOGICAL_DEVICE``: that identifier is
    already a topology class at a different value, and this test is precisely
    the thing that would fail -- one name, two numbers, one document -- if a
    later amendment reused it.
    """
    text = section_text("8.")
    documented = registry(text, r"`([A-Z_0-9]+)=(\d+)`")
    registries = (C.TopologyClass, C.NodeClass, C.Scope, C.Ordering)
    for enum in registries:
        encoded = {member.name: int(member) for member in enum}
        for name, value in encoded.items():
            assert documented.get(name) == value, (name, value, documented.get(name))
    assert len(documented) == sum(len(enum) for enum in registries)


# ---------------------------------------------------------------------------
# section 9 -- feature bits
# ---------------------------------------------------------------------------
FEATURE_NAMES = {
    0: "HOST_QUEUE_ABI",
    1: "DEPLOYMENT_DESCRIPTOR_ABI",
    2: "DETERMINISTIC_MICROSEQUENCER",
    3: "BF16_TENSOR",
    4: "FP8_E4M3FN_TENSOR",
    5: "MXFP4_E2M1_E8M0",
    6: "TRANSACTIONAL_STATE",
    7: "ON_DEVICE_SELECTION",
    8: "INTER_CHIP_ENDPOINT",
    9: "WAFER_ENDPOINT",
    10: "INTEGRITY_RETRY",
    11: "SIGNED_DEPLOYMENT",
    12: "DATA_BEARING_TIMING",
}


def test_feature_bit_registry_matches_the_document() -> None:
    table = table_for("9.", "Bit")
    documented = {int(bit): text for bit, text in table.rows}
    assert {int(m): m.name for m in C.Feature} == FEATURE_NAMES
    assert set(documented) == set(FEATURE_NAMES)
    assert "argmax" in documented[7] and "EOS" in documented[7]
    assert C.FEATURE_VECTOR_BYTES == 32
    vector = C.feature_vector(sorted(documented))
    assert len(vector) == C.FEATURE_VECTOR_BYTES
    assert C.feature_bits(vector) == frozenset(documented)
    # The vector is little-endian: bit 0 is the low bit of byte 0.
    assert C.feature_vector([0])[0] == 1
    assert C.feature_vector([8])[1] == 1
    assert C.feature_vector([255])[31] == 0x80


def test_feature_vector_rejects_out_of_range_bits() -> None:
    with pytest.raises(ValueError):
        C.feature_vector([256])
    with pytest.raises(ValueError):
        C.feature_bits(b"\x00" * 31)


# ---------------------------------------------------------------------------
# section 10 -- counter namespaces
# ---------------------------------------------------------------------------
def test_counter_group_registry_matches_the_document() -> None:
    text = section_text("10.")
    documented = {
        int(value, 16) for value in re.findall(r"`(0x[0-9a-f]{2})`", text)
    }
    assert documented == {int(member) for member in C.CounterGroup}
    assert C.counter_id(C.CounterGroup.TENSOR, 7) == (0x04 << 24) | 7
    with pytest.raises(ValueError):
        C.counter_id(C.CounterGroup.TENSOR, 1 << 24)
    assert re.search(r"unsigned 64-bit saturating counters", text)


# ---------------------------------------------------------------------------
# section 12 -- typed descriptor payloads
# ---------------------------------------------------------------------------
def test_typed_payload_sizes_match_the_document() -> None:
    table = table_for("12.", "Type")
    documented: dict[str, tuple[int, int]] = {}
    variable: set[str] = set()
    for name, payload, total in table.rows:
        clean = name.strip("`")
        if not payload.isdigit():
            variable.add(clean)
            continue
        documented[clean] = (int(payload), int(total))
    assert variable == {"ENTRYPOINT_TABLE"}
    encoded = {
        D.ExtendedDescriptorType(dtype).name: layout.size
        for dtype, layout in D.PAYLOAD_LAYOUTS.items()
    }
    assert set(encoded) == set(documented)
    for name, (payload_bytes, total_bytes) in documented.items():
        assert encoded[name] == payload_bytes, name
        assert payload_bytes % 64 == 0, name
        assert total_bytes == C.DESCRIPTOR_HEADER_BYTES + payload_bytes, name


def test_entrypoint_table_payload_shape_matches_the_document() -> None:
    row = [
        r
        for r in table_for("12.", "Type").rows
        if r[0].strip("`") == "ENTRYPOINT_TABLE"
    ][0]
    shape = re.search(r"(\d+) \+ (\d+) per entry", row[1])
    assert shape is not None
    assert int(shape.group(1)) == D.ENTRYPOINT_HEADER_PAYLOAD.size
    assert int(shape.group(2)) == D.ENTRYPOINT_ENTRY.size


def test_dynamic_index_term_shape_matches_the_document() -> None:
    text = section_text("12.1")
    count = re.search(r"`dynamic_term_count` \((\d+) through (\d+)\)", text)
    assert count is not None
    assert int(count.group(1)) == 0
    assert int(count.group(2)) == D.MAX_DYNAMIC_TERMS
    shape = re.search(
        r"uint(\d+) selector_kind, uint(\d+) selector_index, uint(\d+) element_stride",
        text,
    )
    assert shape is not None
    widths = [int(bits) // 8 for bits in shape.groups()]
    for slot in range(D.MAX_DYNAMIC_TERMS):
        sizes = [
            D.TENSOR_VIEW_PAYLOAD.field(f"term{slot}_{suffix}").size
            for suffix in ("kind", "index", "stride")
        ]
        assert sizes == widths
    documented = registry(text, r"`([A-Z_]+)=(\d+)`")
    assert documented == {m.name: int(m) for m in D.SelectorKind}


def test_runtime_symbol_registry_matches_the_document() -> None:
    table = table_for("12.2", "Value")
    documented = {int(value): name.strip("`") for value, name in table.rows}
    assert {int(m): m.name for m in D.Symbol} == documented


# ---------------------------------------------------------------------------
# section 13 -- freeze amendments
# ---------------------------------------------------------------------------
AMENDMENTS = (
    "TA-A3-ARCH-0-A1",
    "TA-A3-ARCH-0-A2",
    "TA-A3-ARCH-0-A3",
    "TA-A3-ARCH-0-A4",
    "TA-A3-ARCH-0-A5",
)


def test_all_five_freeze_amendments_are_documented() -> None:
    """The encoder claims each amendment "is recorded" in this document.

    ``runtime/abi3/records.py`` and ``runtime/abi3/descriptors.py`` both cite the
    wire-format document as the place the amendments live.  If the document does
    not carry them, a decoder written from the specification alone is wrong about
    the completion record, the descriptor registry and loop-parametric views.
    """
    table = table_for("13.", "ID")
    documented = [row[0].strip("`") for row in table.rows]
    assert set(AMENDMENTS) <= set(documented), (
        "the wire format no longer records every amendment the encoder "
        f"implements; missing {sorted(set(AMENDMENTS) - set(documented))}"
    )
    # Amendment IDs are assigned in order and none may be withdrawn or reused.
    numbers = [int(name.rsplit("-A", 1)[1]) for name in documented]
    assert numbers == sorted(numbers) == list(range(1, len(numbers) + 1)), documented
    assert len(set(documented)) == len(documented)


def test_amendment_a1_and_a2_own_the_completion_bytes_they_claim() -> None:
    rows = {row[0].strip("`"): row[1] for row in table_for("13.", "ID").rows}
    first, last = re.search(r"completion bytes (\d+)-(\d+)", rows["TA-A3-ARCH-0-A1"]).groups()
    assert R.COMPLETION.field("final_token_id").offset == int(first)
    assert R.COMPLETION.field("eos_reason").offset == int(last)
    first, last = re.search(r"completion bytes (\d+)-(\d+)", rows["TA-A3-ARCH-0-A2"]).groups()
    work = R.COMPLETION.field("retired_work")
    assert work.offset == int(first)
    assert work.offset + work.size - 1 == int(last)


def test_amendment_a3_assigns_the_predicate_descriptor_type() -> None:
    rows = {row[0].strip("`"): row[1] for row in table_for("13.", "ID").rows}
    value = re.search(r"`PREDICATE = (0x[0-9a-f]+)`", rows["TA-A3-ARCH-0-A3"])
    assert value is not None
    assert int(value.group(1), 16) == D.ExtendedDescriptorType.PREDICATE


def test_encoder_amendment_markers_cite_the_document() -> None:
    """Each amendment must be named where it is implemented and where it is
    specified, so neither side can be changed without meeting the other."""
    owners = {
        R: ("TA-A3-ARCH-0-A1", "TA-A3-ARCH-0-A2"),
        D: ("TA-A3-ARCH-0-A3", "TA-A3-ARCH-0-A4", "TA-A3-ARCH-0-A5"),
    }
    for module, amendments in owners.items():
        source = Path(module.__file__).read_text(encoding="utf-8")
        for amendment in amendments:
            assert amendment in source, f"{module.__name__} does not cite {amendment}"
            assert amendment in DOC_TEXT


# ---------------------------------------------------------------------------
# published machine-readable spec
# ---------------------------------------------------------------------------
SPEC_RECORDS = ROOT / "spec" / "abi3" / "records.json"


@pytest.mark.skipif(
    not SPEC_RECORDS.exists(), reason="spec/abi3/records.json is not published"
)
def test_published_record_spec_agrees_with_the_document() -> None:
    """The published JSON is generated from the encoder; nothing else checks it
    against the prose contract it claims to publish."""
    spec = json.loads(SPEC_RECORDS.read_text(encoding="utf-8"))
    for record, (prefix, column, _layout, names) in RECORD_TABLES.items():
        if record not in spec:
            continue
        documented = [
            (int(row[0]), int(row[1]), normalise(row[2]))
            for row in table_for(prefix, column).rows
        ]
        published = [
            (field["offset"], field["size"], field["name"])
            for field in spec[record]["fields"]
        ]
        assert len(documented) == len(published), record
        for (offset, size, doc_name), (poffset, psize, pname) in zip(
            documented, published
        ):
            assert (offset, size) == (poffset, psize), (record, doc_name)
            if doc_name.startswith("reserved"):
                assert pname.startswith("reserved"), (record, doc_name)
            else:
                assert names[doc_name] == pname, (record, doc_name)
