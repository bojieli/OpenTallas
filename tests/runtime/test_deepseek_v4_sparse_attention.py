from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    binary32_divide,
    decode_binary32,
    encode_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.sparse_attention import (
    KERNEL_SOURCE_SHA256,
    MODEL_SOURCE_SHA256,
    SPARSE_ATTENTION_BLOCK_SIZE,
    SPARSE_ATTENTION_HEAD_DIM,
    SPARSE_ATTENTION_HEADS,
    SPARSE_ATTENTION_KV_BYTES_PER_SELECTED_ROW,
    SPARSE_ATTENTION_NUMERIC_PROFILE,
    SPARSE_ATTENTION_SCALE_BINARY32,
    SPARSE_ATTENTION_SITE_COUNT,
    SparseAttentionCounters,
    SparseAttentionReferenceError,
    SparseAttentionResult,
    sparse_attention_bf16,
)
from runtime.reference.transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
    binary32_exp_general_rne_with_diagnostics,
)


def _bf16(value: int | Fraction) -> int:
    return encode_bf16_rne(value).code


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def test_sparse_attention_reference_is_bound_to_the_official_profile() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert KERNEL_SOURCE_SHA256 == (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    )
    assert SPARSE_ATTENTION_NUMERIC_PROFILE == (
        "opentallas.deepseek_v4_sparse_attention_numeric.v1"
    )
    assert SPARSE_ATTENTION_SITE_COUNT == 46
    assert SPARSE_ATTENTION_HEADS == 64
    assert SPARSE_ATTENTION_HEAD_DIM == 512
    assert SPARSE_ATTENTION_BLOCK_SIZE == 64
    assert SPARSE_ATTENTION_SCALE_BINARY32 == 0x3D3504F3
    assert decode_binary32(SPARSE_ATTENTION_SCALE_BINARY32).value == Fraction(
        11863283, 1 << 28
    )
    assert SPARSE_ATTENTION_KV_BYTES_PER_SELECTED_ROW == 512 * 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Fraction(-256), 0x00000000),
        (Fraction(-104), 0x00000000),
        (Fraction(-100), 0x0000001B),
        (Fraction(-2), 0x3E0A9555),
        (Fraction(-1), 0x3EBC5AB2),
        (Fraction(0), 0x3F800000),
        (Fraction(1), 0x402DF854),
        (Fraction(2), 0x40EC7326),
        (Fraction(10), 0x46AC14EE),
        (Fraction(80), 0x792ABBCE),
        (Fraction(88), 0x7EF882B7),
        (Fraction(887, 10), 0x7F7A37FC),
    ],
)
def test_general_cr32_exponential_has_fixed_known_answers(
    value: Fraction,
    expected: int,
) -> None:
    input_code = _f32(value)
    assert binary32_exp_general_rne(input_code) == expected
    assert binary32_exp_general_rne_with_diagnostics(input_code).code == expected


def test_general_cr32_exponential_matches_independent_decimal_corpus() -> None:
    rng = random.Random(0x5350_4152_5345_4558)
    input_codes = [_f32(Fraction(rng.randrange(-8_000, 8_001), 100)) for _ in range(64)]
    input_codes.extend((0x00000000, 0x80000000, _f32(-100), _f32(88)))

    for input_code in input_codes:
        value = decode_binary32(input_code).value
        assert value is not None
        with localcontext() as context:
            context.prec = 220
            context.rounding = ROUND_HALF_EVEN
            decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
            decimal_exp = context.exp(decimal_value)
        independently_rounded = encode_binary32_rne(Fraction(decimal_exp))
        assert binary32_exp_general_rne(input_code) == independently_rounded


@pytest.mark.parametrize(
    ("code", "match"),
    [
        (_f32(89), "overflows"),
        (_f32(256), "overflows"),
        (0x7F800000, "finite binary32"),
        (0x7FC00001, "finite binary32"),
        (True, "32-bit binary32"),
        (1 << 32, "32-bit binary32"),
    ],
)
def test_general_cr32_exponential_rejects_nonfinite_or_overflowing_results(
    code: object,
    match: str,
) -> None:
    with pytest.raises(TranscendentalReferenceError, match=match):
        binary32_exp_general_rne(code)  # type: ignore[arg-type]


