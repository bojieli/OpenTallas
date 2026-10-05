"""Logical schedule and certificate for the ratio-four compressor slice.

Logical slots establish causality and artifact identity only.  They do not
represent cycles, placement, transfers, utilization, or physical timing.
"""

from __future__ import annotations

import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_compressor import (
    MODEL_ID,
    PROGRAM_SHA256,
    assemble,
)


SCHEDULE_SCHEMA = "opentallas.deepseek_v4_compressor_logical_schedule.v1"
CERTIFICATE_SCHEMA = "opentallas.deepseek_v4_compressor_logical_schedule_certificate.v1"
SCHEDULE_STATUS = "logical_causality_only_no_cycle_claim"
NONCLAIMS = [
    "achieved_bandwidth",
    "cycles",
    "energy",
    "gpu_comparison",
    "latency",
    "physical_hbm_or_sram_transactions",
    "placement",
    "ppa",
    "rom_advantage",
    "routing",
    "throughput",
]


class DeepSeekV4CompressorScheduleError(ValueError):
    """Raised when a logical compressor schedule or certificate differs."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def build_logical_schedule(*, ape_sha256: str) -> dict[str, Any]:
    """Build the exact schedule implied by the fixed semantic microprogram."""

    program = assemble()
    slot_contracts = (
        {
            "condition": "always",
            "consumes": [
                "ape_f32",
                "prior_raw_state",
                "projected_kv_f32",
                "projected_scores_f32",
                "session_ids",
                "start_pos",
            ],
            "depends_on": [],
            "produces": ["candidate_raw_state", "optional_pool_operands"],
        },
        {
            "condition": "candidate_raw_state.should_compress",
            "consumes": ["optional_pool_operands"],
            "depends_on": [0],
            "produces": ["optional_pooled_f32"],
        },
        {
            "condition": "optional_pooled_f32 is present",
            "consumes": ["optional_pooled_f32"],
            "depends_on": [1],
            "produces": ["optional_pooled_bf16"],
        },
        {
            "condition": "always; payload rows are present exactly at ratio boundaries",
            "consumes": [
                "prior_compressed_state",
                "candidate_raw_state",
                "optional_pooled_bf16",
                "session_ids",
                "start_pos",
            ],
            "depends_on": [0, 2],
            "produces": ["candidate_compressed_state"],
        },
        {
            "condition": "always",
            "consumes": ["candidate_compressed_state", "session_ids"],
            "depends_on": [3],
            "produces": ["valid_prefix_view"],
        },
        {
            "condition": "all preceding slots succeeded and atomic publication succeeds",
            "consumes": [
                "candidate_raw_state",
                "candidate_compressed_state",
                "valid_prefix_view",
            ],
            "depends_on": [0, 1, 2, 3, 4],
            "produces": ["published_state_version", "execution_report"],
        },
    )
    slots: list[dict[str, Any]] = []
    for index, (instruction, contract) in enumerate(
        zip(program, slot_contracts, strict=True)
    ):
        slots.append(
            {
                "condition": contract["condition"],
                "consumes": contract["consumes"],
                "depends_on": contract["depends_on"],
                "logical_slot": index,
                "opcode": instruction.opcode.name,
                "produces": contract["produces"],
            }
        )
    return {
        "ape_sha256": ape_sha256,
        "claim_boundary": (
            "Instruction order, conditional payload causality, immutable-state "
            "commit order, and artifact identity only."
        ),
        "model_id": MODEL_ID,
        "nonclaims": list(NONCLAIMS),
        "program_sha256": PROGRAM_SHA256,
        "schema": SCHEDULE_SCHEMA,
        "slots": slots,
        "status": SCHEDULE_STATUS,
    }


def verify_logical_schedule(value: object, *, ape_sha256: str) -> None:
    expected = build_logical_schedule(ape_sha256=ape_sha256)
    if type(value) is not dict or canonical_json_bytes(value) != canonical_json_bytes(
        expected
    ):
        raise DeepSeekV4CompressorScheduleError("logical schedule differs")


def build_logical_schedule_certificate(
    schedule: object,
    *,
    ape_sha256: str,
) -> dict[str, Any]:
    verify_logical_schedule(schedule, ape_sha256=ape_sha256)
    return {
        "ape_sha256": ape_sha256,
        "checks": [
            "exact fixed micro-op order",
            "every dependency targets a lower-numbered logical slot",
            "pool and conversion payloads are conditional on compression readiness",
            "compressed commit follows raw candidate and conditional conversion",
            "valid view follows compressed candidate",
            "COMPLETE depends on every semantic slot and atomic publication",
        ],
        "model_id": MODEL_ID,
        "nonclaims": list(NONCLAIMS),
        "program_sha256": PROGRAM_SHA256,
        "schedule_sha256": _sha256(schedule),
        "schema": CERTIFICATE_SCHEMA,
        "status": SCHEDULE_STATUS,
    }


def verify_logical_schedule_certificate(
    value: object,
    schedule: object,
    *,
    ape_sha256: str,
) -> None:
    expected = build_logical_schedule_certificate(
        schedule,
        ape_sha256=ape_sha256,
    )
    if type(value) is not dict or canonical_json_bytes(value) != canonical_json_bytes(
        expected
    ):
        raise DeepSeekV4CompressorScheduleError("logical schedule certificate differs")


__all__ = [
    "CERTIFICATE_SCHEMA",
    "DeepSeekV4CompressorScheduleError",
    "NONCLAIMS",
    "SCHEDULE_SCHEMA",
    "SCHEDULE_STATUS",
    "build_logical_schedule",
    "build_logical_schedule_certificate",
    "verify_logical_schedule",
    "verify_logical_schedule_certificate",
]
