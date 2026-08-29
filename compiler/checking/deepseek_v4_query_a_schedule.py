"""Independent checker for the DeepSeek V4 Query-A logical schedule.

The checker does not import the schedule builder.  It decodes the committed
wire bytes independently, freezes every operand, reconstructs resource and
register tables from the typed contracts, and checks producer-before-consumer
causality.  A passing certificate is logical conformance evidence only; it is
not execution, timing, bandwidth, physical-schedule, numerical, or PPA proof.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any
import zlib

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    ABI_MAJOR,
    ABI_MINOR,
    HEADER,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    NO_OPERAND,
    RECORD,
    Register,
)
from compiler.microcode.deepseek_v4_query_a import (
    MODEL_ID,
    assemble,
    build_program_contract,
    encode,
    resource_contract,
    tensor_contract,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_query_a_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_query_a_logical_schedule_certificate.v1"
)
LOGICAL_SCHEDULE_STATUS = "logical_schedule_only"
CERTIFICATE_STATUS = "pass"
CLAIM_BOUNDARY = (
    "Deterministic logical instruction, register, and resource ordering for the "
    "exact weighted-RMS and complete Query-A fragment only; this is not "
    "execution, timing, bandwidth, physical scheduling, numeric-correctness, "
    "or PPA evidence."
)
CERTIFICATE_CLAIM_BOUNDARY = (
    "Independent Query-A logical-schedule conformance certificate only; no "
    "execution, cycle, bandwidth, physical-schedule, numeric-correctness, or "
    "PPA claim."
)
REQUIRED_NONCLAIMS = [
    "attention_completion",
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "execution_evidence",
    "full_model_execution",
    "hc_pre_execution",
    "nvidia_comparison",
    "numeric_correctness",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "query_b",
    "rtl_execution",
    "transformer_block_completion",
]
ORDERING_POLICY = {
    "completion_rule": "terminal COMPLETE depends on every preceding logical slot",
    "dependency_rule": (
        "every consumed register is external or produced by a lower-numbered slot"
    ),
    "resource_rule": (
        "resource IDs resolve exactly through the committed Query-A resource contract"
    ),
    "slot_rule": "one microinstruction per monotonically increasing logical slot",
}
EXPECTED_COUNTS = {
    "checkpoint_parameter_bytes": 4_202_752,
    "complete_count": 1,
    "dependency_edge_count": 3,
    "evidence_observable_register_count": 3,
    "external_input_register_count": 1,
    "fp8_linear_count": 1,
    "generated_constant_bytes": 4_096,
    "instruction_count": 3,
    "live_at_complete_register_count": 1,
    "produced_register_count": 2,
    "register_count": 3,
    "resource_count": 4,
    "resource_read_count": 4,
    "rms_norm_count": 1,
    "slot_count": 3,
}

FROZEN_PROGRAM_BYTES = 196
FROZEN_PROGRAM_SHA256 = (
    "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
)
FROZEN_PROGRAM_CONTRACT_ID = (
    "0aa1969479c527d33fa893557f40dd05e3efbc9a3e1af7d959d4cb8496806903"
)
FROZEN_EXHAUSTIVE_ROWS_SHA256 = (
    "c89db7222126863309183fc023c7091fb18392d16a397dac76a96a022cd62cef"
)


class DeepSeekV4QueryAScheduleCheckError(ValueError):
    """Raised when a Query-A schedule or certificate fails closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/int equality aliasing."""

    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4QueryAScheduleCheckError(f"{label} must be an object")
    if not all(type(key) is str for key in value):
        raise DeepSeekV4QueryAScheduleCheckError(f"{label} keys must be strings")
    return value


def _exact(
    value: object,
    keys: set[str],
    label: str,
) -> Mapping[str, Any]:
    record = _mapping(value, label)
    observed = set(record)
    if observed != keys:
        missing = sorted(keys - observed)
        extra = sorted(observed - keys)
        raise DeepSeekV4QueryAScheduleCheckError(
            f"{label} fields differ; missing={missing}, extra={extra}"
        )
    return record


def _array(value: object, label: str) -> list[Any]:
    if type(value) is not list:
        raise DeepSeekV4QueryAScheduleCheckError(f"{label} must be an array")
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DeepSeekV4QueryAScheduleCheckError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4QueryAScheduleCheckError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _frozen_instruction_identities() -> list[dict[str, int]]:
    """Return raw instruction identities independently frozen from the builder."""

    return [
        {
            "destination0": 8,
            "destination1": NO_OPERAND,
            "destination2": NO_OPERAND,
            "destination3": NO_OPERAND,
            "destination4": NO_OPERAND,
            "flags": 0,
            "immediate0": 4_096,
            "immediate1": 0x358637BD,
            "immediate2": 0,
            "immediate3": 0,
            "opcode": 0x14,
            "resource0": 7,
            "resource1": NO_OPERAND,
            "resource2": NO_OPERAND,
            "resource3": NO_OPERAND,
            "source": 3,
        },
        {
            "destination0": 9,
            "destination1": NO_OPERAND,
            "destination2": NO_OPERAND,
            "destination3": NO_OPERAND,
            "destination4": NO_OPERAND,
            "flags": 0,
            "immediate0": 1_024,
            "immediate1": 128,
            "immediate2": 0,
            "immediate3": 0,
            "opcode": 0x20,
            "resource0": 8,
            "resource1": 9,
            "resource2": 10,
            "resource3": NO_OPERAND,
            "source": 8,
        },
        {
            "destination0": NO_OPERAND,
            "destination1": NO_OPERAND,
            "destination2": NO_OPERAND,
            "destination3": NO_OPERAND,
            "destination4": NO_OPERAND,
            "flags": 0,
            "immediate0": 0,
            "immediate1": 0,
            "immediate2": 0,
            "immediate3": 0,
            "opcode": 0xFF,
            "resource0": NO_OPERAND,
            "resource1": NO_OPERAND,
            "resource2": NO_OPERAND,
            "resource3": NO_OPERAND,
            "source": NO_OPERAND,
        },
    ]


def _decode_frozen_program(payload: bytes) -> list[dict[str, int]]:
    """Decode the wire ABI without calling the microcode module's decoder."""

    if type(payload) is not bytes or len(payload) != FROZEN_PROGRAM_BYTES:
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A wire program has an unexpected byte length"
        )
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if (magic, major, minor, record_size, count) != (b"OTEQ", 1, 0, 60, 3):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A wire header differs from the frozen ABI"
        )
    body = payload[HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A wire body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A wire body fails CRC32 verification"
        )

    decoded: list[dict[str, int]] = []
    for index in range(count):
        unpacked = RECORD.unpack_from(body, index * record_size)
        opcode, flags, reserved = unpacked[:3]
        if reserved != 0:
            raise DeepSeekV4QueryAScheduleCheckError(
                f"committed Query-A instruction {index} has reserved bits"
            )
        operands = unpacked[3:]
        decoded.append(
            {
                "destination0": operands[0],
                "destination1": operands[1],
                "destination2": operands[2],
                "destination3": operands[3],
                "destination4": operands[4],
                "flags": flags,
                "immediate0": operands[10],
                "immediate1": operands[11],
                "immediate2": operands[12],
                "immediate3": operands[13],
                "opcode": opcode,
                "resource0": operands[6],
                "resource1": operands[7],
                "resource2": operands[8],
                "resource3": operands[9],
                "source": operands[5],
            }
        )
    expected = _frozen_instruction_identities()
    if not _canonical_equal(decoded, expected):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A wire operands differ from the frozen program"
        )
    return decoded


