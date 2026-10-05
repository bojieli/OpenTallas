"""Independent scalar Qwen GQA and transactional-KV oracle.

The module imports no compiler, simulator, array package, framework, or model
implementation.  Inputs and outputs are architectural BF16 encodings.  It
defines the numeric behavior of ``qwen3_gqa_fp32_softmax_bf16_v1`` and the
byte-preserving prepare/commit behavior consumed by that operation.

Tensor order is ``[sequence][head][head_dimension]``.  A prepared transaction
appends a contiguous sequence at the committed length.  Query token ``i`` may
read every committed token and prepared tokens through ``i``; later prepared
tokens receive the pinned finite BF16 causal-mask value before FP32 softmax.
"""

from __future__ import annotations

from collections.abc import Sequence
import math
import struct

from dataclasses import dataclass
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_exp_nonpositive,
    binary32_lanes8_sum,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
)


NUMERIC_CONTRACT = "qwen3_gqa_fp32_softmax_bf16_v1"
STATE_CONTRACT = "bf16_byte_preserving_state_v1"
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
QUERY_HEADS_PER_KV_HEAD = QUERY_HEADS // KEY_VALUE_HEADS


@dataclass(frozen=True)
class AttentionGeometry:
    """One attention shape this reference is characterised for.

    The module constants above are Qwen3-8B's and remain the default
    everywhere, so every existing caller is unchanged.  This type exists
    because rung G1f runs a reduced regression model -- 8 query heads, 2 KV
    heads, 16-element heads -- and the reference could not express it: it
    hardcoded 32/8/128 and refused any row that was not 128 wide, so there was
    no oracle a reduced attention could be checked against.

    ``scale_code`` is DERIVED, not supplied.  It is bf16(1/sqrt(head_dim)), and
    getting it wrong is silent: at 128 it is 0x3db5 and at 16 it is 0x3e80
    (0.25, which unlike 1/sqrt(128) is exact in BF16).  Making it a field a
    caller could set independently of ``head_dim`` would allow a geometry whose
    scale does not match its own head width.
    """

    query_heads: int
    kv_heads: int
    head_dim: int

    def __post_init__(self) -> None:
        for name in ("query_heads", "kv_heads", "head_dim"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise AttentionReferenceError(f"{name} must be a positive integer")
        if self.query_heads % self.kv_heads:
            raise AttentionReferenceError(
                "query heads must be divisible by KV heads"
            )

    @property
    def query_heads_per_kv_head(self) -> int:
        return self.query_heads // self.kv_heads

    @property
    def scale_code(self) -> int:
        """bf16(1 / sqrt(head_dim)), as a BF16 code."""

        scale = 1.0 / math.sqrt(self.head_dim)
        return (struct.unpack("<I", struct.pack("<f", scale))[0] >> 16) & 0xFFFF


MAX_CONTEXT_TOKENS = 8192
SCALE_BF16_CODE = 0x3DB5
CAUSAL_MASK_BF16_CODE = 0xFF7F

QWEN3_8B_GEOMETRY = AttentionGeometry(
    query_heads=QUERY_HEADS,
    kv_heads=KEY_VALUE_HEADS,
    head_dim=HEAD_DIM,
)

QWEN3_REDUCED_GEOMETRY = AttentionGeometry(query_heads=8, kv_heads=2, head_dim=16)

if QWEN3_8B_GEOMETRY.scale_code != SCALE_BF16_CODE:
    raise AssertionError(
        "the derived Qwen3-8B attention scale does not reproduce SCALE_BF16_CODE"
    )

BF16Vector: TypeAlias = tuple[int, ...]
BF16Heads: TypeAlias = tuple[BF16Vector, ...]
BF16Sequence: TypeAlias = tuple[BF16Heads, ...]


class AttentionReferenceError(ValueError):
    """Raised when attention data, arithmetic, or state is illegal."""


@dataclass(frozen=True)
class KVSnapshotReference:
    """One immutable committed KV generation."""

    resource_id: str
    generation: int
    capacity: int
    key_values: BF16Sequence
    value_values: BF16Sequence
    geometry: "AttentionGeometry" = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.geometry is None:
            object.__setattr__(self, "geometry", QWEN3_8B_GEOMETRY)

    @property
    def length(self) -> int:
        return len(self.key_values)


@dataclass(frozen=True)
class PreparedKVReference:
    """Nonarchitectural append visible only to its active transaction."""

    resource_id: str
    transaction_id: int
    base_generation: int
    position_start: int
    key_values: BF16Sequence
    value_values: BF16Sequence
    geometry: "AttentionGeometry" = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.geometry is None:
            object.__setattr__(self, "geometry", QWEN3_8B_GEOMETRY)

    @property
    def length(self) -> int:
        return len(self.key_values)


@dataclass(frozen=True)
class AttentionReferenceAccounting:
    """Executed arithmetic counts for one attention invocation."""

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
class AttentionReferenceResult:
    """Exact attention payloads, sticky status, and accounting."""

    accounting: AttentionReferenceAccounting
    mask_saturated_element_count: int
    output_saturated_element_count: int
    probability_saturated_element_count: int
    scaling_saturated_element_count: int
    score_saturated_element_count: int
    output_values: BF16Sequence
    probability_values: BF16Sequence
    scaled_score_values: BF16Sequence


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AttentionReferenceError(f"{label} must be a sequence")
    return value


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
        raise AttentionReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _resource_id(value: object) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise AttentionReferenceError("resource_id must be a nonempty canonical string")
    return value


def _finite_bf16(value: object, label: str) -> int:
    code = _bounded_integer(value, label, minimum=0, maximum=0xFFFF)
    if not decode_bf16(code).finite:
        raise AttentionReferenceError(f"{label} must be finite BF16")
    return code


def _tensor3(
    value: object,
    label: str,
    *,
    heads: int,
    allow_empty: bool,
    head_dim: int = HEAD_DIM,
) -> BF16Sequence:
    raw_tokens = _sequence(value, label)
    if not raw_tokens and not allow_empty:
        raise AttentionReferenceError(f"{label} must contain at least one token")
    tokens: list[BF16Heads] = []
    for token_index, raw_heads in enumerate(raw_tokens):
        head_rows = _sequence(raw_heads, f"{label}[{token_index}]")
        if len(head_rows) != heads:
            raise AttentionReferenceError(
                f"{label}[{token_index}] must contain exactly {heads} heads"
            )
        parsed_heads: list[BF16Vector] = []
        for head_index, raw_row in enumerate(head_rows):
            row = _sequence(raw_row, f"{label}[{token_index}][{head_index}]")
            if len(row) != head_dim:
                raise AttentionReferenceError(
                    f"{label}[{token_index}][{head_index}] must contain "
                    f"exactly {head_dim} elements"
                )
            parsed_heads.append(
                tuple(
                    _finite_bf16(
                        code,
                        f"{label}[{token_index}][{head_index}][{element_index}]",
                    )
                    for element_index, code in enumerate(row)
                )
            )
        tokens.append(tuple(parsed_heads))
    return tuple(tokens)


def make_kv_snapshot(
    *,
    resource_id: str,
    generation: int,
    capacity: int,
    key_values: Sequence[Sequence[Sequence[int]]],
    value_values: Sequence[Sequence[Sequence[int]]],
    geometry: AttentionGeometry = QWEN3_8B_GEOMETRY,
) -> KVSnapshotReference:
    """Validate and construct one immutable committed snapshot."""

    resource = _resource_id(resource_id)
    parsed_generation = _bounded_integer(
        generation, "generation", minimum=0, maximum=(1 << 64) - 1
    )
    parsed_capacity = _bounded_integer(
        capacity, "capacity", minimum=1, maximum=MAX_CONTEXT_TOKENS
    )
    keys = _tensor3(
        key_values,
        "key_values",
        heads=geometry.kv_heads,
        allow_empty=True,
        head_dim=geometry.head_dim,
    )
    values = _tensor3(
        value_values,
        "value_values",
        heads=geometry.kv_heads,
        allow_empty=True,
        head_dim=geometry.head_dim,
    )
    if len(keys) != len(values):
        raise AttentionReferenceError("committed key/value lengths differ")
    if len(keys) > parsed_capacity:
        raise AttentionReferenceError("committed KV length exceeds capacity")
    return KVSnapshotReference(
        resource,
        parsed_generation,
        parsed_capacity,
        keys,
        values,
        geometry,
    )


def empty_kv_snapshot(
    resource_id: str,
    *,
    capacity: int = MAX_CONTEXT_TOKENS,
    geometry: AttentionGeometry = QWEN3_8B_GEOMETRY,
) -> KVSnapshotReference:
    """Construct generation zero with no committed tokens."""

    return make_kv_snapshot(
        resource_id=resource_id,
        generation=0,
        capacity=capacity,
        key_values=(),
        value_values=(),
        geometry=geometry,
    )


def _validated_snapshot(snapshot: object) -> KVSnapshotReference:
    if not isinstance(snapshot, KVSnapshotReference):
        raise AttentionReferenceError("snapshot must be a KVSnapshotReference")
    return make_kv_snapshot(
        resource_id=snapshot.resource_id,
        generation=snapshot.generation,
        capacity=snapshot.capacity,
        key_values=snapshot.key_values,
        value_values=snapshot.value_values,
        # Forward the snapshot's OWN geometry.  Re-validating against the
        # default would silently reject every non-Qwen3-8B snapshot here, which
        # is exactly what it did before this line existed.
        geometry=snapshot.geometry,
    )


def prepare_kv_append(
    snapshot: KVSnapshotReference,
    *,
    transaction_id: int,
    expected_generation: int,
    position_start: int,
    key_values: Sequence[Sequence[Sequence[int]]],
    value_values: Sequence[Sequence[Sequence[int]]],
) -> PreparedKVReference:
    """Prepare a contiguous, byte-preserving append without publishing it."""

    committed = _validated_snapshot(snapshot)
    geometry = committed.geometry
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
        raise AttentionReferenceError("expected generation is stale")
    if start != committed.length:
        raise AttentionReferenceError(
            "prepared KV append must begin at the committed length"
        )
    keys = _tensor3(
        key_values,
        "prepared key_values",
        heads=geometry.kv_heads,
        allow_empty=False,
        head_dim=geometry.head_dim,
    )
    values = _tensor3(
        value_values,
        "prepared value_values",
        heads=geometry.kv_heads,
        allow_empty=False,
        head_dim=geometry.head_dim,
    )
    if len(keys) != len(values):
        raise AttentionReferenceError("prepared key/value lengths differ")
    if start + len(keys) > committed.capacity:
        raise AttentionReferenceError("prepared KV append exceeds capacity")
    return PreparedKVReference(
        committed.resource_id,
        transaction,
        committed.generation,
        start,
        keys,
        values,
        geometry,
    )


def _validated_pair(
    snapshot: object,
    prepared: object,
) -> tuple[KVSnapshotReference, PreparedKVReference]:
    committed = _validated_snapshot(snapshot)
    geometry = committed.geometry
    if not isinstance(prepared, PreparedKVReference):
        raise AttentionReferenceError("prepared state must be a PreparedKVReference")
    keys = _tensor3(
        prepared.key_values,
        "prepared key_values",
        heads=geometry.kv_heads,
        allow_empty=False,
        head_dim=geometry.head_dim,
    )
    values = _tensor3(
        prepared.value_values,
        "prepared value_values",
        heads=geometry.kv_heads,
        allow_empty=False,
        head_dim=geometry.head_dim,
    )
    canonical = PreparedKVReference(
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
        keys,
        values,
        geometry,
    )
    if canonical.resource_id != committed.resource_id:
        raise AttentionReferenceError("prepared resource differs from snapshot")
    if canonical.base_generation != committed.generation:
        raise AttentionReferenceError("prepared generation is stale")
    if canonical.position_start != committed.length:
        raise AttentionReferenceError("prepared position differs from committed length")
    if len(keys) != len(values) or committed.length + len(keys) > committed.capacity:
        raise AttentionReferenceError("prepared KV payload is inconsistent")
    return committed, canonical


def prepared_kv_values(
    snapshot: KVSnapshotReference,
    prepared: PreparedKVReference,
) -> tuple[BF16Sequence, BF16Sequence]:
    """Return the transaction-private committed-plus-prepared view."""

    committed, transaction = _validated_pair(snapshot, prepared)
    return (
        committed.key_values + transaction.key_values,
        committed.value_values + transaction.value_values,
    )


def commit_kv_group(
    pairs: Sequence[tuple[KVSnapshotReference, PreparedKVReference]],
) -> tuple[KVSnapshotReference, ...]:
    """Atomically publish one prepared generation for every supplied resource.

    Validation completes for the entire group before any successor snapshot is
    constructed.  All resources must belong to the same request transaction.
    """

    raw_pairs = _sequence(pairs, "pairs")
    if not raw_pairs:
        raise AttentionReferenceError("commit group must contain at least one resource")
    validated: list[tuple[KVSnapshotReference, PreparedKVReference]] = []
    resources: set[str] = set()
    transaction_id: int | None = None
    for index, raw_pair in enumerate(raw_pairs):
        pair = _sequence(raw_pair, f"pairs[{index}]")
        if len(pair) != 2:
            raise AttentionReferenceError(f"pairs[{index}] must contain two items")
        committed, prepared = _validated_pair(pair[0], pair[1])
        if committed.resource_id in resources:
            raise AttentionReferenceError("commit group contains a duplicate resource")
        resources.add(committed.resource_id)
        if transaction_id is None:
            transaction_id = prepared.transaction_id
        elif prepared.transaction_id != transaction_id:
            raise AttentionReferenceError(
                "commit group spans more than one transaction"
            )
        if committed.generation == (1 << 64) - 1:
            raise AttentionReferenceError("KV generation counter would overflow")
        validated.append((committed, prepared))

    return tuple(
        make_kv_snapshot(
            resource_id=committed.resource_id,
            generation=committed.generation + 1,
            capacity=committed.capacity,
            key_values=committed.key_values + prepared.key_values,
            value_values=committed.value_values + prepared.value_values,
        )
        for committed, prepared in validated
    )


def commit_kv_append(
    snapshot: KVSnapshotReference,
    prepared: PreparedKVReference,
) -> KVSnapshotReference:
    """Publish one prepared resource with the group-commit semantics."""

    return commit_kv_group(((snapshot, prepared),))[0]


def abort_kv_group(
    pairs: Sequence[tuple[KVSnapshotReference, PreparedKVReference]],
) -> tuple[KVSnapshotReference, ...]:
    """Validate and discard a transaction while preserving committed state."""

    raw_pairs = _sequence(pairs, "pairs")
    if not raw_pairs:
        raise AttentionReferenceError("abort group must contain at least one resource")
    validated: list[KVSnapshotReference] = []
    resources: set[str] = set()
    transaction_id: int | None = None
    for index, raw_pair in enumerate(raw_pairs):
        pair = _sequence(raw_pair, f"pairs[{index}]")
        if len(pair) != 2:
            raise AttentionReferenceError(f"pairs[{index}] must contain two items")
        committed, prepared = _validated_pair(pair[0], pair[1])
        if committed.resource_id in resources:
            raise AttentionReferenceError("abort group contains a duplicate resource")
        resources.add(committed.resource_id)
        if transaction_id is None:
            transaction_id = prepared.transaction_id
        elif prepared.transaction_id != transaction_id:
            raise AttentionReferenceError("abort group spans more than one transaction")
        validated.append(committed)
    return tuple(validated)


def _negate_binary32(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _maximum_binary32(codes: Sequence[int]) -> int:
    if not codes:
        raise AttentionReferenceError("softmax row must not be empty")
    maximum = codes[0]
    maximum_value = decode_binary32(maximum).value
    assert maximum_value is not None
    for code in codes[1:]:
        value = decode_binary32(code).value
        assert value is not None
        if value > maximum_value:
            maximum = code
            maximum_value = value
    return maximum


def gqa_causal_attention_bf16(
    query_codes: Sequence[Sequence[Sequence[int]]],
    snapshot: KVSnapshotReference,
    prepared: PreparedKVReference,
) -> AttentionReferenceResult:
    """Execute exact full-shape Qwen GQA against transaction-private KV state."""

    committed, transaction = _validated_pair(snapshot, prepared)
    geometry = committed.geometry
    queries = _tensor3(
        query_codes,
        "query_codes",
        heads=geometry.query_heads,
        allow_empty=False,
        head_dim=geometry.head_dim,
    )
    if len(queries) != transaction.length:
        raise AttentionReferenceError(
            "query span must match the prepared KV append length"
        )
    keys = committed.key_values + transaction.key_values
    values = committed.value_values + transaction.value_values
    total_tokens = len(keys)

    score_saturation = 0
    scaling_saturation = 0
    mask_saturation = 0
    probability_saturation = 0
    output_saturation = 0
    all_scaled_scores: list[BF16Heads] = []
    all_probabilities: list[BF16Heads] = []
    all_outputs: list[BF16Heads] = []

    try:
        for query_index, query_heads in enumerate(queries):
            visible_tokens = committed.length + query_index + 1
            token_scores: list[BF16Vector] = []
            token_probabilities: list[BF16Vector] = []
            token_outputs: list[BF16Vector] = []
            for query_head, query in enumerate(query_heads):
                kv_head = query_head // geometry.query_heads_per_kv_head
                masked_codes: list[int] = []
                scaled_codes: list[int] = []
                for key_index, key_token in enumerate(keys):
                    accumulator = 0
                    for left, right in zip(
                        query,
                        key_token[kv_head],
                        strict=True,
                    ):
                        product = binary32_multiply(left << 16, right << 16)
                        accumulator = binary32_add(accumulator, product)
                    score = binary32_bits_to_bf16_rne(accumulator)
                    score_saturation += int(score.saturated)
                    scaled_binary32 = binary32_multiply(
                        score.code << 16,
                        geometry.scale_code << 16,
                    )
                    scaled = binary32_bits_to_bf16_rne(scaled_binary32)
                    scaling_saturation += int(scaled.saturated)
                    mask_code = (
                        0 if key_index < visible_tokens else CAUSAL_MASK_BF16_CODE
                    )
                    masked_binary32 = binary32_add(
                        scaled.code << 16,
                        mask_code << 16,
                    )
                    masked = binary32_bits_to_bf16_rne(masked_binary32)
                    mask_saturation += int(masked.saturated)
                    scaled_codes.append(masked.code)
                    masked_codes.append(masked.code << 16)

                maximum = _maximum_binary32(masked_codes)
                exponentials = tuple(
                    binary32_exp_nonpositive(
                        binary32_add(code, _negate_binary32(maximum))
                    )
                    for code in masked_codes
                )
                denominator = binary32_lanes8_sum(exponentials)
                inverse = binary32_divide(0x3F800000, denominator)
                probability_row: list[int] = []
                for exponential in exponentials:
                    probability = binary32_bits_to_bf16_rne(
                        binary32_multiply(exponential, inverse)
                    )
                    probability_saturation += int(probability.saturated)
                    probability_row.append(probability.code)

                output_row: list[int] = []
                for element in range(geometry.head_dim):
                    accumulator = 0
                    for probability, value_token in zip(
                        probability_row,
                        values,
                        strict=True,
                    ):
                        product = binary32_multiply(
                            probability << 16,
                            value_token[kv_head][element] << 16,
                        )
                        accumulator = binary32_add(accumulator, product)
                    converted = binary32_bits_to_bf16_rne(accumulator)
                    output_saturation += int(converted.saturated)
                    output_row.append(converted.code)

                token_scores.append(tuple(scaled_codes))
                token_probabilities.append(tuple(probability_row))
                token_outputs.append(tuple(output_row))
            all_scaled_scores.append(tuple(token_scores))
            all_probabilities.append(tuple(token_probabilities))
            all_outputs.append(tuple(token_outputs))
    except NumericReferenceError as exc:
        raise AttentionReferenceError(f"attention arithmetic failed: {exc}") from exc

    rows = len(queries) * geometry.query_heads
    score_elements = rows * total_tokens
    value_elements = score_elements * geometry.head_dim
    accounting = AttentionReferenceAccounting(
        exponential_evaluations=score_elements,
        mask_additions=score_elements,
        probability_multiplications=score_elements,
        scaling_multiplications=score_elements,
        score_accumulation_additions=score_elements * geometry.head_dim,
        score_multiplications=score_elements * geometry.head_dim,
        softmax_reduction_additions=rows * (total_tokens - 1),
        softmax_reciprocal_divisions=rows,
        value_accumulation_additions=value_elements,
        value_multiplications=value_elements,
    )
    return AttentionReferenceResult(
        accounting,
        mask_saturation,
        output_saturation,
        probability_saturation,
        scaling_saturation,
        score_saturation,
        tuple(all_outputs),
        tuple(all_probabilities),
        tuple(all_scaled_scores),
    )


__all__ = [
    "AttentionReferenceAccounting",
    "AttentionReferenceError",
    "AttentionReferenceResult",
    "BF16Heads",
    "BF16Sequence",
    "BF16Vector",
    "CAUSAL_MASK_BF16_CODE",
    "AttentionGeometry",
    "QWEN3_8B_GEOMETRY",
    "QWEN3_REDUCED_GEOMETRY",
    "HEAD_DIM",
    "KEY_VALUE_HEADS",
    "KVSnapshotReference",
    "MAX_CONTEXT_TOKENS",
    "NUMERIC_CONTRACT",
    "PreparedKVReference",
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
