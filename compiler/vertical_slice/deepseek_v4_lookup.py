"""Compile canonical DeepSeek V4 lookup tensors into an executable slice."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import shutil
import struct
import tempfile
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_lookup_slice import (
    verify_deepseek_v4_lookup_roundtrip,
)
from compiler.frontend.checkpoint import validate_checkpoint_lock
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from compiler.microcode.deepseek_v4_lookup import (
    ABI_MAJOR,
    ABI_MINOR,
    assemble,
    disassemble,
    encode,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_lookup_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_lookup_slice.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_lookup_tensors.v1"
EXPECTATION_SCHEMA = "opentallas.deepseek_v4_lookup_expectations.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_lookup_coverage.v1"
COMPILER_VERSION = "0.1.0"

EMBEDDING_NAME = "embed.weight"
HASH_ROUTE_NAME = "layers.0.ffn.gate.tid2eid"


class DeepSeekV4LookupBuildError(RuntimeError):
    """Raised when a canonical application cannot form the lookup slice."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _safe_source(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4LookupBuildError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4LookupBuildError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4LookupBuildError(f"{label} is not canonical POSIX")
    path = root / relative
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4LookupBuildError(f"{label} traverses a symlink")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4LookupBuildError(f"{label} escapes its application") from exc
    if not path.is_file():
        raise DeepSeekV4LookupBuildError(f"{label} is not a regular file")
    return path