def _expected_resources() -> list[dict[str, Any]]:
    specs = resource_contract()
    verify_resource_contract(specs)
    records = [
        {
            "checkpoint_derived": spec.checkpoint_derived,
            "content_sha256": spec.content_sha256,
            "dtype": spec.dtype,
            "rank": spec.rank,
            "resource_id": int(spec.resource),
            "resource_name": spec.resource.name,
            "role": spec.role,
            "row_start": spec.row_start,
            "row_stop": spec.row_stop,
            "shape": list(spec.shape),
            "size_bytes": spec.size_bytes,
        }
        for spec in specs
    ]
    frozen = [
        {
            "checkpoint_derived": True,
            "content_sha256": None,
            "dtype": "BF16",
            "rank": None,
            "resource_id": 7,
            "resource_name": "ATTN_NORM_WEIGHT",
            "role": "block.attention_norm.weight",
            "row_start": None,
            "row_stop": None,
            "shape": [4_096],
            "size_bytes": 8_192,
        },
        {
            "checkpoint_derived": True,
            "content_sha256": None,
            "dtype": "F8_E4M3",
            "rank": None,
            "resource_id": 8,
            "resource_name": "QUERY_A_WEIGHT",
            "role": "attention.query_a.weight",
            "row_start": None,
            "row_stop": None,
            "shape": [1_024, 4_096],
            "size_bytes": 4_194_304,
        },
        {
            "checkpoint_derived": True,
            "content_sha256": None,
            "dtype": "F8_E8M0",
            "rank": None,
            "resource_id": 9,
            "resource_name": "QUERY_A_SCALE",
            "role": "attention.query_a.scale",
            "row_start": None,
            "row_stop": None,
            "shape": [8, 32],
            "size_bytes": 256,
        },
        {
            "checkpoint_derived": False,
            "content_sha256": FROZEN_EXHAUSTIVE_ROWS_SHA256,
            "dtype": "U32",
            "rank": None,
            "resource_id": 10,
            "resource_name": "QUERY_A_EXHAUSTIVE_ROWS",
            "role": "attention.query_a.exhaustive_output_rows",
            "row_start": None,
            "row_stop": None,
            "shape": [1_024],
            "size_bytes": 4_096,
        },
    ]
    if not _canonical_equal(records, frozen):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A resources differ from independently frozen bounds"
        )
    return records