def test_one_selected_row_fixes_sink_denominator_output_and_traffic() -> None:
    result = sparse_attention_bf16(
        ((((_bf16(1), _bf16(0)),),),),
        (((_bf16(2), _bf16(4)),),),
        (_f32(0),),
        (((0,),),),
        scale_binary32=_f32(1),
    )
    assert result == SparseAttentionResult(
        values=((((0x3FE1, 0x4061),),),),
        final_max_binary32_codes=(((0x40000000,),),),
        sink_exp_binary32_codes=(((0x3E0A9555,),),),
        final_denominator_binary32_codes=(((0x3F9152AB,),),),
        output_saturated_element_count=0,
        counters=SparseAttentionCounters(
            output_rows=1,
            source_blocks=1,
            query_bf16_values=2,
            query_bf16_read_bytes=4,
            attention_sink_binary32_reads=1,
            attention_sink_binary32_read_bytes=4,
            logical_index_slots=1,
            selected_index_int32_reads=1,
            selected_index_read_bytes=4,
            explicit_padding_slots=0,
            implicit_tail_padding_lanes=63,
            block_compute_lanes=64,
            valid_selected_rows=1,
            unique_selected_rows=1,
            duplicate_selected_rows=0,
            selected_kv_bf16_values=2,
            selected_kv_read_bytes=4,
            qk_valid_product_accumulates=2,
            qk_padding_product_lanes=126,
            score_scale_multiplies=64,
            online_rescale_exp_evaluations=1,
            score_exp_evaluations=64,
            score_reduction_adds=63,
            online_denominator_multiplies=1,
            online_denominator_adds=1,
            probability_bf16_conversions=64,
            output_rescale_multiplies=2,
            av_product_accumulates=128,
            sink_exp_evaluations=1,
            sink_denominator_adds=1,
            final_binary32_divides=2,
            output_bf16_conversions=2,
            output_bf16_write_bytes=4,
        ),
    )


def test_qk_accumulates_in_increasing_dimension_order_with_one_round_per_product_add() -> None:
    tiny = _bf16(Fraction(1, 1 << 12))
    result = sparse_attention_bf16(
        ((((_bf16(1), tiny, _bf16(-1)),),),),
        (((_bf16(1), tiny, _bf16(1)),),),
        (_f32(0),),
        (((0,),),),
        scale_binary32=_f32(1),
    )
    assert result.final_max_binary32_codes == (((0x00000000,),),)
    assert _f32(Fraction(1, 1 << 24)) == 0x33800000
    assert result.values == (
        (((_bf16(Fraction(1, 2)), _bf16(Fraction(1, 1 << 13)), _bf16(Fraction(1, 2))),),),
    )


def test_probability_is_converted_to_bf16_once_before_av_accumulation() -> None:
    result = sparse_attention_bf16(
        ((((_bf16(1), _bf16(0)),),),),
        (
            (
                (_bf16(-2), _bf16(-2)),
                (_bf16(Fraction(-15, 8)), _bf16(-1)),
            ),
        ),
        (_f32(0),),
        (((0, 1),),),
        scale_binary32=_f32(1),
    )
    assert result.values == ((((0xBEDE, 0xBEA9),),),)
    assert result.final_denominator_binary32_codes == (((0x410673FC,),),)

    # Keeping the first score probability in binary32 through AV would round
    # the second output to the adjacent code 0xbea8.  The official shared copy
    # to BF16 before AV therefore remains an observable architectural boundary.
    full_probability = 0x3F61EB51
    assert binary32_bits_to_bf16_rne(full_probability).code == 0x3F62
    full_probability_output = binary32_bits_to_bf16_rne(
        binary32_divide(0xC030F5A8, 0x410673FC)
    ).code
    assert full_probability_output == 0xBEA8


def test_two_blocks_rescale_prior_denominator_and_output_in_source_order() -> None:
    indices = tuple([0] * 64 + [1])
    result = sparse_attention_bf16(
        ((((_bf16(1),),),),),
        (((_bf16(1),), (_bf16(2),)),),
        (_f32(0),),
        ((indices,),),
        scale_binary32=_f32(1),
    )
    assert result.values == ((((0x3F84,),),),)
    assert result.final_max_binary32_codes == (((0x40000000,),),)
    assert result.sink_exp_binary32_codes == (((0x3E0A9555,),),)
    assert result.final_denominator_binary32_codes == (((0x41C56FDD,),),)
    assert result.counters.source_blocks == 2
    assert result.counters.valid_selected_rows == 65
    assert result.counters.unique_selected_rows == 2
    assert result.counters.duplicate_selected_rows == 63
    assert result.counters.selected_kv_read_bytes == 130
    assert result.counters.implicit_tail_padding_lanes == 63


