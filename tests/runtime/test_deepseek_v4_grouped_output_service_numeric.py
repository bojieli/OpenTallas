from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import inspect
import random

import pytest

from runtime.service_engine import grouped_output_numeric
from runtime.service_engine.grouped_output_numeric import (
    CONVERT_SOURCE_PATH,
    CONVERT_SOURCE_SHA256,
    EXCLUDED_CLAIMS,
    GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
    INFERENCE_CONFIG_SHA256,
    MAX_TOKENS_PER_COMMAND,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    MODEL_SOURCE_PATH,
    MODEL_SOURCE_SHA256,
    OFFICIAL_GLOBAL_GROUPS,
    OFFICIAL_GLOBAL_OUTPUT_FEATURES,
    OFFICIAL_GROUP_INPUT_FEATURES,
    OFFICIAL_HEADS,
    OFFICIAL_HEADS_PER_GROUP,
    OFFICIAL_HEAD_DIM,
    OFFICIAL_OUTPUT_RANK,
    OFFICIAL_RUNTIME_WEIGHT_DTYPE,
    OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES,
    SOURCE_OPERATIONS,
    GroupedOutputServiceNumericError,
    GroupedOutputServiceNumericResult,
    execute_grouped_output_project_bf16,
    execute_grouped_output_project_selected_bf16,
    grouped_output_functional_counters,
)


class _ListSubclass(list):
    pass


ZERO_HEAD = (0,) * OFFICIAL_HEAD_DIM
ZERO_WEIGHT_ROW = (0,) * OFFICIAL_GROUP_INPUT_FEATURES


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _round_ties_even(value: Fraction) -> int:
    assert value >= 0
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    return exponent


def _decode_bf16(code: int) -> Fraction:
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    significand = fraction if exponent == 0 else (1 << 7) | fraction
    power = -133 if exponent == 0 else exponent - 134
    value = Fraction(significand) * _pow2(power)
    return -value if code & 0x8000 else value


def _decode_binary32(code: int) -> Fraction:
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    significand = fraction if exponent == 0 else (1 << 23) | fraction
    power = -149 if exponent == 0 else exponent - 150
    value = Fraction(significand) * _pow2(power)
    return -value if code & 0x80000000 else value


