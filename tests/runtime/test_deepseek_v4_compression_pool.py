from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import random

import pytest

from runtime.reference.compression_pool import (
    COMPRESS_POOL_NUMERIC_PROFILE,
    EXCLUDED_DOWNSTREAM_OPERATIONS,
    F32_NEGATIVE_INFINITY,
    INFERENCE_CONFIG_SHA256,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    MODEL_SOURCE_PATH,
    MODEL_SOURCE_SHA256,
    PINNED_INDEX_HEAD_DIM,
    PINNED_INDEX_RATIO4_SITE_COUNT,
    PINNED_MAIN_HEAD_DIM,
    PINNED_MAIN_RATIO4_SITE_COUNT,
    PINNED_MAIN_RATIO128_SITE_COUNT,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    CompressionPoolReferenceError,
    compress_pool_decode_window_f32,
    compress_pool_f32,
    compress_pool_prefill_f32,
)
from runtime.reference.formats import decode_binary32, encode_binary32_rne


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _uniform_projected(
    *,
    batches: int,
    sequence_length: int,
    width: int,
    code: int = 0,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    row = (code,) * width
    sequence = (row,) * sequence_length
    return (sequence,) * batches


def _uniform_ape(
    ratio: int,
    width: int,
    code: int = 0,
) -> tuple[tuple[int, ...], ...]:
    return ((code,) * width,) * ratio


def _direct_ratio4(
    *,
    head_dim: int = PINNED_INDEX_HEAD_DIM,
    batches: int = 1,
    groups: int = 1,
    padded_first_group: bool = True,
) -> tuple[list[list[list[list[int]]]], list[list[list[list[int]]]]]:
    kv: list[list[list[list[int]]]] = []
    scores: list[list[list[list[int]]]] = []
    for _ in range(batches):
        kv_groups: list[list[list[int]]] = []
        score_groups: list[list[list[int]]] = []
        for group in range(groups):
            kv_group = [[0] * head_dim for _ in range(8)]
            score_group = [[0] * head_dim for _ in range(8)]
            if padded_first_group and group == 0:
                for position in range(4):
                    score_group[position] = [F32_NEGATIVE_INFINITY] * head_dim
            kv_groups.append(kv_group)
            score_groups.append(score_group)
        kv.append(kv_groups)
        scores.append(score_groups)
    return kv, scores


def _direct_ratio128(
    *,
    batches: int = 1,
    groups: int = 1,
) -> tuple[list[list[list[list[int]]]], list[list[list[list[int]]]]]:
    kv_group = [[0] * PINNED_MAIN_HEAD_DIM for _ in range(128)]
    score_group = [[0] * PINNED_MAIN_HEAD_DIM for _ in range(128)]
    return (
        [[deepcopy(kv_group) for _ in range(groups)] for _ in range(batches)],
        [[deepcopy(score_group) for _ in range(groups)] for _ in range(batches)],
    )


def _value(code: int) -> Fraction:
    decoded = decode_binary32(code)
    assert decoded.finite and decoded.value is not None
    return decoded.value


def _oracle_add(left: int, right: int) -> int:
    return encode_binary32_rne(_value(left) + _value(right))


def _oracle_multiply(left: int, right: int) -> int:
    return encode_binary32_rne(_value(left) * _value(right))


def _oracle_divide(numerator: int, denominator: int) -> int:
    return encode_binary32_rne(_value(numerator) / _value(denominator))


def _oracle_balanced_sum(codes: tuple[int, ...]) -> int:
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _oracle_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


_EXP_ORACLE_CACHE: dict[tuple[int, int], int] = {}


def _decimal_exp_code(code: int, precision: int) -> int:
    key = (code, precision)
    if key in _EXP_ORACLE_CACHE:
        return _EXP_ORACLE_CACHE[key]
    value = _value(code)
    with localcontext() as context:
        context.prec = precision
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        approximation = decimal_value.exp()
    rounded = encode_binary32_rne(Fraction(approximation))
    _EXP_ORACLE_CACHE[key] = rounded
    return rounded


def _oracle_exp(code: int) -> int:
    at_160_digits = _decimal_exp_code(code, 160)
    at_260_digits = _decimal_exp_code(code, 260)
    assert at_160_digits == at_260_digits
    return at_160_digits


def _oracle_pool_group(
    kv_group: tuple[tuple[int, ...], ...],
    score_group: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    pool_axis = len(kv_group)
    head_dim = len(kv_group[0])
    probability_rows = [[] for _ in range(pool_axis)]
    output: list[int] = []
    for column in range(head_dim):
        finite_scores = tuple(
            score_group[position][column]
            for position in range(pool_axis)
            if score_group[position][column] != F32_NEGATIVE_INFINITY
        )
        maximum = finite_scores[0]
        for score in finite_scores[1:]:
            if _value(score) > _value(maximum):
                maximum = score
        exponentials: list[int] = []
        for position in range(pool_axis):
            score = score_group[position][column]
            if score == F32_NEGATIVE_INFINITY:
                exponentials.append(0)
            else:
                delta = encode_binary32_rne(_value(score) - _value(maximum))
                exponentials.append(_oracle_exp(delta))
        denominator = _oracle_balanced_sum(tuple(exponentials))
        probabilities = tuple(
            _oracle_divide(code, denominator) for code in exponentials
        )
        products = tuple(
            _oracle_multiply(kv_group[position][column], probabilities[position])
            for position in range(pool_axis)
        )
        output.append(_oracle_balanced_sum(products))
        for position, probability in enumerate(probabilities):
            probability_rows[position].append(probability)
    return tuple(output), tuple(tuple(row) for row in probability_rows)


def _source_extracted_overlap_prefill(
    kv: tuple[tuple[tuple[int, ...], ...], ...],
    scores: tuple[tuple[tuple[int, ...], ...], ...],
    ape: tuple[tuple[int, ...], ...],
) -> tuple[
    tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
    tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
]:
    ratio = 4
    head_dim = len(kv[0][0]) // 2
    cutoff = len(kv[0]) - len(kv[0]) % ratio
    group_count = cutoff // ratio
    zero = (0,) * head_dim
    negative_infinity = (F32_NEGATIVE_INFINITY,) * head_dim
    output_kv = []
    output_scores = []
    for batch_index in range(len(kv)):
        biased = tuple(
            tuple(
                _oracle_add(score, bias)
                for score, bias in zip(
                    scores[batch_index][position],
                    ape[position % ratio],
                    strict=True,
                )
            )
            for position in range(cutoff)
        )
        batch_kv = []
        batch_scores = []
        for group_index in range(group_count):
            current = group_index * ratio
            if group_index == 0:
                kv_rows = [zero] * ratio
                score_rows = [negative_infinity] * ratio
            else:
                previous = current - ratio
                kv_rows = [
                    kv[batch_index][previous + phase][:head_dim]
                    for phase in range(ratio)
                ]
                score_rows = [
                    biased[previous + phase][:head_dim] for phase in range(ratio)
                ]
            kv_rows.extend(
                kv[batch_index][current + phase][head_dim:] for phase in range(ratio)
            )
            score_rows.extend(
                biased[current + phase][head_dim:] for phase in range(ratio)
            )
            batch_kv.append(tuple(kv_rows))
            batch_scores.append(tuple(score_rows))
        output_kv.append(tuple(batch_kv))
        output_scores.append(tuple(batch_scores))
    return tuple(output_kv), tuple(output_scores)


def test_compress_pool_is_pinned_to_the_official_release_and_profiles() -> None:
    assert MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert MODEL_SOURCE_PATH == "inference/model.py"
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert COMPRESS_POOL_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_compress_pool_f32.v1"
    )
    assert PINNED_MAIN_RATIO4_SITE_COUNT == 21
    assert PINNED_INDEX_RATIO4_SITE_COUNT == 21
    assert PINNED_MAIN_RATIO128_SITE_COUNT == 20
    assert PINNED_MAX_BATCH_SIZE == 4
    assert PINNED_MAX_POSITION == 1_048_576


def test_production_reference_has_no_host_float_or_framework_dependency() -> None:
    source_path = (
        Path(__file__).parents[2] / "runtime" / "reference" / "compression_pool.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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


def test_nonclaims_keep_pooling_separate_from_state_and_system_evidence() -> None:
    assert set(EXCLUDED_DOWNSTREAM_OPERATIONS) == {
        "compressor_state_mutation",
        "rms_normalization",
        "rotary_embedding",
        "activation_qdq",
        "compressed_cache_write",
        "compiler_lowering",
        "service_engine_execution",
        "schedule_cycles_ppa",
    }


def test_ratio4_first_prefill_group_applies_exact_overlap_fill() -> None:
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    kv = tuple(
        ((_f32(position + 1),) * head_dim + (_f32(10 + position),) * head_dim)
        for position in range(4)
    )
    scores = _uniform_projected(
        batches=1,
        sequence_length=4,
        width=width,
    )
    result = compress_pool_prefill_f32(
        (kv,),
        scores,
        _uniform_ape(4, width),
        ratio=4,
    )
    assert result is not None
    assert result.input_kind == "prefill"
    assert result.shape_profile == "index_ratio4"
    assert result.pool_kv_f32_codes[0][0][:4] == ((0,) * head_dim,) * 4
    assert (
        result.pool_score_f32_codes[0][0][:4]
        == ((F32_NEGATIVE_INFINITY,) * head_dim,) * 4
    )
    assert result.pool_kv_f32_codes[0][0][4:] == tuple(
        (_f32(10 + position),) * head_dim for position in range(4)
    )
    assert result.softmax_probability_f32_codes[0][0][:4] == ((0,) * head_dim,) * 4
    assert (
        result.softmax_probability_f32_codes[0][0][4:]
        == ((_f32(Fraction(1, 4)),) * head_dim,) * 4
    )
    assert result.pooled_f32_codes == (((_f32(Fraction(23, 2)),) * head_dim,),)


def test_ratio4_second_prefill_group_uses_previous_first_and_current_second_half() -> (
    None
):
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    sequence = tuple(
        (_f32(position + 1),) * head_dim + (_f32(11 + position),) * head_dim
        for position in range(8)
    )
    result = compress_pool_prefill_f32(
        (sequence,),
        _uniform_projected(
            batches=1,
            sequence_length=8,
            width=width,
        ),
        _uniform_ape(4, width),
        ratio=4,
    )
    assert result is not None
    assert result.pool_kv_f32_codes[0][1] == tuple(
        (_f32(position + 1),) * head_dim for position in range(4)
    ) + tuple((_f32(15 + position),) * head_dim for position in range(4))
    # (1+2+3+4+15+16+17+18) / 8 = 19/2.
    assert result.pooled_f32_codes[0][1] == (_f32(Fraction(19, 2)),) * head_dim


def test_ape_addition_precedes_overlap_half_selection_and_rounds_once() -> None:
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    kv = _uniform_projected(
        batches=1,
        sequence_length=8,
        width=width,
    )
    scores = (
        tuple(
            (_f32(position),) * head_dim + (_f32(2 * position),) * head_dim
            for position in range(8)
        ),
    )
    ape = tuple(
        (_f32(100 + phase),) * head_dim + (_f32(-10 - phase),) * head_dim
        for phase in range(4)
    )
    result = compress_pool_prefill_f32(kv, scores, ape, ratio=4)
    assert result is not None
    assert result.pool_score_f32_codes[0][0][4:] == tuple(
        (_f32(phase - 10),) * head_dim for phase in range(4)
    )
    assert result.pool_score_f32_codes[0][1][:4] == tuple(
        (_f32(100 + 2 * phase),) * head_dim for phase in range(4)
    )
    assert result.pool_score_f32_codes[0][1][4:] == tuple(
        (_f32(-2 + phase),) * head_dim for phase in range(4)
    )

    half_ulp_at_one = _f32(Fraction(1, 1 << 24))
    tie_scores = _uniform_projected(
        batches=1,
        sequence_length=4,
        width=width,
        code=_f32(1),
    )
    tie_result = compress_pool_prefill_f32(
        _uniform_projected(
            batches=1,
            sequence_length=4,
            width=width,
        ),
        projected_score_f32_codes=tie_scores,
        ape_f32_codes=_uniform_ape(4, width, half_ulp_at_one),
        ratio=4,
    )
    assert tie_result is not None
    assert tie_result.pool_score_f32_codes[0][0][4][0] == _f32(1)


def test_prefill_trailing_incomplete_group_is_not_pooled() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    result = compress_pool_prefill_f32(
        _uniform_projected(batches=2, sequence_length=7, width=width),
        _uniform_projected(batches=2, sequence_length=7, width=width),
        _uniform_ape(4, width),
        ratio=4,
    )
    assert result is not None
    assert result.source_sequence_length == 7
    assert result.prefill_cutoff == 4
    assert result.prefill_remainder == 3
    assert len(result.pooled_f32_codes[0]) == 1
    assert result.counters.source_projected_rows == 8
    assert result.counters.score_ape_additions == 2 * 4 * width


def test_short_prefill_validates_every_input_then_returns_none() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    assert (
        compress_pool_prefill_f32(
            _uniform_projected(batches=1, sequence_length=3, width=width),
            _uniform_projected(batches=1, sequence_length=3, width=width),
            _uniform_ape(4, width),
            ratio=4,
        )
        is None
    )
    poisoned = [
        [list(row) for row in sequence]
        for sequence in _uniform_projected(
            batches=1,
            sequence_length=3,
            width=width,
        )
    ]
    poisoned[0][2][-1] = 0x7F800000
    with pytest.raises(CompressionPoolReferenceError, match="finite binary32"):
        compress_pool_prefill_f32(
            _uniform_projected(batches=1, sequence_length=3, width=width),
            poisoned,
            _uniform_ape(4, width),
            ratio=4,
        )


def test_ratio128_full_official_pool_shape_is_exact_and_uniform() -> None:
    ratio = 128
    width = PINNED_MAIN_HEAD_DIM
    result = compress_pool_prefill_f32(
        _uniform_projected(
            batches=1,
            sequence_length=ratio,
            width=width,
            code=_f32(2),
        ),
        _uniform_projected(
            batches=1,
            sequence_length=ratio,
            width=width,
        ),
        _uniform_ape(ratio, width),
        ratio=ratio,
    )
    assert result is not None
    assert result.shape_profile == "main_ratio128"
    assert result.head_dim == 512
    assert result.projected_width == 512
    assert (
        result.softmax_probability_f32_codes[0][0]
        == ((_f32(Fraction(1, 128)),) * width,) * ratio
    )
    assert result.pooled_f32_codes == (((_f32(2),) * width,),)
    assert result.counters.pool_axis == 128
    assert result.counters.softmax_vectors == 512
    assert result.counters.softmax_exp_evaluations == 128 * 512
    assert result.counters.softmax_reduction_additions == 127 * 512


def test_ratio4_full_main_shape_and_maximum_batch_are_admitted() -> None:
    width = 2 * PINNED_MAIN_HEAD_DIM
    result = compress_pool_prefill_f32(
        _uniform_projected(
            batches=PINNED_MAX_BATCH_SIZE,
            sequence_length=4,
            width=width,
            code=_f32(3),
        ),
        _uniform_projected(
            batches=PINNED_MAX_BATCH_SIZE,
            sequence_length=4,
            width=width,
        ),
        _uniform_ape(4, width),
        ratio=4,
    )
    assert result is not None
    assert result.shape_profile == "main_ratio4"
    assert result.counters.batch_count == PINNED_MAX_BATCH_SIZE
    assert (
        result.pooled_f32_codes
        == (((_f32(3),) * PINNED_MAIN_HEAD_DIM,),) * PINNED_MAX_BATCH_SIZE
    )


def test_direct_pool_contract_round_trips_prefill_handoff_axes() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    prefill = compress_pool_prefill_f32(
        _uniform_projected(
            batches=2,
            sequence_length=8,
            width=width,
            code=_f32(7),
        ),
        _uniform_projected(batches=2, sequence_length=8, width=width),
        _uniform_ape(4, width),
        ratio=4,
    )
    assert prefill is not None
    direct = compress_pool_f32(
        prefill.pool_kv_f32_codes,
        prefill.pool_score_f32_codes,
        ratio=4,
    )
    assert direct.input_kind == "direct"
    assert direct.pool_kv_f32_codes == prefill.pool_kv_f32_codes
    assert direct.pool_score_f32_codes == prefill.pool_score_f32_codes
    assert direct.softmax_probability_f32_codes == (
        prefill.softmax_probability_f32_codes
    )
    assert direct.pooled_f32_codes == prefill.pooled_f32_codes


def test_complete_decode_windows_equal_corresponding_prefill_groups() -> None:
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    first = tuple(
        (_f32(position + 1),) * head_dim + (_f32(10 + position),) * head_dim
        for position in range(4)
    )
    second = tuple(
        (_f32(position + 5),) * head_dim + (_f32(14 + position),) * head_dim
        for position in range(4)
    )
    scores = _uniform_projected(
        batches=1,
        sequence_length=4,
        width=width,
    )
    ape = _uniform_ape(4, width)
    prefill = compress_pool_prefill_f32(
        ((first + second),),
        _uniform_projected(
            batches=1,
            sequence_length=8,
            width=width,
        ),
        ape,
        ratio=4,
    )
    assert prefill is not None
    first_decode = compress_pool_decode_window_f32(
        (first,),
        scores,
        ape,
        ratio=4,
    )
    second_decode = compress_pool_decode_window_f32(
        (second,),
        scores,
        ape,
        ratio=4,
        previous_kv_f32_codes=(first,),
        previous_score_f32_codes=scores,
    )
    assert first_decode.previous_window_present is False
    assert second_decode.previous_window_present is True
    assert first_decode.pool_kv_f32_codes[0][0] == prefill.pool_kv_f32_codes[0][0]
    assert second_decode.pool_kv_f32_codes[0][0] == prefill.pool_kv_f32_codes[0][1]
    assert first_decode.pooled_f32_codes[0][0] == prefill.pooled_f32_codes[0][0]
    assert second_decode.pooled_f32_codes[0][0] == prefill.pooled_f32_codes[0][1]


def test_ratio128_complete_decode_window_matches_prefill() -> None:
    ratio = 128
    width = PINNED_MAIN_HEAD_DIM
    kv = _uniform_projected(
        batches=1,
        sequence_length=ratio,
        width=width,
        code=_f32(-3),
    )
    scores = _uniform_projected(
        batches=1,
        sequence_length=ratio,
        width=width,
    )
    ape = _uniform_ape(ratio, width)
    prefill = compress_pool_prefill_f32(kv, scores, ape, ratio=ratio)
    decode = compress_pool_decode_window_f32(kv, scores, ape, ratio=ratio)
    assert prefill is not None
    assert decode.pool_kv_f32_codes == prefill.pool_kv_f32_codes
    assert decode.pool_score_f32_codes == prefill.pool_score_f32_codes
    assert decode.pooled_f32_codes == prefill.pooled_f32_codes


def test_stable_softmax_underflow_is_exact_positive_zero() -> None:
    kv, scores = _direct_ratio4(padded_first_group=False)
    for position in range(8):
        kv[0][0][position][0] = _f32(position + 1)
        scores[0][0][position][0] = _f32(0 if position == 0 else -200)
    result = compress_pool_f32(kv, scores, ratio=4)
    assert result.softmax_max_f32_codes[0][0][0] == _f32(0)
    assert result.softmax_probability_f32_codes[0][0][0][0] == _f32(1)
    assert (
        tuple(
            result.softmax_probability_f32_codes[0][0][position][0]
            for position in range(1, 8)
        )
        == (0,) * 7
    )
    assert result.pooled_f32_codes[0][0][0] == _f32(1)


def test_softmax_denominator_uses_the_frozen_balanced_tree() -> None:
    kv, scores = _direct_ratio4(padded_first_group=False)
    deltas = (0, 0, 0, 0, 0, 0, -1, -5)
    for position, delta in enumerate(deltas):
        scores[0][0][position] = [_f32(delta)] * PINNED_INDEX_HEAD_DIM
    result = compress_pool_f32(kv, scores, ratio=4)
    denominator = result.softmax_denominator_f32_codes[0][0][0]
    assert denominator == 0x40CBFCDE

    exponentials = tuple(_oracle_exp(_f32(delta)) for delta in deltas)
    left_fold = exponentials[0]
    for code in exponentials[1:]:
        left_fold = _oracle_add(left_fold, code)
    assert left_fold == 0x40CBFCDD
    assert denominator != left_fold


def test_weighted_reduction_uses_the_frozen_balanced_tree() -> None:
    kv, scores = _direct_ratio4(padded_first_group=False)
    large = _f32(1 << 100)
    values = (
        large,
        _f32(1),
        large ^ 0x80000000,
        _f32(1),
        _f32(1),
        _f32(1),
        _f32(1),
        _f32(1),
    )
    for position, code in enumerate(values):
        kv[0][0][position][0] = code
    result = compress_pool_f32(kv, scores, ratio=4)
    assert result.pooled_f32_codes[0][0][0] == _f32(Fraction(1, 2))

    probability = _f32(Fraction(1, 8))
    products = tuple(_oracle_multiply(code, probability) for code in values)
    left_fold = products[0]
    for product in products[1:]:
        left_fold = _oracle_add(left_fold, product)
    assert left_fold == _f32(Fraction(5, 8))
    assert result.pooled_f32_codes[0][0][0] != left_fold


def test_signed_zero_inputs_canonicalize_arithmetic_zero() -> None:
    kv, scores = _direct_ratio4(padded_first_group=False)
    kv[0][0][0][0] = 0x80000000
    scores[0][0][0][0] = 0x80000000
    result = compress_pool_f32(kv, scores, ratio=4)
    assert result.softmax_max_f32_codes[0][0][0] == 0x80000000
    assert result.softmax_probability_f32_codes[0][0][0][0] == _f32(Fraction(1, 8))
    assert result.pooled_f32_codes[0][0][0] == 0


def test_source_extracted_assembly_and_independent_decimal_oracle_match() -> None:
    rng = random.Random(0x434F_4D50_504F_4F4C)
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    kv_palette = tuple(_f32(value) for value in (-16, -3, -1, 0, 1, 2, 7, 15))
    score_palette = tuple(_f32(value) for value in (-5, -2, -1, 0, 1, 3))
    kv = (
        tuple(
            tuple(
                kv_palette[(position + column + rng.randrange(3)) % len(kv_palette)]
                for column in range(width)
            )
            for position in range(8)
        ),
    )
    scores = (
        tuple(
            tuple(
                score_palette[(2 * position + column) % len(score_palette)]
                for column in range(width)
            )
            for position in range(8)
        ),
    )
    ape = tuple(
        tuple(
            score_palette[(phase + 3 * column) % len(score_palette)]
            for column in range(width)
        )
        for phase in range(4)
    )
    expected_kv, expected_scores = _source_extracted_overlap_prefill(
        kv,
        scores,
        ape,
    )
    observed = compress_pool_prefill_f32(kv, scores, ape, ratio=4)
    assert observed is not None
    assert observed.pool_kv_f32_codes == expected_kv
    assert observed.pool_score_f32_codes == expected_scores

    expected_outputs = []
    expected_probabilities = []
    for group_kv, group_scores in zip(expected_kv[0], expected_scores[0], strict=True):
        output, probabilities = _oracle_pool_group(group_kv, group_scores)
        expected_outputs.append(output)
        expected_probabilities.append(probabilities)
    assert observed.pooled_f32_codes == (tuple(expected_outputs),)
    assert observed.softmax_probability_f32_codes == (tuple(expected_probabilities),)


def test_counters_reconcile_overlap_padding_and_all_numeric_work() -> None:
    head_dim = PINNED_INDEX_HEAD_DIM
    width = 2 * head_dim
    result = compress_pool_prefill_f32(
        _uniform_projected(batches=2, sequence_length=8, width=width),
        _uniform_projected(batches=2, sequence_length=8, width=width),
        _uniform_ape(4, width),
        ratio=4,
    )
    assert result is not None
    counters = result.counters
    output_values = 2 * 2 * head_dim
    pool_values = output_values * 8
    padding = 2 * 4 * head_dim
    assert counters.complete_group_count == 2
    assert counters.source_projected_rows == 16
    assert counters.source_projected_kv_f32_values == 16 * width
    assert counters.source_projected_score_f32_values == 16 * width
    assert counters.score_ape_additions == 16 * width
    assert counters.pool_kv_f32_values == pool_values
    assert counters.pool_score_f32_values == pool_values
    assert counters.overlap_zero_fill_values == padding
    assert counters.overlap_negative_infinity_fill_values == padding
    assert counters.softmax_vectors == output_values
    assert counters.softmax_max_comparisons == output_values * 7
    assert counters.softmax_finite_subtractions == pool_values - padding
    assert counters.softmax_exp_evaluations == pool_values - padding
    assert counters.softmax_negative_infinity_lanes == padding
    assert counters.softmax_reduction_additions == output_values * 7
    assert counters.softmax_probability_divisions == pool_values
    assert counters.weighted_multiplications == pool_values
    assert counters.weighted_reduction_additions == output_values * 7
    assert counters.pooled_output_f32_values == output_values
    assert counters.pooled_output_write_bytes == output_values * 4
    assert counters.transaction_commits == 1


def test_caller_inputs_are_unchanged_and_results_are_deeply_immutable() -> None:
    kv, scores = _direct_ratio4()
    before_kv = deepcopy(kv)
    before_scores = deepcopy(scores)
    result = compress_pool_f32(kv, scores, ratio=4)
    assert kv == before_kv
    assert scores == before_scores
    assert type(result.pool_kv_f32_codes) is tuple
    assert type(result.pool_kv_f32_codes[0][0][0]) is tuple
    with pytest.raises(FrozenInstanceError):
        result.ratio = 128  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.pooled_f32_codes[0][0][0] = 1  # type: ignore[index]


@pytest.mark.parametrize("ratio", [True, 0, 1, 3, 5, 127, 129, 4.0, "4"])
def test_ratio_must_be_an_exact_released_profile(ratio: object) -> None:
    kv, scores = _direct_ratio4()
    with pytest.raises(CompressionPoolReferenceError, match="exactly 4.*128"):
        compress_pool_f32(kv, scores, ratio=ratio)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda kv, scores: kv.clear(), "batch extent"),
        (
            lambda kv, scores: kv.extend(deepcopy(kv) for _ in range(4)),
            "batch extent",
        ),
        (lambda kv, scores: kv[0].clear(), "group extent"),
        (lambda kv, scores: kv[0][0].pop(), "exactly 8 pool positions"),
        (lambda kv, scores: kv[0][0][0].pop(), "rectangular"),
        (lambda kv, scores: kv[0][0][0].__setitem__(0, True), "32-bit"),
        (lambda kv, scores: kv[0][0][0].__setitem__(0, -1), "32-bit"),
        (lambda kv, scores: kv[0][0][0].__setitem__(0, 1 << 32), "32-bit"),
        (lambda kv, scores: kv[0][0][0].__setitem__(0, 0x7F800000), "finite"),
        (lambda kv, scores: kv[0][0][0].__setitem__(0, 0x7FC00000), "finite"),
        (lambda kv, scores: scores.pop(), "exactly 1 batches"),
        (lambda kv, scores: scores[0].clear(), "group axis"),
        (lambda kv, scores: scores[0][0].pop(), "exactly 8 pool positions"),
        (lambda kv, scores: scores[0][0][4].pop(), "rectangular"),
        (lambda kv, scores: scores[0][0][4].__setitem__(0, False), "32-bit"),
        (
            lambda kv, scores: scores[0][0][4].__setitem__(0, 0xFF800000),
            "only in the leading four",
        ),
        (
            lambda kv, scores: scores[0][0][0].__setitem__(0, 0),
            "sentinel must fill every value",
        ),
        (
            lambda kv, scores: kv[0][0][0].__setitem__(0, _f32(1)),
            "requires positive-zero KV",
        ),
    ],
)
def test_direct_overlap_contract_fails_closed(
    mutator,
    match: str,
) -> None:
    kv, scores = _direct_ratio4()
    mutator(kv, scores)
    with pytest.raises(CompressionPoolReferenceError, match=match):
        compress_pool_f32(kv, scores, ratio=4)


