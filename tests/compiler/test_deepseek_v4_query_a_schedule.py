from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import struct
from typing import Any
import zlib

import pytest

import compiler.checking.deepseek_v4_query_a_schedule as schedule_checker
from compiler.checking.deepseek_v4_query_a_schedule import (
    EXPECTED_COUNTS,
    FROZEN_PROGRAM_BYTES,
    FROZEN_PROGRAM_CONTRACT_ID,
    FROZEN_PROGRAM_SHA256,
    DeepSeekV4QueryAScheduleCheckError,
    verify_deepseek_v4_query_a_logical_schedule,
    verify_deepseek_v4_query_a_logical_schedule_certificate,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import HEADER, NO_OPERAND, RECORD
from compiler.microcode.deepseek_v4_query_a import (
    assemble,
    build_program_contract,
    encode,
)
from compiler.scheduling.deepseek_v4_query_a import (
    CLAIM_BOUNDARY,
    LOGICAL_SCHEDULE_SCHEMA,
    LOGICAL_SCHEDULE_STATUS,
    REQUIRED_NONCLAIMS,
    DeepSeekV4QueryAScheduleError,
    build_deepseek_v4_query_a_logical_schedule,
)


def _rehash_schedule(schedule: dict[str, Any]) -> None:
    body = {key: value for key, value in schedule.items() if key != "schedule_id"}
    schedule["schedule_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _rehash_certificate(certificate: dict[str, Any]) -> None:
    body = {key: value for key, value in certificate.items() if key != "certificate_id"}
    certificate["certificate_id"] = hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest()


def test_query_a_logical_schedule_is_deterministic_and_wire_program_bound() -> None:
    first = build_deepseek_v4_query_a_logical_schedule()
    second = build_deepseek_v4_query_a_logical_schedule()
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["schema"] == LOGICAL_SCHEDULE_SCHEMA
    assert first["status"] == LOGICAL_SCHEDULE_STATUS
    assert first["claim_boundary"] == CLAIM_BOUNDARY

    body = {key: value for key, value in first.items() if key != "schedule_id"}
    assert (
        first["schedule_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    payload = encode(assemble())
    assert len(payload) == first["identity"]["program_bytes"] == FROZEN_PROGRAM_BYTES
    assert (
        hashlib.sha256(payload).hexdigest()
        == first["identity"]["program_sha256"]
        == FROZEN_PROGRAM_SHA256
    )
    assert (
        first["identity"]["program_contract_id"]
        == build_program_contract()["contract_id"]
        == FROZEN_PROGRAM_CONTRACT_ID
    )
    assert first["identity"]["token_count_minimum"] == 1
    assert first["identity"]["token_count_maximum"] == 4
    assert first["summary"] == EXPECTED_COUNTS


def test_query_a_logical_schedule_freezes_all_three_slots_and_dependencies() -> None:
    slots = build_deepseek_v4_query_a_logical_schedule()["slots"]
    assert slots == [
        {
            "dependency_slots": [],
            "destination_register_ids": [8],
            "external_input_register_ids": [3],
            "flags": 0,
            "immediates": [4_096, 0x358637BD, 0, 0],
            "instruction_index": 0,
            "instruction_sha256": (
                "0d28fa70f70f55ecba41069f6da538731c1b2df3412d63625f4acbabd384d9d3"
            ),
            "opcode": "RMS_NORM",
            "opcode_code": 0x14,
            "resource_ids": [7],
            "slot": 0,
            "source_register_ids": [3],
            "terminal": False,
        },
        {
            "dependency_slots": [0],
            "destination_register_ids": [9],
            "external_input_register_ids": [],
            "flags": 0,
            "immediates": [1_024, 128, 0, 0],
            "instruction_index": 1,
            "instruction_sha256": (
                "68e6a67ce9e5e60231ca9db76999664c1687e9086cafaf0a31be991bad2f988d"
            ),
            "opcode": "FP8_LINEAR",
            "opcode_code": 0x20,
            "resource_ids": [8, 9, 10],
            "slot": 1,
            "source_register_ids": [8],
            "terminal": False,
        },
        {
            "dependency_slots": [0, 1],
            "destination_register_ids": [],
            "external_input_register_ids": [],
            "flags": 0,
            "immediates": [0, 0, 0, 0],
            "instruction_index": 2,
            "instruction_sha256": (
                "e4a183884f0250ee2f8162726fe2bee8ceb851ea0fbf31311cf0cbe19a3cbd6b"
            ),
            "opcode": "COMPLETE",
            "opcode_code": 0xFF,
            "resource_ids": [],
            "slot": 2,
            "source_register_ids": [],
            "terminal": True,
        },
    ]
    assert sum(len(slot["dependency_slots"]) for slot in slots) == 3


def test_query_a_schedule_freezes_resource_provenance_and_byte_partitions() -> None:
    resources = build_deepseek_v4_query_a_logical_schedule()["resources"]
    assert [record["resource_id"] for record in resources] == [7, 8, 9, 10]
    assert [record["resource_name"] for record in resources] == [
        "ATTN_NORM_WEIGHT",
        "QUERY_A_WEIGHT",
        "QUERY_A_SCALE",
        "QUERY_A_EXHAUSTIVE_ROWS",
    ]
    assert [record["dtype"] for record in resources] == [
        "BF16",
        "F8_E4M3",
        "F8_E8M0",
        "U32",
    ]
    assert [record["shape"] for record in resources] == [
        [4_096],
        [1_024, 4_096],
        [8, 32],
        [1_024],
    ]
    assert [record["size_bytes"] for record in resources] == [
        8_192,
        4_194_304,
        256,
        4_096,
    ]
    assert [record["checkpoint_derived"] for record in resources] == [
        True,
        True,
        True,
        False,
    ]
    assert all(record["content_sha256"] is None for record in resources[:3])
    assert resources[3]["content_sha256"] == (
        "c89db7222126863309183fc023c7091fb18392d16a397dac76a96a022cd62cef"
    )
    assert (
        sum(
            record["size_bytes"] for record in resources if record["checkpoint_derived"]
        )
        == EXPECTED_COUNTS["checkpoint_parameter_bytes"]
    )
    assert (
        sum(
            record["size_bytes"]
            for record in resources
            if not record["checkpoint_derived"]
        )
        == EXPECTED_COUNTS["generated_constant_bytes"]
    )


def test_query_a_schedule_freezes_register_causality_and_liveness() -> None:
    registers = build_deepseek_v4_query_a_logical_schedule()["registers"]
    assert [record["register_id"] for record in registers] == [3, 8, 9]
    assert [record["register_name"] for record in registers] == [
        "ATTENTION_INPUT",
        "ATTENTION_NORMALIZED",
        "QUERY_A",
    ]
    assert [record["producer_kind"] for record in registers] == [
        "external",
        "slot",
        "slot",
    ]
    assert [record["producer_slot"] for record in registers] == [None, 0, 1]
    assert [record["consumer_slots"] for record in registers] == [[0], [1], []]
    assert [record["token_major_shape_suffix"] for record in registers] == [
        [4_096],
        [4_096],
        [1_024],
    ]
    assert [record["live_at_complete"] for record in registers] == [
        False,
        False,
        True,
    ]
    assert all(record["evidence_observable"] is True for record in registers)


def test_query_a_checker_emits_a_canonical_independent_certificate() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
    body = {key: value for key, value in certificate.items() if key != "certificate_id"}
    assert (
        certificate["certificate_id"]
        == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    assert certificate["status"] == "pass"
    assert certificate["schedule_id"] == schedule["schedule_id"]
    assert certificate["program_sha256"] == FROZEN_PROGRAM_SHA256
    assert certificate["program_contract_id"] == FROZEN_PROGRAM_CONTRACT_ID
    assert certificate["counts"] == EXPECTED_COUNTS
    assert certificate["checks"]["wire_program_decode"] is True
    assert certificate["checks"]["generated_constant_partition"] is True
    assert all(value is True for value in certificate["checks"].values())
    verify_deepseek_v4_query_a_logical_schedule_certificate(certificate, schedule)


def test_query_a_checker_independently_decodes_crc_and_frozen_wire_operands() -> None:
    payload = encode(assemble())
    decoded = schedule_checker._decode_frozen_program(payload)
    assert [record["opcode"] for record in decoded] == [0x14, 0x20, 0xFF]
    assert decoded[0]["source"] == 3
    assert decoded[0]["destination0"] == 8
    assert decoded[1]["source"] == 8
    assert decoded[1]["destination0"] == 9

    bad_crc = bytearray(payload)
    bad_crc[-1] ^= 1
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match="CRC32"):
        schedule_checker._decode_frozen_program(bytes(bad_crc))

    bad_reserved = bytearray(payload)
    bad_reserved[HEADER.size + 2] = 1
    struct.pack_into(
        "<I",
        bad_reserved,
        12,
        zlib.crc32(bad_reserved[HEADER.size :]) & 0xFFFFFFFF,
    )
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match="reserved bits"):
        schedule_checker._decode_frozen_program(bytes(bad_reserved))

    changed_operand = bytearray(payload)
    first_immediate0 = HEADER.size + 4 + 10 * 4
    struct.pack_into("<I", changed_operand, first_immediate0, 4_095)
    struct.pack_into(
        "<I",
        changed_operand,
        12,
        zlib.crc32(changed_operand[HEADER.size :]) & 0xFFFFFFFF,
    )
    assert len(changed_operand) == HEADER.size + 3 * RECORD.size
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match="frozen program"):
        schedule_checker._decode_frozen_program(bytes(changed_operand))


@pytest.mark.parametrize(
    "changed",
    [
        (
            replace(assemble()[0], immediate1=0x358637BC),
            assemble()[1],
            assemble()[2],
        ),
        (
            assemble()[0],
            replace(assemble()[1], resource2=NO_OPERAND),
            assemble()[2],
        ),
        assemble()[:-1],
    ],
)
def test_query_a_schedule_rejects_a_different_executable_fragment(
    changed: tuple[Any, ...],
) -> None:
    with pytest.raises(DeepSeekV4QueryAScheduleError, match="exact microcode fragment"):
        build_deepseek_v4_query_a_logical_schedule(changed)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("registers", 1, "live_at_complete"), 0),
        (("resources", 3, "checkpoint_derived"), 0),
        (("slots", 0, "terminal"), 0),
    ],
)
def test_query_a_checker_rejects_nested_bool_integer_aliases(
    path: tuple[object, ...],
    replacement: object,
) -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    target: Any = schedule
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError):
        verify_deepseek_v4_query_a_logical_schedule(schedule)


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda value: value["slots"][0]["source_register_ids"].__setitem__(0, 8),
            "instruction identity",
        ),
        (
            lambda value: value["slots"][1]["dependency_slots"].clear(),
            "instruction identity",
        ),
        (
            lambda value: value["slots"][2]["dependency_slots"].pop(0),
            "instruction identity",
        ),
        (
            lambda value: value["resources"][1].__setitem__("size_bytes", 4_194_303),
            "resource identities or bounds",
        ),
        (
            lambda value: value["registers"][1].__setitem__("producer_slot", None),
            "register identities or causality",
        ),
        (
            lambda value: value["summary"].__setitem__("generated_constant_bytes", 0),
            "count reconciliation",
        ),
        (
            lambda value: value["slots"][0].__setitem__("cycles", 1),
            "instruction identity",
        ),
    ],
)
def test_query_a_checker_fails_closed_after_semantic_corruption_and_rehash(
    mutator: Any,
    match: str,
) -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    mutator(schedule)
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match=match):
        verify_deepseek_v4_query_a_logical_schedule(schedule)