def _encode_binary32(value: Fraction) -> int:
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _round_ties_even(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    exponent = _floor_log2(magnitude)
    significand = _round_ties_even(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise OverflowError("binary32 overflow")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _encode_bf16(value: Fraction) -> tuple[int, bool]:
    if value == 0:
        return 0, False
    sign = 0x8000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _round_ties_even(magnitude / _pow2(-133))
        if significand == 0:
            return 0, False
        if significand < 1 << 7:
            return sign | significand, False
        return sign | (1 << 7), False

    exponent = _floor_log2(magnitude)
    significand = _round_ties_even(magnitude / _pow2(exponent - 7))
    if significand == 1 << 8:
        significand = 1 << 7
        exponent += 1
    if exponent > 127:
        return sign | 0x7F7F, True
    return sign | ((exponent + 127) << 7) | (significand - (1 << 7)), False


def _bf16(value: int | Fraction) -> int:
    # Conformance operands follow binary32-to-BF16 staging rather than rounding
    # a rational directly at a wider precision.
    staged = _encode_binary32(Fraction(value))
    return _encode_bf16(_decode_binary32(staged))[0]


def _oracle_dot(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, bool]:
    accumulator = 0
    for left_code, right_code in zip(left, right, strict=True):
        if left_code & 0x7FFF == 0 or right_code & 0x7FFF == 0:
            continue
        exact = _decode_binary32(accumulator) + _decode_bf16(left_code) * _decode_bf16(
            right_code
        )
        accumulator = _encode_binary32(exact)
    return _encode_bf16(_decode_binary32(accumulator))


def _local_group_count(world_size: int) -> int:
    return OFFICIAL_GLOBAL_GROUPS // world_size


def _zero_attention(
    *,
    world_size: int,
    batch_size: int = 1,
    sequence_length: int = 1,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    heads = (ZERO_HEAD,) * (_local_group_count(world_size) * OFFICIAL_HEADS_PER_GROUP)
    sequence = (heads,) * sequence_length
    return (sequence,) * batch_size


def _zero_weights(
    *,
    world_size: int,
    selected_rank_count: int,
) -> tuple[tuple[int, ...], ...]:
    return (ZERO_WEIGHT_ROW,) * (_local_group_count(world_size) * selected_rank_count)


def _heads_from_group_flats(
    group_flats: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(flat[head * OFFICIAL_HEAD_DIM : (head + 1) * OFFICIAL_HEAD_DIM])
        for flat in group_flats
        for head in range(OFFICIAL_HEADS_PER_GROUP)
    )


def _one_token_attention(
    group_flats: tuple[tuple[int, ...], ...],
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return ((_heads_from_group_flats(group_flats),),)


def _flatten_group_heads(
    heads: tuple[tuple[int, ...], ...],
    local_group: int,
) -> tuple[int, ...]:
    start = local_group * OFFICIAL_HEADS_PER_GROUP
    return tuple(
        code
        for head in heads[start : start + OFFICIAL_HEADS_PER_GROUP]
        for code in head
    )


def _oracle_execute(
    attention: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    weights: tuple[tuple[int, ...], ...],
    *,
    local_groups: int,
    selected_ranks: tuple[int, ...],
) -> tuple[
    tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    int,
]:
    grouped_batches = []
    flattened_batches = []
    saturation_count = 0
    for sequence in attention:
        grouped_sequence = []
        flattened_sequence = []
        for heads in sequence:
            output_groups = []
            for group in range(local_groups):
                input_row = _flatten_group_heads(heads, group)
                output_row = []
                for selected_index in range(len(selected_ranks)):
                    code, saturated = _oracle_dot(
                        input_row,
                        weights[group * len(selected_ranks) + selected_index],
                    )
                    output_row.append(code)
                    saturation_count += int(saturated)
                output_groups.append(tuple(output_row))
            grouped_row = tuple(output_groups)
            grouped_sequence.append(grouped_row)
            flattened_sequence.append(
                tuple(code for group in grouped_row for code in group)
            )
        grouped_batches.append(tuple(grouped_sequence))
        flattened_batches.append(tuple(flattened_sequence))
    return tuple(grouped_batches), tuple(flattened_batches), saturation_count


def test_service_contract_is_pinned_and_has_explicit_claim_boundaries() -> None:
    assert MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert MODEL_SOURCE_PATH == "inference/model.py"
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert CONVERT_SOURCE_PATH == "inference/convert.py"
    assert CONVERT_SOURCE_SHA256 == (
        "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_grouped_output_service_bf16.v1"
    )
    assert SOURCE_OPERATIONS == (
        "attention_group_view",
        "weight_group_view",
        "grouped_einsum_bsgd_grd_to_bsgr",
        "group_major_flatten",
    )
    assert set(EXCLUDED_CLAIMS) == {
        "inverse_rotary_embedding",
        "raw_fp8_e8m0_checkpoint_dequantization",
        "output_b_projection",
        "tensor_parallel_collective",
        "compiler_lowering",
        "checkpoint_or_artifact_loading",
        "official_checkpoint_result_attestation",
        "service_command_authentication",
        "schedule_cycles_latency_traffic_energy_area_density_routing_ppa",
        "end_to_end_model_execution",
    }


def test_official_shapes_dtypes_parallelism_and_command_bound_are_frozen() -> None:
    assert OFFICIAL_GLOBAL_GROUPS == 8
    assert OFFICIAL_HEADS == 64
    assert OFFICIAL_HEADS_PER_GROUP == 8
    assert OFFICIAL_HEAD_DIM == 512
    assert OFFICIAL_GROUP_INPUT_FEATURES == 4096
    assert OFFICIAL_OUTPUT_RANK == 1024
    assert OFFICIAL_GLOBAL_OUTPUT_FEATURES == 8192
    assert OFFICIAL_RUNTIME_WEIGHT_DTYPE == "BF16"
    assert OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES == (1, 2, 4, 8)
    assert MAX_TOKENS_PER_COMMAND == 4


def test_service_implementation_is_artifact_neutral_and_reference_independent() -> None:
    source = inspect.getsource(grouped_output_numeric)
    tree = ast.parse(source)
    imported_modules = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_import_fragments = (
        "reference",
        "compiler",
        "checkpoint",
        "safetensors",
        "numpy",
        "torch",
        "pathlib",
        "pickle",
        "importlib",
        "mmap",
    )
    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in forbidden_import_fragments
    )
    assert {
        (node.level, node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level
    } == {(1, "hc_pre_numeric")}
    assert "expected_output" not in source
    assert "golden_output" not in source
    assert "fallback" not in source.lower()
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "float", "eval", "exec", "__import__"}
        for node in ast.walk(tree)
    )
    assert not any(isinstance(node, ast.Bytes) for node in ast.walk(tree))
    assert not any(
        isinstance(node.value, ast.Dict)
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    )
    numeric_literal_vectors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.List, ast.Set, ast.Tuple))
        and node.elts
        and all(
            isinstance(element, ast.Constant) and type(element.value) is int
            for element in node.elts
        )
    ]
    assert all(len(node.elts) <= 4 for node in numeric_literal_vectors)
    production_parameters = inspect.signature(
        execute_grouped_output_project_bf16
    ).parameters
    assert tuple(production_parameters) == (
        "attention_bf16_codes",
        "weight_bf16_codes",
        "tensor_parallel_world_size",
        "tensor_parallel_rank",
    )
    selected_parameters = inspect.signature(
        execute_grouped_output_project_selected_bf16
    ).parameters
    assert tuple(selected_parameters) == (
        "attention_bf16_codes",
        "selected_weight_bf16_codes",
        "tensor_parallel_world_size",
        "tensor_parallel_rank",
        "selected_output_ranks",
    )