def test_overlap_padding_is_legal_only_for_group_zero() -> None:
    kv, scores = _direct_ratio4(groups=2)
    for position in range(4):
        scores[0][1][position] = [F32_NEGATIVE_INFINITY] * PINNED_INDEX_HEAD_DIM
    with pytest.raises(CompressionPoolReferenceError, match="only in the first"):
        compress_pool_f32(kv, scores, ratio=4)


def test_nonoverlap_rejects_negative_infinity_scores() -> None:
    kv, scores = _direct_ratio128()
    scores[0][0][0][0] = F32_NEGATIVE_INFINITY
    with pytest.raises(CompressionPoolReferenceError, match="finite binary32"):
        compress_pool_f32(kv, scores, ratio=128)


@pytest.mark.parametrize("bad_tensor", [object(), "tensor", b"tensor", range(1)])
def test_inputs_must_be_exact_lists_or_tuples(bad_tensor: object) -> None:
    _, scores = _direct_ratio4()
    with pytest.raises(CompressionPoolReferenceError, match="exact list or tuple"):
        compress_pool_f32(bad_tensor, scores, ratio=4)


def test_raw_codes_reject_floats_and_integer_subclasses() -> None:
    class IntegerSubclass(int):
        pass

    for illegal in (0.0, IntegerSubclass(0)):
        kv, scores = _direct_ratio4()
        kv[0][0][0][0] = illegal  # type: ignore[assignment]
        with pytest.raises(CompressionPoolReferenceError, match="32-bit"):
            compress_pool_f32(kv, scores, ratio=4)