def test_query_a_checker_rejects_uncorrected_hash_corruption() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    schedule["slots"][1]["immediates"][1] = 127
    with pytest.raises(
        DeepSeekV4QueryAScheduleCheckError,
        match="canonical schedule serialization",
    ):
        verify_deepseek_v4_query_a_logical_schedule(schedule)


def test_query_a_checker_rejects_self_consistent_but_false_certificate() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
    certificate["checks"]["wire_program_decode"] = 1
    _rehash_certificate(certificate)
    with pytest.raises(
        DeepSeekV4QueryAScheduleCheckError,
        match="differs from independent verification",
    ):
        verify_deepseek_v4_query_a_logical_schedule_certificate(certificate, schedule)


def test_query_a_schedule_and_certificate_fields_are_strict() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    schedule["invented"] = "value"
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match="fields differ"):
        verify_deepseek_v4_query_a_logical_schedule(schedule)

    clean_schedule = build_deepseek_v4_query_a_logical_schedule()
    certificate = verify_deepseek_v4_query_a_logical_schedule(clean_schedule)
    certificate["invented"] = "value"
    _rehash_certificate(certificate)
    with pytest.raises(DeepSeekV4QueryAScheduleCheckError, match="fields differ"):
        verify_deepseek_v4_query_a_logical_schedule_certificate(
            certificate, clean_schedule
        )


