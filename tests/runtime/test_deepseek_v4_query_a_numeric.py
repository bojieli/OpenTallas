from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from runtime.service_engine import query_a_numeric
from runtime.service_engine.query_a_numeric import (
    EXHAUSTIVE_QUERY_A_ROWS,
    HIDDEN_SIZE,
    MAX_TOKEN_COUNT,
    QUERY_A_BLOCK_COUNT,
    QUERY_A_OUTPUT_FEATURES,
    QueryAServiceNumericError,
    execute_complete_query_a,
    query_a_functional_counters,
)


def test_query_a_numeric_contract_is_complete_and_reference_independent() -> None:
    assert HIDDEN_SIZE == 4096
    assert QUERY_A_OUTPUT_FEATURES == 1024
    assert QUERY_A_BLOCK_COUNT == 32
    assert EXHAUSTIVE_QUERY_A_ROWS == tuple(range(1024))
    source = inspect.getsource(query_a_numeric)
    assert "runtime.reference" not in source
    assert "compiler." not in source
    assert "expected_output" not in source


def test_query_a_functional_counters_are_exact_and_shape_derived() -> None:
    one = query_a_functional_counters(1)
    four = query_a_functional_counters(4)
    assert one == {
        "activation_blocks_quantized": 32,
        "activation_values_quantized": 4096,
        "bf16_attention_input_values_read": 4096,
        "bf16_normalized_values_written": 4096,
        "bf16_query_a_values_written": 1024,
        "binary32_epsilon_adds": 1,
        "binary32_fp8_block_reduction_adds": 31_744,
        "binary32_fp8_product_accumulates": 4_194_304,
        "binary32_rms_divides": 1,
        "binary32_rms_normalization_multiplies": 4096,
        "binary32_rms_reduction_adds": 4095,
        "binary32_rms_square_multiplies": 4096,
        "binary32_rms_weight_multiplies": 4096,
        "binary32_rsqrt_evaluations": 1,
        "complete_events": 1,
        "logical_attention_input_bytes_read": 8192,
        "logical_normalized_bytes_written": 8192,
        "logical_query_a_bytes_written": 2048,
        "logical_query_parameter_bytes_read": 4_227_072,
        "logical_rms_weight_bytes_read": 8192,
        "matrix_block_dots": 32_768,
        "micro_ops_executed": 3,
        "semantic_operators_executed": 2,
    }
    assert set(four) == set(one)
    for key, value in one.items():
        if key in {
            "complete_events",
            "micro_ops_executed",
            "semantic_operators_executed",
        }:
            assert four[key] == value
        else:
            assert four[key] == 4 * value


@pytest.mark.parametrize("invalid", [True, False, 0, 5, -1, 1.0, "1", None])
def test_query_a_counter_token_count_is_type_sensitive(invalid: object) -> None:
    with pytest.raises(QueryAServiceNumericError, match="token_count"):
        query_a_functional_counters(invalid)  # type: ignore[arg-type]


def test_query_a_rejects_shape_before_resource_access() -> None:
    accesses: list[tuple[int, ...]] = []

    def weight_row(row: int) -> bytes:
        accesses.append((row,))
        return b""

    def scale_code(row: int, block: int) -> int:
        accesses.append((row, block))
        return 0

    with pytest.raises(QueryAServiceNumericError, match="between 1 and 4"):
        execute_complete_query_a(
            (),
            (),
            weight_row=weight_row,
            scale_code=scale_code,
        )
    with pytest.raises(QueryAServiceNumericError, match="exactly 4096"):
        execute_complete_query_a(
            ((0,),),
            (),
            weight_row=weight_row,
            scale_code=scale_code,
        )
    too_many = tuple((0,) * HIDDEN_SIZE for _ in range(MAX_TOKEN_COUNT + 1))
    with pytest.raises(QueryAServiceNumericError, match="between 1 and 4"):
        execute_complete_query_a(
            too_many,
            (),
            weight_row=weight_row,
            scale_code=scale_code,
        )
    assert accesses == []


@pytest.mark.parametrize("bad", [None, "rows", b"rows", 1, 1.0, object()])
def test_query_a_rejects_nonsequence_input_without_resource_access(bad: object) -> None:
    accessed = False

    def weight_row(_: int) -> bytes:
        nonlocal accessed
        accessed = True
        return b""

    with pytest.raises(QueryAServiceNumericError, match="must be a sequence"):
        execute_complete_query_a(
            bad,  # type: ignore[arg-type]
            (),
            weight_row=weight_row,
            scale_code=lambda _row, _block: 0,
        )
    assert not accessed


def test_query_a_requires_both_resource_accessors() -> None:
    row = ((0,) * HIDDEN_SIZE,)
    weights = (0x3F80,) * HIDDEN_SIZE
    with pytest.raises(QueryAServiceNumericError, match="resource accessors"):
        execute_complete_query_a(
            row,
            weights,
            weight_row=None,  # type: ignore[arg-type]
            scale_code=lambda _row, _block: 0,
        )
    with pytest.raises(QueryAServiceNumericError, match="resource accessors"):
        execute_complete_query_a(
            row,
            weights,
            weight_row=lambda _row: b"",
            scale_code=None,  # type: ignore[arg-type]
        )


