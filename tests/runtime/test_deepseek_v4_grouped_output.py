from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import random
import struct

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_binary32,
    encode_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.grouped_output import (
    CHECKPOINT_INDEX_SHA256,
    CHECKPOINT_LOCK_ID,
    CONVERT_SOURCE_PATH,
    CONVERT_SOURCE_SHA256,
    EXCLUDED_OPERATIONS,
    GROUPED_OUTPUT_NUMERIC_PROFILE,
    INFERENCE_CONFIG_SHA256,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    MODEL_SOURCE_PATH,
    MODEL_SOURCE_SHA256,
    OFFICIAL_DSPARK_SITE_COUNT,
    OFFICIAL_GLOBAL_GROUPS,
    OFFICIAL_GLOBAL_OUTPUT_FEATURES,
    OFFICIAL_GROUP_INPUT_FEATURES,
    OFFICIAL_HEADS,
    OFFICIAL_HEADS_PER_GROUP,
    OFFICIAL_HEAD_DIM,
    OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256,
    OFFICIAL_LAYER0_RAW_SCALE_SHA256,
    OFFICIAL_LAYER0_RAW_WEIGHT_SHA256,
    OFFICIAL_MAIN_SITE_COUNT,
    OFFICIAL_OUTPUT_RANK,
    OFFICIAL_RAW_SCALE_DTYPE,
    OFFICIAL_RAW_SCALE_SHAPE,
    OFFICIAL_RAW_WEIGHT_DTYPE,
    OFFICIAL_RUNTIME_WEIGHT_DTYPE,
    OFFICIAL_SITE_COUNT,
    OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES,
    OFFICIAL_WEIGHT_SHAPE,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    GroupedOutputReferenceError,
    grouped_output_project_bf16,
    grouped_output_project_selected_bf16,
)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _uniform_attention(
    *,
    batches: int,
    sequence_length: int,
    local_groups: int,
    head_dim: int,
    code: int = 0,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    row = (code,) * head_dim
    heads = (row,) * (local_groups * OFFICIAL_HEADS_PER_GROUP)
    sequence = (heads,) * sequence_length
    return (sequence,) * batches


def _uniform_weights(
    *,
    local_groups: int,
    output_rank: int,
    head_dim: int,
    code: int = 0,
) -> tuple[tuple[int, ...], ...]:
    row = (code,) * (OFFICIAL_HEADS_PER_GROUP * head_dim)
    return (row,) * (local_groups * output_rank)


def _finite_bf16_value(code: int) -> Fraction:
    decoded = decode_bf16(code)
    assert decoded.finite and decoded.value is not None
    return decoded.value


def _independent_dot_to_bf16(
    left_codes: tuple[int, ...],
    right_codes: tuple[int, ...],
) -> tuple[int, bool]:
    accumulator = 0
    for left_code, right_code in zip(left_codes, right_codes, strict=True):
        accumulator_value = decode_binary32(accumulator).value
        assert accumulator_value is not None
        exact = accumulator_value + _finite_bf16_value(left_code) * _finite_bf16_value(
            right_code
        )
        accumulator = encode_binary32_rne(exact)
    accumulator_value = decode_binary32(accumulator).value
    assert accumulator_value is not None
    converted = encode_bf16_rne(accumulator_value)
    return converted.code, converted.saturated


def _flatten_group_heads(
    heads: tuple[tuple[int, ...], ...],
    group: int,
) -> tuple[int, ...]:
    start = group * OFFICIAL_HEADS_PER_GROUP
    return tuple(
        value
        for head in heads[start : start + OFFICIAL_HEADS_PER_GROUP]
        for value in head
    )


def test_grouped_output_is_bound_to_official_source_checkpoint_and_config() -> None:
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
    assert CHECKPOINT_INDEX_SHA256 == (
        "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
    )
    assert CHECKPOINT_LOCK_ID == (
        "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
    )
    assert GROUPED_OUTPUT_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_grouped_output_bf16.v1"
    )


