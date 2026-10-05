"""Software service engine for verified OpenTallas deployment artifacts.

The interpreter consumes the deployment manifest, stripped semantic descriptor,
ROM image, tensor table, microcode, and static expectations. It never reads the
source tensor payloads or a known-answer file.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.ir.model import Model, canonical_json_bytes, load_strict_json, parse_model
from compiler.microcode.isa import (
    ABI_MAJOR,
    ABI_MINOR,
    Instruction,
    Opcode,
    decode,
    verify,
)


DEPLOYMENT_SCHEMA = "opentallas.deployment_manifest.v1"
REQUEST_SCHEMA = "opentallas.execution_request.v1"
RESULT_SCHEMA = "opentallas.service_engine_result.v1"
EXPECTED_ROLES = frozenset(
    {
        "execution_expectations",
        "microcode",
        "microcode_disassembly",
        "operator_coverage",
        "rom_image",
        "rom_roundtrip_report",
        "semantic_ir",
        "source_lock",
        "tensor_manifest",
    }
)
COUNTER_KEYS = (
    "activation_tensor_reads",
    "completion_events",
    "elementwise_add_operations",
    "logical_activation_bytes_read",
    "logical_activation_bytes_written",
    "logical_rom_bytes_read",
    "micro_ops_executed",
    "rom_tensor_reads",
    "scalar_accumulate_add_operations",
    "scalar_multiply_operations",
    "semantic_operations_executed",
)


class ServiceEngineError(RuntimeError):
    """Raised when artifacts, control flow, data, or counters fail closed."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ServiceEngineError(f"{label} must be an integer >= {minimum}")
    return value