def _copy_locked(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with source.open("rb") as source_handle, destination.open("xb") as output:
            while chunk := source_handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
    except OSError as exc:
        raise DeepSeekV4LookupBuildError(
            f"cannot copy canonical artifact {source.name!r}: {exc}"
        ) from exc
    observed = digest.hexdigest()
    if observed != expected_sha256 or size != expected_size:
        raise DeepSeekV4LookupBuildError(
            f"canonical artifact {source.name!r} changed during compilation"
        )
    return observed, size


def _validate_route_values(
    path: Path,
    *,
    expert_count: int,
    expected_elements: int,
) -> None:
    observed_elements = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                if len(chunk) % 8:
                    raise DeepSeekV4LookupBuildError(
                        "hash-route payload is not aligned to signed int64"
                    )
                for (expert_id,) in struct.iter_unpack("<q", chunk):
                    if not 0 <= expert_id < expert_count:
                        raise DeepSeekV4LookupBuildError(
                            f"hash-route expert ID {expert_id} is outside "
                            f"[0, {expert_count})"
                        )
                    observed_elements += 1
    except OSError as exc:
        raise DeepSeekV4LookupBuildError(
            f"cannot validate hash-route payload: {exc}"
        ) from exc
    if observed_elements != expected_elements:
        raise DeepSeekV4LookupBuildError(
            "hash-route element count differs from its declared shape"
        )


def _assignment_table(application: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    raw = application.get("assignments")
    if not isinstance(raw, list):
        raise DeepSeekV4LookupBuildError("canonical application lacks assignments")
    result: dict[str, list[Mapping[str, Any]]] = {}
    keys: set[tuple[int, str]] = set()
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4LookupBuildError(
                f"canonical assignment {index} is not an object"
            )
        name = record.get("name")
        rank = record.get("rank")
        if (
            not isinstance(name, str)
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank < 0
            or (rank, name) in keys
        ):
            raise DeepSeekV4LookupBuildError(
                f"canonical assignment {index} has an invalid identity"
            )
        keys.add((rank, name))
        result.setdefault(name, []).append(record)
    for records in result.values():
        records.sort(key=lambda record: record["rank"])
    return result


def _positive(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DeepSeekV4LookupBuildError(f"{label} must be a positive integer")
    return value


def _validate_resources(
    application: Mapping[str, Any],
    *,
    hc_multiplier: int,
    expert_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], dict[str, int]]:
    by_name = _assignment_table(application)
    embedding = by_name.get(EMBEDDING_NAME)
    routes = by_name.get(HASH_ROUTE_NAME)
    if not embedding or not routes:
        raise DeepSeekV4LookupBuildError(
            "application must contain embed.weight and layers.0.ffn.gate.tid2eid"
        )
    ranks = [record["rank"] for record in embedding]
    if ranks != list(range(len(embedding))):
        raise DeepSeekV4LookupBuildError("embedding ranks must be contiguous from zero")
    if [record["rank"] for record in routes] != ranks:
        raise DeepSeekV4LookupBuildError(
            "hash-route replicas must cover the embedding ranks"
        )

    first_source = embedding[0].get("source")
    if not isinstance(first_source, Mapping):
        raise DeepSeekV4LookupBuildError("embedding source metadata is absent")
    source_shape = first_source.get("shape")
    if (
        not isinstance(source_shape, list)
        or len(source_shape) != 2
        or any(
            isinstance(extent, bool) or not isinstance(extent, int) or extent < 1
            for extent in source_shape
        )
    ):
        raise DeepSeekV4LookupBuildError("embedding source shape is invalid")
    vocabulary_size, hidden_size = source_shape
    expected_start = 0
    for record in embedding:
        source = record.get("source")
        descriptor = source.get("slice") if isinstance(source, Mapping) else None
        shape = record.get("shape")
        if (
            record.get("transform") != "identity"
            or record.get("storage_dtype") != "BF16"
            or record.get("logical_dtype") != "BF16"
            or not isinstance(source, Mapping)
            or source.get("name") != EMBEDDING_NAME
            or source.get("shape") != source_shape
            or source.get("storage_dtype") != "BF16"
            or not isinstance(descriptor, Mapping)
            or set(descriptor) != {"axis", "start", "stop"}
            or descriptor.get("axis") != 0
            or descriptor.get("start") != expected_start
            or not isinstance(descriptor.get("stop"), int)
            or descriptor["stop"] <= expected_start
            or shape != [descriptor["stop"] - expected_start, hidden_size]
            or record.get("payload_bytes")
            != (descriptor["stop"] - expected_start) * hidden_size * 2
        ):
            raise DeepSeekV4LookupBuildError(
                f"embedding rank {record.get('rank')!r} has illegal slicing metadata"
            )
        expected_start = descriptor["stop"]
    if expected_start != vocabulary_size:
        raise DeepSeekV4LookupBuildError("embedding ranks do not cover the vocabulary")

    route_hash: str | None = None
    route_bytes: int | None = None
    route_top_k: int | None = None
    for record in routes:
        source = record.get("source")
        shape = record.get("shape")
        if (
            record.get("transform") != "identity"
            or record.get("storage_dtype") != "I64"
            or record.get("logical_dtype") != "INT64"
            or not isinstance(source, Mapping)
            or source.get("name") != HASH_ROUTE_NAME
            or source.get("slice") is not None
            or source.get("storage_dtype") != "I64"
            or not isinstance(shape, list)
            or len(shape) != 2
            or shape[0] != vocabulary_size
            or isinstance(shape[1], bool)
            or not isinstance(shape[1], int)
            or shape[1] < 1
            or record.get("payload_bytes") != vocabulary_size * shape[1] * 8
        ):
            raise DeepSeekV4LookupBuildError(
                f"hash-route rank {record.get('rank')!r} has illegal metadata"
            )
        if route_top_k is None:
            route_top_k = shape[1]
            route_hash = record.get("sha256")
            route_bytes = record.get("payload_bytes")
        elif (
            shape[1] != route_top_k
            or record.get("sha256") != route_hash
            or record.get("payload_bytes") != route_bytes
        ):
            raise DeepSeekV4LookupBuildError(
                "hash-route rank replicas are not byte-identical"
            )
    assert route_top_k is not None
    dimensions = {
        "expert_count": expert_count,
        "hc_multiplier": hc_multiplier,
        "hidden_size": hidden_size,
        "model_parallel": len(embedding),
        "route_top_k": route_top_k,
        "vocabulary_size": vocabulary_size,
    }
    return embedding, routes, dimensions


def _artifact_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    digest, size = _sha256_file(path)
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _build_into(
    *,
    application_root: Path,
    application: Mapping[str, Any],
    verification: Mapping[str, Any],
    root: Path,
    hc_multiplier: int,
    expert_count: int,
) -> dict[str, Any]:
    embedding, routes, dimensions = _validate_resources(
        application,
        hc_multiplier=hc_multiplier,
        expert_count=expert_count,
    )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official and dimensions != {
        "expert_count": 256,
        "hc_multiplier": 4,
        "hidden_size": 4096,
        "model_parallel": 4,
        "route_top_k": 6,
        "vocabulary_size": 129280,
    }:
        raise DeepSeekV4LookupBuildError(
            "official lookup slice dimensions differ from the pinned V4 release"
        )

    embedding_ranks: list[dict[str, Any]] = []
    for record in embedding:
        rank = record["rank"]
        source = _safe_source(
            application_root,
            record["path"],
            f"embedding rank {rank} source",
        )
        relative = f"rom/embed/rank-{rank:03d}.bin"
        destination = root / relative
        digest, size = _copy_locked(
            source,
            destination,
            expected_sha256=record["sha256"],
            expected_size=record["payload_bytes"],
        )
        descriptor = record["source"]["slice"]
        embedding_ranks.append(
            {
                "path": relative,
                "rank": rank,
                "row_start": descriptor["start"],
                "row_stop": descriptor["stop"],
                "sha256": digest,
                "size_bytes": size,
                "source_assignment_path": record["path"],
            }
        )

    route_source_record = routes[0]
    route_source = _safe_source(
        application_root,
        route_source_record["path"],
        "hash-route source",
    )
    route_relative = "rom/hash_route.bin"
    route_digest, route_size = _copy_locked(
        route_source,
        root / route_relative,
        expected_sha256=route_source_record["sha256"],
        expected_size=route_source_record["payload_bytes"],
    )
    _validate_route_values(
        root / route_relative,
        expert_count=dimensions["expert_count"],
        expected_elements=(
            dimensions["vocabulary_size"] * dimensions["route_top_k"]
        ),
    )
    tensor_manifest = {
        "embedding": {
            "dtype": "BF16",
            "hidden_size": dimensions["hidden_size"],
            "ranks": embedding_ranks,
            "vocabulary_size": dimensions["vocabulary_size"],
        },
        "hash_route": {
            "dtype": "I64",
            "expert_count": dimensions["expert_count"],
            "path": route_relative,
            "route_top_k": dimensions["route_top_k"],
            "sha256": route_digest,
            "size_bytes": route_size,
            "source_assignment_path": route_source_record["path"],
            "source_rank": route_source_record["rank"],
            "verified_replica_ranks": [record["rank"] for record in routes],
            "vocabulary_size": dimensions["vocabulary_size"],
        },
        "schema": TENSOR_SCHEMA,
    }
    write_canonical_json(root / "tensor_manifest.json", tensor_manifest)

    source_record = application["source"]
    semantic = {
        "claim_boundary": (
            "Three real-payload pure operators only; not a transformer block, "
            "complete decode, hardware timing, or full-model execution."
        ),
        "dimensions": dimensions,
        "model_id": MODEL_ID,
        "numeric_profile": "deepseek_v4_flash_lookup_bits_v1",
        "operations": [
            {
                "id": "token_embed",
                "input": "token_ids",
                "kind": "TOKEN_EMBED",
                "output": "embedding_bf16_codes",
                "resource": EMBEDDING_NAME,
            },
            {
                "id": "hc_expand",
                "input": "embedding_bf16_codes",
                "kind": "HC_EXPAND",
                "output": "hc_hidden_bf16_codes",
                "resource": None,
            },
            {
                "id": "hash_route",
                "input": "token_ids",
                "kind": "HASH_ROUTE",
                "output": "expert_ids",
                "resource": HASH_ROUTE_NAME,
            },
        ],
        "outputs": [
            "embedding_bf16_codes",
            "hc_hidden_bf16_codes",
            "expert_ids",
        ],
        "schema": SEMANTIC_SCHEMA,
        "source": {
            "application_id": application["application_id"],
            "application_status": application["status"],
            "checkpoint_lock_id": source_record["checkpoint_lock_id"],
            "evidence_scope": application["evidence_scope"],
            "repository": source_record["repository"],
            "revision": source_record["revision"],
            "verification_id": verification["verification_id"],
        },
    }
    write_canonical_json(root / "model.ir.json", semantic)
    instructions = assemble(hc_multiplier)
    (root / "microcode.bin").write_bytes(encode(instructions))
    (root / "microcode.disasm").write_text(
        disassemble(instructions), encoding="ascii", newline="\n"
    )
    expectations = {
        "counter_coefficients_per_token": {
            "bf16_codes_copied": hc_multiplier * dimensions["hidden_size"],
            "logical_activation_bytes_read": dimensions["hidden_size"] * 2,
            "logical_activation_bytes_written": (
                dimensions["hidden_size"] * 2
                + hc_multiplier * dimensions["hidden_size"] * 2
                + dimensions["route_top_k"] * 8
            ),
            "logical_input_bytes_read": 16,
            "logical_rom_bytes_read": (
                dimensions["hidden_size"] * 2
                + dimensions["route_top_k"] * 8
            ),
            "rom_lookup_rows": 2,
        },
        "fixed_counters": {
            "completion_events": 1,
            "micro_ops_executed": 4,
            "semantic_operations_executed": 3,
        },
        "hardware_accounting": {
            "cycles": None,
            "hbm_transactions": None,
            "stalls": None,
            "status": "not modeled by the functional lookup slice",
        },
        "schema": EXPECTATION_SCHEMA,
    }
    write_canonical_json(root / "execution_expectations.json", expectations)
    coverage = {
        "implemented_operator_kinds": ["HASH_ROUTE", "HC_EXPAND", "TOKEN_EMBED"],
        "model_id": MODEL_ID,
        "schema": COVERAGE_SCHEMA,
        "status": "three_operator_real_payload_slice_only",
        "unimplemented_graph_operator_kind_count": 40,
    }
    write_canonical_json(root / "operator_coverage.json", coverage)
    roundtrip = verify_deepseek_v4_lookup_roundtrip(root, application_root)
    write_canonical_json(root / "roundtrip_report.json", roundtrip)

    roles = {
        "execution_expectations.json": "execution_expectations",
        "microcode.bin": "microcode",
        "microcode.disasm": "microcode_disassembly",
        "model.ir.json": "semantic_ir",
        "operator_coverage.json": "operator_coverage",
        "roundtrip_report.json": "roundtrip_report",
        "tensor_manifest.json": "tensor_manifest",
    }
    for rank_record in embedding_ranks:
        roles[rank_record["path"]] = f"embedding_rank_{rank_record['rank']:03d}"
    roles[route_relative] = "hash_route_table"
    artifacts = [
        _artifact_record(root / relative, root, roles[relative])
        for relative in sorted(roles)
    ]
    identity = {
        "artifacts": artifacts,
        "compiler_version": COMPILER_VERSION,
        "microcode_abi": {
            "major": ABI_MAJOR,
            "minor": ABI_MINOR,
            "name": "deepseek_v4_lookup",
        },
        "model_id": MODEL_ID,
        "source_application_id": application["application_id"],
    }
    build_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    deployment = {
        "artifacts": artifacts,
        "build_id": build_id,
        "claim_boundary": [
            "Executes TOKEN_EMBED, HC_EXPAND, and HASH_ROUTE only.",
            "Does not execute a transformer block, attention, MoE arithmetic, logits, or decode state.",
            "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
        ],
        "compiler": {
            "name": "opentallas-deepseek-v4-lookup-slice-compiler",
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "execution_expectations": "execution_expectations.json",
            "microcode": "microcode.bin",
            "semantic_ir": "model.ir.json",
            "tensor_manifest": "tensor_manifest.json",
        },
        "microcode_abi": identity["microcode_abi"],
        "model_id": MODEL_ID,
        "schema": DEPLOYMENT_SCHEMA,
        "source_application_id": application["application_id"],
        "status": (
            "real_checkpoint_lookup_slice_not_full_model"
            if official
            else "development_fixture_lookup_slice_not_release_evidence"
        ),
    }
    write_canonical_json(root / "deployment_manifest.json", deployment)
    return deployment


def build_deepseek_v4_lookup_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
    hc_multiplier: int = 4,
    expert_count: int = 256,
) -> dict[str, Any]:
    """Verify a canonical application and atomically build the lookup slice."""

    validate_checkpoint_lock(lock)
    hc_multiplier = _positive(hc_multiplier, "hc_multiplier")
    expert_count = _positive(expert_count, "expert_count")
    application_root = Path(application_root).resolve()
    output = Path(output).resolve()
    if not application_root.is_dir():
        raise DeepSeekV4LookupBuildError(
            f"canonical application is not a directory: {application_root}"
        )
    if output.exists():
        raise DeepSeekV4LookupBuildError(f"output already exists: {output}")
    if output == Path(output.anchor):
        raise DeepSeekV4LookupBuildError("output must not be a filesystem root")
    try:
        application = load_strict_json(application_root / MANIFEST_FILENAME)
        retained = load_strict_json(application_root / VERIFICATION_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4LookupBuildError(
            f"cannot load canonical application evidence: {exc}"
        ) from exc
    verification = verify_canonical_application(application_root, snapshot, lock)
    if retained != verification:
        raise DeepSeekV4LookupBuildError(
            "retained canonical verification differs from independent replay"
        )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official:
        validate_official_checkpoint_lock(lock, load_official_config())
        source = application.get("source")
        if not isinstance(source, Mapping) or (
            source.get("repository"), source.get("revision")
        ) != (REPOSITORY, REVISION):
            raise DeepSeekV4LookupBuildError(
                "official application is not the pinned V4 Flash release"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent)
    )
    try:
        deployment = _build_into(
            application_root=application_root,
            application=application,
            verification=verification,
            root=temporary,
            hc_multiplier=hc_multiplier,
            expert_count=expert_count,
        )
        os.replace(temporary, output)
        return deployment
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


__all__ = [
    "DeepSeekV4LookupBuildError",
    "build_deepseek_v4_lookup_deployment",
]
