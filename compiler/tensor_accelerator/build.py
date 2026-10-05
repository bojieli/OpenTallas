"""Atomic compiler for tensor-accelerator HBM/SRAM deployments."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .capability import load_capability
from .checking import check_candidate, expectations_from_check
from .command import ABI_MAJOR, ABI_MINOR, disassemble, encode
from .common import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from .lowering import lower_model, operator_coverage
from .model import load_model_graph
from .physical import HBM_IMAGE_PATH, build_commands, build_physical_plan


COMPILER_VERSION = "tensor-accelerator-0.1.0"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.deployment.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.source_lock.v1"


class TensorAcceleratorBuildError(RuntimeError):
    """Raised when a deployment cannot be built atomically and completely."""


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _artifact(root: Path, relative_path: str, role: str) -> dict[str, Any]:
    digest, size = sha256_file(root / relative_path)
    return {
        "path": relative_path,
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _source_lock(
    source_model: Path,
    source_capability: Path,
    *,
    model_id: str,
    capability_id: str,
    semantic_sha256: str,
) -> dict[str, Any]:
    model_payload = source_model.read_bytes()
    capability_payload = source_capability.read_bytes()
    return {
        "capability_id": capability_id,
        "capability_source_sha256": sha256_bytes(capability_payload),
        "capability_source_size_bytes": len(capability_payload),
        "compiler_version": COMPILER_VERSION,
        "model_id": model_id,
        "model_source_sha256": sha256_bytes(model_payload),
        "model_source_size_bytes": len(model_payload),
        "schema": SOURCE_LOCK_SCHEMA,
        "semantic_sha256": semantic_sha256,
    }


def _manifest(
    root: Path,
    *,
    model_id: str,
    numeric_profile: str,
    capability_id: str,
    semantic_sha256: str,
    physical_plan_id: str,
) -> dict[str, Any]:
    roles = {
        "capability.json": "hardware_capability",
        "checks/independent_check.json": "independent_check",
        "execution_expectations.json": "execution_expectations",
        HBM_IMAGE_PATH: "hbm_image",
        "ir/model_graph.json": "model_graph",
        "ir/operator_coverage.json": "operator_coverage",
        "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
        "physical/physical_plan.json": "physical_plan",
        "program/commands.bin": "command_program",
        "program/commands.disasm": "command_disassembly",
        "source.lock.json": "source_lock",
    }
    artifacts = [
        _artifact(root, path, roles[path])
        for path in sorted(roles)
    ]
    body = {
        "artifacts": artifacts,
        "capability_id": capability_id,
        "claim_boundary": [
            "qualified exact-integer tensor-accelerator fixture",
            "not a Qwen3 or DeepSeek model execution",
            "not RTL, target-node PPA, HBM PHY, or product evidence",
        ],
        "command_abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator compiler",
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "capability": "capability.json",
            "command_program": "program/commands.bin",
            "execution_expectations": "execution_expectations.json",
            "hbm_image": HBM_IMAGE_PATH,
            "model_graph": "ir/model_graph.json",
            "physical_plan": "physical/physical_plan.json",
            "tensor_kernel_ir": "ir/tensor_kernel_ir.json",
        },
        "model_id": model_id,
        "numeric_profile": numeric_profile,
        "physical_plan_id": physical_plan_id,
        "schema": MANIFEST_SCHEMA,
        "semantic_sha256": semantic_sha256,
    }
    return {**body, "build_id": sha256_bytes(canonical_json_bytes(body))}


def _build_into(
    source_model: Path,
    source_capability: Path,
    root: Path,
) -> dict[str, Any]:
    model = load_model_graph(source_model, require_initializers=True)
    capability = load_capability(source_capability)
    semantic_sha256 = sha256_bytes(
        canonical_json_bytes(model.to_dict(include_values=True))
    )

    (root / "checks").mkdir()
    (root / "ir").mkdir()
    (root / "memory").mkdir()
    (root / "physical").mkdir()
    (root / "program").mkdir()

    write_canonical_json(root / "capability.json", capability.to_dict())
    write_canonical_json(
        root / "source.lock.json",
        _source_lock(
            source_model,
            source_capability,
            model_id=model.model_id,
            capability_id=capability.capability_id,
            semantic_sha256=semantic_sha256,
        ),
    )
    write_canonical_json(
        root / "ir/model_graph.json",
        model.to_dict(include_values=False),
    )
    coverage = operator_coverage(model)
    write_canonical_json(root / "ir/operator_coverage.json", coverage)
    if coverage["unsupported_operation_count"]:
        raise TensorAcceleratorBuildError(
            "operator coverage contains unsupported operations"
        )
    kernel_ir = lower_model(model, capability)
    write_canonical_json(root / "ir/tensor_kernel_ir.json", kernel_ir)

    hbm_image, physical_plan = build_physical_plan(model, capability)
    (root / HBM_IMAGE_PATH).write_bytes(hbm_image)
    write_canonical_json(root / "physical/physical_plan.json", physical_plan)

    commands = build_commands(model, kernel_ir, physical_plan, capability)
    command_payload = encode(commands)
    (root / "program/commands.bin").write_bytes(command_payload)
    _write_text(root / "program/commands.disasm", disassemble(commands))

    check = check_candidate(
        source_model=source_model,
        source_capability=source_capability,
        root=root,
    )
    if (
        check["semantic_sha256"] != semantic_sha256
        or check["physical_plan_id"] != physical_plan["physical_plan_id"]
    ):
        raise TensorAcceleratorBuildError(
            "independent check identity differs from compiler source"
        )
    write_canonical_json(root / "checks/independent_check.json", check)
    write_canonical_json(
        root / "execution_expectations.json",
        expectations_from_check(check),
    )

    manifest = _manifest(
        root,
        model_id=model.model_id,
        numeric_profile=model.numeric_profile,
        capability_id=capability.capability_id,
        semantic_sha256=semantic_sha256,
        physical_plan_id=physical_plan["physical_plan_id"],
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_deployment(
    source_model: Path,
    source_capability: Path,
    output: Path,
) -> dict[str, Any]:
    """Compile one deployment and publish it atomically after independent checks."""

    source_model = Path(source_model).resolve()
    source_capability = Path(source_capability).resolve()
    output = Path(output).resolve()
    if not source_model.is_file():
        raise TensorAcceleratorBuildError(f"model graph does not exist: {source_model}")
    if not source_capability.is_file():
        raise TensorAcceleratorBuildError(
            f"capability does not exist: {source_capability}"
        )
    if output.exists():
        raise TensorAcceleratorBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent)
    )
    try:
        manifest = _build_into(source_model, source_capability, temporary)
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
