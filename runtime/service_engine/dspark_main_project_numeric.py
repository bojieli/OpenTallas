"""Independent functional arithmetic for DeepSeek V4 DSpark conditioning.

The pinned source captures hidden states from main layers 40, 41, and 42,
concatenates them in that order, applies the released 4,096 by 12,288
FP8/E8M0 projection, and applies weighted BF16 RMS normalization.  This module
implements that composition without importing ``runtime.reference`` or any
compiler package.

The complete immutable resources validate before any exact-zero acceleration.
All-zero activation rows and byte-exact all-zero weight rows may skip redundant
products, while the logical counters retain the complete declared operation.
Those counters are semantic reconciliation values only: they are not physical
bytes, cycles, bandwidth, latency, throughput, energy, area, density, or PPA.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .fp8_numeric import FP8ServiceNumericError, execute_selected_rows
from .rms_numeric import (
    RMS_NORM_EPSILON_BINARY32,
    RMSServiceNumericError,
    execute_weighted_rms_norm,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
SERVICE_NUMERIC_PROFILE = "opentallas.deepseek_v4_dspark_main_project_service.v1"

SOURCE_LAYER_IDS = (40, 41, 42)
SOURCE_COUNT = len(SOURCE_LAYER_IDS)
HIDDEN_WIDTH = 4096
CONCATENATED_WIDTH = SOURCE_COUNT * HIDDEN_WIDTH
OUTPUT_WIDTH = HIDDEN_WIDTH
DENSE_BLOCK_SIZE = 128
REDUCTION_BLOCKS = CONCATENATED_WIDTH // DENSE_BLOCK_SIZE
OUTPUT_SCALE_TILES = OUTPUT_WIDTH // DENSE_BLOCK_SIZE
WEIGHT_BYTES = OUTPUT_WIDTH * CONCATENATED_WIDTH
SCALE_BYTES = OUTPUT_SCALE_TILES * REDUCTION_BLOCKS
MAX_TOKENS_PER_COMMAND = 4

BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16CaptureSet: TypeAlias = tuple[BF16Batch, ...]

_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

EXCLUDED_CLAIMS = (
    "target_hidden_capture_execution",
    "checkpoint_derived_activation",
    "checkpoint_or_artifact_authentication",
    "compiler_lowering",
    "complete_dspark_stage_execution",
    "rtl_execution",
    "physical_bytes_cycles_bandwidth_latency_throughput_energy_area_density_ppa",
    "gpu_performance_advantage",
)


class DSparkMainProjectServiceNumericError(ValueError):
    """Raised when the complete functional command must poison."""


@dataclass(frozen=True, slots=True)
class DSparkMainProjectServiceResult:
    """Immutable projection/RMS boundaries and semantic reconciliation data.

    The retained projection and norm weight authenticate the RMS relationship.
    This record deliberately does not retain the 50 MiB projection resource or
    source captures, so its public constructor cannot independently authenticate
    the projection arithmetic or checkpoint provenance.
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
    logical_counters: Mapping[str, int]

    def __post_init__(self) -> None:
        _validate_result(self)

    @property
    def semantic_counters(self) -> Mapping[str, int]:
        """Alias emphasizing that these values make no physical claim."""

        return self.logical_counters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must be an exact list or tuple"
        )
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must be a deeply immutable exact tuple"
        )
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    if value & 0x7F80 == 0x7F80:
        raise DSparkMainProjectServiceNumericError(f"{label} must be finite BF16")
    return value


def _freeze_vector(
    value: object,
    *,
    label: str,
    width: int,
    exact_tuple: bool = False,
) -> BF16Vector:
    raw = _exact_tuple(value, label) if exact_tuple else _sequence(value, label)
    if len(raw) != width:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must contain exactly {width} values"
        )
    return tuple(
        _finite_bf16(code, f"{label}[{column}]")
        for column, code in enumerate(raw)
    )


