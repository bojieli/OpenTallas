from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.checking.deepseek_v4_hc_pre_schedule import (
    EXPECTED_COUNTS,
    DeepSeekV4HCPreScheduleCheckError,
    verify_deepseek_v4_hc_pre_logical_schedule,
    verify_deepseek_v4_hc_pre_logical_schedule_certificate,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_hc_pre import (
    assemble,
    build_program_contract,
    encode,
)
from compiler.scheduling.deepseek_v4_hc_pre import (
    CLAIM_BOUNDARY,
    LOGICAL_SCHEDULE_SCHEMA,
    LOGICAL_SCHEDULE_STATUS,
    DeepSeekV4HCPreScheduleError,
    build_deepseek_v4_hc_pre_logical_schedule,
)


SCHEMA_ROOT = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "compiler"
    / "deepseek_v4_hc_pre_schedule"
)


def _rehash_schedule(schedule: dict[str, Any]) -> None:
    body = {key: value for key, value in schedule.items() if key != "schedule_id"}
    schedule["schedule_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _rehash_certificate(certificate: dict[str, Any]) -> None:
    body = {key: value for key, value in certificate.items() if key != "certificate_id"}
    certificate["certificate_id"] = hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest()


def test_hc_pre_logical_schedule_is_deterministic_and_microcode_bound() -> None:
    first = build_deepseek_v4_hc_pre_logical_schedule()
    second = build_deepseek_v4_hc_pre_logical_schedule()
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["schema"] == LOGICAL_SCHEDULE_SCHEMA
    assert first["status"] == LOGICAL_SCHEDULE_STATUS
    assert first["claim_boundary"] == CLAIM_BOUNDARY

    body = {key: value for key, value in first.items() if key != "schedule_id"}
    assert (
        first["schedule_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    program = assemble()
    payload = encode(program)
    assert len(payload) == 136
    assert first["identity"]["program_sha256"] == hashlib.sha256(payload).hexdigest()
    assert (
        first["identity"]["program_contract_id"]
        == build_program_contract()["contract_id"]
    )
    assert first["identity"]["token_count_minimum"] == 1
    assert first["identity"]["token_count_maximum"] == 4

    assert first["slots"] == [
        {
            **first["slots"][0],
            "dependency_slots": [],
            "destination_register_ids": [3, 4, 5, 6, 7],
            "external_input_register_ids": [2],
            "flags": 0,
            "immediates": [4, 20, 0x358637BD, 0x358637BD],
            "instruction_index": 0,
            "opcode": "HC_PRE",
            "opcode_code": 0x13,
            "resource_ids": [4, 5, 6],
            "slot": 0,
            "source_register_ids": [2],
            "terminal": False,
        },
        {
            **first["slots"][1],
            "dependency_slots": [0],
            "destination_register_ids": [],
            "external_input_register_ids": [],
            "flags": 0,
            "immediates": [0, 0, 0, 0],
            "instruction_index": 1,
            "opcode": "COMPLETE",
            "opcode_code": 0xFF,
            "resource_ids": [],
            "slot": 1,
            "source_register_ids": [],
            "terminal": True,
        },
    ]
    assert first["summary"] == EXPECTED_COUNTS


def test_hc_pre_logical_schedule_freezes_resource_bounds_and_register_causality() -> (
    None
):
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    resources = schedule["resources"]
    assert [record["resource_id"] for record in resources] == [4, 5, 6]
    assert [record["resource_name"] for record in resources] == [
        "HC_ATTN_BASE",
        "HC_ATTN_PROJECTION",
        "HC_ATTN_SCALE",
    ]
    assert [record["shape"] for record in resources] == [
        [24],
        [24, 16384],
        [3],
    ]
    assert [record["size_bytes"] for record in resources] == [96, 1_572_864, 12]
    assert all(record["checkpoint_derived"] is True for record in resources)
    assert all(record["content_sha256"] is None for record in resources)

    registers = schedule["registers"]
    assert [record["register_id"] for record in registers] == list(range(2, 8))
    assert registers[0]["register_name"] == "HC_HIDDEN"
    assert registers[0]["producer_kind"] == "external"
    assert registers[0]["producer_slot"] is None
    assert registers[0]["consumer_slots"] == [0]
    assert all(record["producer_slot"] == 0 for record in registers[1:])
    assert [record["live_at_complete"] for record in registers] == [
        False,
        True,
        False,
        True,
        True,
        True,
    ]
    assert [record["evidence_observable"] for record in registers] == [
        False,
        True,
        True,
        True,
        True,
        True,
    ]


def test_hc_pre_checker_emits_a_canonical_logical_certificate() -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    certificate = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
    body = {key: value for key, value in certificate.items() if key != "certificate_id"}
    assert (
        certificate["certificate_id"]
        == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    assert certificate["status"] == "pass"
    assert certificate["schedule_id"] == schedule["schedule_id"]
    assert certificate["program_sha256"] == schedule["identity"]["program_sha256"]
    assert certificate["counts"] == EXPECTED_COUNTS
    assert all(value is True for value in certificate["checks"].values())
    verify_deepseek_v4_hc_pre_logical_schedule_certificate(certificate, schedule)


def test_hc_pre_schedule_rejects_a_different_executable_fragment() -> None:
    program = assemble()
    changed = (replace(program[0], immediate1=19), program[1])
    with pytest.raises(DeepSeekV4HCPreScheduleError, match="exact microcode fragment"):
        build_deepseek_v4_hc_pre_logical_schedule(changed)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("registers", 1, "live_at_complete"), 1),
        (("slots", 0, "terminal"), 0),
    ],
)
def test_hc_pre_checker_rejects_nested_bool_integer_aliases(
    path: tuple[object, ...],
    replacement: object,
) -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    target: Any = schedule
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4HCPreScheduleCheckError):
        verify_deepseek_v4_hc_pre_logical_schedule(schedule)


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda value: value["slots"][0]["source_register_ids"].__setitem__(0, 3),
            "instruction identity",
        ),
        (
            lambda value: value["slots"][1]["dependency_slots"].clear(),
            "instruction identity",
        ),
        (
            lambda value: value["resources"][1].__setitem__("size_bytes", 1_572_860),
            "resource identities or bounds",
        ),
        (
            lambda value: value["registers"][1].__setitem__("producer_slot", None),
            "register identities or causality",
        ),
        (
            lambda value: value["summary"].__setitem__("resource_read_count", 2),
            "count reconciliation",
        ),
        (
            lambda value: value["slots"][0].__setitem__("invented_latency", 1),
            "instruction identity",
        ),
    ],
)
def test_hc_pre_checker_fails_closed_after_semantic_corruption_and_rehash(
    mutator: Any,
    match: str,
) -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    mutator(schedule)
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4HCPreScheduleCheckError, match=match):
        verify_deepseek_v4_hc_pre_logical_schedule(schedule)