def test_query_a_executes_all_rows_and_preserves_both_operator_boundaries() -> None:
    # A zero activation keeps the full official shape inexpensive while still
    # proving that all 1,024 rows and all 32 scale blocks are requested.  The
    # normalized intermediate is architecturally observable and must not be
    # skipped even though the eventual projection is zero.
    input_row = tuple(0 for _ in range(HIDDEN_SIZE))
    norm_weights = tuple(0x3F80 for _ in range(HIDDEN_SIZE))
    accessed_rows: list[int] = []
    accessed_scales: list[tuple[int, int]] = []

    def weight_row(row: int) -> bytes:
        accessed_rows.append(row)
        return bytes(HIDDEN_SIZE)

    def scale_code(row: int, block: int) -> int:
        accessed_scales.append((row, block))
        return 0x7F

    result = execute_complete_query_a(
        (input_row,),
        norm_weights,
        weight_row=weight_row,
        scale_code=scale_code,
    )

    assert result.normalized_codes == (input_row,)
    assert result.query_a_codes == ((0,) * QUERY_A_OUTPUT_FEATURES,)
    assert result.mean_square_codes == (0,)
    assert result.inverse_rms_codes == (0x447A0000,)
    assert result.rms_output_saturation_count == 0
    assert result.activation_saturated_block_count == 0
    assert result.query_output_saturated_element_count == 0
    assert accessed_rows == list(EXHAUSTIVE_QUERY_A_ROWS)
    assert accessed_scales == [
        (row, block)
        for row in EXHAUSTIVE_QUERY_A_ROWS
        for block in range(QUERY_A_BLOCK_COUNT)
    ]


def test_query_a_composition_passes_exact_full_shape_between_primitives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The preceding test executes both real primitives over all official rows.
    # This orchestration test spies on their interface so ordinary CI does not
    # duplicate another 4,194,304-product qualification run.
    input_row = tuple(0x3F80 if index == 0 else 0 for index in range(HIDDEN_SIZE))
    norm_weights = tuple(0x3F80 for _ in range(HIDDEN_SIZE))
    normalized_row = tuple(0x4000 if index == 0 else 0 for index in range(HIDDEN_SIZE))
    query_row = tuple(0x3F80 for _ in range(QUERY_A_OUTPUT_FEATURES))
    calls: list[tuple[object, ...]] = []

    def fake_rms(inputs: object, weights: object) -> object:
        calls.append(("rms", inputs, weights))
        return SimpleNamespace(
            output_codes=(normalized_row,),
            mean_square_codes=(0x39800000,),
            inverse_rms_codes=(0x427F7A31,),
            output_saturation_count=2,
        )

    def fake_fp8(
        inputs: object,
        *,
        selected_rows: object,
        input_features: object,
        weight_row: object,
        scale_code: object,
    ) -> tuple[object, int, int]:
        calls.append(
            (
                "fp8",
                inputs,
                selected_rows,
                input_features,
                weight_row,
                scale_code,
            )
        )
        return (query_row,), 3, 5

    monkeypatch.setattr(query_a_numeric, "execute_weighted_rms_norm", fake_rms)
    monkeypatch.setattr(query_a_numeric, "execute_selected_rows", fake_fp8)

    def weight_accessor(_row: int) -> bytes:
        return bytes(HIDDEN_SIZE)

    def scale_accessor(_row: int, _block: int) -> int:
        return 0x7F

    result = execute_complete_query_a(
        (input_row,),
        norm_weights,
        weight_row=weight_accessor,
        scale_code=scale_accessor,
    )

    assert calls == [
        ("rms", (input_row,), norm_weights),
        (
            "fp8",
            (normalized_row,),
            EXHAUSTIVE_QUERY_A_ROWS,
            HIDDEN_SIZE,
            weight_accessor,
            scale_accessor,
        ),
    ]
    assert result.normalized_codes == (normalized_row,)
    assert result.query_a_codes == (query_row,)
    assert result.mean_square_codes == (0x39800000,)
    assert result.inverse_rms_codes == (0x427F7A31,)
    assert result.rms_output_saturation_count == 2
    assert result.activation_saturated_block_count == 3
    assert result.query_output_saturated_element_count == 5


def test_query_a_numeric_poison_has_operator_context() -> None:
    valid_row = ((0,) * HIDDEN_SIZE,)
    valid_norm = (0x3F80,) * HIDDEN_SIZE
    with pytest.raises(QueryAServiceNumericError, match="RMS_NORM numeric poison"):
        execute_complete_query_a(
            valid_row,
            (*valid_norm[:-1], 0x7F80),
            weight_row=lambda _row: bytes(HIDDEN_SIZE),
            scale_code=lambda _row, _block: 0x7F,
        )
    with pytest.raises(QueryAServiceNumericError, match="FP8_LINEAR numeric poison"):
        execute_complete_query_a(
            valid_row,
            valid_norm,
            weight_row=lambda _row: bytes(HIDDEN_SIZE - 1),
            scale_code=lambda _row, _block: 0x7F,
        )
