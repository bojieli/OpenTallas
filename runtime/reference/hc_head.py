"""Deterministic target-format reference for DeepSeek V4 ``HC_HEAD``.

The pinned release uses this operator twice: once after the 43 main blocks and
once after the final DSpark block.  Both sites consume four BF16 hidden streams
of width 4096 and use checkpoint FP32 parameters with shapes ``[4, 16384]``,
``[1]``, and ``[4]``.

PyTorch does not define a backend-independent association for the RMS or
matrix/reduction expressions in ``Block.hc_head``.  OpenTallas therefore
freezes an explicit target profile:

* BF16 inputs widen exactly to binary32 and arithmetic zero is canonicalized
  to positive zero;
* squares reduce with the NUM-6.1 balanced binary32 tree, followed by one
  binary32 divide, the pinned ``1e-6`` add, and correctly rounded binary32
  reciprocal square root;
* each of four projection rows uses increasing-K exact-product binary32 RNE
  product-adds, followed by one separately rounded inverse-RMS multiply;
* the learned scalar multiply and base add are separate binary32 operations;
* sigmoid is correctly rounded to binary32, followed by one binary32 add of
  the pinned HC epsilon; and
* four coefficient/input products reduce through the NUM-6.1 balanced tree
  and convert once to BF16.

This module is independent of compiler lowering, service-engine execution,
microcode, schedules, and RTL.  Its counters describe only functional work;
they are not cycle, bandwidth, latency, energy, area, PPA, or GPU claims.
Public structural-record constructors require deeply immutable exact-tuple
tensors and reconcile every relationship derivable from their retained
fields.  Because they do not retain the input streams or parameters, they are
not authenticated transaction evidence and cannot prove checkpoint payload
provenance, graph qualification, or full-model execution.

The four-token limit is the bounded reference transaction extent used for
numeric qualification.  HC_HEAD has no cross-token reduction, so a later
compiler may tile a longer batch/sequence axis, but this module does not by
itself establish that tiling, its schedule, or complete-sequence execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    binary32_product_add,
    binary32_rsqrt,
    decode_bf16,
    decode_binary32,
)
from .hyper_connection import binary32_sigmoid_rne


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
HC_HEAD_NUMERIC_PROFILE = "opentallas.deepseek_v4_hc_head_numeric.v1"

MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
HC_MULTIPLIER = 4
HIDDEN_SIZE = 4096
FLATTENED_WIDTH = HC_MULTIPLIER * HIDDEN_SIZE
PROJECTION_ROWS = HC_MULTIPLIER
NORMALIZATION_EPSILON_BINARY32 = 0x358637BD
HC_EPSILON_BINARY32 = 0x358637BD
FLATTENED_WIDTH_BINARY32 = 0x46800000
F32_BYTES = 4
BF16_BYTES = 2

INFERENCE_CONFIG_EXPECTED_FIELDS = (
    ("dim", HIDDEN_SIZE),
    ("hc_mult", HC_MULTIPLIER),
)
SOURCE_EXPRESSIONS = (
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

EXCLUDED_SYSTEM_CLAIMS = (
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
)


BF16Vector: TypeAlias = tuple[int, ...]
BF16HCRow: TypeAlias = tuple[BF16Vector, ...]
BF16HCTensor: TypeAlias = tuple[BF16HCRow, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Vector, ...]


class HCHeadReferenceError(ValueError):
    """Raised when an HC_HEAD transaction is malformed or poisoned."""


@dataclass(frozen=True, slots=True)
class HCHeadCounters:
    """Exact shape-derived functional work for one HC_HEAD transaction."""

    token_count: int
    input_bf16_values: int
    input_read_bytes: int
    projection_parameter_f32_values: int
    projection_parameter_bytes: int
    scale_parameter_f32_values: int
    scale_parameter_bytes: int
    base_parameter_f32_values: int
    base_parameter_bytes: int
    rms_square_multiplies: int
    rms_reduction_adds: int
    rms_divides: int
    rms_epsilon_adds: int
    rsqrt_evaluations: int
    projection_product_accumulates: int
    projection_inverse_rms_multiplies: int
    coefficient_scale_multiplies: int
    coefficient_base_adds: int
    sigmoid_evaluations: int
    coefficient_epsilon_adds: int
    branch_coefficient_multiplies: int
    branch_reduction_adds: int
    output_bf16_conversions: int
    output_bf16_saturations: int
    output_bf16_values: int
    output_write_bytes: int
    transaction_commits: int

    def __post_init__(self) -> None:
        """Reject malformed functional accounting at the public constructor."""

        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class HCHeadDiagnostics:
    """Every architecturally relevant binary32 boundary before BF16 output."""

    mean_square_codes: Binary32Vector
    inverse_rms_codes: Binary32Vector
    projection_codes: Binary32Matrix
    normalized_projection_codes: Binary32Matrix
    affine_codes: Binary32Matrix
    sigmoid_codes: Binary32Matrix
    coefficient_codes: Binary32Matrix

    def __post_init__(self) -> None:
        """Require immutable shapes and reconcile retained numeric boundaries."""

        _validate_diagnostics(self)


@dataclass(frozen=True, slots=True)
class HCHeadResult:
    """Immutable output, coefficients, diagnostics, and functional accounting."""

    numeric_profile: str
    output_bf16_codes: BF16Matrix
    coefficient_binary32_codes: Binary32Matrix
    output_saturation_count: int
    diagnostics: HCHeadDiagnostics
    counters: HCHeadCounters

    def __post_init__(self) -> None:
        """Require an immutable, structurally reconciled reference record."""

        _validate_result(self)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise HCHeadReferenceError(f"{label} must be an exact list or tuple")
    return value


def _finite_binary32(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int or not 0 <= value < 1 << 32:
        raise HCHeadReferenceError(f"{label} must be a 32-bit binary32 encoding")
    decoded = decode_binary32(value)
    if not decoded.finite or decoded.value is None:
        raise HCHeadReferenceError(f"{label} must be finite binary32")
    return value, decoded.value


def _finite_binary32_vector(
    value: object,
    *,
    label: str,
    width: int,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    raw = _sequence(value, label)
    if len(raw) != width:
        raise HCHeadReferenceError(f"{label} must contain exactly {width} values")
    codes: list[int] = []
    values: list[Fraction] = []
    for index, item in enumerate(raw):
        code, decoded = _finite_binary32(item, f"{label}[{index}]")
        codes.append(code)
        values.append(decoded)
    return tuple(codes), tuple(values)


def _counter_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise HCHeadReferenceError(f"{label} must be an exact nonnegative integer")
    return value


def _immutable_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise HCHeadReferenceError(
            f"{label} must be a deeply immutable exact-tuple value"
        )
    return value


def _immutable_binary32_vector(
    value: object,
    *,
    label: str,
    width: int,
) -> Binary32Vector:
    raw = _immutable_tuple(value, label)
    if len(raw) != width:
        raise HCHeadReferenceError(f"{label} must contain exactly {width} values")
    return tuple(
        _finite_binary32(code, f"{label}[{index}]")[0] for index, code in enumerate(raw)
    )


def _immutable_binary32_matrix(
    value: object,
    *,
    label: str,
    rows: int,
    columns: int,
) -> Binary32Matrix:
    raw_rows = _immutable_tuple(value, label)
    if len(raw_rows) != rows:
        raise HCHeadReferenceError(f"{label} must contain exactly {rows} rows")
    return tuple(
        _immutable_binary32_vector(
            row,
            label=f"{label}[{row_index}]",
            width=columns,
        )
        for row_index, row in enumerate(raw_rows)
    )


def _immutable_bf16_matrix(value: object, *, token_count: int) -> BF16Matrix:
    raw_rows = _immutable_tuple(value, "output_bf16_codes")
    if len(raw_rows) != token_count:
        raise HCHeadReferenceError(
            "output_bf16_codes token count must match coefficient rows"
        )
    rows: list[BF16Vector] = []
    for token_index, raw_row in enumerate(raw_rows):
        label = f"output_bf16_codes[{token_index}]"
        row = _immutable_tuple(raw_row, label)
        if len(row) != HIDDEN_SIZE:
            raise HCHeadReferenceError(
                f"{label} must contain exactly {HIDDEN_SIZE} values"
            )
        output: list[int] = []
        for column, code in enumerate(row):
            element_label = f"{label}[{column}]"
            if type(code) is not int or not 0 <= code < 1 << 16:
                raise HCHeadReferenceError(
                    f"{element_label} must be a 16-bit BF16 encoding"
                )
            decoded = decode_bf16(code)
            if not decoded.finite or decoded.value is None:
                raise HCHeadReferenceError(f"{element_label} must be finite BF16")
            output.append(code)
        rows.append(tuple(output))
    return tuple(rows)


def _validate_counters(counters: object) -> HCHeadCounters:
    """Validate every scalar and shape-derived HC_HEAD counter formula."""

    if type(counters) is not HCHeadCounters:
        raise HCHeadReferenceError("counters must be an exact HCHeadCounters record")
    values = {
        name: _counter_integer(getattr(counters, name), f"counters.{name}")
        for name in counters.__dataclass_fields__
    }
    token_count = values["token_count"]
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCHeadReferenceError(
            f"counters.token_count must be in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )
    input_values = token_count * FLATTENED_WIDTH
    output_values = token_count * HIDDEN_SIZE
    expected = {
        "token_count": token_count,
        "input_bf16_values": input_values,
        "input_read_bytes": input_values * BF16_BYTES,
        "projection_parameter_f32_values": PROJECTION_ROWS * FLATTENED_WIDTH,
        "projection_parameter_bytes": (PROJECTION_ROWS * FLATTENED_WIDTH * F32_BYTES),
        "scale_parameter_f32_values": 1,
        "scale_parameter_bytes": F32_BYTES,
        "base_parameter_f32_values": PROJECTION_ROWS,
        "base_parameter_bytes": PROJECTION_ROWS * F32_BYTES,
        "rms_square_multiplies": input_values,
        "rms_reduction_adds": token_count * (FLATTENED_WIDTH - 1),
        "rms_divides": token_count,
        "rms_epsilon_adds": token_count,
        "rsqrt_evaluations": token_count,
        "projection_product_accumulates": (
            token_count * PROJECTION_ROWS * FLATTENED_WIDTH
        ),
        "projection_inverse_rms_multiplies": token_count * PROJECTION_ROWS,
        "coefficient_scale_multiplies": token_count * PROJECTION_ROWS,
        "coefficient_base_adds": token_count * PROJECTION_ROWS,
        "sigmoid_evaluations": token_count * PROJECTION_ROWS,
        "coefficient_epsilon_adds": token_count * PROJECTION_ROWS,
        "branch_coefficient_multiplies": output_values * HC_MULTIPLIER,
        "branch_reduction_adds": output_values * (HC_MULTIPLIER - 1),
        "output_bf16_conversions": output_values,
        "output_bf16_values": output_values,
        "output_write_bytes": output_values * BF16_BYTES,
        "transaction_commits": 1,
    }
    for name, expected_value in expected.items():
        if values[name] != expected_value:
            raise HCHeadReferenceError(
                f"counters.{name} does not reconcile to the HC_HEAD dimensions"
            )
    if values["output_bf16_saturations"] > output_values:
        raise HCHeadReferenceError(
            "counters.output_bf16_saturations exceeds output conversions"
        )
    return counters


def _validate_diagnostics(diagnostics: object) -> HCHeadDiagnostics:
    """Validate immutable diagnostic shapes and every retained derivation."""

    if type(diagnostics) is not HCHeadDiagnostics:
        raise HCHeadReferenceError(
            "diagnostics must be an exact HCHeadDiagnostics record"
        )
    raw_means = _immutable_tuple(
        diagnostics.mean_square_codes,
        "diagnostics.mean_square_codes",
    )
    token_count = len(raw_means)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCHeadReferenceError(
            f"diagnostics token count must be in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )
    means = _immutable_binary32_vector(
        raw_means,
        label="diagnostics.mean_square_codes",
        width=token_count,
    )
    inverses = _immutable_binary32_vector(
        diagnostics.inverse_rms_codes,
        label="diagnostics.inverse_rms_codes",
        width=token_count,
    )
    matrices = {
        name: _immutable_binary32_matrix(
            getattr(diagnostics, name),
            label=f"diagnostics.{name}",
            rows=token_count,
            columns=PROJECTION_ROWS,
        )
        for name in (
            "projection_codes",
            "normalized_projection_codes",
            "affine_codes",
            "sigmoid_codes",
            "coefficient_codes",
        )
    }

    for token_index, (mean, inverse) in enumerate(zip(means, inverses, strict=True)):
        mean_value = _finite_binary32(
            mean,
            f"diagnostics.mean_square_codes[{token_index}]",
        )[1]
        inverse_value = _finite_binary32(
            inverse,
            f"diagnostics.inverse_rms_codes[{token_index}]",
        )[1]
        if mean_value < 0 or (mean_value == 0 and mean != 0):
            raise HCHeadReferenceError(
                "diagnostic mean-square codes must be nonnegative with canonical zero"
            )
        if inverse_value <= 0:
            raise HCHeadReferenceError(
                "diagnostic inverse-RMS codes must be positive binary32"
            )
        try:
            expected_inverse = binary32_rsqrt(
                binary32_add(mean, NORMALIZATION_EPSILON_BINARY32)
            )
            expected_normalized = tuple(
                binary32_multiply(code, inverse)
                for code in matrices["projection_codes"][token_index]
            )
            expected_sigmoid = tuple(
                binary32_sigmoid_rne(code)
                for code in matrices["affine_codes"][token_index]
            )
            expected_coefficients = tuple(
                binary32_add(code, HC_EPSILON_BINARY32) for code in expected_sigmoid
            )
        except (NumericReferenceError, ValueError) as exc:
            raise HCHeadReferenceError(
                f"diagnostics numeric boundary poisoned at token {token_index}: {exc}"
            ) from exc
        if inverse != expected_inverse:
            raise HCHeadReferenceError(
                "diagnostic inverse-RMS codes do not reconcile to mean squares"
            )
        if matrices["normalized_projection_codes"][token_index] != (
            expected_normalized
        ):
            raise HCHeadReferenceError(
                "diagnostic normalized projections do not reconcile to projection "
                "and inverse RMS"
            )
        if matrices["sigmoid_codes"][token_index] != expected_sigmoid:
            raise HCHeadReferenceError(
                "diagnostic sigmoid codes do not reconcile to affine codes"
            )
        if matrices["coefficient_codes"][token_index] != expected_coefficients:
            raise HCHeadReferenceError(
                "diagnostic coefficient codes do not reconcile to sigmoid codes"
            )
    return diagnostics


def _validate_result(result: object) -> HCHeadResult:
    """Validate retained structural consistency without asserting provenance."""

    if type(result) is not HCHeadResult:
        raise HCHeadReferenceError("result must be an exact HCHeadResult record")
    if (
        type(result.numeric_profile) is not str
        or result.numeric_profile != HC_HEAD_NUMERIC_PROFILE
    ):
        raise HCHeadReferenceError(
            f"numeric_profile must equal {HC_HEAD_NUMERIC_PROFILE!r}"
        )
    coefficients_raw = _immutable_tuple(
        result.coefficient_binary32_codes,
        "coefficient_binary32_codes",
    )
    token_count = len(coefficients_raw)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCHeadReferenceError(
            "coefficient_binary32_codes token count must be in "
            f"[{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )
    coefficients = _immutable_binary32_matrix(
        coefficients_raw,
        label="coefficient_binary32_codes",
        rows=token_count,
        columns=PROJECTION_ROWS,
    )
    output_codes = _immutable_bf16_matrix(
        result.output_bf16_codes,
        token_count=token_count,
    )
    saturation_count = _counter_integer(
        result.output_saturation_count,
        "output_saturation_count",
    )
    if saturation_count > token_count * HIDDEN_SIZE:
        raise HCHeadReferenceError(
            "output_saturation_count exceeds output BF16 conversions"
        )
    saturation_candidates = sum(
        code & 0x7FFF == 0x7F7F for row in output_codes for code in row
    )
    if saturation_count > saturation_candidates:
        raise HCHeadReferenceError(
            "output_saturation_count exceeds maximum-finite BF16 output candidates"
        )
    diagnostics = _validate_diagnostics(result.diagnostics)
    counters = _validate_counters(result.counters)
    if len(diagnostics.mean_square_codes) != token_count:
        raise HCHeadReferenceError(
            "diagnostics token count does not match result tensor shapes"
        )
    if coefficients != diagnostics.coefficient_codes:
        raise HCHeadReferenceError(
            "coefficient_binary32_codes do not match diagnostic coefficients"
        )
    if counters.token_count != token_count:
        raise HCHeadReferenceError(
            "counter token count does not match result tensor shapes"
        )
    if (
        counters.output_bf16_saturations != saturation_count
        or counters.output_bf16_values != token_count * HIDDEN_SIZE
    ):
        raise HCHeadReferenceError(
            "result saturation or output shape does not reconcile to counters"
        )
    return result


def _finite_projection(
    value: object,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[Fraction, ...], ...]]:
    raw_rows = _sequence(value, "projection_binary32_codes")
    if len(raw_rows) != PROJECTION_ROWS:
        raise HCHeadReferenceError(
            f"projection_binary32_codes must contain exactly {PROJECTION_ROWS} rows"
        )
    code_rows: list[tuple[int, ...]] = []
    value_rows: list[tuple[Fraction, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        codes, values = _finite_binary32_vector(
            raw_row,
            label=f"projection_binary32_codes[{row_index}]",
            width=FLATTENED_WIDTH,
        )
        code_rows.append(codes)
        value_rows.append(values)
    return tuple(code_rows), tuple(value_rows)


def _finite_input(value: object) -> BF16HCTensor:
    raw_tokens = _sequence(value, "input_bf16_codes")
    if not MIN_TOKEN_COUNT <= len(raw_tokens) <= MAX_TOKEN_COUNT:
        raise HCHeadReferenceError(
            "input_bf16_codes token dimension must be in "
            f"[{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )
    tokens: list[BF16HCRow] = []
    for token_index, raw_streams in enumerate(raw_tokens):
        streams = _sequence(raw_streams, f"input_bf16_codes[{token_index}]")
        if len(streams) != HC_MULTIPLIER:
            raise HCHeadReferenceError(
                f"input_bf16_codes[{token_index}] must contain exactly "
                f"{HC_MULTIPLIER} HC streams"
            )
        frozen_streams: list[BF16Vector] = []
        for stream_index, raw_stream in enumerate(streams):
            label = f"input_bf16_codes[{token_index}][{stream_index}]"
            stream = _sequence(raw_stream, label)
            if len(stream) != HIDDEN_SIZE:
                raise HCHeadReferenceError(
                    f"{label} must contain exactly {HIDDEN_SIZE} values"
                )
            output: list[int] = []
            for column, code in enumerate(stream):
                element_label = f"{label}[{column}]"
                if type(code) is not int or not 0 <= code < 1 << 16:
                    raise HCHeadReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite or decoded.value is None:
                    raise HCHeadReferenceError(f"{element_label} must be finite BF16")
                output.append(code)
            frozen_streams.append(tuple(output))
        tokens.append(tuple(frozen_streams))
    return tuple(tokens)


def _validate_contract(
    *,
    normalization_epsilon_binary32: object,
    hc_epsilon_binary32: object,
) -> None:
    if (
        type(normalization_epsilon_binary32) is not int
        or normalization_epsilon_binary32 != NORMALIZATION_EPSILON_BINARY32
    ):
        raise HCHeadReferenceError(
            "normalization_epsilon_binary32 must equal 0x358637bd"
        )
    if (
        type(hc_epsilon_binary32) is not int
        or hc_epsilon_binary32 != HC_EPSILON_BINARY32
    ):
        raise HCHeadReferenceError("hc_epsilon_binary32 must equal 0x358637bd")


def _flatten_token(
    streams: BF16HCRow,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    codes: list[int] = []
    values: list[Fraction] = []
    for stream in streams:
        for code in stream:
            decoded = decode_bf16(code)
            if decoded.value is None:  # pragma: no cover - validated above
                raise RuntimeError("validated HC_HEAD input became nonfinite")
            # The target profile canonicalizes arithmetic zero before FP32 work.
            codes.append(0 if decoded.value == 0 else code << 16)
            values.append(decoded.value)
    return tuple(codes), tuple(values)


def _project(
    input_values: tuple[Fraction, ...],
    projection_values: tuple[tuple[Fraction, ...], ...],
) -> tuple[int, ...]:
    nonzero_indices = tuple(
        index for index, input_value in enumerate(input_values) if input_value != 0
    )
    if not nonzero_indices:
        return (0,) * PROJECTION_ROWS

    outputs: list[int] = []
    for row in projection_values:
        accumulator = 0
        for index in nonzero_indices:
            weight = row[index]
            if weight != 0:
                accumulator = binary32_product_add(
                    accumulator,
                    input_values[index],
                    weight,
                )
        outputs.append(accumulator)
    return tuple(outputs)


def _counters(token_count: int, saturation_count: int) -> HCHeadCounters:
    input_values = token_count * FLATTENED_WIDTH
    output_values = token_count * HIDDEN_SIZE
    return HCHeadCounters(
        token_count=token_count,
        input_bf16_values=input_values,
        input_read_bytes=input_values * BF16_BYTES,
        projection_parameter_f32_values=PROJECTION_ROWS * FLATTENED_WIDTH,
        projection_parameter_bytes=PROJECTION_ROWS * FLATTENED_WIDTH * F32_BYTES,
        scale_parameter_f32_values=1,
        scale_parameter_bytes=F32_BYTES,
        base_parameter_f32_values=PROJECTION_ROWS,
        base_parameter_bytes=PROJECTION_ROWS * F32_BYTES,
        rms_square_multiplies=input_values,
        rms_reduction_adds=token_count * (FLATTENED_WIDTH - 1),
        rms_divides=token_count,
        rms_epsilon_adds=token_count,
        rsqrt_evaluations=token_count,
        projection_product_accumulates=(
            token_count * PROJECTION_ROWS * FLATTENED_WIDTH
        ),
        projection_inverse_rms_multiplies=token_count * PROJECTION_ROWS,
        coefficient_scale_multiplies=token_count * PROJECTION_ROWS,
        coefficient_base_adds=token_count * PROJECTION_ROWS,
        sigmoid_evaluations=token_count * PROJECTION_ROWS,
        coefficient_epsilon_adds=token_count * PROJECTION_ROWS,
        branch_coefficient_multiplies=output_values * HC_MULTIPLIER,
        branch_reduction_adds=output_values * (HC_MULTIPLIER - 1),
        output_bf16_conversions=output_values,
        output_bf16_saturations=saturation_count,
        output_bf16_values=output_values,
        output_write_bytes=output_values * BF16_BYTES,
        transaction_commits=1,
    )


def hc_head_bf16(
    input_bf16_codes: object,
    projection_binary32_codes: object,
    scale_binary32_codes: object,
    base_binary32_codes: object,
    *,
    normalization_epsilon_binary32: int = NORMALIZATION_EPSILON_BINARY32,
    hc_epsilon_binary32: int = HC_EPSILON_BINARY32,
) -> HCHeadResult:
    """Execute one immutable, fail-closed DeepSeek V4 HC_HEAD transaction."""

    _validate_contract(
        normalization_epsilon_binary32=normalization_epsilon_binary32,
        hc_epsilon_binary32=hc_epsilon_binary32,
    )
    inputs = _finite_input(input_bf16_codes)
    scales, _ = _finite_binary32_vector(
        scale_binary32_codes,
        label="scale_binary32_codes",
        width=1,
    )
    bases, _ = _finite_binary32_vector(
        base_binary32_codes,
        label="base_binary32_codes",
        width=PROJECTION_ROWS,
    )
    _, projection_values = _finite_projection(projection_binary32_codes)

    flattened_codes: list[tuple[int, ...]] = []
    means: list[int] = []
    inverses: list[int] = []
    projected_rows: list[Binary32Vector] = []
    normalized_rows: list[Binary32Vector] = []
    affine_rows: list[Binary32Vector] = []
    sigmoid_rows: list[Binary32Vector] = []
    coefficient_rows: list[Binary32Vector] = []

    for token_index, streams in enumerate(inputs):
        input_codes, input_values = _flatten_token(streams)
        flattened_codes.append(input_codes)
        try:
            if all(value == 0 for value in input_values):
                square_sum = 0
            else:
                squares = tuple(binary32_multiply(code, code) for code in input_codes)
                square_sum = binary32_balanced_sum(squares)
            mean = binary32_divide(square_sum, FLATTENED_WIDTH_BINARY32)
            biased_mean = binary32_add(mean, NORMALIZATION_EPSILON_BINARY32)
            inverse = binary32_rsqrt(biased_mean)
            projection = _project(input_values, projection_values)
            normalized = tuple(binary32_multiply(code, inverse) for code in projection)
            affine = tuple(
                binary32_add(
                    binary32_multiply(code, scales[0]),
                    bases[row],
                )
                for row, code in enumerate(normalized)
            )
            sigmoid = tuple(binary32_sigmoid_rne(code) for code in affine)
            coefficients = tuple(
                binary32_add(code, HC_EPSILON_BINARY32) for code in sigmoid
            )
        except (NumericReferenceError, ValueError) as exc:
            raise HCHeadReferenceError(
                f"HC_HEAD coefficient generation failed at token {token_index}: {exc}"
            ) from exc
        means.append(mean)
        inverses.append(inverse)
        projected_rows.append(projection)
        normalized_rows.append(normalized)
        affine_rows.append(affine)
        sigmoid_rows.append(sigmoid)
        coefficient_rows.append(coefficients)

    output_rows: list[BF16Vector] = []
    saturation_count = 0
    for token_index, (input_codes, coefficients) in enumerate(
        zip(flattened_codes, coefficient_rows, strict=True)
    ):
        output: list[int] = []
        for column in range(HIDDEN_SIZE):
            try:
                products = tuple(
                    binary32_multiply(
                        coefficients[stream],
                        input_codes[stream * HIDDEN_SIZE + column],
                    )
                    for stream in range(HC_MULTIPLIER)
                )
                total = binary32_balanced_sum(products)
                converted = binary32_bits_to_bf16_rne(total)
            except NumericReferenceError as exc:
                raise HCHeadReferenceError(
                    "HC_HEAD stream reduction failed at token "
                    f"{token_index}, column {column}: {exc}"
                ) from exc
            output.append(converted.code)
            saturation_count += int(converted.saturated)
        output_rows.append(tuple(output))

    diagnostics = HCHeadDiagnostics(
        mean_square_codes=tuple(means),
        inverse_rms_codes=tuple(inverses),
        projection_codes=tuple(projected_rows),
        normalized_projection_codes=tuple(normalized_rows),
        affine_codes=tuple(affine_rows),
        sigmoid_codes=tuple(sigmoid_rows),
        coefficient_codes=tuple(coefficient_rows),
    )
    return HCHeadResult(
        numeric_profile=HC_HEAD_NUMERIC_PROFILE,
        output_bf16_codes=tuple(output_rows),
        coefficient_binary32_codes=tuple(coefficient_rows),
        output_saturation_count=saturation_count,
        diagnostics=diagnostics,
        counters=_counters(len(inputs), saturation_count),
    )


__all__ = [
    "BF16_BYTES",
    "EXCLUDED_SYSTEM_CLAIMS",
    "F32_BYTES",
    "FLATTENED_WIDTH",
    "FLATTENED_WIDTH_BINARY32",
    "HC_EPSILON_BINARY32",
    "HC_HEAD_NUMERIC_PROFILE",
    "HC_MULTIPLIER",
    "HIDDEN_SIZE",
    "INFERENCE_CONFIG_EXPECTED_FIELDS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "MAX_TOKEN_COUNT",
    "MIN_TOKEN_COUNT",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "NORMALIZATION_EPSILON_BINARY32",
    "PROJECTION_ROWS",
    "SOURCE_EXPRESSIONS",
    "HCHeadCounters",
    "HCHeadDiagnostics",
    "HCHeadReferenceError",
    "HCHeadResult",
    "hc_head_bf16",
]
