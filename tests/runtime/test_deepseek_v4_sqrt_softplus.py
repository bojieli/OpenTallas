from __future__ import annotations

from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import inspect
import os
from pathlib import Path
import random

import pytest

from runtime.reference.formats import (
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)
import runtime.reference.sqrt_softplus as sqrt_softplus_module
from runtime.reference.sqrt_softplus import (
    MODEL_SOURCE_SHA256,
    NUMERIC_PROFILE,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    SOFTPLUS_BETA_BINARY32,
    SOFTPLUS_THRESHOLD_BINARY32,
    SOURCE_EXPRESSION,
    SqrtSoftplusReferenceError,
    bf16_sqrt_softplus_binary32_rne,
    binary32_sqrt_softplus_rne,
    binary32_sqrt_softplus_rne_with_diagnostics,
    sqrt_softplus_binary32,
)


SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_SNAPSHOT"


def _widen_bf16(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code << 16


def _ordered_finite_bf16_codes() -> tuple[int, ...]:
    # Negative finite encodings increase numerically as their bit patterns
    # decrease. Both signed zeros are retained as distinct legal source bits.
    return tuple(range(0xFF7F, 0x7FFF, -1)) + tuple(range(0x0000, 0x7F80))


def _decimal_oracle(input_code: int, precision: int) -> tuple[int, int]:
    decoded = decode_binary32(input_code)
    assert decoded.finite and decoded.value is not None
    exact = decoded.value
    with localcontext() as context:
        context.prec = precision
        value = Decimal(exact.numerator) / Decimal(exact.denominator)
        if exact > 20:
            softplus = value
        else:
            softplus = (Decimal(1) + value.exp()).ln()
        softplus_code = encode_binary32_rne(Fraction(softplus))
        rounded = decode_binary32(softplus_code).value
        assert rounded is not None
        square_root = (Decimal(rounded.numerator) / Decimal(rounded.denominator)).sqrt()
        output_code = encode_binary32_rne(Fraction(square_root))
    return softplus_code, output_code


def _assert_exact_sqrt_rounding(input_code: int, output_code: int) -> None:
    source = decode_binary32(input_code)
    output = decode_binary32(output_code)
    assert source.finite and source.value is not None and source.value >= 0
    assert output.finite and output.value is not None and output.value >= 0
    value = source.value
    candidate = output.value
    if value == 0:
        assert output_code == 0
        return
    candidate_square = candidate * candidate
    if candidate_square == value:
        return
    if candidate_square < value:
        lower_code = output_code
        upper_code = output_code + 1
    else:
        assert output_code > 0
        lower_code = output_code - 1
        upper_code = output_code
    lower = decode_binary32(lower_code).value
    upper = decode_binary32(upper_code).value
    assert lower is not None and upper is not None
    midpoint_square = ((lower + upper) / 2) ** 2
    if output_code == lower_code:
        assert value < midpoint_square or (
            value == midpoint_square and lower_code & 1 == 0
        )
    else:
        assert value > midpoint_square or (
            value == midpoint_square and upper_code & 1 == 0
        )


def _stratified_binary32_inputs() -> tuple[int, ...]:
    values = {
        0x00000000,
        0x80000000,
        0x00000001,
        0x80000001,
        0x007FFFFF,
        0x807FFFFF,
        0x00800000,
        0x80800000,
        0x3F800000,
        0xBF800000,
        0x41A00000,
        0x41A00001,
        0x419FFFFF,
        0xC2D20000,
        0xC2D20001,
        0xC2D1FFFF,
        0x7F7FFFFF,
        0xFF7FFFFF,
    }
    for sign in (0, 0x80000000):
        for exponent in range(0xFF):
            for fraction in (0, 1, 0x3FFFFF, 0x7FFFFF):
                values.add(sign | (exponent << 23) | fraction)
    generator = random.Random(0x5351525453504C55)
    while len(values) < 4096:
        code = generator.randrange(1 << 32)
        if code & 0x7F800000 != 0x7F800000:
            values.add(code)
    return tuple(sorted(values))


def test_operator_is_pinned_to_exact_official_source_identity() -> None:
    assert OFFICIAL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert OFFICIAL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert SOURCE_EXPRESSION == "scores = F.softplus(scores).sqrt()"
    assert NUMERIC_PROFILE == "opentallas.deepseek_v4_sqrt_softplus_numeric.v1"
    assert SOFTPLUS_BETA_BINARY32 == 0x3F800000
    assert SOFTPLUS_THRESHOLD_BINARY32 == 0x41A00000


def test_cached_official_source_has_the_pinned_gate_expression() -> None:
    default = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / OFFICIAL_REVISION
    )
    snapshot = Path(os.environ.get(SNAPSHOT_ENV, default))
    source = snapshot / "inference/model.py"
    if not source.is_file():
        pytest.skip(f"official pinned source is not cached at {source}")
    payload = source.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == MODEL_SOURCE_SHA256
    lines = payload.decode("utf-8").splitlines()
    assert lines[568].strip().startswith("def forward(")
    assert lines[569].strip() == "scores = linear(x.float(), self.weight.float())"
    assert lines[575].strip() == SOURCE_EXPRESSION