def test_hc_pre_checker_rejects_uncorrected_hash_corruption() -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    schedule["slots"][0]["immediates"][1] = 19
    with pytest.raises(
        DeepSeekV4HCPreScheduleCheckError,
        match="canonical schedule serialization",
    ):
        verify_deepseek_v4_hc_pre_logical_schedule(schedule)


def test_hc_pre_checker_rejects_self_consistent_but_false_certificate() -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    certificate = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
    certificate["checks"]["terminal_complete"] = 1
    _rehash_certificate(certificate)
    with pytest.raises(
        DeepSeekV4HCPreScheduleCheckError,
        match="differs from independent verification",
    ):
        verify_deepseek_v4_hc_pre_logical_schedule_certificate(certificate, schedule)


def test_hc_pre_schedule_and_certificate_schemas_are_strict() -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    certificate = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
    schedule_schema = json.loads(
        (SCHEMA_ROOT / "logical_schedule_v1.schema.json").read_text(encoding="utf-8")
    )
    certificate_schema = json.loads(
        (SCHEMA_ROOT / "logical_schedule_certificate_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    for schema in (schedule_schema, certificate_schema):
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        Draft202012Validator.check_schema(schema)
    Draft202012Validator(schedule_schema).validate(schedule)
    Draft202012Validator(certificate_schema).validate(certificate)

    false_as_zero = copy.deepcopy(schedule)
    false_as_zero["slots"][0]["terminal"] = 0
    assert list(Draft202012Validator(schedule_schema).iter_errors(false_as_zero))
    true_as_one = copy.deepcopy(certificate)
    true_as_one["checks"]["terminal_complete"] = 1
    assert list(Draft202012Validator(certificate_schema).iter_errors(true_as_one))


def test_hc_pre_schedule_contains_no_physical_or_execution_metrics() -> None:
    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    certificate = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
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
    assert [slot["slot"] for slot in schedule["slots"]] == [0, 1]
    assert "logical" in schedule["claim_boundary"].lower()
    assert "not execution" in schedule["claim_boundary"].lower()
