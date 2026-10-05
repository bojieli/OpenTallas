"""Deterministic DeepSeek V4 DSpark prefill-only KV composition.

During ``forward_spec(..., start_pos=0)`` each of the three DSpark blocks skips
its ordinary block body.  It projects the already-normalized DSpark
conditioning through that stage's FP8 ``wkv``, applies the BF16 ``kv_norm``,
base RoPE, block-64 FP8 QDQ to the 448 non-RoPE channels, and commits the
resulting 512-value rows to the stage-local circular window.  It returns the
draft hidden state unchanged; that dataflow alias belongs to the graph and is
not duplicated here.

This module composes already qualified arithmetic and state references while
retaining every boundary.  Exact-zero and zero-weight-row acceleration is
permitted only after complete resources validate, and semantic counters retain
the declared work.  Logical values and bytes are not physical ROM/SRAM/HBM
traffic, cycles, bandwidth, latency, throughput, energy, area, or PPA.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import TypeAlias

from .formats import NumericReferenceError, decode_bf16, quantize_bf16_activation_block
from .kv_window import (
    KVWindowReferenceError,
    KVWindowState,
    KVWindowWriteResult,
    kv_window_state_bf16,
    kv_window_write_bf16,
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
from .quantization import QuantizationReferenceError, fp8_qdq_bf16
from .rope import (
    BASE_ROPE_PROFILE,
    MAX_SEQUENCE_LENGTH,
    RopeReferenceError,
    apply_rotary_bf16_result,
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
NUMERIC_PROFILE = "opentallas.deepseek_v4_dspark_prefill_kv_bf16.v1"

STAGE_COUNT = 3
INPUT_WIDTH = 4096
KV_WIDTH = 512
ROPE_WIDTH = 64
QDQ_WIDTH = KV_WIDTH - ROPE_WIDTH
DENSE_BLOCK_SIZE = 128
REDUCTION_BLOCKS = INPUT_WIDTH // DENSE_BLOCK_SIZE
OUTPUT_SCALE_TILES = KV_WIDTH // DENSE_BLOCK_SIZE
FP8_QDQ_BLOCK_SIZE = 64
FP8_QDQ_BLOCKS = QDQ_WIDTH // FP8_QDQ_BLOCK_SIZE
WINDOW_SIZE = 128
MAX_BATCH_SIZE = 4
MAX_PREFILL_SEQUENCE = MAX_SEQUENCE_LENGTH
WEIGHT_BYTES = KV_WIDTH * INPUT_WIDTH
SCALE_BYTES = OUTPUT_SCALE_TILES * REDUCTION_BLOCKS
NORM_WEIGHT_BYTES = KV_WIDTH * 2

OFFICIAL_WEIGHT_SHA256 = (
    "20c0fa4ef0ae2ef220c961ef65c5f3eabaea222076045f079598f256af69f879",
    "f07ed5151bfb40f806ffa38d9690e15edad187784014f18af3794a15402b2fbe",
    "bb8763965211a702de6774c88c3029870287053acd3d0bc3f8bf13e9da95dd2d",
)
OFFICIAL_SCALE_SHA256 = (
    "54f9be7d804c9fb80089795165c60096bb09e41f4ac2fe6b49cae5dfe128cfdb",
    "d21da0046a704b7c13202583b9b25630c200fc5ed4a8f7b7f71553b5c0d535d2",
    "977c8ed4b4a12c1c6f9fa3f71f41d1bb95758e55b8dfc9df50b1c327e8557370",
)
OFFICIAL_NORM_WEIGHT_SHA256 = (
    "1019ee0ee1beae3b42168430434f61e11315c6a5597d99483f0c6410015b9d7d",
    "ba6cb6d2cd77bce562feebd727810d82d6971d28f16aa1f992ed498bd0756fc6",
    "d509478a1a195bea335f2a29f96c8d2df6e00e94c88721a58b377c6a0f91150c",
)

SOURCE_EXPRESSIONS = (
    "if start_pos > 0:",
    "return super().forward(x, start_pos, input_ids, main_x)",
    "return self.attn(x, start_pos, main_x)",
    "main_kv = self.kv_norm(self.wkv(main_x))",
    "apply_rotary_emb(main_kv[..., -rd:], main_freqs_cis)",
    "act_quant(main_kv[..., :-rd], 64, scale_fmt, scale_dtype, True)",
    "self.kv_cache[:bsz, :seqlen] = main_kv",
)

EXCLUDED_CLAIMS = (
    "dspark_conditioning_producer_execution",
    "draft_hidden_or_block_execution",
    "checkpoint_derived_activation",
    "artifact_driven_service_execution",
    "rtl_execution",
    "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_ppa",
    "gpu_performance_advantage",
)

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
U8Sequence: TypeAlias = tuple[tuple[int, ...], ...]
U8Batch: TypeAlias = tuple[U8Sequence, ...]


class DSparkPrefillKVReferenceError(ValueError):
    """Raised when the complete prefill composition must poison."""


@dataclass(frozen=True, slots=True)
class DSparkPrefillKVCounters:
    """Complete logical arithmetic, state, and commit reconciliation."""

    stage_id: int
    batch_count: int
    sequence_length: int
    token_count: int
    state_batch_capacity: int
    previous_active_batch_count: int
    removed_batch_count: int
    conditioning_bf16_values: int
    projection_weight_e4m3_values: int
    projection_scale_e8m0_values: int
    activation_blocks_quantized: int
    activation_values_quantized: int
    activation_saturated_blocks: int
    projection_block_dots: int
    projection_exact_product_accumulates: int
    projection_cross_block_reduction_adds: int
    projection_bf16_conversions: int
    projection_saturated_outputs: int
    rms_weight_bf16_values: int
    rms_square_multiplies: int
    rms_reduction_adds: int
    rms_divides: int
    rms_epsilon_adds: int
    rms_rsqrt_evaluations: int
    rms_pointwise_multiplies: int
    rms_bf16_conversions: int
    rms_saturated_outputs: int
    rope_prefix_bf16_values_preserved: int
    rope_rotated_bf16_values: int
    rope_phasor_binary32_values_read: int
    rope_binary32_multiplications: int
    rope_binary32_additions_or_subtractions: int
    rope_bf16_conversions: int
    qdq_input_bf16_values: int
    qdq_blocks_quantized: int
    qdq_e4m3_values: int
    qdq_scale_e8m0_values: int
    qdq_output_bf16_values: int
    kv_rows_produced: int
    window_source_rows_read: int
    window_source_bf16_values_read: int
    window_state_rows_written: int
    window_state_bf16_values_written: int
    window_state_write_logical_bytes: int
    window_state_rows_preserved: int
    window_metadata_fields_read: int
    window_metadata_fields_written: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class DSparkPrefillKVResult:
    """All arithmetic boundaries and the stage-local committed window.

    The retained projection and norm weight reconstruct every boundary after
    projection. Conditioning and projection resources are omitted, so public
    construction cannot authenticate projection arithmetic or provenance.
    """

    numeric_profile: str
    stage_id: int
    projection_bf16_codes: BF16Batch
    normalized_bf16_codes: BF16Batch
    norm_weight_bf16_codes: BF16Vector
    mean_square_binary32_codes: tuple[int, ...]
    inverse_rms_binary32_codes: tuple[int, ...]
    rotated_bf16_codes: BF16Batch
    qdq_e4m3fn_codes: U8Batch
    qdq_scale_e8m0_codes: U8Batch
    committed_kv_bf16_codes: BF16Batch
    activation_saturated_block_count: int
    projection_saturated_output_count: int
    normalization_saturated_output_count: int
    window_write: KVWindowWriteResult
    counters: DSparkPrefillKVCounters

    def __post_init__(self) -> None:
        _validate_result(self)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise DSparkPrefillKVReferenceError(
            f"{label} must be an exact list or tuple"
        )
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise DSparkPrefillKVReferenceError(
            f"{label} must be a deeply immutable exact tuple"
        )
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DSparkPrefillKVReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise DSparkPrefillKVReferenceError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise DSparkPrefillKVReferenceError(f"{label} must be finite BF16")
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
        raise DSparkPrefillKVReferenceError(
            f"{label} must contain exactly {width} values"
        )
    return tuple(
        _finite_bf16(code, f"{label}[{column}]")
        for column, code in enumerate(raw)
    )


def _freeze_batch(
    value: object,
    *,
    label: str,
    width: int,
    exact_tuple: bool = False,
    batch_count: int | None = None,
    sequence_length: int | None = None,
) -> tuple[BF16Batch, int, int]:
    batches = _exact_tuple(value, label) if exact_tuple else _sequence(value, label)
    if batch_count is None:
        batch_count = len(batches)
        if not 1 <= batch_count <= MAX_BATCH_SIZE:
            raise DSparkPrefillKVReferenceError(
                f"{label} batch extent must be in [1, {MAX_BATCH_SIZE}]"
            )
    elif len(batches) != batch_count:
        raise DSparkPrefillKVReferenceError(f"{label} batch extent differs")
    frozen_batches: list[BF16Sequence] = []
    for batch_index, raw_sequence in enumerate(batches):
        sequence = (
            _exact_tuple(raw_sequence, f"{label}[{batch_index}]")
            if exact_tuple
            else _sequence(raw_sequence, f"{label}[{batch_index}]")
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if not 1 <= sequence_length <= MAX_PREFILL_SEQUENCE:
                raise DSparkPrefillKVReferenceError(
                    f"{label} sequence extent is outside the pinned RoPE table"
                )
        elif len(sequence) != sequence_length:
            raise DSparkPrefillKVReferenceError(
                f"{label} must be rectangular on the sequence axis"
            )
        frozen_batches.append(
            tuple(
                _freeze_vector(
                    row,
                    label=f"{label}[{batch_index}][{position}]",
                    width=width,
                    exact_tuple=exact_tuple,
                )
                for position, row in enumerate(sequence)
            )
        )
    assert sequence_length is not None
    return tuple(frozen_batches), batch_count, sequence_length


def _resource_bytes(
    value: object,
    *,
    label: str,
    size: int,
    forbidden: tuple[int, ...],
) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise DSparkPrefillKVReferenceError(
            f"{label} must be immutable bytes of length {size}"
        )
    for code in forbidden:
        if code in value:
            raise DSparkPrefillKVReferenceError(
                f"{label} contains forbidden encoding 0x{code:02x}"
            )
    return value


def _flatten(batch: BF16Batch) -> tuple[BF16Vector, ...]:
    return tuple(row for sequence in batch for row in sequence)


def _reshape(
    rows: tuple[tuple[int, ...], ...],
    *,
    batch_count: int,
    sequence_length: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    return tuple(
        tuple(
            rows[batch_index * sequence_length + position]
            for position in range(sequence_length)
        )
        for batch_index in range(batch_count)
    )


def _activation_saturations(rows: tuple[BF16Vector, ...]) -> int:
    count = 0
    try:
        for row in rows:
            for block in range(REDUCTION_BLOCKS):
                start = block * DENSE_BLOCK_SIZE
                count += int(
                    quantize_bf16_activation_block(
                        row[start : start + DENSE_BLOCK_SIZE]
                    ).saturated
                )
    except NumericReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"activation quantization failed: {exc}"
        ) from exc
    return count


def _project(
    rows: tuple[BF16Vector, ...],
    weights: bytes,
    scales: bytes,
) -> DenseFP8LinearResult:
    if all(code & 0x7FFF == 0 for row in rows for code in row):
        return DenseFP8LinearResult(0, 0, tuple((0,) * KV_WIDTH for _ in rows))
    zero_row = bytes(INPUT_WIDTH)
    nonzero_rows = tuple(
        row
        for row in range(KV_WIDTH)
        if weights[row * INPUT_WIDTH : (row + 1) * INPUT_WIDTH] != zero_row
    )
    if not nonzero_rows:
        return DenseFP8LinearResult(
            _activation_saturations(rows),
            0,
            tuple((0,) * KV_WIDTH for _ in rows),
        )
    weight_view = memoryview(weights)
    scale_view = memoryview(scales)
    selected_weights = tuple(
        weight_view[row * INPUT_WIDTH : (row + 1) * INPUT_WIDTH]
        for row in nonzero_rows
    )
    scale_rows = tuple(
        scale_view[tile * REDUCTION_BLOCKS : (tile + 1) * REDUCTION_BLOCKS]
        for tile in range(OUTPUT_SCALE_TILES)
    )
    try:
        selected = dense_fp8_linear_selected_rows_bf16(
            rows,
            selected_weights,
            scale_rows,
            output_row_indices=nonzero_rows,
            declared_output_count=KV_WIDTH,
        )
    except MatrixReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"DSpark main-KV projection failed: {exc}"
        ) from exc
    expanded: list[BF16Vector] = []
    for values in selected.values:
        row = [0] * KV_WIDTH
        for logical_row, code in zip(nonzero_rows, values, strict=True):
            row[logical_row] = code
        expanded.append(tuple(row))
    return DenseFP8LinearResult(
        selected.activation_saturated_block_count,
        selected.output_saturated_element_count,
        tuple(expanded),
    )


def _apply_qdq(
    rotated: BF16Batch,
    *,
    batch_count: int,
    sequence_length: int,
) -> tuple[BF16Batch, U8Batch, U8Batch]:
    rows = _flatten(rotated)
    prefixes = tuple(row[:QDQ_WIDTH] for row in rows)
    try:
        qdq = fp8_qdq_bf16(prefixes, block_size=FP8_QDQ_BLOCK_SIZE)
    except QuantizationReferenceError as exc:
        raise DSparkPrefillKVReferenceError(f"DSpark KV QDQ failed: {exc}") from exc
    committed_rows = tuple(
        qdq.values[index] + rows[index][QDQ_WIDTH:] for index in range(len(rows))
    )
    return (
        _reshape(
            committed_rows,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
        _reshape(
            qdq.e4m3fn_codes,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
        _reshape(
            qdq.scale_codes,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
    )


def _window_input(committed: BF16Batch) -> tuple[tuple[tuple[BF16Vector, ...], ...], ...]:
    return tuple(
        tuple((row,) for row in sequence)
        for sequence in committed
    )


def _validate_official_window_state(value: object) -> KVWindowState:
    try:
        state = kv_window_state_bf16(value)
    except (TypeError, ValueError) as exc:
        raise DSparkPrefillKVReferenceError(
            f"DSpark stage window state is invalid: {exc}"
        ) from exc
    if len(state.bf16_codes[0]) != WINDOW_SIZE:
        raise DSparkPrefillKVReferenceError(
            f"DSpark stage window must contain exactly {WINDOW_SIZE} slots"
        )
    if len(state.bf16_codes[0][0]) != 1 or len(state.bf16_codes[0][0][0]) != (
        KV_WIDTH
    ):
        raise DSparkPrefillKVReferenceError(
            "DSpark stage window must have official [H=1,V=512] rows"
        )
    return state


def _balanced_add_count(width: int) -> int:
    additions = 0
    level = width
    while level > 1:
        if level & 1:
            level += 1
        additions += level // 2
        level //= 2
    return additions


def _counter_values(
    *,
    stage_id: int,
    batch_count: int,
    sequence_length: int,
    activation_saturations: int,
    projection_saturations: int,
    rms_saturations: int,
    window_write: KVWindowWriteResult,
) -> dict[str, int]:
    token_count = batch_count * sequence_length
    projection_outputs = token_count * KV_WIDTH
    block_dots = projection_outputs * REDUCTION_BLOCKS
    window = window_write.counters
    return {
        "stage_id": stage_id,
        "batch_count": batch_count,
        "sequence_length": sequence_length,
        "token_count": token_count,
        "state_batch_capacity": window.state_batch_capacity,
        "previous_active_batch_count": window.previous_active_batch_count,
        "removed_batch_count": window.removed_batch_count,
        "conditioning_bf16_values": token_count * INPUT_WIDTH,
        "projection_weight_e4m3_values": WEIGHT_BYTES,
        "projection_scale_e8m0_values": SCALE_BYTES,
        "activation_blocks_quantized": token_count * REDUCTION_BLOCKS,
        "activation_values_quantized": token_count * INPUT_WIDTH,
        "activation_saturated_blocks": activation_saturations,
        "projection_block_dots": block_dots,
        "projection_exact_product_accumulates": block_dots * DENSE_BLOCK_SIZE,
        "projection_cross_block_reduction_adds": (
            projection_outputs * _balanced_add_count(REDUCTION_BLOCKS)
        ),
        "projection_bf16_conversions": projection_outputs,
        "projection_saturated_outputs": projection_saturations,
        "rms_weight_bf16_values": KV_WIDTH,
        "rms_square_multiplies": projection_outputs,
        "rms_reduction_adds": token_count * (KV_WIDTH - 1),
        "rms_divides": token_count,
        "rms_epsilon_adds": token_count,
        "rms_rsqrt_evaluations": token_count,
        "rms_pointwise_multiplies": 2 * projection_outputs,
        "rms_bf16_conversions": projection_outputs,
        "rms_saturated_outputs": rms_saturations,
        "rope_prefix_bf16_values_preserved": token_count * QDQ_WIDTH,
        "rope_rotated_bf16_values": token_count * ROPE_WIDTH,
        "rope_phasor_binary32_values_read": token_count * ROPE_WIDTH,
        "rope_binary32_multiplications": token_count * ROPE_WIDTH * 2,
        "rope_binary32_additions_or_subtractions": token_count * ROPE_WIDTH,
        "rope_bf16_conversions": token_count * ROPE_WIDTH,
        "qdq_input_bf16_values": token_count * QDQ_WIDTH,
        "qdq_blocks_quantized": token_count * FP8_QDQ_BLOCKS,
        "qdq_e4m3_values": token_count * QDQ_WIDTH,
        "qdq_scale_e8m0_values": token_count * FP8_QDQ_BLOCKS,
        "qdq_output_bf16_values": token_count * QDQ_WIDTH,
        "kv_rows_produced": token_count,
        "window_source_rows_read": window.logical_source_rows_read,
        "window_source_bf16_values_read": window.logical_source_bf16_values_read,
        "window_state_rows_written": window.logical_state_rows_written,
        "window_state_bf16_values_written": window.logical_state_bf16_values_written,
        "window_state_write_logical_bytes": window.logical_state_write_bytes,
        "window_state_rows_preserved": window.state_rows_preserved,
        "window_metadata_fields_read": window.logical_metadata_fields_read,
        "window_metadata_fields_written": window.logical_metadata_fields_written,
        "transaction_commits": 1,
    }


def _validate_counters(value: object) -> DSparkPrefillKVCounters:
    if type(value) is not DSparkPrefillKVCounters:
        raise DSparkPrefillKVReferenceError(
            "counters must be an exact DSparkPrefillKVCounters record"
        )
    stage = _integer(value.stage_id, "counters.stage_id", minimum=0, maximum=2)
    batch_count = _integer(
        value.batch_count,
        "counters.batch_count",
        minimum=1,
        maximum=MAX_BATCH_SIZE,
    )
    sequence_length = _integer(
        value.sequence_length,
        "counters.sequence_length",
        minimum=1,
        maximum=MAX_PREFILL_SEQUENCE,
    )
    token_count = batch_count * sequence_length
    state_capacity = _integer(
        value.state_batch_capacity,
        "counters.state_batch_capacity",
        minimum=1,
        maximum=MAX_BATCH_SIZE,
    )
    if batch_count > state_capacity:
        raise DSparkPrefillKVReferenceError(
            "counter batch count exceeds state capacity"
        )
    previous_active = _integer(
        value.previous_active_batch_count,
        "counters.previous_active_batch_count",
        minimum=0,
        maximum=state_capacity,
    )
    removed_count = _integer(
        value.removed_batch_count,
        "counters.removed_batch_count",
        minimum=0,
        maximum=state_capacity,
    )
    if removed_count != max(0, previous_active - batch_count):
        raise DSparkPrefillKVReferenceError(
            "counter removed batch count does not reconcile"
        )
    activation_saturations = _integer(
        value.activation_saturated_blocks,
        "counters.activation_saturated_blocks",
        minimum=0,
        maximum=token_count * REDUCTION_BLOCKS,
    )
    projection_saturations = _integer(
        value.projection_saturated_outputs,
        "counters.projection_saturated_outputs",
        minimum=0,
        maximum=token_count * KV_WIDTH,
    )
    rms_saturations = _integer(
        value.rms_saturated_outputs,
        "counters.rms_saturated_outputs",
        minimum=0,
        maximum=token_count * KV_WIDTH,
    )
    invariant = {
        name: expected
        for name, expected in _counter_values_without_window(
            stage_id=stage,
            batch_count=batch_count,
            sequence_length=sequence_length,
            state_batch_capacity=state_capacity,
            previous_active_batch_count=previous_active,
            removed_batch_count=removed_count,
            activation_saturations=activation_saturations,
            projection_saturations=projection_saturations,
            rms_saturations=rms_saturations,
        ).items()
    }
    for name, expected in invariant.items():
        observed = getattr(value, name)
        if type(observed) is not int or observed != expected:
            raise DSparkPrefillKVReferenceError(
                f"counters.{name} does not reconcile to DSpark prefill dimensions"
            )
    return value


def _counter_values_without_window(
    *,
    stage_id: int,
    batch_count: int,
    sequence_length: int,
    state_batch_capacity: int,
    previous_active_batch_count: int,
    removed_batch_count: int,
    activation_saturations: int,
    projection_saturations: int,
    rms_saturations: int,
) -> dict[str, int]:
    # Use a dimension-only spelling so public counter construction can reject
    # forgeries before a window write record is available.
    token_count = batch_count * sequence_length
    projection_outputs = token_count * KV_WIDTH
    block_dots = projection_outputs * REDUCTION_BLOCKS
    written_rows = batch_count * min(sequence_length, WINDOW_SIZE)
    changed_lanes = max(previous_active_batch_count, batch_count)
    metadata_reads = (
        2 * state_batch_capacity
        + previous_active_batch_count
        + changed_lanes
    )
    metadata_writes = (
        2 * batch_count + 2 * changed_lanes + removed_batch_count
    )
    return {
        "stage_id": stage_id,
        "batch_count": batch_count,
        "sequence_length": sequence_length,
        "token_count": token_count,
        "state_batch_capacity": state_batch_capacity,
        "previous_active_batch_count": previous_active_batch_count,
        "removed_batch_count": removed_batch_count,
        "conditioning_bf16_values": token_count * INPUT_WIDTH,
        "projection_weight_e4m3_values": WEIGHT_BYTES,
        "projection_scale_e8m0_values": SCALE_BYTES,
        "activation_blocks_quantized": token_count * REDUCTION_BLOCKS,
        "activation_values_quantized": token_count * INPUT_WIDTH,
        "activation_saturated_blocks": activation_saturations,
        "projection_block_dots": block_dots,
        "projection_exact_product_accumulates": block_dots * DENSE_BLOCK_SIZE,
        "projection_cross_block_reduction_adds": (
            projection_outputs * _balanced_add_count(REDUCTION_BLOCKS)
        ),
        "projection_bf16_conversions": projection_outputs,
        "projection_saturated_outputs": projection_saturations,
        "rms_weight_bf16_values": KV_WIDTH,
        "rms_square_multiplies": projection_outputs,
        "rms_reduction_adds": token_count * (KV_WIDTH - 1),
        "rms_divides": token_count,
        "rms_epsilon_adds": token_count,
        "rms_rsqrt_evaluations": token_count,
        "rms_pointwise_multiplies": 2 * projection_outputs,
        "rms_bf16_conversions": projection_outputs,
        "rms_saturated_outputs": rms_saturations,
        "rope_prefix_bf16_values_preserved": token_count * QDQ_WIDTH,
        "rope_rotated_bf16_values": token_count * ROPE_WIDTH,
        "rope_phasor_binary32_values_read": token_count * ROPE_WIDTH,
        "rope_binary32_multiplications": token_count * ROPE_WIDTH * 2,
        "rope_binary32_additions_or_subtractions": token_count * ROPE_WIDTH,
        "rope_bf16_conversions": token_count * ROPE_WIDTH,
        "qdq_input_bf16_values": token_count * QDQ_WIDTH,
        "qdq_blocks_quantized": token_count * FP8_QDQ_BLOCKS,
        "qdq_e4m3_values": token_count * QDQ_WIDTH,
        "qdq_scale_e8m0_values": token_count * FP8_QDQ_BLOCKS,
        "qdq_output_bf16_values": token_count * QDQ_WIDTH,
        "kv_rows_produced": token_count,
        "window_source_rows_read": written_rows,
        "window_source_bf16_values_read": written_rows * KV_WIDTH,
        "window_state_rows_written": written_rows,
        "window_state_bf16_values_written": written_rows * KV_WIDTH,
        "window_state_write_logical_bytes": written_rows * KV_WIDTH * 2,
        "window_state_rows_preserved": (
            state_batch_capacity * WINDOW_SIZE - written_rows
        ),
        "window_metadata_fields_read": metadata_reads,
        "window_metadata_fields_written": metadata_writes,
        "transaction_commits": 1,
    }


def _freeze_u8_batch(
    value: object,
    *,
    label: str,
    width: int,
    batch_count: int,
    sequence_length: int,
) -> U8Batch:
    batches = _exact_tuple(value, label)
    if len(batches) != batch_count:
        raise DSparkPrefillKVReferenceError(f"{label} batch extent differs")
    output = []
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _exact_tuple(raw_sequence, f"{label}[{batch_index}]")
        if len(sequence) != sequence_length:
            raise DSparkPrefillKVReferenceError(f"{label} sequence extent differs")
        rows = []
        for position, raw_row in enumerate(sequence):
            row = _exact_tuple(raw_row, f"{label}[{batch_index}][{position}]")
            if len(row) != width:
                raise DSparkPrefillKVReferenceError(f"{label} row width differs")
            rows.append(
                tuple(
                    _integer(
                        code,
                        f"{label}[{batch_index}][{position}][{column}]",
                        minimum=0,
                        maximum=254 if width == FP8_QDQ_BLOCKS else 255,
                    )
                    for column, code in enumerate(row)
                )
            )
        output.append(tuple(rows))
    return tuple(output)


def _validate_result(value: object) -> DSparkPrefillKVResult:
    if type(value) is not DSparkPrefillKVResult:
        raise DSparkPrefillKVReferenceError(
            "result must be an exact DSparkPrefillKVResult record"
        )
    if type(value.numeric_profile) is not str or value.numeric_profile != (
        NUMERIC_PROFILE
    ):
        raise DSparkPrefillKVReferenceError("result numeric profile differs")
    stage = _integer(value.stage_id, "result.stage_id", minimum=0, maximum=2)
    if type(value.counters) is not DSparkPrefillKVCounters:
        raise DSparkPrefillKVReferenceError("result counters must be exact")
    counters = _validate_counters(value.counters)
    if counters.stage_id != stage:
        raise DSparkPrefillKVReferenceError("result stage and counters differ")
    batch_count = counters.batch_count
    sequence_length = counters.sequence_length
    projection, _, _ = _freeze_batch(
        value.projection_bf16_codes,
        label="result.projection_bf16_codes",
        width=KV_WIDTH,
        exact_tuple=True,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    normalized, _, _ = _freeze_batch(
        value.normalized_bf16_codes,
        label="result.normalized_bf16_codes",
        width=KV_WIDTH,
        exact_tuple=True,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    rotated, _, _ = _freeze_batch(
        value.rotated_bf16_codes,
        label="result.rotated_bf16_codes",
        width=KV_WIDTH,
        exact_tuple=True,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    committed, _, _ = _freeze_batch(
        value.committed_kv_bf16_codes,
        label="result.committed_kv_bf16_codes",
        width=KV_WIDTH,
        exact_tuple=True,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    norm_weight = _freeze_vector(
        value.norm_weight_bf16_codes,
        label="result.norm_weight_bf16_codes",
        width=KV_WIDTH,
        exact_tuple=True,
    )
    means = _exact_tuple(
        value.mean_square_binary32_codes,
        "result.mean_square_binary32_codes",
    )
    inverses = _exact_tuple(
        value.inverse_rms_binary32_codes,
        "result.inverse_rms_binary32_codes",
    )
    token_count = counters.token_count
    if len(means) != token_count or len(inverses) != token_count:
        raise DSparkPrefillKVReferenceError("result RMS diagnostic extent differs")
    for label, codes in (("mean", means), ("inverse", inverses)):
        for index, code in enumerate(codes):
            if type(code) is not int or not 0 <= code < 1 << 32:
                raise DSparkPrefillKVReferenceError(
                    f"result RMS {label}[{index}] must be a binary32 code"
                )
            if code & 0x7F800000 == 0x7F800000:
                raise DSparkPrefillKVReferenceError(
                    f"result RMS {label}[{index}] must be finite"
                )
    activation_saturations = _integer(
        value.activation_saturated_block_count,
        "result.activation_saturated_block_count",
        minimum=0,
        maximum=token_count * REDUCTION_BLOCKS,
    )
    projection_saturations = _integer(
        value.projection_saturated_output_count,
        "result.projection_saturated_output_count",
        minimum=0,
        maximum=token_count * KV_WIDTH,
    )
    norm_saturations = _integer(
        value.normalization_saturated_output_count,
        "result.normalization_saturated_output_count",
        minimum=0,
        maximum=token_count * KV_WIDTH,
    )
    if (
        activation_saturations != counters.activation_saturated_blocks
        or projection_saturations != counters.projection_saturated_outputs
        or norm_saturations != counters.rms_saturated_outputs
    ):
        raise DSparkPrefillKVReferenceError(
            "result saturation counts and counters differ"
        )
    qdq_codes = _freeze_u8_batch(
        value.qdq_e4m3fn_codes,
        label="result.qdq_e4m3fn_codes",
        width=QDQ_WIDTH,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    qdq_scales = _freeze_u8_batch(
        value.qdq_scale_e8m0_codes,
        label="result.qdq_scale_e8m0_codes",
        width=FP8_QDQ_BLOCKS,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )

    try:
        expected_norm = rms_norm_bf16(_flatten(projection), norm_weight)
    except NormalizationReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"result RMS reconstruction failed: {exc}"
        ) from exc
    if (
        normalized
        != _reshape(
            expected_norm.output_codes,
            batch_count=batch_count,
            sequence_length=sequence_length,
        )
        or tuple(means) != expected_norm.mean_square_codes
        or tuple(inverses) != expected_norm.inverse_rms_codes
        or norm_saturations != expected_norm.output_saturation_count
    ):
        raise DSparkPrefillKVReferenceError(
            "result weighted-RMS boundary does not reconcile"
        )
    try:
        expected_rope = apply_rotary_bf16_result(
            normalized,
            0,
            profile=BASE_ROPE_PROFILE,
        )
    except RopeReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"result RoPE reconstruction failed: {exc}"
        ) from exc
    if rotated != expected_rope.output_bf16_codes:
        raise DSparkPrefillKVReferenceError("result RoPE boundary does not reconcile")
    expected_committed, expected_qdq, expected_scales = _apply_qdq(
        rotated,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    if (
        committed != expected_committed
        or qdq_codes != expected_qdq
        or qdq_scales != expected_scales
    ):
        raise DSparkPrefillKVReferenceError("result QDQ boundary does not reconcile")
    if type(value.window_write) is not KVWindowWriteResult:
        raise DSparkPrefillKVReferenceError("result window write must be exact")
    window_write = value.window_write
    if (
        window_write.mode != "prefill"
        or window_write.start_pos != 0
        or window_write.input_bf16_codes != _window_input(committed)
    ):
        raise DSparkPrefillKVReferenceError(
            "result window write does not consume committed DSpark KV"
        )
    expected_counter_values = _counter_values(
        stage_id=stage,
        batch_count=batch_count,
        sequence_length=sequence_length,
        activation_saturations=activation_saturations,
        projection_saturations=projection_saturations,
        rms_saturations=norm_saturations,
        window_write=window_write,
    )
    for name, expected in expected_counter_values.items():
        if getattr(counters, name) != expected:
            raise DSparkPrefillKVReferenceError(
                f"result counters.{name} differs from retained boundaries"
            )
    return value


def dspark_prefill_kv_bf16(
    conditioning_bf16_codes: object,
    projection_weight_e4m3_bytes: object,
    projection_scale_e8m0_bytes: object,
    norm_weight_bf16_codes: object,
    window_state: KVWindowState,
    *,
    stage_id: int,
    active_session_ids: object,
    expected_window_state_versions: object,
    start_pos: int = 0,
) -> DSparkPrefillKVResult:
    """Execute one stage's complete prefill-only main-KV state transaction."""

    stage = _integer(stage_id, "stage_id", minimum=0, maximum=STAGE_COUNT - 1)
    start = _integer(start_pos, "start_pos", minimum=0, maximum=MAX_PREFILL_SEQUENCE - 1)
    if start != 0:
        raise DSparkPrefillKVReferenceError(
            "DSPARK_PREFILL_KV is defined only for start_pos equal to zero"
        )
    conditioning, batch_count, sequence_length = _freeze_batch(
        conditioning_bf16_codes,
        label="conditioning_bf16_codes",
        width=INPUT_WIDTH,
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
        width=KV_WIDTH,
    )
    state = _validate_official_window_state(window_state)

    projection = _project(_flatten(conditioning), weights, scales)
    try:
        normalized = rms_norm_bf16(projection.values, norm_weight)
    except NormalizationReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"DSpark main-KV normalization failed: {exc}"
        ) from exc
    normalized_batch = _reshape(
        normalized.output_codes,
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    try:
        rotated_result = apply_rotary_bf16_result(
            normalized_batch,
            0,
            profile=BASE_ROPE_PROFILE,
        )
    except RopeReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"DSpark main-KV RoPE failed: {exc}"
        ) from exc
    rotated = rotated_result.output_bf16_codes
    assert isinstance(rotated, tuple)
    committed, qdq_codes, qdq_scales = _apply_qdq(
        rotated,  # type: ignore[arg-type]
        batch_count=batch_count,
        sequence_length=sequence_length,
    )
    try:
        window_write = kv_window_write_bf16(
            state,
            _window_input(committed),
            active_session_ids=active_session_ids,
            expected_state_versions=expected_window_state_versions,
            start_pos=0,
        )
    except KVWindowReferenceError as exc:
        raise DSparkPrefillKVReferenceError(
            f"DSpark main-KV window commit failed: {exc}"
        ) from exc
    counters = DSparkPrefillKVCounters(
        **_counter_values(
            stage_id=stage,
            batch_count=batch_count,
            sequence_length=sequence_length,
            activation_saturations=projection.activation_saturated_block_count,
            projection_saturations=projection.output_saturated_element_count,
            rms_saturations=normalized.output_saturation_count,
            window_write=window_write,
        )
    )
    return DSparkPrefillKVResult(
        numeric_profile=NUMERIC_PROFILE,
        stage_id=stage,
        projection_bf16_codes=_reshape(
            projection.values,
            batch_count=batch_count,
            sequence_length=sequence_length,
        ),
        normalized_bf16_codes=normalized_batch,
        norm_weight_bf16_codes=norm_weight,
        mean_square_binary32_codes=normalized.mean_square_codes,
        inverse_rms_binary32_codes=normalized.inverse_rms_codes,
        rotated_bf16_codes=rotated,  # type: ignore[arg-type]
        qdq_e4m3fn_codes=qdq_codes,
        qdq_scale_e8m0_codes=qdq_scales,
        committed_kv_bf16_codes=committed,
        activation_saturated_block_count=(
            projection.activation_saturated_block_count
        ),
        projection_saturated_output_count=projection.output_saturated_element_count,
        normalization_saturated_output_count=normalized.output_saturation_count,
        window_write=window_write,
        counters=counters,
    )


