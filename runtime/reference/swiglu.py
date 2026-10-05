"""Deterministic DeepSeek V4 routed and shared SwiGLU references.

The pinned ``Expert.forward`` executes three learned projections around an
FP32 clamp/SiLU/gating section.  Routed experts use packed MXFP4 weights with
one E8M0 scale per 32 reduction values; the shared expert uses block-scaled
FP8 weights.  Both paths quantize each BF16 activation row once per 128
reduction values and return BF16 from every learned projection.

The released TileLang kernels do not make tensor-core association, SiLU
approximation, or cross-block accumulation portable.  This target profile
therefore freezes those observable boundaries explicitly:

* each 32-value routed block uses the qualified ordered MXFP4-by-FP8 dot;
* routed block partials accumulate into positive binary32 zero in increasing
  32-value block order, with one binary32 RNE add per partial;
* each shared projection composes the already-qualified dense FP8 linear
  operator and its canonical balanced cross-block tree unchanged;
* BF16 gate/up outputs widen exactly to binary32, ``up`` clamps to ``[-10,10]``
  while ``gate`` has only the source's upper clamp at ``10``;
* SiLU is a direct correctly rounded binary32 logistic followed by a separate
  binary32 ``gate * sigmoid(gate)`` multiplication;
* the clamped ``up`` and optional nonnegative route weight each multiply in
  binary32 before one conversion of the gated intermediate to BF16; and
* the final learned projection returns BF16 and commits the result atomically.

All counters are exact *logical scalar-reference* work or operand-byte counts.
They are not physical transactions, cache behavior, cycles, bandwidth,
throughput, energy, area, or PPA evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    DENSE_REDUCTION_BLOCK,
    ROUTED_REDUCTION_BLOCK,
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
    decode_e4m3fn,
    decode_e8m0,
    mxfp4_fp8_block_dot,
    quantize_bf16_activation_block,
)
from .hyper_connection import (
    HCPreReferenceError,
    binary32_sigmoid_rne_with_diagnostics,
)
from .matrix import MatrixReferenceError, dense_fp8_linear_bf16


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_PATH = "inference/kernel.py"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)

MXFP4_SWIGLU_NUMERIC_PROFILE = "opentallas.deepseek_v4_mxfp4_swiglu.v1"
FP8_SWIGLU_NUMERIC_PROFILE = "opentallas.deepseek_v4_fp8_swiglu.v1"

OFFICIAL_SITE_COUNT = 46
OFFICIAL_HIDDEN_SIZE = 4096
OFFICIAL_INTERMEDIATE_SIZE = 2048
OFFICIAL_ACTIVATION_BLOCK_SIZE = 128
OFFICIAL_ROUTED_WEIGHT_BLOCK_SIZE = 32
OFFICIAL_SWIGLU_LIMIT_BINARY32 = 0x41200000
OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32 = 0xC1200000
OFFICIAL_SWIGLU_LIMIT = Fraction(10)

BF16_MAX_ENCODING = (1 << 16) - 1
BYTE_MAX_ENCODING = (1 << 8) - 1


BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
ByteVector: TypeAlias = tuple[int, ...]
ByteMatrix: TypeAlias = tuple[ByteVector, ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Vector, ...]


class SwiGLUReferenceError(ValueError):
    """Raised when a complete SwiGLU transaction is malformed or poisoned."""


@dataclass(frozen=True)
class OfficialSwiGLUTensorRecord:
    """One canonical layer-0 tensor identity used by the optional audit."""

    tensor_name: str
    canonical_relative_path: str
    dtype: str
    storage_shape: tuple[int, int]
    logical_shape: tuple[int, int]
    size_bytes: int
    sha256: str


OFFICIAL_LAYER0_ROUTED_EXPERT0_TENSORS = (
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w1.weight",
        "ranks/rank-000/layers.0.ffn.experts.0.w1.weight.bin",
        "I8_PACKED_E2M1",
        (2048, 2048),
        (2048, 4096),
        4_194_304,
        "8b8124ab561c2954c4f8d590c60c5478efb7b6726035d1328d89e806988ccceb",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w1.scale",
        "ranks/rank-000/layers.0.ffn.experts.0.w1.scale.bin",
        "F8_E8M0",
        (2048, 128),
        (2048, 128),
        262_144,
        "e2e52dd1cf8e590514eec022f7115e5c1cf7c2305bbe8372f03b1af517b5871a",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w2.weight",
        "ranks/rank-000/layers.0.ffn.experts.0.w2.weight.bin",
        "I8_PACKED_E2M1",
        (4096, 1024),
        (4096, 2048),
        4_194_304,
        "c013d9e37391314d6b8d9e7cadb4d0863aa39e249863c0694cd35e0c17a5e871",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w2.scale",
        "ranks/rank-000/layers.0.ffn.experts.0.w2.scale.bin",
        "F8_E8M0",
        (4096, 64),
        (4096, 64),
        262_144,
        "7c60715f1e31b4c2e64dfa01713c6293e7fa3af437e1d988be0a1b06cc01d579",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w3.weight",
        "ranks/rank-000/layers.0.ffn.experts.0.w3.weight.bin",
        "I8_PACKED_E2M1",
        (2048, 2048),
        (2048, 4096),
        4_194_304,
        "9b074300e23226efb9632565279943358bb15d522275d8bd077c768c563133b9",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.experts.0.w3.scale",
        "ranks/rank-000/layers.0.ffn.experts.0.w3.scale.bin",
        "F8_E8M0",
        (2048, 128),
        (2048, 128),
        262_144,
        "0bb0ec2d1eeaab088ba595dadc674a2646326e156d51e8837b58e739cd0b972d",
    ),
)


OFFICIAL_LAYER0_SHARED_EXPERT_TENSORS = (
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w1.weight",
        "ranks/rank-000/layers.0.ffn.shared_experts.w1.weight.bin",
        "F8_E4M3",
        (2048, 4096),
        (2048, 4096),
        8_388_608,
        "e77b1555b824ef58e4a957ec42624a2b4195970521f88b97ed347a6ea918599c",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w1.scale",
        "ranks/rank-000/layers.0.ffn.shared_experts.w1.scale.bin",
        "F8_E8M0",
        (16, 32),
        (16, 32),
        512,
        "57ef9b4e3281fc835bcd778876d3e1287549bd3335903999f238cacd135c21d1",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w2.weight",
        "ranks/rank-000/layers.0.ffn.shared_experts.w2.weight.bin",
        "F8_E4M3",
        (4096, 2048),
        (4096, 2048),
        8_388_608,
        "fd2d66a842dca0a101a0af6f4659a33225fbd884ce5ba030aed9de699f648638",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w2.scale",
        "ranks/rank-000/layers.0.ffn.shared_experts.w2.scale.bin",
        "F8_E8M0",
        (32, 16),
        (32, 16),
        512,
        "81f89eb49523d54f82bca47c7efba13d4e673d44d92c23e74bcc4960d02c68ae",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w3.weight",
        "ranks/rank-000/layers.0.ffn.shared_experts.w3.weight.bin",
        "F8_E4M3",
        (2048, 4096),
        (2048, 4096),
        8_388_608,
        "98c88381ebf2e836db0efcdc0c1e6da02664bb7b733c7b8f46562759d6628b8c",
    ),
    OfficialSwiGLUTensorRecord(
        "layers.0.ffn.shared_experts.w3.scale",
        "ranks/rank-000/layers.0.ffn.shared_experts.w3.scale.bin",
        "F8_E8M0",
        (16, 32),
        (16, 32),
        512,
        "b88b7a0cf6bb368f3c92c5bfe3f569e42ef6782e0c05f3dbc8f06af1a4a7b862",
    ),
)


@dataclass(frozen=True)
class SwiGLULinearCounters:
    """Exact logical work and operand bytes for one learned projection."""

    weight_format: str
    input_rows: int
    input_features: int
    output_features: int
    activation_blocks_quantized: int
    activation_values_quantized: int
    activation_saturated_blocks: int
    weight_block_dot_evaluations: int
    exact_product_accumulates: int
    cross_block_binary32_adds: int
    output_bf16_conversions: int
    output_bf16_saturations: int
    canonical_weight_payload_bytes: int
    canonical_scale_payload_bytes: int
    logical_input_bf16_read_bytes: int
    logical_weight_data_read_bytes: int
    logical_weight_scale_reads: int
    logical_weight_scale_read_bytes: int
    logical_output_bf16_write_bytes: int


@dataclass(frozen=True)
class SwiGLULinearResult:
    """One immutable BF16 projection plus exact semantic counters."""

    values: BF16Matrix
    counters: SwiGLULinearCounters


@dataclass(frozen=True)
class SwiGLUDiagnostics:
    """Every observable dtype, clamp, and nonlinear boundary before ``w2``."""

    gate_projection_bf16_codes: BF16Matrix
    up_projection_bf16_codes: BF16Matrix
    clamped_gate_binary32_codes: Binary32Matrix
    clamped_up_binary32_codes: Binary32Matrix
    sigmoid_binary32_codes: Binary32Matrix
    silu_binary32_codes: Binary32Matrix
    gated_up_binary32_codes: Binary32Matrix
    post_route_binary32_codes: Binary32Matrix
    intermediate_bf16_codes: BF16Matrix


@dataclass(frozen=True)
class SwiGLUCounters:
    """Exact three-linear and vector work for one atomic expert transaction."""

    token_rows: int
    input_features: int
    intermediate_features: int
    output_features: int
    routed: bool
    w1: SwiGLULinearCounters
    w3: SwiGLULinearCounters
    gate_upper_clamps: int
    up_lower_clamps: int
    up_upper_clamps: int
    sigmoid_evaluations: int
    sigmoid_interval_evaluations: int
    sigmoid_max_precision_bits: int
    silu_gate_multiplies: int
    gated_up_multiplies: int
    route_weight_multiplies: int
    intermediate_bf16_conversions: int
    intermediate_bf16_saturations: int
    w2: SwiGLULinearCounters
    canonical_weight_payload_bytes: int
    canonical_scale_payload_bytes: int
    logical_external_input_bf16_read_bytes: int
    logical_gate_up_bf16_write_bytes: int
    logical_gate_up_bf16_read_bytes: int
    logical_route_weight_binary32_read_bytes: int
    logical_intermediate_bf16_write_bytes: int
    logical_intermediate_bf16_read_bytes: int
    logical_final_output_bf16_write_bytes: int
    total_logical_bf16_read_bytes: int
    total_logical_bf16_write_bytes: int
    logical_weight_data_read_bytes: int
    logical_weight_scale_read_bytes: int
    transaction_commits: int


@dataclass(frozen=True)
class SwiGLUResult:
    """Immutable output, internal semantic witness, and reconciled counters."""

    numeric_profile: str
    official_shape_profile: bool
    output_bf16_codes: BF16Matrix
    diagnostics: SwiGLUDiagnostics
    counters: SwiGLUCounters


@dataclass(frozen=True)
class _LinearResource:
    weight_codes: ByteMatrix
    scale_codes: ByteMatrix
    input_features: int
    output_features: int


@dataclass(frozen=True)
class _VectorStage:
    diagnostics: SwiGLUDiagnostics
    gate_upper_clamps: int
    up_lower_clamps: int
    up_upper_clamps: int
    sigmoid_interval_evaluations: int
    sigmoid_max_precision_bits: int
    intermediate_bf16_saturations: int


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise SwiGLUReferenceError(f"{label} must be an exact list or tuple")
    return value


def _unsigned(value: object, maximum: int, label: str) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise SwiGLUReferenceError(f"{label} must be in [0, {maximum}]")
    return value


def _finite_bf16_matrix(value: object, label: str) -> BF16Matrix:
    raw_rows = _sequence(value, label)
    if not raw_rows:
        raise SwiGLUReferenceError(f"{label} must contain at least one row")
    width: int | None = None
    output: list[BF16Vector] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise SwiGLUReferenceError(
                    f"{label} rows must contain at least one value"
                )
        elif len(row) != width:
            raise SwiGLUReferenceError(f"{label} must be rectangular with width {width}")
        frozen: list[int] = []
        for column, raw_code in enumerate(row):
            code = _unsigned(
                raw_code,
                BF16_MAX_ENCODING,
                f"{label}[{row_index}][{column}]",
            )
            decoded = decode_bf16(code)
            if not decoded.finite or decoded.value is None:
                raise SwiGLUReferenceError(
                    f"{label}[{row_index}][{column}] must be finite BF16"
                )
            frozen.append(code)
        output.append(tuple(frozen))
    return tuple(output)


def _byte_matrix(
    value: object,
    label: str,
    *,
    expected_rows: int | None = None,
    expected_width: int,
) -> ByteMatrix:
    raw_rows = _sequence(value, label)
    if not raw_rows:
        raise SwiGLUReferenceError(f"{label} must contain at least one row")
    if expected_rows is not None and len(raw_rows) != expected_rows:
        raise SwiGLUReferenceError(
            f"{label} must contain exactly {expected_rows} rows"
        )
    output = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if len(row) != expected_width:
            raise SwiGLUReferenceError(
                f"{label}[{row_index}] must contain exactly {expected_width} bytes"
            )
        output.append(
            tuple(
                _unsigned(code, BYTE_MAX_ENCODING, f"{label}[{row_index}][{column}]")
                for column, code in enumerate(row)
            )
        )
    return tuple(output)


def _finite_scale_matrix(
    value: object,
    label: str,
    *,
    expected_rows: int,
    expected_width: int,
) -> ByteMatrix:
    scales = _byte_matrix(
        value,
        label,
        expected_rows=expected_rows,
        expected_width=expected_width,
    )
    for row_index, row in enumerate(scales):
        for column, code in enumerate(row):
            decoded = decode_e8m0(code)
            if not decoded.finite or decoded.value is None:
                raise SwiGLUReferenceError(
                    f"{label}[{row_index}][{column}] uses reserved E8M0 0xff"
                )
    return scales


def _freeze_mxfp4_resource(
    weight_value: object,
    scale_value: object,
    *,
    label: str,
    input_features: int,
) -> _LinearResource:
    if input_features % OFFICIAL_ACTIVATION_BLOCK_SIZE:
        raise SwiGLUReferenceError(
            f"{label} input width must be divisible by "
            f"{OFFICIAL_ACTIVATION_BLOCK_SIZE}"
        )
    weights = _byte_matrix(
        weight_value,
        f"{label}_packed_weight_bytes",
        expected_width=input_features // 2,
    )
    scales = _finite_scale_matrix(
        scale_value,
        f"{label}_scale_codes",
        expected_rows=len(weights),
        expected_width=input_features // OFFICIAL_ROUTED_WEIGHT_BLOCK_SIZE,
    )
    return _LinearResource(weights, scales, input_features, len(weights))


def _freeze_fp8_resource(
    weight_value: object,
    scale_value: object,
    *,
    label: str,
    input_features: int,
) -> _LinearResource:
    if input_features % DENSE_REDUCTION_BLOCK:
        raise SwiGLUReferenceError(
            f"{label} input width must be divisible by {DENSE_REDUCTION_BLOCK}"
        )
    weights = _byte_matrix(
        weight_value,
        f"{label}_weight_codes",
        expected_width=input_features,
    )
    for row_index, row in enumerate(weights):
        for column, code in enumerate(row):
            decoded = decode_e4m3fn(code)
            if not decoded.finite or decoded.value is None:
                raise SwiGLUReferenceError(
                    f"{label}_weight_codes[{row_index}][{column}] must be finite "
                    "E4M3FN"
                )
    scales = _finite_scale_matrix(
        scale_value,
        f"{label}_scale_codes",
        expected_rows=(len(weights) + 127) // 128,
        expected_width=input_features // DENSE_REDUCTION_BLOCK,
    )
    return _LinearResource(weights, scales, input_features, len(weights))


def _route_weights(value: object, *, input_rows: int) -> Binary32Vector:
    raw = _sequence(value, "route_weight_binary32_codes")
    if len(raw) != input_rows:
        raise SwiGLUReferenceError(
            "route_weight_binary32_codes must contain one value per input row"
        )
    output = []
    for row, raw_code in enumerate(raw):
        code = _unsigned(
            raw_code,
            (1 << 32) - 1,
            f"route_weight_binary32_codes[{row}]",
        )
        decoded = decode_binary32(code)
        if not decoded.finite or decoded.value is None:
            raise SwiGLUReferenceError(
                f"route_weight_binary32_codes[{row}] must be finite binary32"
            )
        if decoded.value < 0:
            raise SwiGLUReferenceError(
                f"route_weight_binary32_codes[{row}] must be nonnegative"
            )
        output.append(code)
    return tuple(output)


def _balanced_add_count(value_count: int) -> int:
    count = value_count
    additions = 0
    while count > 1:
        if count & 1:
            count += 1
        additions += count // 2
        count //= 2
    return additions


def _linear_counters(
    *,
    weight_format: str,
    input_rows: int,
    input_features: int,
    output_features: int,
    activation_saturated_blocks: int,
    output_bf16_saturations: int,
) -> SwiGLULinearCounters:
    activation_blocks = input_rows * input_features // DENSE_REDUCTION_BLOCK
    if weight_format == "MXFP4_E2M1_E8M0":
        weight_block_size = ROUTED_REDUCTION_BLOCK
        canonical_weight_payload_bytes = output_features * input_features // 2
        canonical_scale_payload_bytes = (
            output_features * input_features // ROUTED_REDUCTION_BLOCK
        )
        cross_block_adds_per_output = input_features // ROUTED_REDUCTION_BLOCK
    elif weight_format == "FP8_E4M3FN_E8M0":
        weight_block_size = DENSE_REDUCTION_BLOCK
        canonical_weight_payload_bytes = output_features * input_features
        canonical_scale_payload_bytes = (
            (output_features + 127)
            // 128
            * (input_features // DENSE_REDUCTION_BLOCK)
        )
        cross_block_adds_per_output = _balanced_add_count(
            input_features // DENSE_REDUCTION_BLOCK
        )
    else:  # pragma: no cover - private caller invariant
        raise RuntimeError("unknown SwiGLU weight format")

    block_evaluations = (
        input_rows * output_features * input_features // weight_block_size
    )
    scale_reads = block_evaluations
    return SwiGLULinearCounters(
        weight_format=weight_format,
        input_rows=input_rows,
        input_features=input_features,
        output_features=output_features,
        activation_blocks_quantized=activation_blocks,
        activation_values_quantized=input_rows * input_features,
        activation_saturated_blocks=activation_saturated_blocks,
        weight_block_dot_evaluations=block_evaluations,
        exact_product_accumulates=input_rows * output_features * input_features,
        cross_block_binary32_adds=(
            input_rows * output_features * cross_block_adds_per_output
        ),
        output_bf16_conversions=input_rows * output_features,
        output_bf16_saturations=output_bf16_saturations,
        canonical_weight_payload_bytes=canonical_weight_payload_bytes,
        canonical_scale_payload_bytes=canonical_scale_payload_bytes,
        logical_input_bf16_read_bytes=input_rows * input_features * 2,
        logical_weight_data_read_bytes=(
            input_rows * canonical_weight_payload_bytes
        ),
        logical_weight_scale_reads=scale_reads,
        logical_weight_scale_read_bytes=scale_reads,
        logical_output_bf16_write_bytes=input_rows * output_features * 2,
    )


def _execute_mxfp4_linear(
    inputs: BF16Matrix,
    resource: _LinearResource,
    *,
    label: str,
) -> SwiGLULinearResult:
    input_rows = len(inputs)
    reduction_blocks = resource.input_features // DENSE_REDUCTION_BLOCK
    quantized_rows = []
    activation_saturated_blocks = 0
    try:
        for input_row in inputs:
            blocks = []
            for activation_block in range(reduction_blocks):
                start = activation_block * DENSE_REDUCTION_BLOCK
                block = quantize_bf16_activation_block(
                    input_row[start : start + DENSE_REDUCTION_BLOCK]
                )
                activation_saturated_blocks += int(block.saturated)
                blocks.append(block)
            quantized_rows.append(tuple(blocks))
    except NumericReferenceError as exc:
        raise SwiGLUReferenceError(
            f"{label} activation quantization failed: {exc}"
        ) from exc

    output: list[BF16Vector] = []
    output_saturations = 0
    routed_blocks_per_activation = (
        DENSE_REDUCTION_BLOCK // ROUTED_REDUCTION_BLOCK
    )
    try:
        for input_row_index, activation_blocks in enumerate(quantized_rows):
            output_row: list[int] = []
            for output_index, (weight_row, scale_row) in enumerate(
                zip(resource.weight_codes, resource.scale_codes, strict=True)
            ):
                accumulator = 0
                for activation_block_index, activation in enumerate(
                    activation_blocks
                ):
                    for sub_block in range(routed_blocks_per_activation):
                        logical_block = (
                            activation_block_index * routed_blocks_per_activation
                            + sub_block
                        )
                        packed_start = (
                            logical_block * ROUTED_REDUCTION_BLOCK // 2
                        )
                        activation_start = sub_block * ROUTED_REDUCTION_BLOCK
                        partial = mxfp4_fp8_block_dot(
                            weight_row[
                                packed_start : packed_start
                                + ROUTED_REDUCTION_BLOCK // 2
                            ],
                            scale_row[logical_block],
                            activation.value_codes[
                                activation_start : activation_start
                                + ROUTED_REDUCTION_BLOCK
                            ],
                            activation.scale_code,
                        )
                        accumulator = binary32_add(accumulator, partial)
                converted = binary32_bits_to_bf16_rne(accumulator)
                output_saturations += int(converted.saturated)
                output_row.append(converted.code)
            output.append(tuple(output_row))
    except NumericReferenceError as exc:
        raise SwiGLUReferenceError(
            f"{label} MXFP4 arithmetic failed at input row {input_row_index}, "
            f"output row {output_index}: {exc}"
        ) from exc

    return SwiGLULinearResult(
        values=tuple(output),
        counters=_linear_counters(
            weight_format="MXFP4_E2M1_E8M0",
            input_rows=input_rows,
            input_features=resource.input_features,
            output_features=resource.output_features,
            activation_saturated_blocks=activation_saturated_blocks,
            output_bf16_saturations=output_saturations,
        ),
    )


def _execute_fp8_linear(
    inputs: BF16Matrix,
    resource: _LinearResource,
    *,
    label: str,
) -> SwiGLULinearResult:
    try:
        result = dense_fp8_linear_bf16(
            inputs,
            resource.weight_codes,
            resource.scale_codes,
        )
    except MatrixReferenceError as exc:
        raise SwiGLUReferenceError(f"{label} FP8 arithmetic failed: {exc}") from exc
    return SwiGLULinearResult(
        values=result.values,
        counters=_linear_counters(
            weight_format="FP8_E4M3FN_E8M0",
            input_rows=len(inputs),
            input_features=resource.input_features,
            output_features=resource.output_features,
            activation_saturated_blocks=result.activation_saturated_block_count,
            output_bf16_saturations=result.output_saturated_element_count,
        ),
    )


def mxfp4_linear_bf16(
    input_bf16_codes: object,
    packed_weight_bytes: object,
    weight_scale_codes: object,
) -> SwiGLULinearResult:
    """Execute one complete packed-MXFP4 learned projection.

    This general primitive admits bounded output-row subsets for independent
    and official-payload audits.  Such a subset is not a complete expert or a
    declared full-matrix execution.
    """

    inputs = _finite_bf16_matrix(input_bf16_codes, "input_bf16_codes")
    resource = _freeze_mxfp4_resource(
        packed_weight_bytes,
        weight_scale_codes,
        label="linear",
        input_features=len(inputs[0]),
    )
    return _execute_mxfp4_linear(inputs, resource, label="linear")


def _vector_stage(
    gate_projection: BF16Matrix,
    up_projection: BF16Matrix,
    route_weights: Binary32Vector | None,
) -> _VectorStage:
    clamped_gate_rows: list[Binary32Vector] = []
    clamped_up_rows: list[Binary32Vector] = []
    sigmoid_rows: list[Binary32Vector] = []
    silu_rows: list[Binary32Vector] = []
    gated_rows: list[Binary32Vector] = []
    post_route_rows: list[Binary32Vector] = []
    intermediate_rows: list[BF16Vector] = []
    gate_upper_clamps = 0
    up_lower_clamps = 0
    up_upper_clamps = 0
    interval_evaluations = 0
    max_precision_bits = 0
    intermediate_saturations = 0

    try:
        for row_index, (gate_row, up_row) in enumerate(
            zip(gate_projection, up_projection, strict=True)
        ):
            clamped_gate_row: list[int] = []
            clamped_up_row: list[int] = []
            sigmoid_row: list[int] = []
            silu_row: list[int] = []
            gated_row: list[int] = []
            post_route_row: list[int] = []
            intermediate_row: list[int] = []
            for gate_bf16, up_bf16 in zip(gate_row, up_row, strict=True):
                gate_code = gate_bf16 << 16
                up_code = up_bf16 << 16
                gate_value = decode_binary32(gate_code).value
                up_value = decode_binary32(up_code).value
                if gate_value is None or up_value is None:  # pragma: no cover
                    raise RuntimeError("validated BF16 projection became nonfinite")

                if gate_value > OFFICIAL_SWIGLU_LIMIT:
                    gate_code = OFFICIAL_SWIGLU_LIMIT_BINARY32
                    gate_upper_clamps += 1
                if up_value < -OFFICIAL_SWIGLU_LIMIT:
                    up_code = OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32
                    up_lower_clamps += 1
                elif up_value > OFFICIAL_SWIGLU_LIMIT:
                    up_code = OFFICIAL_SWIGLU_LIMIT_BINARY32
                    up_upper_clamps += 1

                sigmoid = binary32_sigmoid_rne_with_diagnostics(gate_code)
                silu = binary32_multiply(gate_code, sigmoid.code)
                gated = binary32_multiply(silu, up_code)
                post_route = (
                    binary32_multiply(gated, route_weights[row_index])
                    if route_weights is not None
                    else gated
                )
                converted = binary32_bits_to_bf16_rne(post_route)

                interval_evaluations += sigmoid.interval_evaluations
                max_precision_bits = max(
                    max_precision_bits,
                    sigmoid.final_precision_bits,
                )
                intermediate_saturations += int(converted.saturated)
                clamped_gate_row.append(gate_code)
                clamped_up_row.append(up_code)
                sigmoid_row.append(sigmoid.code)
                silu_row.append(silu)
                gated_row.append(gated)
                post_route_row.append(post_route)
                intermediate_row.append(converted.code)
            clamped_gate_rows.append(tuple(clamped_gate_row))
            clamped_up_rows.append(tuple(clamped_up_row))
            sigmoid_rows.append(tuple(sigmoid_row))
            silu_rows.append(tuple(silu_row))
            gated_rows.append(tuple(gated_row))
            post_route_rows.append(tuple(post_route_row))
            intermediate_rows.append(tuple(intermediate_row))
    except (NumericReferenceError, HCPreReferenceError) as exc:
        raise SwiGLUReferenceError(
            f"SwiGLU vector arithmetic failed at input row {row_index}: {exc}"
        ) from exc

    diagnostics = SwiGLUDiagnostics(
        gate_projection_bf16_codes=gate_projection,
        up_projection_bf16_codes=up_projection,
        clamped_gate_binary32_codes=tuple(clamped_gate_rows),
        clamped_up_binary32_codes=tuple(clamped_up_rows),
        sigmoid_binary32_codes=tuple(sigmoid_rows),
        silu_binary32_codes=tuple(silu_rows),
        gated_up_binary32_codes=tuple(gated_rows),
        post_route_binary32_codes=tuple(post_route_rows),
        intermediate_bf16_codes=tuple(intermediate_rows),
    )
    return _VectorStage(
        diagnostics=diagnostics,
        gate_upper_clamps=gate_upper_clamps,
        up_lower_clamps=up_lower_clamps,
        up_upper_clamps=up_upper_clamps,
        sigmoid_interval_evaluations=interval_evaluations,
        sigmoid_max_precision_bits=max_precision_bits,
        intermediate_bf16_saturations=intermediate_saturations,
    )


def _complete_result(
    *,
    numeric_profile: str,
    inputs: BF16Matrix,
    gate: SwiGLULinearResult,
    up: SwiGLULinearResult,
    vector: _VectorStage,
    down: SwiGLULinearResult,
    routed: bool,
) -> SwiGLUResult:
    token_rows = len(inputs)
    input_features = len(inputs[0])
    intermediate_features = len(gate.values[0])
    output_features = len(down.values[0])
    vector_values = token_rows * intermediate_features
    linears = (gate.counters, up.counters, down.counters)
    external_input_read_bytes = (
        gate.counters.logical_input_bf16_read_bytes
        + up.counters.logical_input_bf16_read_bytes
    )
    gate_up_write_bytes = (
        gate.counters.logical_output_bf16_write_bytes
        + up.counters.logical_output_bf16_write_bytes
    )
    gate_up_read_bytes = 2 * token_rows * intermediate_features * 2
    route_weight_read_bytes = token_rows * 4 if routed else 0
    intermediate_write_bytes = token_rows * intermediate_features * 2
    intermediate_read_bytes = down.counters.logical_input_bf16_read_bytes
    final_output_write_bytes = down.counters.logical_output_bf16_write_bytes
    counters = SwiGLUCounters(
        token_rows=token_rows,
        input_features=input_features,
        intermediate_features=intermediate_features,
        output_features=output_features,
        routed=routed,
        w1=gate.counters,
        w3=up.counters,
        gate_upper_clamps=vector.gate_upper_clamps,
        up_lower_clamps=vector.up_lower_clamps,
        up_upper_clamps=vector.up_upper_clamps,
        sigmoid_evaluations=vector_values,
        sigmoid_interval_evaluations=vector.sigmoid_interval_evaluations,
        sigmoid_max_precision_bits=vector.sigmoid_max_precision_bits,
        silu_gate_multiplies=vector_values,
        gated_up_multiplies=vector_values,
        route_weight_multiplies=vector_values if routed else 0,
        intermediate_bf16_conversions=vector_values,
        intermediate_bf16_saturations=vector.intermediate_bf16_saturations,
        w2=down.counters,
        canonical_weight_payload_bytes=sum(
            item.canonical_weight_payload_bytes for item in linears
        ),
        canonical_scale_payload_bytes=sum(
            item.canonical_scale_payload_bytes for item in linears
        ),
        logical_external_input_bf16_read_bytes=external_input_read_bytes,
        logical_gate_up_bf16_write_bytes=gate_up_write_bytes,
        logical_gate_up_bf16_read_bytes=gate_up_read_bytes,
        logical_route_weight_binary32_read_bytes=route_weight_read_bytes,
        logical_intermediate_bf16_write_bytes=intermediate_write_bytes,
        logical_intermediate_bf16_read_bytes=intermediate_read_bytes,
        logical_final_output_bf16_write_bytes=final_output_write_bytes,
        total_logical_bf16_read_bytes=(
            external_input_read_bytes
            + gate_up_read_bytes
            + intermediate_read_bytes
        ),
        total_logical_bf16_write_bytes=(
            gate_up_write_bytes
            + intermediate_write_bytes
            + final_output_write_bytes
        ),
        logical_weight_data_read_bytes=sum(
            item.logical_weight_data_read_bytes for item in linears
        ),
        logical_weight_scale_read_bytes=sum(
            item.logical_weight_scale_read_bytes for item in linears
        ),
        transaction_commits=1,
    )
    return SwiGLUResult(
        numeric_profile=numeric_profile,
        official_shape_profile=(
            input_features == OFFICIAL_HIDDEN_SIZE
            and intermediate_features == OFFICIAL_INTERMEDIATE_SIZE
            and output_features == OFFICIAL_HIDDEN_SIZE
        ),
        output_bf16_codes=down.values,
        diagnostics=vector.diagnostics,
        counters=counters,
    )


def mxfp4_swiglu_bf16(
    input_bf16_codes: object,
    route_weight_binary32_codes: object,
    *,
    w1_packed_weight_bytes: object,
    w1_scale_codes: object,
    w2_packed_weight_bytes: object,
    w2_scale_codes: object,
    w3_packed_weight_bytes: object,
    w3_scale_codes: object,
) -> SwiGLUResult:
    """Execute one atomic routed-expert MXFP4 SwiGLU transaction."""

    inputs = _finite_bf16_matrix(input_bf16_codes, "input_bf16_codes")
    input_features = len(inputs[0])
    route_weights = _route_weights(
        route_weight_binary32_codes,
        input_rows=len(inputs),
    )
    w1 = _freeze_mxfp4_resource(
        w1_packed_weight_bytes,
        w1_scale_codes,
        label="w1",
        input_features=input_features,
    )
    w3 = _freeze_mxfp4_resource(
        w3_packed_weight_bytes,
        w3_scale_codes,
        label="w3",
        input_features=input_features,
    )
    if w3.output_features != w1.output_features:
        raise SwiGLUReferenceError("w1 and w3 output feature counts must match")
    w2 = _freeze_mxfp4_resource(
        w2_packed_weight_bytes,
        w2_scale_codes,
        label="w2",
        input_features=w1.output_features,
    )

    gate = _execute_mxfp4_linear(inputs, w1, label="w1")
    up = _execute_mxfp4_linear(inputs, w3, label="w3")
    vector = _vector_stage(gate.values, up.values, route_weights)
    down = _execute_mxfp4_linear(
        vector.diagnostics.intermediate_bf16_codes,
        w2,
        label="w2",
    )
    return _complete_result(
        numeric_profile=MXFP4_SWIGLU_NUMERIC_PROFILE,
        inputs=inputs,
        gate=gate,
        up=up,
        vector=vector,
        down=down,
        routed=True,
    )


def fp8_swiglu_bf16(
    input_bf16_codes: object,
    *,
    w1_weight_codes: object,
    w1_scale_codes: object,
    w2_weight_codes: object,
    w2_scale_codes: object,
    w3_weight_codes: object,
    w3_scale_codes: object,
) -> SwiGLUResult:
    """Execute one atomic shared-expert block-scaled-FP8 SwiGLU transaction."""

    inputs = _finite_bf16_matrix(input_bf16_codes, "input_bf16_codes")
    input_features = len(inputs[0])
    w1 = _freeze_fp8_resource(
        w1_weight_codes,
        w1_scale_codes,
        label="w1",
        input_features=input_features,
    )
    w3 = _freeze_fp8_resource(
        w3_weight_codes,
        w3_scale_codes,
        label="w3",
        input_features=input_features,
    )
    if w3.output_features != w1.output_features:
        raise SwiGLUReferenceError("w1 and w3 output feature counts must match")
    w2 = _freeze_fp8_resource(
        w2_weight_codes,
        w2_scale_codes,
        label="w2",
        input_features=w1.output_features,
    )

    gate = _execute_fp8_linear(inputs, w1, label="w1")
    up = _execute_fp8_linear(inputs, w3, label="w3")
    vector = _vector_stage(gate.values, up.values, None)
    down = _execute_fp8_linear(
        vector.diagnostics.intermediate_bf16_codes,
        w2,
        label="w2",
    )
    return _complete_result(
        numeric_profile=FP8_SWIGLU_NUMERIC_PROFILE,
        inputs=inputs,
        gate=gate,
        up=up,
        vector=vector,
        down=down,
        routed=False,
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "FP8_SWIGLU_NUMERIC_PROFILE",
    "INFERENCE_CONFIG_SHA256",
    "KERNEL_SOURCE_PATH",
    "KERNEL_SOURCE_SHA256",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "MXFP4_SWIGLU_NUMERIC_PROFILE",
    "OFFICIAL_ACTIVATION_BLOCK_SIZE",
    "OFFICIAL_HIDDEN_SIZE",
    "OFFICIAL_INTERMEDIATE_SIZE",
    "OFFICIAL_LAYER0_ROUTED_EXPERT0_TENSORS",
    "OFFICIAL_LAYER0_SHARED_EXPERT_TENSORS",
    "OFFICIAL_NEGATIVE_SWIGLU_LIMIT_BINARY32",
    "OFFICIAL_ROUTED_WEIGHT_BLOCK_SIZE",
    "OFFICIAL_SITE_COUNT",
    "OFFICIAL_SWIGLU_LIMIT_BINARY32",
    "OfficialSwiGLUTensorRecord",
    "SwiGLUCounters",
    "SwiGLUDiagnostics",
    "SwiGLULinearCounters",
    "SwiGLULinearResult",
    "SwiGLUReferenceError",
    "SwiGLUResult",
    "fp8_swiglu_bf16",
    "mxfp4_linear_bf16",
    "mxfp4_swiglu_bf16",
]
