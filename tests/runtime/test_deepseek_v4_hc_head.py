from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

import pytest

from runtime.reference.formats import (
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    binary32_product_add,
    binary32_rsqrt,
    decode_bf16,
    decode_binary32,
    encode_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.hc_head import (
    BF16_BYTES,
    EXCLUDED_SYSTEM_CLAIMS,
    F32_BYTES,
    FLATTENED_WIDTH,
    FLATTENED_WIDTH_BINARY32,
    HC_EPSILON_BINARY32,
    HC_HEAD_NUMERIC_PROFILE,
    HC_MULTIPLIER,
    HIDDEN_SIZE,
    INFERENCE_CONFIG_EXPECTED_FIELDS,
    INFERENCE_CONFIG_PATH,
    INFERENCE_CONFIG_SHA256,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    MODEL_SOURCE_PATH,
    MODEL_SOURCE_SHA256,
    NORMALIZATION_EPSILON_BINARY32,
    PROJECTION_ROWS,
    SOURCE_EXPRESSIONS,
    HCHeadCounters,
    HCHeadDiagnostics,
    HCHeadReferenceError,
    HCHeadResult,
    hc_head_bf16,
)
from runtime.reference.hyper_connection import binary32_sigmoid_rne


ROOT = Path(__file__).resolve().parents[2]
ZERO_STREAM = (0,) * HIDDEN_SIZE
ZERO_TOKEN = (ZERO_STREAM,) * HC_MULTIPLIER
ZERO_PROJECTION_ROW = (0,) * FLATTENED_WIDTH
ZERO_PROJECTION = (ZERO_PROJECTION_ROW,) * PROJECTION_ROWS
ONE_F32 = encode_binary32_rne(1)
ZERO_BASE = (0,) * PROJECTION_ROWS


def _bf16(value: int | Fraction) -> int:
    return encode_bf16_rne(value).code


def _f32(value: int | Fraction) -> int:
    return encode_binary32_rne(value)


def _token_with_values(
    values: dict[tuple[int, int], int],
) -> tuple[tuple[int, ...], ...]:
    streams = [[0] * HIDDEN_SIZE for _ in range(HC_MULTIPLIER)]
    for (stream, column), code in values.items():
        streams[stream][column] = code
    return tuple(tuple(stream) for stream in streams)


def _projection_with_values(
    values: dict[tuple[int, int], int],
) -> tuple[tuple[int, ...], ...]:
    rows = [[0] * FLATTENED_WIDTH for _ in range(PROJECTION_ROWS)]
    for (row, column), code in values.items():
        rows[row][column] = code
    return tuple(tuple(row) for row in rows)


def _execute(
    inputs: object = (ZERO_TOKEN,),
    projection: object = ZERO_PROJECTION,
    scale: object = (ONE_F32,),
    base: object = ZERO_BASE,
    **kwargs: object,
) -> HCHeadResult:
    return hc_head_bf16(inputs, projection, scale, base, **kwargs)  # type: ignore[arg-type]


def test_contract_is_bound_to_the_pinned_release_and_exact_shapes() -> None:
    assert MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert MODEL_SOURCE_PATH == "inference/model.py"
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INFERENCE_CONFIG_PATH == "inference/config.json"
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert HC_HEAD_NUMERIC_PROFILE == "opentallas.deepseek_v4_hc_head_numeric.v1"
    assert (MIN_TOKEN_COUNT, MAX_TOKEN_COUNT) == (1, 4)
    assert HC_MULTIPLIER == PROJECTION_ROWS == 4
    assert HIDDEN_SIZE == 4096
    assert FLATTENED_WIDTH == 16384
    assert FLATTENED_WIDTH_BINARY32 == 0x46800000
    assert NORMALIZATION_EPSILON_BINARY32 == HC_EPSILON_BINARY32 == 0x358637BD
    assert (BF16_BYTES, F32_BYTES) == (2, 4)
    assert INFERENCE_CONFIG_EXPECTED_FIELDS == (("dim", 4096), ("hc_mult", 4))
    assert SOURCE_EXPRESSIONS == (
        "x = x.flatten(2).float()",
        "rsqrt = torch.rsqrt(x.square().mean(-1, keepdim=True) + self.norm_eps)",
        "mixes = F.linear(x, hc_fn) * rsqrt",
        "pre = torch.sigmoid(mixes * hc_scale + hc_base) + self.hc_eps",
        "y = torch.sum(pre.unsqueeze(-1) * x.view(shape), dim=2)",
        "return y.to(dtype)",
        "self.hc_head_fn = nn.Parameter(torch.empty(hc_mult, hc_dim))",
        "self.hc_head_base = nn.Parameter(torch.empty(hc_mult))",
        "self.hc_head_scale = nn.Parameter(torch.empty(1))",
    )


def _compact_source(value: str) -> str:
    return re.sub(r"[\s()]", "", value)


def test_cached_official_source_and_inference_config_content_when_available() -> None:
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / MODEL_REVISION
    )
    source_path = snapshot / MODEL_SOURCE_PATH
    config_path = snapshot / INFERENCE_CONFIG_PATH
    if not source_path.is_file() or not config_path.is_file():
        pytest.skip("pinned official source/config are not in the local HF cache")

    source_bytes = source_path.read_bytes()
    config_bytes = config_path.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == MODEL_SOURCE_SHA256
    assert hashlib.sha256(config_bytes).hexdigest() == INFERENCE_CONFIG_SHA256
    compact_source = _compact_source(source_bytes.decode("utf-8"))
    for expression in SOURCE_EXPRESSIONS:
        assert _compact_source(expression) in compact_source
    config = json.loads(config_bytes)
    for field, expected in INFERENCE_CONFIG_EXPECTED_FIELDS:
        assert type(config[field]) is int
        assert config[field] == expected