def test_holes_and_duplicates_are_preserved_while_only_valid_slots_read_kv() -> None:
    first = (0, -1, 0, -1, 1, *([-1] * 59), 2, -1, 1, -1, 2, -1)
    assert len(first) == 70
    result = sparse_attention_bf16(
        ((((_bf16(1), _bf16(0)),),),),
        (
            (
                (_bf16(0), _bf16(1)),
                (_bf16(1), _bf16(2)),
                (_bf16(2), _bf16(3)),
            ),
        ),
        (_f32(0),),
        ((first,),),
        scale_binary32=_f32(1),
    )
    counters = result.counters
    assert counters.logical_index_slots == 70
    assert counters.selected_index_int32_reads == 70
    assert counters.selected_index_read_bytes == 280
    assert counters.valid_selected_rows == 6
    assert counters.unique_selected_rows == 3
    assert counters.duplicate_selected_rows == 3
    assert counters.explicit_padding_slots == 64
    assert counters.implicit_tail_padding_lanes == 58
    assert counters.block_compute_lanes == 128
    assert counters.selected_kv_bf16_values == 12
    assert counters.selected_kv_read_bytes == 24
    assert counters.qk_padding_product_lanes == (64 + 58) * 2


def test_an_all_padding_later_block_is_legal_and_numerically_neutral() -> None:
    query = ((((_bf16(1),),),),)
    kv = (((_bf16(2),),),)
    sink = (_f32(0),)
    one_block = sparse_attention_bf16(
        query,
        kv,
        sink,
        (((0, *([-1] * 63)),),),
        scale_binary32=_f32(1),
    )
    two_blocks = sparse_attention_bf16(
        query,
        kv,
        sink,
        (((0, *([-1] * 127)),),),
        scale_binary32=_f32(1),
    )
    assert two_blocks.values == one_block.values
    assert two_blocks.final_max_binary32_codes == one_block.final_max_binary32_codes
    assert (
        two_blocks.final_denominator_binary32_codes
        == one_block.final_denominator_binary32_codes
    )
    assert two_blocks.counters.source_blocks == 2
    assert two_blocks.counters.selected_kv_read_bytes == 2


def test_duplicate_selected_rows_are_not_deduplicated() -> None:
    query = ((((_bf16(1), _bf16(0)),),),)
    kv = (((_bf16(0), _bf16(1)), (_bf16(1), _bf16(4))),)
    sink = (_f32(0),)
    duplicate = sparse_attention_bf16(
        query,
        kv,
        sink,
        (((0, 0, 1),),),
        scale_binary32=_f32(1),
    )
    deduplicated = sparse_attention_bf16(
        query,
        kv,
        sink,
        (((0, -1, 1),),),
        scale_binary32=_f32(1),
    )
    assert duplicate.values != deduplicated.values
    assert duplicate.counters.valid_selected_rows == 3
    assert duplicate.counters.unique_selected_rows == 2
    assert duplicate.counters.duplicate_selected_rows == 1
    assert duplicate.counters.selected_kv_read_bytes == 12
    assert deduplicated.counters.selected_kv_read_bytes == 8


def test_shape_generalization_preserves_exact_counter_algebra() -> None:
    query = tuple(
        tuple(
            tuple(tuple(_bf16(1) for _ in range(3)) for _ in range(2))
            for _ in range(2)
        )
        for _ in range(2)
    )
    kv = tuple(
        tuple(tuple(_bf16(row + 1) for _ in range(3)) for row in range(4))
        for _ in range(2)
    )
    indices = (
        ((0, 1, -1), (2, 2, 3)),
        ((1, -1, 0), (3, -1, -1)),
    )
    result = sparse_attention_bf16(
        query,
        kv,
        (_f32(0), _f32(1)),
        indices,
        scale_binary32=_f32(Fraction(1, 2)),
    )
    counters = result.counters
    assert len(result.values) == 2
    assert len(result.values[0]) == 2
    assert len(result.values[0][0]) == 2
    assert len(result.values[0][0][0]) == 3
    assert counters.output_rows == 4
    assert counters.query_bf16_values == 24
    assert counters.query_bf16_read_bytes == 48
    assert counters.logical_index_slots == 12
    assert counters.valid_selected_rows == 8
    assert counters.unique_selected_rows == 7
    assert counters.duplicate_selected_rows == 1
    assert counters.selected_kv_bf16_values == 24
    assert counters.selected_kv_read_bytes == 48
    assert counters.qk_valid_product_accumulates == 48
    assert counters.final_binary32_divides == 24
    assert counters.output_bf16_write_bytes == 48