def _expected_registers() -> list[dict[str, Any]]:
    lower = tensor_contract(MIN_TOKEN_COUNT)
    upper = tensor_contract(MAX_TOKEN_COUNT)
    verify_tensor_contract(lower, MIN_TOKEN_COUNT)
    verify_tensor_contract(upper, MAX_TOKEN_COUNT)
    if len(lower) != len(upper):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A tensor bounds have different register counts"
        )

    producer_slots = {
        Register.ATTENTION_NORMALIZED: 0,
        Register.QUERY_A: 1,
    }
    consumers = {
        Register.ATTENTION_INPUT: [0],
        Register.ATTENTION_NORMALIZED: [1],
    }
    records: list[dict[str, Any]] = []
    for minimum_spec, maximum_spec in zip(lower, upper, strict=True):
        if (
            minimum_spec.register != maximum_spec.register
            or minimum_spec.dtype != maximum_spec.dtype
            or minimum_spec.live_at_complete != maximum_spec.live_at_complete
            or minimum_spec.evidence_observable != maximum_spec.evidence_observable
            or minimum_spec.shape[0] != MIN_TOKEN_COUNT
            or maximum_spec.shape[0] != MAX_TOKEN_COUNT
            or minimum_spec.shape[1:] != maximum_spec.shape[1:]
        ):
            raise DeepSeekV4QueryAScheduleCheckError(
                "committed Query-A tensor bounds are internally inconsistent"
            )
        register = minimum_spec.register
        records.append(
            {
                "consumer_slots": consumers.get(register, []),
                "dtype": minimum_spec.dtype,
                "evidence_observable": minimum_spec.evidence_observable,
                "live_at_complete": minimum_spec.live_at_complete,
                "producer_kind": "slot" if register in producer_slots else "external",
                "producer_slot": producer_slots.get(register),
                "register_id": int(register),
                "register_name": register.name,
                "token_major_shape_suffix": list(minimum_spec.shape[1:]),
            }
        )
    frozen = [
        {
            "consumer_slots": [0],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": False,
            "producer_kind": "external",
            "producer_slot": None,
            "register_id": 3,
            "register_name": "ATTENTION_INPUT",
            "token_major_shape_suffix": [4_096],
        },
        {
            "consumer_slots": [1],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": False,
            "producer_kind": "slot",
            "producer_slot": 0,
            "register_id": 8,
            "register_name": "ATTENTION_NORMALIZED",
            "token_major_shape_suffix": [4_096],
        },
        {
            "consumer_slots": [],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": True,
            "producer_kind": "slot",
            "producer_slot": 1,
            "register_id": 9,
            "register_name": "QUERY_A",
            "token_major_shape_suffix": [1_024],
        },
    ]
    if not _canonical_equal(records, frozen):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A registers differ from independently frozen bounds"
        )
    return records