def _safe_artifact(root: Path, path_text: Any) -> Path:
    if not isinstance(path_text, str) or not path_text:
        raise ServiceEngineError("artifact path must be a non-empty string")
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ServiceEngineError(f"artifact path escapes deployment: {path_text!r}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ServiceEngineError(f"artifact path escapes deployment: {path_text!r}") from exc
    return resolved


def _decode_values(dtype: str, payload: bytes) -> tuple[int, ...]:
    try:
        if dtype == "i8":
            return tuple(struct.unpack(f"<{len(payload)}b", payload))
        if dtype == "i32" and len(payload) % 4 == 0:
            return tuple(struct.unpack(f"<{len(payload) // 4}i", payload))
    except struct.error as exc:
        raise ServiceEngineError(f"cannot decode ROM payload: {exc}") from exc
    raise ServiceEngineError(f"cannot decode {len(payload)} bytes as {dtype}")


def _empty_counters() -> dict[str, int]:
    return {key: 0 for key in COUNTER_KEYS}


@dataclass(frozen=True)
class VerifiedArtifact:
    relative_path: str
    path: Path
    payload: bytes


@dataclass(frozen=True)
class Deployment:
    root: Path
    manifest: dict[str, Any]
    model: Model
    instructions: tuple[Instruction, ...]
    rom_values: dict[int, tuple[int, ...]]
    expectations: dict[str, Any]


def _verify_artifacts(
    root: Path, manifest: dict[str, Any]
) -> dict[str, VerifiedArtifact]:
    raw_records = manifest.get("artifacts")
    if not isinstance(raw_records, list) or not raw_records:
        raise ServiceEngineError("deployment artifact table is missing")
    by_role: dict[str, VerifiedArtifact] = {}
    seen_paths: set[str] = set()
    for index, record in enumerate(raw_records):
        if not isinstance(record, dict) or set(record) != {
            "path",
            "role",
            "sha256",
            "size_bytes",
        }:
            raise ServiceEngineError(f"artifact record {index} is malformed")
        role = record["role"]
        path_text = record["path"]
        if not isinstance(role, str) or role in by_role:
            raise ServiceEngineError(f"artifact role {role!r} is duplicated")
        if not isinstance(path_text, str) or path_text in seen_paths:
            raise ServiceEngineError(f"artifact path {path_text!r} is duplicated")
        seen_paths.add(path_text)
        path = _safe_artifact(root, path_text)
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise ServiceEngineError(
                f"cannot read deployment artifact {path_text!r}: {exc}"
            ) from exc
        if _require_int(record["size_bytes"], f"artifact {path_text} size") != len(payload):
            raise ServiceEngineError(f"artifact {path_text!r} size mismatch")
        if record["sha256"] != _sha256(payload):
            raise ServiceEngineError(f"artifact {path_text!r} SHA-256 mismatch")
        by_role[role] = VerifiedArtifact(path_text, path, payload)
    if frozenset(by_role) != EXPECTED_ROLES:
        raise ServiceEngineError(
            f"deployment roles differ: missing={sorted(EXPECTED_ROLES - by_role.keys())}, "
            f"extra={sorted(by_role.keys() - EXPECTED_ROLES)}"
        )
    return by_role


def _verify_build_id(manifest: dict[str, Any]) -> None:
    try:
        identity = {
            "artifacts": manifest["artifacts"],
            "compiler_version": manifest["compiler"]["version"],
            "microcode_abi": manifest["microcode_abi"],
            "model_id": manifest["model_id"],
            "numeric_profile": manifest["numeric_profile"],
            "semantic_sha256": manifest["semantic_sha256"],
        }
    except (KeyError, TypeError) as exc:
        raise ServiceEngineError(f"deployment identity is incomplete: {exc}") from exc
    expected = _sha256(canonical_json_bytes(identity))
    if manifest.get("build_id") != expected:
        raise ServiceEngineError("deployment build_id does not bind its artifact table")


def _load_rom_values(
    model: Model, tensor_manifest: dict[str, Any], image: bytes
) -> dict[int, tuple[int, ...]]:
    if tensor_manifest.get("schema") != "opentallas.tensor_manifest.v1":
        raise ServiceEngineError("unsupported tensor manifest schema")
    if tensor_manifest.get("byte_order") != "little":
        raise ServiceEngineError("only little-endian tensor images are supported")
    image_record = tensor_manifest.get("image")
    if not isinstance(image_record, dict):
        raise ServiceEngineError("tensor manifest image identity is missing")
    if _require_int(image_record.get("size_bytes"), "ROM image size") != len(image):
        raise ServiceEngineError("ROM image length differs from tensor manifest")
    if image_record.get("sha256") != _sha256(image):
        raise ServiceEngineError("ROM image hash differs from tensor manifest")
    records = tensor_manifest.get("tensors")
    if not isinstance(records, list) or len(records) != len(model.tensors):
        raise ServiceEngineError("tensor manifest coverage differs from semantic IR")
    alignment = _require_int(
        tensor_manifest.get("alignment_bytes"), "image alignment", minimum=1
    )
    occupied = bytearray(len(image))
    rom_values: dict[int, tuple[int, ...]] = {}
    for tensor, record in zip(model.tensors, records, strict=True):
        if not isinstance(record, dict):
            raise ServiceEngineError(f"tensor manifest record {tensor.index} is malformed")
        identity = (
            record.get("tensor_index"),
            record.get("tensor_id"),
            record.get("dtype"),
            record.get("shape"),
            record.get("storage"),
            record.get("size_bytes"),
        )
        expected_identity = (
            tensor.index,
            tensor.tensor_id,
            tensor.dtype,
            list(tensor.shape),
            tensor.storage,
            tensor.size_bytes,
        )
        if identity != expected_identity:
            raise ServiceEngineError(
                f"tensor manifest identity differs for {tensor.tensor_id!r}"
            )
        interval = record.get("image")
        if tensor.storage != "rom":
            if interval is not None:
                raise ServiceEngineError(
                    f"non-ROM tensor {tensor.tensor_id!r} owns ROM bytes"
                )
            continue
        if not isinstance(interval, dict):
            raise ServiceEngineError(f"ROM tensor {tensor.tensor_id!r} lacks bytes")
        offset = _require_int(interval.get("offset_bytes"), "ROM tensor offset")
        length = _require_int(
            interval.get("length_bytes"), "ROM tensor length", minimum=1
        )
        end = offset + length
        if offset % alignment or length != tensor.size_bytes or end > len(image):
            raise ServiceEngineError(f"ROM interval is illegal for {tensor.tensor_id!r}")
        if any(occupied[offset:end]):
            raise ServiceEngineError(f"ROM interval overlaps for {tensor.tensor_id!r}")
        occupied[offset:end] = bytes([1]) * length
        payload = image[offset:end]
        if interval.get("sha256") != _sha256(payload):
            raise ServiceEngineError(f"ROM slice hash mismatch for {tensor.tensor_id!r}")
        values = _decode_values(tensor.dtype, payload)
        if len(values) != tensor.element_count:
            raise ServiceEngineError(f"ROM element count mismatch for {tensor.tensor_id!r}")
        rom_values[tensor.index] = values
    if any(byte != 0 for index, byte in enumerate(image) if not occupied[index]):
        raise ServiceEngineError("ROM padding must be zero")
    return rom_values


def load_deployment(deployment_dir: Path) -> Deployment:
    root = deployment_dir.resolve()
    if not root.is_dir():
        raise ServiceEngineError(f"deployment is not a directory: {root}")
    manifest = load_strict_json(root / "deployment_manifest.json")
    if manifest.get("schema") != DEPLOYMENT_SCHEMA:
        raise ServiceEngineError("unsupported deployment manifest schema")
    if manifest.get("microcode_abi") != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        raise ServiceEngineError("deployment requests an unsupported microcode ABI")
    _verify_build_id(manifest)
    artifacts = _verify_artifacts(root, manifest)

    expected_entrypoint = {
        "execution_expectations": artifacts["execution_expectations"].relative_path,
        "microcode": artifacts["microcode"].relative_path,
        "rom_image": artifacts["rom_image"].relative_path,
        "semantic_ir": artifacts["semantic_ir"].relative_path,
        "tensor_manifest": artifacts["tensor_manifest"].relative_path,
    }
    if manifest.get("entrypoint") != expected_entrypoint:
        raise ServiceEngineError("deployment entrypoint differs from verified artifact roles")

    semantic_ir = load_strict_json(artifacts["semantic_ir"].path)
    model = parse_model(semantic_ir, require_rom_values=False)
    if any(tensor.values is not None for tensor in model.tensors):
        raise ServiceEngineError("runtime semantic IR must not contain ROM payload values")
    if (
        manifest.get("model_id") != model.model_id
        or manifest.get("numeric_profile") != model.numeric_profile
    ):
        raise ServiceEngineError("deployment manifest and semantic IR identities differ")

    instructions = decode(artifacts["microcode"].payload)
    verify(instructions, model)
    tensor_manifest = load_strict_json(artifacts["tensor_manifest"].path)
    tensor_image_identity = tensor_manifest.get("image")
    if (
        not isinstance(tensor_image_identity, dict)
        or tensor_image_identity.get("path")
        != artifacts["rom_image"].relative_path
    ):
        raise ServiceEngineError("tensor manifest image path differs from ROM artifact role")
    rom_values = _load_rom_values(
        model, tensor_manifest, artifacts["rom_image"].payload
    )

    source_lock = load_strict_json(artifacts["source_lock"].path)
    if (
        source_lock.get("schema") != "opentallas.source_lock.v1"
        or source_lock.get("model_id") != model.model_id
        or source_lock.get("compiler_version")
        != manifest.get("compiler", {}).get("version")
        or source_lock.get("semantic_sha256") != manifest.get("semantic_sha256")
    ):
        raise ServiceEngineError("source lock differs from deployment identity")
    reconstructed_semantics = model.to_dict(include_values=False)
    for tensor, record in zip(
        model.tensors, reconstructed_semantics["tensors"], strict=True
    ):
        if tensor.storage == "rom":
            record["values"] = list(rom_values[tensor.index])
    reconstructed_semantic_sha = _sha256(
        canonical_json_bytes(reconstructed_semantics)
    )
    if reconstructed_semantic_sha != manifest.get("semantic_sha256"):
        raise ServiceEngineError(
            "runtime descriptors and ROM image do not reconstruct the locked semantic IR"
        )

    coverage = load_strict_json(artifacts["operator_coverage"].path)
    if (
        coverage.get("schema") != "opentallas.operator_coverage.v1"
        or coverage.get("model_id") != model.model_id
        or coverage.get("numeric_profile") != model.numeric_profile
        or coverage.get("status") != "pass"
        or coverage.get("unsupported_operation_count") != 0
    ):
        raise ServiceEngineError("operator coverage does not close the fixture program")
    roundtrip = load_strict_json(artifacts["rom_roundtrip_report"].path)
    reconstructed_tensors = roundtrip.get("reconstructed_tensors")
    if (
        roundtrip.get("schema") != "opentallas.rom_roundtrip_report.v1"
        or roundtrip.get("model_id") != model.model_id
        or roundtrip.get("status") != "pass"
        or roundtrip.get("image_sha256")
        != tensor_image_identity.get("sha256")
        or not isinstance(reconstructed_tensors, list)
        or len(reconstructed_tensors)
        != sum(tensor.storage == "rom" for tensor in model.tensors)
    ):
        raise ServiceEngineError("ROM roundtrip report does not close the image")

    expectations = load_strict_json(artifacts["execution_expectations"].path)
    if (
        expectations.get("schema") != "opentallas.execution_expectations.v1"
        or expectations.get("model_id") != model.model_id
    ):
        raise ServiceEngineError("execution expectations have the wrong identity")
    expected_counters = expectations.get("counters")
    if not isinstance(expected_counters, dict) or set(expected_counters) != set(COUNTER_KEYS):
        raise ServiceEngineError("execution expectation counters are incomplete")
    for key, value in expected_counters.items():
        _require_int(value, f"expected counter {key}")
    hardware_accounting = expectations.get("hardware_accounting")
    if (
        not isinstance(hardware_accounting, dict)
        or hardware_accounting.get("status")
        != "not modeled by the functional fixture"
        or any(
            hardware_accounting.get(field) is not None
            for field in ("cycles", "flits", "hbm_transactions", "stalls")
        )
    ):
        raise ServiceEngineError(
            "functional fixture must not contain speculative hardware accounting"
        )
    return Deployment(root, manifest, model, instructions, rom_values, expectations)


def _checked_i32(value: int, label: str) -> int:
    if value < -(1 << 31) or value > (1 << 31) - 1:
        raise ServiceEngineError(f"signed i32 overflow during {label}")
    return value


def _load_request(
    model: Model, request_path: Path
) -> tuple[dict[int, tuple[int, ...]], str]:
    request = load_strict_json(request_path)
    if set(request) != {"schema", "model_id", "tensors"}:
        raise ServiceEngineError("execution request has missing or unknown fields")
    if request["schema"] != REQUEST_SCHEMA or request["model_id"] != model.model_id:
        raise ServiceEngineError("execution request identity differs from deployment")
    records = request["tensors"]
    if not isinstance(records, list):
        raise ServiceEngineError("execution request tensors must be an array")
    inputs = [tensor for tensor in model.tensors if tensor.storage == "input"]
    by_id = {tensor.tensor_id: tensor for tensor in inputs}
    values_by_index: dict[int, tuple[int, ...]] = {}
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"dtype", "id", "shape", "values"}:
            raise ServiceEngineError(f"execution input record {index} is malformed")
        tensor_id = record["id"]
        if tensor_id not in by_id or tensor_id in seen:
            raise ServiceEngineError(f"unexpected or duplicate input tensor {tensor_id!r}")
        seen.add(tensor_id)
        tensor = by_id[tensor_id]
        if record["dtype"] != tensor.dtype or record["shape"] != list(tensor.shape):
            raise ServiceEngineError(f"input metadata differs for {tensor_id!r}")
        raw_values = record["values"]
        if not isinstance(raw_values, list) or len(raw_values) != tensor.element_count:
            raise ServiceEngineError(f"input payload length differs for {tensor_id!r}")
        lower, upper = (-128, 127) if tensor.dtype == "i8" else (-(1 << 31), (1 << 31) - 1)
        parsed: list[int] = []
        for value_index, value in enumerate(raw_values):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < lower
                or value > upper
            ):
                raise ServiceEngineError(
                    f"input {tensor_id!r} value {value_index} is outside {tensor.dtype}"
                )
            parsed.append(value)
        values_by_index[tensor.index] = tuple(parsed)
    if seen != set(by_id):
        raise ServiceEngineError(f"execution request lacks inputs {sorted(set(by_id) - seen)}")
    return values_by_index, _sha256(canonical_json_bytes(request))


