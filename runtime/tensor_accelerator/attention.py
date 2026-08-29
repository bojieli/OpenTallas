"""Optimized data-bearing Qwen GQA and transactional-KV implementation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .bf16 import BF16KernelError, dense_bf16_linear_bf16


NUMERIC_CONTRACT = "qwen3_gqa_fp32_softmax_bf16_v1"
STATE_CONTRACT = "bf16_byte_preserving_state_v1"
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
QUERY_HEADS_PER_KV_HEAD = QUERY_HEADS // KEY_VALUE_HEADS
MAX_CONTEXT_TOKENS = 8000
SCALE_BF16_CODE = 0x3DB5
CAUSAL_MASK_BF16_CODE = 0xFF7F


class AttentionKernelError(ValueError):
    """Raised when attention data, arithmetic, or state is illegal."""


@dataclass(frozen=True)
class KVSnapshot:
    """One immutable committed KV generation."""

    resource_id: str
    generation: int
    capacity: int
    key_values: np.ndarray[Any, np.dtype[np.uint16]]
    value_values: np.ndarray[Any, np.dtype[np.uint16]]

    @property
    def length(self) -> int:
        return int(self.key_values.shape[0])


@dataclass(frozen=True)
class PreparedKV:
    """Nonarchitectural append visible only to its active transaction."""

    resource_id: str
    transaction_id: int
    base_generation: int
    position_start: int
    key_values: np.ndarray[Any, np.dtype[np.uint16]]
    value_values: np.ndarray[Any, np.dtype[np.uint16]]

    @property
    def length(self) -> int:
        return int(self.key_values.shape[0])


@dataclass(frozen=True)
class AttentionKernelAccounting:
    exponential_evaluations: int
    mask_additions: int
    probability_multiplications: int
    scaling_multiplications: int
    score_accumulation_additions: int
    score_multiplications: int
    softmax_reduction_additions: int
    softmax_reciprocal_divisions: int
    value_accumulation_additions: int
    value_multiplications: int


@dataclass(frozen=True)
class AttentionKernelResult:
    accounting: AttentionKernelAccounting
    mask_saturated_element_count: int
    output_saturated_element_count: int
    probability_saturated_element_count: int
    scaling_saturated_element_count: int
    score_saturated_element_count: int
    output_values: np.ndarray[Any, np.dtype[np.uint16]]
    probability_values: np.ndarray[Any, np.dtype[np.uint16]]
    scaled_score_values: np.ndarray[Any, np.dtype[np.uint16]]


def _bounded_integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise AttentionKernelError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _resource_id(value: object) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise AttentionKernelError("resource_id must be a nonempty canonical string")
    return value


def _codes3(
    value: object,
    label: str,
    *,
    heads: int,
    allow_empty: bool,
) -> np.ndarray[Any, np.dtype[np.uint16]]:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise AttentionKernelError(f"{label} must be a rank-3 BF16 tensor") from exc
    if raw.size == 0:
        if not allow_empty:
            raise AttentionKernelError(f"{label} must contain at least one token")
        return np.empty((0, heads, HEAD_DIM), dtype=np.uint16)
    if raw.ndim != 3 or raw.shape[1:] != (heads, HEAD_DIM):
        raise AttentionKernelError(
            f"{label} must have shape [tokens, {heads}, {HEAD_DIM}]"
        )
    if raw.dtype.kind not in {"i", "u"}:
        raise AttentionKernelError(f"{label} must contain integer BF16 encodings")
    if np.any(raw < 0) or np.any(raw > 0xFFFF):
        raise AttentionKernelError(f"{label} contains a value outside 16-bit BF16")
    codes = np.ascontiguousarray(raw, dtype=np.uint16)
    if np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise AttentionKernelError(f"{label} contains BF16 NaN or infinity")
    return codes


def _immutable(
    values: np.ndarray[Any, np.dtype[np.uint16]],
) -> np.ndarray[Any, np.dtype[np.uint16]]:
    result = np.ascontiguousarray(values, dtype=np.uint16).copy()
    result.setflags(write=False)
    return result


def _decode(
    codes: np.ndarray[Any, np.dtype[np.uint16]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    return np.ascontiguousarray(codes.astype(np.uint32) << np.uint32(16)).view(
        np.float32
    )


def _encode(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], int]:
    finite = np.ascontiguousarray(values, dtype=np.float32)
    if not np.all(np.isfinite(finite)):
        raise AttentionKernelError(
            "attention binary32 arithmetic produced NaN or infinity"
        )
    bits = finite.view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    rounded = upper + increment.astype(np.uint32)
    saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
    count = int(np.count_nonzero(saturated))
    rounded = np.where(
        saturated,
        (rounded & np.uint32(0x8000)) | np.uint32(0x7F7F),
        rounded,
    )
    rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, 0, rounded)
    return np.ascontiguousarray(rounded, dtype=np.uint16), count


def make_kv_snapshot(
    *,
    resource_id: str,
    generation: int,
    capacity: int,
    key_values: object,
    value_values: object,
) -> KVSnapshot:
    """Validate and construct one immutable committed snapshot."""

    resource = _resource_id(resource_id)
    parsed_generation = _bounded_integer(
        generation, "generation", minimum=0, maximum=(1 << 64) - 1
    )
    parsed_capacity = _bounded_integer(
        capacity, "capacity", minimum=1, maximum=MAX_CONTEXT_TOKENS
    )
    keys = _codes3(
        key_values,
        "key_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=True,
    )
    values = _codes3(
        value_values,
        "value_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=True,
    )
    if keys.shape != values.shape:
        raise AttentionKernelError("committed key/value shapes differ")
    if keys.shape[0] > parsed_capacity:
        raise AttentionKernelError("committed KV length exceeds capacity")
    return KVSnapshot(
        resource,
        parsed_generation,
        parsed_capacity,
        _immutable(keys),
        _immutable(values),
    )


def empty_kv_snapshot(
    resource_id: str,
    *,
    capacity: int = MAX_CONTEXT_TOKENS,
) -> KVSnapshot:
    return make_kv_snapshot(
        resource_id=resource_id,
        generation=0,
        capacity=capacity,
        key_values=(),
        value_values=(),
    )


def _validated_snapshot(snapshot: object) -> KVSnapshot:
    if not isinstance(snapshot, KVSnapshot):
        raise AttentionKernelError("snapshot must be a KVSnapshot")
    return make_kv_snapshot(
        resource_id=snapshot.resource_id,
        generation=snapshot.generation,
        capacity=snapshot.capacity,
        key_values=snapshot.key_values,
        value_values=snapshot.value_values,
    )


def prepare_kv_append(
    snapshot: KVSnapshot,
    *,
    transaction_id: int,
    expected_generation: int,
    position_start: int,
    key_values: object,
    value_values: object,
) -> PreparedKV:
    committed = _validated_snapshot(snapshot)
    transaction = _bounded_integer(
        transaction_id,
        "transaction_id",
        minimum=1,
        maximum=(1 << 64) - 1,
    )
    expected = _bounded_integer(
        expected_generation,
        "expected_generation",
        minimum=0,
        maximum=(1 << 64) - 1,
    )
    start = _bounded_integer(
        position_start,
        "position_start",
        minimum=0,
        maximum=committed.capacity - 1,
    )
    if expected != committed.generation:
        raise AttentionKernelError("expected generation is stale")
    if start != committed.length:
        raise AttentionKernelError(
            "prepared KV append must begin at the committed length"
        )
    keys = _codes3(
        key_values,
        "prepared key_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=False,
    )
    values = _codes3(
        value_values,
        "prepared value_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=False,
    )
    if keys.shape != values.shape:
        raise AttentionKernelError("prepared key/value shapes differ")
    if start + keys.shape[0] > committed.capacity:
        raise AttentionKernelError("prepared KV append exceeds capacity")
    return PreparedKV(
        committed.resource_id,
        transaction,
        committed.generation,
        start,
        _immutable(keys),
        _immutable(values),
    )


def _validated_pair(
    snapshot: object,
    prepared: object,
) -> tuple[KVSnapshot, PreparedKV]:
    committed = _validated_snapshot(snapshot)
    if not isinstance(prepared, PreparedKV):
        raise AttentionKernelError("prepared state must be a PreparedKV")
    keys = _codes3(
        prepared.key_values,
        "prepared key_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=False,
    )
    values = _codes3(
        prepared.value_values,
        "prepared value_values",
        heads=KEY_VALUE_HEADS,
        allow_empty=False,
    )
    canonical = PreparedKV(
        _resource_id(prepared.resource_id),
        _bounded_integer(
            prepared.transaction_id,
            "transaction_id",
            minimum=1,
            maximum=(1 << 64) - 1,
        ),
        _bounded_integer(
            prepared.base_generation,
            "base_generation",
            minimum=0,
            maximum=(1 << 64) - 1,
        ),
        _bounded_integer(
            prepared.position_start,
            "position_start",
            minimum=0,
            maximum=committed.capacity - 1,
        ),
        _immutable(keys),
        _immutable(values),
    )
    if canonical.resource_id != committed.resource_id:
        raise AttentionKernelError("prepared resource differs from snapshot")
    if canonical.base_generation != committed.generation:
        raise AttentionKernelError("prepared generation is stale")
    if canonical.position_start != committed.length:
        raise AttentionKernelError("prepared position differs from committed length")
    if (
        keys.shape != values.shape
        or committed.length + keys.shape[0] > committed.capacity
    ):
        raise AttentionKernelError("prepared KV payload is inconsistent")
    return committed, canonical


def prepared_kv_values(
    snapshot: KVSnapshot,
    prepared: PreparedKV,
) -> tuple[
    np.ndarray[Any, np.dtype[np.uint16]],
    np.ndarray[Any, np.dtype[np.uint16]],
]:
    committed, transaction = _validated_pair(snapshot, prepared)
    return (
        np.concatenate((committed.key_values, transaction.key_values), axis=0),
        np.concatenate((committed.value_values, transaction.value_values), axis=0),
    )


def commit_kv_group(
    pairs: Sequence[tuple[KVSnapshot, PreparedKV]],
) -> tuple[KVSnapshot, ...]:
    if isinstance(pairs, (str, bytes, bytearray)) or not isinstance(pairs, Sequence):
        raise AttentionKernelError("pairs must be a sequence")
    if not pairs:
        raise AttentionKernelError("commit group must contain at least one resource")
    validated: list[tuple[KVSnapshot, PreparedKV]] = []
    resources: set[str] = set()
    transaction_id: int | None = None
    for index, pair in enumerate(pairs):
        if not isinstance(pair, Sequence) or len(pair) != 2:
            raise AttentionKernelError(f"pairs[{index}] must contain two items")
        committed, prepared = _validated_pair(pair[0], pair[1])
        if committed.resource_id in resources:
            raise AttentionKernelError("commit group contains a duplicate resource")
        resources.add(committed.resource_id)
        if transaction_id is None:
            transaction_id = prepared.transaction_id
        elif prepared.transaction_id != transaction_id:
            raise AttentionKernelError("commit group spans more than one transaction")
        if committed.generation == (1 << 64) - 1:
            raise AttentionKernelError("KV generation counter would overflow")
        validated.append((committed, prepared))
    return tuple(
        make_kv_snapshot(
            resource_id=committed.resource_id,
            generation=committed.generation + 1,
            capacity=committed.capacity,
            key_values=np.concatenate(
                (committed.key_values, prepared.key_values), axis=0
            ),
            value_values=np.concatenate(
                (committed.value_values, prepared.value_values), axis=0
            ),
        )
        for committed, prepared in validated
    )


def commit_kv_append(snapshot: KVSnapshot, prepared: PreparedKV) -> KVSnapshot:
    return commit_kv_group(((snapshot, prepared),))[0]


def abort_kv_group(
    pairs: Sequence[tuple[KVSnapshot, PreparedKV]],
) -> tuple[KVSnapshot, ...]:
    if isinstance(pairs, (str, bytes, bytearray)) or not isinstance(pairs, Sequence):
        raise AttentionKernelError("pairs must be a sequence")
    if not pairs:
        raise AttentionKernelError("abort group must contain at least one resource")
    committed_states: list[KVSnapshot] = []
    resources: set[str] = set()
    transaction_id: int | None = None
    for index, pair in enumerate(pairs):
        if not isinstance(pair, Sequence) or len(pair) != 2:
            raise AttentionKernelError(f"pairs[{index}] must contain two items")
        committed, prepared = _validated_pair(pair[0], pair[1])
        if committed.resource_id in resources:
            raise AttentionKernelError("abort group contains a duplicate resource")
        resources.add(committed.resource_id)
        if transaction_id is None:
            transaction_id = prepared.transaction_id
        elif prepared.transaction_id != transaction_id:
            raise AttentionKernelError("abort group spans more than one transaction")
        committed_states.append(committed)
    return tuple(committed_states)


def _lanes8_sum(values: np.ndarray[Any, np.dtype[np.float32]]) -> np.float32:
    row = np.ascontiguousarray(values, dtype=np.float32)
    if row.ndim != 1 or row.size == 0 or not np.all(np.isfinite(row)):
        raise AttentionKernelError("softmax reduction row must be nonempty and finite")
    if row.size < 8:
        accumulator = row[0]
        for item in row[1:]:
            accumulator = np.add(accumulator, item, dtype=np.float32)
        return np.float32(accumulator)
    lanes = row[:8].copy()
    full = row.size - row.size % 8
    for start in range(8, full, 8):
        lanes = np.add(lanes, row[start : start + 8], dtype=np.float32)
    tail = row[full:]
    if tail.size:
        lanes[: tail.size] = np.add(lanes[: tail.size], tail, dtype=np.float32)
    half = np.add(lanes[:4], lanes[4:], dtype=np.float32)
    quarter = np.add(half[:2], half[2:], dtype=np.float32)
    return np.float32(np.add(quarter[0], quarter[1], dtype=np.float32))


def _exp_binary32_rne(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Evaluate exp with guard precision before architectural binary32 RNE.

    NumPy's float32 exponential is an optimized single-precision
    approximation, not a correctly rounded binary32 operation.  For example,
    it places ``exp(-1.0)`` one binary32 ulp below the value required by this
    target numeric contract.  Preserve the architectural binary32 input,
    evaluate it with binary64 guard precision, and round once on conversion
    to the architectural binary32 result.
    """

    binary32 = np.ascontiguousarray(values, dtype=np.float32)
    binary64 = np.asarray(binary32, dtype=np.float64)
    return np.ascontiguousarray(
        np.exp(binary64, dtype=np.float64).astype(np.float32),
        dtype=np.float32,
    )