@pytest.mark.parametrize(
    ("world_size", "rank"),
    [
        (world_size, rank)
        for world_size in OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES
        for rank in range(world_size)
    ],
)
def test_every_official_tensor_parallel_rank_owns_contiguous_groups(
    world_size: int,
    rank: int,
) -> None:
    local_groups = _local_group_count(world_size)
    result = execute_grouped_output_project_selected_bf16(
        _zero_attention(world_size=world_size),
        _zero_weights(world_size=world_size, selected_rank_count=1),
        tensor_parallel_world_size=world_size,
        tensor_parallel_rank=rank,
        selected_output_ranks=(OFFICIAL_OUTPUT_RANK - 1,),
    )
    start = rank * local_groups
    assert result.tensor_parallel_world_size == world_size
    assert result.tensor_parallel_rank == rank
    assert result.global_group_indices == tuple(range(start, start + local_groups))
    assert result.grouped_bf16_codes == (((((0,),) * local_groups),),)
    assert result.flattened_bf16_codes == (((0,) * local_groups,),)
    assert result.complete_output is False
    assert result.selected_output_ranks == (OFFICIAL_OUTPUT_RANK - 1,)
    assert result.logical_counters["grouped_output_local_group_count"] == local_groups
    assert result.logical_counters["grouped_output_local_head_count"] == (
        local_groups * OFFICIAL_HEADS_PER_GROUP
    )
    assert result.logical_counters[
        "grouped_output_declared_full_output_bf16_values"
    ] == (local_groups * OFFICIAL_OUTPUT_RANK)


@pytest.mark.parametrize(
    ("batch_size", "sequence_length"),
    ((1, 1), (1, 2), (1, 3), (1, 4), (2, 1), (2, 2), (3, 1), (4, 1)),
)
def test_every_rectangular_one_to_four_token_command_extent_is_supported(
    batch_size: int,
    sequence_length: int,
) -> None:
    result = execute_grouped_output_project_selected_bf16(
        _zero_attention(
            world_size=8,
            batch_size=batch_size,
            sequence_length=sequence_length,
        ),
        (ZERO_WEIGHT_ROW,),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=7,
        selected_output_ranks=(0,),
    )
    assert len(result.grouped_bf16_codes) == batch_size
    assert all(
        len(sequence) == sequence_length for sequence in result.grouped_bf16_codes
    )
    assert all(
        len(sequence) == sequence_length for sequence in result.flattened_bf16_codes
    )
    assert result.logical_counters["grouped_output_token_count"] == (
        batch_size * sequence_length
    )
    assert result.logical_counters["grouped_output_attention_bf16_values"] == (
        batch_size * sequence_length * OFFICIAL_HEADS_PER_GROUP * OFFICIAL_HEAD_DIM
    )


def test_full_entry_point_executes_all_1024_declared_rows_with_nonzero_data() -> None:
    positive = _bf16(1)
    negative = _bf16(-1)
    flat = (positive,) + (0,) * (OFFICIAL_GROUP_INPUT_FEATURES - 1)
    positive_weight = (positive,) + (0,) * (OFFICIAL_GROUP_INPUT_FEATURES - 1)
    negative_weight = (negative,) + (0,) * (OFFICIAL_GROUP_INPUT_FEATURES - 1)
    weights = tuple(
        positive_weight if output_rank % 2 == 0 else negative_weight
        for output_rank in range(OFFICIAL_OUTPUT_RANK)
    )
    expected = tuple(
        positive if output_rank % 2 == 0 else negative
        for output_rank in range(OFFICIAL_OUTPUT_RANK)
    )
    result = execute_grouped_output_project_bf16(
        _one_token_attention((flat,)),
        weights,
        tensor_parallel_world_size=8,
        tensor_parallel_rank=4,
    )
    assert result.selected_output_ranks == tuple(range(OFFICIAL_OUTPUT_RANK))
    assert result.complete_output is True
    assert result.global_group_indices == (4,)
    assert result.grouped_bf16_codes == (((expected,),),)
    assert result.flattened_bf16_codes == ((expected,),)
    assert result.output_saturation_count == 0
    assert result.logical_counters["grouped_output_exact_product_accumulates"] == (
        OFFICIAL_OUTPUT_RANK * OFFICIAL_GROUP_INPUT_FEATURES
    )
    assert result.logical_counters["grouped_output_output_bf16_conversions"] == (
        OFFICIAL_OUTPUT_RANK
    )
    assert (
        result.logical_counters["grouped_output_declared_full_output_bf16_values"]
        == OFFICIAL_OUTPUT_RANK
    )


