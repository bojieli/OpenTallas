from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import struct

import pytest

from runtime.reference.grouped_output import (
    OFFICIAL_GROUP_INPUT_FEATURES,
    OFFICIAL_HEADS_PER_GROUP,
    OFFICIAL_HEAD_DIM,
    OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256,
    OFFICIAL_OUTPUT_RANK,
    grouped_output_project_selected_bf16,
)
from runtime.service_engine.grouped_output_numeric import (
    execute_grouped_output_project_selected_bf16,
)


_EVIDENCE_ROOT_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"
_SELECTED_OUTPUT_RANKS = (0, OFFICIAL_OUTPUT_RANK - 1)
_EVIDENCE_SHA256 = "7966492eeeed82bfd9b8cc7555bef3c31f3c4ec65079e235379ddc957906aaed"


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _flatten_codes(value: object):
    if type(value) is int:
        yield value
        return
    assert type(value) is tuple
    for item in value:
        yield from _flatten_codes(item)


def _code_sha256(value: object) -> str:
    payload = b"".join(code.to_bytes(2, "little") for code in _flatten_codes(value))
    return hashlib.sha256(payload).hexdigest()


def _canonical_weight_payloads(root: Path) -> tuple[bytes, ...]:
    payloads = []
    for rank, expected_sha256 in enumerate(OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256):
        path = root / f"ranks/rank-{rank:03d}/layers.0.attn.wo_a.weight.bin"
        if not path.is_file():
            pytest.skip(f"canonical grouped-output weight is unavailable: {path}")
        payload = path.read_bytes()
        assert len(payload) == 2_048 * OFFICIAL_GROUP_INPUT_FEATURES * 2
        assert hashlib.sha256(payload).hexdigest() == expected_sha256
        payloads.append(payload)
    return tuple(payloads)