def test_production_reference_has_no_framework_host_float_or_compiler_dependency() -> (
    None
):
    source_path = ROOT / "runtime/reference/hc_head.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert imported_roots.isdisjoint(
        {"compiler", "decimal", "math", "mpmath", "numpy", "torch"}
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(tree)
    )
    assert "placeholder" not in source.lower()
    assert "demo" not in source.lower()


def test_zero_transaction_fixes_every_numeric_boundary_and_counter() -> None:
    result = _execute()
    coefficient = 0x3F000011
    assert result.numeric_profile == HC_HEAD_NUMERIC_PROFILE
    assert result.output_bf16_codes == (ZERO_STREAM,)
    assert result.coefficient_binary32_codes == ((coefficient,) * 4,)
    assert result.output_saturation_count == 0
    assert result.diagnostics == HCHeadDiagnostics(
        mean_square_codes=(0,),
        inverse_rms_codes=(0x447A0000,),
        projection_codes=((0, 0, 0, 0),),
        normalized_projection_codes=((0, 0, 0, 0),),
        affine_codes=((0, 0, 0, 0),),
        sigmoid_codes=((0x3F000000,) * 4,),
        coefficient_codes=((coefficient,) * 4,),
    )
    assert result.counters == HCHeadCounters(
        token_count=1,
        input_bf16_values=16384,
        input_read_bytes=32768,
        projection_parameter_f32_values=65536,
        projection_parameter_bytes=262144,
        scale_parameter_f32_values=1,
        scale_parameter_bytes=4,
        base_parameter_f32_values=4,
        base_parameter_bytes=16,
        rms_square_multiplies=16384,
        rms_reduction_adds=16383,
        rms_divides=1,
        rms_epsilon_adds=1,
        rsqrt_evaluations=1,
        projection_product_accumulates=65536,
        projection_inverse_rms_multiplies=4,
        coefficient_scale_multiplies=4,
        coefficient_base_adds=4,
        sigmoid_evaluations=4,
        coefficient_epsilon_adds=4,
        branch_coefficient_multiplies=16384,
        branch_reduction_adds=12288,
        output_bf16_conversions=4096,
        output_bf16_saturations=0,
        output_bf16_values=4096,
        output_write_bytes=8192,
        transaction_commits=1,
    )