def test_group_head_rank_orientation_and_group_major_flatten_are_exact() -> None:
    group_flats = []
    expected = []
    weights = []
    for group in range(2):
        flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
        flat[0] = _bf16(10 * group + 1)
        flat[-1] = _bf16(10 * group + 2)
        group_flats.append(tuple(flat))

        first = [0] * OFFICIAL_GROUP_INPUT_FEATURES
        first[0] = _bf16(1)
        last = [0] * OFFICIAL_GROUP_INPUT_FEATURES
        last[-1] = _bf16(1)
        weights.extend((tuple(first), tuple(last)))
        expected.append((_bf16(10 * group + 1), _bf16(10 * group + 2)))

    attention = _one_token_attention(tuple(group_flats))
    result = execute_grouped_output_project_selected_bf16(
        attention,
        tuple(weights),
        tensor_parallel_world_size=4,
        tensor_parallel_rank=3,
        selected_output_ranks=(0, OFFICIAL_OUTPUT_RANK - 1),
    )
    assert result.global_group_indices == (6, 7)
    assert result.grouped_bf16_codes == ((tuple(expected),),)
    assert result.flattened_bf16_codes == (((expected[0] + expected[1]),),)


def test_increasing_k_fma_rounding_and_left_association_are_observable() -> None:
    tiny = _bf16(Fraction(1, 1 << 12))
    flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    flat[:3] = (_bf16(1), tiny, _bf16(-1))
    weight = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    weight[:3] = (_bf16(1), tiny, _bf16(1))
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(weight),),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert result.flattened_bf16_codes == (((0,),),)
    assert _encode_bf16(Fraction(1, 1 << 24))[0] != 0

    large = _bf16(1 << 100)
    flat[:8] = (
        large,
        _bf16(1),
        large ^ 0x8000,
        _bf16(1),
        _bf16(1),
        _bf16(1),
        _bf16(1),
        _bf16(1),
    )
    weight[:8] = (_bf16(1),) * 8
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(weight),),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert result.flattened_bf16_codes == (((_bf16(5),),),)


def test_bf16_final_rne_subnormal_and_signed_zero_boundaries() -> None:
    flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    flat[:3] = (_bf16(1), _bf16(Fraction(1, 1 << 8)), _bf16(Fraction(1, 1 << 16)))
    tie = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    tie[:2] = (_bf16(1), _bf16(1))
    above = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    above[:3] = (_bf16(1), _bf16(1), _bf16(1))
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(tie), tuple(above)),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0, 1),
    )
    assert result.flattened_bf16_codes == (((0x3F80, 0x3F81),),)

    flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    flat[0] = 0x0001
    identity = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    identity[0] = _bf16(1)
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(identity),),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert result.flattened_bf16_codes == (((0x0001,),),)

    flat[0] = 0x8000
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(identity),),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert result.flattened_bf16_codes == (((0,),),)