def test_official_shapes_dtypes_sites_and_payload_hashes_are_frozen() -> None:
    assert OFFICIAL_SITE_COUNT == 46
    assert OFFICIAL_MAIN_SITE_COUNT == 43
    assert OFFICIAL_DSPARK_SITE_COUNT == 3
    assert OFFICIAL_MAIN_SITE_COUNT + OFFICIAL_DSPARK_SITE_COUNT == OFFICIAL_SITE_COUNT
    assert OFFICIAL_GLOBAL_GROUPS == 8
    assert OFFICIAL_HEADS == 64
    assert OFFICIAL_HEADS_PER_GROUP == 8
    assert OFFICIAL_HEAD_DIM == 512
    assert OFFICIAL_GROUP_INPUT_FEATURES == 4096
    assert OFFICIAL_OUTPUT_RANK == 1024
    assert OFFICIAL_GLOBAL_OUTPUT_FEATURES == 8192
    assert OFFICIAL_WEIGHT_SHAPE == (8192, 4096)
    assert OFFICIAL_RAW_WEIGHT_DTYPE == "F8_E4M3"
    assert OFFICIAL_RAW_SCALE_SHAPE == (64, 32)
    assert OFFICIAL_RAW_SCALE_DTYPE == "F8_E8M0"
    assert OFFICIAL_RUNTIME_WEIGHT_DTYPE == "BF16"
    assert OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES == (1, 2, 4, 8)
    assert PINNED_MAX_POSITION == 1_048_576
    assert OFFICIAL_LAYER0_RAW_WEIGHT_SHA256 == (
        "4ed730a5e64d2bf11cd13af4800473cf24ac1113744c0d1d5fdb8d438bded258"
    )
    assert OFFICIAL_LAYER0_RAW_SCALE_SHA256 == (
        "96416ed079e48da7b60aca5f5c020b4579124d07262bfc50082a414964a3f345"
    )
    assert OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256 == (
        "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b",
        "ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016",
        "d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc",
        "0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b",
    )


def test_production_reference_has_no_framework_or_host_float_dependency() -> None:
    source = (
        Path(__file__).parents[2] / "runtime" / "reference" / "grouped_output.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert imported_roots.isdisjoint({"decimal", "math", "mpmath", "numpy", "torch"})
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )


def test_operator_nonclaims_are_explicit() -> None:
    assert set(EXCLUDED_OPERATIONS) == {
        "inverse_rotary_embedding",
        "raw_fp8_e8m0_checkpoint_dequantization",
        "output_b_projection",
        "tensor_parallel_collective",
        "compiler_lowering",
        "service_engine_execution",
        "schedule_cycles_traffic_energy_area_ppa",
        "end_to_end_model_execution",
    }


def test_group_and_rank_orientation_matches_source_einsum_and_flatten() -> None:
    local_groups = 2
    head_dim = 2
    heads = tuple(
        (_bf16(100 * head + 1), _bf16(100 * head + 2))
        for head in range(local_groups * OFFICIAL_HEADS_PER_GROUP)
    )
    attention = ((heads,),)
    group_width = OFFICIAL_HEADS_PER_GROUP * head_dim

    weights = []
    for group in range(local_groups):
        first = [0] * group_width
        first[0] = _bf16(1)
        last = [0] * group_width
        last[-1] = _bf16(1)
        weights.extend((tuple(first), tuple(last)))

    result = grouped_output_project_bf16(
        attention,
        tuple(weights),
        local_group_count=local_groups,
    )
    assert result.complete_output is True
    assert result.official_shape_profile is False
    assert result.grouped_bf16_codes == (
        (
            (
                (_bf16(1), _bf16(702)),
                (_bf16(801), _bf16(1502)),
            ),
        ),
    )
    assert result.flattened_bf16_codes == (
        ((_bf16(1), _bf16(702), _bf16(801), _bf16(1502)),),
    )


def test_contiguous_head_feature_order_crosses_each_head_boundary_once() -> None:
    head_dim = 3
    heads = tuple(
        tuple(_bf16(10 * head + column + 1) for column in range(head_dim))
        for head in range(OFFICIAL_HEADS_PER_GROUP)
    )
    group_width = OFFICIAL_HEADS_PER_GROUP * head_dim
    weights = []
    for feature in range(group_width):
        row = [0] * group_width
        row[feature] = _bf16(1)
        weights.append(tuple(row))
    result = grouped_output_project_bf16(
        ((heads,),),
        tuple(weights),
        local_group_count=1,
    )
    assert result.flattened_bf16_codes[0][0] == tuple(
        code for head in heads for code in head
    )


