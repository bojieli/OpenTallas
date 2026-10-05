"""Artifact-neutral service arithmetic for DeepSeek V4 grouped output.

The implementation is pinned to ``deepseek-ai/DeepSeek-V4-Flash-0731`` at
revision ``7872f01b1d1fe23eabc4c98b48bffcef5a386062``.  The relevant official
source fragment reshapes sparse-attention output and canonical ``wo_a`` BF16
weights by local group, evaluates ``torch.einsum("bsgd,grd->bsgr", ...)``, and
then flattens group-major before ``wo_b``.

This module is a standalone arithmetic lane for artifact-service integration.
It accepts already authenticated, already materialized BF16 encodings.  It has
no compiler, checkpoint, filesystem, expected-output, or reference-model
dependency.  Raw FP8/E8M0 checkpoint conversion remains an upstream concern;
this module does not claim that such conversion or authentication occurred.

PyTorch does not freeze a cross-backend reduction tree.  The service profile
therefore uses the same explicit target rule as the architecture contract:
flatten each group's eight contiguous heads in increasing head/column order,
start at positive binary32 zero, and apply one binary32 RNE fused product-add
for every increasing-K BF16 product.  The completed finite accumulator is
converted once to BF16 RNE with finite saturation.  Intermediate binary32
overflow poisons the entire command.

Logical counters below are source-derived arithmetic reconciliation values.
They are not cycles, latency, throughput, physical memory traffic, energy,
area, density, routing, or PPA evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .hc_pre_numeric import HCPreServiceNumericError, rn32_fused_product_add


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
CONVERT_SOURCE_PATH = "inference/convert.py"
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE = (
    "opentallas.deepseek_v4_grouped_output_service_bf16.v1"
)

OFFICIAL_GLOBAL_GROUPS = 8
OFFICIAL_HEADS = 64
OFFICIAL_HEADS_PER_GROUP = 8
OFFICIAL_HEAD_DIM = 512
OFFICIAL_GROUP_INPUT_FEATURES = 4096
OFFICIAL_OUTPUT_RANK = 1024
OFFICIAL_GLOBAL_OUTPUT_FEATURES = 8192
OFFICIAL_RUNTIME_WEIGHT_DTYPE = "BF16"
OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES = (1, 2, 4, 8)
MAX_TOKENS_PER_COMMAND = 4
BF16_MAX_ENCODING = (1 << 16) - 1
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

SOURCE_OPERATIONS = (
    "attention_group_view",
    "weight_group_view",
    "grouped_einsum_bsgd_grd_to_bsgr",
    "group_major_flatten",
)

EXCLUDED_CLAIMS = (
    "inverse_rotary_embedding",
    "raw_fp8_e8m0_checkpoint_dequantization",
    "output_b_projection",
    "tensor_parallel_collective",
    "compiler_lowering",
    "checkpoint_or_artifact_loading",
    "official_checkpoint_result_attestation",
    "service_command_authentication",
    "schedule_cycles_latency_traffic_energy_area_density_routing_ppa",
    "end_to_end_model_execution",
)


BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadTensor: TypeAlias = tuple[BF16Vector, ...]
BF16SequenceTensor: TypeAlias = tuple[BF16HeadTensor, ...]
BF16AttentionTensor: TypeAlias = tuple[BF16SequenceTensor, ...]
BF16WeightMatrix: TypeAlias = tuple[BF16Vector, ...]
BF16GroupedOutput: TypeAlias = tuple[tuple[tuple[BF16Vector, ...], ...], ...]
BF16FlattenedOutput: TypeAlias = tuple[tuple[BF16Vector, ...], ...]


class GroupedOutputServiceNumericError(ValueError):
    """Raised when a complete grouped-output service command must poison."""


@dataclass(frozen=True)
class GroupedOutputServiceNumericResult:
    """Immutable local-rank outputs, ownership metadata, and logical counts.

    ``complete_output`` means that every declared output-rank row was
    evaluated for each local group.  It does not attest checkpoint provenance,
    source-artifact authentication, or end-to-end model execution.
    """

    numeric_profile: str
    tensor_parallel_world_size: int
    tensor_parallel_rank: int
    global_group_indices: tuple[int, ...]
    selected_output_ranks: tuple[int, ...]
    complete_output: bool
    grouped_bf16_codes: BF16GroupedOutput
    flattened_bf16_codes: BF16FlattenedOutput
    output_saturation_count: int
    logical_counters: Mapping[str, int]

    def __post_init__(self) -> None:
        if self.numeric_profile != GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE:
            raise GroupedOutputServiceNumericError(
                "grouped-output result numeric profile differs"
            )
        world_size, rank, local_group_count, global_groups = _tensor_parallel_mapping(
            self.tensor_parallel_world_size,
            self.tensor_parallel_rank,
        )
        if (
            type(self.global_group_indices) is not tuple
            or self.global_group_indices != global_groups
        ):
            raise GroupedOutputServiceNumericError(
                "grouped-output result global-group ownership differs"
            )
        if type(self.selected_output_ranks) is not tuple:
            raise GroupedOutputServiceNumericError(
                "grouped-output result selected ranks must be immutable"
            )
        selected_ranks = _selected_output_ranks(self.selected_output_ranks)
        selected_rank_count = len(selected_ranks)
        complete_output = selected_ranks == tuple(range(OFFICIAL_OUTPUT_RANK))
        if (
            type(self.complete_output) is not bool
            or self.complete_output != complete_output
        ):
            raise GroupedOutputServiceNumericError(
                "grouped-output result completion status differs from rank coverage"
            )

        if type(self.grouped_bf16_codes) is not tuple or not (
            1 <= len(self.grouped_bf16_codes) <= MAX_TOKENS_PER_COMMAND
        ):
            raise GroupedOutputServiceNumericError(
                "grouped-output result batch axis is not an immutable valid extent"
            )
        sequence_length: int | None = None
        expected_flattened: list[tuple[BF16Vector, ...]] = []
        for batch_index, sequence in enumerate(self.grouped_bf16_codes):
            if type(sequence) is not tuple or not sequence:
                raise GroupedOutputServiceNumericError(
                    f"grouped-output result batch {batch_index} has an invalid sequence"
                )
            if sequence_length is None:
                sequence_length = len(sequence)
                if len(self.grouped_bf16_codes) * sequence_length > (
                    MAX_TOKENS_PER_COMMAND
                ):
                    raise GroupedOutputServiceNumericError(
                        "grouped-output result token count exceeds the command bound"
                    )
            elif len(sequence) != sequence_length:
                raise GroupedOutputServiceNumericError(
                    "grouped-output result is not rectangular on the sequence axis"
                )
            flattened_sequence: list[BF16Vector] = []
            for position, groups in enumerate(sequence):
                if type(groups) is not tuple or len(groups) != local_group_count:
                    raise GroupedOutputServiceNumericError(
                        "grouped-output result has an invalid local-group extent at "
                        f"batch {batch_index}, position {position}"
                    )
                flattened_row: list[int] = []
                for local_group, row in enumerate(groups):
                    if type(row) is not tuple or len(row) != selected_rank_count:
                        raise GroupedOutputServiceNumericError(
                            "grouped-output result has an invalid selected-rank extent "
                            f"at batch {batch_index}, position {position}, local group "
                            f"{local_group}"
                        )
                    flattened_row.extend(
                        _finite_bf16(
                            code,
                            "grouped-output result grouped_bf16_codes"
                            f"[{batch_index}][{position}][{local_group}][{output}]",
                        )
                        for output, code in enumerate(row)
                    )
                flattened_sequence.append(tuple(flattened_row))
            expected_flattened.append(tuple(flattened_sequence))

        expected_flattened_tuple = tuple(expected_flattened)
        if (
            type(self.flattened_bf16_codes) is not tuple
            or any(
                type(sequence) is not tuple for sequence in self.flattened_bf16_codes
            )
            or any(
                type(row) is not tuple
                for sequence in self.flattened_bf16_codes
                for row in sequence
            )
            or self.flattened_bf16_codes != expected_flattened_tuple
        ):
            raise GroupedOutputServiceNumericError(
                "grouped-output result flattened payload differs from grouped payload"
            )

        assert sequence_length is not None
        token_count = len(self.grouped_bf16_codes) * sequence_length
        evaluated_outputs = token_count * local_group_count * selected_rank_count
        saturation_count = _integer(
            self.output_saturation_count,
            "grouped-output result output_saturation_count",
            minimum=0,
            maximum=evaluated_outputs,
        )
        if type(self.logical_counters) is not _MAPPING_PROXY_TYPE:
            raise GroupedOutputServiceNumericError(
                "grouped-output result logical counters must be an immutable mapping"
            )
        counter_values = dict(self.logical_counters)
        expected_counters = grouped_output_functional_counters(
            token_count,
            world_size,
            selected_rank_count,
            output_saturation_count=saturation_count,
        )
        if counter_values != dict(expected_counters):
            raise GroupedOutputServiceNumericError(
                "grouped-output result logical counters do not reconcile"
            )
        # ``MappingProxyType`` prevents mutation through the proxy but callers
        # can retain and mutate its backing dictionary.  Replace every accepted
        # proxy with one backed by a private, reconciled snapshot so a public
        # constructor cannot create a result whose counters drift after return.
        object.__setattr__(
            self,
            "logical_counters",
            MappingProxyType(counter_values),
        )

    @property
    def semantic_counters(self) -> Mapping[str, int]:
        """Alias emphasizing that these counts make no physical claim."""

        return self.logical_counters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise GroupedOutputServiceNumericError(
            f"{label} must be an exact list or tuple"
        )
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise GroupedOutputServiceNumericError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _tensor_parallel_mapping(
    world_size: object,
    rank: object,
) -> tuple[int, int, int, tuple[int, ...]]:
    if type(world_size) is not int or world_size not in (
        OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES
    ):
        raise GroupedOutputServiceNumericError(
            "tensor_parallel_world_size must be exactly 1, 2, 4, or 8"
        )
    rank = _integer(
        rank,
        "tensor_parallel_rank",
        minimum=0,
        maximum=world_size - 1,
    )
    local_group_count = OFFICIAL_GLOBAL_GROUPS // world_size
    group_start = rank * local_group_count
    return (
        world_size,
        rank,
        local_group_count,
        tuple(range(group_start, group_start + local_group_count)),
    )


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise GroupedOutputServiceNumericError(
            f"{label} must be an unsigned 16-bit BF16 encoding"
        )
    if value & 0x7F80 == 0x7F80:
        raise GroupedOutputServiceNumericError(f"{label} must be finite BF16")
    return value


_RowCache = dict[int, tuple[tuple[object, ...], BF16Vector]]


def _freeze_bf16_row(
    value: object,
    *,
    expected_length: int,
    label: str,
    immutable_cache: _RowCache,
) -> BF16Vector:
    row = _sequence(value, label)
    if len(row) != expected_length:
        raise GroupedOutputServiceNumericError(
            f"{label} must contain exactly {expected_length} BF16 values"
        )

    # Exact tuples and integers are deeply immutable.  Retaining an exact
    # source tuple lets repeated immutable rows be validated once without
    # weakening atomicity or trusting mutable caller storage.
    if type(row) is tuple:
        cached = immutable_cache.get(id(row))
        if cached is not None and cached[0] is row:
            return cached[1]

    frozen = tuple(
        _finite_bf16(code, f"{label}[{column}]") for column, code in enumerate(row)
    )
    if type(row) is tuple:
        immutable_cache[id(row)] = (row, frozen)
    return frozen


def _freeze_attention(
    value: object,
    *,
    local_group_count: int,
) -> tuple[BF16AttentionTensor, int, int, int]:
    label = "attention_bf16_codes"
    raw_batches = _sequence(value, label)
    if not raw_batches:
        raise GroupedOutputServiceNumericError(
            f"{label} must contain at least one batch"
        )
    if len(raw_batches) > MAX_TOKENS_PER_COMMAND:
        raise GroupedOutputServiceNumericError(
            f"{label} batch extent exceeds the {MAX_TOKENS_PER_COMMAND}-token "
            "command bound"
        )

    expected_heads = local_group_count * OFFICIAL_HEADS_PER_GROUP
    sequence_length: int | None = None
    row_cache: _RowCache = {}
    batches: list[BF16SequenceTensor] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence_label = f"{label}[{batch_index}]"
        sequence = _sequence(raw_sequence, sequence_label)
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise GroupedOutputServiceNumericError(
                    f"{label} must contain at least one position per batch"
                )
            token_count = len(raw_batches) * sequence_length
            if token_count > MAX_TOKENS_PER_COMMAND:
                raise GroupedOutputServiceNumericError(
                    f"{label} batch*sequence must be in [1, {MAX_TOKENS_PER_COMMAND}]"
                )
        elif len(sequence) != sequence_length:
            raise GroupedOutputServiceNumericError(
                f"{label} must be rectangular on the sequence axis"
            )

        frozen_sequence: list[BF16HeadTensor] = []
        for position, raw_heads in enumerate(sequence):
            heads_label = f"{sequence_label}[{position}]"
            heads = _sequence(raw_heads, heads_label)
            if len(heads) != expected_heads:
                raise GroupedOutputServiceNumericError(
                    f"{heads_label} must contain exactly {expected_heads} local heads"
                )
            frozen_sequence.append(
                tuple(
                    _freeze_bf16_row(
                        raw_head,
                        expected_length=OFFICIAL_HEAD_DIM,
                        label=f"{heads_label}[{head}]",
                        immutable_cache=row_cache,
                    )
                    for head, raw_head in enumerate(heads)
                )
            )
        batches.append(tuple(frozen_sequence))

    assert sequence_length is not None
    return (
        tuple(batches),
        len(batches),
        sequence_length,
        len(batches) * sequence_length,
    )


def _selected_output_ranks(value: object) -> tuple[int, ...]:
    raw = _sequence(value, "selected_output_ranks")
    ranks = tuple(
        _integer(
            rank,
            f"selected_output_ranks[{index}]",
            minimum=0,
            maximum=OFFICIAL_OUTPUT_RANK - 1,
        )
        for index, rank in enumerate(raw)
    )
    if not ranks:
        raise GroupedOutputServiceNumericError(
            "selected_output_ranks must contain at least one rank"
        )
    if ranks != tuple(sorted(set(ranks))):
        raise GroupedOutputServiceNumericError(
            "selected_output_ranks must be unique and strictly increasing"
        )
    return ranks


def _freeze_weights(
    value: object,
    *,
    local_group_count: int,
    selected_rank_count: int,
) -> BF16WeightMatrix:
    label = "weight_bf16_codes"
    raw_rows = _sequence(value, label)
    expected_rows = local_group_count * selected_rank_count
    if len(raw_rows) != expected_rows:
        raise GroupedOutputServiceNumericError(
            f"{label} must contain exactly {expected_rows} group-major rows"
        )

    row_cache: _RowCache = {}
    return tuple(
        _freeze_bf16_row(
            raw_row,
            expected_length=OFFICIAL_GROUP_INPUT_FEATURES,
            label=f"{label}[{row}]",
            immutable_cache=row_cache,
        )
        for row, raw_row in enumerate(raw_rows)
    )


def _binary32_to_bf16(code: object) -> tuple[int, bool]:
    if type(code) is not int or not 0 <= code < 1 << 32:
        raise GroupedOutputServiceNumericError(
            "binary32 result must be an unsigned 32-bit encoding"
        )
    if code & 0x7F800000 == 0x7F800000:
        raise GroupedOutputServiceNumericError(
            "nonfinite binary32 cannot convert to BF16"
        )
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = upper & 0x7F80 == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return upper, saturated


def _widen_bf16(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code << 16


def _ordered_dot_to_bf16(
    left: BF16Vector,
    right: BF16Vector,
    *,
    batch_index: int,
    position: int,
    local_group: int,
    output_rank: int,
) -> tuple[int, bool]:
    accumulator = 0
    for feature, (left_code, right_code) in enumerate(zip(left, right, strict=True)):
        # The established service FMA canonicalizes zero and returns the
        # accumulator unchanged for an exact zero product.  Skipping that call
        # is semantically identical; logical counters still count every K.
        if left_code & 0x7FFF == 0 or right_code & 0x7FFF == 0:
            continue
        try:
            accumulator = rn32_fused_product_add(
                accumulator,
                _widen_bf16(left_code),
                _widen_bf16(right_code),
            )
        except HCPreServiceNumericError as exc:
            raise GroupedOutputServiceNumericError(
                "grouped-output arithmetic failed at batch "
                f"{batch_index}, position {position}, local group "
                f"{local_group}, output rank {output_rank}, feature "
                f"{feature}: {exc}"
            ) from exc
    return _binary32_to_bf16(accumulator)


def grouped_output_functional_counters(
    token_count: object,
    tensor_parallel_world_size: object,
    evaluated_output_ranks_per_group: object,
    *,
    output_saturation_count: object = 0,
) -> Mapping[str, int]:
    """Return exact source-shape arithmetic counts for one local command."""

    token_count = _integer(
        token_count,
        "token_count",
        minimum=1,
        maximum=MAX_TOKENS_PER_COMMAND,
    )
    world_size, _, local_group_count, _ = _tensor_parallel_mapping(
        tensor_parallel_world_size,
        0,
    )
    selected_rank_count = _integer(
        evaluated_output_ranks_per_group,
        "evaluated_output_ranks_per_group",
        minimum=1,
        maximum=OFFICIAL_OUTPUT_RANK,
    )
    evaluated_outputs = token_count * local_group_count * selected_rank_count
    saturation_count = _integer(
        output_saturation_count,
        "output_saturation_count",
        minimum=0,
        maximum=evaluated_outputs,
    )
    input_values = token_count * local_group_count * OFFICIAL_GROUP_INPUT_FEATURES
    weight_values = (
        local_group_count * selected_rank_count * OFFICIAL_GROUP_INPUT_FEATURES
    )
    product_accumulates = evaluated_outputs * OFFICIAL_GROUP_INPUT_FEATURES
    counters = {
        "complete_events": 1,
        "grouped_output_attention_bf16_values": input_values,
        "grouped_output_attention_group_view_values": input_values,
        "grouped_output_binary32_accumulation_roundings": product_accumulates,
        "grouped_output_canonical_weight_bf16_values": weight_values,
        "grouped_output_declared_full_output_bf16_values": (
            token_count * local_group_count * OFFICIAL_OUTPUT_RANK
        ),
        "grouped_output_evaluated_output_ranks_per_group": selected_rank_count,
        "grouped_output_exact_product_accumulates": product_accumulates,
        "grouped_output_flattened_output_bf16_values": evaluated_outputs,
        "grouped_output_group_input_features": OFFICIAL_GROUP_INPUT_FEATURES,
        "grouped_output_grouped_output_bf16_values": evaluated_outputs,
        "grouped_output_local_group_count": local_group_count,
        "grouped_output_local_head_count": (
            local_group_count * OFFICIAL_HEADS_PER_GROUP
        ),
        "grouped_output_output_bf16_conversions": evaluated_outputs,
        "grouped_output_output_bf16_saturations": saturation_count,
        "grouped_output_token_count": token_count,
        "grouped_output_weight_group_view_values": weight_values,
        "semantic_operators_executed": 1,
        "tensor_parallel_world_size": world_size,
    }
    return MappingProxyType(dict(sorted(counters.items())))


def _execute_validated(
    attention: BF16AttentionTensor,
    weights: BF16WeightMatrix,
    *,
    batch_count: int,
    sequence_length: int,
    token_count: int,
    tensor_parallel_world_size: int,
    tensor_parallel_rank: int,
    local_group_count: int,
    global_group_indices: tuple[int, ...],
    selected_output_ranks: tuple[int, ...],
) -> GroupedOutputServiceNumericResult:
    selected_rank_count = len(selected_output_ranks)
    grouped_batches: list[tuple[tuple[BF16Vector, ...], ...]] = []
    flattened_batches: list[tuple[BF16Vector, ...]] = []
    saturation_count = 0

    for batch_index in range(batch_count):
        grouped_sequence: list[tuple[BF16Vector, ...]] = []
        flattened_sequence: list[BF16Vector] = []
        for position in range(sequence_length):
            heads = attention[batch_index][position]
            output_groups: list[BF16Vector] = []
            for local_group in range(local_group_count):
                head_start = local_group * OFFICIAL_HEADS_PER_GROUP
                input_row = tuple(
                    code
                    for head in heads[
                        head_start : head_start + OFFICIAL_HEADS_PER_GROUP
                    ]
                    for code in head
                )
                output_row: list[int] = []
                weight_start = local_group * selected_rank_count
                for selected_index, output_rank in enumerate(selected_output_ranks):
                    output_code, saturated = _ordered_dot_to_bf16(
                        input_row,
                        weights[weight_start + selected_index],
                        batch_index=batch_index,
                        position=position,
                        local_group=local_group,
                        output_rank=output_rank,
                    )
                    output_row.append(output_code)
                    saturation_count += int(saturated)
                output_groups.append(tuple(output_row))
            grouped_row = tuple(output_groups)
            grouped_sequence.append(grouped_row)
            flattened_sequence.append(
                tuple(code for group in grouped_row for code in group)
            )
        grouped_batches.append(tuple(grouped_sequence))
        flattened_batches.append(tuple(flattened_sequence))

    complete_output = selected_output_ranks == tuple(range(OFFICIAL_OUTPUT_RANK))
    counters = grouped_output_functional_counters(
        token_count,
        tensor_parallel_world_size,
        selected_rank_count,
        output_saturation_count=saturation_count,
    )
    return GroupedOutputServiceNumericResult(
        numeric_profile=GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        tensor_parallel_world_size=tensor_parallel_world_size,
        tensor_parallel_rank=tensor_parallel_rank,
        global_group_indices=global_group_indices,
        selected_output_ranks=selected_output_ranks,
        complete_output=complete_output,
        grouped_bf16_codes=tuple(grouped_batches),
        flattened_bf16_codes=tuple(flattened_batches),
        output_saturation_count=saturation_count,
        logical_counters=counters,
    )


def execute_grouped_output_project_selected_bf16(
    attention_bf16_codes: object,
    selected_weight_bf16_codes: object,
    *,
    tensor_parallel_world_size: int,
    tensor_parallel_rank: int,
    selected_output_ranks: object,
) -> GroupedOutputServiceNumericResult:
    """Execute explicit official output-rank rows for every local group.

    Attention has shape ``[B,S,H_local,512]`` where ``B*S`` is in ``1..4``.
    Selected weights have shape ``[G_local*R_selected,4096]`` in group-major,
    then increasing-selected-rank order.  This audit entry point preserves the
    official declared rank of 1,024 and is structurally complete only when all
    rows appear.  It does not establish where the supplied rows came from.
    """

    world_size, rank, local_group_count, global_groups = _tensor_parallel_mapping(
        tensor_parallel_world_size,
        tensor_parallel_rank,
    )
    selected_ranks = _selected_output_ranks(selected_output_ranks)
    attention, batch_count, sequence_length, token_count = _freeze_attention(
        attention_bf16_codes,
        local_group_count=local_group_count,
    )
    weights = _freeze_weights(
        selected_weight_bf16_codes,
        local_group_count=local_group_count,
        selected_rank_count=len(selected_ranks),
    )
    return _execute_validated(
        attention,
        weights,
        batch_count=batch_count,
        sequence_length=sequence_length,
        token_count=token_count,
        tensor_parallel_world_size=world_size,
        tensor_parallel_rank=rank,
        local_group_count=local_group_count,
        global_group_indices=global_groups,
        selected_output_ranks=selected_ranks,
    )


def execute_grouped_output_project_bf16(
    attention_bf16_codes: object,
    weight_bf16_codes: object,
    *,
    tensor_parallel_world_size: int,
    tensor_parallel_rank: int,
) -> GroupedOutputServiceNumericResult:
    """Execute all 1,024 official output ranks for one tensor-parallel rank."""

    return execute_grouped_output_project_selected_bf16(
        attention_bf16_codes,
        weight_bf16_codes,
        tensor_parallel_world_size=tensor_parallel_world_size,
        tensor_parallel_rank=tensor_parallel_rank,
        selected_output_ranks=tuple(range(OFFICIAL_OUTPUT_RANK)),
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "CONVERT_SOURCE_PATH",
    "CONVERT_SOURCE_SHA256",
    "EXCLUDED_CLAIMS",
    "GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE",
    "INFERENCE_CONFIG_SHA256",
    "MAX_TOKENS_PER_COMMAND",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_GLOBAL_GROUPS",
    "OFFICIAL_GLOBAL_OUTPUT_FEATURES",
    "OFFICIAL_GROUP_INPUT_FEATURES",
    "OFFICIAL_HEADS",
    "OFFICIAL_HEADS_PER_GROUP",
    "OFFICIAL_HEAD_DIM",
    "OFFICIAL_OUTPUT_RANK",
    "OFFICIAL_RUNTIME_WEIGHT_DTYPE",
    "OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES",
    "SOURCE_OPERATIONS",
    "GroupedOutputServiceNumericError",
    "GroupedOutputServiceNumericResult",
    "execute_grouped_output_project_bf16",
    "execute_grouped_output_project_selected_bf16",
    "grouped_output_functional_counters",
]