def _used_ids(record: Mapping[str, int], prefix: str, count: int) -> list[int]:
    return [
        value
        for index in range(count)
        if (value := record[f"{prefix}{index}"]) != NO_OPERAND
    ]


def _expected_slots(
    instructions: Sequence[Mapping[str, int]],
) -> list[dict[str, Any]]:
    rms, linear, complete = instructions
    return [
        {
            "dependency_slots": [],
            "destination_register_ids": _used_ids(rms, "destination", 5),
            "external_input_register_ids": [rms["source"]],
            "flags": rms["flags"],
            "immediates": [
                rms["immediate0"],
                rms["immediate1"],
                rms["immediate2"],
                rms["immediate3"],
            ],
            "instruction_index": 0,
            "instruction_sha256": _sha256(dict(rms)),
            "opcode": "RMS_NORM",
            "opcode_code": rms["opcode"],
            "resource_ids": _used_ids(rms, "resource", 4),
            "slot": 0,
            "source_register_ids": [rms["source"]],
            "terminal": False,
        },
        {
            "dependency_slots": [0],
            "destination_register_ids": _used_ids(linear, "destination", 5),
            "external_input_register_ids": [],
            "flags": linear["flags"],
            "immediates": [
                linear["immediate0"],
                linear["immediate1"],
                linear["immediate2"],
                linear["immediate3"],
            ],
            "instruction_index": 1,
            "instruction_sha256": _sha256(dict(linear)),
            "opcode": "FP8_LINEAR",
            "opcode_code": linear["opcode"],
            "resource_ids": _used_ids(linear, "resource", 4),
            "slot": 1,
            "source_register_ids": [linear["source"]],
            "terminal": False,
        },
        {
            "dependency_slots": [0, 1],
            "destination_register_ids": _used_ids(complete, "destination", 5),
            "external_input_register_ids": [],
            "flags": complete["flags"],
            "immediates": [
                complete["immediate0"],
                complete["immediate1"],
                complete["immediate2"],
                complete["immediate3"],
            ],
            "instruction_index": 2,
            "instruction_sha256": _sha256(dict(complete)),
            "opcode": "COMPLETE",
            "opcode_code": complete["opcode"],
            "resource_ids": _used_ids(complete, "resource", 4),
            "slot": 2,
            "source_register_ids": [],
            "terminal": True,
        },
    ]


