"""Deterministic DeepSeek V4 grouped attention-output projection.

The implementation is pinned to ``deepseek-ai/DeepSeek-V4-Flash-0731`` at
revision ``7872f01b1d1fe23eabc4c98b48bffcef5a386062``.  The official
``Attention.forward`` executes the following source-visible steps after sparse
attention and inverse RoPE::

    o = o.view(bsz, seqlen, n_local_groups, -1)
    wo_a = self.wo_a.weight.view(n_local_groups, o_lora_rank, -1)
    o = torch.einsum("bsgd,grd->bsgr", o, wo_a)
    x = self.wo_b(o.flatten(2))

Sparse attention emits BF16.  ``convert.py`` slices each raw FP8/E8M0
``wo_a`` pair on output axis zero, dequantizes it, rounds it to BF16, and saves
that BF16 runtime parameter.  This operator therefore consumes BF16 input and
canonical BF16 weight encodings; raw checkpoint conversion is a separate
upstream contract.

The source fixes orientation and dtype but not a cross-backend tensor-core
reduction tree.  The OpenTallas numeric profile freezes every group/rank dot as
exact BF16 products accumulated into positive binary32 zero in increasing
flattened group-feature order.  Each fused product-add has one binary32 RNE
rounding, and the completed finite accumulator converts once to BF16 RNE with
sticky finite saturation.  No host floating-point arithmetic participates.

The released shape is eight global groups, eight contiguous attention heads
per group, head dimension 512, group width 4,096, and output rank 1,024.  The
global weight is ``[8192,4096]`` and group-major flattening feeds an
``[B,S,8192]`` tensor to ``wo_b``.  Tensor parallelism may use 1, 2, 4, or 8
ranks: each rank owns a contiguous group interval and sees respectively 8, 4,
2, or 1 local groups.  Smaller head dimensions and ranks are admitted only as
bounded unit profiles; :attr:`GroupedOutputProjectResult.official_shape_profile`
distinguishes the exact released shape.

The selected-rank entry point retains full declared shape and reduction width
while evaluating explicit output-rank rows per group.  It is an audit slice,
not a complete operator execution.  Neither entry point claims inverse RoPE,
checkpoint dequantization, ``wo_b``, tensor-parallel all-reduce, compiler or
service-engine execution, schedules, cycles, traffic, energy, area, PPA, or
end-to-end model correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_bits_to_bf16_rne,
    binary32_ordered_dot,
    decode_bf16,
)


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
CONVERT_SOURCE_PATH = "inference/convert.py"
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
CHECKPOINT_INDEX_SHA256 = (
    "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
)
CHECKPOINT_LOCK_ID = "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
GROUPED_OUTPUT_NUMERIC_PROFILE = "opentallas.deepseek_v4_grouped_output_bf16.v1"

OFFICIAL_SITE_COUNT = 46
OFFICIAL_MAIN_SITE_COUNT = 43
OFFICIAL_DSPARK_SITE_COUNT = 3
OFFICIAL_GLOBAL_GROUPS = 8
OFFICIAL_HEADS = 64
OFFICIAL_HEADS_PER_GROUP = 8
OFFICIAL_HEAD_DIM = 512
OFFICIAL_GROUP_INPUT_FEATURES = 4096
OFFICIAL_OUTPUT_RANK = 1024
OFFICIAL_GLOBAL_OUTPUT_FEATURES = 8192
OFFICIAL_WEIGHT_SHAPE = (
    OFFICIAL_GLOBAL_OUTPUT_FEATURES,
    OFFICIAL_GROUP_INPUT_FEATURES,
)
OFFICIAL_RAW_WEIGHT_DTYPE = "F8_E4M3"
OFFICIAL_RAW_SCALE_SHAPE = (64, 32)
OFFICIAL_RAW_SCALE_DTYPE = "F8_E8M0"
OFFICIAL_RUNTIME_WEIGHT_DTYPE = "BF16"
OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES = (1, 2, 4, 8)
OFFICIAL_LAYER0_RAW_WEIGHT_SHA256 = (
    "4ed730a5e64d2bf11cd13af4800473cf24ac1113744c0d1d5fdb8d438bded258"
)
OFFICIAL_LAYER0_RAW_SCALE_SHA256 = (
    "96416ed079e48da7b60aca5f5c020b4579124d07262bfc50082a414964a3f345"
)
OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256 = (
    "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b",
    "ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016",
    "d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc",
    "0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b",
)

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
BF16_MAX_ENCODING = (1 << 16) - 1

EXCLUDED_OPERATIONS = (
    "inverse_rotary_embedding",
    "raw_fp8_e8m0_checkpoint_dequantization",
    "output_b_projection",
    "tensor_parallel_collective",
    "compiler_lowering",
    "service_engine_execution",
    "schedule_cycles_traffic_energy_area_ppa",
    "end_to_end_model_execution",
)


BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadTensor: TypeAlias = tuple[BF16Vector, ...]
BF16SequenceTensor: TypeAlias = tuple[BF16HeadTensor, ...]
BF16AttentionTensor: TypeAlias = tuple[BF16SequenceTensor, ...]
BF16WeightMatrix: TypeAlias = tuple[BF16Vector, ...]
BF16GroupedOutput: TypeAlias = tuple[tuple[tuple[BF16Vector, ...], ...], ...]
BF16FlattenedOutput: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
BF16ValueVector: TypeAlias = tuple[Fraction, ...]
BF16ValueHeadTensor: TypeAlias = tuple[BF16ValueVector, ...]
BF16ValueSequenceTensor: TypeAlias = tuple[BF16ValueHeadTensor, ...]
BF16ValueAttentionTensor: TypeAlias = tuple[BF16ValueSequenceTensor, ...]
BF16ValueWeightMatrix: TypeAlias = tuple[BF16ValueVector, ...]


class GroupedOutputReferenceError(ValueError):
    """Raised when a grouped-output transaction is malformed or poisoned."""


@dataclass(frozen=True)
class GroupedOutputProjectCounters:
    """Exact logical shape and arithmetic counts for evaluated output rows."""

    batch_count: int
    sequence_length: int
    tensor_parallel_world_size: int
    tensor_parallel_rank: int
    local_group_count: int
    local_head_count: int
    heads_per_group: int
    head_dim: int
    group_input_features: int
    declared_output_rank: int
    evaluated_output_ranks_per_group: int
    complete_output: bool
    attention_input_bf16_values: int
    canonical_weight_bf16_values: int
    attention_group_reshape_values: int
    weight_group_reshape_values: int
    exact_product_accumulates: int
    binary32_accumulation_roundings: int
    output_bf16_conversions: int
    output_bf16_saturated_values: int
    evaluated_grouped_output_bf16_values: int
    evaluated_flattened_output_bf16_values: int
    declared_full_output_bf16_values: int
    transaction_commits: int


@dataclass(frozen=True)
class GroupedOutputProjectResult:
    """Immutable grouped and group-major flattened BF16 outputs."""

    numeric_profile: str
    tensor_parallel_world_size: int
    tensor_parallel_rank: int
    global_group_indices: tuple[int, ...]
    selected_output_ranks: tuple[int, ...]
    declared_output_rank: int
    complete_output: bool
    official_shape_profile: bool
    grouped_bf16_codes: BF16GroupedOutput
    flattened_bf16_codes: BF16FlattenedOutput
    counters: GroupedOutputProjectCounters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise GroupedOutputReferenceError(f"{label} must be an exact list or tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise GroupedOutputReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _local_group_count(value: object) -> int:
    if type(value) is not int or value not in {1, 2, 4, 8}:
        raise GroupedOutputReferenceError(
            "local_group_count must be exactly 1, 2, 4, or 8"
        )
    return value


def _finite_bf16(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise GroupedOutputReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise GroupedOutputReferenceError(f"{label} must be finite BF16")
    return value, decoded.value


def _freeze_attention(
    value: object,
    *,
    local_group_count: int,
) -> tuple[
    BF16AttentionTensor,
    BF16ValueAttentionTensor,
    int,
    int,
    int,
    int,
]:
    raw_batches = _sequence(value, "attention_bf16_codes")
    if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
        raise GroupedOutputReferenceError(
            f"attention_bf16_codes batch extent must be in [1, {PINNED_MAX_BATCH_SIZE}]"
        )

    expected_heads = local_group_count * OFFICIAL_HEADS_PER_GROUP
    frozen_batches: list[BF16SequenceTensor] = []
    value_batches: list[BF16ValueSequenceTensor] = []
    sequence_length: int | None = None
    head_dim: int | None = None
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(
            raw_sequence,
            f"attention_bf16_codes[{batch_index}]",
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if not 1 <= sequence_length <= PINNED_MAX_POSITION:
                raise GroupedOutputReferenceError(
                    "attention_bf16_codes sequence extent must be in "
                    f"[1, {PINNED_MAX_POSITION}]"
                )
        elif len(sequence) != sequence_length:
            raise GroupedOutputReferenceError(
                "attention_bf16_codes must be rectangular on the sequence axis"
            )

        frozen_sequence: list[BF16HeadTensor] = []
        value_sequence: list[BF16ValueHeadTensor] = []
        for position, raw_heads in enumerate(sequence):
            heads = _sequence(
                raw_heads,
                f"attention_bf16_codes[{batch_index}][{position}]",
            )
            if len(heads) != expected_heads:
                raise GroupedOutputReferenceError(
                    f"attention_bf16_codes[{batch_index}][{position}] must "
                    f"contain exactly {expected_heads} local heads"
                )

            frozen_heads: list[BF16Vector] = []
            value_heads: list[BF16ValueVector] = []
            for head, raw_row in enumerate(heads):
                row = _sequence(
                    raw_row,
                    f"attention_bf16_codes[{batch_index}][{position}][{head}]",
                )
                if head_dim is None:
                    head_dim = len(row)
                    if not 1 <= head_dim <= OFFICIAL_HEAD_DIM:
                        raise GroupedOutputReferenceError(
                            "attention head dimension must be in "
                            f"[1, {OFFICIAL_HEAD_DIM}]"
                        )
                elif len(row) != head_dim:
                    raise GroupedOutputReferenceError(
                        "attention_bf16_codes must be rectangular on the "
                        "head-dimension axis"
                    )

                frozen_row: list[int] = []
                value_row: list[Fraction] = []
                for column, code in enumerate(row):
                    frozen_code, decoded = _finite_bf16(
                        code,
                        "attention_bf16_codes"
                        f"[{batch_index}][{position}][{head}][{column}]",
                    )
                    frozen_row.append(frozen_code)
                    value_row.append(decoded)
                frozen_heads.append(tuple(frozen_row))
                value_heads.append(tuple(value_row))
            frozen_sequence.append(tuple(frozen_heads))
            value_sequence.append(tuple(value_heads))
        frozen_batches.append(tuple(frozen_sequence))
        value_batches.append(tuple(value_sequence))

    assert sequence_length is not None
    assert head_dim is not None
    return (
        tuple(frozen_batches),
        tuple(value_batches),
        len(frozen_batches),
        sequence_length,
        expected_heads,
        head_dim,
    )


def _selected_ranks(
    value: object,
    *,
    declared_output_rank: int,
) -> tuple[int, ...]:
    raw = _sequence(value, "selected_output_ranks")
    ranks = tuple(
        _integer(
            rank,
            f"selected_output_ranks[{index}]",
            minimum=0,
            maximum=declared_output_rank - 1,
        )
        for index, rank in enumerate(raw)
    )
    if not ranks:
        raise GroupedOutputReferenceError(
            "selected_output_ranks must contain at least one rank"
        )
    if ranks != tuple(sorted(set(ranks))):
        raise GroupedOutputReferenceError(
            "selected_output_ranks must be unique and strictly increasing"
        )
    return ranks


def _freeze_weights(
    value: object,
    *,
    local_group_count: int,
    rows_per_group: int,
    group_input_features: int,
) -> tuple[BF16WeightMatrix, BF16ValueWeightMatrix]:
    raw_rows = _sequence(value, "weight_bf16_codes")
    expected_rows = local_group_count * rows_per_group
    if len(raw_rows) != expected_rows:
        raise GroupedOutputReferenceError(
            f"weight_bf16_codes must contain exactly {expected_rows} group-major rows"
        )

    frozen_rows: list[BF16Vector] = []
    value_rows: list[BF16ValueVector] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"weight_bf16_codes[{row_index}]")
        if len(row) != group_input_features:
            raise GroupedOutputReferenceError(
                f"weight_bf16_codes[{row_index}] must contain exactly "
                f"{group_input_features} group-input features"
            )
        frozen_row: list[int] = []
        value_row: list[Fraction] = []
        for column, code in enumerate(row):
            frozen_code, decoded = _finite_bf16(
                code,
                f"weight_bf16_codes[{row_index}][{column}]",
            )
            frozen_row.append(frozen_code)
            value_row.append(decoded)
        frozen_rows.append(tuple(frozen_row))
        value_rows.append(tuple(value_row))
    return tuple(frozen_rows), tuple(value_rows)


def _reshape_attention_groups(
    attention: BF16ValueAttentionTensor,
    *,
    local_group_count: int,
) -> tuple[tuple[tuple[BF16ValueVector, ...], ...], ...]:
    grouped_batches = []
    for sequence in attention:
        grouped_sequence = []
        for heads in sequence:
            groups = []
            for group in range(local_group_count):
                head_start = group * OFFICIAL_HEADS_PER_GROUP
                groups.append(
                    tuple(
                        value
                        for head in heads[
                            head_start : head_start + OFFICIAL_HEADS_PER_GROUP
                        ]
                        for value in head
                    )
                )
            grouped_sequence.append(tuple(groups))
        grouped_batches.append(tuple(grouped_sequence))
    return tuple(grouped_batches)


def _project_validated(
    attention_values: BF16ValueAttentionTensor,
    weight_values: BF16ValueWeightMatrix,
    *,
    batch_count: int,
    sequence_length: int,
    local_group_count: int,
    head_dim: int,
    declared_output_rank: int,
    selected_output_ranks: tuple[int, ...],
    tensor_parallel_rank: int,
) -> GroupedOutputProjectResult:
    evaluated_rank_count = len(selected_output_ranks)
    group_input_features = OFFICIAL_HEADS_PER_GROUP * head_dim
    tensor_parallel_world_size = OFFICIAL_GLOBAL_GROUPS // local_group_count
    global_group_start = tensor_parallel_rank * local_group_count
    global_group_indices = tuple(
        range(global_group_start, global_group_start + local_group_count)
    )
    complete_output = selected_output_ranks == tuple(range(declared_output_rank))
    official_shape_profile = (
        head_dim == OFFICIAL_HEAD_DIM and declared_output_rank == OFFICIAL_OUTPUT_RANK
    )
    grouped_attention = _reshape_attention_groups(
        attention_values,
        local_group_count=local_group_count,
    )

    grouped_batches: list[tuple[tuple[BF16Vector, ...], ...]] = []
    flattened_batches: list[tuple[BF16Vector, ...]] = []
    saturation_count = 0
    try:
        for batch_index in range(batch_count):
            grouped_sequence: list[tuple[BF16Vector, ...]] = []
            flattened_sequence: list[BF16Vector] = []
            for position in range(sequence_length):
                output_groups: list[BF16Vector] = []
                for local_group in range(local_group_count):
                    input_row = grouped_attention[batch_index][position][local_group]
                    output_row: list[int] = []
                    weight_start = local_group * evaluated_rank_count
                    for selected_index, output_rank in enumerate(selected_output_ranks):
                        weight_row = weight_values[weight_start + selected_index]
                        try:
                            accumulator = binary32_ordered_dot(
                                input_row,
                                weight_row,
                            )
                            converted = binary32_bits_to_bf16_rne(accumulator)
                        except NumericReferenceError as exc:
                            raise GroupedOutputReferenceError(
                                "grouped-output arithmetic failed at batch "
                                f"{batch_index}, position {position}, local "
                                f"group {local_group}, output rank "
                                f"{output_rank}: {exc}"
                            ) from exc
                        saturation_count += int(converted.saturated)
                        output_row.append(converted.code)
                    output_groups.append(tuple(output_row))
                grouped_row = tuple(output_groups)
                grouped_sequence.append(grouped_row)
                flattened_sequence.append(
                    tuple(code for group in grouped_row for code in group)
                )
            grouped_batches.append(tuple(grouped_sequence))
            flattened_batches.append(tuple(flattened_sequence))
    except GroupedOutputReferenceError:
        raise

    input_values = (
        batch_count * sequence_length * local_group_count * group_input_features
    )
    weight_values_count = (
        local_group_count * evaluated_rank_count * group_input_features
    )
    evaluated_outputs = (
        batch_count * sequence_length * local_group_count * evaluated_rank_count
    )
    full_outputs = (
        batch_count * sequence_length * local_group_count * declared_output_rank
    )
    product_accumulates = evaluated_outputs * group_input_features
    counters = GroupedOutputProjectCounters(
        batch_count=batch_count,
        sequence_length=sequence_length,
        tensor_parallel_world_size=tensor_parallel_world_size,
        tensor_parallel_rank=tensor_parallel_rank,
        local_group_count=local_group_count,
        local_head_count=local_group_count * OFFICIAL_HEADS_PER_GROUP,
        heads_per_group=OFFICIAL_HEADS_PER_GROUP,
        head_dim=head_dim,
        group_input_features=group_input_features,
        declared_output_rank=declared_output_rank,
        evaluated_output_ranks_per_group=evaluated_rank_count,
        complete_output=complete_output,
        attention_input_bf16_values=input_values,
        canonical_weight_bf16_values=weight_values_count,
        attention_group_reshape_values=input_values,
        weight_group_reshape_values=weight_values_count,
        exact_product_accumulates=product_accumulates,
        binary32_accumulation_roundings=product_accumulates,
        output_bf16_conversions=evaluated_outputs,
        output_bf16_saturated_values=saturation_count,
        evaluated_grouped_output_bf16_values=evaluated_outputs,
        evaluated_flattened_output_bf16_values=evaluated_outputs,
        declared_full_output_bf16_values=full_outputs,
        transaction_commits=1,
    )
    return GroupedOutputProjectResult(
        numeric_profile=GROUPED_OUTPUT_NUMERIC_PROFILE,
        tensor_parallel_world_size=tensor_parallel_world_size,
        tensor_parallel_rank=tensor_parallel_rank,
        global_group_indices=global_group_indices,
        selected_output_ranks=selected_output_ranks,
        declared_output_rank=declared_output_rank,
        complete_output=complete_output,
        official_shape_profile=official_shape_profile,
        grouped_bf16_codes=tuple(grouped_batches),
        flattened_bf16_codes=tuple(flattened_batches),
        counters=counters,
    )


def grouped_output_project_selected_bf16(
    attention_bf16_codes: object,
    selected_weight_bf16_codes: object,
    *,
    local_group_count: int,
    declared_output_rank: int,
    selected_output_ranks: object,
    tensor_parallel_rank: int = 0,
) -> GroupedOutputProjectResult:
    """Evaluate selected output-rank rows from every local group.

    ``attention_bf16_codes`` has source shape ``[B,S,H_local,D_head]``.
    Exactly eight contiguous heads form each group.  Selected weights have
    shape ``[G_local*R_selected, 8*D_head]`` in group-major then increasing
    selected-rank order.  This audit API preserves the declared full rank and
    reports ``complete_output=False`` unless every rank was supplied.
    """

    local_group_count = _local_group_count(local_group_count)
    tensor_parallel_world_size = OFFICIAL_GLOBAL_GROUPS // local_group_count
    tensor_parallel_rank = _integer(
        tensor_parallel_rank,
        "tensor_parallel_rank",
        minimum=0,
        maximum=tensor_parallel_world_size - 1,
    )
    declared_output_rank = _integer(
        declared_output_rank,
        "declared_output_rank",
        minimum=1,
        maximum=OFFICIAL_OUTPUT_RANK,
    )
    selected_ranks = _selected_ranks(
        selected_output_ranks,
        declared_output_rank=declared_output_rank,
    )
    (
        _,
        attention_values,
        batch_count,
        sequence_length,
        _,
        head_dim,
    ) = _freeze_attention(
        attention_bf16_codes,
        local_group_count=local_group_count,
    )
    group_input_features = OFFICIAL_HEADS_PER_GROUP * head_dim
    _, weight_values = _freeze_weights(
        selected_weight_bf16_codes,
        local_group_count=local_group_count,
        rows_per_group=len(selected_ranks),
        group_input_features=group_input_features,
    )
    return _project_validated(
        attention_values,
        weight_values,
        batch_count=batch_count,
        sequence_length=sequence_length,
        local_group_count=local_group_count,
        head_dim=head_dim,
        declared_output_rank=declared_output_rank,
        selected_output_ranks=selected_ranks,
        tensor_parallel_rank=tensor_parallel_rank,
    )


def grouped_output_project_bf16(
    attention_bf16_codes: object,
    weight_bf16_codes: object,
    *,
    local_group_count: int,
    tensor_parallel_rank: int = 0,
) -> GroupedOutputProjectResult:
    """Execute the complete supplied-rank grouped BF16 projection.

    Canonical weights have source orientation
    ``[G_local*R, 8*D_head]``.  ``R`` is inferred from the complete weight row
    count and must be in ``[1,1024]``.  Output is returned both as
    ``[B,S,G_local,R]`` and in the exact group-major ``[B,S,G_local*R]``
    flattening consumed by the downstream ``wo_b`` operation.
    """

    local_group_count = _local_group_count(local_group_count)
    raw_weights = _sequence(weight_bf16_codes, "weight_bf16_codes")
    if not raw_weights or len(raw_weights) % local_group_count:
        raise GroupedOutputReferenceError(
            "weight_bf16_codes row count must be a nonzero multiple of "
            "local_group_count"
        )
    output_rank = len(raw_weights) // local_group_count
    if output_rank > OFFICIAL_OUTPUT_RANK:
        raise GroupedOutputReferenceError(
            f"inferred output rank must be in [1, {OFFICIAL_OUTPUT_RANK}]"
        )
    return grouped_output_project_selected_bf16(
        attention_bf16_codes,
        raw_weights,
        local_group_count=local_group_count,
        declared_output_rank=output_rank,
        selected_output_ranks=tuple(range(output_rank)),
        tensor_parallel_rank=tensor_parallel_rank,
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "CHECKPOINT_INDEX_SHA256",
    "CHECKPOINT_LOCK_ID",
    "CONVERT_SOURCE_PATH",
    "CONVERT_SOURCE_SHA256",
    "EXCLUDED_OPERATIONS",
    "GROUPED_OUTPUT_NUMERIC_PROFILE",
    "INFERENCE_CONFIG_SHA256",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_DSPARK_SITE_COUNT",
    "OFFICIAL_GLOBAL_GROUPS",
    "OFFICIAL_GLOBAL_OUTPUT_FEATURES",
    "OFFICIAL_GROUP_INPUT_FEATURES",
    "OFFICIAL_HEADS",
    "OFFICIAL_HEADS_PER_GROUP",
    "OFFICIAL_HEAD_DIM",
    "OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256",
    "OFFICIAL_LAYER0_RAW_SCALE_SHA256",
    "OFFICIAL_LAYER0_RAW_WEIGHT_SHA256",
    "OFFICIAL_MAIN_SITE_COUNT",
    "OFFICIAL_OUTPUT_RANK",
    "OFFICIAL_RAW_SCALE_DTYPE",
    "OFFICIAL_RAW_SCALE_SHAPE",
    "OFFICIAL_RAW_WEIGHT_DTYPE",
    "OFFICIAL_RUNTIME_WEIGHT_DTYPE",
    "OFFICIAL_SITE_COUNT",
    "OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES",
    "OFFICIAL_WEIGHT_SHAPE",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "GroupedOutputProjectCounters",
    "GroupedOutputProjectResult",
    "GroupedOutputReferenceError",
    "grouped_output_project_bf16",
    "grouped_output_project_selected_bf16",
]