def test_sink_exponential_overflow_poisons_the_complete_command() -> None:
    with pytest.raises(SparseAttentionReferenceError, match="exponential overflows"):
        sparse_attention_bf16(
            ((((_bf16(-1),),),),),
            (((_bf16(100),),),),
            (_f32(100),),
            (((0,),),),
            scale_binary32=_f32(1),
        )


_VALID_QUERY = [[[[0]]]]
_VALID_KV = [[[0]]]
_VALID_SINK = [0]
_VALID_INDICES = [[[0]]]


@pytest.mark.parametrize(
    ("query", "kv", "sink", "indices", "scale", "match"),
    [
        (object(), _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "sequence"),
        ([], _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "one batch"),
        ([[[]]], _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "one head"),
        ([[[[]]]], _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "one value"),
        (
            [[[[0]]], [[[0], [0]]]],
            [[[0]], [[0]]],
            _VALID_SINK,
            [[[0]], [[0]]],
            _f32(1),
            "rectangular rank-4",
        ),
        ([[[[True]]]], _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "16-bit BF16"),
        ([[[[0x7F80]]]], _VALID_KV, _VALID_SINK, _VALID_INDICES, _f32(1), "finite BF16"),
        (_VALID_QUERY, [], _VALID_SINK, _VALID_INDICES, _f32(1), "batch count"),
        (_VALID_QUERY, [[]], _VALID_SINK, _VALID_INDICES, _f32(1), "one row"),
        (_VALID_QUERY, [[[0, 0]]], _VALID_SINK, _VALID_INDICES, _f32(1), "dimension 1"),
        (_VALID_QUERY, [[[0x7FC0]]], _VALID_SINK, _VALID_INDICES, _f32(1), "finite BF16"),
        (_VALID_QUERY, _VALID_KV, object(), _VALID_INDICES, _f32(1), "sequence"),
        (_VALID_QUERY, _VALID_KV, [], _VALID_INDICES, _f32(1), "length"),
        (_VALID_QUERY, _VALID_KV, [True], _VALID_INDICES, _f32(1), "binary32"),
        (_VALID_QUERY, _VALID_KV, [0x7F800000], _VALID_INDICES, _f32(1), "finite binary32"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, object(), _f32(1), "sequence"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [], _f32(1), "batch count"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [[[]]], _f32(1), "one slot"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [[[True]]], _f32(1), "INT32"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [[[-2]]], _f32(1), "INT32"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [[[1 << 31]]], _f32(1), "INT32"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, [[[1]]], _f32(1), "outside 1 KV"),
        (
            _VALID_QUERY,
            _VALID_KV,
            _VALID_SINK,
            [[[*([-1] * 64), 0]]],
            _f32(1),
            "first 64-slot",
        ),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, _VALID_INDICES, True, "binary32"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, _VALID_INDICES, 0, "greater than zero"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, _VALID_INDICES, 0xBF800000, "greater than zero"),
        (_VALID_QUERY, _VALID_KV, _VALID_SINK, _VALID_INDICES, 0x7F800000, "finite binary32"),
    ],
)
def test_sparse_attention_rejects_malformed_or_nonfinite_inputs(
    query: object,
    kv: object,
    sink: object,
    indices: object,
    scale: object,
    match: str,
) -> None:
    with pytest.raises(SparseAttentionReferenceError, match=match):
        sparse_attention_bf16(  # type: ignore[arg-type]
            query,
            kv,
            sink,
            indices,
            scale_binary32=scale,
        )


def _governed_differential_fixture() -> tuple[object, ...]:
    rng = random.Random(0x5350_4152_5345_4456)
    batch_size = 2
    sequence_length = 2
    head_count = 3
    head_dim = 8
    kv_rows = 10

    query = tuple(
        tuple(
            tuple(
                tuple(_bf16(Fraction(rng.randrange(-8, 9), 8)) for _ in range(head_dim))
                for _ in range(head_count)
            )
            for _ in range(sequence_length)
        )
        for _ in range(batch_size)
    )
    kv = tuple(
        tuple(
            tuple(_bf16(Fraction(rng.randrange(-8, 9), 8)) for _ in range(head_dim))
            for _ in range(kv_rows)
        )
        for _ in range(batch_size)
    )
    patterns = (
        (0, 1, 2, -1, 2, *([-1] * 59), 3, 4, 5, 6, 7, 8),
        (1, 2, 3, 4, *([-1] * 60), 5, 6, -1, 7, 8, 9),
        (9, -1, 8, 7, 7, *([-1] * 59), 6, 5, 4, -1, 3, 2),
        (4, 0, -1, 1, *([-1] * 60), 2, 3, 4, 5, -1, 6),
    )
    assert all(len(pattern) == 70 for pattern in patterns)
    indices = (
        (patterns[0], patterns[1]),
        (patterns[2], patterns[3]),
    )
    sink_values = (Fraction(1, 4), Fraction(-1, 2), Fraction(1, 8))
    sinks = tuple(_f32(value) for value in sink_values)
    return query, kv, sinks, indices, sink_values


