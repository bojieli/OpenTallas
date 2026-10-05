"""Deterministic DeepSeek V4 DSpark main-conditioning projection.

The pinned source captures main-layer hidden states 40, 41, and 42 in that
order, concatenates their BF16 vectors, applies the released FP8/E8M0
``mtp.0.main_proj`` matrix, and then applies the released weighted BF16
``mtp.0.main_norm``.  This module composes the already qualified dense-FP8 and
weighted-RMS arithmetic without making either boundary disappear.

The official entry point consumes immutable contiguous weight and scale bytes.
An exact zero-input path and exact all-zero-weight rows may be evaluated without
performing mathematically redundant products, but all resource codes validate
and the counters retain the full semantic work.  Logical work is not physical
traffic, cycles, latency, energy, area, or PPA evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
from typing import TypeAlias

from .formats import (
    DENSE_REDUCTION_BLOCK,
    NumericReferenceError,
    decode_bf16,
    quantize_bf16_activation_block,
)
from .matrix import (
    DenseFP8LinearResult,
    MatrixReferenceError,
    dense_fp8_linear_selected_rows_bf16,
)
from .normalization import (
    NormalizationReferenceError,
    rms_norm_bf16,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
CHECKPOINT_LOCK_ID = "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
NUMERIC_PROFILE = "opentallas.deepseek_v4_dspark_main_project_bf16.v1"

SOURCE_LAYER_IDS = (40, 41, 42)
SOURCE_COUNT = len(SOURCE_LAYER_IDS)
HIDDEN_WIDTH = 4096
CONCATENATED_WIDTH = SOURCE_COUNT * HIDDEN_WIDTH
OUTPUT_WIDTH = HIDDEN_WIDTH
REDUCTION_BLOCKS = CONCATENATED_WIDTH // DENSE_REDUCTION_BLOCK
OUTPUT_SCALE_TILES = OUTPUT_WIDTH // DENSE_REDUCTION_BLOCK
WEIGHT_BYTES = OUTPUT_WIDTH * CONCATENATED_WIDTH
SCALE_BYTES = OUTPUT_SCALE_TILES * REDUCTION_BLOCKS
NORM_WEIGHT_BYTES = OUTPUT_WIDTH * 2
MAX_TOKENS_PER_TRANSACTION = 4
NORM_EPSILON_BINARY32 = 0x358637BD

OFFICIAL_WEIGHT_SHA256 = (
    "1b405d7483945533ca2195df653940e4a536775e1be6cdbd735fc80b9070c9bd"
)
OFFICIAL_SCALE_SHA256 = (
    "fa8ca8b8728b715805cd2722d3f27da8e47397d8fe70ebea8dbd38c0753e656b"
)
OFFICIAL_NORM_WEIGHT_SHA256 = (
    "c794bc276bb502e0a60f4c817da6c3fd31d3f6b3ad848643d94d9f221771a684"
)

SOURCE_EXPRESSIONS = (
    "if i in self.target_layer_ids:",
    "main_hiddens.append(h.mean(dim=2))",
    "main_hidden = torch.cat(main_hiddens, dim=-1) if main_hiddens else None",
    "main_x = self.main_norm(self.main_proj(main_hidden))",
)
CONFIG_EXPECTED_FIELDS = (
    ("dim", HIDDEN_WIDTH),
    ("dtype", "fp8"),
    ("dspark_target_layer_ids", list(SOURCE_LAYER_IDS)),
)
EXCLUDED_CLAIMS = (
    "target_hidden_capture_execution",
    "checkpoint_derived_activation",
    "complete_dspark_stage_execution",
    "artifact_driven_service_execution",
    "rtl_execution",
    "physical_schedule",
    "cycles_bandwidth_latency_energy_area_ppa",
    "gpu_performance_advantage",
)

BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16CaptureSet: TypeAlias = tuple[BF16Batch, ...]


class DSparkMainProjectReferenceError(ValueError):
    """Raised when the complete DSpark-conditioning transaction poisons."""


@dataclass(frozen=True, slots=True)
class DSparkMainProjectCounters:
    """Exact semantic shape and work counts for one composed transaction."""

    batch_count: int
    sequence_length: int
    token_count: int
    source_count: int
    source_hidden_width: int
    concatenated_width: int
    projection_output_width: int
    capture_input_bf16_values: int
    concatenated_view_bf16_values: int
    activation_blocks_quantized: int
    activation_values_quantized: int
    projection_weight_e4m3_values: int
    projection_scale_e8m0_values: int
    projection_block_dots: int
    projection_exact_product_accumulates: int
    projection_cross_block_reduction_adds: int
    projection_bf16_conversions: int
    rms_weight_bf16_values: int
    rms_square_multiplies: int
    rms_reduction_adds: int
    rms_divides: int
    rms_epsilon_adds: int
    rms_rsqrt_evaluations: int
    rms_pointwise_multiplies: int
    rms_bf16_conversions: int
    activation_saturated_blocks: int
    projection_saturated_outputs: int
    rms_saturated_outputs: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class DSparkMainProjectResult:
    """Projection boundary, RMS boundary, and immutable reconciliation data.

    Retaining the projection and norm weight authenticates the weighted-RMS
    relationship. Captures and the 50 MiB projection resource are intentionally
    omitted, so public construction cannot authenticate projection arithmetic
    or checkpoint provenance.
    """

    numeric_profile: str
    source_layer_ids: tuple[int, ...]
    projection_bf16_codes: BF16Batch
    normalized_bf16_codes: BF16Batch
    norm_weight_bf16_codes: BF16Vector
    mean_square_binary32_codes: tuple[int, ...]
    inverse_rms_binary32_codes: tuple[int, ...]
    activation_saturated_block_count: int
    projection_saturated_output_count: int
    normalization_saturated_output_count: int
    counters: DSparkMainProjectCounters

    def __post_init__(self) -> None:
        _validate_result(self)


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise DSparkMainProjectReferenceError(f"{label} must be a sequence")
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise DSparkMainProjectReferenceError(
            f"{label} must be a deeply immutable exact tuple"
        )
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DSparkMainProjectReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16_code(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise DSparkMainProjectReferenceError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise DSparkMainProjectReferenceError(f"{label} must be finite BF16")
    return value


def _freeze_bf16_vector(
    value: object,
    *,
    label: str,
    width: int,
    exact_tuple: bool = False,
) -> BF16Vector:
    raw = _exact_tuple(value, label) if exact_tuple else _sequence(value, label)
    if len(raw) != width:
        raise DSparkMainProjectReferenceError(
            f"{label} must contain exactly {width} values"
        )
    return tuple(
        _finite_bf16_code(code, f"{label}[{column}]")
        for column, code in enumerate(raw)
    )


def _freeze_captures(value: object) -> tuple[BF16CaptureSet, int, int, BF16Matrix]:
    raw_sources = _sequence(value, "captured_hidden_bf16_codes")
    if len(raw_sources) != SOURCE_COUNT:
        raise DSparkMainProjectReferenceError(
            f"captured_hidden_bf16_codes must contain exactly {SOURCE_COUNT} sources"
        )
    sources: list[BF16Batch] = []
    batch_count: int | None = None
    sequence_length: int | None = None
    for source, raw_batches in enumerate(raw_sources):
        batches = _sequence(
            raw_batches,
            f"captured_hidden_bf16_codes[{source}]",
        )
        if batch_count is None:
            batch_count = len(batches)
            if not 1 <= batch_count <= MAX_TOKENS_PER_TRANSACTION:
                raise DSparkMainProjectReferenceError(
                    "captured hidden batch extent is outside the transaction bound"
                )
        elif len(batches) != batch_count:
            raise DSparkMainProjectReferenceError(
                "captured hidden sources must share the batch extent"
            )
        frozen_batches: list[BF16Sequence] = []
        for batch, raw_sequence in enumerate(batches):
            sequence = _sequence(
                raw_sequence,
                f"captured_hidden_bf16_codes[{source}][{batch}]",
            )
            if sequence_length is None:
                sequence_length = len(sequence)
                if sequence_length < 1:
                    raise DSparkMainProjectReferenceError(
                        "captured hidden sequence extent must be nonzero"
                    )
                if batch_count * sequence_length > MAX_TOKENS_PER_TRANSACTION:
                    raise DSparkMainProjectReferenceError(
                        "captured hidden batch*sequence exceeds the transaction bound"
                    )
            elif len(sequence) != sequence_length:
                raise DSparkMainProjectReferenceError(
                    "captured hidden sources must be rectangular on the sequence axis"
                )
            frozen_batches.append(
                tuple(
                    _freeze_bf16_vector(
                        row,
                        label=(
                            "captured_hidden_bf16_codes"
                            f"[{source}][{batch}][{position}]"
                        ),
                        width=HIDDEN_WIDTH,
                    )
                    for position, row in enumerate(sequence)
                )
            )
        sources.append(tuple(frozen_batches))
    assert batch_count is not None and sequence_length is not None

    rows = tuple(
        tuple(
            code
            for source in range(SOURCE_COUNT)
            for code in sources[source][batch][position]
        )
        for batch in range(batch_count)
        for position in range(sequence_length)
    )
    return tuple(sources), batch_count, sequence_length, rows


def _freeze_resource_bytes(
    value: object,
    *,
    label: str,
    size: int,
    forbidden: tuple[int, ...],
) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise DSparkMainProjectReferenceError(
            f"{label} must be immutable bytes of length {size}"
        )
    for code in forbidden:
        if code in value:
            raise DSparkMainProjectReferenceError(
                f"{label} contains forbidden encoding 0x{code:02x}"
            )
    return value


def _scale_rows(scale_bytes: bytes) -> tuple[memoryview, ...]:
    view = memoryview(scale_bytes)
    return tuple(
        view[tile * REDUCTION_BLOCKS : (tile + 1) * REDUCTION_BLOCKS]
        for tile in range(OUTPUT_SCALE_TILES)
    )


def _activation_saturation_count(rows: BF16Matrix) -> int:
    count = 0
    try:
        for row in rows:
            for block in range(REDUCTION_BLOCKS):
                start = block * DENSE_REDUCTION_BLOCK
                count += int(
                    quantize_bf16_activation_block(
                        row[start : start + DENSE_REDUCTION_BLOCK]
                    ).saturated
                )
    except NumericReferenceError as exc:
        raise DSparkMainProjectReferenceError(
            f"activation quantization failed: {exc}"
        ) from exc
    return count


def _project_bf16(
    rows: BF16Matrix,
    weight_bytes: bytes,
    scale_bytes: bytes,
) -> DenseFP8LinearResult:
    if all(code & 0x7FFF == 0 for row in rows for code in row):
        return DenseFP8LinearResult(
            activation_saturated_block_count=0,
            output_saturated_element_count=0,
            values=tuple((0,) * OUTPUT_WIDTH for _ in rows),
        )

    zero_row = bytes(CONCATENATED_WIDTH)
    nonzero_rows = tuple(
        row
        for row in range(OUTPUT_WIDTH)
        if weight_bytes[
            row * CONCATENATED_WIDTH : (row + 1) * CONCATENATED_WIDTH
        ]
        != zero_row
    )
    if not nonzero_rows:
        return DenseFP8LinearResult(
            activation_saturated_block_count=_activation_saturation_count(rows),
            output_saturated_element_count=0,
            values=tuple((0,) * OUTPUT_WIDTH for _ in rows),
        )

    view = memoryview(weight_bytes)
    selected_weights = tuple(
        view[row * CONCATENATED_WIDTH : (row + 1) * CONCATENATED_WIDTH]
        for row in nonzero_rows
    )
    try:
        selected = dense_fp8_linear_selected_rows_bf16(
            rows,
            selected_weights,
            _scale_rows(scale_bytes),
            output_row_indices=nonzero_rows,
            declared_output_count=OUTPUT_WIDTH,
        )
    except MatrixReferenceError as exc:
        raise DSparkMainProjectReferenceError(
            f"main projection failed: {exc}"
        ) from exc
    expanded = []
    for selected_values in selected.values:
        row = [0] * OUTPUT_WIDTH
        for logical_row, code in zip(nonzero_rows, selected_values, strict=True):
            row[logical_row] = code
        expanded.append(tuple(row))
    return DenseFP8LinearResult(
        selected.activation_saturated_block_count,
        selected.output_saturated_element_count,
        tuple(expanded),
    )


def _reshape_rows(
    rows: BF16Matrix,
    *,
    batch_count: int,
    sequence_length: int,
) -> BF16Batch:
    return tuple(
        tuple(
            rows[batch * sequence_length + position]
            for position in range(sequence_length)
        )
        for batch in range(batch_count)
    )


def _balanced_add_count(width: int) -> int:
    count = 0
    level = width
    while level > 1:
        if level & 1:
            level += 1
        count += level // 2
        level //= 2
    return count


def _counter_values(
    *,
    batch_count: int,
    sequence_length: int,
    activation_saturations: int,
    projection_saturations: int,
    rms_saturations: int,
) -> dict[str, int]:
    token_count = batch_count * sequence_length
    projection_outputs = token_count * OUTPUT_WIDTH
    block_dots = projection_outputs * REDUCTION_BLOCKS
    return {
        "batch_count": batch_count,
        "sequence_length": sequence_length,
        "token_count": token_count,
        "source_count": SOURCE_COUNT,
        "source_hidden_width": HIDDEN_WIDTH,
        "concatenated_width": CONCATENATED_WIDTH,
        "projection_output_width": OUTPUT_WIDTH,
        "capture_input_bf16_values": token_count * CONCATENATED_WIDTH,
        "concatenated_view_bf16_values": token_count * CONCATENATED_WIDTH,
        "activation_blocks_quantized": token_count * REDUCTION_BLOCKS,
        "activation_values_quantized": token_count * CONCATENATED_WIDTH,
        "projection_weight_e4m3_values": WEIGHT_BYTES,
        "projection_scale_e8m0_values": SCALE_BYTES,
        "projection_block_dots": block_dots,
        "projection_exact_product_accumulates": (
            block_dots * DENSE_REDUCTION_BLOCK
        ),
        "projection_cross_block_reduction_adds": (
            projection_outputs * _balanced_add_count(REDUCTION_BLOCKS)
        ),
        "projection_bf16_conversions": projection_outputs,
        "rms_weight_bf16_values": OUTPUT_WIDTH,
        "rms_square_multiplies": projection_outputs,
        "rms_reduction_adds": token_count * (OUTPUT_WIDTH - 1),
        "rms_divides": token_count,
        "rms_epsilon_adds": token_count,
        "rms_rsqrt_evaluations": token_count,
        "rms_pointwise_multiplies": 2 * projection_outputs,
        "rms_bf16_conversions": projection_outputs,
        "activation_saturated_blocks": activation_saturations,
        "projection_saturated_outputs": projection_saturations,
        "rms_saturated_outputs": rms_saturations,
        "transaction_commits": 1,
    }


def _validate_counters(counters: object) -> DSparkMainProjectCounters:
    if type(counters) is not DSparkMainProjectCounters:
        raise DSparkMainProjectReferenceError(
            "counters must be an exact DSparkMainProjectCounters record"
        )
    batch_count = _integer(
        counters.batch_count,
        "counters.batch_count",
        minimum=1,
        maximum=MAX_TOKENS_PER_TRANSACTION,
    )
    sequence_length = _integer(
        counters.sequence_length,
        "counters.sequence_length",
        minimum=1,
        maximum=MAX_TOKENS_PER_TRANSACTION,
    )
    token_count = batch_count * sequence_length
    if token_count > MAX_TOKENS_PER_TRANSACTION:
        raise DSparkMainProjectReferenceError(
            "counter token count exceeds the transaction bound"
        )
    activation_saturations = _integer(
        counters.activation_saturated_blocks,
        "counters.activation_saturated_blocks",
        minimum=0,
        maximum=token_count * REDUCTION_BLOCKS,
    )
    projection_saturations = _integer(
        counters.projection_saturated_outputs,
        "counters.projection_saturated_outputs",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    rms_saturations = _integer(
        counters.rms_saturated_outputs,
        "counters.rms_saturated_outputs",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    expected = _counter_values(
        batch_count=batch_count,
        sequence_length=sequence_length,
        activation_saturations=activation_saturations,
        projection_saturations=projection_saturations,
        rms_saturations=rms_saturations,
    )
    for name, expected_value in expected.items():
        observed = getattr(counters, name)
        if type(observed) is not int or observed != expected_value:
            raise DSparkMainProjectReferenceError(
                f"counters.{name} does not reconcile to DSpark dimensions"
            )
    return counters


def _immutable_batch(
    value: object,
    *,
    label: str,
    batch_count: int,
    sequence_length: int,
) -> BF16Batch:
    batches = _exact_tuple(value, label)
    if len(batches) != batch_count:
        raise DSparkMainProjectReferenceError(
            f"{label} batch extent does not reconcile"
        )
    frozen_batches: list[BF16Sequence] = []
    for batch, sequence in enumerate(batches):
        immutable_sequence = _exact_tuple(sequence, f"{label}[{batch}]")
        if len(immutable_sequence) != sequence_length:
            raise DSparkMainProjectReferenceError(
                f"{label}[{batch}] sequence extent does not reconcile"
            )
        frozen_batches.append(
            tuple(
                _freeze_bf16_vector(
                    row,
                    label=f"{label}[{batch}][{position}]",
                    width=OUTPUT_WIDTH,
                    exact_tuple=True,
                )
                for position, row in enumerate(immutable_sequence)
            )
        )
    return tuple(frozen_batches)


def _validate_result(result: object) -> DSparkMainProjectResult:
    if type(result) is not DSparkMainProjectResult:
        raise DSparkMainProjectReferenceError(
            "result must be an exact DSparkMainProjectResult record"
        )
    if type(result.numeric_profile) is not str or result.numeric_profile != (
        NUMERIC_PROFILE
    ):
        raise DSparkMainProjectReferenceError("result numeric profile differs")
    if (
        type(result.source_layer_ids) is not tuple
        or result.source_layer_ids != SOURCE_LAYER_IDS
        or any(type(layer) is not int for layer in result.source_layer_ids)
    ):
        raise DSparkMainProjectReferenceError("result source-layer order differs")
    if type(result.counters) is not DSparkMainProjectCounters:
        raise DSparkMainProjectReferenceError(
            "result counters must be an exact DSparkMainProjectCounters record"
        )
    counters = _validate_counters(result.counters)
    projection = _immutable_batch(
        result.projection_bf16_codes,
        label="result.projection_bf16_codes",
        batch_count=counters.batch_count,
        sequence_length=counters.sequence_length,
    )
    normalized = _immutable_batch(
        result.normalized_bf16_codes,
        label="result.normalized_bf16_codes",
        batch_count=counters.batch_count,
        sequence_length=counters.sequence_length,
    )
    norm_weight = _freeze_bf16_vector(
        result.norm_weight_bf16_codes,
        label="result.norm_weight_bf16_codes",
        width=OUTPUT_WIDTH,
        exact_tuple=True,
    )
    token_count = counters.token_count
    means = _exact_tuple(
        result.mean_square_binary32_codes,
        "result.mean_square_binary32_codes",
    )
    inverses = _exact_tuple(
        result.inverse_rms_binary32_codes,
        "result.inverse_rms_binary32_codes",
    )
    if len(means) != token_count or len(inverses) != token_count:
        raise DSparkMainProjectReferenceError(
            "result RMS diagnostic extent does not reconcile"
        )
    for label, values in (("mean", means), ("inverse", inverses)):
        for index, code in enumerate(values):
            if type(code) is not int or not 0 <= code < 1 << 32:
                raise DSparkMainProjectReferenceError(
                    f"result RMS {label}[{index}] must be an exact binary32 code"
                )
            if code & 0x7F800000 == 0x7F800000:
                raise DSparkMainProjectReferenceError(
                    f"result RMS {label}[{index}] must be finite binary32"
                )
    activation_saturations = _integer(
        result.activation_saturated_block_count,
        "result.activation_saturated_block_count",
        minimum=0,
        maximum=token_count * REDUCTION_BLOCKS,
    )
    projection_saturations = _integer(
        result.projection_saturated_output_count,
        "result.projection_saturated_output_count",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    normalization_saturations = _integer(
        result.normalization_saturated_output_count,
        "result.normalization_saturated_output_count",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    if (
        counters.activation_saturated_blocks != activation_saturations
        or counters.projection_saturated_outputs != projection_saturations
        or counters.rms_saturated_outputs != normalization_saturations
    ):
        raise DSparkMainProjectReferenceError(
            "result saturation counts do not reconcile to counters"
        )
    projection_saturation_candidates = sum(
        code & 0x7FFF == 0x7F7F
        for sequence in projection
        for row in sequence
        for code in row
    )
    if projection_saturations > projection_saturation_candidates:
        raise DSparkMainProjectReferenceError(
            "projection saturation count exceeds maximum-finite candidates"
        )

    projection_rows = tuple(row for sequence in projection for row in sequence)
    try:
        expected_norm = rms_norm_bf16(
            projection_rows,
            norm_weight,
            epsilon_binary32=NORM_EPSILON_BINARY32,
        )
    except NormalizationReferenceError as exc:
        raise DSparkMainProjectReferenceError(
            f"result RMS reconciliation failed: {exc}"
        ) from exc
    expected_normalized = _reshape_rows(
        expected_norm.output_codes,
        batch_count=counters.batch_count,
        sequence_length=counters.sequence_length,
    )
    if (
        normalized != expected_normalized
        or tuple(means) != expected_norm.mean_square_codes
        or tuple(inverses) != expected_norm.inverse_rms_codes
        or normalization_saturations != expected_norm.output_saturation_count
    ):
        raise DSparkMainProjectReferenceError(
            "result weighted-RMS boundary does not reconcile to projection"
        )
    return result


def dspark_main_project_bf16(
    captured_hidden_bf16_codes: object,
    projection_weight_e4m3_bytes: object,
    projection_scale_e8m0_bytes: object,
    norm_weight_bf16_codes: object,
) -> DSparkMainProjectResult:
    """Execute the complete official DSpark main-conditioning composition.

    Captures are supplied in the fixed layer order ``(40, 41, 42)`` with each
    tensor shaped ``[B,S,4096]`` and ``B*S`` in ``1..4``. Projection resources
    are contiguous row-major immutable bytes with official shapes
    ``[4096,12288]`` and ``[32,96]``. The result retains both architectural
    boundaries and the norm weights needed to reconcile the second boundary.
    """

    _, batch_count, sequence_length, rows = _freeze_captures(
        captured_hidden_bf16_codes
    )
    weights = _freeze_resource_bytes(
        projection_weight_e4m3_bytes,
        label="projection_weight_e4m3_bytes",
        size=WEIGHT_BYTES,
        forbidden=(0x7F, 0xFF),
    )
    scales = _freeze_resource_bytes(
        projection_scale_e8m0_bytes,
        label="projection_scale_e8m0_bytes",
        size=SCALE_BYTES,
        forbidden=(0xFF,),
    )
    norm_weight = _freeze_bf16_vector(
        norm_weight_bf16_codes,
        label="norm_weight_bf16_codes",
        width=OUTPUT_WIDTH,
    )

    projection = _project_bf16(rows, weights, scales)
    try:
        normalized = rms_norm_bf16(
            projection.values,
            norm_weight,
            epsilon_binary32=NORM_EPSILON_BINARY32,
        )
    except NormalizationReferenceError as exc:
        raise DSparkMainProjectReferenceError(
            f"main normalization failed: {exc}"
        ) from exc
    counters = DSparkMainProjectCounters(
        **_counter_values(
            batch_count=batch_count,
            sequence_length=sequence_length,
            activation_saturations=projection.activation_saturated_block_count,
            projection_saturations=projection.output_saturated_element_count,
            rms_saturations=normalized.output_saturation_count,
        )
    )
    return DSparkMainProjectResult(
        numeric_profile=NUMERIC_PROFILE,
        source_layer_ids=SOURCE_LAYER_IDS,
        projection_bf16_codes=_reshape_rows(
            projection.values,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
        normalized_bf16_codes=_reshape_rows(
            normalized.output_codes,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
        norm_weight_bf16_codes=norm_weight,
        mean_square_binary32_codes=normalized.mean_square_codes,
        inverse_rms_binary32_codes=normalized.inverse_rms_codes,
        activation_saturated_block_count=(
            projection.activation_saturated_block_count
        ),
        projection_saturated_output_count=(
            projection.output_saturated_element_count
        ),
        normalization_saturated_output_count=normalized.output_saturation_count,
        counters=counters,
    )


def official_resource_hashes(
    projection_weight_e4m3_bytes: object,
    projection_scale_e8m0_bytes: object,
    norm_weight_bf16_codes: object,
) -> dict[str, str]:
    """Validate resources and return identities without promoting provenance."""

    weights = _freeze_resource_bytes(
        projection_weight_e4m3_bytes,
        label="projection_weight_e4m3_bytes",
        size=WEIGHT_BYTES,
        forbidden=(0x7F, 0xFF),
    )
    scales = _freeze_resource_bytes(
        projection_scale_e8m0_bytes,
        label="projection_scale_e8m0_bytes",
        size=SCALE_BYTES,
        forbidden=(0xFF,),
    )
    norm = _freeze_bf16_vector(
        norm_weight_bf16_codes,
        label="norm_weight_bf16_codes",
        width=OUTPUT_WIDTH,
    )
    return {
        "norm_weight_sha256": hashlib.sha256(
            b"".join(code.to_bytes(2, "little") for code in norm)
        ).hexdigest(),
        "scale_sha256": hashlib.sha256(scales).hexdigest(),
        "weight_sha256": hashlib.sha256(weights).hexdigest(),
    }


__all__ = [
    "CHECKPOINT_LOCK_ID",
    "CONFIG_EXPECTED_FIELDS",
    "CONCATENATED_WIDTH",
    "EXCLUDED_CLAIMS",
    "HIDDEN_WIDTH",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "MAX_TOKENS_PER_TRANSACTION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "NORM_WEIGHT_BYTES",
    "NUMERIC_PROFILE",
    "OFFICIAL_NORM_WEIGHT_SHA256",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_SCALE_SHA256",
    "OFFICIAL_WEIGHT_SHA256",
    "OUTPUT_WIDTH",
    "REDUCTION_BLOCKS",
    "SCALE_BYTES",
    "SOURCE_COUNT",
    "SOURCE_EXPRESSIONS",
    "SOURCE_LAYER_IDS",
    "WEIGHT_BYTES",
    "DSparkMainProjectCounters",
    "DSparkMainProjectReferenceError",
    "DSparkMainProjectResult",
    "dspark_main_project_bf16",
    "official_resource_hashes",
]