def test_projection_orientation_affine_and_stream_reduction_compose_exactly() -> None:
    token = _token_with_values(
        {
            (0, 0): _bf16(1),
            (1, 0): _bf16(2),
            (2, 0): _bf16(-1),
            (3, 0): _bf16(Fraction(1, 2)),
            (0, 1): _bf16(3),
        }
    )
    indices = (0, HIDDEN_SIZE, 2 * HIDDEN_SIZE, 3 * HIDDEN_SIZE)
    projection_values: dict[tuple[int, int], int] = {}
    for row in range(PROJECTION_ROWS):
        for stream, index in enumerate(indices):
            projection_values[row, index] = _f32((row + 1) * (stream + 1))
    projection = _projection_with_values(projection_values)
    scales = (_f32(Fraction(3, 2)),)
    bases = (_f32(-1), _f32(0), _f32(1), _f32(2))

    result = _execute((token,), projection, scales, bases)

    flattened_codes = tuple(
        0 if decode_bf16(code).value == 0 else code << 16
        for stream in token
        for code in stream
    )
    flattened_values = tuple(
        decode_bf16(code).value for stream in token for code in stream
    )
    squares = tuple(binary32_multiply(code, code) for code in flattened_codes)
    mean = binary32_divide(
        binary32_balanced_sum(squares),
        FLATTENED_WIDTH_BINARY32,
    )
    inverse = binary32_rsqrt(binary32_add(mean, NORMALIZATION_EPSILON_BINARY32))
    expected_projection = []
    for row in projection:
        accumulator = 0
        for input_value, weight_code in zip(flattened_values, row, strict=True):
            weight_value = decode_binary32(weight_code).value
            if input_value and weight_value:
                accumulator = binary32_product_add(
                    accumulator,
                    input_value,
                    weight_value,
                )
        expected_projection.append(accumulator)
    expected_normalized = tuple(
        binary32_multiply(code, inverse) for code in expected_projection
    )
    expected_affine = tuple(
        binary32_add(binary32_multiply(code, scales[0]), bases[row])
        for row, code in enumerate(expected_normalized)
    )
    expected_sigmoid = tuple(binary32_sigmoid_rne(code) for code in expected_affine)
    expected_coefficients = tuple(
        binary32_add(code, HC_EPSILON_BINARY32) for code in expected_sigmoid
    )
    expected_column0 = binary32_bits_to_bf16_rne(
        binary32_balanced_sum(
            tuple(
                binary32_multiply(expected_coefficients[stream], token[stream][0] << 16)
                for stream in range(4)
            )
        )
    ).code

    assert result.diagnostics.mean_square_codes == (mean,)
    assert result.diagnostics.inverse_rms_codes == (inverse,)
    assert result.diagnostics.projection_codes == (tuple(expected_projection),)
    assert result.diagnostics.normalized_projection_codes == (expected_normalized,)
    assert result.diagnostics.affine_codes == (expected_affine,)
    assert result.diagnostics.sigmoid_codes == (expected_sigmoid,)
    assert result.coefficient_binary32_codes == (expected_coefficients,)
    assert result.output_bf16_codes[0][0] == expected_column0


def test_projection_uses_increasing_k_product_add_order() -> None:
    large = _bf16(1 << 30)
    token = _token_with_values(
        {(0, 0): large, (0, 1): _bf16(1), (0, 2): _bf16(-(1 << 30))}
    )
    projection = _projection_with_values(
        {(0, 0): ONE_F32, (0, 1): ONE_F32, (0, 2): ONE_F32}
    )
    result = _execute((token,), projection)

    # Increasing K loses +1 at 2^30, then cancellation returns +0.  A
    # cancellation-first reassociation would instead retain +1.
    assert result.diagnostics.projection_codes[0][0] == 0


def test_balanced_four_stream_reduction_is_not_a_left_fold() -> None:
    token = _token_with_values(
        {
            (0, 0): _bf16(-20),
            (1, 0): _bf16(-19),
            (2, 0): _bf16(19),
            (3, 0): _bf16(20),
        }
    )
    result = _execute((token,))
    coefficients = result.coefficient_binary32_codes[0]
    products = tuple(
        binary32_multiply(coefficients[stream], token[stream][0] << 16)
        for stream in range(4)
    )
    balanced = binary32_balanced_sum(products)
    left = 0
    for product in products:
        left = binary32_add(left, product)
    assert balanced == 0x00000000
    assert left == 0x35800000
    assert result.output_bf16_codes[0][0] == 0x0000
    assert binary32_bits_to_bf16_rne(left).code == 0x3580