def _selected_weights(
    payloads: tuple[bytes, ...],
    global_groups: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    rows = []
    row_bytes = OFFICIAL_GROUP_INPUT_FEATURES * 2
    for global_group in global_groups:
        assignment_rank = global_group // 2
        assignment_group = global_group % 2
        payload = payloads[assignment_rank]
        for output_rank in _SELECTED_OUTPUT_RANKS:
            local_row = assignment_group * OFFICIAL_OUTPUT_RANK + output_rank
            rows.append(
                struct.unpack_from(
                    f"<{OFFICIAL_GROUP_INPUT_FEATURES}H",
                    payload,
                    local_row * row_bytes,
                )
            )
    return tuple(rows)


def _attention(
    global_groups: tuple[int, ...],
    token_count: int,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    positions = (0, 1, 63, 64, 127, 128, 255, 256, 511)
    palette = (
        0x0001,
        0x8001,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    tokens = []
    for token in range(token_count):
        heads = []
        for global_group in global_groups:
            for head in range(OFFICIAL_HEADS_PER_GROUP):
                row = [0] * OFFICIAL_HEAD_DIM
                for slot, column in enumerate(positions):
                    row[column] = palette[
                        (token * 7 + global_group * 5 + head * 3 + slot) % len(palette)
                    ]
                heads.append(tuple(row))
        tokens.append(tuple(heads))
    return (tuple(tokens),)


def _assert_counter_reconciliation(reference, service) -> None:
    counters = reference.counters
    logical = service.logical_counters
    token_count = counters.batch_count * counters.sequence_length
    assert logical == {
        "complete_events": counters.transaction_commits,
        "grouped_output_attention_bf16_values": (
            counters.attention_input_bf16_values
        ),
        "grouped_output_attention_group_view_values": (
            counters.attention_group_reshape_values
        ),
        "grouped_output_binary32_accumulation_roundings": (
            counters.binary32_accumulation_roundings
        ),
        "grouped_output_canonical_weight_bf16_values": (
            counters.canonical_weight_bf16_values
        ),
        "grouped_output_declared_full_output_bf16_values": (
            token_count * counters.local_group_count * OFFICIAL_OUTPUT_RANK
        ),
        "grouped_output_evaluated_output_ranks_per_group": (
            counters.evaluated_output_ranks_per_group
        ),
        "grouped_output_exact_product_accumulates": (
            counters.exact_product_accumulates
        ),
        "grouped_output_flattened_output_bf16_values": (
            counters.evaluated_flattened_output_bf16_values
        ),
        "grouped_output_group_input_features": counters.group_input_features,
        "grouped_output_grouped_output_bf16_values": (
            counters.evaluated_grouped_output_bf16_values
        ),
        "grouped_output_local_group_count": counters.local_group_count,
        "grouped_output_local_head_count": counters.local_head_count,
        "grouped_output_output_bf16_conversions": counters.output_bf16_conversions,
        "grouped_output_output_bf16_saturations": (
            counters.output_bf16_saturated_values
        ),
        "grouped_output_token_count": token_count,
        "grouped_output_weight_group_view_values": (
            counters.weight_group_reshape_values
        ),
        "semantic_operators_executed": 1,
        "tensor_parallel_world_size": counters.tensor_parallel_world_size,
    }


def _record(
    payloads: tuple[bytes, ...],
    *,
    world_size: int,
    rank: int,
    token_count: int,
) -> dict[str, object]:
    local_group_count = 8 // world_size
    global_groups = tuple(
        range(rank * local_group_count, (rank + 1) * local_group_count)
    )
    attention = _attention(global_groups, token_count)
    weights = _selected_weights(payloads, global_groups)
    reference = grouped_output_project_selected_bf16(
        attention,
        weights,
        local_group_count=local_group_count,
        declared_output_rank=OFFICIAL_OUTPUT_RANK,
        selected_output_ranks=_SELECTED_OUTPUT_RANKS,
        tensor_parallel_rank=rank,
    )
    service = execute_grouped_output_project_selected_bf16(
        attention,
        weights,
        tensor_parallel_world_size=world_size,
        tensor_parallel_rank=rank,
        selected_output_ranks=_SELECTED_OUTPUT_RANKS,
    )
    assert reference.global_group_indices == service.global_group_indices
    assert reference.selected_output_ranks == service.selected_output_ranks
    assert reference.complete_output == service.complete_output is False
    assert reference.grouped_bf16_codes == service.grouped_bf16_codes
    assert reference.flattened_bf16_codes == service.flattened_bf16_codes
    assert (
        reference.counters.output_bf16_saturated_values
        == service.output_saturation_count
    )
    _assert_counter_reconciliation(reference, service)
    record = {
        "attention_sha256": _code_sha256(attention),
        "global_groups": list(global_groups),
        "grouped_output_sha256": _code_sha256(reference.grouped_bf16_codes),
        "rank": rank,
        "reference_counters_sha256": hashlib.sha256(
            _canonical_bytes(asdict(reference.counters))
        ).hexdigest(),
        "saturation_count": service.output_saturation_count,
        "service_counters_sha256": hashlib.sha256(
            _canonical_bytes(dict(service.logical_counters))
        ).hexdigest(),
        "token_count": token_count,
        "weight_sha256": _code_sha256(weights),
        "world_size": world_size,
    }
    record["record_sha256"] = hashlib.sha256(_canonical_bytes(record)).hexdigest()
    return record


def _evidence_body() -> dict[str, object]:
    root = Path(
        os.environ.get(
            _EVIDENCE_ROOT_ENV,
            "/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731",
        )
    ) / "canonical-mp4"
    payloads = _canonical_weight_payloads(root)
    records = [
        _record(payloads, world_size=world_size, rank=rank, token_count=1)
        for world_size in (1, 2, 4, 8)
        for rank in range(world_size)
    ]
    records.extend(
        _record(payloads, world_size=4, rank=0, token_count=token_count)
        for token_count in range(2, 5)
    )
    return {
        "canonical_mp4_assignment_sha256": list(
            OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256
        ),
        "records": records,
        "selected_output_ranks": list(_SELECTED_OUTPUT_RANKS),
        "status": "exact_reference_service_match",
    }


def test_official_weight_reference_service_differential() -> None:
    body = _evidence_body()
    assert len(body["records"]) == 18  # type: ignore[arg-type]
    assert hashlib.sha256(_canonical_bytes(body)).hexdigest() == _EVIDENCE_SHA256
