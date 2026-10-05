"""Atomic full-checkpoint Qwen3-8B image and deployment compiler."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, BinaryIO, Mapping

from compiler.frontend.checkpoint import (
    LockedCheckpointReader,
    validate_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, write_canonical_json

from .adapter import (
    TensorSpec,
    build_tensor_specs,
    load_official_config,
    validate_official_checkpoint_lock,
)
from .checking import (
    DEPLOYMENT_SCHEMA,
    PHYSICAL_MAP_SCHEMA,
    verify_deployment_artifacts,
    verify_physical_images,
    verify_schedule,
)
from .constants import (
    CONFIG_SHA256,
    LAYER_COUNT,
    MODEL_ID,
    PAYLOAD_BYTES,
    REVISION,
    TARGET_CONTEXT_TOKENS,
    TENSOR_COUNT,
)
from .graph import build_graph_nodes, build_official_graph_contract
from .isa import assemble, disassemble, encode, tables_record
from .schedule import build_schedule


COMPILER_VERSION = "qwen3-production-v1"
DEFAULT_ALIGNMENT = 4096
CHUNK_BYTES = 16 * 1024 * 1024


class Qwen3DeploymentError(RuntimeError):
    """Raised when a complete official deployment cannot be emitted safely."""


class _ImageWriter:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.handle: BinaryIO = path.open("xb")
        self.digest = hashlib.sha256()
        self.cursor = 0
        self.payload_bytes = 0
        self.padding_bytes = 0

    def write_padding(self, size: int) -> None:
        if size < 0:
            raise Qwen3DeploymentError("negative image padding")
        zero = bytes(min(CHUNK_BYTES, max(size, 1)))
        remaining = size
        while remaining:
            chunk = zero[: min(remaining, len(zero))]
            self.handle.write(chunk)
            self.digest.update(chunk)
            self.cursor += len(chunk)
            self.padding_bytes += len(chunk)
            remaining -= len(chunk)

    def consume_payload(self, chunk: bytes) -> None:
        if not chunk:
            raise Qwen3DeploymentError(
                "checkpoint reader supplied an empty payload chunk"
            )
        self.handle.write(chunk)
        self.digest.update(chunk)
        self.cursor += len(chunk)
        self.payload_bytes += len(chunk)

    def close(self) -> None:
        if self.handle.closed:
            return
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.handle.close()

    def abort(self) -> None:
        if not self.handle.closed:
            self.handle.close()


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & -alignment


def _stage_for(spec: TensorSpec) -> int:
    if spec.layer is not None:
        return spec.layer
    if spec.name == "model.embed_tokens.weight":
        return 0
    if spec.name in {"model.norm.weight", "lm_head.weight"}:
        return LAYER_COUNT - 1
    raise Qwen3DeploymentError(f"tensor {spec.name!r} has no physical stage")


def _stage_specs(specs: tuple[TensorSpec, ...]) -> tuple[tuple[TensorSpec, ...], ...]:
    stages: list[list[TensorSpec]] = [[] for _ in range(LAYER_COUNT)]
    for spec in specs:
        stages[_stage_for(spec)].append(spec)
    if any(not stage for stage in stages):
        raise Qwen3DeploymentError("one or more physical stages have no payload")
    return tuple(tuple(stage) for stage in stages)


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _artifact(root: Path, path: str, role: str) -> dict[str, Any]:
    digest, size = _sha256_file(root / path)
    return {"path": path, "role": role, "sha256": digest, "size_bytes": size}


def _copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=CHUNK_BYTES)
        writer.flush()
        os.fsync(writer.fileno())


def _write_text_new(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _emit_images(
    root: Path,
    snapshot: Path,
    lock: dict[str, Any],
    specs: tuple[TensorSpec, ...],
    alignment: int,
    progress: Callable[[int, int, str], None] | None,
) -> list[dict[str, Any]]:
    stages = _stage_specs(specs)
    emitted: list[dict[str, Any]] = []
    completed = 0
    with LockedCheckpointReader(snapshot, lock) as reader:
        for stage_index, stage_specs in enumerate(stages):
            relative = f"images/qwen3-stage-{stage_index:02d}.rom.bin"
            writer = _ImageWriter(root / relative)
            tensors: list[dict[str, Any]] = []
            try:
                for spec in stage_specs:
                    offset = _align(writer.cursor, alignment)
                    writer.write_padding(offset - writer.cursor)
                    locked_record = reader.tensor_record(spec.name)
                    expected = {
                        "dtype": spec.dtype,
                        "name": spec.name,
                        "shape": list(spec.shape),
                        "size_bytes": spec.size_bytes,
                    }
                    if any(
                        locked_record[key] != value for key, value in expected.items()
                    ):
                        raise Qwen3DeploymentError(
                            f"locked metadata differs while emitting {spec.name!r}"
                        )
                    reader.consume_tensor_payload(
                        spec.name,
                        writer.consume_payload,
                        chunk_bytes=CHUNK_BYTES,
                    )
                    tensors.append(
                        {
                            "dtype": spec.dtype,
                            "layer": spec.layer,
                            "name": spec.name,
                            "offset_bytes": offset,
                            "payload_sha256": locked_record["payload_sha256"],
                            "role": spec.role,
                            "shape": list(spec.shape),
                            "size_bytes": spec.size_bytes,
                        }
                    )
                    completed += 1
                    if progress is not None:
                        progress(completed, len(specs), spec.name)
                final_size = _align(writer.cursor, alignment)
                writer.write_padding(final_size - writer.cursor)
                writer.close()
            except Exception:
                writer.abort()
                raise
            emitted.append(
                {
                    "image_path": relative,
                    "image_sha256": writer.digest.hexdigest(),
                    "image_size_bytes": writer.cursor,
                    "padding_bytes": writer.padding_bytes,
                    "payload_bytes": writer.payload_bytes,
                    "stage": stage_index,
                    "tensors": tensors,
                }
            )
        if reader.accessed_tensor_names != tuple(sorted(spec.name for spec in specs)):
            raise Qwen3DeploymentError(
                "image emission did not consume every locked tensor"
            )
    return emitted


def _physical_map(
    lock: Mapping[str, Any],
    stages: list[dict[str, Any]],
    alignment: int,
) -> dict[str, Any]:
    payload = sum(stage["payload_bytes"] for stage in stages)
    padding = sum(stage["padding_bytes"] for stage in stages)
    image_bytes = sum(stage["image_size_bytes"] for stage in stages)
    tensor_count = sum(len(stage["tensors"]) for stage in stages)
    if payload != PAYLOAD_BYTES or tensor_count != TENSOR_COUNT:
        raise Qwen3DeploymentError(
            "emitted images do not cover the complete checkpoint"
        )
    body = {
        "coverage": {
            "all_padding_zero": True,
            "all_tensors_inverse_reconstructed": True,
            "image_bytes": image_bytes,
            "image_count": len(stages),
            "padding_bytes": padding,
            "payload_bytes": payload,
            "tensor_count": tensor_count,
        },
        "layout": {
            "address_unit": "byte",
            "alignment_bytes": alignment,
            "stage_count": LAYER_COUNT,
        },
        "model": {
            "checkpoint_lock_id": lock["lock_id"],
            "id": MODEL_ID,
            "revision": REVISION,
            "target_context_tokens": TARGET_CONTEXT_TOKENS,
        },
        "schema": PHYSICAL_MAP_SCHEMA,
        "stages": stages,
    }
    return {
        **body,
        "physical_map_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def _manifest(
    root: Path, lock: Mapping[str, Any], graph: Mapping[str, Any]
) -> dict[str, Any]:
    roles = {
        "checkpoint.lock.json": "checkpoint_lock",
        "execution/graph.json": "semantic_graph",
        "execution/microcode.bin": "microcode",
        "execution/microcode.disasm": "microcode_disassembly",
        "execution/microcode_tables.json": "microcode_tables",
        "model/config.json": "model_config",
        "model/generation_config.json": "generation_config",
        "physical/inverse_report.json": "inverse_report",
        "physical/physical_map.json": "physical_map",
        "schedule/schedule.json": "execution_schedule",
        "schedule/schedule_certificate.json": "schedule_certificate",
        "tokenizer/merges.txt": "tokenizer_merges",
        "tokenizer/tokenizer.json": "tokenizer",
        "tokenizer/tokenizer_config.json": "tokenizer_config",
        "tokenizer/vocab.json": "tokenizer_vocab",
    }
    for path in sorted((root / "images").glob("*.rom.bin")):
        roles[path.relative_to(root).as_posix()] = "rom_image"
    artifacts = [_artifact(root, path, roles[path]) for path in sorted(roles)]
    source_root = Path(__file__).resolve().parent
    source_files = [
        {
            "path": f"compiler/qwen3/{path.name}",
            "sha256": _sha256_file(path)[0],
        }
        for path in sorted(source_root.glob("*.py"))
    ]
    body = {
        "artifacts": artifacts,
        "compiler": {
            "deterministic": True,
            "source_files": source_files,
            "version": COMPILER_VERSION,
        },
        "model": {
            "checkpoint_lock_id": lock["lock_id"],
            "config_sha256": CONFIG_SHA256,
            "graph_id": graph["graph_id"],
            "id": MODEL_ID,
            "revision": REVISION,
            "target_context_tokens": TARGET_CONTEXT_TOKENS,
        },
        "runtime": {
            "attention_backends": ["eager", "sdpa"],
            "batch_size": 1,
            "decode_output": "last_position_logits",
            "requires_artifact_hash_verification": True,
            "weight_residency": "one physical stage at a time",
        },
        "schema": DEPLOYMENT_SCHEMA,
    }
    return {**body, "build_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}


def compile_official_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    output: Path,
    alignment: int = DEFAULT_ALIGNMENT,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Compile all 16.38 GB of official weights into an atomic deployment."""

    try:
        validate_checkpoint_lock(lock)
        validate_official_checkpoint_lock(lock)
    except Exception as exc:
        raise Qwen3DeploymentError(
            f"checkpoint lock is not official Qwen3-8B: {exc}"
        ) from exc
    if isinstance(alignment, bool) or not isinstance(alignment, int) or alignment < 64:
        raise Qwen3DeploymentError("alignment must be an integer >= 64")
    if alignment & (alignment - 1) or alignment > 1024 * 1024:
        raise Qwen3DeploymentError("alignment must be a power of two <= 1 MiB")
    snapshot = Path(snapshot).resolve()
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise Qwen3DeploymentError(f"snapshot is not a directory: {snapshot}")
    if output.exists():
        raise Qwen3DeploymentError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        config = load_official_config()
        specs = build_tensor_specs(config)
        graph = build_official_graph_contract()
        nodes = build_graph_nodes(config)
        program = assemble(nodes, tuple(spec.name for spec in specs), graph["graph_id"])

        (temporary / "execution").mkdir(parents=True, exist_ok=True)
        (temporary / "physical").mkdir(parents=True, exist_ok=True)
        (temporary / "schedule").mkdir(parents=True, exist_ok=True)
        write_canonical_json(temporary / "checkpoint.lock.json", lock)
        write_canonical_json(temporary / "execution/graph.json", graph)
        write_canonical_json(
            temporary / "execution/microcode_tables.json", tables_record(program)
        )
        with (temporary / "execution/microcode.bin").open("xb") as handle:
            handle.write(encode(program))
            handle.flush()
            os.fsync(handle.fileno())
        _write_text_new(temporary / "execution/microcode.disasm", disassemble(program))

        stages = _emit_images(
            temporary,
            snapshot,
            lock,
            specs,
            alignment,
            progress,
        )
        physical_map = _physical_map(lock, stages, alignment)
        write_canonical_json(temporary / "physical/physical_map.json", physical_map)
        inverse = verify_physical_images(temporary, physical_map, lock)
        write_canonical_json(temporary / "physical/inverse_report.json", inverse)
        schedule = build_schedule(program, nodes, physical_map)
        write_canonical_json(temporary / "schedule/schedule.json", schedule)
        schedule_certificate = verify_schedule(schedule, program, nodes, physical_map)
        write_canonical_json(
            temporary / "schedule/schedule_certificate.json",
            schedule_certificate,
        )

        snapshot_files = {
            "config.json": "model/config.json",
            "generation_config.json": "model/generation_config.json",
            "merges.txt": "tokenizer/merges.txt",
            "tokenizer.json": "tokenizer/tokenizer.json",
            "tokenizer_config.json": "tokenizer/tokenizer_config.json",
            "vocab.json": "tokenizer/vocab.json",
        }
        for source_name, target_name in snapshot_files.items():
            _copy_exact(snapshot / source_name, temporary / target_name)

        manifest = _manifest(temporary, lock, graph)
        write_canonical_json(temporary / "deployment_manifest.json", manifest)
        verify_deployment_artifacts(temporary, manifest)
        temporary.rename(output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "COMPILER_VERSION",
    "DEFAULT_ALIGNMENT",
    "Qwen3DeploymentError",
    "compile_official_deployment",
]