def test_finite_bf16_saturation_counts_and_binary32_overflow_poisons() -> None:
    flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    flat[:2] = (0x7F7F, 0x7B00)
    weight = [0] * OFFICIAL_GROUP_INPUT_FEATURES
    weight[:2] = (_bf16(1), _bf16(1))
    result = execute_grouped_output_project_selected_bf16(
        _one_token_attention((tuple(flat),)),
        (tuple(weight),),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert result.flattened_bf16_codes == (((0x7F7F,),),)
    assert result.output_saturation_count == 1
    assert result.logical_counters["grouped_output_output_bf16_saturations"] == 1

    flat[1] = 0
    weight[0] = _bf16(2)
    overflowing_attention = _one_token_attention((tuple(flat),))
    overflowing_weights = (tuple(weight),)
    before_attention = deepcopy(overflowing_attention)
    before_weights = deepcopy(overflowing_weights)
    with pytest.raises(
        GroupedOutputServiceNumericError,
        match=r"batch 0, position 0, local group 0, output rank 0, feature 0:.*overflow",
    ):
        execute_grouped_output_project_selected_bf16(
            overflowing_attention,
            overflowing_weights,
            tensor_parallel_world_size=8,
            tensor_parallel_rank=0,
            selected_output_ranks=(0,),
        )
    assert overflowing_attention == before_attention
    assert overflowing_weights == before_weights


def test_all_finite_bf16_values_round_trip_exhaustively_at_output_boundary() -> None:
    finite_count = 0
    nonfinite_count = 0
    for code in range(1 << 16):
        if code & 0x7F80 == 0x7F80:
            nonfinite_count += 1
            with pytest.raises(GroupedOutputServiceNumericError, match="finite BF16"):
                grouped_output_numeric._finite_bf16(code, "code")
            continue
        finite_count += 1
        observed, saturated = grouped_output_numeric._binary32_to_bf16(code << 16)
        expected = 0 if code & 0x7FFF == 0 else code
        assert (observed, saturated) == (expected, False)
    assert finite_count == 65_280
    assert nonfinite_count == 256


@pytest.mark.parametrize(
    ("binary32_code", "expected_bf16", "saturated"),
    (
        (0x3F808000, 0x3F80, False),
        (0x3F818000, 0x3F82, False),
        (0x00008000, 0x0000, False),
        (0x00008001, 0x0001, False),
        (0x80008000, 0x0000, False),
        (0x80008001, 0x8001, False),
        (0x7F7F8000, 0x7F7F, True),
        (0xFF7F8000, 0xFF7F, True),
    ),
)
def test_binary32_to_bf16_tie_subnormal_and_saturation_boundaries(
    binary32_code: int,
    expected_bf16: int,
    saturated: bool,
) -> None:
    assert grouped_output_numeric._binary32_to_bf16(binary32_code) == (
        expected_bf16,
        saturated,
    )


@pytest.mark.parametrize(
    "invalid",
    (
        True,
        False,
        -1,
        1 << 32,
        1.0,
        "0",
        None,
        0x7F800000,
        0xFF800000,
        0x7FC00001,
    ),
)
def test_binary32_to_bf16_rejects_invalid_or_nonfinite_encodings(
    invalid: object,
) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match="binary32"):
        grouped_output_numeric._binary32_to_bf16(invalid)


def test_source_derived_functional_counters_reconcile_exactly() -> None:
    counters = grouped_output_functional_counters(
        4,
        4,
        3,
        output_saturation_count=2,
    )
    assert dict(counters) == {
        "complete_events": 1,
        "grouped_output_attention_bf16_values": 32_768,
        "grouped_output_attention_group_view_values": 32_768,
        "grouped_output_binary32_accumulation_roundings": 98_304,
        "grouped_output_canonical_weight_bf16_values": 24_576,
        "grouped_output_declared_full_output_bf16_values": 8192,
        "grouped_output_evaluated_output_ranks_per_group": 3,
        "grouped_output_exact_product_accumulates": 98_304,
        "grouped_output_flattened_output_bf16_values": 24,
        "grouped_output_group_input_features": 4096,
        "grouped_output_grouped_output_bf16_values": 24,
        "grouped_output_local_group_count": 2,
        "grouped_output_local_head_count": 16,
        "grouped_output_output_bf16_conversions": 24,
        "grouped_output_output_bf16_saturations": 2,
        "grouped_output_token_count": 4,
        "grouped_output_weight_group_view_values": 24_576,
        "semantic_operators_executed": 1,
        "tensor_parallel_world_size": 4,
    }
    assert counters == grouped_output_numeric.MappingProxyType(dict(counters))
    assert list(counters) == sorted(counters)
    assert all(type(value) is int and value >= 0 for value in counters.values())
    with pytest.raises(TypeError):
        counters["new"] = 1  # type: ignore[index]

    prohibited_physical_claims = (
        "cycle",
        "latency",
        "throughput",
        "bandwidth",
        "traffic",
        "energy",
        "area",
        "density",
        "routing",
        "ppa",
    )
    assert not any(
        token in counter_name
        for counter_name in counters
        for token in prohibited_physical_claims
    )


@pytest.mark.parametrize("invalid", (True, False, 0, 5, -1, 1.0, "1", None))
def test_functional_counter_token_count_is_strict(invalid: object) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match="token_count"):
        grouped_output_functional_counters(invalid, 1, 1)


@pytest.mark.parametrize("invalid", (True, False, 0, -1, 1025, 1.0, "1", None))
def test_functional_counter_evaluated_rank_count_is_strict(invalid: object) -> None:
    with pytest.raises(
        GroupedOutputServiceNumericError,
        match="evaluated_output_ranks_per_group",
    ):
        grouped_output_functional_counters(1, 1, invalid)