@pytest.mark.parametrize(
    ("local_groups", "tensor_parallel_rank", "world_size", "global_groups"),
    [
        (8, 0, 1, tuple(range(8))),
        (4, 1, 2, (4, 5, 6, 7)),
        (2, 3, 4, (6, 7)),
        (1, 7, 8, (7,)),
    ],
)
def test_tensor_parallel_rank_owns_a_contiguous_global_group_interval(
    local_groups: int,
    tensor_parallel_rank: int,
    world_size: int,
    global_groups: tuple[int, ...],
) -> None:
    result = grouped_output_project_bf16(
        _uniform_attention(
            batches=1,
            sequence_length=1,
            local_groups=local_groups,
            head_dim=1,
        ),
        _uniform_weights(
            local_groups=local_groups,
            output_rank=1,
            head_dim=1,
        ),
        local_group_count=local_groups,
        tensor_parallel_rank=tensor_parallel_rank,
    )
    assert result.tensor_parallel_world_size == world_size
    assert result.tensor_parallel_rank == tensor_parallel_rank
    assert result.global_group_indices == global_groups


def test_selected_rank_slice_preserves_declared_rank_and_group_major_rows() -> None:
    selected = (0, 17, 1023)
    local_groups = 2
    attention = _uniform_attention(
        batches=1,
        sequence_length=1,
        local_groups=local_groups,
        head_dim=1,
        code=_bf16(1),
    )
    weights = tuple(
        (_bf16(10 * group + selected_index + 1),) * 8
        for group in range(local_groups)
        for selected_index in range(len(selected))
    )
    result = grouped_output_project_selected_bf16(
        attention,
        weights,
        local_group_count=local_groups,
        declared_output_rank=OFFICIAL_OUTPUT_RANK,
        selected_output_ranks=selected,
        tensor_parallel_rank=2,
    )
    assert result.selected_output_ranks == selected
    assert result.declared_output_rank == OFFICIAL_OUTPUT_RANK
    assert result.complete_output is False
    assert result.grouped_bf16_codes == (
        (((_bf16(8), _bf16(16), _bf16(24)), (_bf16(88), _bf16(96), _bf16(104))),),
    )
    assert result.flattened_bf16_codes == (
        ((_bf16(8), _bf16(16), _bf16(24), _bf16(88), _bf16(96), _bf16(104)),),
    )


def test_selected_audit_executes_the_full_official_reduction_width() -> None:
    local_groups = 2  # The pinned MP4 local shape.
    attention = []
    for head in range(local_groups * OFFICIAL_HEADS_PER_GROUP):
        attention.append(
            tuple(_bf16(100 * head + column) for column in range(OFFICIAL_HEAD_DIM))
        )
    group_width = OFFICIAL_GROUP_INPUT_FEATURES
    selected = (0, OFFICIAL_OUTPUT_RANK - 1)
    weights = []
    expected = []
    for group in range(local_groups):
        group_expected = []
        for selected_index in range(len(selected)):
            feature = selected_index * (group_width - 1)
            row = [0] * group_width
            row[feature] = _bf16(1)
            weights.append(tuple(row))
            flat = tuple(
                value
                for head in attention[
                    group * OFFICIAL_HEADS_PER_GROUP : (group + 1)
                    * OFFICIAL_HEADS_PER_GROUP
                ]
                for value in head
            )
            group_expected.append(flat[feature])
        expected.append(tuple(group_expected))

    result = grouped_output_project_selected_bf16(
        ((tuple(attention),),),
        tuple(weights),
        local_group_count=local_groups,
        declared_output_rank=OFFICIAL_OUTPUT_RANK,
        selected_output_ranks=selected,
        tensor_parallel_rank=3,
    )
    assert result.official_shape_profile is True
    assert result.complete_output is False
    assert result.global_group_indices == (6, 7)
    assert result.grouped_bf16_codes == ((tuple(expected),),)
    assert result.counters.group_input_features == 4096
    assert result.counters.exact_product_accumulates == 2 * 2 * 4096
    assert result.counters.declared_full_output_bf16_values == 2 * 1024


