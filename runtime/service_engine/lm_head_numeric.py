"""Independent functional arithmetic for selected DeepSeek V4 LM-head rows.

This lane imports neither ``runtime.reference`` nor compiler code.  It accepts
already authenticated BF16 input and weight encodings, widens them exactly to
binary32, and applies one finite binary32 RNE fused product/add per increasing
hidden index.  Explicit global vocabulary row indices are mapped to equal,
contiguous tensor-parallel shards.

The result is selected-row numeric evidence.  It does not authenticate a
checkpoint, execute a complete vocabulary head, issue a collective, or claim
physical cycles, traffic, throughput, energy, area, routing, or PPA.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .hc_pre_numeric import HCPreServiceNumericError, rn32_fused_product_add


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
SERVICE_NUMERIC_PROFILE = "opentallas.deepseek_v4_lm_head_service_binary32.v1"

OFFICIAL_HIDDEN_WIDTH = 4096
OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MAX_EVIDENCE_ROWS = 20
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Vector, ...]

EXCLUDED_CLAIMS = (
    "complete_vocabulary_output",
    "checkpoint_or_artifact_authentication",
    "hidden_activation_provenance",
    "tensor_parallel_collective_execution",
    "sampling_or_dspark_markov_loop",
    "compiler_or_rtl_execution",
    "physical_cycles_traffic_bandwidth_latency_throughput_energy_area_routing_ppa",
)


class LMHeadServiceNumericError(ValueError):
    """Raised when a selected-row numeric command must poison."""


@dataclass(frozen=True, slots=True)
class LMHeadServiceNumericResult:
    """Immutable selected logits, ownership, and logical reconciliation."""

    numeric_profile: str
    vocabulary_row_indices: tuple[int, ...]
    owner_ranks: tuple[int, ...]
    logits_binary32_codes: Binary32Matrix
    logical_counters: MappingProxyType

    def __post_init__(self) -> None:
        _validate_result(self)

    @property
    def semantic_counters(self) -> MappingProxyType:
        """Alias emphasizing that the values make no physical claim."""

        return self.logical_counters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise LMHeadServiceNumericError(f"{label} must be an exact list or tuple")
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise LMHeadServiceNumericError(
            f"{label} must be a deeply immutable exact tuple"
        )
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise LMHeadServiceNumericError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise LMHeadServiceNumericError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    if value & 0x7F80 == 0x7F80:
        raise LMHeadServiceNumericError(f"{label} must be finite BF16")
    return value


def _finite_binary32(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 32:
        raise LMHeadServiceNumericError(f"{label} must be a binary32 encoding")
    if value & 0x7F800000 == 0x7F800000:
        raise LMHeadServiceNumericError(f"{label} must be finite binary32")
    return 0 if value & 0x7FFFFFFF == 0 else value


def _freeze_matrix(
    value: object,
    *,
    label: str,
    expected_width: int | None = None,
    exact_tuple: bool = False,
) -> tuple[BF16Matrix, int]:
    raw_rows = _exact_tuple(value, label) if exact_tuple else _sequence(value, label)
    if not raw_rows:
        raise LMHeadServiceNumericError(f"{label} must contain at least one row")
    if len(raw_rows) > OFFICIAL_MAX_EVIDENCE_ROWS:
        raise LMHeadServiceNumericError(f"{label} exceeds the selected-row bound")
    width = expected_width
    output: list[BF16Vector] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = (
            _exact_tuple(raw_row, f"{label}[{row_index}]")
            if exact_tuple
            else _sequence(raw_row, f"{label}[{row_index}]")
        )
        if width is None:
            width = len(row)
            if not 1 <= width <= OFFICIAL_HIDDEN_WIDTH:
                raise LMHeadServiceNumericError(
                    f"{label} width is outside the official bound"
                )
        elif len(row) != width:
            raise LMHeadServiceNumericError(f"{label} must be rectangular")
        output.append(
            tuple(
                _finite_bf16(code, f"{label}[{row_index}][{column}]")
                for column, code in enumerate(row)
            )
        )
    assert width is not None
    return tuple(output), width


def _bf16_to_binary32(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code << 16


def _execute(input_rows: BF16Matrix, weight_rows: BF16Matrix) -> Binary32Matrix:
    output: list[Binary32Vector] = []
    for input_index, input_row in enumerate(input_rows):
        output_row: list[int] = []
        for selected_index, weight_row in enumerate(weight_rows):
            accumulator = 0
            try:
                for input_code, weight_code in zip(
                    input_row,
                    weight_row,
                    strict=True,
                ):
                    accumulator = rn32_fused_product_add(
                        accumulator,
                        _bf16_to_binary32(input_code),
                        _bf16_to_binary32(weight_code),
                    )
            except HCPreServiceNumericError as exc:
                raise LMHeadServiceNumericError(
                    f"LM-head service arithmetic failed at input row {input_index}, "
                    f"selected vocabulary row {selected_index}: {exc}"
                ) from exc
            output_row.append(accumulator)
        output.append(tuple(output_row))
    return tuple(output)


def _counter_values(
    *,
    input_rows: int,
    hidden_width: int,
    selected_rows: int,
    declared_vocabulary_size: int,
    world_size: int,
) -> dict[str, int]:
    products = input_rows * selected_rows * hidden_width
    return {
        "input_row_count": input_rows,
        "hidden_width": hidden_width,
        "selected_vocabulary_row_count": selected_rows,
        "declared_vocabulary_size": declared_vocabulary_size,
        "tensor_parallel_world_size": world_size,
        "local_vocabulary_size": declared_vocabulary_size // world_size,
        "input_bf16_values_read": input_rows * hidden_width,
        "selected_weight_bf16_values_read": selected_rows * hidden_width,
        "binary32_exact_product_accumulates": products,
        "selected_binary32_logits_produced": input_rows * selected_rows,
    }


def _validate_result(value: object) -> LMHeadServiceNumericResult:
    if type(value) is not LMHeadServiceNumericResult:
        raise LMHeadServiceNumericError(
            "result must be an exact LMHeadServiceNumericResult record"
        )
    if value.numeric_profile != SERVICE_NUMERIC_PROFILE:
        raise LMHeadServiceNumericError("result numeric profile differs")
    indices = _exact_tuple(value.vocabulary_row_indices, "result.vocabulary_row_indices")
    owners = _exact_tuple(value.owner_ranks, "result.owner_ranks")
    logits = _exact_tuple(value.logits_binary32_codes, "result.logits_binary32_codes")
    if type(value.logical_counters) is not _MAPPING_PROXY_TYPE:
        raise LMHeadServiceNumericError("result counters must be a mapping proxy")
    counters = dict(value.logical_counters)
    required = {
        "input_row_count",
        "hidden_width",
        "selected_vocabulary_row_count",
        "declared_vocabulary_size",
        "tensor_parallel_world_size",
        "local_vocabulary_size",
        "input_bf16_values_read",
        "selected_weight_bf16_values_read",
        "binary32_exact_product_accumulates",
        "selected_binary32_logits_produced",
    }
    if set(counters) != required or any(type(item) is not int for item in counters.values()):
        raise LMHeadServiceNumericError("result counter schema differs")
    expected = _counter_values(
        input_rows=counters["input_row_count"],
        hidden_width=counters["hidden_width"],
        selected_rows=counters["selected_vocabulary_row_count"],
        declared_vocabulary_size=counters["declared_vocabulary_size"],
        world_size=counters["tensor_parallel_world_size"],
    )
    if counters != expected:
        raise LMHeadServiceNumericError("result counters do not reconcile")
    if len(indices) != expected["selected_vocabulary_row_count"] or len(owners) != len(
        indices
    ):
        raise LMHeadServiceNumericError("result selected-row metadata extent differs")
    local = expected["local_vocabulary_size"]
    normalized_indices = tuple(
        _integer(
            index,
            f"result.vocabulary_row_indices[{position}]",
            minimum=0,
            maximum=expected["declared_vocabulary_size"] - 1,
        )
        for position, index in enumerate(indices)
    )
    if any(right <= left for left, right in zip(normalized_indices, normalized_indices[1:])):
        raise LMHeadServiceNumericError("result vocabulary rows must be increasing")
    if owners != tuple(index // local for index in normalized_indices):
        raise LMHeadServiceNumericError("result owner ranks differ")
    if len(logits) != expected["input_row_count"]:
        raise LMHeadServiceNumericError("result logit row extent differs")
    for row_index, raw_row in enumerate(logits):
        row = _exact_tuple(raw_row, f"result.logits_binary32_codes[{row_index}]")
        if len(row) != len(indices):
            raise LMHeadServiceNumericError("result selected-logit width differs")
        for column, code in enumerate(row):
            _finite_binary32(
                code,
                f"result.logits_binary32_codes[{row_index}][{column}]",
            )
    return value


def execute_selected_vocabulary_rows(
    input_bf16_codes: object,
    selected_weight_bf16_codes: object,
    *,
    vocabulary_row_indices: object,
    declared_vocabulary_size: int,
    tensor_parallel_world_size: int,
) -> LMHeadServiceNumericResult:
    """Execute independent increasing-K arithmetic for selected global rows."""

    inputs, width = _freeze_matrix(input_bf16_codes, label="input_bf16_codes")
    weights, _ = _freeze_matrix(
        selected_weight_bf16_codes,
        label="selected_weight_bf16_codes",
        expected_width=width,
    )
    vocabulary = _integer(
        declared_vocabulary_size,
        "declared_vocabulary_size",
        minimum=len(weights),
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    world = _integer(
        tensor_parallel_world_size,
        "tensor_parallel_world_size",
        minimum=1,
        maximum=vocabulary,
    )
    if vocabulary % world:
        raise LMHeadServiceNumericError("declared vocabulary must divide across ranks")
    raw_indices = _sequence(vocabulary_row_indices, "vocabulary_row_indices")
    if len(raw_indices) != len(weights):
        raise LMHeadServiceNumericError("vocabulary row count must match selected weights")
    indices = tuple(
        _integer(
            index,
            f"vocabulary_row_indices[{position}]",
            minimum=0,
            maximum=vocabulary - 1,
        )
        for position, index in enumerate(raw_indices)
    )
    if any(right <= left for left, right in zip(indices, indices[1:])):
        raise LMHeadServiceNumericError("selected vocabulary rows must be increasing")
    local = vocabulary // world
    counters = MappingProxyType(
        _counter_values(
            input_rows=len(inputs),
            hidden_width=width,
            selected_rows=len(weights),
            declared_vocabulary_size=vocabulary,
            world_size=world,
        )
    )
    return LMHeadServiceNumericResult(
        numeric_profile=SERVICE_NUMERIC_PROFILE,
        vocabulary_row_indices=indices,
        owner_ranks=tuple(index // local for index in indices),
        logits_binary32_codes=_execute(inputs, weights),
        logical_counters=counters,
    )


__all__ = [
    "EXCLUDED_CLAIMS",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_HIDDEN_WIDTH",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_VOCABULARY_SIZE",
    "SERVICE_NUMERIC_PROFILE",
    "LMHeadServiceNumericError",
    "LMHeadServiceNumericResult",
    "execute_selected_vocabulary_rows",
]