@pytest.mark.parametrize("invalid", (True, False, -1, 2, 1.0, "0", None))
def test_functional_counter_saturation_count_is_strict(invalid: object) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match="saturation_count"):
        grouped_output_functional_counters(
            1,
            8,
            1,
            output_saturation_count=invalid,
        )


@pytest.mark.parametrize("invalid", (True, False, 0, 3, 16, 1.0, "1", None))
def test_tensor_parallel_world_size_is_strict(invalid: object) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match="world_size"):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=8),
            (ZERO_WEIGHT_ROW,),
            tensor_parallel_world_size=invalid,  # type: ignore[arg-type]
            tensor_parallel_rank=0,
            selected_output_ranks=(0,),
        )


@pytest.mark.parametrize("invalid", (True, False, -1, 2, 1.0, "0", None))
def test_tensor_parallel_rank_is_strict(invalid: object) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match="tensor_parallel_rank"):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=2),
            _zero_weights(world_size=2, selected_rank_count=1),
            tensor_parallel_world_size=2,
            tensor_parallel_rank=invalid,  # type: ignore[arg-type]
            selected_output_ranks=(0,),
        )


@pytest.mark.parametrize(
    ("invalid", "message"),
    (
        ((), "at least one"),
        ((1, 0), "strictly increasing"),
        ((0, 0), "strictly increasing"),
        ((True,), "integer"),
        ((-1,), "integer"),
        ((OFFICIAL_OUTPUT_RANK,), "integer"),
        ((1.0,), "integer"),
        (range(1), "exact list or tuple"),
    ),
)
def test_selected_output_ranks_are_strict(invalid: object, message: str) -> None:
    with pytest.raises(GroupedOutputServiceNumericError, match=message):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=8),
            (ZERO_WEIGHT_ROW,),
            tensor_parallel_world_size=8,
            tensor_parallel_rank=0,
            selected_output_ranks=invalid,
        )


def test_attention_shape_type_extent_and_finiteness_fail_closed() -> None:
    valid_weights = (ZERO_WEIGHT_ROW,)
    valid_heads = (ZERO_HEAD,) * OFFICIAL_HEADS_PER_GROUP
    short_heads = (ZERO_HEAD,) * (OFFICIAL_HEADS_PER_GROUP - 1)
    short_head_tensor = (ZERO_HEAD[:-1],) + (ZERO_HEAD,) * 7
    common = {
        "tensor_parallel_world_size": 8,
        "tensor_parallel_rank": 0,
        "selected_output_ranks": (0,),
    }
    invalid_cases = (
        (None, "exact list or tuple"),
        ((), "at least one batch"),
        (((),), "at least one position"),
        (
            _zero_attention(world_size=8, batch_size=1, sequence_length=5),
            "batch\\*sequence",
        ),
        (
            _zero_attention(world_size=8, batch_size=2, sequence_length=3),
            "batch\\*sequence",
        ),
        (
            _zero_attention(world_size=8, batch_size=5, sequence_length=1),
            "batch extent",
        ),
        (((valid_heads,), (valid_heads,) * 2), "rectangular"),
        (((short_heads,),), "exactly 8 local heads"),
        (((short_head_tensor,),), "exactly 512"),
    )
    for invalid, message in invalid_cases:
        with pytest.raises(GroupedOutputServiceNumericError, match=message):
            execute_grouped_output_project_selected_bf16(
                invalid,
                valid_weights,
                **common,
            )

    for invalid_code, message in (
        (True, "16-bit"),
        (-1, "16-bit"),
        (1 << 16, "16-bit"),
        (0x7F80, "finite BF16"),
        (0x7FC1, "finite BF16"),
        (0xFF80, "finite BF16"),
    ):
        head = (invalid_code,) + ZERO_HEAD[1:]
        heads = (head,) + (ZERO_HEAD,) * 7
        attention = ((heads,),)
        with pytest.raises(GroupedOutputServiceNumericError, match=message):
            execute_grouped_output_project_selected_bf16(
                attention,
                valid_weights,
                **common,
            )


