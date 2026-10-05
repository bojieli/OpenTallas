"""Deterministic deployment builder for the first executable vertical slice."""

from __future__ import annotations

from collections import Counter
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from compiler.checking.expectations import build_execution_expectations
from compiler.checking.inverse import check_rom_image
from compiler.image.rom import build_rom_image
from compiler.ir.model import (
    SUPPORTED_OPERATIONS,
    canonical_json_bytes,
    load_model,
    write_canonical_json,
)
from compiler.microcode.isa import ABI_MAJOR, ABI_MINOR, assemble, disassemble, encode


COMPILER_VERSION = "0.1.0"
DEPLOYMENT_SCHEMA = "opentallas.deployment_manifest.v1"
SOURCE_LOCK_SCHEMA = "opentallas.source_lock.v1"
OPERATOR_COVERAGE_SCHEMA = "opentallas.operator_coverage.v1"


class BuildError(RuntimeError):
    """Raised when a deployment cannot be built atomically and completely."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_record(path: Path, role: str, root: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _operator_coverage(model: Any) -> dict[str, Any]:
    counts = Counter(operation.kind for operation in model.operations)
    return {
        "encountered_operations": [
            {"count": counts[kind], "kind": kind}
            for kind in sorted(counts)
        ],
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "schema": OPERATOR_COVERAGE_SCHEMA,
        "scope": "deterministic fixture only; not the DeepSeek operator ledger",
        "status": "pass",
        "supported_operations": list(SUPPORTED_OPERATIONS),
        "unsupported_operation_count": 0,
    }


def _build_into(source_ir: Path, root: Path) -> dict[str, Any]:
    source_raw = source_ir.read_bytes()
    model = load_model(source_ir, require_rom_values=True)
    semantic_source = canonical_json_bytes(model.to_dict(include_values=True))
    source_lock = {
        "compiler_version": COMPILER_VERSION,
        "model_id": model.model_id,
        "raw_source_sha256": _sha256(source_raw),
        "raw_source_size_bytes": len(source_raw),
        "schema": SOURCE_LOCK_SCHEMA,
        "semantic_ir_schema": "opentallas.semantic_ir.v1",
        "semantic_sha256": _sha256(semantic_source),
    }
    write_canonical_json(root / "source.lock.json", source_lock)
    write_canonical_json(root / "model.ir.json", model.to_dict(include_values=False))

    rom_image, tensor_manifest = build_rom_image(model)
    (root / "rom_stage00_image.bin").write_bytes(rom_image)
    write_canonical_json(root / "tensor_manifest.json", tensor_manifest)

    instructions = assemble(model)
    (root / "microcode_stage00.bin").write_bytes(encode(instructions))
    _write_text(root / "microcode_stage00.disasm", disassemble(instructions, model))
    write_canonical_json(root / "operator_coverage.json", _operator_coverage(model))
    write_canonical_json(
        root / "execution_expectations.json",
        build_execution_expectations(model),
    )

    # This checker is a separately implemented inverse mapping, not a packer
    # self-check. Its deterministic report becomes part of the deployment.
    roundtrip = check_rom_image(source_ir, root)
    write_canonical_json(root / "roundtrip_report.json", roundtrip)

    roles = {
        "execution_expectations.json": "execution_expectations",
        "microcode_stage00.bin": "microcode",
        "microcode_stage00.disasm": "microcode_disassembly",
        "model.ir.json": "semantic_ir",
        "operator_coverage.json": "operator_coverage",
        "rom_stage00_image.bin": "rom_image",
        "roundtrip_report.json": "rom_roundtrip_report",
        "source.lock.json": "source_lock",
        "tensor_manifest.json": "tensor_manifest",
    }
    artifacts = [
        _file_record(root / name, roles[name], root) for name in sorted(roles)
    ]
    identity = {
        "artifacts": artifacts,
        "compiler_version": COMPILER_VERSION,
        "microcode_abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "semantic_sha256": source_lock["semantic_sha256"],
    }
    build_id = _sha256(canonical_json_bytes(identity))
    manifest = {
        "artifacts": artifacts,
        "build_id": build_id,
        "claim_boundary": [
            "This is an exact-integer compiler fixture, not a DeepSeek model or layer.",
            "Functional interpreter steps and semantic bytes are not hardware cycles, transactions, or performance.",
            "Target numeric formats, complete checkpoint ingestion, placement, schedules, RTL execution, and model quality remain open under COMP-01.",
        ],
        "compiler": {
            "name": "opentallas-executable-system-compiler",
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "execution_expectations": "execution_expectations.json",
            "microcode": "microcode_stage00.bin",
            "rom_image": "rom_stage00_image.bin",
            "semantic_ir": "model.ir.json",
            "tensor_manifest": "tensor_manifest.json",
        },
        "microcode_abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "schema": DEPLOYMENT_SCHEMA,
        "semantic_sha256": source_lock["semantic_sha256"],
    }
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_deployment(source_ir: Path, output_dir: Path) -> dict[str, Any]:
    """Build atomically, refusing to merge with an existing output directory."""

    source_ir = source_ir.resolve()
    output_dir = output_dir.resolve()
    if not source_ir.is_file():
        raise BuildError(f"semantic IR is not a file: {source_ir}")
    if output_dir == Path(output_dir.anchor):
        raise BuildError("refusing to use a filesystem root as a deployment directory")
    if output_dir.exists():
        raise BuildError(f"deployment output already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        manifest = _build_into(source_ir, temporary)
        os.replace(temporary, output_dir)
        return manifest
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
