"""Artifact-only simulator for compiled HBM/SRAM tensor-accelerator programs."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import struct
from typing import Any, Mapping

from compiler.tensor_accelerator.capability import Capability, parse_capability
from compiler.tensor_accelerator.checking import (
    CHECK_SCHEMA,
    COUNTER_KEYS,
    EXPECTATIONS_SCHEMA,
)
from compiler.tensor_accelerator.command import (
    ABI_MAJOR,
    ABI_MINOR,
    Command,
    Opcode,
    decode,
)
from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.model import ModelGraph, parse_model_graph
from compiler.tensor_accelerator.physical import HBM_IMAGE_PATH, PHYSICAL_PLAN_SCHEMA


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.deployment.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.execution_request.v1"
REPORT_SCHEMA = "opentallas.tensor_accelerator.execution_report.v1"


class SimulationError(RuntimeError):
    """Raised when a deployment or execution request is invalid."""


@dataclass(frozen=True)
class Artifact:
    role: str
    relative_path: str
    path: Path
    payload: bytes


@dataclass(frozen=True)
class Deployment:
    root: Path
    manifest: Mapping[str, Any]
    capability: Capability
    model: ModelGraph
    kernel_ir: Mapping[str, Any]
    physical_plan: Mapping[str, Any]
    commands: tuple[Command, ...]
    hbm_image: bytes
    expectations: Mapping[str, Any]


class _SRAM:
    def __init__(self, capability: Capability):
        self.capability = capability
        self.payload = bytearray(capability.sram.capacity_bytes)
        self.initialized = bytearray(capability.sram.capacity_bytes)

    def _range(self, address: int, size: int, label: str) -> tuple[int, int]:
        if (
            isinstance(address, bool)
            or not isinstance(address, int)
            or address < 0
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise SimulationError(f"{label} has an invalid SRAM range")
        end = address + size
        if end > len(self.payload):
            raise SimulationError(f"{label} exceeds SRAM capacity")
        start_bank = address // self.capability.sram.bytes_per_bank
        end_bank = (end - 1) // self.capability.sram.bytes_per_bank if size else start_bank
        if size and start_bank != end_bank:
            raise SimulationError(f"{label} crosses an SRAM bank boundary")
        return address, end

    def write(self, address: int, payload: bytes, label: str) -> None:
        start, end = self._range(address, len(payload), label)
        self.payload[start:end] = payload
        self.initialized[start:end] = bytes([1]) * len(payload)

    def read(self, address: int, size: int, label: str) -> bytes:
        start, end = self._range(address, size, label)
        if any(value == 0 for value in self.initialized[start:end]):
            raise SimulationError(f"{label} reads uninitialized SRAM")
        return bytes(self.payload[start:end])


def _body_id(value: Mapping[str, Any], id_key: str) -> str:
    body = dict(value)
    body.pop(id_key, None)
    return sha256_bytes(canonical_json_bytes(body))


def _verify_build_id(manifest: Mapping[str, Any]) -> None:
    observed = _body_id(manifest, "build_id")
    if manifest.get("build_id") != observed:
        raise SimulationError(
            f"deployment build_id mismatch: expected {observed}, "
            f"observed {manifest.get('build_id')!r}"
        )


def _verify_artifacts(root: Path, manifest: Mapping[str, Any]) -> dict[str, Artifact]:
    raw_artifacts = manifest.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise SimulationError("deployment artifact table is empty")
    by_role: dict[str, Artifact] = {}
    seen_paths: set[str] = set()
    for index, raw in enumerate(raw_artifacts):
        if not isinstance(raw, dict):
            raise SimulationError(f"artifact {index} is not an object")
        try:
            exact_keys(
                raw,
                {"path", "role", "sha256", "size_bytes"},
                set(),
                f"artifact {index}",
            )
            expected_hash = require_sha256(
                raw["sha256"], f"artifact {index}.sha256"
            )
            expected_size = require_int(
                raw["size_bytes"], f"artifact {index}.size_bytes", minimum=0
            )
        except ArtifactError as exc:
            raise SimulationError(str(exc)) from exc
        relative = raw["path"]
        role = raw["role"]
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or not isinstance(role, str)
            or not role
            or relative in seen_paths
            or role in by_role
        ):
            raise SimulationError(f"artifact {index} has an invalid path or role")
        seen_paths.add(relative)
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise SimulationError(f"artifact {relative!r} escapes or is missing")
        payload = path.read_bytes()
        if len(payload) != expected_size:
            raise SimulationError(f"artifact {relative!r} byte count mismatch")
        if sha256_bytes(payload) != expected_hash:
            raise SimulationError(f"artifact {relative!r} SHA-256 mismatch")
        by_role[role] = Artifact(role, relative, path, payload)
    expected_roles = {
        "command_disassembly",
        "command_program",
        "execution_expectations",
        "hardware_capability",
        "hbm_image",
        "independent_check",
        "model_graph",
        "operator_coverage",
        "physical_plan",
        "source_lock",
        "tensor_kernel_ir",
    }
    if set(by_role) != expected_roles:
        raise SimulationError("deployment artifact roles are incomplete or unknown")
    return by_role


def _decode_json(artifact: Artifact, label: str) -> dict[str, Any]:
    try:
        value = load_strict_json(artifact.path)
    except ArtifactError as exc:
        raise SimulationError(f"{label} is invalid: {exc}") from exc
    if canonical_json_bytes(value) != artifact.payload:
        raise SimulationError(f"{label} is not canonically serialized")
    return value


def _load_deployment(root_path: Path) -> Deployment:
    root = Path(root_path).resolve()
    if not root.is_dir():
        raise SimulationError(f"deployment is not a directory: {root}")
    try:
        manifest = load_strict_json(root / "deployment_manifest.json")
    except ArtifactError as exc:
        raise SimulationError(f"cannot load deployment manifest: {exc}") from exc
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise SimulationError("unsupported deployment manifest schema")
    if manifest.get("command_abi") != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        raise SimulationError("deployment command ABI is unsupported")
    _verify_build_id(manifest)
    artifacts = _verify_artifacts(root, manifest)

    entrypoint = manifest.get("entrypoint")
    expected_entrypoint = {
        "capability": artifacts["hardware_capability"].relative_path,
        "command_program": artifacts["command_program"].relative_path,
        "execution_expectations": artifacts["execution_expectations"].relative_path,
        "hbm_image": artifacts["hbm_image"].relative_path,
        "model_graph": artifacts["model_graph"].relative_path,
        "physical_plan": artifacts["physical_plan"].relative_path,
        "tensor_kernel_ir": artifacts["tensor_kernel_ir"].relative_path,
    }
    if entrypoint != expected_entrypoint:
        raise SimulationError("deployment entrypoint differs from artifact roles")

    try:
        capability = parse_capability(
            _decode_json(artifacts["hardware_capability"], "capability")
        )
        model = parse_model_graph(
            _decode_json(artifacts["model_graph"], "Model Graph IR"),
            require_initializers=False,
        )
        if any(tensor.values is not None for tensor in model.tensors):
            raise SimulationError(
                "runtime Model Graph IR must not contain initializer payloads"
            )
        commands = decode(artifacts["command_program"].payload)
    except (ArtifactError, ValueError) as exc:
        raise SimulationError(f"deployment ABI artifact is invalid: {exc}") from exc
    kernel_ir = _decode_json(artifacts["tensor_kernel_ir"], "Tensor Kernel IR")
    physical_plan = _decode_json(artifacts["physical_plan"], "physical plan")
    expectations = _decode_json(
        artifacts["execution_expectations"], "execution expectations"
    )
    source_lock = _decode_json(artifacts["source_lock"], "source lock")
    coverage = _decode_json(artifacts["operator_coverage"], "operator coverage")
    check = _decode_json(artifacts["independent_check"], "independent check")

    if (
        manifest.get("model_id") != model.model_id
        or manifest.get("numeric_profile") != model.numeric_profile
        or manifest.get("capability_id") != capability.capability_id
        or source_lock.get("model_id") != model.model_id
        or source_lock.get("capability_id") != capability.capability_id
        or source_lock.get("semantic_sha256") != manifest.get("semantic_sha256")
    ):
        raise SimulationError("deployment identities disagree")
    if (
        kernel_ir.get("model_id") != model.model_id
        or kernel_ir.get("capability_id") != capability.capability_id
        or physical_plan.get("schema") != PHYSICAL_PLAN_SCHEMA
        or physical_plan.get("model_id") != model.model_id
        or physical_plan.get("capability_id") != capability.capability_id
        or physical_plan.get("physical_plan_id") != manifest.get("physical_plan_id")
        or physical_plan.get("physical_plan_id")
        != _body_id(physical_plan, "physical_plan_id")
    ):
        raise SimulationError("IR and physical-plan identities disagree")
    if (
        coverage.get("status") != "pass"
        or coverage.get("unsupported_operation_count") != 0
        or coverage.get("model_id") != model.model_id
    ):
        raise SimulationError("operator coverage does not close the deployment")
    if (
        check.get("schema") != CHECK_SCHEMA
        or check.get("status") != "pass"
        or check.get("model_id") != model.model_id
        or check.get("capability_id") != capability.capability_id
        or check.get("semantic_sha256") != manifest.get("semantic_sha256")
        or check.get("physical_plan_id") != manifest.get("physical_plan_id")
        or check.get("command_sha256")
        != sha256_bytes(artifacts["command_program"].payload)
        or check.get("hbm_image_sha256")
        != sha256_bytes(artifacts["hbm_image"].payload)
    ):
        raise SimulationError("independent check does not close the deployment")
    expected_counters = expectations.get("counters")
    if (
        expectations.get("schema") != EXPECTATIONS_SCHEMA
        or expectations.get("model_id") != model.model_id
        or expectations.get("capability_id") != capability.capability_id
        or not isinstance(expected_counters, dict)
        or set(expected_counters) != set(COUNTER_KEYS)
        or check.get("expected_counters") != expected_counters
    ):
        raise SimulationError("execution expectations are incomplete or inconsistent")

    hbm_image = artifacts["hbm_image"].payload
    image_record = physical_plan.get("hbm", {}).get("image", {})
    if (
        image_record.get("path") != HBM_IMAGE_PATH
        or image_record.get("size_bytes") != len(hbm_image)
        or image_record.get("sha256") != sha256_bytes(hbm_image)
    ):
        raise SimulationError("physical plan does not bind the HBM image")
    if len(commands) != check.get("command_count"):
        raise SimulationError("command count differs from independent check")
    return Deployment(
        root,
        manifest,
        capability,
        model,
        kernel_ir,
        physical_plan,
        commands,
        hbm_image,
        expectations,
    )


def _tensor_records(
    physical_plan: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], Mapping[str, Any]]:
    allocations = physical_plan.get("sram", {}).get("allocations")
    staging = physical_plan.get("sram", {}).get("staging")
    if not isinstance(allocations, list) or not isinstance(staging, dict):
        raise SimulationError("physical plan SRAM records are invalid")
    by_tensor: dict[str, Mapping[str, Any]] = {}
    for raw in allocations:
        if not isinstance(raw, dict) or not isinstance(raw.get("tensor_id"), str):
            raise SimulationError("physical plan SRAM allocation is invalid")
        tensor_id = raw["tensor_id"]
        if tensor_id in by_tensor:
            raise SimulationError(f"duplicate SRAM tensor allocation {tensor_id!r}")
        by_tensor[tensor_id] = raw
    return by_tensor, staging


def _parse_request(
    model: ModelGraph,
    request_path: Path,
) -> tuple[dict[str, tuple[int, ...]], str]:
    try:
        request = load_strict_json(request_path)
    except ArtifactError as exc:
        raise SimulationError(f"execution request is invalid: {exc}") from exc
    try:
        exact_keys(
            request,
            {"schema", "model_id", "symbols", "tensors"},
            set(),
            "execution request",
        )
    except ArtifactError as exc:
        raise SimulationError(str(exc)) from exc
    if request["schema"] != REQUEST_SCHEMA or request["model_id"] != model.model_id:
        raise SimulationError("execution request identity differs from deployment")
    symbols = request["symbols"]
    if not isinstance(symbols, dict):
        raise SimulationError("execution request symbols must be an object")
    expected_symbols = model.symbol_by_id
    if set(symbols) != set(expected_symbols):
        raise SimulationError("execution request symbols differ from the model")
    for symbol_id, raw_value in symbols.items():
        symbol = expected_symbols[symbol_id]
        value = require_int(
            raw_value,
            f"execution symbol {symbol_id}",
            minimum=symbol.minimum,
            maximum=symbol.maximum,
        )
        if value % symbol.multiple_of:
            raise SimulationError(
                f"execution symbol {symbol_id!r} violates multiple_of"
            )
        if value != symbol.default:
            raise SimulationError(
                "qualified fixture accepts only compiled default symbol values"
            )
    records = request["tensors"]
    if not isinstance(records, list):
        raise SimulationError("execution request tensors must be an array")
    expected = [tensor for tensor in model.tensors if tensor.role == "input"]
    by_id = {tensor.tensor_id: tensor for tensor in expected}
    values: dict[str, tuple[int, ...]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise SimulationError(f"execution tensor {index} is not an object")
        try:
            exact_keys(
                record,
                {"id", "dtype", "shape", "values"},
                set(),
                f"execution tensor {index}",
            )
        except ArtifactError as exc:
            raise SimulationError(str(exc)) from exc
        tensor_id = record["id"]
        if tensor_id not in by_id or tensor_id in values:
            raise SimulationError(f"unexpected or duplicate input {tensor_id!r}")
        tensor = by_id[tensor_id]
        if (
            record["dtype"] != tensor.dtype
            or record["shape"] != list(tensor.resolved_shape(expected_symbols))
        ):
            raise SimulationError(f"input metadata differs for {tensor_id!r}")
        raw_values = record["values"]
        expected_count = tensor.element_count(expected_symbols)
        if not isinstance(raw_values, list) or len(raw_values) != expected_count:
            raise SimulationError(f"input value count differs for {tensor_id!r}")
        parsed: list[int] = []
        for value_index, value in enumerate(raw_values):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < -128
                or value > 127
            ):
                raise SimulationError(
                    f"input {tensor_id!r} value {value_index} is outside i8"
                )
            parsed.append(value)
        values[tensor_id] = tuple(parsed)
    if set(values) != set(by_id):
        raise SimulationError("execution request lacks required input tensors")
    return values, sha256_bytes(canonical_json_bytes(request))


def _encode_values(dtype: str, values: tuple[int, ...]) -> bytes:
    try:
        if dtype == "i8":
            return struct.pack(f"<{len(values)}b", *values)
        if dtype == "i32":
            return struct.pack(f"<{len(values)}i", *values)
    except struct.error as exc:
        raise SimulationError(f"cannot encode {dtype} values: {exc}") from exc
    raise SimulationError(f"simulator cannot encode dtype {dtype!r}")


def _decode_values(dtype: str, payload: bytes) -> tuple[int, ...]:
    try:
        if dtype == "i8":
            return tuple(struct.unpack(f"<{len(payload)}b", payload))
        if dtype == "i32" and len(payload) % 4 == 0:
            return tuple(struct.unpack(f"<{len(payload) // 4}i", payload))
    except struct.error as exc:
        raise SimulationError(f"cannot decode {dtype} values: {exc}") from exc
    raise SimulationError(f"simulator cannot decode {len(payload)} bytes as {dtype}")


def _checked_i32(value: int, label: str) -> int:
    if value < -(1 << 31) or value > (1 << 31) - 1:
        raise SimulationError(f"signed i32 overflow during {label}")
    return value


class TensorAcceleratorSimulator:
    """Execute only verified deployment artifacts and runtime inputs."""

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    @classmethod
    def load(cls, deployment_dir: Path) -> "TensorAcceleratorSimulator":
        return cls(_load_deployment(deployment_dir))

    def execute(
        self,
        request_path: Path,
        *,
        mode: str = "data_bearing_timing",
    ) -> dict[str, Any]:
        if mode not in {"functional", "data_bearing_timing"}:
            raise SimulationError(
                "mode must be 'functional' or 'data_bearing_timing'"
            )
        deployment = self.deployment
        model = deployment.model
        inputs, request_sha256 = _parse_request(model, Path(request_path))
        sram = _SRAM(deployment.capability)
        sram_records, staging = _tensor_records(deployment.physical_plan)
        tensors = model.tensor_by_id
        symbols = model.symbol_by_id
        for tensor_id, values in inputs.items():
            tensor = tensors[tensor_id]
            payload = _encode_values(tensor.dtype, values)
            record = sram_records[tensor_id]
            if len(payload) != record["size_bytes"]:
                raise SimulationError(f"input {tensor_id!r} byte count differs")
            sram.write(record["address"], payload, f"input {tensor_id}")

        observed = {key: 0 for key in COUNTER_KEYS}
        observed["host_input_bytes_written"] = sum(
            tensors[tensor_id].size_bytes(symbols) for tensor_id in inputs
        )
        observed["sram_bytes_written"] = observed["host_input_bytes_written"]
        traces: list[dict[str, Any]] = []
        kernel_by_index = {
            kernel["index"]: kernel
            for kernel in deployment.kernel_ir["kernels"]
        }

        for command in deployment.commands:
            before_cycle = observed["cycles"]
            if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                end = command.source0 + command.size0
                if end > len(deployment.hbm_image):
                    raise SimulationError(
                        f"command {command.index} HBM read exceeds the image"
                    )
                if (
                    command.destination != staging["address"]
                    or command.size0 > staging["size_bytes"]
                ):
                    raise SimulationError(
                        f"command {command.index} exceeds the weight staging buffer"
                    )
                payload = deployment.hbm_image[command.source0:end]
                sram.write(
                    command.destination,
                    payload,
                    f"command {command.index} DMA destination",
                )
                kernel = kernel_by_index[command.kernel_index]
                # Derive timing from the exact per-kernel weight transfer.
                useful = kernel["traffic_bytes"]["input1"]
                burst = deployment.capability.hbm.burst_bytes
                transactions = (
                    (command.source0 + useful + burst - 1) // burst
                    - command.source0 // burst
                )
                transferred = transactions * burst
                issue = math.ceil(
                    transferred
                    / (
                        deployment.capability.dma.issue_bytes_per_cycle
                        * deployment.capability.dma.count
                    )
                )
                words = math.ceil(
                    useful / deployment.capability.sram.word_bytes
                )
                write_service = (
                    deployment.capability.sram.write_latency_cycles
                    + math.ceil(
                        words
                        / deployment.capability.sram.write_ports_per_bank
                    )
                )
                command_cycles = deployment.capability.hbm.read_latency_cycles + max(
                    issue, write_service
                )
                observed["dma_commands"] += 1
                observed["dma_cycles"] += command_cycles
                observed["hbm_read_transactions"] += transactions
                observed["hbm_transferred_bytes_read"] += transferred
                observed["hbm_useful_bytes_read"] += useful
                observed["sram_bytes_written"] += useful
            elif command.opcode == Opcode.MATMUL_I8_I8_I32:
                kernel = kernel_by_index[command.kernel_index]
                if kernel["kind"] != "GEMM_I8_I8_I32":
                    raise SimulationError(
                        f"command {command.index} kernel kind mismatch"
                    )
                m, n, k = command.size0, command.size1, command.size2
                left_bytes = m * k
                weight_bytes = n * k
                output_bytes = m * n * 4
                left = _decode_values(
                    "i8",
                    sram.read(
                        command.source0,
                        left_bytes,
                        f"command {command.index} MATMUL input",
                    ),
                )
                weights = _decode_values(
                    "i8",
                    sram.read(
                        command.source1,
                        weight_bytes,
                        f"command {command.index} MATMUL weight",
                    ),
                )
                result: list[int] = []
                for batch in range(m):
                    for row in range(n):
                        accumulator = 0
                        for reduction in range(k):
                            accumulator = _checked_i32(
                                accumulator
                                + left[batch * k + reduction]
                                * weights[row * k + reduction],
                                f"command {command.index} MATMUL accumulation",
                            )
                        result.append(accumulator)
                sram.write(
                    command.destination,
                    _encode_values("i32", tuple(result)),
                    f"command {command.index} MATMUL output",
                )
                macs = m * n * k
                read_words0 = math.ceil(
                    left_bytes / deployment.capability.sram.word_bytes
                )
                read_words1 = math.ceil(
                    weight_bytes / deployment.capability.sram.word_bytes
                )
                bank0 = command.source0 // deployment.capability.sram.bytes_per_bank
                bank1 = command.source1 // deployment.capability.sram.bytes_per_bank
                if bank0 == bank1:
                    max_words = read_words0 + read_words1
                else:
                    max_words = max(read_words0, read_words1)
                read_cycles = (
                    deployment.capability.sram.read_latency_cycles
                    + math.ceil(
                        max_words
                        / deployment.capability.sram.read_ports_per_bank
                    )
                )
                compute_cycles = deployment.capability.tensor.setup_cycles + math.ceil(
                    macs
                    / (
                        deployment.capability.tensor.macs_per_cycle
                        * deployment.capability.tensor.count
                    )
                )
                write_cycles = (
                    deployment.capability.sram.write_latency_cycles
                    + math.ceil(
                        math.ceil(
                            output_bytes / deployment.capability.sram.word_bytes
                        )
                        / deployment.capability.sram.write_ports_per_bank
                    )
                )
                command_cycles = read_cycles + compute_cycles + write_cycles
                observed["tensor_commands"] += 1
                observed["tensor_cycles"] += command_cycles
                observed["scalar_multiply_operations"] += macs
                observed["scalar_accumulate_add_operations"] += macs
                observed["sram_bytes_read"] += left_bytes + weight_bytes
                observed["sram_bytes_written"] += output_bytes
                observed["semantic_operations_executed"] += 1
            elif command.opcode == Opcode.ADD_I32:
                kernel = kernel_by_index[command.kernel_index]
                if kernel["kind"] != "ADD_I32":
                    raise SimulationError(
                        f"command {command.index} kernel kind mismatch"
                    )
                elements = command.size0
                size = elements * 4
                left = _decode_values(
                    "i32",
                    sram.read(
                        command.source0,
                        size,
                        f"command {command.index} ADD input",
                    ),
                )
                right = _decode_values(
                    "i32",
                    sram.read(
                        command.source1,
                        size,
                        f"command {command.index} ADD weight",
                    ),
                )
                result = tuple(
                    _checked_i32(a + b, f"command {command.index} ADD")
                    for a, b in zip(left, right, strict=True)
                )
                sram.write(
                    command.destination,
                    _encode_values("i32", result),
                    f"command {command.index} ADD output",
                )
                read_words = math.ceil(size / deployment.capability.sram.word_bytes)
                bank0 = command.source0 // deployment.capability.sram.bytes_per_bank
                bank1 = command.source1 // deployment.capability.sram.bytes_per_bank
                max_words = read_words * 2 if bank0 == bank1 else read_words
                read_cycles = (
                    deployment.capability.sram.read_latency_cycles
                    + math.ceil(
                        max_words
                        / deployment.capability.sram.read_ports_per_bank
                    )
                )
                vector_cycles = deployment.capability.vector.setup_cycles + math.ceil(
                    elements
                    / (
                        deployment.capability.vector.elements_per_cycle
                        * deployment.capability.vector.count
                    )
                )
                write_cycles = (
                    deployment.capability.sram.write_latency_cycles
                    + math.ceil(
                        read_words
                        / deployment.capability.sram.write_ports_per_bank
                    )
                )
                command_cycles = read_cycles + vector_cycles + write_cycles
                observed["vector_commands"] += 1
                observed["vector_cycles"] += command_cycles
                observed["elementwise_add_operations"] += elements
                observed["sram_bytes_read"] += size * 2
                observed["sram_bytes_written"] += size
                observed["semantic_operations_executed"] += 1
            elif command.opcode == Opcode.COMPLETE:
                command_cycles = 1
                observed["completion_events"] += 1
                observed["control_cycles"] += command_cycles
            else:  # pragma: no cover - command decoder rejects unknown opcodes.
                raise SimulationError(
                    f"command {command.index} opcode is not executable"
                )
            observed["commands_executed"] += 1
            observed["cycles"] += command_cycles
            traces.append(
                {
                    "command_index": command.index,
                    "cycle_begin": before_cycle,
                    "cycle_end": observed["cycles"],
                    "engine": command.engine.name,
                    "opcode": command.opcode.name,
                }
            )

        expected = deployment.expectations["counters"]
        if observed != expected:
            differences = {
                key: {"expected": expected[key], "observed": observed[key]}
                for key in COUNTER_KEYS
                if observed[key] != expected[key]
            }
            raise SimulationError(f"counter reconciliation failed: {differences}")
        outputs: list[dict[str, Any]] = []
        for tensor_id in model.outputs:
            tensor = tensors[tensor_id]
            record = sram_records[tensor_id]
            payload = sram.read(
                record["address"],
                record["size_bytes"],
                f"output {tensor_id}",
            )
            outputs.append(
                {
                    "dtype": tensor.dtype,
                    "id": tensor_id,
                    "payload_sha256": sha256_bytes(payload),
                    "shape": list(tensor.resolved_shape(symbols)),
                    "values": list(_decode_values(tensor.dtype, payload)),
                }
            )
        return {
            "build_id": deployment.manifest["build_id"],
            "capability_id": deployment.capability.capability_id,
            "counter_reconciliation": "exact",
            "counters": observed,
            "model_id": model.model_id,
            "mode": mode,
            "outputs": outputs,
            "request_sha256": request_sha256,
            "schema": REPORT_SCHEMA,
            "semantic_sha256": deployment.manifest["semantic_sha256"],
            "status": "pass",
            "timing": {
                "clock_hz": deployment.capability.clock_hz,
                "cycles": observed["cycles"],
                "seconds": observed["cycles"] / deployment.capability.clock_hz,
            },
            "trace": traces,
        }
