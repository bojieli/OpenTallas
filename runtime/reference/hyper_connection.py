"""Deterministic independent reference for DeepSeek V4 ``HC_PRE``.

The official release leaves FP32 GEMM association, reductions, reciprocal
square root, TileLang ``exp``/``sigmoid``, and flush-to-zero behavior dependent
on the execution backend.  This module freezes an OpenTallas target profile at
those boundaries.  It is independent of compiler lowering, service-engine
execution, and RTL, and deliberately makes no claim of bit identity with the
official CUDA/TileLang implementation.

The profile is:

* finite BF16 input with shape ``[T, 4, 4096]`` for ``1 <= T <= 4``;
* a width-16384 binary32 RMS calculation using the NUM-6.1 balanced tree;
* 24 projection rows accumulated in increasing K order with NUM-4.1 exact
  products and one binary32 RNE result per product-add;
* a separate binary32 multiply and add for every learned affine transform;
* correctly rounded binary32 logistic and nonpositive exponential functions,
  proved by exact rational enclosures rather than host floating point;
* balanced four-term sums for the initial row softmax, followed by one initial
  column normalization and 19 row/column normalization stages, using the same
  tree at every Sinkhorn normalization; and
* four binary32 branch products reduced by a balanced tree and converted once
  to BF16.

All validation and arithmetic complete before an immutable result is returned.
Any malformed or exceptional input raises :class:`HCPreReferenceError`, so a
caller cannot observe a partially committed architectural result.

Public records require deeply immutable exact-tuple payloads, bind the numeric
profile, and reconcile every shape, counter, and retained numeric relationship
that their fields can prove.  They do not retain learned parameters or input
provenance, so even a valid record is not authenticated checkpoint, compiler,
service-engine, RTL, physical, or performance evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
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
    encode_binary32_rne,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_PATH = "inference/kernel.py"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
NUMERIC_PROFILE = "opentallas.deepseek_v4_hc_pre_numeric.v1"

MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
HC_MULTIPLIER = 4
HIDDEN_SIZE = 4096
FLATTENED_WIDTH = HC_MULTIPLIER * HIDDEN_SIZE
MIX_PARAMETER_COUNT = (2 + HC_MULTIPLIER) * HC_MULTIPLIER
SINKHORN_ITERATIONS = 20
NORMALIZATION_EPSILON_BINARY32 = 0x358637BD
SINKHORN_EPSILON_BINARY32 = 0x358637BD

_BINARY32_ONE = 0x3F800000
_BINARY32_TWO = 0x40000000
_BINARY32_WIDTH = 0x46800000  # exactly 16384
_TRANSCENDENTAL_INITIAL_PRECISION = 48

INFERENCE_CONFIG_EXPECTED_FIELDS = (
    ("dim", HIDDEN_SIZE),
    ("hc_mult", HC_MULTIPLIER),
    ("hc_sinkhorn_iters", SINKHORN_ITERATIONS),
)
MODEL_SOURCE_EXPRESSIONS = (
    "x = x.flatten(2).float()",
    "rsqrt = torch.rsqrt(x.square().mean(-1, keepdim=True) + self.norm_eps)",
    "mixes = F.linear(x, hc_fn) * rsqrt",
    "pre, post, comb = hc_split_sinkhorn(mixes, hc_scale, hc_base, self.hc_mult, self.hc_sinkhorn_iters, self.hc_eps)",
    "y = torch.sum(pre.unsqueeze(-1) * x.view(shape), dim=2)",
    "return y.to(dtype), post, comb",
)
KERNEL_SOURCE_EXPRESSIONS = (
    "pre[i, j] = T.sigmoid(mixes_shared[j] * hc_scale[0] + hc_base[j]) + eps",
    "post[i, j] = 2 * T.sigmoid(mixes_shared[j + hc] * hc_scale[1] + hc_base[j + hc])",
    "T.reduce_max(comb_frag, row_max, dim=1)",
    "comb_frag[j, k] = T.exp(comb_frag[j, k] - row_max[j])",
    "T.reduce_sum(comb_frag, row_sum, dim=1)",
    "T.reduce_sum(comb_frag, col_sum, dim=0)",
    "for _ in T.serial(sinkhorn_iters - 1)",
)
EXCLUDED_SYSTEM_CLAIMS = (
    "authenticated_transaction_provenance",
    "complete_sequence_tiling_or_execution",
    "official_backend_bit_equivalence",
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
Binary32Tensor3: TypeAlias = tuple[Binary32Matrix, ...]
SinkhornStages: TypeAlias = tuple[Binary32Tensor3, ...]


class HCPreReferenceError(ValueError):
    """Raised when an HC_PRE transaction is malformed or numerically poisoned."""


@dataclass(frozen=True, slots=True)
class TranscendentalRounding:
    """One CR32 code and the exact-interval resources needed to resolve it."""

    code: int
    interval_evaluations: int
    final_precision_bits: int

    def __post_init__(self) -> None:
        _validate_transcendental_rounding(self)


TranscendentalVector: TypeAlias = tuple[TranscendentalRounding, ...]
TranscendentalMatrix: TypeAlias = tuple[TranscendentalVector, ...]
TranscendentalTensor3: TypeAlias = tuple[TranscendentalMatrix, ...]


@dataclass(frozen=True, slots=True)
class HCSplitDiagnostics:
    """Every visible affine, nonlinear, softmax, and Sinkhorn boundary."""

    pre_affine_codes: Binary32Matrix
    pre_sigmoid_codes: Binary32Matrix
    post_affine_codes: Binary32Matrix
    post_sigmoid_codes: Binary32Matrix
    comb_affine_codes: Binary32Tensor3
    softmax_codes: Binary32Tensor3
    pre_sigmoid_rounding: TranscendentalMatrix
    post_sigmoid_rounding: TranscendentalMatrix
    softmax_exp_rounding: TranscendentalTensor3
    # Outer dimension is the exact 20 completed column-normalized stages.
    sinkhorn_stage_codes: SinkhornStages

    def __post_init__(self) -> None:
        _validate_split_diagnostics(self)


@dataclass(frozen=True, slots=True)
class HCSplitResult:
    """The architectural pre/post/comb coefficients plus retained diagnostics."""

    pre_binary32_codes: Binary32Matrix
    post_binary32_codes: Binary32Matrix
    comb_binary32_codes: Binary32Tensor3
    diagnostics: HCSplitDiagnostics

    def __post_init__(self) -> None:
        _validate_split_result(self)


@dataclass(frozen=True, slots=True)
class HCPreCounters:
    """Exact semantic-work counts for later artifact/runtime differentials."""

    hc_pre_token_count: int
    hc_pre_input_bf16_values: int
    hc_pre_rms_square_multiplies: int
    hc_pre_rms_reduction_adds: int
    hc_pre_rms_divides: int
    hc_pre_rms_epsilon_adds: int
    hc_pre_rsqrt_evaluations: int
    hc_pre_projection_product_accumulates: int
    hc_pre_projection_rms_multiplies: int
    hc_pre_field_affine_multiplies: int
    hc_pre_field_affine_adds: int
    hc_pre_sigmoid_evaluations: int
    hc_pre_coefficient_epsilon_adds: int
    hc_pre_post_factor_multiplies: int
    hc_pre_softmax_max_comparisons: int
    hc_pre_softmax_subtracts: int
    hc_pre_exp_evaluations: int
    hc_pre_sinkhorn_row_stages: int
    hc_pre_sinkhorn_column_stages: int
    hc_pre_sinkhorn_row_reduction_adds: int
    hc_pre_sinkhorn_column_reduction_adds: int
    hc_pre_sinkhorn_divides: int
    hc_pre_sinkhorn_epsilon_adds: int
    hc_pre_branch_coefficient_multiplies: int
    hc_pre_branch_reduction_adds: int
    hc_pre_branch_bf16_conversions: int
    hc_pre_branch_bf16_saturations: int
    hc_pre_residual_bf16_values_preserved: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class HCPreDiagnostics:
    """Retained normalization, projection, and coefficient-generation state."""

    mean_square_codes: Binary32Vector
    inverse_rms_codes: Binary32Vector
    projection_codes: Binary32Matrix
    normalized_projection_codes: Binary32Matrix
    split: HCSplitDiagnostics

    def __post_init__(self) -> None:
        _validate_pre_diagnostics(self)


@dataclass(frozen=True, slots=True)
class HCPreResult:
    """All architectural HC_PRE outputs from one committed transaction."""

    numeric_profile: str
    branch_bf16_codes: BF16Matrix
    pre_binary32_codes: Binary32Matrix
    post_binary32_codes: Binary32Matrix
    comb_binary32_codes: Binary32Tensor3
    residual_bf16_codes: BF16HCTensor
    branch_output_saturation_count: int
    diagnostics: HCPreDiagnostics
    counters: HCPreCounters

    def __post_init__(self) -> None:
        _validate_pre_result(self)


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise HCPreReferenceError(f"{label} must be a sequence")
    return value


def _finite_binary32_code(value: object, label: str) -> tuple[int, Fraction]:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << 32
    ):
        raise HCPreReferenceError(f"{label} must be a 32-bit binary32 encoding")
    decoded = decode_binary32(value)
    if not decoded.finite or decoded.value is None:
        raise HCPreReferenceError(f"{label} must be finite binary32")
    return value, decoded.value


def _finite_binary32_vector(
    value: object,
    *,
    label: str,
    width: int,
) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if len(raw) != width:
        raise HCPreReferenceError(f"{label} must contain exactly {width} values")
    return tuple(
        _finite_binary32_code(code, f"{label}[{index}]")[0]
        for index, code in enumerate(raw)
    )


def _finite_projection(value: object) -> tuple[tuple[int, ...], ...]:
    raw_rows = _sequence(value, "projection_binary32_codes")
    if len(raw_rows) != MIX_PARAMETER_COUNT:
        raise HCPreReferenceError(
            f"projection_binary32_codes must contain exactly {MIX_PARAMETER_COUNT} rows"
        )
    return tuple(
        _finite_binary32_vector(
            row,
            label=f"projection_binary32_codes[{row_index}]",
            width=FLATTENED_WIDTH,
        )
        for row_index, row in enumerate(raw_rows)
    )


def _finite_hc_input(value: object) -> BF16HCTensor:
    raw_tokens = _sequence(value, "input_bf16_codes")
    if not MIN_TOKEN_COUNT <= len(raw_tokens) <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError(
            "input_bf16_codes token dimension must be in "
            f"[{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )

    tokens: list[BF16HCRow] = []
    for token_index, raw_streams in enumerate(raw_tokens):
        streams = _sequence(raw_streams, f"input_bf16_codes[{token_index}]")
        if len(streams) != HC_MULTIPLIER:
            raise HCPreReferenceError(
                f"input_bf16_codes[{token_index}] must contain exactly "
                f"{HC_MULTIPLIER} HC streams"
            )
        output_streams: list[BF16Vector] = []
        for stream_index, raw_stream in enumerate(streams):
            label = f"input_bf16_codes[{token_index}][{stream_index}]"
            stream = _sequence(raw_stream, label)
            if len(stream) != HIDDEN_SIZE:
                raise HCPreReferenceError(
                    f"{label} must contain exactly {HIDDEN_SIZE} values"
                )
            output: list[int] = []
            for column, code in enumerate(stream):
                element_label = f"{label}[{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code < 1 << 16
                ):
                    raise HCPreReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite or decoded.value is None:
                    raise HCPreReferenceError(f"{element_label} must be finite BF16")
                output.append(code)
            output_streams.append(tuple(output))
        tokens.append(tuple(output_streams))
    return tuple(tokens)


def _exact_nonnegative_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise HCPreReferenceError(f"{label} must be an exact nonnegative integer")
    return value


def _immutable_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise HCPreReferenceError(
            f"{label} must be a deeply immutable exact-tuple value"
        )
    return value


def _immutable_binary32_code(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int:
        raise HCPreReferenceError(
            f"{label} must be an exact 32-bit binary32 encoding"
        )
    return _finite_binary32_code(value, label)


def _immutable_binary32_vector(
    value: object,
    *,
    label: str,
    width: int,
) -> Binary32Vector:
    raw = _immutable_tuple(value, label)
    if len(raw) != width:
        raise HCPreReferenceError(f"{label} must contain exactly {width} values")
    return tuple(
        _immutable_binary32_code(code, f"{label}[{index}]")[0]
        for index, code in enumerate(raw)
    )


def _immutable_binary32_matrix(
    value: object,
    *,
    label: str,
    rows: int,
    columns: int,
) -> Binary32Matrix:
    raw = _immutable_tuple(value, label)
    if len(raw) != rows:
        raise HCPreReferenceError(f"{label} must contain exactly {rows} rows")
    return tuple(
        _immutable_binary32_vector(
            row,
            label=f"{label}[{row_index}]",
            width=columns,
        )
        for row_index, row in enumerate(raw)
    )


def _immutable_binary32_tensor3(
    value: object,
    *,
    label: str,
    planes: int,
    rows: int,
    columns: int,
) -> Binary32Tensor3:
    raw = _immutable_tuple(value, label)
    if len(raw) != planes:
        raise HCPreReferenceError(f"{label} must contain exactly {planes} planes")
    return tuple(
        _immutable_binary32_matrix(
            plane,
            label=f"{label}[{plane_index}]",
            rows=rows,
            columns=columns,
        )
        for plane_index, plane in enumerate(raw)
    )


def _immutable_bf16_vector(
    value: object,
    *,
    label: str,
    width: int,
) -> BF16Vector:
    raw = _immutable_tuple(value, label)
    if len(raw) != width:
        raise HCPreReferenceError(f"{label} must contain exactly {width} values")
    output: list[int] = []
    for index, code in enumerate(raw):
        element_label = f"{label}[{index}]"
        if type(code) is not int or not 0 <= code < 1 << 16:
            raise HCPreReferenceError(
                f"{element_label} must be a 16-bit BF16 encoding"
            )
        decoded = decode_bf16(code)
        if not decoded.finite or decoded.value is None:
            raise HCPreReferenceError(f"{element_label} must be finite BF16")
        output.append(code)
    return tuple(output)


def _immutable_bf16_matrix(
    value: object,
    *,
    label: str,
    rows: int,
    columns: int,
) -> BF16Matrix:
    raw = _immutable_tuple(value, label)
    if len(raw) != rows:
        raise HCPreReferenceError(f"{label} must contain exactly {rows} rows")
    return tuple(
        _immutable_bf16_vector(
            row,
            label=f"{label}[{row_index}]",
            width=columns,
        )
        for row_index, row in enumerate(raw)
    )


def _immutable_bf16_hc_tensor(
    value: object,
    *,
    label: str,
    token_count: int,
) -> BF16HCTensor:
    raw = _immutable_tuple(value, label)
    if len(raw) != token_count:
        raise HCPreReferenceError(
            f"{label} must contain exactly {token_count} token rows"
        )
    output: list[BF16HCRow] = []
    for token_index, token_value in enumerate(raw):
        token_label = f"{label}[{token_index}]"
        token = _immutable_tuple(token_value, token_label)
        if len(token) != HC_MULTIPLIER:
            raise HCPreReferenceError(
                f"{token_label} must contain exactly {HC_MULTIPLIER} streams"
            )
        output.append(
            tuple(
                _immutable_bf16_vector(
                    stream,
                    label=f"{token_label}[{stream_index}]",
                    width=HIDDEN_SIZE,
                )
                for stream_index, stream in enumerate(token)
            )
        )
    return tuple(output)


def _immutable_transcendental_matrix(
    value: object,
    *,
    label: str,
    rows: int,
    columns: int,
) -> TranscendentalMatrix:
    raw = _immutable_tuple(value, label)
    if len(raw) != rows:
        raise HCPreReferenceError(f"{label} must contain exactly {rows} rows")
    output: list[TranscendentalVector] = []
    for row_index, row_value in enumerate(raw):
        row_label = f"{label}[{row_index}]"
        row = _immutable_tuple(row_value, row_label)
        if len(row) != columns:
            raise HCPreReferenceError(
                f"{row_label} must contain exactly {columns} values"
            )
        for column, item in enumerate(row):
            if type(item) is not TranscendentalRounding:
                raise HCPreReferenceError(
                    f"{row_label}[{column}] must be an exact "
                    "TranscendentalRounding record"
                )
        output.append(tuple(row))  # type: ignore[arg-type]
    return tuple(output)


def _immutable_transcendental_tensor3(
    value: object,
    *,
    label: str,
    planes: int,
    rows: int,
    columns: int,
) -> TranscendentalTensor3:
    raw = _immutable_tuple(value, label)
    if len(raw) != planes:
        raise HCPreReferenceError(f"{label} must contain exactly {planes} planes")
    return tuple(
        _immutable_transcendental_matrix(
            plane,
            label=f"{label}[{plane_index}]",
            rows=rows,
            columns=columns,
        )
        for plane_index, plane in enumerate(raw)
    )


def _validate_transcendental_rounding(
    rounding: object,
) -> TranscendentalRounding:
    if type(rounding) is not TranscendentalRounding:
        raise HCPreReferenceError(
            "rounding must be an exact TranscendentalRounding record"
        )
    _immutable_binary32_code(rounding.code, "rounding.code")
    evaluations = _exact_nonnegative_integer(
        rounding.interval_evaluations,
        "rounding.interval_evaluations",
    )
    precision = _exact_nonnegative_integer(
        rounding.final_precision_bits,
        "rounding.final_precision_bits",
    )
    if (evaluations == 0) != (precision == 0):
        raise HCPreReferenceError(
            "rounding interval evaluations and precision must both be zero or nonzero"
        )
    if evaluations:
        expected_precision = _TRANSCENDENTAL_INITIAL_PRECISION << (evaluations - 1)
        if precision != expected_precision:
            raise HCPreReferenceError(
                "rounding precision does not reconcile to interval evaluations"
            )
    return rounding


def _sinkhorn_stages_from_softmax(softmax: Binary32Matrix) -> SinkhornStages:
    matrix = [list(row) for row in softmax]

    def normalize_columns() -> None:
        sums = tuple(
            binary32_balanced_sum(
                matrix[row][column] for row in range(HC_MULTIPLIER)
            )
            for column in range(HC_MULTIPLIER)
        )
        denominators = tuple(
            binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in sums
        )
        for row in range(HC_MULTIPLIER):
            for column in range(HC_MULTIPLIER):
                matrix[row][column] = binary32_divide(
                    matrix[row][column], denominators[column]
                )

    def normalize_rows() -> None:
        sums = tuple(binary32_balanced_sum(row) for row in matrix)
        denominators = tuple(
            binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in sums
        )
        for row in range(HC_MULTIPLIER):
            for column in range(HC_MULTIPLIER):
                matrix[row][column] = binary32_divide(
                    matrix[row][column], denominators[row]
                )

    stages: list[Binary32Tensor3] = []
    normalize_columns()
    stages.append((tuple(tuple(row) for row in matrix),))
    for _ in range(1, SINKHORN_ITERATIONS):
        normalize_rows()
        normalize_columns()
        stages.append((tuple(tuple(row) for row in matrix),))
    return tuple(stages)


def _validate_split_diagnostics(
    diagnostics: object,
) -> HCSplitDiagnostics:
    if type(diagnostics) is not HCSplitDiagnostics:
        raise HCPreReferenceError(
            "split diagnostics must be an exact HCSplitDiagnostics record"
        )
    raw_pre_affine = _immutable_tuple(
        diagnostics.pre_affine_codes,
        "split.pre_affine_codes",
    )
    token_count = len(raw_pre_affine)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError(
            f"split diagnostic token count must be in [{MIN_TOKEN_COUNT}, "
            f"{MAX_TOKEN_COUNT}]"
        )
    pre_affine = _immutable_binary32_matrix(
        raw_pre_affine,
        label="split.pre_affine_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    pre_sigmoid = _immutable_binary32_matrix(
        diagnostics.pre_sigmoid_codes,
        label="split.pre_sigmoid_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    post_affine = _immutable_binary32_matrix(
        diagnostics.post_affine_codes,
        label="split.post_affine_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    post_sigmoid = _immutable_binary32_matrix(
        diagnostics.post_sigmoid_codes,
        label="split.post_sigmoid_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    comb_affine = _immutable_binary32_tensor3(
        diagnostics.comb_affine_codes,
        label="split.comb_affine_codes",
        planes=token_count,
        rows=HC_MULTIPLIER,
        columns=HC_MULTIPLIER,
    )
    softmax = _immutable_binary32_tensor3(
        diagnostics.softmax_codes,
        label="split.softmax_codes",
        planes=token_count,
        rows=HC_MULTIPLIER,
        columns=HC_MULTIPLIER,
    )
    pre_rounding = _immutable_transcendental_matrix(
        diagnostics.pre_sigmoid_rounding,
        label="split.pre_sigmoid_rounding",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    post_rounding = _immutable_transcendental_matrix(
        diagnostics.post_sigmoid_rounding,
        label="split.post_sigmoid_rounding",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    exp_rounding = _immutable_transcendental_tensor3(
        diagnostics.softmax_exp_rounding,
        label="split.softmax_exp_rounding",
        planes=token_count,
        rows=HC_MULTIPLIER,
        columns=HC_MULTIPLIER,
    )
    raw_stages = _immutable_tuple(
        diagnostics.sinkhorn_stage_codes,
        "split.sinkhorn_stage_codes",
    )
    if len(raw_stages) != SINKHORN_ITERATIONS:
        raise HCPreReferenceError(
            f"split.sinkhorn_stage_codes must contain exactly {SINKHORN_ITERATIONS} "
            "stages"
        )
    stages = tuple(
        _immutable_binary32_tensor3(
            stage,
            label=f"split.sinkhorn_stage_codes[{stage_index}]",
            planes=token_count,
            rows=HC_MULTIPLIER,
            columns=HC_MULTIPLIER,
        )
        for stage_index, stage in enumerate(raw_stages)
    )

    expected_stages_by_token: list[SinkhornStages] = []
    try:
        for token in range(token_count):
            expected_pre_rounding = tuple(
                binary32_sigmoid_rne_with_diagnostics(code)
                for code in pre_affine[token]
            )
            expected_post_rounding = tuple(
                binary32_sigmoid_rne_with_diagnostics(code)
                for code in post_affine[token]
            )
            if pre_rounding[token] != expected_pre_rounding or pre_sigmoid[token] != (
                tuple(item.code for item in expected_pre_rounding)
            ):
                raise HCPreReferenceError(
                    "split pre-sigmoid diagnostics do not reconcile"
                )
            if post_rounding[token] != expected_post_rounding or post_sigmoid[token] != (
                tuple(item.code for item in expected_post_rounding)
            ):
                raise HCPreReferenceError(
                    "split post-sigmoid diagnostics do not reconcile"
                )

            expected_softmax_rows: list[Binary32Vector] = []
            expected_exp_rows: list[TranscendentalVector] = []
            for row in comb_affine[token]:
                maximum = max(
                    row,
                    key=lambda code: _finite_binary32_code(
                        code, "split combination maximum candidate"
                    )[1],
                )
                expected_exp = tuple(
                    binary32_exp_rne_with_diagnostics(
                        binary32_add(code, maximum ^ 0x80000000)
                    )
                    for code in row
                )
                expected_exp_rows.append(expected_exp)
                exponential_codes = tuple(item.code for item in expected_exp)
                denominator = binary32_balanced_sum(exponential_codes)
                expected_softmax_rows.append(
                    tuple(
                        binary32_add(
                            binary32_divide(code, denominator),
                            SINKHORN_EPSILON_BINARY32,
                        )
                        for code in exponential_codes
                    )
                )
            if exp_rounding[token] != tuple(expected_exp_rows):
                raise HCPreReferenceError(
                    "split softmax exponential diagnostics do not reconcile"
                )
            expected_softmax = tuple(expected_softmax_rows)
            if softmax[token] != expected_softmax:
                raise HCPreReferenceError(
                    "split stable-softmax diagnostics do not reconcile"
                )
            expected_stages_by_token.append(
                _sinkhorn_stages_from_softmax(expected_softmax)
            )
    except NumericReferenceError as exc:
        raise HCPreReferenceError(
            f"split diagnostic numeric reconciliation poisoned: {exc}"
        ) from exc

    expected_stages = tuple(
        tuple(expected_stages_by_token[token][stage][0] for token in range(token_count))
        for stage in range(SINKHORN_ITERATIONS)
    )
    if stages != expected_stages:
        raise HCPreReferenceError(
            "split Sinkhorn stages do not reconcile to stable softmax"
        )
    return diagnostics


def _validate_split_result(result: object) -> HCSplitResult:
    if type(result) is not HCSplitResult:
        raise HCPreReferenceError("split result must be an exact HCSplitResult record")
    raw_pre = _immutable_tuple(result.pre_binary32_codes, "split result pre codes")
    token_count = len(raw_pre)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError("split result token count must be in [1, 4]")
    pre = _immutable_binary32_matrix(
        raw_pre,
        label="split result pre codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    post = _immutable_binary32_matrix(
        result.post_binary32_codes,
        label="split result post codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    comb = _immutable_binary32_tensor3(
        result.comb_binary32_codes,
        label="split result combination codes",
        planes=token_count,
        rows=HC_MULTIPLIER,
        columns=HC_MULTIPLIER,
    )
    if type(result.diagnostics) is not HCSplitDiagnostics:
        raise HCPreReferenceError(
            "split result diagnostics must be an exact HCSplitDiagnostics record"
        )
    diagnostics = result.diagnostics
    if len(diagnostics.pre_affine_codes) != token_count:
        raise HCPreReferenceError(
            "split result token count does not match diagnostics"
        )
    try:
        expected_pre = tuple(
            tuple(binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in row)
            for row in diagnostics.pre_sigmoid_codes
        )
        expected_post = tuple(
            tuple(binary32_multiply(_BINARY32_TWO, code) for code in row)
            for row in diagnostics.post_sigmoid_codes
        )
    except NumericReferenceError as exc:
        raise HCPreReferenceError(
            f"split result reconciliation poisoned: {exc}"
        ) from exc
    if pre != expected_pre:
        raise HCPreReferenceError("split pre coefficients do not reconcile")
    if post != expected_post:
        raise HCPreReferenceError("split post coefficients do not reconcile")
    if comb != diagnostics.sinkhorn_stage_codes[-1]:
        raise HCPreReferenceError("split combination does not match final Sinkhorn stage")
    return result


def _validate_counters(counters: object) -> HCPreCounters:
    if type(counters) is not HCPreCounters:
        raise HCPreReferenceError("counters must be an exact HCPreCounters record")
    values = {
        name: _exact_nonnegative_integer(getattr(counters, name), f"counters.{name}")
        for name in counters.__dataclass_fields__
    }
    token_count = values["hc_pre_token_count"]
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError("counters token count must be in [1, 4]")
    expected = {
        "hc_pre_token_count": token_count,
        "hc_pre_input_bf16_values": token_count * FLATTENED_WIDTH,
        "hc_pre_rms_square_multiplies": token_count * FLATTENED_WIDTH,
        "hc_pre_rms_reduction_adds": token_count * (FLATTENED_WIDTH - 1),
        "hc_pre_rms_divides": token_count,
        "hc_pre_rms_epsilon_adds": token_count,
        "hc_pre_rsqrt_evaluations": token_count,
        "hc_pre_projection_product_accumulates": (
            token_count * MIX_PARAMETER_COUNT * FLATTENED_WIDTH
        ),
        "hc_pre_projection_rms_multiplies": token_count * MIX_PARAMETER_COUNT,
        "hc_pre_field_affine_multiplies": token_count * MIX_PARAMETER_COUNT,
        "hc_pre_field_affine_adds": token_count * MIX_PARAMETER_COUNT,
        "hc_pre_sigmoid_evaluations": token_count * 2 * HC_MULTIPLIER,
        "hc_pre_coefficient_epsilon_adds": token_count * HC_MULTIPLIER,
        "hc_pre_post_factor_multiplies": token_count * HC_MULTIPLIER,
        "hc_pre_softmax_max_comparisons": (
            token_count * HC_MULTIPLIER * (HC_MULTIPLIER - 1)
        ),
        "hc_pre_softmax_subtracts": token_count * HC_MULTIPLIER * HC_MULTIPLIER,
        "hc_pre_exp_evaluations": token_count * HC_MULTIPLIER * HC_MULTIPLIER,
        "hc_pre_sinkhorn_row_stages": token_count * SINKHORN_ITERATIONS,
        "hc_pre_sinkhorn_column_stages": token_count * SINKHORN_ITERATIONS,
        "hc_pre_sinkhorn_row_reduction_adds": (
            token_count
            * SINKHORN_ITERATIONS
            * HC_MULTIPLIER
            * (HC_MULTIPLIER - 1)
        ),
        "hc_pre_sinkhorn_column_reduction_adds": (
            token_count
            * SINKHORN_ITERATIONS
            * HC_MULTIPLIER
            * (HC_MULTIPLIER - 1)
        ),
        "hc_pre_sinkhorn_divides": (
            token_count * HC_MULTIPLIER * HC_MULTIPLIER * 2 * SINKHORN_ITERATIONS
        ),
        "hc_pre_sinkhorn_epsilon_adds": (
            token_count
            * (
                HC_MULTIPLIER * HC_MULTIPLIER
                + (SINKHORN_ITERATIONS - 1) * 2 * HC_MULTIPLIER
                + HC_MULTIPLIER
            )
        ),
        "hc_pre_branch_coefficient_multiplies": (
            token_count * HC_MULTIPLIER * HIDDEN_SIZE
        ),
        "hc_pre_branch_reduction_adds": (
            token_count * (HC_MULTIPLIER - 1) * HIDDEN_SIZE
        ),
        "hc_pre_branch_bf16_conversions": token_count * HIDDEN_SIZE,
        "hc_pre_residual_bf16_values_preserved": token_count * FLATTENED_WIDTH,
    }
    for name, expected_value in expected.items():
        if values[name] != expected_value:
            raise HCPreReferenceError(
                f"counters.{name} does not reconcile to HC_PRE dimensions"
            )
    if values["hc_pre_branch_bf16_saturations"] > token_count * HIDDEN_SIZE:
        raise HCPreReferenceError(
            "counters branch saturations exceed BF16 conversions"
        )
    return counters


def _validate_pre_diagnostics(diagnostics: object) -> HCPreDiagnostics:
    if type(diagnostics) is not HCPreDiagnostics:
        raise HCPreReferenceError(
            "diagnostics must be an exact HCPreDiagnostics record"
        )
    raw_means = _immutable_tuple(
        diagnostics.mean_square_codes,
        "diagnostics.mean_square_codes",
    )
    token_count = len(raw_means)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError("diagnostic token count must be in [1, 4]")
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
    projections = _immutable_binary32_matrix(
        diagnostics.projection_codes,
        label="diagnostics.projection_codes",
        rows=token_count,
        columns=MIX_PARAMETER_COUNT,
    )
    normalized = _immutable_binary32_matrix(
        diagnostics.normalized_projection_codes,
        label="diagnostics.normalized_projection_codes",
        rows=token_count,
        columns=MIX_PARAMETER_COUNT,
    )
    if type(diagnostics.split) is not HCSplitDiagnostics:
        raise HCPreReferenceError(
            "diagnostics.split must be an exact HCSplitDiagnostics record"
        )
    if len(diagnostics.split.pre_affine_codes) != token_count:
        raise HCPreReferenceError(
            "diagnostic token count does not match split diagnostics"
        )
    try:
        for token, (mean, inverse) in enumerate(zip(means, inverses, strict=True)):
            mean_value = _finite_binary32_code(
                mean, f"diagnostics.mean_square_codes[{token}]"
            )[1]
            inverse_value = _finite_binary32_code(
                inverse, f"diagnostics.inverse_rms_codes[{token}]"
            )[1]
            if mean_value < 0 or (mean_value == 0 and mean != 0):
                raise HCPreReferenceError(
                    "diagnostic means must be nonnegative with canonical zero"
                )
            if inverse_value <= 0:
                raise HCPreReferenceError(
                    "diagnostic inverse RMS values must be positive"
                )
            expected_inverse = binary32_rsqrt(
                binary32_add(mean, NORMALIZATION_EPSILON_BINARY32)
            )
            if inverse != expected_inverse:
                raise HCPreReferenceError(
                    "diagnostic inverse RMS does not reconcile to mean"
                )
            expected_normalized = tuple(
                binary32_multiply(code, inverse) for code in projections[token]
            )
            if normalized[token] != expected_normalized:
                raise HCPreReferenceError(
                    "diagnostic normalized projections do not reconcile"
                )
    except NumericReferenceError as exc:
        raise HCPreReferenceError(
            f"diagnostic numeric reconciliation poisoned: {exc}"
        ) from exc
    return diagnostics


def _validate_pre_result(result: object) -> HCPreResult:
    if type(result) is not HCPreResult:
        raise HCPreReferenceError("result must be an exact HCPreResult record")
    if type(result.numeric_profile) is not str or result.numeric_profile != NUMERIC_PROFILE:
        raise HCPreReferenceError(
            f"numeric_profile must equal {NUMERIC_PROFILE!r}"
        )
    raw_branch = _immutable_tuple(result.branch_bf16_codes, "branch_bf16_codes")
    token_count = len(raw_branch)
    if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError("result token count must be in [1, 4]")
    branch = _immutable_bf16_matrix(
        raw_branch,
        label="branch_bf16_codes",
        rows=token_count,
        columns=HIDDEN_SIZE,
    )
    pre = _immutable_binary32_matrix(
        result.pre_binary32_codes,
        label="pre_binary32_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    post = _immutable_binary32_matrix(
        result.post_binary32_codes,
        label="post_binary32_codes",
        rows=token_count,
        columns=HC_MULTIPLIER,
    )
    comb = _immutable_binary32_tensor3(
        result.comb_binary32_codes,
        label="comb_binary32_codes",
        planes=token_count,
        rows=HC_MULTIPLIER,
        columns=HC_MULTIPLIER,
    )
    residual = _immutable_bf16_hc_tensor(
        result.residual_bf16_codes,
        label="residual_bf16_codes",
        token_count=token_count,
    )
    if len(residual) != token_count:
        raise HCPreReferenceError(
            "residual_bf16_codes must contain exactly four streams per token"
        )
    saturation_count = _exact_nonnegative_integer(
        result.branch_output_saturation_count,
        "branch_output_saturation_count",
    )
    if saturation_count > token_count * HIDDEN_SIZE:
        raise HCPreReferenceError("branch saturation count exceeds output values")
    saturation_candidates = sum(
        code & 0x7FFF == 0x7F7F for row in branch for code in row
    )
    if saturation_count > saturation_candidates:
        raise HCPreReferenceError(
            "branch saturation count exceeds maximum-finite BF16 candidates"
        )
    if type(result.diagnostics) is not HCPreDiagnostics:
        raise HCPreReferenceError(
            "diagnostics must be an exact HCPreDiagnostics record"
        )
    if type(result.counters) is not HCPreCounters:
        raise HCPreReferenceError("counters must be an exact HCPreCounters record")
    if len(result.diagnostics.mean_square_codes) != token_count:
        raise HCPreReferenceError("result token count does not match diagnostics")
    split = result.diagnostics.split
    try:
        if (
            pre
            != tuple(
                tuple(binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in row)
                for row in split.pre_sigmoid_codes
            )
            or post
            != tuple(
                tuple(binary32_multiply(_BINARY32_TWO, code) for code in row)
                for row in split.post_sigmoid_codes
            )
            or comb != split.sinkhorn_stage_codes[-1]
        ):
            raise HCPreReferenceError(
                "architectural coefficients do not reconcile to diagnostics"
            )

        expected_branches: list[BF16Vector] = []
        expected_saturation_count = 0
        for token, streams in enumerate(residual):
            input_codes, _ = _flatten_token(streams)
            if all(code == 0 for code in input_codes):
                square_sum = 0
            else:
                square_sum = binary32_balanced_sum(
                    binary32_multiply(code, code) for code in input_codes
                )
            expected_mean = binary32_divide(square_sum, _BINARY32_WIDTH)
            expected_inverse = binary32_rsqrt(
                binary32_add(expected_mean, NORMALIZATION_EPSILON_BINARY32)
            )
            if (
                result.diagnostics.mean_square_codes[token] != expected_mean
                or result.diagnostics.inverse_rms_codes[token] != expected_inverse
            ):
                raise HCPreReferenceError(
                    "result RMS diagnostics do not reconcile to residual input"
                )

            expected_branch: list[int] = []
            for column in range(HIDDEN_SIZE):
                products = tuple(
                    binary32_multiply(
                        pre[token][stream],
                        input_codes[stream * HIDDEN_SIZE + column],
                    )
                    for stream in range(HC_MULTIPLIER)
                )
                converted = binary32_bits_to_bf16_rne(
                    binary32_balanced_sum(products)
                )
                expected_branch.append(converted.code)
                expected_saturation_count += int(converted.saturated)
            expected_branches.append(tuple(expected_branch))
    except NumericReferenceError as exc:
        raise HCPreReferenceError(
            f"result numeric reconciliation poisoned: {exc}"
        ) from exc
    if branch != tuple(expected_branches):
        raise HCPreReferenceError(
            "branch output does not reconcile to residual input and pre coefficients"
        )
    if saturation_count != expected_saturation_count:
        raise HCPreReferenceError(
            "branch saturation count does not reconcile to branch arithmetic"
        )
    counters = result.counters
    if counters.hc_pre_token_count != token_count:
        raise HCPreReferenceError("counter token count does not match result")
    if counters.hc_pre_branch_bf16_saturations != saturation_count:
        raise HCPreReferenceError("counter saturation count does not match result")
    if counters.hc_pre_residual_bf16_values_preserved != sum(
        len(stream) for token in residual for stream in token
    ):
        raise HCPreReferenceError("residual shape does not reconcile to counters")
    return result


def _validate_fixed_contract(
    *,
    normalization_epsilon_binary32: object,
    sinkhorn_epsilon_binary32: object,
    sinkhorn_iterations: object,
) -> None:
    if (
        isinstance(normalization_epsilon_binary32, bool)
        or not isinstance(normalization_epsilon_binary32, int)
        or normalization_epsilon_binary32 != NORMALIZATION_EPSILON_BINARY32
    ):
        raise HCPreReferenceError(
            "normalization_epsilon_binary32 must equal 0x358637bd"
        )
    if (
        isinstance(sinkhorn_epsilon_binary32, bool)
        or not isinstance(sinkhorn_epsilon_binary32, int)
        or sinkhorn_epsilon_binary32 != SINKHORN_EPSILON_BINARY32
    ):
        raise HCPreReferenceError("sinkhorn_epsilon_binary32 must equal 0x358637bd")
    if (
        isinstance(sinkhorn_iterations, bool)
        or not isinstance(sinkhorn_iterations, int)
        or sinkhorn_iterations != SINKHORN_ITERATIONS
    ):
        raise HCPreReferenceError("sinkhorn_iterations must equal 20")


def _fraction_floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _fraction_ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _exp_negative_fixed_interval(
    value: Fraction,
    precision: int,
) -> tuple[int, int]:
    """Enclose ``exp(value)`` as fixed-point integers with exact bounds.

    ``value`` is in ``(-256, 0)``.  Power-of-two argument reduction puts the
    alternating Taylor series in ``[-1/2, 0)``. Consecutive partial sums are
    rigorous lower/upper bounds; subsequent fixed-point squaring always rounds
    outward. No binary host arithmetic participates.
    """

    if not Fraction(-256) < value < 0:
        raise RuntimeError("negative exponential interval input is out of range")
    magnitude = -value
    squarings = 0
    while magnitude > Fraction(1, 2):
        magnitude /= 2
        squarings += 1

    partial = Fraction(1)
    term = Fraction(1)
    lower = Fraction(0)
    upper = Fraction(1)
    target_scale = 1 << (precision + squarings + 8)
    index = 0
    while True:
        index += 1
        term = term * magnitude / index
        if index & 1:
            partial -= term
            lower = partial
            upper = partial + term
        else:
            partial += term
            upper = partial
            lower = partial - term
        if (upper - lower) * target_scale < 1:
            break

    scale = 1 << precision
    lower_fixed = _fraction_floor(lower * scale)
    upper_fixed = _fraction_ceil(upper * scale)
    for _ in range(squarings):
        lower_fixed = (lower_fixed * lower_fixed) // scale
        upper_fixed = (upper_fixed * upper_fixed + scale - 1) // scale
        # exp(nonpositive) is at most one; this exact analytic bound tightens
        # harmless outward-rounding growth close to zero.
        upper_fixed = min(upper_fixed, scale)
    return lower_fixed, upper_fixed


def _round_exp_negative(value: Fraction) -> TranscendentalRounding:
    if value == 0:
        return TranscendentalRounding(_BINARY32_ONE, 0, 0)
    # e > 2, hence exp(-256) < 2^-256, far below the binary32 zero
    # midpoint 2^-150. This also bounds work for extreme finite inputs.
    if value <= -256:
        return TranscendentalRounding(0, 0, 0)

    # Termination is exact, not heuristic. For nonzero rational ``value``,
    # Lindemann-Weierstrass makes exp(value) transcendental, while every
    # binary32 rounding midpoint is rational. The convergent outward interval
    # therefore eventually excludes every midpoint. Zero is handled above.
    precision = _TRANSCENDENTAL_INITIAL_PRECISION
    interval_evaluations = 0
    while True:
        interval_evaluations += 1
        lower, upper = _exp_negative_fixed_interval(value, precision)
        scale = 1 << precision
        try:
            lower_code = encode_binary32_rne(Fraction(lower, scale))
            upper_code = encode_binary32_rne(Fraction(upper, scale))
        except NumericReferenceError as exc:  # pragma: no cover - result <= 1
            raise HCPreReferenceError(
                f"nonpositive binary32 exponential failed: {exc}"
            ) from exc
        if lower_code == upper_code:
            return TranscendentalRounding(
                lower_code,
                interval_evaluations,
                precision,
            )
        precision *= 2


@lru_cache(maxsize=4096)
def _binary32_exp_rne_cached(value_code: int) -> TranscendentalRounding:
    decoded = decode_binary32(value_code)
    if decoded.value is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("validated exponential input became nonfinite")
    value = decoded.value
    if value > 0:
        raise HCPreReferenceError(
            "binary32 exponential input must be nonpositive in the HC profile"
        )
    return _round_exp_negative(value)


def binary32_exp_rne(value_code: int) -> int:
    """Correctly round ``exp(x)`` for the HC softmax domain ``x <= 0``.

    Positive arguments are outside this profile because row-max subtraction
    makes every architectural softmax argument nonpositive. Invalid,
    nonfinite, or positive inputs fail closed.
    """

    code, _ = _finite_binary32_code(value_code, "binary32 exponential input")
    return _binary32_exp_rne_cached(code).code


def binary32_exp_rne_with_diagnostics(value_code: int) -> TranscendentalRounding:
    """Return CR32 ``exp`` plus adaptive exact-interval resource diagnostics."""

    code, _ = _finite_binary32_code(value_code, "binary32 exponential input")
    return _binary32_exp_rne_cached(code)


@lru_cache(maxsize=4096)
def _binary32_sigmoid_rne_cached(value_code: int) -> TranscendentalRounding:
    decoded = decode_binary32(value_code)
    if decoded.value is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("validated sigmoid input became nonfinite")
    value = decoded.value
    if value == 0:
        return TranscendentalRounding(0x3F000000, 0, 0)
    if value <= -256:
        return TranscendentalRounding(0, 0, 0)
    if value >= 256:
        return TranscendentalRounding(_BINARY32_ONE, 0, 0)

    # If direct logistic(z) equalled a rational binary32 midpoint for nonzero
    # rational z, rearranging y = 1/(1 + exp(-z)) would make exp(-z) algebraic,
    # contradicting Lindemann-Weierstrass. Thus these shrinking enclosures also
    # terminate for every legal input. Zero and analytic tails are handled above.
    precision = _TRANSCENDENTAL_INITIAL_PRECISION
    interval_evaluations = 0
    while True:
        interval_evaluations += 1
        lower_exp, upper_exp = _exp_negative_fixed_interval(-abs(value), precision)
        scale = 1 << precision
        if value < 0:
            lower = Fraction(lower_exp, scale + lower_exp)
            upper = Fraction(upper_exp, scale + upper_exp)
        else:
            lower = Fraction(scale, scale + upper_exp)
            upper = Fraction(scale, scale + lower_exp)
        try:
            lower_code = encode_binary32_rne(lower)
            upper_code = encode_binary32_rne(upper)
        except NumericReferenceError as exc:  # pragma: no cover - result in [0, 1]
            raise HCPreReferenceError(f"binary32 sigmoid failed: {exc}") from exc
        if lower_code == upper_code:
            return TranscendentalRounding(
                lower_code,
                interval_evaluations,
                precision,
            )
        precision *= 2


def binary32_sigmoid_rne(value_code: int) -> int:
    """Correctly round the mathematical logistic function to binary32.

    An exact enclosure for ``exp(-abs(x))`` is transformed monotonically into
    a logistic enclosure. No rounded exponential, add, or divide is exposed:
    this is one direct correctly rounded mathematical-function boundary.
    """

    code, _ = _finite_binary32_code(value_code, "binary32 sigmoid input")
    return _binary32_sigmoid_rne_cached(code).code


def binary32_sigmoid_rne_with_diagnostics(
    value_code: int,
) -> TranscendentalRounding:
    """Return direct CR32 logistic plus exact-interval resource diagnostics."""

    code, _ = _finite_binary32_code(value_code, "binary32 sigmoid input")
    return _binary32_sigmoid_rne_cached(code)


def _affine(mix_code: int, scale_code: int, base_code: int) -> int:
    return binary32_add(binary32_multiply(mix_code, scale_code), base_code)


def _matrix_snapshot(matrix: Sequence[Sequence[int]]) -> Binary32Matrix:
    return tuple(tuple(row) for row in matrix)


def _split_validated(
    mixes: tuple[tuple[int, ...], ...],
    scales: tuple[int, ...],
    bases: tuple[int, ...],
) -> HCSplitResult:
    all_pre: list[Binary32Vector] = []
    all_post: list[Binary32Vector] = []
    all_comb: list[Binary32Matrix] = []
    all_pre_affine: list[Binary32Vector] = []
    all_pre_sigmoid: list[Binary32Vector] = []
    all_post_affine: list[Binary32Vector] = []
    all_post_sigmoid: list[Binary32Vector] = []
    all_comb_affine: list[Binary32Matrix] = []
    all_softmax: list[Binary32Matrix] = []
    all_pre_sigmoid_rounding: list[TranscendentalVector] = []
    all_post_sigmoid_rounding: list[TranscendentalVector] = []
    all_softmax_exp_rounding: list[TranscendentalMatrix] = []
    # Stages are stored stage-major, then token-major, for direct comparisons
    # between the same iteration in independent implementations.
    all_stages: list[list[Binary32Matrix]] = [[] for _ in range(SINKHORN_ITERATIONS)]

    for token_index, token_mixes in enumerate(mixes):
        try:
            pre_affine = tuple(
                _affine(token_mixes[index], scales[0], bases[index])
                for index in range(HC_MULTIPLIER)
            )
            pre_rounding = tuple(
                binary32_sigmoid_rne_with_diagnostics(code) for code in pre_affine
            )
            pre_sigmoid = tuple(item.code for item in pre_rounding)
            pre = tuple(
                binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in pre_sigmoid
            )

            post_affine = tuple(
                _affine(
                    token_mixes[HC_MULTIPLIER + index],
                    scales[1],
                    bases[HC_MULTIPLIER + index],
                )
                for index in range(HC_MULTIPLIER)
            )
            post_rounding = tuple(
                binary32_sigmoid_rne_with_diagnostics(code) for code in post_affine
            )
            post_sigmoid = tuple(item.code for item in post_rounding)
            post = tuple(
                binary32_multiply(_BINARY32_TWO, code) for code in post_sigmoid
            )

            comb_affine = tuple(
                tuple(
                    _affine(
                        token_mixes[2 * HC_MULTIPLIER + row * HC_MULTIPLIER + column],
                        scales[2],
                        bases[2 * HC_MULTIPLIER + row * HC_MULTIPLIER + column],
                    )
                    for column in range(HC_MULTIPLIER)
                )
                for row in range(HC_MULTIPLIER)
            )

            softmax_rows: list[list[int]] = []
            softmax_rounding_rows: list[TranscendentalVector] = []
            for row in comb_affine:
                maximum = max(
                    row,
                    key=lambda code: _finite_binary32_code(
                        code, "comb affine maximum candidate"
                    )[1],
                )
                negative_maximum = maximum ^ 0x80000000
                exponential_rounding = tuple(
                    binary32_exp_rne_with_diagnostics(
                        binary32_add(code, negative_maximum)
                    )
                    for code in row
                )
                exponentials = [item.code for item in exponential_rounding]
                denominator = binary32_balanced_sum(exponentials)
                softmax_rows.append(
                    [
                        binary32_add(
                            binary32_divide(code, denominator),
                            SINKHORN_EPSILON_BINARY32,
                        )
                        for code in exponentials
                    ]
                )
                softmax_rounding_rows.append(exponential_rounding)
            softmax = _matrix_snapshot(softmax_rows)

            comb = [list(row) for row in softmax]

            def normalize_columns() -> None:
                sums = tuple(
                    binary32_balanced_sum(
                        comb[row][column] for row in range(HC_MULTIPLIER)
                    )
                    for column in range(HC_MULTIPLIER)
                )
                denominators = tuple(
                    binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in sums
                )
                for row in range(HC_MULTIPLIER):
                    for column in range(HC_MULTIPLIER):
                        comb[row][column] = binary32_divide(
                            comb[row][column], denominators[column]
                        )

            def normalize_rows() -> None:
                sums = tuple(binary32_balanced_sum(row) for row in comb)
                denominators = tuple(
                    binary32_add(code, SINKHORN_EPSILON_BINARY32) for code in sums
                )
                for row in range(HC_MULTIPLIER):
                    for column in range(HC_MULTIPLIER):
                        comb[row][column] = binary32_divide(
                            comb[row][column], denominators[row]
                        )

            # Stage 0 is the initial softmax-plus-column normalization. Stages
            # 1..19 each execute a row normalization and then a column
            # normalization, exactly matching the source's 20-stage ordering.
            normalize_columns()
            all_stages[0].append(_matrix_snapshot(comb))
            for stage in range(1, SINKHORN_ITERATIONS):
                normalize_rows()
                normalize_columns()
                all_stages[stage].append(_matrix_snapshot(comb))

        except NumericReferenceError as exc:
            raise HCPreReferenceError(
                f"HC coefficient arithmetic failed at token {token_index}: {exc}"
            ) from exc

        all_pre.append(pre)
        all_post.append(post)
        all_comb.append(_matrix_snapshot(comb))
        all_pre_affine.append(pre_affine)
        all_pre_sigmoid.append(pre_sigmoid)
        all_post_affine.append(post_affine)
        all_post_sigmoid.append(post_sigmoid)
        all_comb_affine.append(comb_affine)
        all_softmax.append(softmax)
        all_pre_sigmoid_rounding.append(pre_rounding)
        all_post_sigmoid_rounding.append(post_rounding)
        all_softmax_exp_rounding.append(tuple(softmax_rounding_rows))

    diagnostics = HCSplitDiagnostics(
        pre_affine_codes=tuple(all_pre_affine),
        pre_sigmoid_codes=tuple(all_pre_sigmoid),
        post_affine_codes=tuple(all_post_affine),
        post_sigmoid_codes=tuple(all_post_sigmoid),
        comb_affine_codes=tuple(all_comb_affine),
        softmax_codes=tuple(all_softmax),
        pre_sigmoid_rounding=tuple(all_pre_sigmoid_rounding),
        post_sigmoid_rounding=tuple(all_post_sigmoid_rounding),
        softmax_exp_rounding=tuple(all_softmax_exp_rounding),
        sinkhorn_stage_codes=tuple(tuple(stage) for stage in all_stages),
    )
    return HCSplitResult(
        pre_binary32_codes=tuple(all_pre),
        post_binary32_codes=tuple(all_post),
        comb_binary32_codes=tuple(all_comb),
        diagnostics=diagnostics,
    )


def hc_split_sinkhorn_binary32(
    mixes_binary32_codes: Sequence[Sequence[int]],
    scale_binary32_codes: Sequence[int],
    base_binary32_codes: Sequence[int],
    *,
    sinkhorn_epsilon_binary32: int = SINKHORN_EPSILON_BINARY32,
    sinkhorn_iterations: int = SINKHORN_ITERATIONS,
) -> HCSplitResult:
    """Split 24 mixes and execute the qualified 20-stage Sinkhorn profile."""

    _validate_fixed_contract(
        normalization_epsilon_binary32=NORMALIZATION_EPSILON_BINARY32,
        sinkhorn_epsilon_binary32=sinkhorn_epsilon_binary32,
        sinkhorn_iterations=sinkhorn_iterations,
    )
    raw_mixes = _sequence(mixes_binary32_codes, "mixes_binary32_codes")
    if not MIN_TOKEN_COUNT <= len(raw_mixes) <= MAX_TOKEN_COUNT:
        raise HCPreReferenceError(
            "mixes_binary32_codes token dimension must be in [1, 4]"
        )
    mixes = tuple(
        _finite_binary32_vector(
            row,
            label=f"mixes_binary32_codes[{token}]",
            width=MIX_PARAMETER_COUNT,
        )
        for token, row in enumerate(raw_mixes)
    )
    scales = _finite_binary32_vector(
        scale_binary32_codes,
        label="scale_binary32_codes",
        width=3,
    )
    bases = _finite_binary32_vector(
        base_binary32_codes,
        label="base_binary32_codes",
        width=MIX_PARAMETER_COUNT,
    )
    return _split_validated(mixes, scales, bases)


def _flatten_token(
    streams: BF16HCRow,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    codes: list[int] = []
    values: list[Fraction] = []
    for stream in streams:
        for code in stream:
            decoded = decode_bf16(code)
            if decoded.value is None:  # pragma: no cover - validated earlier
                raise RuntimeError("validated HC input became nonfinite")
            codes.append(0 if decoded.value == 0 else code << 16)
            values.append(decoded.value)
    return tuple(codes), tuple(values)


def _project_token(
    input_values: tuple[Fraction, ...],
    projection: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    nonzero_indices = tuple(
        index for index, value in enumerate(input_values) if value != 0
    )
    if not nonzero_indices:
        return (0,) * MIX_PARAMETER_COUNT

    outputs: list[int] = []
    for row in projection:
        accumulator = 0
        for index in nonzero_indices:
            weight = decode_binary32(row[index]).value
            if weight is None:  # pragma: no cover - validated earlier
                raise RuntimeError("validated HC projection weight became nonfinite")
            if weight != 0:
                accumulator = binary32_product_add(
                    accumulator,
                    input_values[index],
                    weight,
                )
        outputs.append(accumulator)
    return tuple(outputs)


def _counters(token_count: int, saturation_count: int) -> HCPreCounters:
    return HCPreCounters(
        hc_pre_token_count=token_count,
        hc_pre_input_bf16_values=token_count * FLATTENED_WIDTH,
        hc_pre_rms_square_multiplies=token_count * FLATTENED_WIDTH,
        hc_pre_rms_reduction_adds=token_count * (FLATTENED_WIDTH - 1),
        hc_pre_rms_divides=token_count,
        hc_pre_rms_epsilon_adds=token_count,
        hc_pre_rsqrt_evaluations=token_count,
        hc_pre_projection_product_accumulates=(
            token_count * MIX_PARAMETER_COUNT * FLATTENED_WIDTH
        ),
        hc_pre_projection_rms_multiplies=token_count * MIX_PARAMETER_COUNT,
        hc_pre_field_affine_multiplies=token_count * MIX_PARAMETER_COUNT,
        hc_pre_field_affine_adds=token_count * MIX_PARAMETER_COUNT,
        hc_pre_sigmoid_evaluations=token_count * 2 * HC_MULTIPLIER,
        hc_pre_coefficient_epsilon_adds=token_count * HC_MULTIPLIER,
        hc_pre_post_factor_multiplies=token_count * HC_MULTIPLIER,
        hc_pre_softmax_max_comparisons=(
            token_count * HC_MULTIPLIER * (HC_MULTIPLIER - 1)
        ),
        hc_pre_softmax_subtracts=(token_count * HC_MULTIPLIER * HC_MULTIPLIER),
        hc_pre_exp_evaluations=token_count * HC_MULTIPLIER * HC_MULTIPLIER,
        hc_pre_sinkhorn_row_stages=token_count * SINKHORN_ITERATIONS,
        hc_pre_sinkhorn_column_stages=token_count * SINKHORN_ITERATIONS,
        hc_pre_sinkhorn_row_reduction_adds=(
            token_count * SINKHORN_ITERATIONS * HC_MULTIPLIER * (HC_MULTIPLIER - 1)
        ),
        hc_pre_sinkhorn_column_reduction_adds=(
            token_count * SINKHORN_ITERATIONS * HC_MULTIPLIER * (HC_MULTIPLIER - 1)
        ),
        hc_pre_sinkhorn_divides=(
            token_count * HC_MULTIPLIER * HC_MULTIPLIER * (2 * SINKHORN_ITERATIONS)
        ),
        hc_pre_sinkhorn_epsilon_adds=(
            token_count
            * (
                HC_MULTIPLIER * HC_MULTIPLIER
                + (SINKHORN_ITERATIONS - 1) * 2 * HC_MULTIPLIER
                + HC_MULTIPLIER
            )
        ),
        hc_pre_branch_coefficient_multiplies=(
            token_count * HC_MULTIPLIER * HIDDEN_SIZE
        ),
        hc_pre_branch_reduction_adds=(token_count * (HC_MULTIPLIER - 1) * HIDDEN_SIZE),
        hc_pre_branch_bf16_conversions=token_count * HIDDEN_SIZE,
        hc_pre_branch_bf16_saturations=saturation_count,
        hc_pre_residual_bf16_values_preserved=token_count * FLATTENED_WIDTH,
    )


def hc_pre_bf16(
    input_bf16_codes: Sequence[Sequence[Sequence[int]]],
    projection_binary32_codes: Sequence[Sequence[int]],
    scale_binary32_codes: Sequence[int],
    base_binary32_codes: Sequence[int],
    *,
    normalization_epsilon_binary32: int = NORMALIZATION_EPSILON_BINARY32,
    sinkhorn_epsilon_binary32: int = SINKHORN_EPSILON_BINARY32,
    sinkhorn_iterations: int = SINKHORN_ITERATIONS,
) -> HCPreResult:
    """Execute one immutable, fail-closed DeepSeek V4 HC_PRE transaction."""

    _validate_fixed_contract(
        normalization_epsilon_binary32=normalization_epsilon_binary32,
        sinkhorn_epsilon_binary32=sinkhorn_epsilon_binary32,
        sinkhorn_iterations=sinkhorn_iterations,
    )
    inputs = _finite_hc_input(input_bf16_codes)
    # Small parameter vectors are validated before the large projection so
    # malformed requests fail without unnecessary work.
    scales = _finite_binary32_vector(
        scale_binary32_codes,
        label="scale_binary32_codes",
        width=3,
    )
    bases = _finite_binary32_vector(
        base_binary32_codes,
        label="base_binary32_codes",
        width=MIX_PARAMETER_COUNT,
    )
    projection = _finite_projection(projection_binary32_codes)

    means: list[int] = []
    inverses: list[int] = []
    projected: list[Binary32Vector] = []
    normalized_projected: list[Binary32Vector] = []
    flattened_codes: list[tuple[int, ...]] = []

    for token_index, streams in enumerate(inputs):
        codes, values = _flatten_token(streams)
        flattened_codes.append(codes)
        try:
            if all(value == 0 for value in values):
                square_sum = 0
            else:
                squares = tuple(binary32_multiply(code, code) for code in codes)
                square_sum = binary32_balanced_sum(squares)
            mean = binary32_divide(square_sum, _BINARY32_WIDTH)
            biased_mean = binary32_add(mean, NORMALIZATION_EPSILON_BINARY32)
            inverse = binary32_rsqrt(biased_mean)
            projection_codes = _project_token(values, projection)
            normalized_codes = tuple(
                binary32_multiply(code, inverse) for code in projection_codes
            )
        except NumericReferenceError as exc:
            raise HCPreReferenceError(
                f"HC normalization/projection failed at token {token_index}: {exc}"
            ) from exc
        means.append(mean)
        inverses.append(inverse)
        projected.append(projection_codes)
        normalized_projected.append(normalized_codes)

    split = _split_validated(tuple(normalized_projected), scales, bases)

    branch_outputs: list[BF16Vector] = []
    saturation_count = 0
    for token_index, (codes, pre) in enumerate(
        zip(flattened_codes, split.pre_binary32_codes, strict=True)
    ):
        output: list[int] = []
        for column in range(HIDDEN_SIZE):
            try:
                products = tuple(
                    binary32_multiply(
                        pre[stream],
                        codes[stream * HIDDEN_SIZE + column],
                    )
                    for stream in range(HC_MULTIPLIER)
                )
                total = binary32_balanced_sum(products)
                converted = binary32_bits_to_bf16_rne(total)
            except NumericReferenceError as exc:
                raise HCPreReferenceError(
                    "HC branch reduction failed at "
                    f"token {token_index}, column {column}: {exc}"
                ) from exc
            output.append(converted.code)
            saturation_count += int(converted.saturated)
        branch_outputs.append(tuple(output))

    diagnostics = HCPreDiagnostics(
        mean_square_codes=tuple(means),
        inverse_rms_codes=tuple(inverses),
        projection_codes=tuple(projected),
        normalized_projection_codes=tuple(normalized_projected),
        split=split.diagnostics,
    )
    return HCPreResult(
        numeric_profile=NUMERIC_PROFILE,
        branch_bf16_codes=tuple(branch_outputs),
        pre_binary32_codes=split.pre_binary32_codes,
        post_binary32_codes=split.post_binary32_codes,
        comb_binary32_codes=split.comb_binary32_codes,
        residual_bf16_codes=inputs,
        branch_output_saturation_count=saturation_count,
        diagnostics=diagnostics,
        counters=_counters(len(inputs), saturation_count),
    )


__all__ = [
    "EXCLUDED_SYSTEM_CLAIMS",
    "FLATTENED_WIDTH",
    "HC_MULTIPLIER",
    "HIDDEN_SIZE",
    "INFERENCE_CONFIG_EXPECTED_FIELDS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "HCPreCounters",
    "HCPreDiagnostics",
    "HCPreReferenceError",
    "HCPreResult",
    "HCSplitDiagnostics",
    "HCSplitResult",
    "KERNEL_SOURCE_SHA256",
    "KERNEL_SOURCE_EXPRESSIONS",
    "KERNEL_SOURCE_PATH",
    "MAX_TOKEN_COUNT",
    "MIN_TOKEN_COUNT",
    "MIX_PARAMETER_COUNT",
    "MODEL_SOURCE_EXPRESSIONS",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "NORMALIZATION_EPSILON_BINARY32",
    "NUMERIC_PROFILE",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "SINKHORN_EPSILON_BINARY32",
    "SINKHORN_ITERATIONS",
    "TranscendentalRounding",
    "binary32_exp_rne",
    "binary32_exp_rne_with_diagnostics",
    "binary32_sigmoid_rne",
    "binary32_sigmoid_rne_with_diagnostics",
    "hc_pre_bf16",
    "hc_split_sinkhorn_binary32",
]