def _softmax_bf16(
    masked_codes: np.ndarray[Any, np.dtype[np.uint16]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], int]:
    values = _decode(masked_codes)
    maximum = np.max(values)
    shifted = np.subtract(values, maximum, dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        exponentials = _exp_binary32_rne(shifted)
    finally:
        np.seterr(**previous)
    exponentials = np.where(
        shifted <= np.float32(-104.0), np.float32(0.0), exponentials
    ).astype(np.float32, copy=False)
    if not np.all(np.isfinite(exponentials)):
        raise AttentionKernelError("softmax exponential produced NaN or infinity")
    denominator = _lanes8_sum(exponentials)
    if not np.isfinite(denominator) or denominator <= 0:
        raise AttentionKernelError("softmax denominator is not positive finite")
    inverse = np.divide(np.float32(1.0), denominator, dtype=np.float32)
    probabilities = np.multiply(exponentials, inverse, dtype=np.float32)
    return _encode(probabilities)


def gqa_causal_attention_bf16(
    query_codes: object,
    snapshot: KVSnapshot,
    prepared: PreparedKV,
) -> AttentionKernelResult:
    """Execute full-shape Qwen GQA against transaction-private KV state."""

    committed, transaction = _validated_pair(snapshot, prepared)
    queries = _codes3(
        query_codes,
        "query_codes",
        heads=QUERY_HEADS,
        allow_empty=False,
    )
    if queries.shape[0] != transaction.length:
        raise AttentionKernelError(
            "query span must match the prepared KV append length"
        )
    keys = np.concatenate((committed.key_values, transaction.key_values), axis=0)
    values = np.concatenate((committed.value_values, transaction.value_values), axis=0)
    total_tokens = keys.shape[0]
    scores = np.empty((queries.shape[0], QUERY_HEADS, total_tokens), dtype=np.uint16)
    probabilities = np.empty_like(scores)
    outputs = np.empty((queries.shape[0], QUERY_HEADS, HEAD_DIM), dtype=np.uint16)
    score_saturation = 0
    scaling_saturation = 0
    mask_saturation = 0
    probability_saturation = 0
    output_saturation = 0

    try:
        scale = _decode(np.asarray([SCALE_BF16_CODE], dtype=np.uint16))[0]
        for query_index in range(queries.shape[0]):
            visible_tokens = committed.length + query_index + 1
            for query_head in range(QUERY_HEADS):
                kv_head = query_head // QUERY_HEADS_PER_KV_HEAD
                score_result = dense_bf16_linear_bf16(
                    queries[query_index, query_head][None, :],
                    keys[:, kv_head, :],
                    input_tile_rows=1,
                    output_tile_rows=64,
                )
                score_saturation += score_result.output_saturated_element_count
                scaled_values = np.multiply(
                    _decode(score_result.values[0]), scale, dtype=np.float32
                )
                scaled_codes, scaled_count = _encode(scaled_values)
                scaling_saturation += scaled_count
                mask_codes = np.zeros(total_tokens, dtype=np.uint16)
                mask_codes[visible_tokens:] = np.uint16(CAUSAL_MASK_BF16_CODE)
                masked_values = np.add(
                    _decode(scaled_codes),
                    _decode(mask_codes),
                    dtype=np.float32,
                )
                masked_codes, masked_count = _encode(masked_values)
                mask_saturation += masked_count
                probability_codes, probability_count = _softmax_bf16(masked_codes)
                probability_saturation += probability_count
                output_result = dense_bf16_linear_bf16(
                    probability_codes[None, :],
                    values[:, kv_head, :].T,
                    input_tile_rows=1,
                    output_tile_rows=HEAD_DIM,
                )
                output_saturation += output_result.output_saturated_element_count
                scores[query_index, query_head] = masked_codes
                probabilities[query_index, query_head] = probability_codes
                outputs[query_index, query_head] = output_result.values[0]
    except BF16KernelError as exc:
        raise AttentionKernelError(
            f"attention matrix arithmetic failed: {exc}"
        ) from exc

    rows = queries.shape[0] * QUERY_HEADS
    score_elements = rows * total_tokens
    value_elements = score_elements * HEAD_DIM
    accounting = AttentionKernelAccounting(
        exponential_evaluations=score_elements,
        mask_additions=score_elements,
        probability_multiplications=score_elements,
        scaling_multiplications=score_elements,
        score_accumulation_additions=score_elements * HEAD_DIM,
        score_multiplications=score_elements * HEAD_DIM,
        softmax_reduction_additions=rows * (total_tokens - 1),
        softmax_reciprocal_divisions=rows,
        value_accumulation_additions=value_elements,
        value_multiplications=value_elements,
    )
    return AttentionKernelResult(
        accounting,
        mask_saturation,
        output_saturation,
        probability_saturation,
        scaling_saturation,
        score_saturation,
        np.ascontiguousarray(outputs),
        np.ascontiguousarray(probabilities),
        np.ascontiguousarray(scores),
    )


__all__ = [
    "AttentionKernelAccounting",
    "AttentionKernelError",
    "AttentionKernelResult",
    "CAUSAL_MASK_BF16_CODE",
    "HEAD_DIM",
    "KEY_VALUE_HEADS",
    "KVSnapshot",
    "MAX_CONTEXT_TOKENS",
    "NUMERIC_CONTRACT",
    "PreparedKV",
    "QUERY_HEADS",
    "QUERY_HEADS_PER_KV_HEAD",
    "SCALE_BF16_CODE",
    "STATE_CONTRACT",
    "abort_kv_group",
    "commit_kv_append",
    "commit_kv_group",
    "empty_kv_snapshot",
    "gqa_causal_attention_bf16",
    "make_kv_snapshot",
    "prepare_kv_append",
    "prepared_kv_values",
]