def test_production_path_uses_no_host_math_or_framework_transcendentals() -> None:
    source = inspect.getsource(sqrt_softplus_module)
    for forbidden in (
        "import math",
        "from math",
        "import numpy",
        "import torch",
        "import decimal",
        "import mpmath",
        "runtime.service_engine",
    ):
        assert forbidden not in source
    assert "Fraction" in source
    assert "Lindemann-Weierstrass" in source


def test_known_two_stage_boundaries_and_default_threshold_rule() -> None:
    zero = binary32_sqrt_softplus_rne_with_diagnostics(0x00000000)
    negative_zero = binary32_sqrt_softplus_rne_with_diagnostics(0x80000000)
    assert zero == negative_zero
    assert zero.softplus_binary32_code == 0x3F317218
    assert zero.output_binary32_code == 0x3F55224D
    assert zero.softplus_branch == "transcendental"
    assert zero.softplus_interval_evaluations >= 1
    assert zero.softplus_final_precision_bits >= 48

    at_threshold = binary32_sqrt_softplus_rne_with_diagnostics(0x41A00000)
    above_threshold = binary32_sqrt_softplus_rne_with_diagnostics(0x41A00001)
    below_threshold = binary32_sqrt_softplus_rne_with_diagnostics(0x419FFFFF)
    assert at_threshold.softplus_branch == "transcendental"
    assert below_threshold.softplus_branch == "transcendental"
    assert above_threshold.softplus_branch == "linear_threshold"
    assert at_threshold.softplus_binary32_code == 0x41A00000
    assert above_threshold.softplus_binary32_code == 0x41A00001
    assert above_threshold.softplus_interval_evaluations == 0
    assert above_threshold.softplus_final_precision_bits == 0

    at_zero_cutoff = binary32_sqrt_softplus_rne_with_diagnostics(0xC2D20000)
    below_zero_cutoff = binary32_sqrt_softplus_rne_with_diagnostics(0xC2D20001)
    above_zero_cutoff = binary32_sqrt_softplus_rne_with_diagnostics(0xC2D1FFFF)
    assert at_zero_cutoff.softplus_branch == "proved_underflow_zero"
    assert below_zero_cutoff.softplus_branch == "proved_underflow_zero"
    assert above_zero_cutoff.softplus_branch == "transcendental"
    assert at_zero_cutoff.softplus_binary32_code == 0
    assert at_zero_cutoff.output_binary32_code == 0

    maximum = binary32_sqrt_softplus_rne_with_diagnostics(0x7F7FFFFF)
    assert maximum.softplus_binary32_code == 0x7F7FFFFF
    assert maximum.output_binary32_code == 0x5F7FFFFF
    assert maximum.softplus_branch == "linear_threshold"


def test_underflow_cutoff_has_an_exact_rational_proof() -> None:
    argument = Fraction(7, 10)
    partial = sum(
        (argument**index) / math_factorial
        for index, math_factorial in enumerate((1, 1, 2, 6, 24))
    )
    assert partial > 2
    assert 150 * argument == 105


@pytest.mark.parametrize(
    "invalid",
    [
        True,
        False,
        1.0,
        "0",
        b"\0\0\0\0",
        -1,
        1 << 32,
        0x7F800000,
        0xFF800000,
        0x7FC00000,
        0xFFC00001,
    ],
)
def test_binary32_scalar_poison_is_strict(invalid: object) -> None:
    with pytest.raises(SqrtSoftplusReferenceError):
        binary32_sqrt_softplus_rne(invalid)  # type: ignore[arg-type]


def test_integer_subclasses_do_not_alias_exact_encodings() -> None:
    class IntegerAlias(int):
        pass

    with pytest.raises(SqrtSoftplusReferenceError, match="exact 32-bit"):
        binary32_sqrt_softplus_rne(IntegerAlias(0x3F800000))
    with pytest.raises(SqrtSoftplusReferenceError, match="exact 16-bit"):
        bf16_sqrt_softplus_binary32_rne(IntegerAlias(0x3F80))


@pytest.mark.parametrize(
    "invalid",
    [True, False, 1.0, "0", -1, 1 << 16, 0x7F80, 0xFF80, 0x7FC1, 0xFFC1],
)
def test_bf16_audit_wrapper_poison_is_strict(invalid: object) -> None:
    with pytest.raises(SqrtSoftplusReferenceError):
        bf16_sqrt_softplus_binary32_rne(invalid)  # type: ignore[arg-type]


