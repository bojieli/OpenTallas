"""Deterministic DeepSeek V4 shared vocabulary-head semantics.

The pinned ``ParallelHead`` stores one untied BF16 vocabulary matrix, widens
that matrix and the BF16 hidden input to binary32, evaluates a bias-free linear
projection, and concatenates contiguous tensor-parallel vocabulary shards in
rank order.  Main-model execution first selects only the final source position;
DSpark calls the same head with ``full_logits=True`` and projects all five draft
positions.

The released source leaves CUDA GEMM association backend-dependent.  The target
profile freezes one exact BF16 product followed by one binary32 RNE fused
product-add at each increasing hidden index.  The final accumulator is the
binary32 logit; there is no BF16 output conversion.

``lm_head_bf16`` is the complete operator and accepts rank-ordered weight
shards.  ``lm_head_selected_bf16`` evaluates explicit global vocabulary rows
while retaining the declared full vocabulary and tensor-parallel mapping.  The
latter is an evidence slice, not complete execution.  Neither function claims
checkpoint-derived hidden state, a framework GEMM differential, a physical
collective, compiler/service/RTL execution, or performance.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from fractions import Fraction
import hashlib
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_ordered_dot,
    decode_bf16,
    decode_binary32,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
CONVERT_SOURCE_PATH = "inference/convert.py"
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
GENERATE_SOURCE_PATH = "inference/generate.py"
GENERATE_SOURCE_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
CHECKPOINT_INDEX_PATH = "model.safetensors.index.json"
CHECKPOINT_INDEX_SHA256 = (
    "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
)
CHECKPOINT_LOCK_ID = "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
LM_HEAD_NUMERIC_PROFILE = "opentallas.deepseek_v4_lm_head_binary32.v1"

OFFICIAL_HIDDEN_WIDTH = 4096
OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MAIN_SITE_COUNT = 1
OFFICIAL_DSPARK_SITE_COUNT = 1
OFFICIAL_SITE_COUNT = OFFICIAL_MAIN_SITE_COUNT + OFFICIAL_DSPARK_SITE_COUNT
OFFICIAL_DSPARK_BLOCK_SIZE = 5
OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES = (1, 2, 4, 8)
OFFICIAL_MP4_PARTITION_ROWS = OFFICIAL_VOCABULARY_SIZE // 4
OFFICIAL_WEIGHT_SHAPE = (OFFICIAL_VOCABULARY_SIZE, OFFICIAL_HIDDEN_WIDTH)
OFFICIAL_WEIGHT_BYTES = OFFICIAL_VOCABULARY_SIZE * OFFICIAL_HIDDEN_WIDTH * 2
OFFICIAL_WEIGHT_SHA256 = (
    "029e3c5293b29cc426e21d87795e15efa4d363f27b2bc4a9e3aef7d79f047919"
)
OFFICIAL_MP4_WEIGHT_SHA256 = (
    "517371776bf297a7c1fba6317c04649c8080841cf0107d3395b23559b8540ee1",
    "a0e8f1115ad0ce49a7ec27af80017abe5beff4ac0fde26cfaf1ff6fbb7d217ba",
    "ea93b80dcc8940969e20c481de389f85709ea9b015a02a28540719e77c7cd494",
    "abbeab307dd4d6cf87f0d38106032743af343954a9671deec6960a0384e089c4",
)
OFFICIAL_SELECTED_ROW_SHA256 = (
    (0, "162f09c5797bcba1555a099a5de9da5761b0fc34d04022dbeef8eb50f406757e"),
    (32_319, "e1a8c0455e9fce11d63f5df882b85df0f5fe4bc157676f4f238d0dc03e4bdc96"),
    (32_320, "aefdc3bbc727717d741b9c57e9b6b3483e409c7ceef0c28599ea982e91ebf7a3"),
    (64_639, "679fcaf5960da3188e7d1aa49ee01387636b195b9c8eee0b32892bf55dcb3295"),
    (64_640, "d6ecd4976ad1af6c2a8ebefd3f8b48f1055372be10b048582524c3f7256c7672"),
    (96_959, "c1e117f1bc5c3c224c108c1f5945c1420744521a08a35669f05994048111f28c"),
    (96_960, "24c00c267308a4c26f6262fabe82e6b2449e17343b7a3dbb53275e5387dedc41"),
    (129_279, "e91cbbddc23effa754f3c3a4635defe39e803ed3b550cb0ff3a45df135a9ac0a"),
)

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
BF16_MAX_ENCODING = (1 << 16) - 1
BINARY32_MAX_ENCODING = (1 << 32) - 1

SOURCE_EXPRESSIONS = (
    "self.part_vocab_size = (vocab_size // world_size)",
    "self.weight = nn.Parameter(torch.empty(self.part_vocab_size, self.dim, dtype=torch.float32))",
    "if not full_logits:",
    "x = x[:, -1]",
    "logits = F.linear(x.float(), self.weight)",
    "dist.all_gather(all_logits, logits)",
    "logits = torch.cat(all_logits, dim=-1)",
    "logits = self.head(self.norm(x), full_logits=True)",
)
CONVERT_SOURCE_EXPRESSIONS = (
    '"head": ("head", 0),',
    "shard_size = param.size(dim) // mp",
    "new_param = param.narrow(dim, i * shard_size, shard_size).contiguous()",
)
CONFIG_EXPECTED_FIELDS = (
    ("dim", OFFICIAL_HIDDEN_WIDTH),
    ("vocab_size", OFFICIAL_VOCABULARY_SIZE),
    ("dspark_block_size", OFFICIAL_DSPARK_BLOCK_SIZE),
)
EXCLUDED_CLAIMS = (
    "final_rms_normalization",
    "checkpoint_derived_hidden_state",
    "pytorch_cuda_gemm_bit_equivalence",
    "physical_tensor_parallel_collective",
    "compiler_service_or_rtl_execution",
    "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
    "sampling_generation_or_end_to_end_model_evidence",
)


BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16ValueVector: TypeAlias = tuple[Fraction, ...]
BF16ValueMatrix: TypeAlias = tuple[BF16ValueVector, ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32MainOutput: TypeAlias = tuple[Binary32Vector, ...]
Binary32FullOutput: TypeAlias = tuple[tuple[Binary32Vector, ...], ...]
Binary32Output: TypeAlias = Binary32MainOutput | Binary32FullOutput


class LMHeadReferenceError(ValueError):
    """Raised when vocabulary-head input or target arithmetic poisons."""


@dataclass(frozen=True, slots=True)
class LMHeadCounters:
    """Exact semantic shape, topology, and arithmetic counts."""

    batch_count: int
    source_sequence_length: int
    evaluated_positions_per_batch: int
    full_logits: bool
    hidden_width: int
    declared_vocabulary_size: int
    evaluated_vocabulary_rows: int
    complete_output: bool
    tensor_parallel_world_size: int
    partition_vocabulary_rows: int
    declared_tensor_parallel_shards: int
    evaluated_tensor_parallel_shards: int
    source_hidden_rows_validated: int
    selected_hidden_rows_read: int
    source_hidden_bf16_values_validated: int
    selected_hidden_bf16_values_read: int
    selected_weight_bf16_values_read: int
    input_binary32_widens: int
    weight_binary32_widens: int
    exact_product_accumulates: int
    binary32_accumulation_roundings: int
    binary32_logits_written: int
    logical_gathered_binary32_values: int
    source_rows_excluded_by_last_token_selection: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class LMHeadResult:
    """Immutable exact logits, topology map, source hashes, and counters.

    The record retains hashes rather than the potentially 1.06 GB selected
    weight payload.  It detects mutation of its output and binds the evaluated
    sources, but public construction cannot by itself authenticate checkpoint
    provenance or reconstruct the dot products.
    """

    numeric_profile: str
    full_logits: bool
    tensor_parallel_world_size: int
    declared_vocabulary_size: int
    selected_token_ids: tuple[int, ...]
    selected_partition_ranks: tuple[int, ...]
    selected_local_row_indices: tuple[int, ...]
    complete_output: bool
    official_shape_profile: bool
    source_sequence_length: int
    selected_hidden_bf16_sha256: str
    selected_weight_bf16_sha256: str
    logits_binary32_sha256: str
    logits_binary32_codes: Binary32Output
    counters: LMHeadCounters

    def __post_init__(self) -> None:
        _validate_result(self)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise LMHeadReferenceError(f"{label} must be an exact list or tuple")
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise LMHeadReferenceError(f"{label} must be a deeply immutable exact tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise LMHeadReferenceError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _world_size(value: object) -> int:
    if type(value) is not int or value not in OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES:
        raise LMHeadReferenceError(
            "tensor_parallel_world_size must be exactly 1, 2, 4, or 8"
        )
    return value


def _finite_bf16(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise LMHeadReferenceError(f"{label} must be an exact 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise LMHeadReferenceError(f"{label} must be finite BF16")
    return value, decoded.value


def _finite_binary32(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BINARY32_MAX_ENCODING:
        raise LMHeadReferenceError(
            f"{label} must be an exact 32-bit binary32 encoding"
        )
    decoded = decode_binary32(value)
    if not decoded.finite or decoded.value is None:
        raise LMHeadReferenceError(f"{label} must be finite binary32")
    return value


def _freeze_hidden(
    value: object,
    *,
    full_logits: bool,
) -> tuple[BF16Batch, BF16ValueMatrix, int, int, int]:
    raw_batches = _sequence(value, "hidden_bf16_codes")
    if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
        raise LMHeadReferenceError(
            f"hidden_bf16_codes batch extent must be in [1, {PINNED_MAX_BATCH_SIZE}]"
        )
    frozen_batches: list[BF16Sequence] = []
    selected_rows: list[BF16ValueVector] = []
    sequence_length: int | None = None
    hidden_width: int | None = None
    for batch, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"hidden_bf16_codes[{batch}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if not 1 <= sequence_length <= PINNED_MAX_POSITION:
                raise LMHeadReferenceError(
                    "hidden_bf16_codes sequence extent is outside the position bound"
                )
        elif len(sequence) != sequence_length:
            raise LMHeadReferenceError(
                "hidden_bf16_codes must be rectangular on the sequence axis"
            )
        frozen_sequence: list[BF16Vector] = []
        value_sequence: list[BF16ValueVector] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(raw_row, f"hidden_bf16_codes[{batch}][{position}]")
            if hidden_width is None:
                hidden_width = len(row)
                if not 1 <= hidden_width <= OFFICIAL_HIDDEN_WIDTH:
                    raise LMHeadReferenceError(
                        "hidden width must be in [1, 4096]"
                    )
            elif len(row) != hidden_width:
                raise LMHeadReferenceError(
                    "hidden_bf16_codes must be rectangular on the hidden axis"
                )
            frozen_row: list[int] = []
            values: list[Fraction] = []
            for column, code in enumerate(row):
                frozen_code, decoded = _finite_bf16(
                    code,
                    f"hidden_bf16_codes[{batch}][{position}][{column}]",
                )
                frozen_row.append(frozen_code)
                values.append(decoded)
            frozen_sequence.append(tuple(frozen_row))
            value_sequence.append(tuple(values))
        frozen_batches.append(tuple(frozen_sequence))
        selected_rows.extend(
            value_sequence if full_logits else (value_sequence[-1],)
        )
    assert sequence_length is not None and hidden_width is not None
    return (
        tuple(frozen_batches),
        tuple(selected_rows),
        len(frozen_batches),
        sequence_length,
        hidden_width,
    )


def _selected_token_ids(
    value: object,
    *,
    vocabulary_size: int,
) -> tuple[int, ...]:
    raw = _sequence(value, "selected_token_ids")
    selected = tuple(
        _integer(
            token_id,
            f"selected_token_ids[{index}]",
            minimum=0,
            maximum=vocabulary_size - 1,
        )
        for index, token_id in enumerate(raw)
    )
    if not selected:
        raise LMHeadReferenceError("selected_token_ids must not be empty")
    if selected != tuple(sorted(set(selected))):
        raise LMHeadReferenceError(
            "selected_token_ids must be unique and strictly increasing"
        )
    return selected


def _freeze_selected_weights(
    value: object,
    *,
    selected_count: int,
    hidden_width: int,
) -> tuple[tuple[BF16Vector, ...], BF16ValueMatrix]:
    raw_rows = _sequence(value, "selected_weight_bf16_codes")
    if len(raw_rows) != selected_count:
        raise LMHeadReferenceError(
            "selected weight row count must match selected_token_ids"
        )
    frozen_rows: list[BF16Vector] = []
    value_rows: list[BF16ValueVector] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"selected_weight_bf16_codes[{row_index}]")
        if len(row) != hidden_width:
            raise LMHeadReferenceError(
                f"selected_weight_bf16_codes[{row_index}] must have hidden width "
                f"{hidden_width}"
            )
        frozen_row: list[int] = []
        values: list[Fraction] = []
        for column, code in enumerate(row):
            frozen_code, decoded = _finite_bf16(
                code,
                f"selected_weight_bf16_codes[{row_index}][{column}]",
            )
            frozen_row.append(frozen_code)
            values.append(decoded)
        frozen_rows.append(tuple(frozen_row))
        value_rows.append(tuple(values))
    return tuple(frozen_rows), tuple(value_rows)


def _hash_bf16_rows(rows: tuple[BF16Vector, ...]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        for code in row:
            digest.update(code.to_bytes(2, "little"))
    return digest.hexdigest()


def _hash_binary32_output(value: Binary32Output, *, full_logits: bool) -> str:
    digest = hashlib.sha256()
    if full_logits:
        for sequence in value:
            for row in sequence:
                for code in row:
                    digest.update(code.to_bytes(4, "little"))
    else:
        for row in value:
            for code in row:
                digest.update(code.to_bytes(4, "little"))
    return digest.hexdigest()


def _complete_selection(selected: tuple[int, ...], vocabulary_size: int) -> bool:
    return len(selected) == vocabulary_size and all(
        token_id == index for index, token_id in enumerate(selected)
    )


def _counter_values(
    *,
    batch_count: int,
    sequence_length: int,
    evaluated_positions: int,
    full_logits: bool,
    hidden_width: int,
    vocabulary_size: int,
    evaluated_vocabulary_rows: int,
    complete_output: bool,
    world_size: int,
    evaluated_shards: int,
) -> dict[str, int | bool]:
    source_rows = batch_count * sequence_length
    selected_rows = batch_count * evaluated_positions
    outputs = selected_rows * evaluated_vocabulary_rows
    products = outputs * hidden_width
    return {
        "batch_count": batch_count,
        "source_sequence_length": sequence_length,
        "evaluated_positions_per_batch": evaluated_positions,
        "full_logits": full_logits,
        "hidden_width": hidden_width,
        "declared_vocabulary_size": vocabulary_size,
        "evaluated_vocabulary_rows": evaluated_vocabulary_rows,
        "complete_output": complete_output,
        "tensor_parallel_world_size": world_size,
        "partition_vocabulary_rows": vocabulary_size // world_size,
        "declared_tensor_parallel_shards": world_size,
        "evaluated_tensor_parallel_shards": evaluated_shards,
        "source_hidden_rows_validated": source_rows,
        "selected_hidden_rows_read": selected_rows,
        "source_hidden_bf16_values_validated": source_rows * hidden_width,
        "selected_hidden_bf16_values_read": selected_rows * hidden_width,
        "selected_weight_bf16_values_read": evaluated_vocabulary_rows
        * hidden_width,
        "input_binary32_widens": selected_rows * hidden_width,
        "weight_binary32_widens": evaluated_vocabulary_rows * hidden_width,
        "exact_product_accumulates": products,
        "binary32_accumulation_roundings": products,
        "binary32_logits_written": outputs,
        "logical_gathered_binary32_values": outputs,
        "source_rows_excluded_by_last_token_selection": (
            0 if full_logits else batch_count * (sequence_length - 1)
        ),
        "transaction_commits": 1,
    }


def _validate_counters(value: object) -> LMHeadCounters:
    if type(value) is not LMHeadCounters:
        raise LMHeadReferenceError("counters must be an exact LMHeadCounters record")
    batch_count = _integer(
        value.batch_count,
        "counters.batch_count",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    sequence_length = _integer(
        value.source_sequence_length,
        "counters.source_sequence_length",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    if type(value.full_logits) is not bool:
        raise LMHeadReferenceError("counters.full_logits must be an exact boolean")
    evaluated_positions = sequence_length if value.full_logits else 1
    hidden_width = _integer(
        value.hidden_width,
        "counters.hidden_width",
        minimum=1,
        maximum=OFFICIAL_HIDDEN_WIDTH,
    )
    vocabulary_size = _integer(
        value.declared_vocabulary_size,
        "counters.declared_vocabulary_size",
        minimum=1,
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    world_size = value.tensor_parallel_world_size
    if type(world_size) is not int or world_size not in (
        OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES
    ):
        raise LMHeadReferenceError("counter tensor-parallel world size differs")
    if vocabulary_size % world_size:
        raise LMHeadReferenceError(
            "counter vocabulary size is not divisible by tensor parallelism"
        )
    evaluated_rows = _integer(
        value.evaluated_vocabulary_rows,
        "counters.evaluated_vocabulary_rows",
        minimum=1,
        maximum=vocabulary_size,
    )
    if type(value.complete_output) is not bool:
        raise LMHeadReferenceError("counters.complete_output must be an exact boolean")
    evaluated_shards = _integer(
        value.evaluated_tensor_parallel_shards,
        "counters.evaluated_tensor_parallel_shards",
        minimum=1,
        maximum=world_size,
    )
    expected = _counter_values(
        batch_count=batch_count,
        sequence_length=sequence_length,
        evaluated_positions=evaluated_positions,
        full_logits=value.full_logits,
        hidden_width=hidden_width,
        vocabulary_size=vocabulary_size,
        evaluated_vocabulary_rows=evaluated_rows,
        complete_output=value.complete_output,
        world_size=world_size,
        evaluated_shards=evaluated_shards,
    )
    for field in fields(value):
        observed = getattr(value, field.name)
        expected_value = expected[field.name]
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise LMHeadReferenceError(
                f"counters.{field.name} does not reconcile to LM-head dimensions"
            )
    return value


def _hash_text(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LMHeadReferenceError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _validate_result(value: object) -> LMHeadResult:
    if type(value) is not LMHeadResult:
        raise LMHeadReferenceError("result must be an exact LMHeadResult record")
    if (
        type(value.numeric_profile) is not str
        or value.numeric_profile != LM_HEAD_NUMERIC_PROFILE
    ):
        raise LMHeadReferenceError("result numeric profile differs")
    if type(value.full_logits) is not bool:
        raise LMHeadReferenceError("result.full_logits must be an exact boolean")
    world_size = value.tensor_parallel_world_size
    if type(world_size) is not int or world_size not in (
        OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES
    ):
        raise LMHeadReferenceError("result tensor-parallel world size differs")
    vocabulary_size = _integer(
        value.declared_vocabulary_size,
        "result.declared_vocabulary_size",
        minimum=1,
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    if vocabulary_size % world_size:
        raise LMHeadReferenceError(
            "result vocabulary is not divisible by tensor parallelism"
        )
    _exact_tuple(value.selected_token_ids, "result.selected_token_ids")
    selected = _selected_token_ids(
        value.selected_token_ids,
        vocabulary_size=vocabulary_size,
    )
    partition_rows = vocabulary_size // world_size
    expected_ranks = tuple(token_id // partition_rows for token_id in selected)
    expected_local = tuple(token_id % partition_rows for token_id in selected)
    if (
        type(value.selected_partition_ranks) is not tuple
        or value.selected_partition_ranks != expected_ranks
        or any(type(rank) is not int for rank in value.selected_partition_ranks)
    ):
        raise LMHeadReferenceError("result selected partition ranks differ")
    if (
        type(value.selected_local_row_indices) is not tuple
        or value.selected_local_row_indices != expected_local
        or any(type(row) is not int for row in value.selected_local_row_indices)
    ):
        raise LMHeadReferenceError("result selected local rows differ")
    complete = _complete_selection(selected, vocabulary_size)
    if type(value.complete_output) is not bool or value.complete_output != complete:
        raise LMHeadReferenceError("result completion status differs")
    if type(value.counters) is not LMHeadCounters:
        raise LMHeadReferenceError("result counters must be exact")
    counters = _validate_counters(value.counters)
    official = (
        counters.hidden_width == OFFICIAL_HIDDEN_WIDTH
        and vocabulary_size == OFFICIAL_VOCABULARY_SIZE
    )
    if (
        type(value.official_shape_profile) is not bool
        or value.official_shape_profile != official
    ):
        raise LMHeadReferenceError("result official-shape status differs")
    if (
        counters.full_logits != value.full_logits
        or counters.declared_vocabulary_size != vocabulary_size
        or counters.evaluated_vocabulary_rows != len(selected)
        or counters.complete_output != complete
        or counters.tensor_parallel_world_size != world_size
        or counters.source_sequence_length != value.source_sequence_length
        or counters.evaluated_tensor_parallel_shards
        != len(set(expected_ranks))
    ):
        raise LMHeadReferenceError("result metadata does not reconcile to counters")
    _hash_text(
        value.selected_hidden_bf16_sha256,
        "result.selected_hidden_bf16_sha256",
    )
    _hash_text(
        value.selected_weight_bf16_sha256,
        "result.selected_weight_bf16_sha256",
    )
    _hash_text(value.logits_binary32_sha256, "result.logits_binary32_sha256")

    batch_count = counters.batch_count
    positions = counters.evaluated_positions_per_batch
    selected_count = len(selected)
    batches = _exact_tuple(value.logits_binary32_codes, "result.logits_binary32_codes")
    if len(batches) != batch_count:
        raise LMHeadReferenceError("result logits batch extent differs")
    if value.full_logits:
        for batch, raw_sequence in enumerate(batches):
            sequence = _exact_tuple(
                raw_sequence,
                f"result.logits_binary32_codes[{batch}]",
            )
            if len(sequence) != positions:
                raise LMHeadReferenceError("result full-logit position extent differs")
            for position, raw_row in enumerate(sequence):
                row = _exact_tuple(
                    raw_row,
                    f"result.logits_binary32_codes[{batch}][{position}]",
                )
                if len(row) != selected_count:
                    raise LMHeadReferenceError("result vocabulary extent differs")
                for index, code in enumerate(row):
                    _finite_binary32(
                        code,
                        "result.logits_binary32_codes"
                        f"[{batch}][{position}][{index}]",
                    )
    else:
        for batch, raw_row in enumerate(batches):
            row = _exact_tuple(
                raw_row,
                f"result.logits_binary32_codes[{batch}]",
            )
            if len(row) != selected_count:
                raise LMHeadReferenceError("result vocabulary extent differs")
            for index, code in enumerate(row):
                _finite_binary32(
                    code,
                    f"result.logits_binary32_codes[{batch}][{index}]",
                )
    if _hash_binary32_output(
        value.logits_binary32_codes,
        full_logits=value.full_logits,
    ) != value.logits_binary32_sha256:
        raise LMHeadReferenceError("result logits hash does not reconcile")
    return value


def lm_head_selected_bf16(
    hidden_bf16_codes: object,
    selected_weight_bf16_codes: object,
    *,
    declared_vocabulary_size: int,
    selected_token_ids: object,
    tensor_parallel_world_size: int = 4,
    full_logits: bool = False,
) -> LMHeadResult:
    """Evaluate explicit global vocabulary rows under the complete head profile.

    Hidden input has shape ``[B,S,D]``. Main mode (``full_logits=False``)
    returns source-exact shape ``[B,V_selected]`` and reads only position
    ``S-1``. Full-logit mode returns ``[B,S,V_selected]``. Selected weight rows
    are supplied in increasing global token-ID order with shape
    ``[V_selected,D]``.
    """

    if type(full_logits) is not bool:
        raise LMHeadReferenceError("full_logits must be an exact boolean")
    world_size = _world_size(tensor_parallel_world_size)
    vocabulary_size = _integer(
        declared_vocabulary_size,
        "declared_vocabulary_size",
        minimum=1,
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    if vocabulary_size % world_size:
        raise LMHeadReferenceError(
            "declared_vocabulary_size must be divisible by tensor parallelism"
        )
    selected = _selected_token_ids(
        selected_token_ids,
        vocabulary_size=vocabulary_size,
    )
    (
        frozen_hidden,
        hidden_values,
        batch_count,
        sequence_length,
        hidden_width,
    ) = _freeze_hidden(hidden_bf16_codes, full_logits=full_logits)
    frozen_weights, weight_values = _freeze_selected_weights(
        selected_weight_bf16_codes,
        selected_count=len(selected),
        hidden_width=hidden_width,
    )

    output_rows: list[Binary32Vector] = []
    for hidden_row_index, hidden_row in enumerate(hidden_values):
        output_row: list[int] = []
        for selected_index, (token_id, weight_row) in enumerate(
            zip(selected, weight_values, strict=True)
        ):
            try:
                output_row.append(binary32_ordered_dot(hidden_row, weight_row))
            except NumericReferenceError as exc:
                raise LMHeadReferenceError(
                    "LM-head arithmetic failed at selected hidden row "
                    f"{hidden_row_index}, global token {token_id}, selected row "
                    f"{selected_index}: {exc}"
                ) from exc
        output_rows.append(tuple(output_row))

    evaluated_positions = sequence_length if full_logits else 1
    if full_logits:
        logits: Binary32Output = tuple(
            tuple(
                output_rows[batch * evaluated_positions + position]
                for position in range(evaluated_positions)
            )
            for batch in range(batch_count)
        )
    else:
        logits = tuple(output_rows)
    selected_hidden_codes = tuple(
        frozen_hidden[batch][position]
        for batch in range(batch_count)
        for position in (
            range(sequence_length) if full_logits else (sequence_length - 1,)
        )
    )
    partition_rows = vocabulary_size // world_size
    partition_ranks = tuple(token_id // partition_rows for token_id in selected)
    local_rows = tuple(token_id % partition_rows for token_id in selected)
    complete = _complete_selection(selected, vocabulary_size)
    counters = LMHeadCounters(
        **_counter_values(
            batch_count=batch_count,
            sequence_length=sequence_length,
            evaluated_positions=evaluated_positions,
            full_logits=full_logits,
            hidden_width=hidden_width,
            vocabulary_size=vocabulary_size,
            evaluated_vocabulary_rows=len(selected),
            complete_output=complete,
            world_size=world_size,
            evaluated_shards=len(set(partition_ranks)),
        )
    )
    return LMHeadResult(
        numeric_profile=LM_HEAD_NUMERIC_PROFILE,
        full_logits=full_logits,
        tensor_parallel_world_size=world_size,
        declared_vocabulary_size=vocabulary_size,
        selected_token_ids=selected,
        selected_partition_ranks=partition_ranks,
        selected_local_row_indices=local_rows,
        complete_output=complete,
        official_shape_profile=(
            hidden_width == OFFICIAL_HIDDEN_WIDTH
            and vocabulary_size == OFFICIAL_VOCABULARY_SIZE
        ),
        source_sequence_length=sequence_length,
        selected_hidden_bf16_sha256=_hash_bf16_rows(selected_hidden_codes),
        selected_weight_bf16_sha256=_hash_bf16_rows(frozen_weights),
        logits_binary32_sha256=_hash_binary32_output(
            logits,
            full_logits=full_logits,
        ),
        logits_binary32_codes=logits,
        counters=counters,
    )


def lm_head_bf16(
    hidden_bf16_codes: object,
    weight_shards_bf16_codes: object,
    *,
    tensor_parallel_world_size: int = 4,
    full_logits: bool = False,
) -> LMHeadResult:
    """Execute every vocabulary row from rank-ordered contiguous shards.

    ``weight_shards_bf16_codes`` contains exactly ``world_size`` equal-sized
    matrices. Concatenating shard rows in rank order reconstructs global token
    IDs and the released ``all_gather``/``cat`` result.
    """

    world_size = _world_size(tensor_parallel_world_size)
    raw_shards = _sequence(weight_shards_bf16_codes, "weight_shards_bf16_codes")
    if len(raw_shards) != world_size:
        raise LMHeadReferenceError(
            "weight_shards_bf16_codes must contain one shard per tensor-parallel rank"
        )
    partition_rows: int | None = None
    flattened: list[object] = []
    for rank, raw_shard in enumerate(raw_shards):
        shard = _sequence(raw_shard, f"weight_shards_bf16_codes[{rank}]")
        if partition_rows is None:
            partition_rows = len(shard)
            if partition_rows < 1:
                raise LMHeadReferenceError("weight shards must contain a row")
        elif len(shard) != partition_rows:
            raise LMHeadReferenceError("weight shards must have equal row counts")
        flattened.extend(shard)
    assert partition_rows is not None
    vocabulary_size = partition_rows * world_size
    if vocabulary_size > OFFICIAL_VOCABULARY_SIZE:
        raise LMHeadReferenceError("weight shards exceed the official vocabulary")
    return lm_head_selected_bf16(
        hidden_bf16_codes,
        flattened,
        declared_vocabulary_size=vocabulary_size,
        selected_token_ids=list(range(vocabulary_size)),
        tensor_parallel_world_size=world_size,
        full_logits=full_logits,
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "BINARY32_MAX_ENCODING",
    "CHECKPOINT_INDEX_PATH",
    "CHECKPOINT_INDEX_SHA256",
    "CHECKPOINT_LOCK_ID",
    "CONFIG_EXPECTED_FIELDS",
    "CONVERT_SOURCE_EXPRESSIONS",
    "CONVERT_SOURCE_PATH",
    "CONVERT_SOURCE_SHA256",
    "EXCLUDED_CLAIMS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "LM_HEAD_NUMERIC_PROFILE",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "GENERATE_SOURCE_PATH",
    "GENERATE_SOURCE_SHA256",
    "OFFICIAL_DSPARK_BLOCK_SIZE",
    "OFFICIAL_DSPARK_SITE_COUNT",
    "OFFICIAL_HIDDEN_WIDTH",
    "OFFICIAL_MAIN_SITE_COUNT",
    "OFFICIAL_MP4_PARTITION_ROWS",
    "OFFICIAL_MP4_WEIGHT_SHA256",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_SELECTED_ROW_SHA256",
    "OFFICIAL_SITE_COUNT",
    "OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES",
    "OFFICIAL_VOCABULARY_SIZE",
    "OFFICIAL_WEIGHT_BYTES",
    "OFFICIAL_WEIGHT_SHA256",
    "OFFICIAL_WEIGHT_SHAPE",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "SOURCE_EXPRESSIONS",
    "LMHeadCounters",
    "LMHeadReferenceError",
    "LMHeadResult",
    "lm_head_bf16",
    "lm_head_selected_bf16",
]