def _reconcile_counts(
    slots: Sequence[Mapping[str, Any]],
    registers: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    checkpoint_bytes = 0
    generated_bytes = 0
    for record in resources:
        size_bytes = _integer(record.get("size_bytes"), "resource size_bytes")
        checkpoint_derived = record.get("checkpoint_derived")
        if type(checkpoint_derived) is not bool:
            raise DeepSeekV4QueryAScheduleCheckError(
                "resource checkpoint_derived must be boolean"
            )
        if checkpoint_derived:
            checkpoint_bytes += size_bytes
        else:
            generated_bytes += size_bytes
    return {
        "checkpoint_parameter_bytes": checkpoint_bytes,
        "complete_count": sum(record.get("opcode") == "COMPLETE" for record in slots),
        "dependency_edge_count": sum(
            len(_array(record.get("dependency_slots"), "slot dependency_slots"))
            for record in slots
        ),
        "evidence_observable_register_count": sum(
            record.get("evidence_observable") is True for record in registers
        ),
        "external_input_register_count": sum(
            record.get("producer_kind") == "external" for record in registers
        ),
        "fp8_linear_count": sum(
            record.get("opcode") == "FP8_LINEAR" for record in slots
        ),
        "generated_constant_bytes": generated_bytes,
        "instruction_count": len(slots),
        "live_at_complete_register_count": sum(
            record.get("live_at_complete") is True for record in registers
        ),
        "produced_register_count": sum(
            record.get("producer_kind") == "slot" for record in registers
        ),
        "register_count": len(registers),
        "resource_count": len(resources),
        "resource_read_count": sum(
            len(_array(record.get("resource_ids"), "slot resource_ids"))
            for record in slots
        ),
        "rms_norm_count": sum(record.get("opcode") == "RMS_NORM" for record in slots),
        "slot_count": len(slots),
    }


def _verify_causality(
    slots: Sequence[Mapping[str, Any]],
    registers: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> None:
    register_by_id = {
        _integer(record.get("register_id"), "register_id"): record
        for record in registers
    }
    resource_ids = {
        _integer(record.get("resource_id"), "resource_id") for record in resources
    }
    if len(register_by_id) != len(registers) or len(resource_ids) != len(resources):
        raise DeepSeekV4QueryAScheduleCheckError(
            "register or resource identity is duplicated"
        )

    observed_consumers: dict[int, list[int]] = {
        register_id: [] for register_id in register_by_id
    }
    observed_producers: dict[int, int] = {}
    terminal_count = 0
    for index, slot in enumerate(slots):
        if slot.get("slot") != index or slot.get("instruction_index") != index:
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} is not monotonically ordered"
            )
        dependencies = _array(slot.get("dependency_slots"), "dependency_slots")
        dependency_ids = [
            _integer(dependency, "dependency slot") for dependency in dependencies
        ]
        if dependency_ids != sorted(set(dependency_ids)) or any(
            dependency >= index for dependency in dependency_ids
        ):
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} has invalid preceding dependencies"
            )

        external_ids = [
            _integer(value, "external register ID")
            for value in _array(
                slot.get("external_input_register_ids"), "external register IDs"
            )
        ]
        if external_ids != sorted(set(external_ids)):
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} duplicates an external register"
            )
        required_dependencies: set[int] = set()
        required_external: set[int] = set()
        for raw_register_id in _array(
            slot.get("source_register_ids"), "source register IDs"
        ):
            register_id = _integer(raw_register_id, "source register ID")
            try:
                register = register_by_id[register_id]
            except KeyError as exc:
                raise DeepSeekV4QueryAScheduleCheckError(
                    f"logical slot {index} reads unknown register {register_id}"
                ) from exc
            observed_consumers[register_id].append(index)
            producer = register.get("producer_slot")
            if register.get("producer_kind") == "external":
                if producer is not None:
                    raise DeepSeekV4QueryAScheduleCheckError(
                        f"logical slot {index} has incorrect external causality"
                    )
                required_external.add(register_id)
            elif type(producer) is not int or producer >= index:
                raise DeepSeekV4QueryAScheduleCheckError(
                    f"logical slot {index} consumes a non-preceding producer"
                )
            else:
                required_dependencies.add(producer)
        if set(external_ids) != required_external:
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} external inputs differ from its sources"
            )

        destination_ids = [
            _integer(value, "destination register ID")
            for value in _array(
                slot.get("destination_register_ids"), "destination register IDs"
            )
        ]
        if destination_ids != list(dict.fromkeys(destination_ids)):
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} duplicates a destination register"
            )
        for register_id in destination_ids:
            if (
                register_id not in register_by_id
                or register_by_id[register_id].get("producer_slot") != index
                or register_id in observed_producers
            ):
                raise DeepSeekV4QueryAScheduleCheckError(
                    f"logical slot {index} has an incorrect destination producer"
                )
            observed_producers[register_id] = index

        used_resources = [
            _integer(value, "used resource ID")
            for value in _array(slot.get("resource_ids"), "resource IDs")
        ]
        if (
            len(used_resources) != len(set(used_resources))
            or not set(used_resources) <= resource_ids
        ):
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} has duplicated or unknown resources"
            )

        if slot.get("terminal") is True:
            terminal_count += 1
            if (
                index != len(slots) - 1
                or dependency_ids != list(range(index))
                or destination_ids
                or slot.get("source_register_ids") != []
                or used_resources
            ):
                raise DeepSeekV4QueryAScheduleCheckError(
                    "terminal COMPLETE is not the final all-predecessor barrier"
                )
        elif set(dependency_ids) != required_dependencies:
            raise DeepSeekV4QueryAScheduleCheckError(
                f"logical slot {index} dependencies differ from producer causality"
            )

    if terminal_count != 1 or not slots or slots[-1].get("opcode") != "COMPLETE":
        raise DeepSeekV4QueryAScheduleCheckError(
            "logical schedule lacks one exact terminal COMPLETE"
        )
    for register_id, register in register_by_id.items():
        if not _canonical_equal(
            register.get("consumer_slots"), observed_consumers[register_id]
        ):
            raise DeepSeekV4QueryAScheduleCheckError(
                f"register {register_id} consumer table differs from slot reads"
            )
        producer_kind = register.get("producer_kind")
        if producer_kind == "external":
            if register_id in observed_producers:
                raise DeepSeekV4QueryAScheduleCheckError(
                    f"external register {register_id} is also produced by a slot"
                )
        elif producer_kind == "slot":
            if observed_producers.get(register_id) != register.get("producer_slot"):
                raise DeepSeekV4QueryAScheduleCheckError(
                    f"register {register_id} producer table differs from slot writes"
                )
        else:
            raise DeepSeekV4QueryAScheduleCheckError(
                f"register {register_id} has an unknown producer kind"
            )