def test_maximum_command_extent_and_counters_are_shape_derived() -> None:
    result = _execute((ZERO_TOKEN,) * MAX_TOKEN_COUNT)
    assert result.output_bf16_codes == (ZERO_STREAM,) * MAX_TOKEN_COUNT
    assert result.counters.token_count == MAX_TOKEN_COUNT
    assert result.counters.input_bf16_values == MAX_TOKEN_COUNT * FLATTENED_WIDTH
    assert result.counters.projection_product_accumulates == (
        MAX_TOKEN_COUNT * PROJECTION_ROWS * FLATTENED_WIDTH
    )
    assert result.counters.output_bf16_values == MAX_TOKEN_COUNT * HIDDEN_SIZE
    assert result.counters.transaction_commits == 1


def test_signed_zero_and_subnormal_inputs_are_valid_and_caller_data_is_immutable() -> (
    None
):
    token_lists = [[[0] * HIDDEN_SIZE for _ in range(HC_MULTIPLIER)]]
    token_lists[0][0][0] = 0x8000
    token_lists[0][1][0] = 0x0001
    before = deepcopy(token_lists)
    result = _execute(token_lists)
    assert token_lists == before
    assert result.output_bf16_codes[0][1:] == (0,) * (HIDDEN_SIZE - 1)
    assert type(result.output_bf16_codes) is tuple
    assert type(result.output_bf16_codes[0]) is tuple
    with pytest.raises(FrozenInstanceError):
        result.output_saturation_count = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"normalization_epsilon_binary32": 0}, "must equal 0x358637bd"),
        ({"normalization_epsilon_binary32": True}, "must equal 0x358637bd"),
        ({"hc_epsilon_binary32": 0}, "must equal 0x358637bd"),
        ({"hc_epsilon_binary32": True}, "must equal 0x358637bd"),
    ],
)
def test_numeric_profile_cannot_be_overridden(kwargs: dict, match: str) -> None:
    with pytest.raises(HCHeadReferenceError, match=match):
        _execute(**kwargs)


@pytest.mark.parametrize(
    ("inputs", "match"),
    [
        ((), "token dimension"),
        ((ZERO_TOKEN,) * (MAX_TOKEN_COUNT + 1), "token dimension"),
        ("bad", "exact list or tuple"),
        (((ZERO_STREAM,) * 3,), "exactly 4 HC streams"),
        ((((0,) * (HIDDEN_SIZE - 1),) + (ZERO_STREAM,) * 3,), "exactly 4096"),
        ((((True,) + (0,) * (HIDDEN_SIZE - 1),) + (ZERO_STREAM,) * 3,), "16-bit BF16"),
        (
            (((0x7F80,) + (0,) * (HIDDEN_SIZE - 1),) + (ZERO_STREAM,) * 3,),
            "finite BF16",
        ),
    ],
)
def test_malformed_or_nonfinite_input_fails_closed(inputs: object, match: str) -> None:
    with pytest.raises(HCHeadReferenceError, match=match):
        _execute(inputs)


@pytest.mark.parametrize(
    ("scale", "base", "match"),
    [
        ((), ZERO_BASE, "exactly 1 value"),
        ((True,), ZERO_BASE, "32-bit binary32"),
        ((0x7F800000,), ZERO_BASE, "finite binary32"),
        ((ONE_F32,), (0, 0, 0), "exactly 4 values"),
        ((ONE_F32,), (0, 0, 0, 0x7FC00000), "finite binary32"),
    ],
)
def test_malformed_scale_or_base_fails_before_projection(
    scale: object,
    base: object,
    match: str,
) -> None:
    with pytest.raises(HCHeadReferenceError, match=match):
        _execute(scale=scale, base=base)


@pytest.mark.parametrize(
    ("projection", "match"),
    [
        ((), "exactly 4 rows"),
        ((ZERO_PROJECTION_ROW,) * 3, "exactly 4 rows"),
        (((0,) * (FLATTENED_WIDTH - 1),) + ZERO_PROJECTION[1:], "exactly 16384"),
        (
            ((0x7F800000,) + (0,) * (FLATTENED_WIDTH - 1),) + ZERO_PROJECTION[1:],
            "finite binary32",
        ),
        ((range(FLATTENED_WIDTH),) + ZERO_PROJECTION[1:], "exact list or tuple"),
    ],
)
def test_malformed_projection_fails_closed(projection: object, match: str) -> None:
    with pytest.raises(HCHeadReferenceError, match=match):
        _execute(projection=projection)


