from __future__ import annotations

import ast
from copy import deepcopy
import inspect
import random

import pytest

from runtime.reference.formats import bf16_rsqrt
from runtime.reference.normalization import head_rms_norm_bf16
from runtime.service_engine import head_rms_numeric
from runtime.service_engine.head_rms_numeric import (
    HEAD_RMS_NORM_EPSILON_BF16,
    HEAD_RMS_NORM_MAX_ROWS,
    HEAD_RMS_NORM_WIDTH,
    HeadRMSServiceNumericError,
    HeadRMSServiceResult,
    cr_bf16_rsqrt,
    execute_head_rms_norm,
)


WIDTH = HEAD_RMS_NORM_WIDTH
ZEROS = (0,) * WIDTH
ONES = (0x3F80,) * WIDTH


def _assert_matches_reference(rows: tuple[tuple[int, ...], ...]) -> None:
    for start in range(0, len(rows), HEAD_RMS_NORM_MAX_ROWS):
        command = rows[start : start + HEAD_RMS_NORM_MAX_ROWS]
        expected = head_rms_norm_bf16(command)
        observed = execute_head_rms_norm(command)
        assert observed.mean_square_codes == expected.mean_square_codes
        assert observed.inverse_rms_codes == expected.inverse_rms_codes
        assert observed.output_codes == expected.output_codes
        assert observed.output_saturation_count == expected.output_saturation_count


def test_head_rms_service_contract_is_pinned_and_reference_independent() -> None:
    assert HEAD_RMS_NORM_WIDTH == 512
    assert HEAD_RMS_NORM_MAX_ROWS == 4
    assert HEAD_RMS_NORM_EPSILON_BF16 == 0x3586
    source = inspect.getsource(head_rms_numeric)
    assert "runtime.reference" not in source
    assert "runtime.service_engine" not in source
    assert "numpy" not in source
    assert "torch" not in source
    assert "__import__" not in source
    assert "importlib" not in source
    assert "exec(" not in source
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert imported_modules == {
        "collections.abc",
        "dataclasses",
        "fractions",
        "typing",
    }


def test_head_rms_service_known_answers_expose_every_bf16_boundary() -> None:
    one_hot = (0x3F80,) + (0,) * (WIDTH - 1)
    rounded_square = (0x3F81,) * WIDTH

    result = execute_head_rms_norm((ZEROS, ONES, one_hot, rounded_square))

    assert isinstance(result, HeadRMSServiceResult)
    assert result.mean_square_codes == (0, 0x3F80, 0x3B00, 0x3F82)
    assert result.inverse_rms_codes == (0x447A, 0x3F80, 0x41B5, 0x3F7E)
    assert result.output_codes == (
        ZEROS,
        ONES,
        (0x41B5,) + (0,) * (WIDTH - 1),
        ONES,
    )
    assert result.output_saturation_count == 0


def test_head_rms_service_uses_num_6_1_balanced_square_tree() -> None:
    row = (0x3651, 0x4239, 0x47F9, 0x4859) + (0,) * (WIDTH - 4)

    result = execute_head_rms_norm((row,))

    # The direct-BF16 squares are 2d2b, 4506, 5072, and 5138. The target
    # pair tree produces binary32 square sum 0x51748001 and BF16 mean 4cf5;
    # a left fold produces 0x51748000 and adjacent BF16 mean 4cf4.
    assert result.mean_square_codes == (0x4CF5,)
    assert result.inverse_rms_codes == (0x38B9,)
    assert result.output_codes[0][:4] == (0x2F97, 0x3B86, 0x4134, 0x419D)
    assert result.output_codes[0][4:] == (0,) * (WIDTH - 4)


def test_head_rms_service_preserves_subnormals_signs_and_canonicalizes_zero() -> None:
    alternating = tuple(0xBF80 if index & 1 else 0x3F80 for index in range(WIDTH))
    result = execute_head_rms_norm(
        (
            alternating,
            (0x8000,) * WIDTH,
            (0x0001,) * WIDTH,
            (0x8001,) * WIDTH,
        )
    )

    assert result.mean_square_codes == (0x3F80, 0, 0, 0)
    assert result.inverse_rms_codes == (0x3F80, 0x447A, 0x447A, 0x447A)
    assert result.output_codes == (
        alternating,
        (0,) * WIDTH,
        (0x01FA,) * WIDTH,
        (0x81FA,) * WIDTH,
    )
    assert result.output_saturation_count == 0


