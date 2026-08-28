"""Atomic application of canonical tensor plans to hash-locked payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, BinaryIO

from compiler.canonical.deepseek_v4 import (
    CANONICAL_PLAN_SCHEMA,
    CanonicalTransformError,
    dequantize_fp8_e8m0_matrix_to_bf16,
    dtype_bytes,
    slice_row_major_payload,
    validate_native_mxfp4_pair,
)
from compiler.canonical.plan import build_official_canonical_plan
from compiler.checking.deepseek_v4_application import (
    APPLICATION_SCHEMA,
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.frontend.checkpoint import (
    LockedCheckpointReader,
    validate_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import (
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, write_canonical_json


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,239}$")
_TRANSFORMS = {
    "dequantize_fp8_e8m0_to_bf16_rne",
    "identity",
    "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first",
}


class CanonicalApplicationError(CanonicalTransformError):
    """Raised when a locked payload cannot be applied atomically and exactly."""


def _exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CanonicalApplicationError(f"{label} must be an object")
    observed = set(value)
    if observed != keys:
        raise CanonicalApplicationError(
            f"{label} fields differ: missing={sorted(keys - observed)}, "
            f"unknown={sorted(observed - keys)}"
        )
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CanonicalApplicationError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise CanonicalApplicationError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or _NAME.fullmatch(value) is None:
        raise CanonicalApplicationError(f"{label} is not a safe tensor name")
    return value


def _shape(value: Any, label: str) -> tuple[int, ...]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or not value
        or len(value) > 16
    ):
        raise CanonicalApplicationError(f"{label} must be a nonempty shape")
    return tuple(
        _integer(extent, f"{label}[{index}]", minimum=1)
        for index, extent in enumerate(value)
    )


def _slice(
    value: Any, shape: tuple[int, ...], label: str
) -> dict[str, int] | None:
    if value is None:
        return None
    record = _exact_keys(value, {"axis", "start", "stop"}, label)
    axis = _integer(record["axis"], f"{label}.axis")
    if axis >= len(shape):
        raise CanonicalApplicationError(f"{label}.axis is outside the shape")
    start = _integer(record["start"], f"{label}.start")
    stop = _integer(record["stop"], f"{label}.stop", minimum=1)
    if not start < stop <= shape[axis]:
        raise CanonicalApplicationError(f"{label} bounds are invalid")
    return {"axis": axis, "start": start, "stop": stop}


def _slice_shape(
    shape: tuple[int, ...], descriptor: dict[str, int] | None
) -> tuple[int, ...]:
    if descriptor is None:
        return shape
    result = list(shape)
    result[descriptor["axis"]] = descriptor["stop"] - descriptor["start"]
    return tuple(result)


def _validate_plan_records(
    raw_records: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    if isinstance(raw_records, (str, bytes)) or not isinstance(raw_records, Sequence):
        raise CanonicalApplicationError("plan inputs must be a sequence")
    if not raw_records:
        raise CanonicalApplicationError("plan inputs must not be empty")
    records: list[Mapping[str, Any]] = []
    names: set[str] = set()
    assignment_keys: set[tuple[int, str]] = set()
    for input_index, value in enumerate(raw_records):
        record = _exact_keys(
            value,
            {
                "action",
                "logical_dtype",
                "name",
                "outputs",
                "semantic_role",
                "shape",
                "size_bytes",
                "storage_dtype",
            },
            f"plan.inputs[{input_index}]",
        )
        name = _name(record["name"], f"plan.inputs[{input_index}].name")
        if name in names:
            raise CanonicalApplicationError(f"plan input {name!r} is duplicated")
        names.add(name)
        input_shape = _shape(record["shape"], f"plan.inputs[{input_index}].shape")
        storage_dtype = record["storage_dtype"]
        try:
            input_bytes = math.prod(input_shape) * dtype_bytes(storage_dtype)
        except CanonicalTransformError as exc:
            raise CanonicalApplicationError(str(exc)) from exc
        if _integer(
            record["size_bytes"], f"plan.inputs[{input_index}].size_bytes", minimum=1
        ) != input_bytes:
            raise CanonicalApplicationError(
                f"plan input {name!r} size differs from shape/dtype"
            )
        for field in ("action", "logical_dtype", "semantic_role"):
            if not isinstance(record[field], str) or not record[field]:
                raise CanonicalApplicationError(
                    f"plan.inputs[{input_index}].{field} is invalid"
                )
        outputs = record["outputs"]
        if not isinstance(outputs, list):
            raise CanonicalApplicationError(
                f"plan input {name!r} outputs must be an array"
            )
        ranks: list[int] = []
        for output_index, raw_output in enumerate(outputs):
            output = _exact_keys(
                raw_output,
                {
                    "logical_dtype",
                    "name",
                    "payload_bytes",
                    "rank",
                    "scale_source",
                    "scale_source_slice",
                    "shape",
                    "source_slice",
                    "storage_dtype",
                    "transform",
                },
                f"plan.inputs[{input_index}].outputs[{output_index}]",
            )
            if output["name"] != name:
                raise CanonicalApplicationError("plan output name differs from input")
            rank = _integer(
                output["rank"],
                f"plan.inputs[{input_index}].outputs[{output_index}].rank",
            )
            ranks.append(rank)
            key = (rank, name)
            if key in assignment_keys:
                raise CanonicalApplicationError(
                    f"plan assignment rank/name {key!r} is duplicated"
                )
            assignment_keys.add(key)
            descriptor = _slice(
                output["source_slice"], input_shape, "plan output source_slice"
            )
            output_shape = _shape(output["shape"], "plan output shape")
            if output_shape != _slice_shape(input_shape, descriptor):
                raise CanonicalApplicationError(
                    f"plan output {name!r} shape differs from its source slice"
                )
            output_dtype = output["storage_dtype"]
            try:
                expected_output_bytes = math.prod(output_shape) * dtype_bytes(
                    output_dtype
                )
            except CanonicalTransformError as exc:
                raise CanonicalApplicationError(str(exc)) from exc
            if _integer(output["payload_bytes"], "plan output payload_bytes", minimum=1) != (
                expected_output_bytes
            ):
                raise CanonicalApplicationError(
                    f"plan output {name!r} size differs from shape/dtype"
                )
            transform = output["transform"]
            if transform not in _TRANSFORMS:
                raise CanonicalApplicationError(
                    f"plan output {name!r} has unsupported transform {transform!r}"
                )
            if transform == "identity" and (
                output_dtype != storage_dtype
                or output["logical_dtype"] != record["logical_dtype"]
            ):
                raise CanonicalApplicationError("identity output changes its dtype")
            if transform == "dequantize_fp8_e8m0_to_bf16_rne" and (
                storage_dtype != "F8_E4M3"
                or output_dtype != "BF16"
                or output["logical_dtype"] != "BF16"
                or not isinstance(output["scale_source"], str)
            ):
                raise CanonicalApplicationError("wo_a dequantization metadata differs")
            if (
                transform
                == "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
                and (
                    storage_dtype != "I8"
                    or output_dtype != "U8"
                    or output["logical_dtype"] != record["logical_dtype"]
                    or descriptor is not None
                )
            ):
                raise CanonicalApplicationError("native MXFP4 metadata differs")
            scale_source = output["scale_source"]
            if scale_source is None:
                if output["scale_source_slice"] is not None:
                    raise CanonicalApplicationError(
                        "scale_source_slice exists without scale_source"
                    )
            elif not isinstance(scale_source, str) or not scale_source:
                raise CanonicalApplicationError("plan output scale_source is invalid")
        if ranks != sorted(ranks) or len(ranks) != len(set(ranks)):
            raise CanonicalApplicationError(
                f"plan outputs for {name!r} are not uniquely rank-sorted"
            )
        records.append(record)
    if [record["name"] for record in records] != sorted(names):
        raise CanonicalApplicationError("plan inputs are not name-sorted")
    return tuple(records)


def _dependency_closure(
    records: tuple[Mapping[str, Any], ...],
    requested_names: Sequence[str] | None,
) -> tuple[set[str], tuple[str, ...], tuple[str, ...]]:
    by_name = {record["name"]: record for record in records}
    if requested_names is None:
        requested = set(by_name)
    else:
        if isinstance(requested_names, (str, bytes)) or not isinstance(
            requested_names, Sequence
        ):
            raise CanonicalApplicationError(
                "requested tensor names must be a sequence"
            )
        requested = {
            _name(value, f"requested_names[{index}]")
            for index, value in enumerate(requested_names)
        }
        if not requested:
            raise CanonicalApplicationError("requested tensor names must not be empty")
        missing = sorted(requested - by_name.keys())
        if missing:
            raise CanonicalApplicationError(
                f"requested tensors are absent from the plan: {missing[:8]}"
            )
    selected = set(requested)
    changed = True
    while changed:
        changed = False
        for name in tuple(selected):
            record = by_name[name]
            dependencies = {
                output["scale_source"]
                for output in record["outputs"]
                if output["scale_source"] is not None
            }
            if record["logical_dtype"] == "MXFP4_E2M1_X2" and name.endswith(
                ".weight"
            ):
                dependencies.add(name[: -len(".weight")] + ".scale")
            if record["action"] == "consume_wo_a_scale" and name.endswith(".scale"):
                dependencies.add(name[: -len(".scale")] + ".weight")
            if name.endswith(".scale"):
                weight_name = name[: -len(".scale")] + ".weight"
                weight = by_name.get(weight_name)
                if weight is not None and weight["logical_dtype"] == "MXFP4_E2M1_X2":
                    dependencies.add(weight_name)
            missing_dependencies = sorted(dependencies - by_name.keys())
            if missing_dependencies:
                raise CanonicalApplicationError(
                    f"plan dependencies are absent: {missing_dependencies[:8]}"
                )
            previous = len(selected)
            selected.update(dependencies)
            changed = changed or len(selected) != previous
    return selected, tuple(sorted(requested)), tuple(sorted(selected - requested))


def _artifact_relative(rank: int, name: str) -> str:
    return f"ranks/rank-{rank:03d}/{name}.bin"


class _SliceWriter:
    def __init__(
        self,
        root: Path,
        assignment: Mapping[str, Any],
        source_shape: tuple[int, ...],
        source_dtype: str,
    ):
        relative = assignment["path"]
        self._path = root / relative
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle: BinaryIO = self._path.open("xb")
        self._digest = hashlib.sha256()
        self._written = 0
        self._expected = assignment["payload_bytes"]
        descriptor = assignment["source"]["slice"]
        if descriptor is None:
            self._outer = 1
            self._group_bytes = math.prod(source_shape) * dtype_bytes(source_dtype)
            self._first = 0
            self._length = self._group_bytes
        else:
            axis = descriptor["axis"]
            inner_bytes = math.prod(source_shape[axis + 1 :]) * dtype_bytes(
                source_dtype
            )
            self._outer = math.prod(source_shape[:axis])
            self._group_bytes = source_shape[axis] * inner_bytes
            self._first = descriptor["start"] * inner_bytes
            self._length = (
                descriptor["stop"] - descriptor["start"]
            ) * inner_bytes
        self._outer_index = 0

    def consume(self, chunk: bytes, source_offset: int) -> None:
        chunk_end = source_offset + len(chunk)
        while self._outer_index < self._outer:
            interval_start = (
                self._outer_index * self._group_bytes + self._first
            )
            interval_end = interval_start + self._length
            if interval_start >= chunk_end:
                break
            if interval_end <= source_offset:
                self._outer_index += 1
                continue
            overlap_start = max(interval_start, source_offset)
            overlap_end = min(interval_end, chunk_end)
            selected = chunk[
                overlap_start - source_offset : overlap_end - source_offset
            ]
            self._handle.write(selected)
            self._digest.update(selected)
            self._written += len(selected)
            if interval_end <= chunk_end:
                self._outer_index += 1
            else:
                break

    def finish(self) -> str:
        self._handle.close()
        if self._outer_index != self._outer or self._written != self._expected:
            raise CanonicalApplicationError(
                f"canonical output {self._path.name!r} has incomplete slice coverage"
            )
        return self._digest.hexdigest()

    def abort(self) -> None:
        if not self._handle.closed:
            self._handle.close()


def _read_locked(reader: LockedCheckpointReader, name: str) -> bytes:
    chunks: list[bytes] = []
    reader.consume_tensor_payload(name, chunks.append)
    return b"".join(chunks)


def _write_streamed_assignments(
    root: Path,
    reader: LockedCheckpointReader,
    name: str,
    source_shape: tuple[int, ...],
    source_dtype: str,
    assignments: list[dict[str, Any]],
    payload: bytes | None = None,
) -> list[dict[str, Any]]:
    writers: list[tuple[dict[str, Any], _SliceWriter]] = []
    try:
        for assignment in assignments:
            writers.append(
                (
                    assignment,
                    _SliceWriter(root, assignment, source_shape, source_dtype),
                )
            )
        source_offset = 0

        def distribute(chunk: bytes) -> None:
            nonlocal source_offset
            for _, writer in writers:
                writer.consume(chunk, source_offset)
            source_offset += len(chunk)

        if payload is None:
            reader.consume_tensor_payload(name, distribute)
        else:
            distribute(payload)
        result: list[dict[str, Any]] = []
        for assignment, writer in writers:
            completed = dict(assignment)
            completed["sha256"] = writer.finish()
            result.append(completed)
        return result
    except Exception:
        for _, writer in writers:
            writer.abort()
        raise


def _write_payload_assignment(
    root: Path, assignment: dict[str, Any], payload: bytes
) -> dict[str, Any]:
    if len(payload) != assignment["payload_bytes"]:
        raise CanonicalApplicationError(
            f"transformed output {assignment['name']!r} has {len(payload)} bytes, "
            f"expected {assignment['payload_bytes']}"
        )
    path = root / assignment["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except OSError as exc:
        raise CanonicalApplicationError(
            f"cannot write canonical artifact {assignment['path']!r}: {exc}"
        ) from exc
    result = dict(assignment)
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _assignment_prototypes(
    selected_records: tuple[Mapping[str, Any], ...],
    locked_by_name: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    assignments: list[dict[str, Any]] = []
    by_source: dict[str, list[dict[str, Any]]] = {}
    for record in selected_records:
        name = record["name"]
        source_locked = locked_by_name[name]
        source_shape = tuple(record["shape"])
        for output in record["outputs"]:
            scale_name = output["scale_source"]
            if (
                output["transform"]
                == "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
            ):
                scale_name = name[: -len(".weight")] + ".scale"
            scale_record: dict[str, Any] | None = None
            if scale_name is not None:
                scale_locked = locked_by_name.get(scale_name)
                if scale_locked is None:
                    raise CanonicalApplicationError(
                        f"scale dependency {scale_name!r} is not selected"
                    )
                scale_shape = tuple(scale_locked["shape"])
                scale_slice = _slice(
                    output["scale_source_slice"],
                    scale_shape,
                    f"output scale slice for {name!r}",
                )
                scale_record = {
                    "name": scale_name,
                    "payload_sha256": scale_locked["payload_sha256"],
                    "shape": list(scale_shape),
                    "slice": scale_slice,
                    "storage_dtype": scale_locked["dtype"],
                }
            source_slice = _slice(
                output["source_slice"], source_shape, f"output source slice for {name!r}"
            )
            assignment: dict[str, Any] = {
                "logical_dtype": output["logical_dtype"],
                "name": name,
                "path": _artifact_relative(output["rank"], name),
                "payload_bytes": output["payload_bytes"],
                "rank": output["rank"],
                "scale_source": scale_record,
                "sha256": "0" * 64,
                "shape": list(output["shape"]),
                "source": {
                    "name": name,
                    "payload_sha256": source_locked["payload_sha256"],
                    "shape": list(source_shape),
                    "slice": source_slice,
                    "storage_dtype": source_locked["dtype"],
                },
                "storage_dtype": output["storage_dtype"],
                "transform": output["transform"],
            }
            assignments.append(assignment)
            by_source.setdefault(name, []).append(assignment)
    return assignments, by_source


def _status(evidence_scope: str, complete_plan: bool) -> str:
    if evidence_scope == "official_checkpoint":
        if complete_plan:
            return "complete_official_transform_application"
        return "partial_official_transform_application_not_release_evidence"
    if evidence_scope == "development_fixture":
        return "development_fixture_application_not_release_evidence"
    raise CanonicalApplicationError(f"unsupported evidence scope {evidence_scope!r}")


def _apply_canonical_plan_records(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    plan_id: str,
    plan_schema: str,
    plan_inputs: Sequence[Mapping[str, Any]],
    expected_plan_input_count: int,
    output: Path,
    requested_names: Sequence[str] | None,
    evidence_scope: str,
) -> dict[str, Any]:
    validate_checkpoint_lock(lock)
    plan_id = _digest(plan_id, "plan_id")
    if not isinstance(plan_schema, str) or not plan_schema:
        raise CanonicalApplicationError("plan_schema must be a nonempty string")
    expected_plan_input_count = _integer(
        expected_plan_input_count, "expected_plan_input_count", minimum=1
    )
    records = _validate_plan_records(plan_inputs)
    if len(records) > expected_plan_input_count:
        raise CanonicalApplicationError(
            "plan inputs exceed expected_plan_input_count"
        )
    selected_names, requested, dependencies = _dependency_closure(
        records, requested_names
    )
    selected_records = tuple(
        record for record in records if record["name"] in selected_names
    )
    complete_plan = (
        len(records) == expected_plan_input_count
        and len(selected_records) == expected_plan_input_count
    )

    try:
        output = Path(output)
    except TypeError as exc:
        raise CanonicalApplicationError("output must be a filesystem path") from exc
    if not output.name or output.name in {".", ".."}:
        raise CanonicalApplicationError("output must name a specific directory")
    if output.exists():
        raise CanonicalApplicationError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with LockedCheckpointReader(snapshot, lock) as reader:
        locked_by_name: dict[str, dict[str, Any]] = {}
        input_manifest: list[dict[str, Any]] = []
        for record in selected_records:
            locked = reader.tensor_record(record["name"])
            if (
                locked["dtype"] != record["storage_dtype"]
                or locked["shape"] != record["shape"]
                or locked["size_bytes"] != record["size_bytes"]
            ):
                raise CanonicalApplicationError(
                    f"plan input {record['name']!r} differs from its checkpoint lock"
                )
            locked_by_name[record["name"]] = locked
            input_manifest.append(
                {
                    "action": record["action"],
                    "logical_dtype": record["logical_dtype"],
                    "name": record["name"],
                    "payload_sha256": locked["payload_sha256"],
                    "shape": list(record["shape"]),
                    "size_bytes": record["size_bytes"],
                    "storage_dtype": record["storage_dtype"],
                }
            )
        prototypes, prototypes_by_source = _assignment_prototypes(
            selected_records, locked_by_name
        )
        output_payload_bytes = sum(
            assignment["payload_bytes"] for assignment in prototypes
        )
        free_bytes = shutil.disk_usage(output.parent).free
        reserve = min(max(output_payload_bytes // 100, 1024 * 1024), 4 << 30)
        if free_bytes < output_payload_bytes + reserve:
            raise CanonicalApplicationError(
                f"canonical application needs {output_payload_bytes + reserve} "
                f"free bytes including reserve, but {free_bytes} are available"
            )

        temporary = Path(
            tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent)
        )
        try:
            dependency_names = {
                assignment["scale_source"]["name"]
                for assignment in prototypes
                if assignment["scale_source"] is not None
            }
            scale_cache: dict[str, bytes] = {}
            completed_assignments: list[dict[str, Any]] = []
            for record in selected_records:
                name = record["name"]
                source_assignments = prototypes_by_source.get(name, [])
                transforms = {
                    assignment["transform"] for assignment in source_assignments
                }
                needs_bytes = name in dependency_names or bool(
                    transforms
                    & {
                        "dequantize_fp8_e8m0_to_bf16_rne",
                        "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first",
                    }
                )
                payload: bytes | None = None
                if needs_bytes:
                    payload = _read_locked(reader, name)
                    if name in dependency_names:
                        scale_cache[name] = payload

                if not source_assignments:
                    if payload is None:
                        reader.consume_tensor_payload(name, lambda _: None)
                    continue
                if transforms <= {"identity"}:
                    completed_assignments.extend(
                        _write_streamed_assignments(
                            temporary,
                            reader,
                            name,
                            tuple(record["shape"]),
                            record["storage_dtype"],
                            source_assignments,
                            payload,
                        )
                    )
                    continue
                if transforms == {"dequantize_fp8_e8m0_to_bf16_rne"}:
                    if payload is None:
                        raise RuntimeError("dequantization payload was not loaded")
                    scale_names = {
                        assignment["scale_source"]["name"]
                        for assignment in source_assignments
                    }
                    if len(scale_names) != 1:
                        raise CanonicalApplicationError(
                            "dequantization outputs do not share one scale source"
                        )
                    scale_name = next(iter(scale_names))
                    scale_payload = scale_cache.get(scale_name)
                    if scale_payload is None:
                        raise CanonicalApplicationError(
                            f"scale source {scale_name!r} was not consumed first"
                        )
                    scale_locked = locked_by_name[scale_name]
                    for assignment in source_assignments:
                        source_slice = assignment["source"]["slice"]
                        scale_slice = assignment["scale_source"]["slice"]
                        sliced_weight, weight_shape = slice_row_major_payload(
                            payload,
                            record["shape"],
                            record["storage_dtype"],
                            **source_slice,
                        )
                        sliced_scale, scale_shape = slice_row_major_payload(
                            scale_payload,
                            scale_locked["shape"],
                            scale_locked["dtype"],
                            **scale_slice,
                        )
                        transformed = dequantize_fp8_e8m0_matrix_to_bf16(
                            sliced_weight,
                            sliced_scale,
                            weight_shape,
                            scale_shape,
                        )
                        completed_assignments.append(
                            _write_payload_assignment(
                                temporary, assignment, transformed
                            )
                        )
                    scale_cache.pop(scale_name, None)
                    continue
                if transforms == {
                    "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
                }:
                    if payload is None:
                        raise RuntimeError("native MXFP4 payload was not loaded")
                    scale_names = {
                        assignment["scale_source"]["name"]
                        for assignment in source_assignments
                    }
                    if len(scale_names) != 1:
                        raise CanonicalApplicationError(
                            "native MXFP4 outputs do not share one scale source"
                        )
                    scale_name = next(iter(scale_names))
                    scale_payload = scale_cache.get(scale_name)
                    if scale_payload is None:
                        raise CanonicalApplicationError(
                            f"scale source {scale_name!r} was not consumed first"
                        )
                    scale_locked = locked_by_name[scale_name]
                    validate_native_mxfp4_pair(
                        payload,
                        scale_payload,
                        record["shape"],
                        scale_locked["shape"],
                    )
                    completed_assignments.extend(
                        _write_streamed_assignments(
                            temporary,
                            reader,
                            name,
                            tuple(record["shape"]),
                            record["storage_dtype"],
                            source_assignments,
                            payload,
                        )
                    )
                    scale_cache.pop(scale_name, None)
                    continue
                raise CanonicalApplicationError(
                    f"source {name!r} mixes incompatible transforms"
                )
            if scale_cache:
                raise CanonicalApplicationError(
                    f"unused scale dependencies remain: {sorted(scale_cache)[:8]}"
                )
            if reader.accessed_tensor_names != tuple(
                record["name"] for record in selected_records
            ):
                raise CanonicalApplicationError(
                    "application did not consume every selected input"
                )

            body: dict[str, Any] = {
                "assignments": completed_assignments,
                "coverage": {
                    "consumed_input_count": len(input_manifest),
                    "consumed_input_payload_bytes": sum(
                        record["size_bytes"] for record in input_manifest
                    ),
                    "output_assignment_count": len(completed_assignments),
                    "output_payload_bytes": sum(
                        record["payload_bytes"] for record in completed_assignments
                    ),
                },
                "evidence_scope": evidence_scope,
                "inputs": input_manifest,
                "plan": {
                    "expected_input_count": expected_plan_input_count,
                    "plan_id": plan_id,
                    "schema": plan_schema,
                },
                "schema": APPLICATION_SCHEMA,
                "selection": {
                    "complete_plan": complete_plan,
                    "dependency_input_names": list(dependencies),
                    "requested_input_names": list(requested),
                },
                "source": {
                    "checkpoint_lock_id": lock["lock_id"],
                    "repository": lock["source"]["repository"],
                    "revision": lock["source"]["revision"],
                },
                "status": _status(evidence_scope, complete_plan),
            }
            body["application_id"] = hashlib.sha256(
                canonical_json_bytes(body)
            ).hexdigest()
            write_canonical_json(temporary / MANIFEST_FILENAME, body)
        except Exception:
            shutil.rmtree(temporary)
            raise

    try:
        verification = verify_canonical_application(temporary, snapshot, lock)
        write_canonical_json(temporary / VERIFICATION_FILENAME, verification)
        temporary.rename(output)
    except Exception:
        shutil.rmtree(temporary)
        raise
    return {"manifest": body, "verification": verification}


def apply_canonical_plan_records(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    plan_id: str,
    plan_schema: str,
    plan_inputs: Sequence[Mapping[str, Any]],
    output: Path,
    requested_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Apply a complete development fixture through the production machinery."""

    return _apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=plan_id,
        plan_schema=plan_schema,
        plan_inputs=plan_inputs,
        expected_plan_input_count=len(plan_inputs),
        output=output,
        requested_names=requested_names,
        evidence_scope="development_fixture",
    )


def apply_official_canonical_plan(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    plan: Mapping[str, Any],
    output: Path,
    requested_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Apply the exact official V4 plan, fully or as marked partial evidence."""

    validate_official_checkpoint_lock(lock, load_official_config())
    if not isinstance(plan, Mapping):
        raise CanonicalApplicationError("official canonical plan must be an object")
    profile = plan.get("profile")
    if not isinstance(profile, Mapping):
        raise CanonicalApplicationError("official canonical plan lacks its profile")
    model_parallel = profile.get("model_parallel")
    expected = build_official_canonical_plan(model_parallel=model_parallel)
    if dict(plan) != expected:
        raise CanonicalApplicationError(
            "canonical plan differs from the deterministic official plan"
        )
    return _apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=expected["plan_id"],
        plan_schema=CANONICAL_PLAN_SCHEMA,
        plan_inputs=expected["inputs"],
        expected_plan_input_count=len(expected["inputs"]),
        output=output,
        requested_names=requested_names,
        evidence_scope="official_checkpoint",
    )


__all__ = [
    "CanonicalApplicationError",
    "apply_canonical_plan_records",
    "apply_official_canonical_plan",
]