def test_projection_overflow_poison_is_atomic() -> None:
    token = _token_with_values({(0, 0): 0x7F7F})
    projection = _projection_with_values({(0, 0): 0x7F7FFFFF})
    before = deepcopy(token)
    with pytest.raises(HCHeadReferenceError, match="coefficient generation failed"):
        _execute((token,), projection)
    assert token == before


def test_public_counter_constructor_validates_every_integer_and_formula() -> None:
    counters = _execute().counters
    for field in fields(counters):
        with pytest.raises(HCHeadReferenceError, match="exact nonnegative integer"):
            replace(counters, **{field.name: True})

    for field in fields(counters):
        if field.name == "output_bf16_saturations":
            continue
        with pytest.raises(HCHeadReferenceError):
            replace(
                counters,
                **{field.name: getattr(counters, field.name) + 1},
            )
    with pytest.raises(HCHeadReferenceError, match="exceeds output conversions"):
        replace(
            counters,
            output_bf16_saturations=counters.output_bf16_values + 1,
        )


def test_public_diagnostics_require_deeply_immutable_exact_shapes() -> None:
    diagnostics = _execute().diagnostics
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(
            diagnostics,
            mean_square_codes=list(diagnostics.mean_square_codes),
        )
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(
            diagnostics,
            projection_codes=(list(diagnostics.projection_codes[0]),),
        )
    with pytest.raises(HCHeadReferenceError, match="exactly 4 values"):
        replace(
            diagnostics,
            projection_codes=(diagnostics.projection_codes[0][:-1],),
        )
    with pytest.raises(HCHeadReferenceError, match="32-bit binary32"):
        replace(diagnostics, mean_square_codes=(True,))
    with pytest.raises(HCHeadReferenceError, match="finite binary32"):
        replace(diagnostics, affine_codes=((0x7F800000, 0, 0, 0),))


def test_public_diagnostics_reconcile_every_retained_numeric_derivation() -> None:
    diagnostics = _execute().diagnostics
    with pytest.raises(HCHeadReferenceError, match="nonnegative"):
        replace(diagnostics, mean_square_codes=(0x80000000,))
    with pytest.raises(HCHeadReferenceError, match="positive"):
        replace(diagnostics, inverse_rms_codes=(0,))
    with pytest.raises(HCHeadReferenceError, match="inverse-RMS"):
        replace(diagnostics, inverse_rms_codes=(ONE_F32,))
    with pytest.raises(HCHeadReferenceError, match="normalized projections"):
        replace(diagnostics, projection_codes=((ONE_F32, 0, 0, 0),))
    with pytest.raises(HCHeadReferenceError, match="normalized projections"):
        replace(
            diagnostics,
            normalized_projection_codes=((ONE_F32, 0, 0, 0),),
        )
    with pytest.raises(HCHeadReferenceError, match="sigmoid codes"):
        replace(diagnostics, affine_codes=((ONE_F32, 0, 0, 0),))
    with pytest.raises(HCHeadReferenceError, match="sigmoid codes"):
        replace(diagnostics, sigmoid_codes=((0, 0x3F000000, 0x3F000000, 0x3F000000),))
    with pytest.raises(HCHeadReferenceError, match="coefficient codes"):
        replace(
            diagnostics, coefficient_codes=((0, 0x3F000011, 0x3F000011, 0x3F000011),)
        )


@pytest.mark.parametrize("profile", [True, 0, "wrong.profile"])
def test_public_result_binds_the_exact_numeric_profile(profile: object) -> None:
    result = _execute()
    assert result.numeric_profile == HC_HEAD_NUMERIC_PROFILE
    with pytest.raises(HCHeadReferenceError, match="numeric_profile"):
        replace(result, numeric_profile=profile)


def test_public_result_requires_deeply_immutable_exact_shapes() -> None:
    result = _execute()
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(result, output_bf16_codes=[list(result.output_bf16_codes[0])])
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(result, output_bf16_codes=(list(result.output_bf16_codes[0]),))
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(
            result,
            coefficient_binary32_codes=[list(result.coefficient_binary32_codes[0])],
        )
    with pytest.raises(HCHeadReferenceError, match="deeply immutable"):
        replace(
            result,
            coefficient_binary32_codes=(list(result.coefficient_binary32_codes[0]),),
        )
    with pytest.raises(HCHeadReferenceError, match="exactly 4096"):
        replace(result, output_bf16_codes=(result.output_bf16_codes[0][:-1],))
    with pytest.raises(HCHeadReferenceError, match="finite BF16"):
        replace(
            result,
            output_bf16_codes=((0x7F80,) + result.output_bf16_codes[0][1:],),
        )
    with pytest.raises(HCHeadReferenceError, match="finite binary32"):
        replace(
            result,
            coefficient_binary32_codes=(
                (0x7F800000,) + result.coefficient_binary32_codes[0][1:],
            ),
        )