def test_head_rms_service_matches_reference_on_adversarial_random_rows() -> None:
    generator = random.Random(0x4845_4144_5356_4352)
    palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x007F,
        0x807F,
        0x0080,
        0x8080,
        0x3586,
        0xB586,
        0x3D80,
        0xBD80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
        0x4100,
        0xC100,
    )
    palette_rows = tuple(
        tuple(generator.choice(palette) for _ in range(WIDTH)) for _ in range(6)
    )
    broad_rows = tuple(
        tuple(
            (generator.randrange(2) << 15)
            | (generator.randrange(80, 161) << 7)
            | generator.randrange(128)
            for _ in range(WIDTH)
        )
        for _ in range(6)
    )
    rows = (*palette_rows, *broad_rows)

    _assert_matches_reference(rows)
    command = rows[:HEAD_RMS_NORM_MAX_ROWS]
    assert execute_head_rms_norm(command) == execute_head_rms_norm(command)


def test_one_bit_input_mutation_is_visible_at_the_architectural_output() -> None:
    baseline = execute_head_rms_norm((ONES,))
    mutated_row = ((0x3F80 ^ 0x0001),) + ONES[1:]
    mutated = execute_head_rms_norm((mutated_row,))

    assert baseline.mean_square_codes == (0x3F80,)
    assert baseline.inverse_rms_codes == (0x3F80,)
    assert mutated.mean_square_codes == (0x3F80,)
    assert mutated.inverse_rms_codes == (0x3F80,)
    assert mutated.output_codes[0][:2] == (0x3F81, 0x3F80)
    assert mutated != baseline


def test_cr_bf16_rsqrt_matches_independent_reference_exhaustively() -> None:
    # Every positive finite BF16 encoding is covered.  This permanently retains
    # the qualification audit for the exact midpoint/ties-to-even selector.
    for code in range(1, 0x7F80):
        assert cr_bf16_rsqrt(code) == bf16_rsqrt(code)


@pytest.mark.parametrize(
    ("inputs", "epsilon", "match"),
    [
        ((), HEAD_RMS_NORM_EPSILON_BF16, "at least one row"),
        ("bad", HEAD_RMS_NORM_EPSILON_BF16, "must be a sequence"),
        ((0,) * WIDTH, HEAD_RMS_NORM_EPSILON_BF16, "must be a sequence"),
        (((0,) * (WIDTH - 1),), HEAD_RMS_NORM_EPSILON_BF16, "exactly 512"),
        (((0,) * (WIDTH + 1),), HEAD_RMS_NORM_EPSILON_BF16, "exactly 512"),
        (
            (ZEROS,) * (HEAD_RMS_NORM_MAX_ROWS + 1),
            HEAD_RMS_NORM_EPSILON_BF16,
            "command maximum",
        ),
        (((False,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        (((-1,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        ((((1 << 16),) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        (((1.0,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        (((0x7F80,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "finite BF16"),
        (((0xFF80,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "finite BF16"),
        (((0x7FC1,) * WIDTH,), HEAD_RMS_NORM_EPSILON_BF16, "finite BF16"),
        ((ZEROS,), 0x3585, "must equal"),
        ((ZEROS,), 0x3587, "must equal"),
        ((ZEROS,), True, "must equal"),
        ((ZEROS,), 1e-6, "must equal"),
    ],
)
def test_head_rms_service_rejects_shape_nonfinite_and_profile_mutations(
    inputs: object,
    epsilon: object,
    match: str,
) -> None:
    with pytest.raises(HeadRMSServiceNumericError, match=match):
        execute_head_rms_norm(  # type: ignore[arg-type]
            inputs,
            epsilon_bf16=epsilon,
        )


def test_head_rms_service_poisons_direct_bf16_square_overflow() -> None:
    with pytest.raises(HeadRMSServiceNumericError, match="BF16 square overflow"):
        execute_head_rms_norm(((0x7F7F,) * WIDTH,))


def test_head_rms_service_poisons_balanced_binary32_reduction_overflow() -> None:
    # 5e80 squares directly to finite BF16 7d80. The width-512 binary32
    # reduction nevertheless overflows before the required divide.
    with pytest.raises(HeadRMSServiceNumericError, match="binary32 reduction overflow"):
        execute_head_rms_norm(((0x5E80,) * WIDTH,))


def test_later_invalid_row_poisons_atomically_without_mutating_inputs() -> None:
    mutable = [list(ONES), list(ONES)]
    mutable[1][-1] = 0x7FC0
    before = deepcopy(mutable)

    with pytest.raises(
        HeadRMSServiceNumericError,
        match=r"input_codes\[1\]\[511\].*finite BF16",
    ):
        execute_head_rms_norm(mutable)
    assert mutable == before


def test_later_arithmetic_overflow_does_not_commit_an_earlier_row() -> None:
    mutable = [list(ONES), [0x7F7F] * WIDTH]
    before = deepcopy(mutable)

    with pytest.raises(
        HeadRMSServiceNumericError,
        match=r"input_codes row 1 failed.*BF16 square overflow",
    ):
        execute_head_rms_norm(mutable)
    assert mutable == before