def test_query_a_schedule_contains_explicit_nonclaims_and_no_physical_metrics() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
    assert schedule["required_nonclaims"] == list(REQUIRED_NONCLAIMS)
    assert {
        "bandwidth",
        "checkpoint_execution",
        "cycle_accuracy",
        "execution_evidence",
        "physical_schedule",
        "ppa",
        "rtl_execution",
    }.issubset(schedule["required_nonclaims"])
    forbidden_keys = {
        "bandwidth",
        "cycles",
        "energy",
        "execution_results",
        "frequency",
        "latency",
        "physical_stage",
        "physical_topology",
        "power",
        "throughput",
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            assert forbidden_keys.isdisjoint(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schedule)
    visit(certificate)
    assert [slot["slot"] for slot in schedule["slots"]] == [0, 1, 2]
    assert "logical" in schedule["claim_boundary"].lower()
    assert "not execution" in schedule["claim_boundary"].lower()


def test_query_a_checker_does_not_mutate_schedule_or_certificate_inputs() -> None:
    schedule = build_deepseek_v4_query_a_logical_schedule()
    original_schedule = copy.deepcopy(schedule)
    certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
    assert schedule == original_schedule
    original_certificate = copy.deepcopy(certificate)
    verify_deepseek_v4_query_a_logical_schedule_certificate(certificate, schedule)
    assert schedule == original_schedule
    assert certificate == original_certificate
