"""Independent replay checker for canonical checkpoint applications."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from pathlib import Path
import re
from typing import Any, BinaryIO

from compiler.checking.deepseek_v4_transforms import (
    DeepSeekV4TransformCheckError,
    verify_dequantized_fp8_e8m0_bf16,
    verify_native_mxfp4_identity,
)
from compiler.frontend.checkpoint import LockedCheckpointReader
from compiler.ir.model import canonical_json_bytes, load_strict_json


APPLICATION_SCHEMA = "opentallas.canonical_application.v1"
APPLICATION_CHECK_SCHEMA = "opentallas.canonical_application_check.v1"
MANIFEST_FILENAME = "canonical_application.json"
VERIFICATION_FILENAME = "canonical_verification.json"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,239}$")
_DTYPE_BYTES = {
    "BF16": 2,
    "BOOL": 1,
    "F16": 2,
    "F32": 4,
    "F64": 8,
    "F8_E4M3": 1,
    "F8_E5M2": 1,
    "F8_E8M0": 1,
    "I16": 2,
    "I32": 4,
    "I64": 8,
    "I8": 1,
    "U16": 2,
    "U32": 4,
    "U64": 8,
    "U8": 1,
}
_TRANSFORMS = {
    "dequantize_fp8_e8m0_to_bf16_rne",
    "identity",
    "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first",
}


class DeepSeekV4ApplicationCheckError(RuntimeError):
    """Raised when emitted canonical artifacts fail independent replay."""


def _exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4ApplicationCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != keys:
        raise DeepSeekV4ApplicationCheckError(
            f"{label} fields differ: missing={sorted(keys - observed)}, "
            f"unknown={sorted(observed - keys)}"
        )
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DeepSeekV4ApplicationCheckError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4ApplicationCheckError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or _NAME.fullmatch(value) is None:
        raise DeepSeekV4ApplicationCheckError(f"{label} is not a safe tensor name")
    return value


def _shape(value: Any, label: str) -> tuple[int, ...]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or not value
        or len(value) > 16
    ):
        raise DeepSeekV4ApplicationCheckError(f"{label} must be a nonempty shape")
    return tuple(
        _integer(extent, f"{label}[{index}]", minimum=1)
        for index, extent in enumerate(value)
    )


def _slice(value: Any, shape: tuple[int, ...], label: str) -> dict[str, int] | None:
    if value is None:
        return None
    record = _exact_keys(value, {"axis", "start", "stop"}, label)
    axis = _integer(record["axis"], f"{label}.axis")
    if axis >= len(shape):
        raise DeepSeekV4ApplicationCheckError(f"{label}.axis is outside the shape")
    start = _integer(record["start"], f"{label}.start")
    stop = _integer(record["stop"], f"{label}.stop", minimum=1)
    if not start < stop <= shape[axis]:
        raise DeepSeekV4ApplicationCheckError(f"{label} bounds are invalid")
    return {"axis": axis, "start": start, "stop": stop}


def _slice_shape(
    shape: tuple[int, ...], descriptor: dict[str, int] | None
) -> tuple[int, ...]:
    if descriptor is None:
        return shape
    result = list(shape)
    result[descriptor["axis"]] = descriptor["stop"] - descriptor["start"]
    return tuple(result)


def _safe_artifact_path(root: Path, value: Any, label: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or "\\" in value
    ):
        raise DeepSeekV4ApplicationCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4ApplicationCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4ApplicationCheckError(f"{label} is not canonical POSIX")
    path = root / relative
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4ApplicationCheckError(
                f"{label} traverses a symlinked directory"
            )
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4ApplicationCheckError(
            f"{label} escapes the application directory"
        ) from exc
    if path.is_symlink() or not path.is_file():
        raise DeepSeekV4ApplicationCheckError(
            f"{label} does not name a regular non-symlink artifact"
        )
    return path


def _read_output(path: Path, size: int, digest: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4ApplicationCheckError(
            f"cannot read canonical artifact {path.name!r}: {exc}"
        ) from exc
    if len(payload) != size:
        raise DeepSeekV4ApplicationCheckError(
            f"canonical artifact {path.name!r} has {len(payload)} bytes, expected {size}"
        )
    if hashlib.sha256(payload).hexdigest() != digest:
        raise DeepSeekV4ApplicationCheckError(
            f"canonical artifact {path.name!r} differs from its manifest hash"
        )
    return payload


def _read_locked(reader: LockedCheckpointReader, name: str) -> bytes:
    chunks: list[bytes] = []
    reader.consume_tensor_payload(name, chunks.append)
    return b"".join(chunks)


def _independent_slice(
    payload: bytes,
    shape: tuple[int, ...],
    dtype: str,
    descriptor: dict[str, int] | None,
) -> tuple[bytes, tuple[int, ...]]:
    item_bytes = _DTYPE_BYTES[dtype]
    if len(payload) != math.prod(shape) * item_bytes:
        raise DeepSeekV4ApplicationCheckError("locked source size differs from shape")
    if descriptor is None:
        return payload, shape
    axis = descriptor["axis"]
    start = descriptor["start"]
    stop = descriptor["stop"]
    outer = math.prod(shape[:axis])
    inner_bytes = math.prod(shape[axis + 1 :]) * item_bytes
    group_bytes = shape[axis] * inner_bytes
    selected_bytes = (stop - start) * inner_bytes
    result = bytearray(outer * selected_bytes)
    destination = 0
    for outer_index in range(outer):
        source = outer_index * group_bytes + start * inner_bytes
        result[destination : destination + selected_bytes] = payload[
            source : source + selected_bytes
        ]
        destination += selected_bytes
    return bytes(result), _slice_shape(shape, descriptor)


class _SliceComparator:
    def __init__(
        self,
        path: Path,
        expected_sha256: str,
        expected_bytes: int,
        source_shape: tuple[int, ...],
        source_dtype: str,
        descriptor: dict[str, int] | None,
    ):
        try:
            observed_size = path.stat().st_size
            self._handle: BinaryIO = path.open("rb")
        except OSError as exc:
            raise DeepSeekV4ApplicationCheckError(
                f"cannot open canonical artifact {path.name!r}: {exc}"
            ) from exc
        if observed_size != expected_bytes:
            self._handle.close()
            raise DeepSeekV4ApplicationCheckError(
                f"canonical artifact {path.name!r} has {observed_size} bytes, "
                f"expected {expected_bytes}"
            )
        self._path = path
        self._expected_sha256 = expected_sha256
        self._expected_bytes = expected_bytes
        self._digest = hashlib.sha256()
        self._checked_bytes = 0
        if descriptor is None:
            self._outer = 1
            self._group_bytes = math.prod(source_shape) * _DTYPE_BYTES[source_dtype]
            self._first = 0
            self._length = self._group_bytes
        else:
            axis = descriptor["axis"]
            inner_bytes = (
                math.prod(source_shape[axis + 1 :]) * _DTYPE_BYTES[source_dtype]
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
            expected = chunk[
                overlap_start - source_offset : overlap_end - source_offset
            ]
            observed = self._handle.read(len(expected))
            if observed != expected:
                self._handle.close()
                raise DeepSeekV4ApplicationCheckError(
                    f"canonical artifact {self._path.name!r} differs at output "
                    f"byte {self._checked_bytes}"
                )
            self._digest.update(observed)
            self._checked_bytes += len(observed)
            if interval_end <= chunk_end:
                self._outer_index += 1
            else:
                break

    def finish(self) -> str:
        trailing = self._handle.read(1)
        self._handle.close()
        if (
            self._outer_index != self._outer
            or self._checked_bytes != self._expected_bytes
            or trailing
        ):
            raise DeepSeekV4ApplicationCheckError(
                f"canonical artifact {self._path.name!r} has incomplete slice coverage"
            )
        observed_sha256 = self._digest.hexdigest()
        if observed_sha256 != self._expected_sha256:
            raise DeepSeekV4ApplicationCheckError(
                f"canonical artifact {self._path.name!r} differs from its manifest hash"
            )
        return observed_sha256

    def abort(self) -> None:
        if not self._handle.closed:
            self._handle.close()


def _check_record(
    assignment: Mapping[str, Any], *, method: str, detail_check_id: str | None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "assignment_path": assignment["path"],
        "checked_output_bytes": assignment["payload_bytes"],
        "detail_check_id": detail_check_id,
        "method": method,
        "output_sha256": assignment["sha256"],
        "rank": assignment["rank"],
        "source_name": assignment["source"]["name"],
        "status": "full_payload_match",
        "transform": assignment["transform"],
    }
    body["check_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


def _validate_manifest(
    manifest: Mapping[str, Any], lock_id: str
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    _exact_keys(
        manifest,
        {
            "application_id",
            "assignments",
            "coverage",
            "evidence_scope",
            "inputs",
            "plan",
            "schema",
            "selection",
            "source",
            "status",
        },
        "canonical application",
    )
    if manifest["schema"] != APPLICATION_SCHEMA:
        raise DeepSeekV4ApplicationCheckError("unsupported application schema")
    application_id = _sha256(manifest["application_id"], "application_id")
    body = dict(manifest)
    body.pop("application_id")
    if hashlib.sha256(canonical_json_bytes(body)).hexdigest() != application_id:
        raise DeepSeekV4ApplicationCheckError("canonical application ID differs")
    source = _exact_keys(
        manifest["source"],
        {"checkpoint_lock_id", "repository", "revision"},
        "canonical application source",
    )
    if source["checkpoint_lock_id"] != lock_id:
        raise DeepSeekV4ApplicationCheckError("application checkpoint lock differs")
    for field in ("repository", "revision"):
        if not isinstance(source[field], str) or not source[field]:
            raise DeepSeekV4ApplicationCheckError(f"source.{field} is invalid")
    plan = _exact_keys(
        manifest["plan"],
        {"expected_input_count", "plan_id", "schema"},
        "canonical application plan",
    )
    _integer(plan["expected_input_count"], "plan.expected_input_count", minimum=1)
    _sha256(plan["plan_id"], "plan.plan_id")
    if not isinstance(plan["schema"], str) or not plan["schema"]:
        raise DeepSeekV4ApplicationCheckError("plan.schema is invalid")
    evidence_scope = manifest["evidence_scope"]
    if evidence_scope not in {"development_fixture", "official_checkpoint"}:
        raise DeepSeekV4ApplicationCheckError("application evidence_scope is invalid")

    raw_inputs = manifest["inputs"]
    raw_assignments = manifest["assignments"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise DeepSeekV4ApplicationCheckError("application inputs must be nonempty")
    if not isinstance(raw_assignments, list):
        raise DeepSeekV4ApplicationCheckError("application assignments must be an array")
    inputs: list[Mapping[str, Any]] = []
    inputs_by_name: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(raw_inputs):
        record = _exact_keys(
            value,
            {
                "action",
                "logical_dtype",
                "name",
                "payload_sha256",
                "shape",
                "size_bytes",
                "storage_dtype",
            },
            f"inputs[{index}]",
        )
        name = _name(record["name"], f"inputs[{index}].name")
        if name in inputs_by_name:
            raise DeepSeekV4ApplicationCheckError("application inputs are duplicated")
        shape = _shape(record["shape"], f"inputs[{index}].shape")
        dtype = record["storage_dtype"]
        if dtype not in _DTYPE_BYTES:
            raise DeepSeekV4ApplicationCheckError("input storage dtype is unsupported")
        if _integer(record["size_bytes"], f"inputs[{index}].size_bytes", minimum=1) != (
            math.prod(shape) * _DTYPE_BYTES[dtype]
        ):
            raise DeepSeekV4ApplicationCheckError("input size differs from shape/dtype")
        _sha256(record["payload_sha256"], f"inputs[{index}].payload_sha256")
        for field in ("action", "logical_dtype"):
            if not isinstance(record[field], str) or not record[field]:
                raise DeepSeekV4ApplicationCheckError(
                    f"inputs[{index}].{field} is invalid"
                )
        inputs.append(record)
        inputs_by_name[name] = record
    if [record["name"] for record in inputs] != sorted(inputs_by_name):
        raise DeepSeekV4ApplicationCheckError("application inputs are not name-sorted")

    assignments: list[Mapping[str, Any]] = []
    assignment_keys: set[tuple[int, str]] = set()
    paths: set[str] = set()
    for index, value in enumerate(raw_assignments):
        record = _exact_keys(
            value,
            {
                "logical_dtype",
                "name",
                "path",
                "payload_bytes",
                "rank",
                "scale_source",
                "sha256",
                "shape",
                "source",
                "storage_dtype",
                "transform",
            },
            f"assignments[{index}]",
        )
        name = _name(record["name"], f"assignments[{index}].name")
        if not isinstance(record["logical_dtype"], str) or not record["logical_dtype"]:
            raise DeepSeekV4ApplicationCheckError(
                f"assignments[{index}].logical_dtype is invalid"
            )
        rank = _integer(record["rank"], f"assignments[{index}].rank")
        key = (rank, name)
        if key in assignment_keys:
            raise DeepSeekV4ApplicationCheckError("application assignment is duplicated")
        assignment_keys.add(key)
        expected_path = f"ranks/rank-{rank:03d}/{name}.bin"
        if record["path"] != expected_path or expected_path in paths:
            raise DeepSeekV4ApplicationCheckError("assignment path is not canonical")
        paths.add(expected_path)
        shape = _shape(record["shape"], f"assignments[{index}].shape")
        dtype = record["storage_dtype"]
        if dtype not in _DTYPE_BYTES:
            raise DeepSeekV4ApplicationCheckError("output storage dtype is unsupported")
        payload_bytes = _integer(
            record["payload_bytes"], f"assignments[{index}].payload_bytes", minimum=1
        )
        if payload_bytes != math.prod(shape) * _DTYPE_BYTES[dtype]:
            raise DeepSeekV4ApplicationCheckError("output size differs from shape/dtype")
        _sha256(record["sha256"], f"assignments[{index}].sha256")
        if record["transform"] not in _TRANSFORMS:
            raise DeepSeekV4ApplicationCheckError("assignment transform is unsupported")
        source_record = _exact_keys(
            record["source"],
            {"name", "payload_sha256", "shape", "slice", "storage_dtype"},
            f"assignments[{index}].source",
        )
        source_name = _name(
            source_record["name"], f"assignments[{index}].source.name"
        )
        if source_name != name:
            raise DeepSeekV4ApplicationCheckError(
                "assignment output and source names differ"
            )
        source_input = inputs_by_name.get(source_name)
        if source_input is None:
            raise DeepSeekV4ApplicationCheckError("assignment source is not consumed")
        source_shape = _shape(
            source_record["shape"], f"assignments[{index}].source.shape"
        )
        source_slice = _slice(
            source_record["slice"], source_shape, f"assignments[{index}].source.slice"
        )
        if (
            source_record["payload_sha256"] != source_input["payload_sha256"]
            or list(source_shape) != source_input["shape"]
            or source_record["storage_dtype"] != source_input["storage_dtype"]
        ):
            raise DeepSeekV4ApplicationCheckError("assignment source metadata differs")
        if record["transform"] != "dequantize_fp8_e8m0_to_bf16_rne" and (
            tuple(shape) != _slice_shape(source_shape, source_slice)
        ):
            raise DeepSeekV4ApplicationCheckError("assignment shape differs from slice")
        if record["transform"] == "dequantize_fp8_e8m0_to_bf16_rne" and (
            source_record["storage_dtype"] != "F8_E4M3"
            or dtype != "BF16"
            or record["logical_dtype"] != "BF16"
            or tuple(shape) != _slice_shape(source_shape, source_slice)
        ):
            raise DeepSeekV4ApplicationCheckError(
                "dequantization assignment metadata differs"
            )
        if (
            record["transform"]
            == "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
            and (
                source_record["storage_dtype"] != "I8"
                or dtype != "U8"
                or source_slice is not None
            )
        ):
            raise DeepSeekV4ApplicationCheckError(
                "native MXFP4 assignment metadata differs"
            )
        scale_source = record["scale_source"]
        if scale_source is not None:
            scale_record = _exact_keys(
                scale_source,
                {"name", "payload_sha256", "shape", "slice", "storage_dtype"},
                f"assignments[{index}].scale_source",
            )
            scale_name = _name(
                scale_record["name"], f"assignments[{index}].scale_source.name"
            )
            scale_input = inputs_by_name.get(scale_name)
            if scale_input is None:
                raise DeepSeekV4ApplicationCheckError("scale source is not consumed")
            scale_shape = _shape(
                scale_record["shape"], f"assignments[{index}].scale_source.shape"
            )
            _slice(
                scale_record["slice"],
                scale_shape,
                f"assignments[{index}].scale_source.slice",
            )
            if (
                scale_record["payload_sha256"] != scale_input["payload_sha256"]
                or list(scale_shape) != scale_input["shape"]
                or scale_record["storage_dtype"] != scale_input["storage_dtype"]
            ):
                raise DeepSeekV4ApplicationCheckError("scale source metadata differs")
        if (
            record["transform"]
            in {
                "dequantize_fp8_e8m0_to_bf16_rne",
                "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first",
            }
            and scale_source is None
        ):
            raise DeepSeekV4ApplicationCheckError(
                "transformed assignment lacks its scale source"
            )
        if record["transform"] == "identity" and scale_source is not None:
            raise DeepSeekV4ApplicationCheckError(
                "identity assignment unexpectedly names a scale source"
            )
        assignments.append(record)

    input_order = {record["name"]: index for index, record in enumerate(inputs)}
    assignment_order = [
        (input_order[record["source"]["name"]], record["rank"], record["name"])
        for record in assignments
    ]
    if assignment_order != sorted(assignment_order):
        raise DeepSeekV4ApplicationCheckError("application assignments are not canonical")

    coverage = _exact_keys(
        manifest["coverage"],
        {
            "consumed_input_count",
            "consumed_input_payload_bytes",
            "output_assignment_count",
            "output_payload_bytes",
        },
        "application coverage",
    )
    expected_coverage = {
        "consumed_input_count": len(inputs),
        "consumed_input_payload_bytes": sum(record["size_bytes"] for record in inputs),
        "output_assignment_count": len(assignments),
        "output_payload_bytes": sum(record["payload_bytes"] for record in assignments),
    }
    if dict(coverage) != expected_coverage:
        raise DeepSeekV4ApplicationCheckError("application coverage differs")
    selection = _exact_keys(
        manifest["selection"],
        {
            "complete_plan",
            "dependency_input_names",
            "requested_input_names",
        },
        "application selection",
    )
    if not isinstance(selection["complete_plan"], bool):
        raise DeepSeekV4ApplicationCheckError("selection.complete_plan must be boolean")

    def names_list(value: Any, label: str) -> list[str]:
        if not isinstance(value, list) or not value:
            raise DeepSeekV4ApplicationCheckError(f"{label} must be nonempty")
        result = [_name(item, f"{label}[{index}]") for index, item in enumerate(value)]
        if result != sorted(set(result)):
            raise DeepSeekV4ApplicationCheckError(f"{label} must be unique and sorted")
        return result

    requested = names_list(
        selection["requested_input_names"], "selection.requested_input_names"
    )
    dependencies_raw = selection["dependency_input_names"]
    if not isinstance(dependencies_raw, list):
        raise DeepSeekV4ApplicationCheckError(
            "selection.dependency_input_names must be an array"
        )
    dependencies = [
        _name(item, f"selection.dependency_input_names[{index}]")
        for index, item in enumerate(dependencies_raw)
    ]
    if dependencies != sorted(set(dependencies)):
        raise DeepSeekV4ApplicationCheckError(
            "selection.dependency_input_names must be unique and sorted"
        )
    if set(requested) & set(dependencies) or set(requested) | set(dependencies) != set(
        inputs_by_name
    ):
        raise DeepSeekV4ApplicationCheckError(
            "selection names do not partition consumed inputs"
        )
    complete_plan = (
        len(inputs) == plan["expected_input_count"]
        and not dependencies
        and set(requested) == set(inputs_by_name)
    )
    if selection["complete_plan"] != complete_plan:
        raise DeepSeekV4ApplicationCheckError("selection.complete_plan differs")
    expected_status = {
        ("development_fixture", False): (
            "development_fixture_application_not_release_evidence"
        ),
        ("development_fixture", True): (
            "development_fixture_application_not_release_evidence"
        ),
        ("official_checkpoint", False): (
            "partial_official_transform_application_not_release_evidence"
        ),
        ("official_checkpoint", True): "complete_official_transform_application",
    }[(evidence_scope, complete_plan)]
    if manifest["status"] != expected_status:
        raise DeepSeekV4ApplicationCheckError("application status differs from scope")
    return inputs, assignments


def verify_canonical_application(
    application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> dict[str, Any]:
    """Replay every consumed input and compare every emitted assignment byte."""

    application_root = Path(application_root)
    try:
        manifest = load_strict_json(application_root / MANIFEST_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4ApplicationCheckError(
            f"cannot load canonical application manifest: {exc}"
        ) from exc
    inputs, assignments = _validate_manifest(manifest, lock["lock_id"])
    if (
        manifest["source"]["repository"] != lock["source"]["repository"]
        or manifest["source"]["revision"] != lock["source"]["revision"]
    ):
        raise DeepSeekV4ApplicationCheckError("application source release differs")

    assignments_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for assignment in assignments:
        assignments_by_source.setdefault(assignment["source"]["name"], []).append(
            assignment
        )
    dependency_names = {
        assignment["scale_source"]["name"]
        for assignment in assignments
        if assignment["scale_source"] is not None
    }
    assignment_by_rank_name = {
        (assignment["rank"], assignment["name"]): assignment
        for assignment in assignments
    }
    scale_cache: dict[str, bytes] = {}
    checks: list[dict[str, Any]] = []
    inputs_by_name = {record["name"]: record for record in inputs}
    input_order = {record["name"]: index for index, record in enumerate(inputs)}

    with LockedCheckpointReader(snapshot, lock) as reader:
        for input_record in inputs:
            name = input_record["name"]
            locked = reader.tensor_record(name)
            if (
                locked["dtype"] != input_record["storage_dtype"]
                or locked["shape"] != input_record["shape"]
                or locked["size_bytes"] != input_record["size_bytes"]
                or locked["payload_sha256"] != input_record["payload_sha256"]
            ):
                raise DeepSeekV4ApplicationCheckError(
                    f"consumed input {name!r} differs from its checkpoint lock"
                )
            source_assignments = assignments_by_source.get(name, [])
            transforms = {record["transform"] for record in source_assignments}
            needs_bytes = name in dependency_names or bool(
                transforms
                & {
                    "dequantize_fp8_e8m0_to_bf16_rne",
                    "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first",
                }
            )
            if needs_bytes:
                payload = _read_locked(reader, name)
                if name in dependency_names:
                    scale_cache[name] = payload
            else:
                payload = b""

            if not source_assignments:
                if not needs_bytes:
                    reader.consume_tensor_payload(name, lambda _: None)
                continue

            if transforms <= {"identity"}:
                comparators: list[tuple[Mapping[str, Any], _SliceComparator]] = []
                try:
                    for assignment in source_assignments:
                        path = _safe_artifact_path(
                            application_root, assignment["path"], "assignment.path"
                        )
                        descriptor = _slice(
                            assignment["source"]["slice"],
                            tuple(input_record["shape"]),
                            "assignment.source.slice",
                        )
                        comparators.append(
                            (
                                assignment,
                                _SliceComparator(
                                    path,
                                    assignment["sha256"],
                                    assignment["payload_bytes"],
                                    tuple(input_record["shape"]),
                                    input_record["storage_dtype"],
                                    descriptor,
                                ),
                            )
                        )
                except Exception:
                    for _, comparator in comparators:
                        comparator.abort()
                    raise
                source_offset = 0

                def compare_chunk(chunk: bytes) -> None:
                    nonlocal source_offset
                    for _, comparator in comparators:
                        comparator.consume(chunk, source_offset)
                    source_offset += len(chunk)

                try:
                    if needs_bytes:
                        compare_chunk(payload)
                    else:
                        reader.consume_tensor_payload(name, compare_chunk)
                    for assignment, comparator in comparators:
                        comparator.finish()
                        checks.append(
                            _check_record(
                                assignment,
                                method="streamed_identity_or_slice",
                                detail_check_id=None,
                            )
                        )
                except Exception:
                    for _, comparator in comparators:
                        comparator.abort()
                    raise
                continue

            if transforms == {"dequantize_fp8_e8m0_to_bf16_rne"}:
                for assignment in source_assignments:
                    scale_record = assignment["scale_source"]
                    if scale_record is None:
                        raise DeepSeekV4ApplicationCheckError(
                            "dequantization assignment has no scale source"
                        )
                    scale_name = scale_record["name"]
                    scale_payload = scale_cache.get(scale_name)
                    if scale_payload is None:
                        raise DeepSeekV4ApplicationCheckError(
                            f"scale source {scale_name!r} was not consumed first"
                        )
                    weight_slice = _slice(
                        assignment["source"]["slice"],
                        tuple(input_record["shape"]),
                        "assignment.source.slice",
                    )
                    scale_input = inputs_by_name[scale_name]
                    scale_slice = _slice(
                        scale_record["slice"],
                        tuple(scale_input["shape"]),
                        "assignment.scale_source.slice",
                    )
                    sliced_weight, weight_shape = _independent_slice(
                        payload,
                        tuple(input_record["shape"]),
                        input_record["storage_dtype"],
                        weight_slice,
                    )
                    sliced_scale, scale_shape = _independent_slice(
                        scale_payload,
                        tuple(scale_input["shape"]),
                        scale_input["storage_dtype"],
                        scale_slice,
                    )
                    output_path = _safe_artifact_path(
                        application_root, assignment["path"], "assignment.path"
                    )
                    output = _read_output(
                        output_path,
                        assignment["payload_bytes"],
                        assignment["sha256"],
                    )
                    try:
                        detail = verify_dequantized_fp8_e8m0_bf16(
                            sliced_weight,
                            sliced_scale,
                            output,
                            weight_shape,
                            scale_shape,
                        )
                    except DeepSeekV4TransformCheckError as exc:
                        raise DeepSeekV4ApplicationCheckError(str(exc)) from exc
                    checks.append(
                        _check_record(
                            assignment,
                            method="independent_fp8_e8m0_bf16",
                            detail_check_id=detail["check_id"],
                        )
                    )
                scale_cache.pop(scale_name, None)
                continue

            if transforms == {
                "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
            }:
                for assignment in source_assignments:
                    scale_record = assignment["scale_source"]
                    if scale_record is None:
                        raise DeepSeekV4ApplicationCheckError(
                            "native MXFP4 assignment has no scale source"
                        )
                    scale_name = scale_record["name"]
                    scale_payload = scale_cache.get(scale_name)
                    if scale_payload is None:
                        raise DeepSeekV4ApplicationCheckError(
                            f"scale source {scale_name!r} was not consumed first"
                        )
                    scale_assignment = assignment_by_rank_name.get(
                        (assignment["rank"], scale_name)
                    )
                    if scale_assignment is None:
                        raise DeepSeekV4ApplicationCheckError(
                            "native MXFP4 output lacks its rank-local scale artifact"
                        )
                    output_weight = _read_output(
                        _safe_artifact_path(
                            application_root, assignment["path"], "assignment.path"
                        ),
                        assignment["payload_bytes"],
                        assignment["sha256"],
                    )
                    output_scale = _read_output(
                        _safe_artifact_path(
                            application_root,
                            scale_assignment["path"],
                            "scale assignment.path",
                        ),
                        scale_assignment["payload_bytes"],
                        scale_assignment["sha256"],
                    )
                    scale_input = inputs_by_name[scale_name]
                    try:
                        detail = verify_native_mxfp4_identity(
                            payload,
                            scale_payload,
                            output_weight,
                            output_scale,
                            input_record["shape"],
                            scale_input["shape"],
                        )
                    except DeepSeekV4TransformCheckError as exc:
                        raise DeepSeekV4ApplicationCheckError(str(exc)) from exc
                    checks.append(
                        _check_record(
                            assignment,
                            method="native_mxfp4_pair_identity",
                            detail_check_id=detail["check_id"],
                        )
                    )
                scale_cache.pop(scale_name, None)
                continue
            raise DeepSeekV4ApplicationCheckError(
                f"source {name!r} mixes incompatible transforms"
            )

        verified_names = reader.accessed_tensor_names

    expected_names = tuple(record["name"] for record in inputs)
    if verified_names != expected_names:
        raise DeepSeekV4ApplicationCheckError(
            "verification did not consume every declared input exactly by identity"
        )
    if scale_cache:
        raise DeepSeekV4ApplicationCheckError(
            f"unused scale dependencies remain: {sorted(scale_cache)[:8]}"
        )
    if len(checks) != len(assignments):
        raise DeepSeekV4ApplicationCheckError(
            "verification check count differs from output assignments"
        )
    checks.sort(
        key=lambda record: (
            input_order[record["source_name"]],
            record["rank"],
            record["assignment_path"],
        )
    )
    body: dict[str, Any] = {
        "application_id": manifest["application_id"],
        "checkpoint_lock_id": lock["lock_id"],
        "checks": checks,
        "coverage": {
            "checked_assignment_count": len(checks),
            "checked_input_count": len(verified_names),
            "checked_output_bytes": sum(
                record["checked_output_bytes"] for record in checks
            ),
        },
        "schema": APPLICATION_CHECK_SCHEMA,
        "status": "full_assignment_match",
    }
    body["verification_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


__all__ = [
    "APPLICATION_CHECK_SCHEMA",
    "APPLICATION_SCHEMA",
    "DeepSeekV4ApplicationCheckError",
    "MANIFEST_FILENAME",
    "VERIFICATION_FILENAME",
    "verify_canonical_application",
]