def test_increasing_feature_accumulation_rounding_is_observable() -> None:
    tiny = _bf16(Fraction(1, 1 << 12))
    flat = (_bf16(1), tiny, _bf16(-1), 0, 0, 0, 0, 0)
    heads = tuple((code,) for code in flat)
    weight = ((_bf16(1), tiny, _bf16(1), 0, 0, 0, 0, 0),)
    result = grouped_output_project_bf16(
        ((heads,),),
        weight,
        local_group_count=1,
    )
    assert result.flattened_bf16_codes == (((0,),),)
    assert encode_bf16_rne(Fraction(1, 1 << 24)).code != 0


def test_accumulation_is_left_associated_in_flattened_feature_order() -> None:
    large = _bf16(1 << 100)
    flat = (
        large,
        _bf16(1),
        large ^ 0x8000,
        _bf16(1),
        _bf16(1),
        _bf16(1),
        _bf16(1),
        _bf16(1),
    )
    result = grouped_output_project_bf16(
        ((tuple((code,) for code in flat),),),
        ((_bf16(1),) * 8,),
        local_group_count=1,
    )
    assert result.flattened_bf16_codes == (((_bf16(5),),),)


def test_final_binary32_to_bf16_boundary_uses_rne_ties_to_even() -> None:
    halfway = _bf16(Fraction(1, 1 << 8))
    above_halfway = _bf16(Fraction(1, 1 << 16))
    heads = (
        (_bf16(1),),
        (halfway,),
        (above_halfway,),
        (0,),
        (0,),
        (0,),
        (0,),
        (0,),
    )
    weights = (
        (_bf16(1), _bf16(1), 0, 0, 0, 0, 0, 0),
        (_bf16(1), _bf16(1), _bf16(1), 0, 0, 0, 0, 0),
    )
    result = grouped_output_project_bf16(
        ((heads,),),
        weights,
        local_group_count=1,
    )
    assert result.flattened_bf16_codes[0][0] == (0x3F80, 0x3F81)


def test_bf16_subnormal_is_preserved_through_product_and_output() -> None:
    heads = ((0x0001,),) + ((0,),) * 7
    result = grouped_output_project_bf16(
        ((heads,),),
        ((_bf16(1),) + (0,) * 7,),
        local_group_count=1,
    )
    assert result.flattened_bf16_codes == (((0x0001,),),)


def test_finite_bf16_output_saturation_is_sticky_and_counted() -> None:
    heads = ((0x7F7F,), (0x7B00,)) + ((0,),) * 6
    result = grouped_output_project_bf16(
        ((heads,),),
        ((_bf16(1), _bf16(1)) + (0,) * 6,),
        local_group_count=1,
    )
    assert result.flattened_bf16_codes == (((0x7F7F,),),)
    assert result.counters.output_bf16_saturated_values == 1


def test_intermediate_binary32_overflow_poisons_the_complete_transaction() -> None:
    heads = ((0x7F7F,),) + ((0,),) * 7
    weights = ((_bf16(2),) + (0,) * 7,)
    with pytest.raises(
        GroupedOutputReferenceError,
        match=r"batch 0, position 0, local group 0, output rank 0:.*overflow",
    ):
        grouped_output_project_bf16(
            ((heads,),),
            weights,
            local_group_count=1,
        )


