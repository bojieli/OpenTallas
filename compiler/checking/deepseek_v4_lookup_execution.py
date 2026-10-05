"""Independent checkpoint differential for the DeepSeek V4 lookup engine.

This checker does not import the lookup service engine.  It streams the original
hash-locked checkpoint tensors, extracts only requested rows, constructs HC
copies through the qualified reference operator, and compares the persisted
service result bit-for-bit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from pathlib import Path
import struct
from typing import Any

from compiler.frontend.checkpoint import (
    LockedCheckpointReader,
    validate_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import MODEL_ID
from compiler.ir.model import canonical_json_bytes, load_strict_json
from runtime.reference.structural import hc_expand_bf16


DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_lookup_differential.v1"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_lookup_deployment.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_lookup_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_lookup_result.v1"


class DeepSeekV4LookupDifferentialError(RuntimeError):
    """Raised when a persisted lookup execution differs from its checkpoint."""


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4LookupDifferentialError(f"cannot load {label}: {exc}") from exc


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4LookupDifferentialError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _integer(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">= {minimum}"
        raise DeepSeekV4LookupDifferentialError(
            f"{label} must be an integer in {bound}"
        )
    return value


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _dimensions(semantic: Mapping[str, Any]) -> dict[str, int]:
    dimensions = semantic.get("dimensions")
    if not isinstance(dimensions, Mapping):
        raise DeepSeekV4LookupDifferentialError("lookup semantic dimensions are absent")
    expected = {
        "expert_count",
        "hc_multiplier",
        "hidden_size",
        "model_parallel",
        "route_top_k",
        "vocabulary_size",
    }
    _exact_keys(dimensions, expected, "lookup semantic dimensions")
    return {
        key: _integer(dimensions[key], f"dimensions.{key}", minimum=1)
        for key in expected
    }


def _parse_request(
    request: Mapping[str, Any],
    *,
    build_id: str,
    vocabulary_size: int,
) -> tuple[tuple[tuple[int, ...], ...], str]:
    _exact_keys(
        request,
        {"build_id", "model_id", "schema", "token_ids"},
        "lookup request",
    )
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != build_id
    ):
        raise DeepSeekV4LookupDifferentialError("lookup request identity differs")
    raw_batches = request["token_ids"]
    if (
        isinstance(raw_batches, (str, bytes, bytearray))
        or not isinstance(raw_batches, Sequence)
        or not raw_batches
    ):
        raise DeepSeekV4LookupDifferentialError(
            "lookup token IDs must be a non-empty rank-2 array"
        )
    result: list[tuple[int, ...]] = []
    sequence_length: int | None = None
    for batch_index, raw_batch in enumerate(raw_batches):
        if (
            isinstance(raw_batch, (str, bytes, bytearray))
            or not isinstance(raw_batch, Sequence)
            or not raw_batch
        ):
            raise DeepSeekV4LookupDifferentialError(
                f"token_ids[{batch_index}] must be a non-empty array"
            )
        if sequence_length is None:
            sequence_length = len(raw_batch)
        elif len(raw_batch) != sequence_length:
            raise DeepSeekV4LookupDifferentialError(
                "lookup token IDs must be rectangular"
            )
        result.append(
            tuple(
                _integer(
                    token,
                    f"token_ids[{batch_index}][{position}]",
                    maximum=vocabulary_size - 1,
                )
                for position, token in enumerate(raw_batch)
            )
        )
    return tuple(result), _sha256_json(dict(request))


class _RowCollector:
    """Collect selected fixed-width rows from a sequential tensor stream."""

    def __init__(self, row_indices: Sequence[int], row_bytes: int):
        self._row_bytes = row_bytes
        self._rows = tuple(sorted(set(row_indices)))
        self._buffers = {row: bytearray(row_bytes) for row in self._rows}
        self._filled = {row: 0 for row in self._rows}
        self._offset = 0

    def consume(self, chunk: bytes) -> None:
        chunk_start = self._offset
        chunk_stop = chunk_start + len(chunk)
        for row in self._rows:
            row_start = row * self._row_bytes
            row_stop = row_start + self._row_bytes
            overlap_start = max(chunk_start, row_start)
            overlap_stop = min(chunk_stop, row_stop)
            if overlap_start >= overlap_stop:
                continue
            source_start = overlap_start - chunk_start
            destination_start = overlap_start - row_start
            length = overlap_stop - overlap_start
            self._buffers[row][destination_start : destination_start + length] = chunk[
                source_start : source_start + length
            ]
            self._filled[row] += length
        self._offset = chunk_stop

    def finish(self, expected_payload_bytes: int) -> dict[int, bytes]:
        if self._offset != expected_payload_bytes:
            raise DeepSeekV4LookupDifferentialError(
                "locked tensor stream length differs from its declared payload"
            )
        incomplete = [
            row for row, filled in self._filled.items() if filled != self._row_bytes
        ]
        if incomplete:
            raise DeepSeekV4LookupDifferentialError(
                f"locked tensor stream did not contain requested rows {incomplete}"
            )
        return {row: bytes(payload) for row, payload in self._buffers.items()}


def _checkpoint_rows(
    reader: LockedCheckpointReader,
    tensor_name: str,
    tokens: tuple[tuple[int, ...], ...],
    *,
    row_bytes: int,
    expected_dtype: str,
    expected_shape: list[int],
) -> tuple[dict[int, bytes], dict[str, Any]]:
    flattened = tuple(token for batch in tokens for token in batch)
    collector = _RowCollector(flattened, row_bytes)
    record = reader.consume_tensor_payload(tensor_name, collector.consume)
    if record["dtype"] != expected_dtype or record["shape"] != expected_shape:
        raise DeepSeekV4LookupDifferentialError(
            f"locked tensor {tensor_name!r} metadata differs"
        )
    rows = collector.finish(record["size_bytes"])
    return rows, record


def _parse_tensor3(
    value: Any,
    shape: tuple[int, int, int],
    label: str,
    *,
    maximum: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    if not isinstance(value, list) or len(value) != shape[0]:
        raise DeepSeekV4LookupDifferentialError(f"{label} batch extent differs")
    result: list[tuple[tuple[int, ...], ...]] = []
    for batch_index, raw_batch in enumerate(value):
        if not isinstance(raw_batch, list) or len(raw_batch) != shape[1]:
            raise DeepSeekV4LookupDifferentialError(
                f"{label}[{batch_index}] sequence extent differs"
            )
        batch: list[tuple[int, ...]] = []
        for position, raw_vector in enumerate(raw_batch):
            if not isinstance(raw_vector, list) or len(raw_vector) != shape[2]:
                raise DeepSeekV4LookupDifferentialError(
                    f"{label}[{batch_index}][{position}] vector extent differs"
                )
            batch.append(
                tuple(
                    _integer(
                        element,
                        f"{label}[{batch_index}][{position}][{column}]",
                        maximum=maximum,
                    )
                    for column, element in enumerate(raw_vector)
                )
            )
        result.append(tuple(batch))
    return tuple(result)


def _parse_tensor4(
    value: Any,
    shape: tuple[int, int, int, int],
    label: str,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    if not isinstance(value, list) or len(value) != shape[0]:
        raise DeepSeekV4LookupDifferentialError(f"{label} batch extent differs")
    result: list[tuple[tuple[tuple[int, ...], ...], ...]] = []
    for batch_index, raw_batch in enumerate(value):
        if not isinstance(raw_batch, list) or len(raw_batch) != shape[1]:
            raise DeepSeekV4LookupDifferentialError(
                f"{label}[{batch_index}] sequence extent differs"
            )
        batch: list[tuple[tuple[int, ...], ...]] = []
        for position, raw_copies in enumerate(raw_batch):
            if not isinstance(raw_copies, list) or len(raw_copies) != shape[2]:
                raise DeepSeekV4LookupDifferentialError(
                    f"{label}[{batch_index}][{position}] HC extent differs"
                )
            copies: list[tuple[int, ...]] = []
            for copy_index, raw_vector in enumerate(raw_copies):
                if not isinstance(raw_vector, list) or len(raw_vector) != shape[3]:
                    raise DeepSeekV4LookupDifferentialError(
                        f"{label}[{batch_index}][{position}][{copy_index}] width differs"
                    )
                copies.append(
                    tuple(
                        _integer(
                            element,
                            (
                                f"{label}[{batch_index}][{position}]"
                                f"[{copy_index}][{column}]"
                            ),
                            maximum=(1 << 16) - 1,
                        )
                        for column, element in enumerate(raw_vector)
                    )
                )
            batch.append(tuple(copies))
        result.append(tuple(batch))
    return tuple(result)


def _parse_outputs(
    result: Mapping[str, Any],
    *,
    batch_size: int,
    sequence_length: int,
    dimensions: Mapping[str, int],
) -> dict[str, Any]:
    raw_outputs = result.get("outputs")
    if not isinstance(raw_outputs, list) or len(raw_outputs) != 3:
        raise DeepSeekV4LookupDifferentialError("lookup result outputs differ")
    expected_metadata = [
        (
            "embedding_bf16_codes",
            "BF16_BITS",
            [batch_size, sequence_length, dimensions["hidden_size"]],
        ),
        (
            "hc_hidden_bf16_codes",
            "BF16_BITS",
            [
                batch_size,
                sequence_length,
                dimensions["hc_multiplier"],
                dimensions["hidden_size"],
            ],
        ),
        (
            "expert_ids",
            "I64",
            [batch_size, sequence_length, dimensions["route_top_k"]],
        ),
    ]
    by_id: dict[str, Any] = {}
    for index, (raw, metadata) in enumerate(zip(raw_outputs, expected_metadata, strict=True)):
        if not isinstance(raw, Mapping):
            raise DeepSeekV4LookupDifferentialError(
                f"lookup output {index} is not an object"
            )
        _exact_keys(raw, {"dtype", "id", "shape", "values"}, f"lookup output {index}")
        tensor_id, dtype, shape = metadata
        if (raw["id"], raw["dtype"], raw["shape"]) != (tensor_id, dtype, shape):
            raise DeepSeekV4LookupDifferentialError(
                f"lookup output {index} metadata differs"
            )
        if tensor_id == "embedding_bf16_codes":
            parsed = _parse_tensor3(
                raw["values"], tuple(shape), tensor_id, maximum=(1 << 16) - 1
            )
        elif tensor_id == "hc_hidden_bf16_codes":
            parsed = _parse_tensor4(raw["values"], tuple(shape), tensor_id)
        else:
            parsed = _parse_tensor3(
                raw["values"],
                tuple(shape),
                tensor_id,
                maximum=dimensions["expert_count"] - 1,
            )
        by_id[tensor_id] = parsed
    return by_id


def _expected_counters(dimensions: Mapping[str, int], token_count: int) -> dict[str, int]:
    hidden = dimensions["hidden_size"]
    multiplier = dimensions["hc_multiplier"]
    route_top_k = dimensions["route_top_k"]
    return {
        "bf16_codes_copied": token_count * multiplier * hidden,
        "completion_events": 1,
        "logical_activation_bytes_read": token_count * hidden * 2,
        "logical_activation_bytes_written": token_count
        * (hidden * 2 + multiplier * hidden * 2 + route_top_k * 8),
        "logical_input_bytes_read": token_count * 16,
        "logical_rom_bytes_read": token_count * (hidden * 2 + route_top_k * 8),
        "micro_ops_executed": 4,
        "rom_lookup_rows": token_count * 2,
        "semantic_operations_executed": 3,
    }


def verify_deepseek_v4_lookup_execution(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    deployment_root: Path,
    request_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    """Compare persisted service outputs directly with locked checkpoint rows."""

    validate_checkpoint_lock(lock)
    deployment_root = Path(deployment_root).resolve()
    manifest = _load_json(
        deployment_root / "deployment_manifest.json", "lookup deployment manifest"
    )
    semantic = _load_json(deployment_root / "model.ir.json", "lookup semantic IR")
    request = _load_json(Path(request_path), "lookup request")
    result = _load_json(Path(result_path), "lookup result")
    if (
        manifest.get("schema") != DEPLOYMENT_SCHEMA
        or manifest.get("model_id") != MODEL_ID
        or semantic.get("schema") != "opentallas.deepseek_v4_lookup_slice.v1"
        or semantic.get("model_id") != MODEL_ID
    ):
        raise DeepSeekV4LookupDifferentialError(
            "lookup deployment or semantic identity differs"
        )
    dimensions = _dimensions(semantic)
    source = semantic.get("source")
    if (
        not isinstance(source, Mapping)
        or source.get("checkpoint_lock_id") != lock["lock_id"]
        or source.get("application_id") != manifest.get("source_application_id")
    ):
        raise DeepSeekV4LookupDifferentialError(
            "lookup semantic source differs from checkpoint or deployment"
        )
    build_id = manifest.get("build_id")
    if not isinstance(build_id, str):
        raise DeepSeekV4LookupDifferentialError("lookup deployment build_id is absent")
    tokens, request_sha256 = _parse_request(
        request,
        build_id=build_id,
        vocabulary_size=dimensions["vocabulary_size"],
    )
    _exact_keys(
        result,
        {
            "build_id",
            "counter_reconciliation",
            "counters",
            "deployment_status",
            "evidence_scope",
            "execution_scope",
            "model_id",
            "outputs",
            "request_sha256",
            "schema",
            "source_application_status",
            "status",
        },
        "lookup result",
    )
    if (
        result["schema"] != RESULT_SCHEMA
        or result["model_id"] != MODEL_ID
        or result["build_id"] != build_id
        or result["request_sha256"] != request_sha256
        or result["status"] != "pass"
        or result["counter_reconciliation"] != "exact"
        or result["execution_scope"] != "three_operator_real_payload_slice_only"
        or result["source_application_status"] != source.get("application_status")
        or result["evidence_scope"] != source.get("evidence_scope")
    ):
        raise DeepSeekV4LookupDifferentialError("lookup result identity differs")
    token_count = sum(len(batch) for batch in tokens)
    expected_counters = _expected_counters(dimensions, token_count)
    if result["counters"] != expected_counters:
        raise DeepSeekV4LookupDifferentialError(
            "lookup result counters differ from independent accounting"
        )
    observed = _parse_outputs(
        result,
        batch_size=len(tokens),
        sequence_length=len(tokens[0]),
        dimensions=dimensions,
    )

    with LockedCheckpointReader(snapshot, lock) as reader:
        embedding_rows, embedding_record = _checkpoint_rows(
            reader,
            "embed.weight",
            tokens,
            row_bytes=dimensions["hidden_size"] * 2,
            expected_dtype="BF16",
            expected_shape=[
                dimensions["vocabulary_size"],
                dimensions["hidden_size"],
            ],
        )
        route_rows, route_record = _checkpoint_rows(
            reader,
            "layers.0.ffn.gate.tid2eid",
            tokens,
            row_bytes=dimensions["route_top_k"] * 8,
            expected_dtype="I64",
            expected_shape=[
                dimensions["vocabulary_size"],
                dimensions["route_top_k"],
            ],
        )
    embedding_decoder = struct.Struct(f"<{dimensions['hidden_size']}H")
    route_decoder = struct.Struct(f"<{dimensions['route_top_k']}q")
    expected_embedding = tuple(
        tuple(embedding_decoder.unpack(embedding_rows[token]) for token in batch)
        for batch in tokens
    )
    expected_hc = hc_expand_bf16(
        expected_embedding, dimensions["hc_multiplier"]
    )
    expected_routes = tuple(
        tuple(route_decoder.unpack(route_rows[token]) for token in batch)
        for batch in tokens
    )
    expected_outputs = {
        "embedding_bf16_codes": expected_embedding,
        "expert_ids": expected_routes,
        "hc_hidden_bf16_codes": expected_hc,
    }
    comparisons: list[dict[str, Any]] = []
    shapes = {
        "embedding_bf16_codes": [
            len(tokens),
            len(tokens[0]),
            dimensions["hidden_size"],
        ],
        "hc_hidden_bf16_codes": [
            len(tokens),
            len(tokens[0]),
            dimensions["hc_multiplier"],
            dimensions["hidden_size"],
        ],
        "expert_ids": [
            len(tokens),
            len(tokens[0]),
            dimensions["route_top_k"],
        ],
    }
    for tensor_id in (
        "embedding_bf16_codes",
        "hc_hidden_bf16_codes",
        "expert_ids",
    ):
        expected = expected_outputs[tensor_id]
        actual = observed[tensor_id]
        if actual != expected:
            raise DeepSeekV4LookupDifferentialError(
                f"lookup output {tensor_id!r} differs from locked checkpoint semantics"
            )
        digest = _sha256_json(actual)
        comparisons.append(
            {
                "element_count": math.prod(shapes[tensor_id]),
                "expected_sha256": _sha256_json(expected),
                "observed_sha256": digest,
                "output": tensor_id,
                "shape": shapes[tensor_id],
                "status": "exact",
            }
        )
    tensor_sources = []
    for record in (embedding_record, route_record):
        tensor_sources.append(
            {
                "dtype": record["dtype"],
                "name": record["name"],
                "payload_sha256": record["payload_sha256"],
                "shape": record["shape"],
                "size_bytes": record["size_bytes"],
            }
        )
    body: dict[str, Any] = {
        "build_id": build_id,
        "checkpoint_lock_id": lock["lock_id"],
        "claim_boundary": (
            "Exact three-operator selected-row differential only; this is not "
            "a transformer block or full-model validation."
        ),
        "comparisons": comparisons,
        "counters": expected_counters,
        "model_id": MODEL_ID,
        "request_sha256": request_sha256,
        "schema": DIFFERENTIAL_SCHEMA,
        "source_tensors": tensor_sources,
        "status": "exact_locked_checkpoint_differential",
        "token_count": token_count,
        "token_ids_sha256": _sha256_json(tokens),
    }
    body["differential_id"] = _sha256_json(body)
    return body


__all__ = [
    "DIFFERENTIAL_SCHEMA",
    "DeepSeekV4LookupDifferentialError",
    "verify_deepseek_v4_lookup_execution",
]