def test_every_nested_input_axis_requires_an_exact_list_or_tuple() -> None:
    valid_heads = (ZERO_HEAD,) * OFFICIAL_HEADS_PER_GROUP
    common = {
        "tensor_parallel_world_size": 8,
        "tensor_parallel_rank": 0,
        "selected_output_ranks": (0,),
    }
    invalid_attention_values = (
        _ListSubclass([(valid_heads,)]),
        (_ListSubclass([valid_heads]),),
        ((_ListSubclass(valid_heads),),),
        (((_ListSubclass(ZERO_HEAD),) + (ZERO_HEAD,) * 7,),),
    )
    for invalid in invalid_attention_values:
        with pytest.raises(
            GroupedOutputServiceNumericError, match="exact list or tuple"
        ):
            execute_grouped_output_project_selected_bf16(
                invalid,
                (ZERO_WEIGHT_ROW,),
                **common,
            )

    with pytest.raises(GroupedOutputServiceNumericError, match="exact list or tuple"):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=8),
            _ListSubclass([ZERO_WEIGHT_ROW]),
            **common,
        )
    with pytest.raises(GroupedOutputServiceNumericError, match="exact list or tuple"):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=8),
            (_ListSubclass(ZERO_WEIGHT_ROW),),
            **common,
        )
    with pytest.raises(GroupedOutputServiceNumericError, match="exact list or tuple"):
        execute_grouped_output_project_selected_bf16(
            _zero_attention(world_size=8),
            (ZERO_WEIGHT_ROW,),
            **{**common, "selected_output_ranks": _ListSubclass([0])},
        )


def test_weight_shape_type_and_finiteness_fail_closed() -> None:
    attention = _zero_attention(world_size=8)
    common = {
        "tensor_parallel_world_size": 8,
        "tensor_parallel_rank": 0,
        "selected_output_ranks": (0,),
    }
    invalid_cases = (
        (None, "exact list or tuple"),
        ((), "exactly 1 group-major rows"),
        ((ZERO_WEIGHT_ROW, ZERO_WEIGHT_ROW), "exactly 1 group-major rows"),
        ((ZERO_WEIGHT_ROW[:-1],), "exactly 4096"),
        (((True,) + ZERO_WEIGHT_ROW[1:],), "16-bit"),
        (((-1,) + ZERO_WEIGHT_ROW[1:],), "16-bit"),
        ((((1 << 16),) + ZERO_WEIGHT_ROW[1:],), "16-bit"),
        (((0x7F80,) + ZERO_WEIGHT_ROW[1:],), "finite BF16"),
    )
    for invalid, message in invalid_cases:
        with pytest.raises(GroupedOutputServiceNumericError, match=message):
            execute_grouped_output_project_selected_bf16(
                attention,
                invalid,
                **common,
            )


def test_all_validation_completes_before_any_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def forbidden_fma(_accumulator: int, _left: int, _right: int) -> int:
        nonlocal calls
        calls += 1
        raise AssertionError("arithmetic ran before validation completed")

    monkeypatch.setattr(grouped_output_numeric, "rn32_fused_product_add", forbidden_fma)
    nonzero_head = (_bf16(1),) + ZERO_HEAD[1:]
    heads = (nonzero_head,) + (ZERO_HEAD,) * 7
    attention = ((heads,),)
    invalid_weight = (_bf16(1),) + ZERO_WEIGHT_ROW[1:-1] + (0x7F80,)
    with pytest.raises(GroupedOutputServiceNumericError, match="finite BF16"):
        execute_grouped_output_project_selected_bf16(
            attention,
            (invalid_weight,),
            tensor_parallel_world_size=8,
            tensor_parallel_rank=0,
            selected_output_ranks=(0,),
        )
    assert calls == 0


def test_inputs_are_unchanged_and_result_is_deeply_immutable() -> None:
    attention = [
        [
            [list(ZERO_HEAD) for _ in range(OFFICIAL_HEADS_PER_GROUP)],
        ],
    ]
    weights = [list(ZERO_WEIGHT_ROW)]
    attention[0][0][0][0] = _bf16(1)
    weights[0][0] = _bf16(1)
    before_attention = deepcopy(attention)
    before_weights = deepcopy(weights)
    result = execute_grouped_output_project_selected_bf16(
        attention,
        weights,
        tensor_parallel_world_size=8,
        tensor_parallel_rank=0,
        selected_output_ranks=(0,),
    )
    assert attention == before_attention
    assert weights == before_weights
    assert result.flattened_bf16_codes == (((_bf16(1),),),)
    frozen_result = result
    attention[0][0][0][0] = _bf16(-1)
    weights[0][0] = _bf16(-1)
    assert result == frozen_result
    assert result.flattened_bf16_codes == (((_bf16(1),),),)
    assert result.semantic_counters is result.logical_counters
    with pytest.raises(FrozenInstanceError):
        result.complete_output = True  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.grouped_bf16_codes[0][0][0][0] = 0  # type: ignore[index]
    with pytest.raises(TypeError):
        result.logical_counters["new"] = 1  # type: ignore[index]