class ServiceEngine:
    """Verified, single-program functional service-engine instance."""

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    @classmethod
    def load(cls, deployment_dir: Path) -> "ServiceEngine":
        return cls(load_deployment(deployment_dir))

    def execute(self, request_path: Path) -> dict[str, Any]:
        model = self.deployment.model
        tensors = {tensor.index: tensor for tensor in model.tensors}
        state: dict[int, tuple[int, ...]] = dict(self.deployment.rom_values)
        request_values, request_sha256 = _load_request(model, request_path)
        state.update(request_values)
        counters = _empty_counters()
        completed = False

        for pc, instruction in enumerate(self.deployment.instructions):
            counters["micro_ops_executed"] += 1
            if instruction.opcode == Opcode.COMPLETE:
                if pc != len(self.deployment.instructions) - 1 or completed:
                    raise ServiceEngineError("illegal COMPLETE control flow")
                if instruction.destination not in state:
                    raise ServiceEngineError("COMPLETE observed before output availability")
                completed = True
                counters["completion_events"] += 1
                continue

            counters["semantic_operations_executed"] += 1
            destination = tensors[instruction.destination]
            sources = (tensors[instruction.source0], tensors[instruction.source1])
            for source in sources:
                if source.index not in state:
                    raise ServiceEngineError(
                        f"pc {pc} reads unavailable tensor {source.tensor_id!r}"
                    )
                if source.storage == "rom":
                    counters["rom_tensor_reads"] += 1
                    counters["logical_rom_bytes_read"] += source.size_bytes
                else:
                    counters["activation_tensor_reads"] += 1
                    counters["logical_activation_bytes_read"] += source.size_bytes
            counters["logical_activation_bytes_written"] += destination.size_bytes
            left = state[instruction.source0]
            right = state[instruction.source1]

            if instruction.opcode == Opcode.ROM_MATMUL:
                batch, reduction = sources[0].shape
                rows, _ = sources[1].shape
                result: list[int] = []
                for batch_index in range(batch):
                    for row_index in range(rows):
                        accumulator = 0
                        for reduction_index in range(reduction):
                            product = (
                                left[batch_index * reduction + reduction_index]
                                * right[row_index * reduction + reduction_index]
                            )
                            counters["scalar_multiply_operations"] += 1
                            accumulator = _checked_i32(
                                accumulator + product,
                                f"ROM_MATMUL pc {pc} accumulator",
                            )
                            counters["scalar_accumulate_add_operations"] += 1
                        result.append(accumulator)
                state[destination.index] = tuple(result)
            elif instruction.opcode == Opcode.VECTOR_ADD:
                result = []
                for element_index, (left_value, right_value) in enumerate(
                    zip(left, right, strict=True)
                ):
                    result.append(
                        _checked_i32(
                            left_value + right_value,
                            f"VECTOR_ADD pc {pc} element {element_index}",
                        )
                    )
                    counters["elementwise_add_operations"] += 1
                state[destination.index] = tuple(result)
            else:  # Static verification should make this unreachable.
                raise ServiceEngineError(f"pc {pc} has unsupported opcode")

        if not completed:
            raise ServiceEngineError("program terminated without COMPLETE")
        expected = self.deployment.expectations["counters"]
        if counters != expected:
            differences = {
                key: {"actual": counters[key], "expected": expected[key]}
                for key in COUNTER_KEYS
                if counters[key] != expected[key]
            }
            raise ServiceEngineError(f"execution counters do not reconcile: {differences}")
        outputs = []
        by_id = model.tensor_by_id
        for tensor_id in model.outputs:
            tensor = by_id[tensor_id]
            outputs.append(
                {
                    "dtype": tensor.dtype,
                    "id": tensor.tensor_id,
                    "shape": list(tensor.shape),
                    "values": list(state[tensor.index]),
                }
            )
        return {
            "build_id": self.deployment.manifest["build_id"],
            "counter_reconciliation": "exact",
            "counters": counters,
            "model_id": model.model_id,
            "outputs": outputs,
            "request_sha256": request_sha256,
            "schema": RESULT_SCHEMA,
            "semantic_sha256": self.deployment.manifest["semantic_sha256"],
            "status": "pass",
        }


def execute_deployment(
    deployment_dir: Path, request_path: Path
) -> dict[str, Any]:
    return ServiceEngine.load(deployment_dir).execute(request_path)