def _freeze_captures(value: object) -> tuple[BF16CaptureSet, int, int, BF16Matrix]:
    raw_sources = _sequence(value, "captured_hidden_bf16_codes")
    if len(raw_sources) != SOURCE_COUNT:
        raise DSparkMainProjectServiceNumericError(
            f"captured_hidden_bf16_codes must contain exactly {SOURCE_COUNT} sources"
        )

    sources: list[BF16Batch] = []
    batch_count: int | None = None
    sequence_length: int | None = None
    for source_index, raw_batches in enumerate(raw_sources):
        batches = _sequence(
            raw_batches,
            f"captured_hidden_bf16_codes[{source_index}]",
        )
        if batch_count is None:
            batch_count = len(batches)
            if not 1 <= batch_count <= MAX_TOKENS_PER_COMMAND:
                raise DSparkMainProjectServiceNumericError(
                    "captured hidden batch extent is outside the command bound"
                )
        elif len(batches) != batch_count:
            raise DSparkMainProjectServiceNumericError(
                "captured hidden sources must share the batch extent"
            )

        frozen_batches: list[BF16Sequence] = []
        for batch_index, raw_positions in enumerate(batches):
            positions = _sequence(
                raw_positions,
                f"captured_hidden_bf16_codes[{source_index}][{batch_index}]",
            )
            if sequence_length is None:
                sequence_length = len(positions)
                if sequence_length < 1:
                    raise DSparkMainProjectServiceNumericError(
                        "captured hidden sequence extent must be nonzero"
                    )
                if batch_count * sequence_length > MAX_TOKENS_PER_COMMAND:
                    raise DSparkMainProjectServiceNumericError(
                        "captured hidden batch*sequence exceeds the command bound"
                    )
            elif len(positions) != sequence_length:
                raise DSparkMainProjectServiceNumericError(
                    "captured hidden sources must be rectangular on the sequence axis"
                )
            frozen_batches.append(
                tuple(
                    _freeze_vector(
                        row,
                        label=(
                            "captured_hidden_bf16_codes"
                            f"[{source_index}][{batch_index}][{position}]"
                        ),
                        width=HIDDEN_WIDTH,
                    )
                    for position, row in enumerate(positions)
                )
            )
        sources.append(tuple(frozen_batches))

    assert batch_count is not None and sequence_length is not None
    rows = tuple(
        tuple(
            code
            for source_index in range(SOURCE_COUNT)
            for code in sources[source_index][batch_index][position]
        )
        for batch_index in range(batch_count)
        for position in range(sequence_length)
    )
    return tuple(sources), batch_count, sequence_length, rows


def _resource_bytes(
    value: object,
    *,
    label: str,
    size: int,
    forbidden: tuple[int, ...],
) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise DSparkMainProjectServiceNumericError(
            f"{label} must be immutable bytes of length {size}"
        )
    for code in forbidden:
        if code in value:
            raise DSparkMainProjectServiceNumericError(
                f"{label} contains forbidden encoding 0x{code:02x}"
            )
    return value