def test_counters_reconcile_shapes_products_roundings_and_flattening() -> None:
    batches = 2
    sequence_length = 3
    local_groups = 2
    head_dim = 4
    output_rank = 5
    result = grouped_output_project_bf16(
        _uniform_attention(
            batches=batches,
            sequence_length=sequence_length,
            local_groups=local_groups,
            head_dim=head_dim,
        ),
        _uniform_weights(
            local_groups=local_groups,
            output_rank=output_rank,
            head_dim=head_dim,
        ),
        local_group_count=local_groups,
        tensor_parallel_rank=1,
    )
    counters = result.counters
    input_values = batches * sequence_length * local_groups * 8 * head_dim
    weight_values = local_groups * output_rank * 8 * head_dim
    outputs = batches * sequence_length * local_groups * output_rank
    products = outputs * 8 * head_dim
    assert counters.batch_count == batches
    assert counters.sequence_length == sequence_length
    assert counters.tensor_parallel_world_size == 4
    assert counters.tensor_parallel_rank == 1
    assert counters.local_group_count == local_groups
    assert counters.local_head_count == 16
    assert counters.heads_per_group == 8
    assert counters.head_dim == head_dim
    assert counters.group_input_features == 8 * head_dim
    assert counters.declared_output_rank == output_rank
    assert counters.evaluated_output_ranks_per_group == output_rank
    assert counters.complete_output is True
    assert counters.attention_input_bf16_values == input_values
    assert counters.canonical_weight_bf16_values == weight_values
    assert counters.attention_group_reshape_values == input_values
    assert counters.weight_group_reshape_values == weight_values
    assert counters.exact_product_accumulates == products
    assert counters.binary32_accumulation_roundings == products
    assert counters.output_bf16_conversions == outputs
    assert counters.output_bf16_saturated_values == 0
    assert counters.evaluated_grouped_output_bf16_values == outputs
    assert counters.evaluated_flattened_output_bf16_values == outputs
    assert counters.declared_full_output_bf16_values == outputs
    assert counters.transaction_commits == 1


def test_randomized_projection_matches_independent_scalar_assembly() -> None:
    rng = random.Random(0x4752_4F55_5045_444F)
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
    for _ in range(200):
        local_groups = rng.choice((1, 2, 4))
        batch_count = rng.randint(1, 2)
        sequence_length = rng.randint(1, 3)
        head_dim = rng.randint(1, 6)
        output_rank = rng.randint(1, 5)
        attention = tuple(
            tuple(
                tuple(
                    tuple(rng.choice(palette) for _ in range(head_dim))
                    for _ in range(local_groups * OFFICIAL_HEADS_PER_GROUP)
                )
                for _ in range(sequence_length)
            )
            for _ in range(batch_count)
        )
        weights = tuple(
            tuple(
                rng.choice(palette) for _ in range(OFFICIAL_HEADS_PER_GROUP * head_dim)
            )
            for _ in range(local_groups * output_rank)
        )
        observed = grouped_output_project_bf16(
            attention,
            weights,
            local_group_count=local_groups,
        )

        expected_grouped = []
        saturation_count = 0
        for sequence in attention:
            expected_sequence = []
            for heads in sequence:
                expected_groups = []
                for group in range(local_groups):
                    input_row = _flatten_group_heads(heads, group)
                    output_row = []
                    for output in range(output_rank):
                        code, saturated = _independent_dot_to_bf16(
                            input_row,
                            weights[group * output_rank + output],
                        )
                        output_row.append(code)
                        saturation_count += int(saturated)
                    expected_groups.append(tuple(output_row))
                expected_sequence.append(tuple(expected_groups))
            expected_grouped.append(tuple(expected_sequence))
        expected_grouped_tuple = tuple(expected_grouped)
        assert observed.grouped_bf16_codes == expected_grouped_tuple
        assert observed.flattened_bf16_codes == tuple(
            tuple(
                tuple(code for group in groups for code in group) for groups in sequence
            )
            for sequence in expected_grouped_tuple
        )
        assert observed.counters.output_bf16_saturated_values == saturation_count


def test_all_caller_inputs_remain_unchanged_and_result_is_deeply_immutable() -> None:
    attention = [
        [
            [[_bf16(head + 1), _bf16(head + 2)] for head in range(8)],
        ],
    ]
    weights = [[[0] * 16][0]]
    weights[0][0] = _bf16(1)
    before_attention = deepcopy(attention)
    before_weights = deepcopy(weights)
    result = grouped_output_project_bf16(
        attention,
        weights,
        local_group_count=1,
    )
    assert attention == before_attention
    assert weights == before_weights
    assert type(result.grouped_bf16_codes) is tuple
    assert type(result.grouped_bf16_codes[0][0][0]) is tuple
    with pytest.raises(FrozenInstanceError):
        result.complete_output = False  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.flattened_bf16_codes[0][0][0] = 1  # type: ignore[index]