def verify_deepseek_v4_query_a_logical_schedule(
    value: object,
) -> dict[str, Any]:
    """Verify the schedule and return a hash-bound logical certificate."""

    schedule = _exact(
        value,
        {
            "claim_boundary",
            "identity",
            "ordering_policy",
            "registers",
            "required_nonclaims",
            "resources",
            "schedule_id",
            "schema",
            "slots",
            "status",
            "summary",
        },
        "Query-A logical schedule",
    )
    if schedule["schema"] != LOGICAL_SCHEDULE_SCHEMA:
        raise DeepSeekV4QueryAScheduleCheckError(
            "unsupported Query-A logical schedule schema"
        )
    if schedule["status"] != LOGICAL_SCHEDULE_STATUS:
        raise DeepSeekV4QueryAScheduleCheckError("Query-A schedule status differs")
    body = {key: schedule[key] for key in schedule if key != "schedule_id"}
    if _digest(schedule["schedule_id"], "schedule_id") != _sha256(body):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule_id does not bind canonical schedule serialization"
        )
    if schedule["claim_boundary"] != CLAIM_BOUNDARY:
        raise DeepSeekV4QueryAScheduleCheckError("schedule claim boundary differs")
    if not _canonical_equal(schedule["ordering_policy"], ORDERING_POLICY):
        raise DeepSeekV4QueryAScheduleCheckError("schedule ordering policy differs")
    if not _canonical_equal(schedule["required_nonclaims"], REQUIRED_NONCLAIMS):
        raise DeepSeekV4QueryAScheduleCheckError("schedule nonclaims differ")

    program = assemble()
    verify(program)
    program_payload = encode(program)
    if (
        len(program_payload) != FROZEN_PROGRAM_BYTES
        or hashlib.sha256(program_payload).hexdigest() != FROZEN_PROGRAM_SHA256
    ):
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A program bytes differ from the frozen identity"
        )
    decoded_instructions = _decode_frozen_program(program_payload)
    program_contract = build_program_contract()
    verify_program_contract(program_contract)
    if program_contract.get("contract_id") != FROZEN_PROGRAM_CONTRACT_ID:
        raise DeepSeekV4QueryAScheduleCheckError(
            "committed Query-A program contract identity differs"
        )

    expected_resources = _expected_resources()
    expected_registers = _expected_registers()
    expected_slots = _expected_slots(decoded_instructions)
    expected_identity = {
        "abi_magic_ascii": MAGIC.decode("ascii"),
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "instruction_record_bytes": RECORD.size,
        "model_id": MODEL_ID,
        "program_bytes": FROZEN_PROGRAM_BYTES,
        "program_contract_id": FROZEN_PROGRAM_CONTRACT_ID,
        "program_sha256": FROZEN_PROGRAM_SHA256,
        "register_table_sha256": _sha256(expected_registers),
        "resource_table_sha256": _sha256(expected_resources),
        "token_count_maximum": MAX_TOKEN_COUNT,
        "token_count_minimum": MIN_TOKEN_COUNT,
    }
    if not _canonical_equal(schedule["identity"], expected_identity):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule program or table identity differs"
        )

    resources = _array(schedule["resources"], "schedule resources")
    registers = _array(schedule["registers"], "schedule registers")
    slots = _array(schedule["slots"], "schedule slots")
    if not _canonical_equal(resources, expected_resources):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule resource identities or bounds differ"
        )
    if not _canonical_equal(registers, expected_registers):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule register identities or causality differ"
        )
    if not _canonical_equal(slots, expected_slots):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule instruction identity or ordering differs"
        )
    _verify_causality(slots, registers, resources)
    reconciled = _reconcile_counts(slots, registers, resources)
    if not _canonical_equal(reconciled, EXPECTED_COUNTS) or not _canonical_equal(
        schedule["summary"], EXPECTED_COUNTS
    ):
        raise DeepSeekV4QueryAScheduleCheckError(
            "schedule exact count reconciliation differs"
        )

    certificate_body = {
        "checks": {
            "canonical_serialization_hash": True,
            "exact_count_reconciliation": True,
            "generated_constant_partition": True,
            "instruction_identity": True,
            "producer_before_consumer": True,
            "register_contract": True,
            "resource_identity_and_bounds": True,
            "terminal_complete": True,
            "wire_program_decode": True,
        },
        "claim_boundary": CERTIFICATE_CLAIM_BOUNDARY,
        "counts": dict(EXPECTED_COUNTS),
        "program_contract_id": expected_identity["program_contract_id"],
        "program_sha256": expected_identity["program_sha256"],
        "register_table_sha256": expected_identity["register_table_sha256"],
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "resource_table_sha256": expected_identity["resource_table_sha256"],
        "schedule_id": schedule["schedule_id"],
        "schema": LOGICAL_CERTIFICATE_SCHEMA,
        "status": CERTIFICATE_STATUS,
    }
    return {
        **certificate_body,
        "certificate_id": _sha256(certificate_body),
    }


def verify_deepseek_v4_query_a_logical_schedule_certificate(
    value: object,
    schedule: object,
) -> None:
    """Require a certificate to equal an independent fresh schedule check."""

    expected = verify_deepseek_v4_query_a_logical_schedule(schedule)
    certificate = _exact(
        value,
        set(expected),
        "Query-A logical schedule certificate",
    )
    if not _canonical_equal(dict(certificate), expected):
        raise DeepSeekV4QueryAScheduleCheckError(
            "logical schedule certificate differs from independent verification"
        )


__all__ = [
    "CERTIFICATE_CLAIM_BOUNDARY",
    "CERTIFICATE_STATUS",
    "EXPECTED_COUNTS",
    "FROZEN_PROGRAM_BYTES",
    "FROZEN_PROGRAM_CONTRACT_ID",
    "FROZEN_PROGRAM_SHA256",
    "LOGICAL_CERTIFICATE_SCHEMA",
    "LOGICAL_SCHEDULE_SCHEMA",
    "DeepSeekV4QueryAScheduleCheckError",
    "verify_deepseek_v4_query_a_logical_schedule",
    "verify_deepseek_v4_query_a_logical_schedule_certificate",
]
