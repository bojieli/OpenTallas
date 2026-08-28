"""Artifact-only functional simulator for ABI 2.3 attention and KV state."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path, PurePosixPath
import struct
from typing import Any, Mapping

import numpy as np

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from compiler.tensor_accelerator.production_command import (
    ABI_MAJOR,
    ABI_MINOR,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi,
    decode,
)

from .attention import (
    AttentionKernelError,
    KVSnapshot,
    PreparedKV,
    commit_kv_append,
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.attention_deployment.v1"
PLAN_SCHEMA = "opentallas.tensor_accelerator.attention_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.attention_request.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.attention_expectations.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.attention_execution.v1"
QUALIFICATION_SCHEMA = "opentallas.tensor_accelerator.attention_qualification.v1"
QUALIFICATION_ID = "82bd8f8b687e6674d72220b6a749e43da5224a22ba3bbeba562284a449d5a5bd"

HBM_IMAGE_PATH = "memory/hbm_attention.bin"
PLAN_PATH = "physical/physical_plan.json"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
EXPECTATIONS_PATH = "execution_expectations.json"

FIXTURE_ID = "checkpoint_derived_nonempty_history"
RESOURCE_ID = "kv.layer.0"
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
CONTEXT_CAPACITY = 8000
COMMITTED_LENGTH = 3
PREPARED_LENGTH = 1
BASE_GENERATION = 4
TRANSACTION_ID = 0x4154544E0002
TOKEN_BYTES = KEY_VALUE_HEADS * HEAD_DIM * 2
QUERY_BYTES = QUERY_HEADS * HEAD_DIM * 2
STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")


class ProductionAttentionSimulationError(ValueError):
    """Raised when artifacts or execution violate the attention machine."""


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionAttentionSimulationError(str(exc)) from exc
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionAttentionSimulationError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ProductionAttentionSimulationError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionAttentionSimulationError(f"{label} must be a safe relative path")
    return path.as_posix()


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionAttentionSimulationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionAttentionSimulationError(f"{label} is not canonical JSON")
    return value, payload


def _tensor(values: np.ndarray) -> dict[str, Any]:
    codes = np.ascontiguousarray(values, dtype=np.uint16)
    payload = np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")
    return {
        "codes": [int(item) for item in codes.reshape(-1).tolist()],
        "dtype": "bf16",
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "shape": list(codes.shape),
        "size_bytes": len(payload),
    }


def _state_record(state: KVSnapshot) -> dict[str, Any]:
    key_payload = np.ascontiguousarray(state.key_values, dtype="<u2").tobytes(order="C")
    value_payload = np.ascontiguousarray(state.value_values, dtype="<u2").tobytes(order="C")
    body = {
        "capacity": state.capacity,
        "generation": state.generation,
        "key_payload_sha256": hashlib.sha256(key_payload).hexdigest(),
        "length": state.length,
        "resource_id": state.resource_id,
        "value_payload_sha256": hashlib.sha256(value_payload).hexdigest(),
    }
    return {**body, "state_sha256": sha256_bytes(canonical_json_bytes(body))}


def _manifest(root: Path) -> dict[str, Any]:
    value, _ = _load_canonical(root / "deployment_manifest.json", "deployment manifest")
    _identity(value, "build_id", "deployment manifest")
    required = {
        "artifacts",
        "build_id",
        "capability_id",
        "claim_boundary",
        "command_abi",
        "compiler",
        "entrypoint",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_report_id",
        "schema",
        "source_lock_id",
    }
    try:
        exact_keys(value, required, set(), "deployment manifest")
    except ArtifactError as exc:
        raise ProductionAttentionSimulationError(str(exc)) from exc
    if value["schema"] != MANIFEST_SCHEMA:
        raise ProductionAttentionSimulationError("manifest schema differs")
    if value["command_abi"] != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        raise ProductionAttentionSimulationError("manifest command ABI differs")
    if value["qualification_report_id"] != QUALIFICATION_ID:
        raise ProductionAttentionSimulationError("manifest qualification differs")
    entrypoint = value["entrypoint"]
    if entrypoint != {
        "capability": "capability.json",
        "command_program": COMMAND_PATH,
        "hbm_image": HBM_IMAGE_PATH,
        "physical_plan": PLAN_PATH,
        "request": REQUEST_PATH,
    }:
        raise ProductionAttentionSimulationError("manifest entrypoint differs")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 13:
        raise ProductionAttentionSimulationError("manifest artifact coverage differs")
    paths: set[str] = set()
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionAttentionSimulationError(f"artifact {index} is malformed")
        try:
            exact_keys(record, {"path", "role", "sha256", "size_bytes"}, set(), f"artifact {index}")
            path = _safe_relative(record["path"], f"artifact {index}.path")
            digest = require_sha256(record["sha256"], f"artifact {index}.sha256")
            size = require_int(record["size_bytes"], f"artifact {index}.size_bytes", minimum=1)
        except ArtifactError as exc:
            raise ProductionAttentionSimulationError(str(exc)) from exc
        if path in paths:
            raise ProductionAttentionSimulationError("manifest contains duplicate artifact paths")
        paths.add(path)
        try:
            payload = (root / path).read_bytes()
        except OSError as exc:
            raise ProductionAttentionSimulationError(f"cannot read artifact {path}: {exc}") from exc
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise ProductionAttentionSimulationError(f"artifact {path} identity differs")
    expected_paths = {
        "capability.json",
        "checks/independent_check.json",
        EXPECTATIONS_PATH,
        HBM_IMAGE_PATH,
        "ir/tensor_kernel_ir.json",
        PLAN_PATH,
        COMMAND_PATH,
        "program/commands.disasm",
        REQUEST_PATH,
        "source.lock.json",
        "source/model_graph.v2.json",
        "source/qkv_execution.json",
        "source/qualification.json",
    }
    if paths != expected_paths:
        raise ProductionAttentionSimulationError("manifest artifact paths differ")
    return value


def _qualification(root: Path) -> Mapping[str, Any]:
    value, _ = _load_canonical(root / "source/qualification.json", "attention qualification")
    _identity(value, "report_id", "attention qualification")
    if (
        value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("report_id") != QUALIFICATION_ID
        or value.get("status") != "pass"
    ):
        raise ProductionAttentionSimulationError("attention qualification differs")
    fixtures = value.get("fixtures")
    if not isinstance(fixtures, list):
        raise ProductionAttentionSimulationError("qualification fixtures differ")
    selected = [item for item in fixtures if isinstance(item, Mapping) and item.get("fixture_id") == FIXTURE_ID]
    if len(selected) != 1:
        raise ProductionAttentionSimulationError("nonempty qualification fixture differs")
    return selected[0]


def _request(path: Path) -> dict[str, Any]:
    value, _ = _load_canonical(path, "execution request")
    _identity(value, "request_id", "execution request")
    expected = {
        "expected_generation": BASE_GENERATION,
        "fixture_id": FIXTURE_ID,
        "position_start": COMMITTED_LENGTH,
        "schema": REQUEST_SCHEMA,
        "span_tokens": PREPARED_LENGTH,
        "state_resource": RESOURCE_ID,
        "transaction_id": TRANSACTION_ID,
    }
    for field, item in expected.items():
        if value.get(field) != item:
            raise ProductionAttentionSimulationError(f"request {field} differs")
    if not isinstance(value.get("graph_id"), str) or not isinstance(value.get("source_operation_ids"), list):
        raise ProductionAttentionSimulationError("request graph binding differs")
    return value


class ProductionAttentionSimulator:
    """Loaded immutable deployment with per-execution mutable machine state."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: Mapping[str, Any],
        capability: ProductionCapability,
        plan: Mapping[str, Any],
        hbm_image: bytes,
        commands: tuple[ProductionCommand, ...],
        expectations: Mapping[str, Any],
        qualification_fixture: Mapping[str, Any],
    ) -> None:
        self._root = root
        self._manifest = manifest
        self._capability = capability
        self._plan = plan
        self._hbm_image = hbm_image
        self._commands = commands
        self._expectations = expectations
        self._qualification_fixture = qualification_fixture

    @classmethod
    def load(cls, root: Path) -> "ProductionAttentionSimulator":
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionAttentionSimulationError(f"deployment directory does not exist: {deployment}")
        manifest = _manifest(deployment)
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionAttentionSimulationError(f"capability load failed: {exc}") from exc
        if (
            capability.capability_id != manifest["capability_id"]
            or (capability.command_abi_major, capability.command_abi_minor) != (ABI_MAJOR, ABI_MINOR)
        ):
            raise ProductionAttentionSimulationError("capability identity or ABI differs")
        plan, _ = _load_canonical(deployment / PLAN_PATH, "physical plan")
        _identity(plan, "physical_plan_id", "physical plan")
        if (
            plan.get("schema") != PLAN_SCHEMA
            or plan.get("physical_plan_id") != manifest["physical_plan_id"]
            or plan.get("capability_id") != capability.capability_id
            or plan.get("qualification_report_id") != QUALIFICATION_ID
        ):
            raise ProductionAttentionSimulationError("physical plan binding differs")
        image_record = plan.get("hbm", {}).get("image", {})
        try:
            hbm_image = (deployment / HBM_IMAGE_PATH).read_bytes()
        except OSError as exc:
            raise ProductionAttentionSimulationError(f"cannot read HBM image: {exc}") from exc
        if image_record != {
            "base_address": capability.hbm.base_address,
            "path": HBM_IMAGE_PATH,
            "sha256": hashlib.sha256(hbm_image).hexdigest(),
            "size_bytes": len(hbm_image),
        }:
            raise ProductionAttentionSimulationError("HBM image metadata differs")
        try:
            command_payload = (deployment / COMMAND_PATH).read_bytes()
            commands = decode(command_payload)
        except (OSError, ProductionCommandError) as exc:
            raise ProductionAttentionSimulationError(f"command program load failed: {exc}") from exc
        program = plan.get("program")
        if (
            command_abi(command_payload) != (ABI_MAJOR, ABI_MINOR)
            or not isinstance(program, Mapping)
            or program.get("path") != COMMAND_PATH
            or program.get("command_count") != len(commands)
            or program.get("size_bytes") != len(command_payload)
            or program.get("sha256") != hashlib.sha256(command_payload).hexdigest()
        ):
            raise ProductionAttentionSimulationError("command program metadata differs")
        expectations, _ = _load_canonical(deployment / EXPECTATIONS_PATH, "execution expectations")
        _identity(expectations, "expectations_id", "execution expectations")
        if (
            expectations.get("schema") != EXPECTATIONS_SCHEMA
            or expectations.get("qualification_report_id") != QUALIFICATION_ID
            or expectations.get("counters") != plan.get("expected_counters")
        ):
            raise ProductionAttentionSimulationError("execution expectations differ")
        fixture = _qualification(deployment)
        if expectations.get("output_payload_sha256") != {
            role: fixture["outputs"][role]["payload_sha256"]
            for role in ("attention", "probabilities", "scaled_scores")
        } or expectations.get("committed_state_sha256") != fixture["transaction"]["committed_state_sha256"]:
            raise ProductionAttentionSimulationError("expectations differ from qualification")
        return cls(
            root=deployment,
            manifest=manifest,
            capability=capability,
            plan=plan,
            hbm_image=hbm_image,
            commands=commands,
            expectations=expectations,
            qualification_fixture=fixture,
        )

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        request = _request(self._root / REQUEST_PATH if request_path is None else Path(request_path))
        if request["graph_id"] != self._manifest["graph_id"]:
            raise ProductionAttentionSimulationError("request graph differs")
        hbm = bytearray(self._hbm_image)
        sram = bytearray(self._capability.sram.capacity_bytes)
        regions = self._plan.get("hbm", {}).get("regions")
        sram_regions = self._plan.get("sram", {}).get("regions")
        if not isinstance(regions, list) or not isinstance(sram_regions, list):
            raise ProductionAttentionSimulationError("physical region coverage differs")
        hbm_by_id = {record.get("id"): record for record in regions if isinstance(record, Mapping)}
        sram_by_id = {record.get("id"): record for record in sram_regions if isinstance(record, Mapping)}
        if set(hbm_by_id) != {"query", "current_key", "current_value", "key_state", "value_state", "state_metadata", "transaction_descriptor"}:
            raise ProductionAttentionSimulationError("HBM region roles differ")
        if set(sram_by_id) != {"query", "current_key", "current_value", "attention_output"}:
            raise ProductionAttentionSimulationError("SRAM region roles differ")

        def hbm_offset(address: int, size: int) -> int:
            offset = address - self._capability.hbm.base_address
            if offset < 0 or size < 0 or offset + size > len(hbm):
                raise ProductionAttentionSimulationError("HBM access is outside the image")
            return offset

        def sram_offset(address: int, size: int) -> int:
            if address < 0 or size < 0 or address + size > len(sram):
                raise ProductionAttentionSimulationError("SRAM access is outside the scratchpad")
            return address

        def state_metadata() -> tuple[int, int, int, int, int]:
            address = int(hbm_by_id["state_metadata"]["address"])
            offset = hbm_offset(address, 64)
            magic, generation, length, capacity, key_base, value_base, resource_index, reserved = STATE_METADATA.unpack(bytes(hbm[offset : offset + 64]))
            if magic != STATE_MAGIC or resource_index != 0 or reserved != bytes(8):
                raise ProductionAttentionSimulationError("state metadata encoding differs")
            return generation, length, capacity, key_base, value_base

        def transaction_descriptor() -> tuple[int, int, int, int, int, int]:
            address = int(hbm_by_id["transaction_descriptor"]["address"])
            offset = hbm_offset(address, 64)
            magic, transaction_id, expected_generation, position, span, resources, metadata_address, reserved = TRANSACTION_DESCRIPTOR.unpack(bytes(hbm[offset : offset + 64]))
            if magic != TRANSACTION_MAGIC or reserved != bytes(8):
                raise ProductionAttentionSimulationError("transaction descriptor encoding differs")
            return transaction_id, expected_generation, position, span, resources, metadata_address

        expected_counters = self._expectations["counters"]
        counters = {key: 0 for key in expected_counters}
        trace: list[dict[str, Any]] = []
        snapshot: KVSnapshot | None = None
        prepared: PreparedKV | None = None
        attention_result: Any = None
        committed: KVSnapshot | None = None
        initialized_sram: set[str] = set()

        for command in self._commands:
            counters["command_count"] += 1
            if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                matching_hbm = [record for record in hbm_by_id.values() if record["address"] == command.source0 and record["payload_size_bytes"] == command.size0]
                matching_sram = [record for record in sram_by_id.values() if record["address"] == command.destination and record["size_bytes"] == command.size0]
                if len(matching_hbm) != 1 or len(matching_sram) != 1:
                    raise ProductionAttentionSimulationError("DMA does not match declared regions")
                source = hbm_offset(command.source0, command.size0)
                destination = sram_offset(command.destination, command.size0)
                sram[destination : destination + command.size0] = hbm[source : source + command.size0]
                initialized_sram.add(str(matching_sram[0]["id"]))
                counters["dma_command_count"] += 1
                counters["direct_dma_command_count"] += 1
                counters["dma_sram_bytes_written"] += command.size0
                counters["hbm_useful_bytes_read"] += command.size0
                counters["hbm_transferred_bytes_read"] += command.size0
            elif command.opcode == Opcode.KV_PREPARE_BF16:
                if not {"current_key", "current_value"} <= initialized_sram or prepared is not None:
                    raise ProductionAttentionSimulationError("KV prepare lacks causal DMA or is duplicated")
                generation, length, capacity, key_base, value_base = state_metadata()
                descriptor = transaction_descriptor()
                if (
                    (generation, length, capacity) != (request["expected_generation"], request["position_start"], CONTEXT_CAPACITY)
                    or descriptor != (request["transaction_id"], request["expected_generation"], request["position_start"], request["span_tokens"], 1, int(hbm_by_id["state_metadata"]["address"]))
                    or command.destination != key_base
                    or command.auxiliary != value_base
                    or (command.size0, command.size1, command.size2) != (PREPARED_LENGTH, KEY_VALUE_HEADS, HEAD_DIM)
                ):
                    raise ProductionAttentionSimulationError("KV prepare state or descriptor differs")
                key_offset = hbm_offset(key_base, length * TOKEN_BYTES)
                value_offset = hbm_offset(value_base, length * TOKEN_BYTES)
                committed_keys = np.frombuffer(hbm, dtype="<u2", count=length * KEY_VALUE_HEADS * HEAD_DIM, offset=key_offset).copy().reshape((length, KEY_VALUE_HEADS, HEAD_DIM))
                committed_values = np.frombuffer(hbm, dtype="<u2", count=length * KEY_VALUE_HEADS * HEAD_DIM, offset=value_offset).copy().reshape((length, KEY_VALUE_HEADS, HEAD_DIM))
                key_sram = sram_offset(command.source0, TOKEN_BYTES)
                value_sram = sram_offset(command.source1, TOKEN_BYTES)
                current_keys = np.frombuffer(sram, dtype="<u2", count=KEY_VALUE_HEADS * HEAD_DIM, offset=key_sram).copy().reshape((1, KEY_VALUE_HEADS, HEAD_DIM))
                current_values = np.frombuffer(sram, dtype="<u2", count=KEY_VALUE_HEADS * HEAD_DIM, offset=value_sram).copy().reshape((1, KEY_VALUE_HEADS, HEAD_DIM))
                try:
                    snapshot = make_kv_snapshot(resource_id=RESOURCE_ID, generation=generation, capacity=capacity, key_values=committed_keys, value_values=committed_values)
                    prepared = prepare_kv_append(snapshot, transaction_id=request["transaction_id"], expected_generation=request["expected_generation"], position_start=request["position_start"], key_values=current_keys, value_values=current_values)
                except AttentionKernelError as exc:
                    raise ProductionAttentionSimulationError(f"KV prepare failed: {exc}") from exc
                metadata_before = bytes(hbm[hbm_offset(int(hbm_by_id["state_metadata"]["address"]), 64) : hbm_offset(int(hbm_by_id["state_metadata"]["address"]), 64) + 64])
                prepared_key_offset = hbm_offset(key_base + length * TOKEN_BYTES, TOKEN_BYTES)
                prepared_value_offset = hbm_offset(value_base + length * TOKEN_BYTES, TOKEN_BYTES)
                hbm[prepared_key_offset : prepared_key_offset + TOKEN_BYTES] = np.ascontiguousarray(current_keys, dtype="<u2").tobytes(order="C")
                hbm[prepared_value_offset : prepared_value_offset + TOKEN_BYTES] = np.ascontiguousarray(current_values, dtype="<u2").tobytes(order="C")
                if bytes(hbm[hbm_offset(int(hbm_by_id["state_metadata"]["address"]), 64) : hbm_offset(int(hbm_by_id["state_metadata"]["address"]), 64) + 64]) != metadata_before:
                    raise ProductionAttentionSimulationError("KV prepare published committed metadata")
                counters["kv_prepare_command_count"] += 1
                counters["kv_prepare_sram_bytes_read"] += 2 * TOKEN_BYTES
                counters["state_payload_bytes_written"] += 2 * TOKEN_BYTES
                counters["state_metadata_bytes_read"] += 128
                counters["hbm_useful_bytes_read"] += 128
                counters["hbm_transferred_bytes_read"] += 128
                counters["hbm_useful_bytes_written"] += 2 * TOKEN_BYTES
                counters["hbm_transferred_bytes_written"] += 2 * TOKEN_BYTES
            elif command.opcode == Opcode.GQA_ATTENTION_BF16:
                if "query" not in initialized_sram or snapshot is None or prepared is None or attention_result is not None:
                    raise ProductionAttentionSimulationError("attention lacks prepared causal inputs or is duplicated")
                if (
                    command.source1 != int(hbm_by_id["key_state"]["address"])
                    or command.auxiliary != int(hbm_by_id["value_state"]["address"])
                    or (command.size0, command.size1, command.size2, command.size3) != (PREPARED_LENGTH, QUERY_HEADS, KEY_VALUE_HEADS, HEAD_DIM)
                ):
                    raise ProductionAttentionSimulationError("attention command shape or state addresses differ")
                query_offset = sram_offset(command.source0, QUERY_BYTES)
                query = np.frombuffer(sram, dtype="<u2", count=QUERY_HEADS * HEAD_DIM, offset=query_offset).copy().reshape((1, QUERY_HEADS, HEAD_DIM))
                try:
                    attention_result = gqa_causal_attention_bf16(query, snapshot, prepared)
                except AttentionKernelError as exc:
                    raise ProductionAttentionSimulationError(f"attention execution failed: {exc}") from exc
                output_payload = np.ascontiguousarray(attention_result.output_values, dtype="<u2").tobytes(order="C")
                output_offset = sram_offset(command.destination, len(output_payload))
                sram[output_offset : output_offset + len(output_payload)] = output_payload
                initialized_sram.add("attention_output")
                counters["attention_command_count"] += 1
                counters["attention_query_sram_bytes_read"] += QUERY_BYTES
                counters["attention_output_sram_bytes_written"] += QUERY_BYTES
                visible_bytes = (snapshot.length + prepared.length) * 2 * TOKEN_BYTES
                counters["state_payload_bytes_read"] += visible_bytes
                counters["hbm_useful_bytes_read"] += visible_bytes
                counters["hbm_transferred_bytes_read"] += visible_bytes
                for name, value in asdict(attention_result.accounting).items():
                    counters[name] += value
            elif command.opcode == Opcode.STATE_COMMIT:
                if snapshot is None or prepared is None or attention_result is None or committed is not None:
                    raise ProductionAttentionSimulationError("state commit lacks successful attention or is duplicated")
                generation, length, capacity, key_base, value_base = state_metadata()
                descriptor = transaction_descriptor()
                if (
                    command.source0 != int(hbm_by_id["state_metadata"]["address"])
                    or command.source1 != int(hbm_by_id["transaction_descriptor"]["address"])
                    or (command.size0, command.size1) != (CONTEXT_CAPACITY, 1)
                    or (generation, length, capacity) != (BASE_GENERATION, COMMITTED_LENGTH, CONTEXT_CAPACITY)
                    or descriptor[0] != TRANSACTION_ID
                ):
                    raise ProductionAttentionSimulationError("state commit descriptor differs")
                try:
                    committed = commit_kv_append(snapshot, prepared)
                except AttentionKernelError as exc:
                    raise ProductionAttentionSimulationError(f"state commit failed: {exc}") from exc
                new_metadata = STATE_METADATA.pack(STATE_MAGIC, committed.generation, committed.length, committed.capacity, key_base, value_base, 0, bytes(8))
                metadata_offset = hbm_offset(command.source0, 64)
                hbm[metadata_offset : metadata_offset + 64] = new_metadata
                counters["state_commit_command_count"] += 1
                counters["state_metadata_bytes_read"] += 128
                counters["state_metadata_bytes_written"] += 64
                counters["hbm_useful_bytes_read"] += 128
                counters["hbm_transferred_bytes_read"] += 128
                counters["hbm_useful_bytes_written"] += 64
                counters["hbm_transferred_bytes_written"] += 64
            elif command.opcode == Opcode.COMPLETE:
                if committed is None or attention_result is None:
                    raise ProductionAttentionSimulationError("COMPLETE retired before attention and commit")
                counters["complete_command_count"] += 1
            else:
                raise ProductionAttentionSimulationError(f"unsupported opcode {command.opcode.name}")
            generation, length, _, _, _ = state_metadata()
            trace.append(
                {
                    "command_index": command.index,
                    "opcode": command.opcode.name,
                    "state_generation": generation,
                    "state_length": length,
                    "transaction_private": prepared is not None and committed is None,
                }
            )

        if counters != expected_counters:
            raise ProductionAttentionSimulationError("observed counters differ from expectations")
        if attention_result is None or committed is None:
            raise ProductionAttentionSimulationError("execution did not produce attention and committed state")
        outputs = {
            "attention": _tensor(attention_result.output_values),
            "probabilities": _tensor(attention_result.probability_values),
            "scaled_scores": _tensor(attention_result.scaled_score_values),
        }
        observed_hashes = {role: record["payload_sha256"] for role, record in outputs.items()}
        if observed_hashes != self._expectations["output_payload_sha256"]:
            raise ProductionAttentionSimulationError("attention output differs from qualification")
        state = _state_record(committed)
        if state["state_sha256"] != self._expectations["committed_state_sha256"]:
            raise ProductionAttentionSimulationError("committed state differs from qualification")
        trace_sha256 = sha256_bytes(canonical_json_bytes(trace))
        body = {
            "build_id": self._manifest["build_id"],
            "capability_id": self._capability.capability_id,
            "counter_reconciliation": "exact",
            "counters": counters,
            "mode": "artifact_only_data_bearing_functional",
            "outputs": outputs,
            "physical_plan_id": self._plan["physical_plan_id"],
            "qualification_report_id": QUALIFICATION_ID,
            "request_id": request["request_id"],
            "saturation": {
                "mask": attention_result.mask_saturated_element_count,
                "output": attention_result.output_saturated_element_count,
                "probability": attention_result.probability_saturated_element_count,
                "scaling": attention_result.scaling_saturated_element_count,
                "score": attention_result.score_saturated_element_count,
            },
            "schema": EXECUTION_SCHEMA,
            "state": state,
            "status": "pass",
            "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
            "trace": trace,
            "trace_sha256": trace_sha256,
        }
        return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def publish_attention_execution_report(report: Mapping[str, Any], output_path: Path) -> None:
    """Retain a canonical report without overwriting existing evidence."""

    if not isinstance(report, Mapping):
        raise ProductionAttentionSimulationError("execution report must be an object")
    expected = sha256_bytes(
        canonical_json_bytes({key: value for key, value in report.items() if key != "report_id"})
    )
    if report.get("report_id") != expected:
        raise ProductionAttentionSimulationError("execution report identity differs")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ProductionAttentionSimulationError(f"execution report will not be overwritten: {destination}")
    destination.write_bytes(canonical_json_bytes(dict(report)))


__all__ = [
    "EXECUTION_SCHEMA",
    "ProductionAttentionSimulationError",
    "ProductionAttentionSimulator",
    "publish_attention_execution_report",
]
