"""The 128-word semantic record, assembled from RAW descriptor bytes.

``ot_a3_hc_pre_t1_descriptor_rne`` and ``ot_a3_vector_mhc_pre_tile_scheduler``
consume one 128-word bundle carrying everything the decoder and view resolver
already produced: the profile and token count, the instruction, the operator
descriptor, its counter class, its numeric profile with the 256-bit contract
digest, its schedule, and its six resolved views.

``tools/build_a3_mhc_pre_tile_vectors.py::config_words`` already assembles that
bundle -- from *decoded* descriptors, as Python objects.  Hardware does not have
decoded descriptors.  What the microsequencer has on its fetch port is
``desc_id``, ``desc_valid`` and 192 raw bytes, so a collector in RTL must reach
every field by byte offset, and this module is that reading expressed once, in
Python, where it can be checked against the bundle the decoded path produces.

It exists to be a specification rather than a second implementation: an RTL
collector's bench compares against ``config_words`` through this, so a
transcription error in either reading is a test failure and not a silent
disagreement between two things that were never compared.

Layout, all little-endian: a descriptor is a 64-byte header followed by its
payload.  ``primary_object_id`` sits at header byte 16 and ``permissions`` at
byte 32; every payload field is at ``64 + field.offset`` for its type's entry in
``PAYLOAD_LAYOUTS``.  The record's word order is fixed by section 3.8's
consumers and is restated here field by field rather than derived, because the
order is a contract with the RTL and not a property of the descriptors.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .descriptors import DESCRIPTOR_HEADER, PAYLOAD_LAYOUTS, ExtendedDescriptorType

HEADER_BYTES = 64
CONFIG_WORDS = 128

#: The record's blocks, as (first word, descriptor role, field names).  ``None``
#: as a field name means a header field rather than a payload one.
OPERATOR_FIELDS = (
    "engine_family", "engine_sub", "flags", "source_graph_operation_id",
    "source_kernel_id", "counter_class_id", "numeric_profile_id", "schedule_id",
    "input_view_0", "input_view_1", "input_view_2", "input_view_3",
    "output_view_0", "output_view_1", "aux_id_0", "aux_id_1", "aux_id_2",
    "aux_id_3",
)
COUNTER_FIELDS = ("group", "event_count", "counter_0", "counter_1", "counter_2")
NUMERIC_FIELDS = (
    "input_dtype", "second_input_dtype", "accumulator_dtype", "output_dtype",
    "rounding_mode", "reduction_order", "saturate", "nan_policy",
    "epsilon_bits", "scale_bits", "flags",
)
SCHEDULE_FIELDS = (
    "engine_family", "queue_index", "issue_window", "tile_rows", "tile_cols",
    "tile_depth", "bank_mask", "port_mask", "noc_route_class",
    "resource_bound", "max_outstanding", "priority",
)
VIEW_PAYLOAD_FIELDS = (
    "dtype", "rank", "dim0", "dim1", "dim2", "stride0", "stride1", "stride2",
)
VIEW_SLOTS = ("input0", "input1", "input2", "input3", "output0", "output1")


class SemanticRecordError(ValueError):
    """A raw descriptor does not carry the field the record needs."""


def _header(raw: bytes, name: str) -> int:
    field = DESCRIPTOR_HEADER.field(name)
    return int.from_bytes(raw[field.offset : field.offset + field.size], "little")


def _payload(raw: bytes, kind: ExtendedDescriptorType, name: str) -> int:
    layout = PAYLOAD_LAYOUTS[kind]
    field = layout.field(name)
    start = HEADER_BYTES + field.offset
    if start + field.size > len(raw):
        raise SemanticRecordError(
            f"{kind.name} field {name!r} at payload offset {field.offset} runs "
            f"past the {len(raw)}-byte descriptor"
        )
    return int.from_bytes(raw[start : start + field.size], "little")


def _digest_words(raw: bytes) -> list[int]:
    layout = PAYLOAD_LAYOUTS[ExtendedDescriptorType.NUMERIC]
    field = layout.field("contract_digest")
    if field.size != 32:
        raise SemanticRecordError(
            f"the numeric contract digest is {field.size} bytes, not 256 bits"
        )
    start = HEADER_BYTES + field.offset
    digest = raw[start : start + 32]
    return [
        int.from_bytes(digest[offset : offset + 4], "little")
        for offset in range(0, 32, 4)
    ]


def record_from_raw(
    *,
    profile: int,
    active_tokens: int,
    program_counter: int,
    instruction: Mapping[str, int],
    raw: Mapping[str, bytes],
) -> list[int]:
    """The 128 words, read from raw descriptor bytes.

    ``instruction`` carries the five instruction fields the record names -- a
    decoder gives them directly and they are not descriptor bytes.  ``raw`` maps
    each role (``operator``, ``counter``, ``numeric``, ``schedule``, ``wait`` and
    the six view slots) to that descriptor's 192 raw bytes.
    """
    missing = sorted(
        {"operator", "counter", "numeric", "schedule", "wait", *VIEW_SLOTS} - set(raw)
    )
    if missing:
        raise SemanticRecordError(f"the record needs descriptors {missing}")

    words = [0] * CONFIG_WORDS
    T = ExtendedDescriptorType
    words[0:10] = [
        int(profile),
        int(active_tokens),
        int(program_counter),
        int(instruction["flags"]),
        int(instruction["descriptor_id"]),
        int(instruction["wait_set_id"]),
        _payload(raw["wait"], T.EVENT_WAIT_SET, "producer_0"),
        int(instruction["signal_event_id"]),
        int(instruction["control_id"]),
        int(instruction["source_operation_id"]),
    ]
    words[10:28] = [
        _payload(raw["operator"], T.OPERATOR, name) for name in OPERATOR_FIELDS
    ]
    words[28:33] = [
        _payload(raw["counter"], T.COUNTER_CLASS, name) for name in COUNTER_FIELDS
    ]
    words[33:44] = [
        _payload(raw["numeric"], T.NUMERIC, name) for name in NUMERIC_FIELDS
    ]
    words[44:52] = _digest_words(raw["numeric"])
    words[52:64] = [
        _payload(raw["schedule"], T.SCHEDULE, name) for name in SCHEDULE_FIELDS
    ]
    for slot, name in enumerate(VIEW_SLOTS):
        view = raw[name]
        base = 64 + slot * 10
        words[base] = _header(view, "primary_object_id")
        words[base + 1] = _header(view, "permissions")
        words[base + 2 : base + 10] = [
            _payload(view, T.TENSOR_VIEW, field) for field in VIEW_PAYLOAD_FIELDS
        ]
    return words