def _execute_projection(
    rows: BF16Matrix,
    weights: bytes,
    scales: bytes,
) -> tuple[BF16Matrix, int, int]:
    if all(code & 0x7FFF == 0 for row in rows for code in row):
        return tuple((0,) * OUTPUT_WIDTH for _ in rows), 0, 0

    zero_row = bytes(CONCATENATED_WIDTH)
    nonzero_rows = tuple(
        row
        for row in range(OUTPUT_WIDTH)
        if weights[row * CONCATENATED_WIDTH : (row + 1) * CONCATENATED_WIDTH]
        != zero_row
    )
    evaluated_rows = nonzero_rows or (0,)

    def weight_row(logical_row: int) -> bytes:
        start = logical_row * CONCATENATED_WIDTH
        return weights[start : start + CONCATENATED_WIDTH]

    def scale_code(logical_row: int, block_index: int) -> int:
        return scales[
            (logical_row // DENSE_BLOCK_SIZE) * REDUCTION_BLOCKS + block_index
        ]

    try:
        selected, activation_saturations, output_saturations = execute_selected_rows(
            rows,
            selected_rows=evaluated_rows,
            input_features=CONCATENATED_WIDTH,
            weight_row=weight_row,
            scale_code=scale_code,
        )
    except FP8ServiceNumericError as exc:
        raise DSparkMainProjectServiceNumericError(
            f"main projection failed: {exc}"
        ) from exc

    if not nonzero_rows:
        return tuple((0,) * OUTPUT_WIDTH for _ in rows), activation_saturations, 0

    expanded: list[BF16Vector] = []
    for selected_values in selected:
        row = [0] * OUTPUT_WIDTH
        for logical_row, code in zip(nonzero_rows, selected_values, strict=True):
            row[logical_row] = code
        expanded.append(tuple(row))
    return tuple(expanded), activation_saturations, output_saturations


def _reshape_rows(
    rows: BF16Matrix,
    *,
    batch_count: int,
    sequence_length: int,
) -> BF16Batch:
    return tuple(
        tuple(
            rows[batch_index * sequence_length + position]
            for position in range(sequence_length)
        )
        for batch_index in range(batch_count)
    )


def _balanced_add_count(width: int) -> int:
    additions = 0
    level = width
    while level > 1:
        if level & 1:
            level += 1
        additions += level // 2
        level //= 2
    return additions


def dspark_main_project_functional_counters(
    *,
    batch_count: int,
    sequence_length: int,
    activation_saturations: int,
    projection_saturations: int,
    rms_saturations: int,
) -> Mapping[str, int]:
    """Return immutable logical work for the complete declared composition."""

    batch_count = _integer(
        batch_count,
        "batch_count",
        minimum=1,
        maximum=MAX_TOKENS_PER_COMMAND,
    )
    sequence_length = _integer(
        sequence_length,
        "sequence_length",
        minimum=1,
        maximum=MAX_TOKENS_PER_COMMAND,
    )
    token_count = batch_count * sequence_length
    if token_count > MAX_TOKENS_PER_COMMAND:
        raise DSparkMainProjectServiceNumericError(
            "counter token count exceeds the command bound"
        )
    activation_saturations = _integer(
        activation_saturations,
        "activation_saturations",
        minimum=0,
        maximum=token_count * REDUCTION_BLOCKS,
    )
    projection_saturations = _integer(
        projection_saturations,
        "projection_saturations",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    rms_saturations = _integer(
        rms_saturations,
        "rms_saturations",
        minimum=0,
        maximum=token_count * OUTPUT_WIDTH,
    )
    projection_outputs = token_count * OUTPUT_WIDTH
    block_dots = projection_outputs * REDUCTION_BLOCKS
    return MappingProxyType(
        {
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
            "projection_exact_product_accumulates": block_dots * DENSE_BLOCK_SIZE,
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
    )


def _immutable_batch(
    value: object,
    *,
    label: str,
    batch_count: int,
    sequence_length: int,
) -> BF16Batch:
    batches = _exact_tuple(value, label)
    if len(batches) != batch_count:
        raise DSparkMainProjectServiceNumericError(
            f"{label} batch extent does not reconcile"
        )
    frozen: list[BF16Sequence] = []
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _exact_tuple(raw_sequence, f"{label}[{batch_index}]")
        if len(sequence) != sequence_length:
            raise DSparkMainProjectServiceNumericError(
                f"{label}[{batch_index}] sequence extent does not reconcile"
            )
        frozen.append(
            tuple(
                _freeze_vector(
                    row,
                    label=f"{label}[{batch_index}][{position}]",
                    width=OUTPUT_WIDTH,
                    exact_tuple=True,
                )
                for position, row in enumerate(sequence)
            )
        )
    return tuple(frozen)


def _validate_result(result: object) -> DSparkMainProjectServiceResult:
    if type(result) is not DSparkMainProjectServiceResult:
        raise DSparkMainProjectServiceNumericError(
            "result must be an exact DSparkMainProjectServiceResult record"
        )
    if (
        type(result.numeric_profile) is not str
        or result.numeric_profile != SERVICE_NUMERIC_PROFILE
    ):
        raise DSparkMainProjectServiceNumericError("result numeric profile differs")
    if (
        type(result.source_layer_ids) is not tuple
        or result.source_layer_ids != SOURCE_LAYER_IDS
        or any(type(layer) is not int for layer in result.source_layer_ids)
    ):
        raise DSparkMainProjectServiceNumericError(
            "result source-layer order differs"
        )
    if type(result.logical_counters) is not _MAPPING_PROXY_TYPE:
        raise DSparkMainProjectServiceNumericError(
            "result logical counters must be an immutable mapping"
        )
    observed_counters = dict(result.logical_counters)
    try:
        batch_count = observed_counters["batch_count"]
        sequence_length = observed_counters["sequence_length"]
    except KeyError as exc:
        raise DSparkMainProjectServiceNumericError(
            "result logical counters omit shape metadata"
        ) from exc

    projection = _immutable_batch(
        result.projection_bf16_codes,
        label="result.projection_bf16_codes",
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    normalized = _immutable_batch(
        result.normalized_bf16_codes,
        label="result.normalized_bf16_codes",
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    norm_weight = _freeze_vector(
        result.norm_weight_bf16_codes,
        label="result.norm_weight_bf16_codes",
        width=OUTPUT_WIDTH,
        exact_tuple=True,
    )
    token_count = batch_count * sequence_length
    means = _exact_tuple(
        result.mean_square_binary32_codes,
        "result.mean_square_binary32_codes",
    )
    inverses = _exact_tuple(
        result.inverse_rms_binary32_codes,
        "result.inverse_rms_binary32_codes",
    )
    if len(means) != token_count or len(inverses) != token_count:
        raise DSparkMainProjectServiceNumericError(
            "result RMS diagnostic extent does not reconcile"
        )
    for label, values in (("mean", means), ("inverse", inverses)):
        for index, code in enumerate(values):
            if type(code) is not int or not 0 <= code < 1 << 32:
                raise DSparkMainProjectServiceNumericError(
                    f"result RMS {label}[{index}] must be an exact binary32 code"
                )
            if code & 0x7F800000 == 0x7F800000:
                raise DSparkMainProjectServiceNumericError(
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
    expected_counters = dspark_main_project_functional_counters(
        batch_count=batch_count,
        sequence_length=sequence_length,
        activation_saturations=activation_saturations,
        projection_saturations=projection_saturations,
        rms_saturations=normalization_saturations,
    )
    if observed_counters != dict(expected_counters):
        raise DSparkMainProjectServiceNumericError(
            "result logical counters do not reconcile"
        )

    projection_saturation_candidates = sum(
        code & 0x7FFF == 0x7F7F
        for sequence in projection
        for row in sequence
        for code in row
    )
    if projection_saturations > projection_saturation_candidates:
        raise DSparkMainProjectServiceNumericError(
            "projection saturation count exceeds maximum-finite candidates"
        )

    projection_rows = tuple(row for sequence in projection for row in sequence)
    try:
        expected_norm = execute_weighted_rms_norm(
            projection_rows,
            norm_weight,
            epsilon_binary32=RMS_NORM_EPSILON_BINARY32,
        )
    except RMSServiceNumericError as exc:
        raise DSparkMainProjectServiceNumericError(
            f"result RMS reconciliation failed: {exc}"
        ) from exc
    expected_normalized = _reshape_rows(
        expected_norm.output_codes,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    if (
        normalized != expected_normalized
        or tuple(means) != expected_norm.mean_square_codes
        or tuple(inverses) != expected_norm.inverse_rms_codes
        or normalization_saturations != expected_norm.output_saturation_count
    ):
        raise DSparkMainProjectServiceNumericError(
            "result weighted-RMS boundary does not reconcile to projection"
        )

    object.__setattr__(
        result,
        "logical_counters",
        MappingProxyType(observed_counters),
    )
    return result


def execute_dspark_main_project_bf16(
    captured_hidden_bf16_codes: object,
    projection_weight_e4m3_bytes: object,
    projection_scale_e8m0_bytes: object,
    norm_weight_bf16_codes: object,
) -> DSparkMainProjectServiceResult:
    """Execute the complete target arithmetic for one bounded command."""

    _, batch_count, sequence_length, rows = _freeze_captures(
        captured_hidden_bf16_codes
    )
    weights = _resource_bytes(
        projection_weight_e4m3_bytes,
        label="projection_weight_e4m3_bytes",
        size=WEIGHT_BYTES,
        forbidden=(0x7F, 0xFF),
    )
    scales = _resource_bytes(
        projection_scale_e8m0_bytes,
        label="projection_scale_e8m0_bytes",
        size=SCALE_BYTES,
        forbidden=(0xFF,),
    )
    norm_weight = _freeze_vector(
        norm_weight_bf16_codes,
        label="norm_weight_bf16_codes",
        width=OUTPUT_WIDTH,
    )

    projection, activation_saturations, projection_saturations = (
        _execute_projection(rows, weights, scales)
    )
    try:
        normalized = execute_weighted_rms_norm(
            projection,
            norm_weight,
            epsilon_binary32=RMS_NORM_EPSILON_BINARY32,
        )
    except RMSServiceNumericError as exc:
        raise DSparkMainProjectServiceNumericError(
            f"main normalization failed: {exc}"
        ) from exc
    counters = dspark_main_project_functional_counters(
        batch_count=batch_count,
        sequence_length=sequence_length,
        activation_saturations=activation_saturations,
        projection_saturations=projection_saturations,
        rms_saturations=normalized.output_saturation_count,
    )
    return DSparkMainProjectServiceResult(
        numeric_profile=SERVICE_NUMERIC_PROFILE,
        source_layer_ids=SOURCE_LAYER_IDS,
        projection_bf16_codes=_reshape_rows(
            projection,
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
        activation_saturated_block_count=activation_saturations,
        projection_saturated_output_count=projection_saturations,
        normalization_saturated_output_count=normalized.output_saturation_count,
        logical_counters=counters,
    )


__all__ = [
    "CONCATENATED_WIDTH",
    "EXCLUDED_CLAIMS",
    "HIDDEN_WIDTH",
    "MAX_TOKENS_PER_COMMAND",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OUTPUT_WIDTH",
    "REDUCTION_BLOCKS",
    "SCALE_BYTES",
    "SERVICE_NUMERIC_PROFILE",
    "SOURCE_COUNT",
    "SOURCE_LAYER_IDS",
    "WEIGHT_BYTES",
    "DSparkMainProjectServiceNumericError",
    "DSparkMainProjectServiceResult",
    "dspark_main_project_functional_counters",
    "execute_dspark_main_project_bf16",
]
