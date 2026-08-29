"""Artifact-only functional simulator for the complete Qwen deployment.

The simulator consumes the published HBM shards, SRAM plan, Model Graph IR,
runtime request, and ABI 2.5 command stream.  It imports neither the physical
compiler nor its independent checker.  Every command is decoded, validated,
and accounted; contiguous matrix command groups are numerically fused only at
the 64-row output-block boundary, preserving the specified increasing-K
binary32 reduction exactly while avoiding hundreds of thousands of Python
kernel calls.

The immutable deployment is never modified.  Transaction-private and committed
KV state live in a separate runtime object and become visible atomically only
after terminal commit and COMPLETE both succeed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import struct
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.tensor_accelerator.common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from compiler.tensor_accelerator.hbm_shards import HBMShardError, HBMShardReader
from compiler.tensor_accelerator.production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from compiler.tensor_accelerator.production_command import (
    ABI_MAJOR,
    MATMUL_FINAL,
    MATMUL_INIT,
    NO_KERNEL,
    SELECTION_ABI_MINOR,
    Engine,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    decode,
)
from compiler.tensor_accelerator.production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)

from .attention import (
    AttentionKernelError,
    KVSnapshot,
    PreparedKV,
    commit_kv_group,
    empty_kv_snapshot,
    gqa_causal_attention_bf16,
    prepare_kv_append,
)
from .bf16 import (
    BF16KernelError,
    dense_bf16_linear_bf16,
)
from .elementwise import (
    ElementwiseKernelError,
    bf16_add_rne,
    qwen3_silu_mul_bf16,
)
from .rmsnorm import RMSNormKernelError, rms_norm_bf16
from .rope import RoPEKernelError, rope_bf16


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_deployment.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_request.v1"
CHECK_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_physical_check.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_execution.v1"
SIMULATOR_VERSION = "tensor-accelerator-qwen-full-model-simulator-0.1.0"

MANIFEST_PATH = "deployment_manifest.json"
PLAN_PATH = "physical/physical_plan.json"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
CHECK_PATH = "checks/independent_check.json"
MODEL_GRAPH_PATH = "source/model_graph.v2.json"
CAPABILITY_PATH = "capability.json"

MODEL_ID = "qwen3-8b"
OPERATION_COUNT = 617
TENSOR_COUNT = 1053
WEIGHT_COUNT = 399
STATE_COUNT = 36
LAYER_COUNT = 36
CONTEXT_CAPACITY = 8000
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
VOCABULARY_SIZE = 151936
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
N_TILE = 64
K_TILE = 256
BF16_BYTES = 2
TILE_BYTES = N_TILE * K_TILE * BF16_BYTES
EMBEDDING_ROW_BYTES = HIDDEN_WIDTH * BF16_BYTES
KV_TOKEN_BYTES = KEY_VALUE_HEADS * HEAD_DIM * BF16_BYTES
EXPECTED_COMMAND_COUNT = 924386

STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")


class QwenFullModelSimulationError(ArtifactError):
    """Raised when the retained deployment cannot execute causally and exactly."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = dict(body)
    value[field] = sha256_bytes(canonical_json_bytes(body))
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelSimulationError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise QwenFullModelSimulationError(
            f"{label} must be a safe relative POSIX path"
        )
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or parsed.as_posix() != value
    ):
        raise QwenFullModelSimulationError(
            f"{label} must be a safe relative POSIX path"
        )
    return value


def _canonical(path: Path, label: str) -> dict[str, Any]:
    value = load_strict_json(path)
    if path.read_bytes() != canonical_json_bytes(value):
        raise QwenFullModelSimulationError(f"{label} is not canonical JSON")
    return value


def _artifact(root: Path, relative: str, label: str) -> Path:
    candidate = root / _safe_relative(relative, label)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise QwenFullModelSimulationError(f"cannot resolve {label}: {exc}") from exc
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise QwenFullModelSimulationError(f"{label} escapes the deployment")
    if candidate.is_symlink() or not resolved.is_file():
        raise QwenFullModelSimulationError(f"{label} is not a regular file")
    return resolved


def _u16_payload(value: np.ndarray[Any, Any]) -> bytes:
    return np.ascontiguousarray(value, dtype="<u2").tobytes(order="C")


def _payload_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class _SRAMSlot:
    slot_id: str
    address: int
    allocated_bytes: int
    logical_capacity: int
    storage: bytearray

    @classmethod
    def create(cls, record: Mapping[str, Any]) -> _SRAMSlot:
        allocated = int(record["allocated_bytes"])
        capacity = int(record["capacity_bytes"])
        if allocated < capacity or allocated <= 0:
            raise QwenFullModelSimulationError(
                f"SRAM slot {record.get('id')!r} capacity differs"
            )
        return cls(
            str(record["id"]),
            int(record["address"]),
            allocated,
            capacity,
            bytearray(allocated),
        )

    def contains(self, address: int, size: int) -> bool:
        return (
            self.address <= address
            and address + size <= self.address + self.allocated_bytes
        )

    def read(self, address: int, size: int) -> bytes:
        if size < 0 or not self.contains(address, size):
            raise QwenFullModelSimulationError(
                f"SRAM read escapes slot {self.slot_id!r}"
            )
        start = address - self.address
        return bytes(self.storage[start : start + size])

    def write(self, address: int, payload: bytes) -> None:
        if not self.contains(address, len(payload)):
            raise QwenFullModelSimulationError(
                f"SRAM write escapes slot {self.slot_id!r}"
            )
        start = address - self.address
        self.storage[start : start + len(payload)] = payload


def _slots(raw: Mapping[str, Any]) -> dict[str, _SRAMSlot]:
    records = raw.get("slots")
    if not isinstance(records, list) or len(records) != 18:
        raise QwenFullModelSimulationError("physical SRAM slot table differs")
    result: dict[str, _SRAMSlot] = {}
    for record in records:
        slot = _SRAMSlot.create(record)
        if slot.slot_id in result:
            raise QwenFullModelSimulationError("SRAM slot identifiers are not unique")
        result[slot.slot_id] = slot
    if len(result) != len(records):
        raise QwenFullModelSimulationError("SRAM slot identifiers are not unique")
    ordered = list(result.values())
    for index, slot in enumerate(ordered):
        for other in ordered[:index]:
            if (
                slot.address < other.address + other.allocated_bytes
                and other.address < slot.address + slot.allocated_bytes
            ):
                raise QwenFullModelSimulationError(
                    f"SRAM slots {other.slot_id!r} and {slot.slot_id!r} overlap"
                )
    return result


def _slot_for(slots: Mapping[str, _SRAMSlot], address: int, size: int) -> _SRAMSlot:
    found = [slot for slot in slots.values() if slot.contains(address, size)]
    if len(found) != 1:
        raise QwenFullModelSimulationError(
            f"SRAM address 0x{address:x}+{size} maps to {len(found)} slots"
        )
    return found[0]


def _finite_bf16(payload: bytes, label: str) -> np.ndarray[Any, np.dtype[np.uint16]]:
    if len(payload) % BF16_BYTES:
        raise QwenFullModelSimulationError(f"{label} has an odd BF16 byte count")
    codes = np.frombuffer(payload, dtype="<u2")
    if np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise QwenFullModelSimulationError(f"{label} contains BF16 NaN or infinity")
    return codes