def _require_governed_development_stack(torch, device: str) -> None:
    if str(torch.__version__) != "2.10.0+cu128":
        pytest.skip("development observation is pinned to PyTorch 2.10.0+cu128")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")
    if device == "cuda" and (
        torch.version.cuda != "12.8" or torch.cuda.get_device_capability() != (12, 0)
    ):
        pytest.skip("CUDA development observation is pinned to CUDA 12.8 and SM120")


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_sparse_attention_matches_bounded_source_structure_differential(
    device: str,
) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    _require_governed_development_stack(torch, device)
    query, kv, sinks, indices, sink_values = _governed_differential_fixture()
    expected = sparse_attention_bf16(
        query,
        kv,
        sinks,
        indices,
        scale_binary32=_f32(Fraction(1, 2)),
    ).values

    query_native = torch.tensor(query, dtype=torch.uint16).view(torch.bfloat16).to(device)
    kv_native = torch.tensor(kv, dtype=torch.uint16).view(torch.bfloat16).to(device)
    sink_native = torch.tensor(
        [float(value) for value in sink_values],
        dtype=torch.float32,
        device=device,
    )
    batch_size, sequence_length, head_count, head_dim = query_native.shape
    observed = torch.empty_like(query_native)
    for batch_index in range(batch_size):
        for position in range(sequence_length):
            scores_max = torch.full(
                (head_count,),
                -torch.inf,
                dtype=torch.float32,
                device=device,
            )
            sum_exp = torch.zeros(head_count, dtype=torch.float32, device=device)
            accumulator = torch.zeros(
                (head_count, head_dim),
                dtype=torch.float32,
                device=device,
            )
            row_indices = indices[batch_index][position]
            for start in range(0, len(row_indices), SPARSE_ATTENTION_BLOCK_SIZE):
                block = list(row_indices[start : start + SPARSE_ATTENTION_BLOCK_SIZE])
                block.extend([-1] * (SPARSE_ATTENTION_BLOCK_SIZE - len(block)))
                valid = torch.tensor(
                    [index != -1 for index in block],
                    dtype=torch.bool,
                    device=device,
                )
                safe_indices = torch.tensor(
                    [max(index, 0) for index in block],
                    dtype=torch.int64,
                    device=device,
                )
                rows = kv_native[batch_index, safe_indices].clone()
                rows[~valid] = 0
                scores = torch.einsum(
                    "hd,td->ht",
                    query_native[batch_index, position].float(),
                    rows.float(),
                )
                scores *= 0.5
                scores[:, ~valid] = -torch.inf
                previous_maximum = scores_max.clone()
                scores_max = torch.maximum(scores_max, scores.max(dim=1).values)
                scores_scale = torch.exp(previous_maximum - scores_max)
                probabilities = torch.exp(scores - scores_max[:, None])
                sum_exp = sum_exp * scores_scale + probabilities.sum(dim=1)
                accumulator *= scores_scale[:, None]
                accumulator += (
                    probabilities.to(torch.bfloat16).float().unsqueeze(-1)
                    * rows.float().unsqueeze(0)
                ).sum(dim=1)
            sum_exp += torch.exp(sink_native - scores_max)
            observed[batch_index, position] = (accumulator / sum_exp[:, None]).to(
                torch.bfloat16
            )

    observed_codes = tuple(
        int(code) & 0xFFFF
        for code in observed.view(torch.int16).reshape(-1).cpu().tolist()
    )
    expected_codes = tuple(
        code
        for sequence in expected
        for heads in sequence
        for row in heads
        for code in row
    )
    differences = [
        (observed_code, expected_code)
        for observed_code, expected_code in zip(
            observed_codes,
            expected_codes,
            strict=True,
        )
        if (0 if observed_code & 0x7FFF == 0 else observed_code) != expected_code
    ]
    assert len(expected_codes) == 96
    assert differences == []