def test_public_result_reconciles_diagnostics_counters_and_saturation() -> None:
    result = _execute()
    two_token_result = _execute((ZERO_TOKEN, ZERO_TOKEN))
    coefficient = result.coefficient_binary32_codes[0]
    with pytest.raises(HCHeadReferenceError, match="diagnostic coefficients"):
        replace(
            result,
            coefficient_binary32_codes=((0,) + coefficient[1:],),
        )
    with pytest.raises(HCHeadReferenceError, match="diagnostics token count"):
        replace(result, diagnostics=two_token_result.diagnostics)
    with pytest.raises(HCHeadReferenceError, match="counter token count"):
        replace(result, counters=two_token_result.counters)
    with pytest.raises(HCHeadReferenceError, match="exact nonnegative integer"):
        replace(result, output_saturation_count=True)
    with pytest.raises(HCHeadReferenceError, match="maximum-finite"):
        replace(result, output_saturation_count=1)
    saturation_counter = replace(result.counters, output_bf16_saturations=1)
    with pytest.raises(HCHeadReferenceError, match="saturation"):
        replace(result, counters=saturation_counter)
    with pytest.raises(HCHeadReferenceError, match="exact HCHeadDiagnostics"):
        replace(result, diagnostics=object())
    with pytest.raises(HCHeadReferenceError, match="exact HCHeadCounters"):
        replace(result, counters=object())


def test_public_records_reject_subclass_authority() -> None:
    result = _execute()

    class CounterSubclass(HCHeadCounters):
        pass

    class DiagnosticsSubclass(HCHeadDiagnostics):
        pass

    class ResultSubclass(HCHeadResult):
        pass

    counter_fields = {
        field.name: getattr(result.counters, field.name)
        for field in fields(result.counters)
    }
    diagnostic_fields = {
        field.name: getattr(result.diagnostics, field.name)
        for field in fields(result.diagnostics)
    }
    result_fields = {
        field.name: getattr(result, field.name) for field in fields(result)
    }
    with pytest.raises(HCHeadReferenceError, match="exact HCHeadCounters"):
        CounterSubclass(**counter_fields)
    with pytest.raises(HCHeadReferenceError, match="exact HCHeadDiagnostics"):
        DiagnosticsSubclass(**diagnostic_fields)
    with pytest.raises(HCHeadReferenceError, match="exact HCHeadResult"):
        ResultSubclass(**result_fields)


def test_public_records_have_no_writable_instance_dictionary() -> None:
    result = _execute()
    for record in (result, result.diagnostics, result.counters):
        assert not hasattr(record, "__dict__")
        with pytest.raises(TypeError):
            vars(record)

    with pytest.raises(FrozenInstanceError):
        result.numeric_profile = "forged"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.counters.transaction_commits = 99  # type: ignore[misc]


def test_result_and_counter_contracts_are_explicit_and_physically_agnostic() -> None:
    assert [field.name for field in fields(HCHeadResult)] == [
        "numeric_profile",
        "output_bf16_codes",
        "coefficient_binary32_codes",
        "output_saturation_count",
        "diagnostics",
        "counters",
    ]
    counter_names = {field.name for field in fields(HCHeadCounters)}
    assert len(counter_names) == 27
    prohibited = {
        "cycle",
        "latency",
        "bandwidth",
        "energy",
        "power",
        "area",
        "frequency",
        "throughput",
    }
    assert not any(term in name for name in counter_names for term in prohibited)
    assert set(EXCLUDED_SYSTEM_CLAIMS) == {
        "authenticated_transaction_provenance",
        "complete_sequence_tiling_or_execution",
        "checkpoint_payload_identity",
        "semantic_graph_qualification",
        "full_model_execution",
        "service_engine_execution",
        "rtl_execution",
        "physical_schedule",
        "cycles_bandwidth_latency_energy_area_ppa",
        "gpu_performance_advantage",
    }