def _untile_n_block(
    payload: bytes, details: Mapping[str, Any]
) -> np.ndarray[Any, np.dtype[np.uint16]]:
    expected = int(details["n_tile"]) * int(details["k"]) * BF16_BYTES
    if len(payload) != expected:
        raise QwenFullModelSimulationError("matrix N-block byte count differs")
    tiled = _finite_bf16(payload, "matrix N-block").reshape(
        int(details["k_tiles"]),
        int(details["n_tile"]),
        int(details["k_tile"]),
    )
    return np.ascontiguousarray(
        tiled.transpose(1, 0, 2).reshape(int(details["n_tile"]), int(details["k"])),
        dtype=np.uint16,
    )


class QwenFullModelSimulator:
    """Loaded immutable deployment plus separately held transactional KV state."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: dict[str, Any],
        plan: dict[str, Any],
        model: ProductionModelGraph,
        capability: ProductionCapability,
        commands: tuple[ProductionCommand, ...],
        request: dict[str, Any],
        hbm: HBMShardReader,
        hbm_hashes_verified: bool,
    ) -> None:
        self._root = root
        self._manifest = manifest
        self._plan = plan
        self._model = model
        self._capability = capability
        self._commands = commands
        self._request = request
        self._hbm = hbm
        self._hbm_hashes_verified = hbm_hashes_verified
        self._closed = False

        self._slot_records = {item["id"]: item for item in plan["sram"]["slots"]}
        self._assignments = {
            item["tensor_id"]: item for item in plan["sram"]["tensor_assignments"]
        }
        self._staged = {
            item["kernel_index"]: item
            for item in plan["sram"]["staged_weight_assignments"]
        }
        self._weights = {
            item["consumer_kernel_index"]: item for item in plan["hbm"]["weights"]
        }
        self._state_records = {
            item["resource_id"]: item for item in plan["hbm"]["states"]
        }
        self._ranges = tuple(plan["command_program"]["kernel_command_ranges"])
        if (
            len(self._slot_records) != 18
            or len(self._assignments) != 617
            or len(self._staged) != 145
            or len(self._weights) != WEIGHT_COUNT
            or len(self._state_records) != STATE_COUNT
            or len(self._ranges) != OPERATION_COUNT
        ):
            self.close()
            raise QwenFullModelSimulationError(
                "physical execution lookup tables are incomplete or ambiguous"
            )
        self._states = self._initial_states()

    @classmethod
    def load(
        cls,
        deployment: Path,
        *,
        verify_hbm_hashes: bool = True,
    ) -> QwenFullModelSimulator:
        """Authenticate and load a complete published deployment."""

        if not isinstance(verify_hbm_hashes, bool):
            raise QwenFullModelSimulationError("verify_hbm_hashes must be a boolean")
        try:
            root = Path(deployment).resolve(strict=True)
        except OSError as exc:
            raise QwenFullModelSimulationError(
                f"cannot resolve deployment: {exc}"
            ) from exc
        if not root.is_dir():
            raise QwenFullModelSimulationError("deployment must be a directory")
        hbm: HBMShardReader | None = None
        try:
            manifest = _canonical(
                _artifact(root, MANIFEST_PATH, "deployment manifest"),
                "deployment manifest",
            )
            _identity(manifest, "build_id", "deployment manifest")
            exact_keys(
                manifest,
                {
                    "artifacts",
                    "build_class",
                    "build_id",
                    "capability_id",
                    "capacity_certificate_id",
                    "claim_boundary",
                    "command_abi",
                    "compiler_version",
                    "graph_id",
                    "independent_check_id",
                    "kernel_ir_id",
                    "physical_plan_id",
                    "schema",
                    "source_lock_id",
                },
                set(),
                "deployment manifest",
            )
            if (
                manifest["schema"] != MANIFEST_SCHEMA
                or manifest["build_class"]
                != "independently_reconstructed_physical_deployment"
                or manifest["command_abi"]
                != {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR}
                or manifest["claim_boundary"]
                != {
                    "complete_checkpoint_payload_deployment": True,
                    "complete_command_template": True,
                    "complete_graph_physical_lowering": True,
                    "full_model_execution": False,
                    "timing_or_performance": False,
                }
            ):
                raise QwenFullModelSimulationError(
                    "deployment manifest boundary differs"
                )

            raw_artifacts = manifest["artifacts"]
            if not isinstance(raw_artifacts, list) or len(raw_artifacts) != 31:
                raise QwenFullModelSimulationError("manifest artifact count differs")
            artifacts: dict[str, dict[str, Any]] = {}
            previous_path = ""
            for index, record in enumerate(raw_artifacts):
                if not isinstance(record, dict):
                    raise QwenFullModelSimulationError(
                        f"manifest artifact {index} must be an object"
                    )
                exact_keys(
                    record,
                    {"path", "role", "sha256", "size_bytes"},
                    set(),
                    f"manifest artifact {index}",
                )
                relative = _safe_relative(
                    record["path"], f"manifest artifact {index}.path"
                )
                require_sha256(record["sha256"], f"manifest artifact {index}.sha256")
                if (
                    relative <= previous_path
                    or relative in artifacts
                    or isinstance(record["size_bytes"], bool)
                    or not isinstance(record["size_bytes"], int)
                    or record["size_bytes"] < 1
                    or not isinstance(record["role"], str)
                    or not record["role"]
                ):
                    raise QwenFullModelSimulationError(
                        "manifest artifacts are not unique, sorted, and bounded"
                    )
                previous_path = relative
                artifacts[relative] = record

            observed_files = {
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
            }
            expected_files = set(artifacts) | {MANIFEST_PATH}
            if observed_files != expected_files:
                raise QwenFullModelSimulationError(
                    "deployment file set differs from the final manifest"
                )
            for path in root.rglob("*"):
                if path.is_symlink():
                    raise QwenFullModelSimulationError(
                        f"deployment contains a symbolic link: {path.relative_to(root)}"
                    )

            for relative, record in artifacts.items():
                if record["role"] == "hbm_shard":
                    continue
                path = _artifact(root, relative, f"artifact {relative}")
                digest, size = sha256_file(path)
                if (digest, size) != (record["sha256"], record["size_bytes"]):
                    raise QwenFullModelSimulationError(
                        f"manifest artifact {relative!r} differs"
                    )

            plan = _canonical(
                _artifact(root, PLAN_PATH, "physical plan"), "physical plan"
            )
            _identity(plan, "physical_plan_id", "physical plan")
            check = _canonical(
                _artifact(root, CHECK_PATH, "independent physical check"),
                "independent physical check",
            )
            _identity(check, "check_id", "independent physical check")
            source_lock = _canonical(
                _artifact(root, "source.lock.json", "physical source lock"),
                "physical source lock",
            )
            _identity(source_lock, "source_lock_id", "physical source lock")
            capacity = _canonical(
                _artifact(
                    root, "physical/capacity_certificate.json", "capacity certificate"
                ),
                "capacity certificate",
            )
            _identity(capacity, "capacity_certificate_id", "capacity certificate")
            request = _canonical(
                _artifact(root, REQUEST_PATH, "execution request"),
                "execution request",
            )
            _identity(request, "request_id", "execution request")
            model = load_production_model_graph(
                _artifact(root, MODEL_GRAPH_PATH, "source Model Graph IR")
            )
            capability = load_production_capability(
                _artifact(root, CAPABILITY_PATH, "deployed capability")
            )
            command_payload = _artifact(
                root, COMMAND_PATH, "command program"
            ).read_bytes()
            commands = decode(command_payload)

            if (
                plan.get("schema") != PHYSICAL_PLAN_SCHEMA
                or plan.get("physical_plan_id") != manifest["physical_plan_id"]
                or plan.get("source_lock_id") != source_lock["source_lock_id"]
                or plan.get("capacity_certificate_id")
                != capacity["capacity_certificate_id"]
                or plan.get("capability_id") != capability.capability_id
                or plan.get("graph_id") != model.graph_id
                or check.get("schema") != CHECK_SCHEMA
                or check.get("status") != "pass"
                or not isinstance(check.get("checks"), dict)
                or not check["checks"]
                or not all(value is True for value in check["checks"].values())
                or check.get("check_id") != manifest["independent_check_id"]
                or check.get("physical_plan_id") != plan["physical_plan_id"]
                or source_lock.get("source_lock_id") != manifest["source_lock_id"]
                or capacity.get("capacity_certificate_id")
                != manifest["capacity_certificate_id"]
                or capability.capability_id != manifest["capability_id"]
                or model.graph_id != manifest["graph_id"]
                or model.model_id != MODEL_ID
                or len(model.operations) != OPERATION_COUNT
                or len(model.tensors) != TENSOR_COUNT
                or len(model.state_resources) != STATE_COUNT
                or len(commands) != EXPECTED_COMMAND_COUNT
            ):
                raise QwenFullModelSimulationError(
                    "deployment graph/check/capacity binding differs"
                )
            program = plan.get("command_program")
            if (
                not isinstance(program, dict)
                or program.get("abi")
                != {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR}
                or program.get("path") != COMMAND_PATH
                or program.get("command_count") != len(commands)
                or program.get("size_bytes") != len(command_payload)
                or program.get("sha256") != hashlib.sha256(command_payload).hexdigest()
            ):
                raise QwenFullModelSimulationError("command-program binding differs")

            image = plan.get("hbm", {}).get("image")
            if not isinstance(image, dict) or not isinstance(image.get("shards"), list):
                raise QwenFullModelSimulationError("HBM image record differs")
            for shard in image["shards"]:
                artifact_record = artifacts.get(shard["path"])
                if artifact_record != {
                    "path": shard["path"],
                    "role": "hbm_shard",
                    "sha256": shard["sha256"],
                    "size_bytes": shard["size_bytes"],
                }:
                    raise QwenFullModelSimulationError(
                        "HBM shard differs between plan and manifest"
                    )
            hbm = HBMShardReader(root, image["shards"], verify_hashes=verify_hbm_hashes)
            if hbm.total_size != image.get("size_bytes"):
                raise QwenFullModelSimulationError("logical HBM image size differs")
            return cls(
                root=root,
                manifest=manifest,
                plan=plan,
                model=model,
                capability=capability,
                commands=commands,
                request=request,
                hbm=hbm,
                hbm_hashes_verified=verify_hbm_hashes,
            )
        except QwenFullModelSimulationError:
            if hbm is not None:
                hbm.close()
            raise
        except (
            ArtifactError,
            HBMShardError,
            OSError,
            ProductionCapabilityError,
            ProductionCommandError,
            ProductionModelGraphError,
            TypeError,
            ValueError,
        ) as exc:
            if hbm is not None:
                hbm.close()
            raise QwenFullModelSimulationError(
                f"cannot load complete Qwen deployment: {exc}"
            ) from exc

    def _hbm_read(self, address: int, size: int) -> bytes:
        base = int(self._plan["hbm"]["base_address"])
        offset = address - base
        if offset < 0:
            raise QwenFullModelSimulationError("HBM address precedes image base")
        return self._hbm.read(offset, size)

    def _initial_states(self) -> dict[str, KVSnapshot]:
        metadata_record = self._plan["hbm"]["metadata_table"]
        descriptor_record = self._plan["hbm"]["descriptor_table"]
        metadata = self._hbm_read(
            metadata_record["address"], metadata_record["size_bytes"]
        )
        descriptors = self._hbm_read(
            descriptor_record["address"], descriptor_record["size_bytes"]
        )
        result: dict[str, KVSnapshot] = {}
        for layer in range(LAYER_COUNT):
            state = self._state_records[f"kv.layer.{layer}"]
            fields = STATE_METADATA.unpack_from(metadata, layer * STATE_METADATA.size)
            descriptor = TRANSACTION_DESCRIPTOR.unpack_from(
                descriptors, layer * TRANSACTION_DESCRIPTOR.size
            )
            if fields != (
                STATE_MAGIC,
                0,
                0,
                CONTEXT_CAPACITY,
                state["key_address"],
                state["value_address"],
                layer,
                bytes(8),
            ):
                raise QwenFullModelSimulationError(
                    f"initial state metadata for layer {layer} differs"
                )
            if descriptor != (
                TRANSACTION_MAGIC,
                self._request["transaction_id"],
                0,
                0,
                1,
                1,
                metadata_record["address"] + layer * STATE_METADATA.size,
                bytes(8),
            ):
                raise QwenFullModelSimulationError(
                    f"initial transaction descriptor for layer {layer} differs"
                )
            result[state["resource_id"]] = empty_kv_snapshot(
                state["resource_id"], capacity=CONTEXT_CAPACITY
            )
        return result

    @property
    def build_id(self) -> str:
        return str(self._manifest["build_id"])

    @property
    def state_generations(self) -> tuple[int, ...]:
        return tuple(
            self._states[f"kv.layer.{layer}"].generation for layer in range(LAYER_COUNT)
        )

    @property
    def state_lengths(self) -> tuple[int, ...]:
        return tuple(
            self._states[f"kv.layer.{layer}"].length for layer in range(LAYER_COUNT)
        )

    def close(self) -> None:
        if not self._closed:
            self._hbm.close()
            self._closed = True

    def __enter__(self) -> QwenFullModelSimulator:
        if self._closed:
            raise QwenFullModelSimulationError("simulator is closed")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _validate_request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        exact_keys(
            dict(request),
            {
                "expected_generations",
                "graph_id",
                "last_row_index",
                "phase",
                "position_end",
                "position_start",
                "request_id",
                "schema",
                "span_tokens",
                "token_id",
                "transaction_id",
            },
            set(),
            "full-model execution request",
        )
        value = dict(request)
        _identity(value, "request_id", "full-model execution request")
        expected = value["expected_generations"]
        integers = {
            field: value[field]
            for field in (
                "last_row_index",
                "position_end",
                "position_start",
                "span_tokens",
                "token_id",
                "transaction_id",
            )
        }
        if any(
            isinstance(item, bool) or not isinstance(item, int)
            for item in integers.values()
        ):
            raise QwenFullModelSimulationError(
                "execution request integer fields differ"
            )
        if (
            value["schema"] != REQUEST_SCHEMA
            or value["graph_id"] != self._model.graph_id
            or value["phase"] not in {"prefill", "decode"}
            or value["span_tokens"] != 1
            or value["last_row_index"] != 0
            or value["position_start"] < 0
            or value["position_end"] != value["position_start"] + 1
            or value["position_end"] > CONTEXT_CAPACITY
            or not 0 <= value["token_id"] < VOCABULARY_SIZE
            or not 1 <= value["transaction_id"] < 1 << 64
            or not isinstance(expected, list)
            or len(expected) != STATE_COUNT
            or any(
                isinstance(generation, bool)
                or not isinstance(generation, int)
                or generation < 0
                or generation >= 1 << 64
                for generation in expected
            )
        ):
            raise QwenFullModelSimulationError("execution request bounds differ")
        if value != self._request:
            raise QwenFullModelSimulationError(
                "execution request v1 differs from the deployed fixed request"
            )
        current_generations = list(self.state_generations)
        current_lengths = list(self.state_lengths)
        if expected != current_generations:
            raise QwenFullModelSimulationError(
                "execution request generations are stale"
            )
        if current_lengths != [value["position_start"]] * STATE_COUNT:
            raise QwenFullModelSimulationError(
                "execution request position differs from committed KV lengths"
            )
        expected_phase = "prefill" if value["position_start"] == 0 else "decode"
        if value["phase"] != expected_phase:
            raise QwenFullModelSimulationError(
                "execution request phase differs from committed state"
            )
        return value

    @staticmethod
    def _account_command(counters: Counter[str], command: ProductionCommand) -> None:
        counters["commands.total"] += 1
        counters[f"commands.{command.opcode.name}"] += 1

    @staticmethod
    def _expect_command(
        observed: ProductionCommand,
        expected: ProductionCommand,
    ) -> None:
        if observed != expected:
            raise QwenFullModelSimulationError(
                f"command {expected.index} differs during causal execution: "
                f"observed={observed.to_dict()!r}, expected={expected.to_dict()!r}"
            )

    def _operation_commands(
        self, operation: ProductionOperation
    ) -> tuple[ProductionCommand, ...]:
        record = self._ranges[operation.index]
        if (
            record.get("kernel_index") != operation.index
            or record.get("operation_id") != operation.operation_id
            or isinstance(record.get("command_start"), bool)
            or not isinstance(record.get("command_start"), int)
            or isinstance(record.get("command_count"), bool)
            or not isinstance(record.get("command_count"), int)
            or record["command_count"] < 1
        ):
            raise QwenFullModelSimulationError(
                f"kernel range for {operation.operation_id!r} differs"
            )
        start = record["command_start"]
        end = start + record["command_count"]
        commands = self._commands[start:end]
        if (
            len(commands) != record["command_count"]
            or commands[0].index != start
            or commands[-1].index + 1 != end
        ):
            raise QwenFullModelSimulationError(
                f"kernel range for {operation.operation_id!r} is not contiguous"
            )
        return commands

    @staticmethod
    def _one_state_effect(operation: ProductionOperation, action: str) -> str:
        resources = [
            effect.state_id for effect in operation.effects if effect.action == action
        ]
        if len(resources) != 1:
            raise QwenFullModelSimulationError(
                f"operation {operation.operation_id!r} has ambiguous {action} state"
            )
        return resources[0]

    def _matrix_operation(
        self,
        *,
        operation: ProductionOperation,
        commands: Sequence[ProductionCommand],
        slots: Mapping[str, _SRAMSlot],
        input_payload: bytes,
        input_address: int,
        output_address: int,
        counters: Counter[str],
    ) -> tuple[bytes, int]:
        record = self._weights.get(operation.index)
        if record is None or record.get("layout") != "n_major_k_minor_tiles_bf16":
            raise QwenFullModelSimulationError(
                f"matrix weight for {operation.operation_id!r} differs"
            )
        details = record["layout_details"]
        k = int(details["k"])
        n = int(details["n"])
        k_tiles = int(details["k_tiles"])
        n_tiles = int(details["n_tiles"])
        if (
            details.get("n_tile") != N_TILE
            or details.get("k_tile") != K_TILE
            or details.get("tile_bytes") != TILE_BYTES
            or details.get("tile_count") != k_tiles * n_tiles
            or len(input_payload) != k * BF16_BYTES
            or len(commands) != 2 * k_tiles * n_tiles
        ):
            raise QwenFullModelSimulationError(
                f"matrix geometry for {operation.operation_id!r} differs"
            )
        inputs = _finite_bf16(
            input_payload, f"matrix input {operation.operation_id}"
        ).reshape(1, k)
        output = np.empty((1, n), dtype=np.uint16)
        cursor = 0
        saturation = 0
        block_bytes = N_TILE * k * BF16_BYTES
        for n_index in range(n_tiles):
            n_start = n_index * N_TILE
            block_address = int(record["address"]) + n_index * block_bytes
            block_payload = self._hbm_read(block_address, block_bytes)
            weights = _untile_n_block(block_payload, details)
            for k_index in range(k_tiles):
                k_start = k_index * K_TILE
                tile_index = n_index * k_tiles + k_index
                dma = commands[cursor]
                matrix = commands[cursor + 1]
                expected_dma = ProductionCommand(
                    index=dma.index,
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=int(record["address"]) + tile_index * TILE_BYTES,
                    destination=slots["weight_tile"].address,
                    size0=TILE_BYTES,
                )
                flags = (MATMUL_INIT if k_index == 0 else 0) | (
                    MATMUL_FINAL if k_index + 1 == k_tiles else 0
                )
                expected_matrix = ProductionCommand(
                    index=matrix.index,
                    opcode=Opcode.MATMUL_BF16_TILE,
                    engine=Engine.TENSOR,
                    flags=flags,
                    kernel_index=operation.index,
                    source0=input_address + k_start * BF16_BYTES,
                    source1=slots["weight_tile"].address,
                    destination=slots["accumulator"].address,
                    auxiliary=output_address + n_start * BF16_BYTES,
                    size0=1,
                    size1=N_TILE,
                    size2=K_TILE,
                )
                self._expect_command(dma, expected_dma)
                self._expect_command(matrix, expected_matrix)
                self._account_command(counters, dma)
                self._account_command(counters, matrix)
                counters["hbm.useful_bytes_read"] += TILE_BYTES
                counters["hbm.transferred_bytes_read"] += align_up(
                    TILE_BYTES, self._capability.hbm.burst_bytes
                )
                counters["sram.dma_bytes_written"] += TILE_BYTES
                counters["matrix.input_bytes_read"] += K_TILE * BF16_BYTES
                counters["matrix.weight_bytes_read"] += TILE_BYTES
                if k_index:
                    counters["matrix.accumulator_bytes_read"] += N_TILE * 4
                counters["matrix.accumulator_bytes_written"] += N_TILE * 4
                if k_index + 1 == k_tiles:
                    counters["matrix.output_bytes_written"] += N_TILE * BF16_BYTES
                scalar = N_TILE * K_TILE
                counters["arithmetic.matrix_multiplications"] += scalar
                counters["arithmetic.matrix_accumulation_additions"] += scalar
                cursor += 2
            try:
                result = dense_bf16_linear_bf16(
                    inputs,
                    weights,
                    input_tile_rows=1,
                    output_tile_rows=N_TILE,
                )
            except BF16KernelError as exc:
                raise QwenFullModelSimulationError(
                    f"matrix execution failed for {operation.operation_id!r}: {exc}"
                ) from exc
            output[:, n_start : n_start + N_TILE] = result.values
            saturation += result.output_saturated_element_count
            counters["matrix.fused_output_blocks"] += 1
        if cursor != len(commands):
            raise QwenFullModelSimulationError(
                f"matrix command coverage for {operation.operation_id!r} differs"
            )
        return _u16_payload(output), saturation

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        """Execute one complete one-token forward transaction artifact-only."""

        if self._closed:
            raise QwenFullModelSimulationError("simulator is closed")
        if not self._hbm_hashes_verified:
            raise QwenFullModelSimulationError(
                "full data-bearing execution requires SHA-256 verification of every "
                "HBM shard"
            )
        if request_path is None:
            raw_request = self._request
        else:
            raw_request = _canonical(Path(request_path), "execution request")
        request = self._validate_request(raw_request)
        slots = _slots(self._plan["sram"])
        owners: dict[str, str] = {}
        produced: set[str] = {
            tensor.tensor_id for tensor in self._model.tensors if tensor.role == "input"
        }
        state_handles: dict[str, str] = {}
        prepared: dict[str, PreparedKV] = {}
        staged_states: dict[str, KVSnapshot] | None = None
        counters: Counter[str] = Counter()
        events: list[dict[str, Any]] = []
        captures: dict[str, dict[str, Any]] = {}
        saturation_by_kernel: dict[str, int] = {}

        runtime = slots["runtime_ids"]
        runtime.write(
            runtime.address,
            struct.pack(
                "<IIII",
                request["token_id"],
                request["position_start"],
                request["last_row_index"],
                0,
            ),
        )
        owners[runtime.slot_id] = "runtime.request_fields"

        def assignment(tensor_id: str) -> Mapping[str, Any]:
            record = self._assignments.get(tensor_id)
            if record is None:
                raise QwenFullModelSimulationError(
                    f"tensor {tensor_id!r} has no SRAM assignment"
                )
            return record

        def tensor_slot(tensor_id: str) -> _SRAMSlot:
            record = assignment(tensor_id)
            try:
                return slots[record["slot_id"]]
            except KeyError as exc:
                raise QwenFullModelSimulationError(
                    f"tensor {tensor_id!r} references an unknown SRAM slot"
                ) from exc

        def tensor_address(tensor_id: str) -> int:
            return tensor_slot(tensor_id).address

        def read_tensor(tensor_id: str) -> bytes:
            record = assignment(tensor_id)
            slot = tensor_slot(tensor_id)
            expected_owner = tensor_id
            if owners.get(slot.slot_id) != expected_owner:
                raise QwenFullModelSimulationError(
                    f"tensor {tensor_id!r} is not live in slot {slot.slot_id!r}"
                )
            return slot.read(slot.address, int(record["logical_bytes"]))

        def capture(tensor_id: str, payload: bytes) -> dict[str, Any]:
            record = {
                "payload_sha256": _payload_sha256(payload),
                "size_bytes": len(payload),
            }
            captures[tensor_id] = record
            return record

        def write_tensor(tensor_id: str, payload: bytes) -> dict[str, Any]:
            record = assignment(tensor_id)
            if len(payload) != record["logical_bytes"]:
                raise QwenFullModelSimulationError(
                    f"tensor {tensor_id!r} payload size differs"
                )
            slot = tensor_slot(tensor_id)
            slot.write(slot.address, payload)
            owners[slot.slot_id] = tensor_id
            produced.add(tensor_id)
            return capture(tensor_id, payload)

        def account_dma(command: ProductionCommand, payload_size: int) -> None:
            self._account_command(counters, command)
            counters["hbm.useful_bytes_read"] += payload_size
            counters["hbm.transferred_bytes_read"] += align_up(
                payload_size, self._capability.hbm.burst_bytes
            )
            counters["sram.dma_bytes_written"] += payload_size

        for operation in self._model.operations:
            commands = self._operation_commands(operation)
            event: dict[str, Any] = {
                "command_count": len(commands),
                "command_start": commands[0].index,
                "kernel_index": operation.index,
                "kind": operation.kind,
                "operation_id": operation.operation_id,
            }
            for tensor_id in operation.inputs:
                tensor = self._model.tensor_by_id[tensor_id]
                if (
                    tensor.role in {"activation", "output"}
                    and tensor_id not in produced
                ):
                    raise QwenFullModelSimulationError(
                        f"operation {operation.operation_id!r} reads unproduced tensor "
                        f"{tensor_id!r}"
                    )

            if operation.kind == "EMBEDDING_LOOKUP":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError(
                        "embedding command count differs"
                    )
                record = self._weights[operation.index]
                command = commands[0]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=record["address"],
                    source1=runtime.address,
                    destination=tensor_address(operation.outputs[0]),
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=VOCABULARY_SIZE,
                    size3=4,
                )
                self._expect_command(command, expected)
                index = struct.unpack("<I", runtime.read(command.source1, 4))[0]
                if index >= command.size2:
                    raise QwenFullModelSimulationError(
                        "embedding index is out of range"
                    )
                source = command.source0 + index * command.size1
                payload = self._hbm_read(source, command.size0)
                account_dma(command, len(payload))
                event["logical_index"] = index
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "RMS_NORM":
                if len(commands) != 2:
                    raise QwenFullModelSimulationError("RMSNorm command count differs")
                record = self._weights[operation.index]
                stage = self._staged[operation.index]
                stage_slot = slots[stage["slot_id"]]
                dma, command = commands
                expected_dma = ProductionCommand(
                    index=dma.index,
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=record["address"],
                    destination=stage_slot.address,
                    size0=record["size_bytes"],
                )
                width = int(operation.attributes["normalization_width"])
                output_bytes = int(assignment(operation.outputs[0])["logical_bytes"])
                rows = output_bytes // (width * BF16_BYTES)
                expected_command = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.RMSNORM_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=stage_slot.address,
                    destination=tensor_address(operation.outputs[0]),
                    size0=rows,
                    size1=width,
                    size2=command.size2,
                )
                self._expect_command(dma, expected_dma)
                if command.size2 != 0x358637BD:
                    raise QwenFullModelSimulationError("RMSNorm epsilon differs")
                self._expect_command(command, expected_command)
                weight_payload = self._hbm_read(dma.source0, dma.size0)
                stage_slot.write(stage_slot.address, weight_payload)
                owners[stage_slot.slot_id] = f"weight:{stage['tensor_id']}"
                account_dma(dma, len(weight_payload))
                input_payload = read_tensor(operation.inputs[0])
                input_codes = _finite_bf16(
                    input_payload, f"RMSNorm input {operation.operation_id}"
                ).reshape(rows, width)
                weight_codes = _finite_bf16(
                    stage_slot.read(stage_slot.address, dma.size0),
                    f"RMSNorm weight {operation.operation_id}",
                )
                try:
                    result = rms_norm_bf16(
                        input_codes, weight_codes, epsilon_code=command.size2
                    )
                except RMSNormKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"RMSNorm execution failed for {operation.operation_id!r}: {exc}"
                    ) from exc
                self._account_command(counters, command)
                elements = rows * width
                counters["sram.rmsnorm_input_bytes_read"] += len(input_payload)
                counters["sram.rmsnorm_weight_bytes_read"] += len(weight_payload)
                counters["sram.rmsnorm_output_bytes_written"] += elements * BF16_BYTES
                counters["arithmetic.rmsnorm_squares"] += elements
                counters["arithmetic.rmsnorm_reduction_additions"] += rows * (width - 1)
                counters["arithmetic.rmsnorm_mean_divisions"] += rows
                counters["arithmetic.rmsnorm_epsilon_additions"] += rows
                counters["arithmetic.rmsnorm_rsqrt"] += rows
                counters["arithmetic.rmsnorm_normalization_multiplications"] += elements
                counters["arithmetic.rmsnorm_weight_multiplications"] += elements
                saturation = (
                    result.normalized_saturated_element_count
                    + result.output_saturated_element_count
                )
                saturation_by_kernel[str(operation.index)] = saturation
                payload = _u16_payload(result.values)
                event["diagnostics"] = {
                    "inverse_rms_sha256": _payload_sha256(
                        np.ascontiguousarray(
                            result.inverse_rms_codes, dtype="<u4"
                        ).tobytes()
                    ),
                    "mean_square_sha256": _payload_sha256(
                        np.ascontiguousarray(
                            result.mean_square_codes, dtype="<u4"
                        ).tobytes()
                    ),
                    "normalized_sha256": _payload_sha256(
                        _u16_payload(result.normalized_values)
                    ),
                }
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "MATMUL":
                input_payload = read_tensor(operation.inputs[0])
                payload, saturation = self._matrix_operation(
                    operation=operation,
                    commands=commands,
                    slots=slots,
                    input_payload=input_payload,
                    input_address=tensor_address(operation.inputs[0]),
                    output_address=tensor_address(operation.outputs[0]),
                    counters=counters,
                )
                saturation_by_kernel[str(operation.index)] = saturation
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "ROPE":
                if len(commands) != 2:
                    raise QwenFullModelSimulationError("RoPE command count differs")
                dma, command = commands
                coefficient = self._plan["hbm"]["coefficient_table"]
                coefficient_slot = slots["rope_coefficients"]
                expected_dma = ProductionCommand(
                    index=dma.index,
                    opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=coefficient["address"],
                    source1=runtime.address + 4,
                    destination=coefficient_slot.address,
                    size0=coefficient["row_bytes"],
                    size1=coefficient["row_bytes"],
                    size2=CONTEXT_CAPACITY,
                    size3=4,
                )
                expected_command = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.ROPE_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=tensor_address(operation.outputs[0]),
                    auxiliary=tensor_address(operation.outputs[1]),
                    size0=QUERY_HEADS,
                    size1=KEY_VALUE_HEADS,
                    size2=HEAD_DIM,
                    size3=coefficient_slot.address,
                )
                self._expect_command(dma, expected_dma)
                self._expect_command(command, expected_command)
                position = struct.unpack("<I", runtime.read(dma.source1, 4))[0]
                if position >= dma.size2:
                    raise QwenFullModelSimulationError("RoPE position is out of range")
                coefficient_payload = self._hbm_read(
                    dma.source0 + position * dma.size1, dma.size0
                )
                coefficient_slot.write(coefficient_slot.address, coefficient_payload)
                owners[coefficient_slot.slot_id] = "rope.coefficient_row"
                account_dma(dma, len(coefficient_payload))
                query_payload = read_tensor(operation.inputs[0])
                key_payload = read_tensor(operation.inputs[1])
                try:
                    result = rope_bf16(
                        _finite_bf16(query_payload, "RoPE query").reshape(
                            QUERY_HEADS, HEAD_DIM
                        ),
                        _finite_bf16(key_payload, "RoPE key").reshape(
                            KEY_VALUE_HEADS, HEAD_DIM
                        ),
                        _finite_bf16(coefficient_payload, "RoPE coefficients"),
                    )
                except RoPEKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"RoPE execution failed for {operation.operation_id!r}: {exc}"
                    ) from exc
                self._account_command(counters, command)
                elements = (QUERY_HEADS + KEY_VALUE_HEADS) * HEAD_DIM
                counters["sram.rope_input_bytes_read"] += (
                    len(query_payload) + len(key_payload) + len(coefficient_payload)
                )
                counters["sram.rope_output_bytes_written"] += elements * BF16_BYTES
                counters["arithmetic.rope_multiplications"] += 2 * elements
                counters["arithmetic.rope_additions"] += elements
                saturation_by_kernel[str(operation.index)] = (
                    result.multiplication_saturated_element_count
                    + result.addition_saturated_element_count
                )
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(
                        operation.outputs[0], _u16_payload(result.query_values)
                    ),
                    operation.outputs[1]: write_tensor(
                        operation.outputs[1], _u16_payload(result.key_values)
                    ),
                }

            elif operation.kind == "KV_PREPARE":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError(
                        "KV prepare command count differs"
                    )
                command = commands[0]
                resource_id = self._one_state_effect(operation, "prepare")
                state = self._state_records[resource_id]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.KV_PREPARE_BF16,
                    engine=Engine.STATE,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=state["key_address"],
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=KEY_VALUE_HEADS,
                    size2=HEAD_DIM,
                )
                self._expect_command(command, expected)
                if resource_id in prepared:
                    raise QwenFullModelSimulationError(
                        f"state resource {resource_id!r} is prepared twice"
                    )
                key_payload = read_tensor(operation.inputs[0])
                value_payload = read_tensor(operation.inputs[1])
                try:
                    transaction = prepare_kv_append(
                        self._states[resource_id],
                        transaction_id=request["transaction_id"],
                        expected_generation=request["expected_generations"][
                            state["layer"]
                        ],
                        position_start=request["position_start"],
                        key_values=_finite_bf16(key_payload, "prepared key").reshape(
                            1, KEY_VALUE_HEADS, HEAD_DIM
                        ),
                        value_values=_finite_bf16(
                            value_payload, "prepared value"
                        ).reshape(1, KEY_VALUE_HEADS, HEAD_DIM),
                    )
                except AttentionKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"KV prepare failed for {resource_id!r}: {exc}"
                    ) from exc
                prepared[resource_id] = transaction
                state_handles[operation.outputs[0]] = resource_id
                produced.add(operation.outputs[0])
                self._account_command(counters, command)
                counters["sram.kv_prepare_bytes_read"] += len(key_payload) + len(
                    value_payload
                )
                counters["state.payload_bytes_written"] += len(key_payload) + len(
                    value_payload
                )
                counters["hbm.useful_bytes_written"] += len(key_payload) + len(
                    value_payload
                )
                counters["hbm.transferred_bytes_written"] += len(key_payload) + len(
                    value_payload
                )
                counters["state.metadata_bytes_read"] += 2 * STATE_METADATA.size
                event["outputs"] = {
                    operation.outputs[0]: {
                        "key_payload_sha256": _payload_sha256(key_payload),
                        "resource_id": resource_id,
                        "transaction_private": True,
                        "value_payload_sha256": _payload_sha256(value_payload),
                    }
                }

            elif operation.kind == "ATTENTION":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError(
                        "attention command count differs"
                    )
                command = commands[0]
                resource_id = self._one_state_effect(operation, "read_prepared")
                if state_handles.get(operation.inputs[1]) != resource_id:
                    raise QwenFullModelSimulationError(
                        "attention state handle differs from graph effect"
                    )
                state = self._state_records[resource_id]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.GQA_ATTENTION_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=state["key_address"],
                    destination=tensor_address(operation.outputs[0]),
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=QUERY_HEADS,
                    size2=KEY_VALUE_HEADS,
                    size3=HEAD_DIM,
                )
                self._expect_command(command, expected)
                query_payload = read_tensor(operation.inputs[0])
                try:
                    result = gqa_causal_attention_bf16(
                        _finite_bf16(query_payload, "attention query").reshape(
                            1, QUERY_HEADS, HEAD_DIM
                        ),
                        self._states[resource_id],
                        prepared[resource_id],
                    )
                except AttentionKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"attention failed for {resource_id!r}: {exc}"
                    ) from exc
                self._account_command(counters, command)
                visible = (self._states[resource_id].length + 1) * 2 * KV_TOKEN_BYTES
                counters["state.payload_bytes_read"] += visible
                counters["hbm.useful_bytes_read"] += visible
                counters["hbm.transferred_bytes_read"] += visible
                counters["sram.attention_query_bytes_read"] += len(query_payload)
                payload = _u16_payload(result.output_values)
                counters["sram.attention_output_bytes_written"] += len(payload)
                for name, count in asdict(result.accounting).items():
                    counters[f"arithmetic.attention_{name}"] += count
                saturation_by_kernel[str(operation.index)] = (
                    result.mask_saturated_element_count
                    + result.output_saturated_element_count
                    + result.probability_saturated_element_count
                    + result.scaling_saturated_element_count
                    + result.score_saturated_element_count
                )
                event["diagnostics"] = {
                    "probability_payload_sha256": _payload_sha256(
                        _u16_payload(result.probability_values)
                    ),
                    "scaled_score_payload_sha256": _payload_sha256(
                        _u16_payload(result.scaled_score_values)
                    ),
                }
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "ADD":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError("ADD command count differs")
                command = commands[0]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.ADD_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=tensor_address(operation.outputs[0]),
                    size0=1,
                    size1=HIDDEN_WIDTH,
                )
                self._expect_command(command, expected)
                left = read_tensor(operation.inputs[0])
                right = read_tensor(operation.inputs[1])
                try:
                    result = bf16_add_rne(
                        _finite_bf16(left, "ADD left").reshape(1, HIDDEN_WIDTH),
                        _finite_bf16(right, "ADD right").reshape(1, HIDDEN_WIDTH),
                    )
                except ElementwiseKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"ADD failed for {operation.operation_id!r}: {exc}"
                    ) from exc
                self._account_command(counters, command)
                counters["sram.add_input_bytes_read"] += len(left) + len(right)
                payload = _u16_payload(result.values)
                counters["sram.add_output_bytes_written"] += len(payload)
                counters["arithmetic.residual_additions"] += HIDDEN_WIDTH
                saturation_by_kernel[str(operation.index)] = (
                    result.output_saturated_element_count
                )
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "SILU_MUL":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError("SiLU command count differs")
                command = commands[0]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.SILU_MUL_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=tensor_address(operation.outputs[0]),
                    size0=1,
                    size1=INTERMEDIATE_WIDTH,
                )
                self._expect_command(command, expected)
                gate = read_tensor(operation.inputs[0])
                up = read_tensor(operation.inputs[1])
                try:
                    result = qwen3_silu_mul_bf16(
                        _finite_bf16(gate, "SiLU gate").reshape(1, INTERMEDIATE_WIDTH),
                        _finite_bf16(up, "SiLU up").reshape(1, INTERMEDIATE_WIDTH),
                    )
                except ElementwiseKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"SiLU failed for {operation.operation_id!r}: {exc}"
                    ) from exc
                self._account_command(counters, command)
                counters["sram.silu_input_bytes_read"] += len(gate) + len(up)
                payload = _u16_payload(result.values)
                counters["sram.silu_output_bytes_written"] += len(payload)
                counters["arithmetic.sigmoid_exponentials"] += INTERMEDIATE_WIDTH
                counters["arithmetic.sigmoid_denominator_additions"] += (
                    INTERMEDIATE_WIDTH
                )
                counters["arithmetic.sigmoid_divisions"] += INTERMEDIATE_WIDTH
                counters["arithmetic.silu_multiplications"] += INTERMEDIATE_WIDTH
                counters["arithmetic.up_gate_multiplications"] += INTERMEDIATE_WIDTH
                saturation_by_kernel[str(operation.index)] = (
                    result.activation_saturated_element_count
                    + result.output_saturated_element_count
                )
                event["diagnostics"] = {
                    "activation_payload_sha256": _payload_sha256(
                        _u16_payload(result.activation_values)
                    )
                }
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "LAST_TOKEN_SELECT":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError(
                        "selection command count differs"
                    )
                command = commands[0]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.DMA_SRAM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=runtime.address + 8,
                    destination=tensor_address(operation.outputs[0]),
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=1,
                    size3=4,
                )
                self._expect_command(command, expected)
                index = struct.unpack("<I", runtime.read(command.source1, 4))[0]
                if index >= command.size2:
                    raise QwenFullModelSimulationError(
                        "last-token selection index is out of range"
                    )
                source_payload = read_tensor(operation.inputs[0])
                start = index * command.size1
                payload = source_payload[start : start + command.size0]
                _finite_bf16(payload, "selected last-token row")
                self._account_command(counters, command)
                counters["sram.selection_index_bytes_read"] += command.size3
                counters["sram.selection_input_bytes_read"] += len(payload)
                counters["sram.selection_output_bytes_written"] += len(payload)
                event["logical_index"] = index
                event["outputs"] = {
                    operation.outputs[0]: write_tensor(operation.outputs[0], payload)
                }

            elif operation.kind == "STATE_COMMIT":
                if len(commands) != 1:
                    raise QwenFullModelSimulationError(
                        "state commit command count differs"
                    )
                command = commands[0]
                expected = ProductionCommand(
                    index=command.index,
                    opcode=Opcode.STATE_COMMIT,
                    engine=Engine.STATE,
                    kernel_index=NO_KERNEL,
                    source0=self._plan["hbm"]["metadata_table"]["address"],
                    source1=self._plan["hbm"]["descriptor_table"]["address"],
                    size0=CONTEXT_CAPACITY,
                    size1=STATE_COUNT,
                )
                self._expect_command(command, expected)
                committed_effects = [
                    effect.state_id
                    for effect in operation.effects
                    if effect.action == "commit"
                ]
                expected_resources = [
                    f"kv.layer.{layer}" for layer in range(LAYER_COUNT)
                ]
                if (
                    operation.index != OPERATION_COUNT - 1
                    or committed_effects != expected_resources
                    or set(prepared) != set(expected_resources)
                ):
                    raise QwenFullModelSimulationError(
                        "terminal 36-resource commit set differs"
                    )
                logits_payload = read_tensor(operation.inputs[0])
                try:
                    committed = commit_kv_group(
                        tuple(
                            (self._states[resource], prepared[resource])
                            for resource in expected_resources
                        )
                    )
                except AttentionKernelError as exc:
                    raise QwenFullModelSimulationError(
                        f"atomic KV commit failed: {exc}"
                    ) from exc
                staged_states = {state.resource_id: state for state in committed}
                self._account_command(counters, command)
                counters["state.metadata_bytes_read"] += (
                    2 * STATE_METADATA.size * STATE_COUNT
                )
                counters["state.metadata_bytes_written"] += (
                    STATE_METADATA.size * STATE_COUNT
                )
                counters["hbm.useful_bytes_written"] += (
                    STATE_METADATA.size * STATE_COUNT
                )
                counters["hbm.transferred_bytes_written"] += (
                    STATE_METADATA.size * STATE_COUNT
                )
                output_id = operation.outputs[0]
                output_record = assignment(output_id)
                if (
                    output_record.get("alias_of") != operation.inputs[0]
                    or tensor_slot(output_id).slot_id
                    != tensor_slot(operation.inputs[0]).slot_id
                ):
                    raise QwenFullModelSimulationError("committed logits alias differs")
                owners[tensor_slot(output_id).slot_id] = output_id
                produced.add(output_id)
                event["outputs"] = {output_id: capture(output_id, logits_payload)}

            else:
                raise QwenFullModelSimulationError(
                    f"unsupported operation {operation.kind!r}"
                )

            if set(operation.outputs) - produced:
                raise QwenFullModelSimulationError(
                    f"operation {operation.operation_id!r} did not produce all outputs"
                )
            events.append(event)

        complete = self._commands[-1]
        expected_complete = ProductionCommand(
            index=EXPECTED_COMMAND_COUNT - 1,
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        )
        self._expect_command(complete, expected_complete)
        self._account_command(counters, complete)
        if staged_states is None or len(staged_states) != STATE_COUNT:
            raise QwenFullModelSimulationError(
                "COMPLETE observes no atomic 36-resource commit"
            )
        if counters["commands.total"] != EXPECTED_COMMAND_COUNT:
            raise QwenFullModelSimulationError("executed command count differs")

        committed_logits = captures.get("output.committed_logits")
        if committed_logits is None:
            raise QwenFullModelSimulationError("committed logits were not captured")
        logits_slot = tensor_slot("output.committed_logits")
        logits_payload = logits_slot.read(
            logits_slot.address,
            int(assignment("output.committed_logits")["logical_bytes"]),
        )
        logits_codes = _finite_bf16(logits_payload, "complete logits")
        logits_values = np.ascontiguousarray(
            logits_codes.astype(np.uint32) << np.uint32(16)
        ).view(np.float32)
        selected_token = int(np.argmax(logits_values))
        maximum = logits_values[selected_token]
        maximum_count = int(np.count_nonzero(logits_values == maximum))
        if maximum_count != 1:
            raise QwenFullModelSimulationError("greedy logit maximum is not unique")

        state_report: list[dict[str, Any]] = []
        for layer in range(LAYER_COUNT):
            resource_id = f"kv.layer.{layer}"
            state = staged_states[resource_id]
            key_payload = _u16_payload(state.key_values)
            value_payload = _u16_payload(state.value_values)
            state_report.append(
                {
                    "generation": state.generation,
                    "key_payload_sha256": _payload_sha256(key_payload),
                    "layer": layer,
                    "length": state.length,
                    "resource_id": resource_id,
                    "value_payload_sha256": _payload_sha256(value_payload),
                }
            )

        layer_outputs = []
        for layer in range(1, LAYER_COUNT + 1):
            tensor_id = f"hidden.{layer}"
            record = captures.get(tensor_id)
            if record is None:
                raise QwenFullModelSimulationError(
                    f"layer output {tensor_id!r} was not captured"
                )
            layer_outputs.append({"layer": layer, "tensor_id": tensor_id, **record})

        total_saturation = sum(saturation_by_kernel.values())
        body = {
            "artifact_admission": {
                "all_hbm_shards_sha256_verified": True,
                "non_hbm_manifest_artifacts_sha256_verified": True,
            },
            "build_id": self._manifest["build_id"],
            "capability_id": self._capability.capability_id,
            "claim_boundary": {
                "complete_model_one_token_execution": True,
                "decode_steps": 0,
                "exact_8000_token_acceptance": False,
                "timing_or_performance": False,
            },
            "command_abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
            "command_count": EXPECTED_COMMAND_COUNT,
            "command_program_sha256": self._plan["command_program"]["sha256"],
            "counter_reconciliation": "complete_observed_command_and_numeric_counts",
            "counters": dict(sorted(counters.items())),
            "events": events,
            "graph_id": self._model.graph_id,
            "hbm_logical_sha256": self._plan["hbm"]["image"]["logical_sha256"],
            "independent_check_id": self._manifest["independent_check_id"],
            "kernel_ir_id": self._manifest["kernel_ir_id"],
            "layer_outputs": layer_outputs,
            "mode": "artifact_only_data_bearing_functional",
            "operation_count": OPERATION_COUNT,
            "outputs": {
                "committed_logits": {
                    **committed_logits,
                    "greedy_maximum_count": maximum_count,
                    "greedy_token_id": selected_token,
                },
                "final_normalization": captures["hidden.final_norm"],
                "hidden_36": captures["hidden.36"],
                "last_token": captures["hidden.last_token"],
            },
            "physical_plan_id": self._plan["physical_plan_id"],
            "request_id": request["request_id"],
            "saturation": {
                "by_kernel": dict(
                    sorted(saturation_by_kernel.items(), key=lambda item: int(item[0]))
                ),
                "total": total_saturation,
            },
            "schema": EXECUTION_SCHEMA,
            "simulator_version": SIMULATOR_VERSION,
            "source_lock_id": self._manifest["source_lock_id"],
            "state": state_report,
            "status": "pass",
            "timing": {
                "reason": "capability_uncharacterized",
                "status": "unavailable",
            },
        }
        report = _identified(body, "report_id")
        self._states = staged_states
        return report


def publish_qwen_full_model_execution_report(
    report: Mapping[str, Any], output: Path
) -> None:
    """Publish one canonical execution report without overwriting evidence."""

    value = dict(report)
    if (
        value.get("schema") != EXECUTION_SCHEMA
        or value.get("status") != "pass"
        or value.get("mode") != "artifact_only_data_bearing_functional"
        or value.get("artifact_admission")
        != {
            "all_hbm_shards_sha256_verified": True,
            "non_hbm_manifest_artifacts_sha256_verified": True,
        }
        or value.get("claim_boundary")
        != {
            "complete_model_one_token_execution": True,
            "decode_steps": 0,
            "exact_8000_token_acceptance": False,
            "timing_or_performance": False,
        }
        or value.get("command_count") != EXPECTED_COMMAND_COUNT
        or value.get("operation_count") != OPERATION_COUNT
        or value.get("timing")
        != {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        }
    ):
        raise QwenFullModelSimulationError("execution report boundary differs")
    _identity(value, "report_id", "execution report")
    path = Path(output)
    if path.exists():
        raise QwenFullModelSimulationError(f"execution report already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


__all__ = [
    "EXECUTION_SCHEMA",
    "QwenFullModelSimulationError",
    "QwenFullModelSimulator",
    "SIMULATOR_VERSION",
    "publish_qwen_full_model_execution_report",
]