def test_public_result_constructor_rejects_mutability_drift_and_overclaims() -> None:
    result = execute_grouped_output_project_selected_bf16(
        _zero_attention(world_size=8),
        (ZERO_WEIGHT_ROW,),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=3,
        selected_output_ranks=(0,),
    )
    assert type(result) is GroupedOutputServiceNumericResult

    invalid_cases = (
        (
            {"numeric_profile": "unqualified"},
            "numeric profile differs",
        ),
        (
            {"global_group_indices": (0,)},
            "global-group ownership differs",
        ),
        (
            {"selected_output_ranks": [0]},
            "selected ranks must be immutable",
        ),
        (
            {"complete_output": True},
            "completion status differs",
        ),
        (
            {"grouped_bf16_codes": [[[(0,)]]]},
            "batch axis is not an immutable",
        ),
        (
            {"grouped_bf16_codes": (((((0x7F80,),),),))},
            "finite BF16",
        ),
        (
            {"flattened_bf16_codes": (((1,),),)},
            "flattened payload differs",
        ),
        (
            {"output_saturation_count": 2},
            "output_saturation_count",
        ),
        (
            {"logical_counters": dict(result.logical_counters)},
            "immutable mapping",
        ),
        (
            {
                "logical_counters": grouped_output_numeric.MappingProxyType(
                    {
                        **result.logical_counters,
                        "complete_events": 2,
                    }
                )
            },
            "do not reconcile",
        ),
    )
    for changes, message in invalid_cases:
        with pytest.raises(GroupedOutputServiceNumericError, match=message):
            replace(result, **changes)


def test_public_result_constructor_detaches_counter_proxy_backing_storage() -> None:
    result = execute_grouped_output_project_selected_bf16(
        _zero_attention(world_size=8),
        (ZERO_WEIGHT_ROW,),
        tensor_parallel_world_size=8,
        tensor_parallel_rank=3,
        selected_output_ranks=(0,),
    )
    caller_backing = dict(result.logical_counters)
    reconstructed = replace(
        result,
        logical_counters=grouped_output_numeric.MappingProxyType(caller_backing),
    )

    caller_backing["complete_events"] = 2
    caller_backing["forged_after_construction"] = 1

    assert reconstructed.logical_counters["complete_events"] == 1
    assert "forged_after_construction" not in reconstructed.logical_counters
    assert dict(reconstructed.logical_counters) == dict(result.logical_counters)


def test_randomized_sparse_commands_match_independent_fraction_oracle() -> None:
    rng = random.Random(0x5345_5256_4752_4F55)
    palette = (
        0,
        0x0001,
        0x8001,
        _bf16(Fraction(1, 16)),
        _bf16(Fraction(-1, 16)),
        _bf16(1),
        _bf16(-1),
        _bf16(3),
        _bf16(-3),
        _bf16(16),
        _bf16(-16),
    )
    for _ in range(80):
        world_size = rng.choice(OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES)
        rank = rng.randrange(world_size)
        local_groups = _local_group_count(world_size)
        token_count = rng.randint(1, MAX_TOKENS_PER_COMMAND)
        selected_ranks = tuple(
            sorted(rng.sample(range(OFFICIAL_OUTPUT_RANK), rng.randint(1, 3)))
        )
        active_features = tuple(sorted(rng.sample(range(4096), rng.randint(4, 16))))

        sequence = []
        for _token in range(token_count):
            group_flats = []
            for _group in range(local_groups):
                flat = [0] * OFFICIAL_GROUP_INPUT_FEATURES
                for feature in active_features:
                    flat[feature] = rng.choice(palette)
                group_flats.append(tuple(flat))
            sequence.append(_heads_from_group_flats(tuple(group_flats)))
        attention = (tuple(sequence),)

        weights = []
        for _group in range(local_groups):
            for _rank in selected_ranks:
                row = [0] * OFFICIAL_GROUP_INPUT_FEATURES
                for feature in active_features:
                    row[feature] = rng.choice(palette)
                weights.append(tuple(row))
        frozen_weights = tuple(weights)

        observed = execute_grouped_output_project_selected_bf16(
            attention,
            frozen_weights,
            tensor_parallel_world_size=world_size,
            tensor_parallel_rank=rank,
            selected_output_ranks=selected_ranks,
        )
        expected_grouped, expected_flattened, expected_saturations = _oracle_execute(
            attention,
            frozen_weights,
            local_groups=local_groups,
            selected_ranks=selected_ranks,
        )
        assert observed.grouped_bf16_codes == expected_grouped
        assert observed.flattened_bf16_codes == expected_flattened
        assert observed.output_saturation_count == expected_saturations