def test_matrix_operator_is_rectangular_immutable_and_scalar_exact() -> None:
    inputs = (
        (0xBF800000, 0x00000000, 0x3F800000),
        (0x41A00000, 0x41A00001, 0xC2D20000),
    )
    expected = tuple(
        tuple(binary32_sqrt_softplus_rne(code) for code in row) for row in inputs
    )
    result = sqrt_softplus_binary32(inputs)
    assert result == expected
    assert type(result) is tuple
    assert all(type(row) is tuple for row in result)
    with pytest.raises(TypeError):
        result[0][0] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid",
    [
        [],
        [[], []],
        [[0], [0, 1]],
        [[0], [True]],
        [[0], [0x7F800000]],
        "scores",
        b"scores",
    ],
)
def test_matrix_operator_rejects_malformed_or_poisoned_inputs(invalid: object) -> None:
    with pytest.raises(SqrtSoftplusReferenceError):
        sqrt_softplus_binary32(invalid)  # type: ignore[arg-type]


def test_matrix_validation_finishes_before_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    original = sqrt_softplus_module.binary32_sqrt_softplus_rne

    def observe(code: int) -> int:
        calls.append(code)
        return original(code)

    monkeypatch.setattr(
        sqrt_softplus_module,
        "binary32_sqrt_softplus_rne",
        observe,
    )
    with pytest.raises(SqrtSoftplusReferenceError):
        sqrt_softplus_binary32([[0, 0], [0, 0x7F800000]])
    assert calls == []


def test_stratified_binary32_domain_matches_independent_decimal_oracle() -> None:
    for input_code in _stratified_binary32_inputs():
        low_precision = _decimal_oracle(input_code, 160)
        high_precision = _decimal_oracle(input_code, 260)
        assert low_precision == high_precision
        diagnostics = binary32_sqrt_softplus_rne_with_diagnostics(input_code)
        assert (
            diagnostics.softplus_binary32_code,
            diagnostics.output_binary32_code,
        ) == high_precision


def test_all_finite_bf16_inputs_are_exhaustively_partitioned_and_exact() -> None:
    previous_input: Fraction | None = None
    previous_softplus: Fraction | None = None
    previous_output: Fraction | None = None
    branches: Counter[str] = Counter()
    codes = _ordered_finite_bf16_codes()
    assert len(codes) == 65_280

    for code in codes:
        decoded = decode_bf16(code)
        assert decoded.finite and decoded.value is not None
        value = decoded.value
        widened = _widen_bf16(code)
        diagnostics = binary32_sqrt_softplus_rne_with_diagnostics(widened)
        assert bf16_sqrt_softplus_binary32_rne(code) == diagnostics.output_binary32_code
        branches[diagnostics.softplus_branch] += 1
        if value > 20:
            assert diagnostics.softplus_branch == "linear_threshold"
            assert diagnostics.softplus_binary32_code == widened
        elif value <= -105:
            assert diagnostics.softplus_branch == "proved_underflow_zero"
            assert diagnostics.softplus_binary32_code == 0
        else:
            assert diagnostics.softplus_branch == "transcendental"
            assert diagnostics.softplus_interval_evaluations >= 1
            assert diagnostics.softplus_final_precision_bits >= 48

        softplus = decode_binary32(diagnostics.softplus_binary32_code)
        output = decode_binary32(diagnostics.output_binary32_code)
        assert softplus.finite and softplus.value is not None
        assert output.finite and output.value is not None
        assert softplus.value >= 0
        assert output.value >= 0
        _assert_exact_sqrt_rounding(
            diagnostics.softplus_binary32_code,
            diagnostics.output_binary32_code,
        )
        if previous_input is not None:
            assert previous_input <= value
            assert previous_softplus is not None and previous_softplus <= softplus.value
            assert previous_output is not None and previous_output <= output.value
        previous_input = value
        previous_softplus = softplus.value
        previous_output = output.value

    assert branches == {
        "linear_threshold": 15_839,
        "proved_underflow_zero": 15_534,
        "transcendental": 33_907,
    }


def test_exact_interval_helpers_enclose_independent_high_precision_values() -> None:
    for value in (Fraction(-104), Fraction(-20), Fraction(-1), Fraction(-1, 256)):
        lower, upper = sqrt_softplus_module._exp_negative_fixed_interval(value, 96)
        with localcontext() as context:
            context.prec = 180
            exact = (Decimal(value.numerator) / Decimal(value.denominator)).exp()
            scale = Decimal(1 << 96)
            assert Decimal(lower) / scale <= exact <= Decimal(upper) / scale

    for value in (
        Fraction(1, 1 << 96),
        Fraction(1, 1024),
        Fraction(1, 2),
        Fraction(1),
    ):
        lower, upper = sqrt_softplus_module._log1p_fixed_interval(value, 96)
        with localcontext() as context:
            context.prec = 180
            exact = (
                Decimal(1) + Decimal(value.numerator) / Decimal(value.denominator)
            ).ln()
            scale = Decimal(1 << 96)
            assert Decimal(lower) / scale <= exact <= Decimal(upper) / scale