def official_resource_hashes(
    projection_weight_e4m3_bytes: object,
    projection_scale_e8m0_bytes: object,
    norm_weight_bf16_codes: object,
) -> dict[str, str]:
    """Validate one stage resource set and return content identities."""

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
    norm = _freeze_vector(
        norm_weight_bf16_codes,
        label="norm_weight_bf16_codes",
        width=KV_WIDTH,
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
    "EXCLUDED_CLAIMS",
    "FP8_QDQ_BLOCKS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "INPUT_WIDTH",
    "KV_WIDTH",
    "MAX_PREFILL_SEQUENCE",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "NORM_WEIGHT_BYTES",
    "NUMERIC_PROFILE",
    "OFFICIAL_NORM_WEIGHT_SHA256",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_SCALE_SHA256",
    "OFFICIAL_WEIGHT_SHA256",
    "QDQ_WIDTH",
    "REDUCTION_BLOCKS",
    "ROPE_WIDTH",
    "SCALE_BYTES",
    "SOURCE_EXPRESSIONS",
    "STAGE_COUNT",
    "WEIGHT_BYTES",
    "WINDOW_SIZE",
    "DSparkPrefillKVCounters",
    "DSparkPrefillKVReferenceError",
    "DSparkPrefillKVResult",
    "dspark_prefill_kv_bf16",
    "official_resource_hashes",
]