def test_direct_group_extent_is_bounded_by_the_official_maximum_position() -> None:
    row = (0,) * PINNED_INDEX_HEAD_DIM
    group = (row,) * 8
    too_many_groups = (group,) * (PINNED_MAX_POSITION // 4 + 1)
    with pytest.raises(CompressionPoolReferenceError, match="group extent"):
        compress_pool_f32((too_many_groups,), (), ratio=4)


@pytest.mark.parametrize(
    ("ratio", "head_dim", "match"),
    [
        (4, 127, "128.*512"),
        (4, 129, "128.*512"),
        (4, 511, "128.*512"),
        (4, 513, "128.*512"),
        (128, 128, "exactly 512"),
        (128, 511, "exactly 512"),
        (128, 513, "exactly 512"),
    ],
)
def test_only_official_head_dimensions_are_admitted(
    ratio: int,
    head_dim: int,
    match: str,
) -> None:
    pool_axis = 8 if ratio == 4 else 128
    kv = ((((0,) * head_dim,) * pool_axis,),)
    scores = ((((0,) * head_dim,) * pool_axis,),)
    with pytest.raises(CompressionPoolReferenceError, match=match):
        compress_pool_f32(kv, scores, ratio=ratio)


def test_prefill_rejects_mismatched_and_nonfinite_projected_or_ape_inputs() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    kv = _uniform_projected(batches=1, sequence_length=4, width=width)
    scores = _uniform_projected(batches=1, sequence_length=4, width=width)
    ape = _uniform_ape(4, width)

    with pytest.raises(CompressionPoolReferenceError, match="exactly 1 batches"):
        compress_pool_prefill_f32(
            kv,
            _uniform_projected(batches=2, sequence_length=4, width=width),
            ape,
            ratio=4,
        )
    with pytest.raises(CompressionPoolReferenceError, match="sequence axis"):
        compress_pool_prefill_f32(
            kv,
            _uniform_projected(batches=1, sequence_length=3, width=width),
            ape,
            ratio=4,
        )
    with pytest.raises(CompressionPoolReferenceError, match="exactly 4 rows"):
        compress_pool_prefill_f32(kv, scores, ape[:-1], ratio=4)
    with pytest.raises(CompressionPoolReferenceError, match="exactly 256 values"):
        compress_pool_prefill_f32(
            kv,
            scores,
            (ape[0][:-1], *ape[1:]),
            ratio=4,
        )
    bad_ape = [list(row) for row in ape]
    bad_ape[3][-1] = 0x7F800000
    with pytest.raises(CompressionPoolReferenceError, match="finite binary32"):
        compress_pool_prefill_f32(kv, scores, bad_ape, ratio=4)


def test_score_plus_ape_and_stable_subtraction_overflow_poison_atomically() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    maximum = 0x7F7FFFFF
    with pytest.raises(
        CompressionPoolReferenceError,
        match=r"score \+ APE.*binary32 accumulation overflow",
    ):
        compress_pool_prefill_f32(
            _uniform_projected(batches=1, sequence_length=4, width=width),
            _uniform_projected(
                batches=1,
                sequence_length=4,
                width=width,
                code=maximum,
            ),
            _uniform_ape(4, width, maximum),
            ratio=4,
        )

    kv, scores = _direct_ratio4(padded_first_group=False)
    scores[0][0][0][0] = maximum
    scores[0][0][1][0] = 0xFF7FFFFF
    with pytest.raises(
        CompressionPoolReferenceError,
        match="compressor-pool arithmetic.*binary32 accumulation overflow",
    ):
        compress_pool_f32(kv, scores, ratio=4)


def test_decode_window_validates_complete_shape_and_previous_pair() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    current = _uniform_projected(batches=1, sequence_length=4, width=width)
    ape = _uniform_ape(4, width)
    with pytest.raises(CompressionPoolReferenceError, match="sequence axis"):
        compress_pool_decode_window_f32(
            _uniform_projected(batches=1, sequence_length=3, width=width),
            _uniform_projected(batches=1, sequence_length=3, width=width),
            ape,
            ratio=4,
        )
    with pytest.raises(CompressionPoolReferenceError, match="supplied together"):
        compress_pool_decode_window_f32(
            current,
            current,
            ape,
            ratio=4,
            previous_kv_f32_codes=current,
        )
    with pytest.raises(CompressionPoolReferenceError, match="does not accept"):
        width128 = PINNED_MAIN_HEAD_DIM
        ratio128 = _uniform_projected(
            batches=1,
            sequence_length=128,
            width=width128,
        )
        compress_pool_decode_window_f32(
            ratio128,
            ratio128,
            _uniform_ape(128, width128),
            ratio=128,
            previous_kv_f32_codes=ratio128,
            previous_score_f32_codes=ratio128,
        )


def test_decode_window_validates_previous_data_before_any_ape_arithmetic() -> None:
    width = 2 * PINNED_INDEX_HEAD_DIM
    current = _uniform_projected(batches=1, sequence_length=4, width=width)
    previous = [
        [list(row) for row in sequence]
        for sequence in _uniform_projected(
            batches=1,
            sequence_length=4,
            width=width,
        )
    ]
    previous[0][3][-1] = 0x7F800000
    # Current score + APE would overflow if reached, but complete transaction
    # validation must report the malformed preceding window first.
    with pytest.raises(
        CompressionPoolReferenceError,
        match=r"previous_kv_f32_codes.*finite binary32",
    ):
        compress_pool_decode_window_f32(
            current,
            _uniform_projected(
                batches=1,
                sequence_length=4,
                width=width,
                code=0x7F7FFFFF,
            ),
            _uniform_ape(4, width, 0x7F7FFFFF),
            ratio=4,
            previous_kv_f32_codes=previous,
            previous_score_f32_codes=current,
        )