@pytest.mark.parametrize(
    "local_group_count",
    [True, False, 0, 3, 5, 6, 7, 9, 1.0, "1"],
)
def test_local_group_count_must_match_a_released_tp_partition(
    local_group_count: object,
) -> None:
    with pytest.raises(GroupedOutputReferenceError, match="exactly 1, 2, 4, or 8"):
        grouped_output_project_bf16(
            (),
            (),
            local_group_count=local_group_count,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad", [object(), "tensor", b"tensor", range(1)])
def test_tensors_must_be_exact_lists_or_tuples(bad: object) -> None:
    with pytest.raises(GroupedOutputReferenceError, match="exact list or tuple"):
        grouped_output_project_bf16(
            (),
            bad,
            local_group_count=1,
        )


def test_complete_weight_row_count_must_be_nonzero_divisible_and_bounded() -> None:
    attention = _uniform_attention(
        batches=1,
        sequence_length=1,
        local_groups=2,
        head_dim=1,
    )
    with pytest.raises(GroupedOutputReferenceError, match="nonzero multiple"):
        grouped_output_project_bf16(
            attention,
            (),
            local_group_count=2,
        )
    with pytest.raises(GroupedOutputReferenceError, match="nonzero multiple"):
        grouped_output_project_bf16(
            attention,
            ((0,) * 8,),
            local_group_count=2,
        )
    with pytest.raises(GroupedOutputReferenceError, match="inferred output rank"):
        grouped_output_project_bf16(
            _uniform_attention(
                batches=1,
                sequence_length=1,
                local_groups=1,
                head_dim=1,
            ),
            ((0,) * 8,) * (OFFICIAL_OUTPUT_RANK + 1),
            local_group_count=1,
        )


@pytest.mark.parametrize(
    ("attention", "match"),
    [
        ((), "batch extent"),
        (((),), "sequence extent"),
        (
            (
                (((0,),) * 8,),
                (((0,),) * 8, ((0,),) * 8),
            ),
            "sequence axis",
        ),
        (((((0,),) * 7,),), "exactly 8 local heads"),
        (((((0,),) * 9,),), "exactly 8 local heads"),
        ((((((),) + ((0,),) * 7),),), "head dimension"),
        (
            (((((0,), (0, 0)) + ((0,),) * 6),),),
            "head-dimension axis",
        ),
    ],
)
def test_attention_shape_validation_fails_closed(
    attention: object,
    match: str,
) -> None:
    with pytest.raises(GroupedOutputReferenceError, match=match):
        grouped_output_project_bf16(
            attention,
            ((0,) * 8,),
            local_group_count=1,
        )


def test_attention_batch_and_head_dimension_bounds_fail_closed() -> None:
    with pytest.raises(GroupedOutputReferenceError, match="batch extent"):
        grouped_output_project_bf16(
            _uniform_attention(
                batches=PINNED_MAX_BATCH_SIZE + 1,
                sequence_length=1,
                local_groups=1,
                head_dim=1,
            ),
            ((0,) * 8,),
            local_group_count=1,
        )
    too_wide_heads = ((0,) * (OFFICIAL_HEAD_DIM + 1),) * 8
    with pytest.raises(GroupedOutputReferenceError, match="head dimension"):
        grouped_output_project_bf16(
            ((too_wide_heads,),),
            ((0,) * (8 * (OFFICIAL_HEAD_DIM + 1)),),
            local_group_count=1,
        )


@pytest.mark.parametrize("illegal", [True, False, -1, 1 << 16, 0.0])
def test_attention_codes_require_exact_unsigned_16_bit_integers(
    illegal: object,
) -> None:
    attention = [
        [[([0] if head else [illegal]) for head in range(8)]],
    ]
    with pytest.raises(GroupedOutputReferenceError, match="16-bit BF16"):
        grouped_output_project_bf16(
            attention,
            ((0,) * 8,),
            local_group_count=1,
        )


@pytest.mark.parametrize("nonfinite", [0x7F80, 0xFF80, 0x7FC0, 0xFFFF])
def test_attention_rejects_every_bf16_nonfinite_class(nonfinite: int) -> None:
    attention = _uniform_attention(
        batches=1,
        sequence_length=1,
        local_groups=1,
        head_dim=1,
    )
    mutable = [[[list(row) for row in attention[0][0]]]]
    mutable[0][0][7][0] = nonfinite
    with pytest.raises(GroupedOutputReferenceError, match="finite BF16"):
        grouped_output_project_bf16(
            mutable,
            ((0,) * 8,),
            local_group_count=1,
        )


def test_integer_subclasses_are_rejected_as_codes() -> None:
    class IntegerSubclass(int):
        pass

    attention = [
        [[[IntegerSubclass(0)] if head == 0 else [0] for head in range(8)]],
    ]
    with pytest.raises(GroupedOutputReferenceError, match="16-bit BF16"):
        grouped_output_project_bf16(
            attention,
            ((0,) * 8,),
            local_group_count=1,
        )


def test_weight_shape_code_and_nonfinite_validation_fails_closed() -> None:
    attention = _uniform_attention(
        batches=1,
        sequence_length=1,
        local_groups=1,
        head_dim=1,
    )
    with pytest.raises(GroupedOutputReferenceError, match="exactly 8"):
        grouped_output_project_bf16(
            attention,
            ((0,) * 7,),
            local_group_count=1,
        )
    for illegal, match in (
        (True, "16-bit BF16"),
        (-1, "16-bit BF16"),
        (1 << 16, "16-bit BF16"),
        (0x7F80, "finite BF16"),
        (0x7FC0, "finite BF16"),
    ):
        row = [0] * 8
        row[-1] = illegal
        with pytest.raises(GroupedOutputReferenceError, match=match):
            grouped_output_project_bf16(
                attention,
                (row,),
                local_group_count=1,
            )


@pytest.mark.parametrize(
    ("selected", "match"),
    [
        ((), "at least one"),
        ((1, 0), "strictly increasing"),
        ((0, 0), "strictly increasing"),
        ((-1,), r"\[0, 3\]"),
        ((4,), r"\[0, 3\]"),
        ((True,), "integer"),
        ((1.0,), "integer"),
        (range(1), "exact list or tuple"),
    ],
)
def test_selected_output_rank_contract_fails_closed(
    selected: object,
    match: str,
) -> None:
    with pytest.raises(GroupedOutputReferenceError, match=match):
        grouped_output_project_selected_bf16(
            _uniform_attention(
                batches=1,
                sequence_length=1,
                local_groups=1,
                head_dim=1,
            ),
            ((0,) * 8,),
            local_group_count=1,
            declared_output_rank=4,
            selected_output_ranks=selected,
        )


@pytest.mark.parametrize("declared", [True, 0, 1025, 1.0, "4"])
def test_declared_output_rank_is_bounded_exact_integer(declared: object) -> None:
    with pytest.raises(GroupedOutputReferenceError, match="declared_output_rank"):
        grouped_output_project_selected_bf16(
            (),
            (),
            local_group_count=1,
            declared_output_rank=declared,  # type: ignore[arg-type]
            selected_output_ranks=(0,),
        )


@pytest.mark.parametrize("rank", [True, -1, 4, 1.0, "0"])
def test_tensor_parallel_rank_is_bounded_exact_integer(rank: object) -> None:
    with pytest.raises(GroupedOutputReferenceError, match="tensor_parallel_rank"):
        grouped_output_project_selected_bf16(
            (),
            (),
            local_group_count=2,
            declared_output_rank=1,
            selected_output_ranks=(0,),
            tensor_parallel_rank=rank,  # type: ignore[arg-type]
        )


def test_all_validation_finishes_before_overflowing_arithmetic() -> None:
    attention = _uniform_attention(
        batches=1,
        sequence_length=1,
        local_groups=1,
        head_dim=1,
        code=0x7F7F,
    )
    malformed_last_weight = [
        [_bf16(2)] * 8,
        [0] * 8,
    ]
    malformed_last_weight[-1][-1] = 0x7F80
    with pytest.raises(
        GroupedOutputReferenceError,
        match=r"weight_bf16_codes\[1\]\[7\] must be finite BF16",
    ):
        grouped_output_project_bf16(
            attention,
            malformed_last_weight,
            local_group_count=1,
        )


def _require_governed_torch(torch, device: str) -> None:
    if str(torch.__version__) != "2.10.0+cu128":
        pytest.skip("development observation is pinned to PyTorch 2.10.0+cu128")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    if device == "cuda" and torch.version.cuda != "12.8":
        pytest.skip("CUDA development observation is pinned to CUDA 12.8")


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_full_width_native_einsum_is_a_bounded_development_differential(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_torch(torch, device)
    rng = random.Random(0x4752_4F55_504E_4154)
    selected = (0, 1, 2, 3)

    def random_bf16() -> int:
        return (
            (rng.randrange(2) << 15)
            | (rng.randrange(117, 135) << 7)
            | rng.randrange(128)
        )

    attention = tuple(
        tuple(random_bf16() for _ in range(OFFICIAL_HEAD_DIM))
        for _ in range(OFFICIAL_HEADS_PER_GROUP)
    )
    weights = tuple(
        tuple(random_bf16() for _ in range(OFFICIAL_GROUP_INPUT_FEATURES))
        for _ in selected
    )
    expected = grouped_output_project_selected_bf16(
        ((attention,),),
        weights,
        local_group_count=1,
        declared_output_rank=OFFICIAL_OUTPUT_RANK,
        selected_output_ranks=selected,
    )

    attention_tensor = (
        torch.tensor(attention, dtype=torch.uint16)
        .view(torch.bfloat16)
        .to(device)
        .view(1, 1, 1, OFFICIAL_GROUP_INPUT_FEATURES)
    )
    weight_tensor = (
        torch.tensor(weights, dtype=torch.uint16)
        .view(torch.bfloat16)
        .to(device)
        .view(1, len(selected), OFFICIAL_GROUP_INPUT_FEATURES)
    )
    observed = torch.einsum(
        "bsgd,grd->bsgr",
        attention_tensor,
        weight_tensor,
    )
    assert observed.dtype == torch.bfloat16
    observed_codes = tuple(
        int(code) for code in observed.view(torch.uint16).reshape(-1).cpu().tolist()
    )
    expected_codes = expected.flattened_bf16_codes[0][0]
    assert all(
        observed_code == expected_code
        or (
            observed_code >> 15 == expected_code >> 15
            and abs(observed_code - expected_code) <= 8
        )
        for observed_code, expected_code in zip(
            observed_codes,
            expected_codes,
            strict=True,
        )
    )


def test_cached_official_mp4_weight_selected_rows_match_independent_oracle() -> None:
    path = (
        Path.home()
        / ".cache/opentallas/deepseek-v4-flash-0731/canonical-mp4"
        / "ranks/rank-000/layers.0.attn.wo_a.weight.bin"
    )
    if not path.is_file():
        pytest.skip("optional canonical MP4 layer-0 wo_a payload is unavailable")
    payload = path.read_bytes()
    assert len(payload) == 2048 * OFFICIAL_GROUP_INPUT_FEATURES * 2
    assert sha256(payload).hexdigest() == OFFICIAL_LAYER0_MP4_BF16_WEIGHT_SHA256[0]

    selected = (0, OFFICIAL_OUTPUT_RANK - 1)
    weights = []
    for group in range(2):
        for rank in selected:
            row = group * OFFICIAL_OUTPUT_RANK + rank
            start = row * OFFICIAL_GROUP_INPUT_FEATURES * 2
            weights.append(
                struct.unpack_from(
                    f"<{OFFICIAL_GROUP_INPUT_FEATURES}H",
                    payload,
                    start,
                )
            )
    rng = random.Random(0x4752_4F55_504F_4646)
    palette = (
        0,
        _bf16(Fraction(1, 8)),
        _bf16(Fraction(-1, 8)),
        _bf16(1),
        _bf16(-1),
        _bf16(2),
        _bf16(-2),
    )
    attention = tuple(
        tuple(rng.choice(palette) for _ in range(OFFICIAL_HEAD_DIM))
        for _ in range(2 * OFFICIAL_HEADS_PER_GROUP)
    )
    result = grouped_output_project_selected_bf16(
        ((attention,),),
        tuple(weights),
        local_group_count=2,
        declared_output_rank=OFFICIAL_OUTPUT_RANK,
        selected_output_ranks=selected,
    )
    expected = []
    for group in range(2):
        input_row = _flatten_group_heads(attention, group)
        expected.append(
            tuple(
                _independent_dot_to_bf16(input_row, weights[group * 2 + row])[0]
                for row in range(2)
            )
        )
    assert result.grouped_bf16_codes == ((tuple(expected),),)
