"""Build a content-addressed bounded DeepSeek V4 Markov deployment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_markov_executable import (
    verify_deepseek_v4_markov_executable_roundtrip,
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
from compiler.microcode.deepseek_v4_markov import (
    ABI_MAJOR,
    ABI_MINOR,
    BLOCK_SIZE,
    PROGRAM_SHA256,
    assemble,
    build_program_contract,
    disassemble,
    encode,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_markov_executable_deployment.v1"
RESOURCE_SCHEMA = "opentallas.deepseek_v4_markov_resources.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_markov_executable_slice.v1"
COMPILER_VERSION = "0.1.0"
W1_NAME = "mtp.2.markov_head.markov_w1.weight"
W2_NAME = "mtp.2.markov_head.markov_w2.weight"
OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MARKOV_RANK = 256
OFFICIAL_W1_SHA256 = (
    "966bd0507046347754d0f4bf3addd6df6c179ff16243d63998258b3987e4b2f5"
)
OFFICIAL_W2_SHA256 = (
    "40ac7e99651c5c6aab8d2555ff65d247931f318414cf94baedc6da2d3bf7c175"
)
MAX_SELECTED_VOCABULARY_SIZE = 1024

CLAIM_BOUNDARY = [
    "Executes the five-step Markov program over an authenticated selected-vocabulary view.",
    "Preserves selected global token identities and original tensor-parallel row ownership.",
    "Does not execute the complete 129280-row vocabulary, checkpoint-derived base logits, or a transformer block.",
    "Functional counters are not physical traffic, cycles, schedules, RTL, PPA, or performance evidence.",
]


class DeepSeekV4MarkovExecutableBuildError(RuntimeError):
    """Raised when canonical Markov tensors cannot form a bounded deployment."""


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _safe_source(root: Path, value: object, label: str) -> Path:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4MarkovExecutableBuildError(
                f"{label} traverses a symlink"
            )
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} escapes its application"
        ) from exc
    if not current.is_file():
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{label} is not a regular file"
        )
    return current


def _selected_ids(value: object) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DeepSeekV4MarkovExecutableBuildError(
            "selected_global_token_ids must be an exact integer sequence"
        )
    result: list[int] = []
    for index, token in enumerate(value):
        if type(token) is not int or token < 0:
            raise DeepSeekV4MarkovExecutableBuildError(
                f"selected_global_token_ids[{index}] must be a nonnegative exact integer"
            )
        result.append(token)
    selected = tuple(result)
    if not selected or any(
        left >= right for left, right in zip(selected, selected[1:])
    ):
        raise DeepSeekV4MarkovExecutableBuildError(
            "selected_global_token_ids must be nonempty and strictly increasing"
        )
    if len(selected) > MAX_SELECTED_VOCABULARY_SIZE:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"selected vocabulary exceeds bounded limit {MAX_SELECTED_VOCABULARY_SIZE}"
        )
    return selected


def _assignment_table(
    application: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    raw = application.get("assignments")
    if not isinstance(raw, list):
        raise DeepSeekV4MarkovExecutableBuildError(
            "canonical application assignments are absent"
        )
    result: dict[str, list[Mapping[str, Any]]] = {}
    keys: set[tuple[str, int]] = set()
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4MarkovExecutableBuildError(
                f"canonical assignment {index} is not an object"
            )
        name = record.get("name")
        rank = record.get("rank")
        if type(name) is not str or type(rank) is not int or rank < 0:
            raise DeepSeekV4MarkovExecutableBuildError(
                f"canonical assignment {index} has invalid identity"
            )
        key = (name, rank)
        if key in keys:
            raise DeepSeekV4MarkovExecutableBuildError(
                f"canonical assignment {index} duplicates {key!r}"
            )
        keys.add(key)
        result.setdefault(name, []).append(record)
    for records in result.values():
        records.sort(key=lambda record: record["rank"])
    return result


def _validate_tensor_assignments(
    records: object,
    *,
    tensor_name: str,
) -> tuple[list[Mapping[str, Any]], int, int, str, list[tuple[int, int]]]:
    if not isinstance(records, list) or not records:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"canonical application lacks {tensor_name} assignments"
        )
    if [record.get("rank") for record in records] != list(range(len(records))):
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{tensor_name} ranks must be contiguous from zero"
        )
    full_shape: list[int] | None = None
    full_payload_sha: str | None = None
    intervals: list[tuple[int, int]] = []
    expected_start = 0
    for rank, record in enumerate(records):
        source = record.get("source")
        descriptor = source.get("slice") if isinstance(source, Mapping) else None
        shape = record.get("shape")
        if (
            record.get("name") != tensor_name
            or record.get("rank") != rank
            or record.get("transform") != "identity"
            or record.get("storage_dtype") != "BF16"
            or record.get("logical_dtype") != "BF16"
            or not isinstance(source, Mapping)
            or source.get("name") != tensor_name
            or source.get("storage_dtype") != "BF16"
            or not isinstance(source.get("shape"), list)
            or len(source["shape"]) != 2
            or any(type(extent) is not int or extent < 1 for extent in source["shape"])
            or not isinstance(descriptor, Mapping)
            or set(descriptor) != {"axis", "start", "stop"}
            or descriptor.get("axis") != 0
            or descriptor.get("start") != expected_start
            or type(descriptor.get("stop")) is not int
            or descriptor["stop"] <= expected_start
            or shape
            != [descriptor["stop"] - descriptor["start"], source["shape"][1]]
            or record.get("payload_bytes")
            != (descriptor["stop"] - descriptor["start"])
            * source["shape"][1]
            * 2
        ):
            raise DeepSeekV4MarkovExecutableBuildError(
                f"{tensor_name} rank {rank} slicing metadata differs"
            )
        if full_shape is None:
            full_shape = list(source["shape"])
            full_payload_sha = _digest(
                source.get("payload_sha256"), f"{tensor_name} full payload SHA"
            )
        elif (
            source["shape"] != full_shape
            or source.get("payload_sha256") != full_payload_sha
        ):
            raise DeepSeekV4MarkovExecutableBuildError(
                f"{tensor_name} rank {rank} source authority differs"
            )
        _digest(record.get("sha256"), f"{tensor_name} rank {rank} SHA")
        intervals.append((descriptor["start"], descriptor["stop"]))
        expected_start = descriptor["stop"]
    assert full_shape is not None and full_payload_sha is not None
    if expected_start != full_shape[0]:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{tensor_name} assignments do not cover the full vocabulary"
        )
    return records, full_shape[0], full_shape[1], full_payload_sha, intervals


def _validate_resources(
    application: Mapping[str, Any],
    selected: tuple[int, ...],
) -> tuple[
    list[Mapping[str, Any]],
    list[Mapping[str, Any]],
    dict[str, int],
    dict[str, str],
    list[tuple[int, ...]],
    list[tuple[int, int]],
]:
    assignments = _assignment_table(application)
    w1, vocabulary, rank_width, w1_full_sha, intervals = (
        _validate_tensor_assignments(assignments.get(W1_NAME), tensor_name=W1_NAME)
    )
    w2, w2_vocabulary, w2_rank_width, w2_full_sha, w2_intervals = (
        _validate_tensor_assignments(assignments.get(W2_NAME), tensor_name=W2_NAME)
    )
    if (
        len(w1) != len(w2)
        or vocabulary != w2_vocabulary
        or rank_width != w2_rank_width
        or intervals != w2_intervals
    ):
        raise DeepSeekV4MarkovExecutableBuildError("W1 and W2 topology differs")
    if selected[-1] >= vocabulary:
        raise DeepSeekV4MarkovExecutableBuildError(
            "selected global token ID exceeds the canonical vocabulary"
        )
    per_rank: list[tuple[int, ...]] = []
    for start, stop in intervals:
        per_rank.append(tuple(token for token in selected if start <= token < stop))
    counts = {len(tokens) for tokens in per_rank}
    if 0 in counts or len(counts) != 1:
        raise DeepSeekV4MarkovExecutableBuildError(
            "selected vocabulary must contain the same nonzero row count per rank"
        )
    if tuple(token for tokens in per_rank for token in tokens) != selected:
        raise DeepSeekV4MarkovExecutableBuildError(
            "selected rank ownership does not reconstruct global token order"
        )
    dimensions = {
        "block_size": BLOCK_SIZE,
        "full_vocabulary_size": vocabulary,
        "markov_rank": rank_width,
        "model_parallel": len(w1),
        "selected_rows_per_rank": len(per_rank[0]),
        "selected_vocabulary_size": len(selected),
    }
    return (
        w1,
        w2,
        dimensions,
        {W1_NAME: w1_full_sha, W2_NAME: w2_full_sha},
        per_rank,
        intervals,
    )


def _extract_rows(
    *,
    application_root: Path,
    record: Mapping[str, Any],
    tensor_name: str,
    global_ids: tuple[int, ...],
    row_start: int,
    markov_rank: int,
) -> tuple[bytes, dict[str, Any]]:
    source_path = _safe_source(
        application_root,
        record.get("path"),
        f"{tensor_name} rank {record.get('rank')} source",
    )
    try:
        source_payload = source_path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"cannot read {tensor_name} rank {record.get('rank')}: {exc}"
        ) from exc
    observed_sha = hashlib.sha256(source_payload).hexdigest()
    expected_sha = _digest(
        record.get("sha256"), f"{tensor_name} rank {record.get('rank')} SHA"
    )
    expected_size = record.get("payload_bytes")
    if (
        type(expected_size) is not int
        or len(source_payload) != expected_size
        or observed_sha != expected_sha
    ):
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{tensor_name} rank {record.get('rank')} changed during extraction"
        )
    row_bytes = markov_rank * 2
    selected_payload = b"".join(
        source_payload[
            (token - row_start) * row_bytes : (token - row_start + 1) * row_bytes
        ]
        for token in global_ids
    )
    if len(selected_payload) != len(global_ids) * row_bytes:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"{tensor_name} selected-row extraction truncated"
        )
    return selected_payload, {
        "source_assignment_path": record["path"],
        "source_assignment_sha256": expected_sha,
        "source_assignment_size_bytes": expected_size,
    }


def _write_selected_payload(
    root: Path,
    *,
    relative: str,
    payload: bytes,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except OSError as exc:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"cannot write selected Markov payload {relative!r}: {exc}"
        ) from exc
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        **dict(source),
    }


def _artifact_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"cannot hash deployment artifact {path.name!r}: {exc}"
        ) from exc
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _build_into(
    *,
    application_root: Path,
    application: Mapping[str, Any],
    verification: Mapping[str, Any],
    selected: tuple[int, ...],
    root: Path,
) -> dict[str, Any]:
    w1, w2, dimensions, full_hashes, per_rank, intervals = _validate_resources(
        application, selected
    )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official and (
        dimensions
        != {
            "block_size": 5,
            "full_vocabulary_size": OFFICIAL_VOCABULARY_SIZE,
            "markov_rank": OFFICIAL_MARKOV_RANK,
            "model_parallel": 4,
            "selected_rows_per_rank": len(selected) // 4,
            "selected_vocabulary_size": len(selected),
        }
        or full_hashes
        != {W1_NAME: OFFICIAL_W1_SHA256, W2_NAME: OFFICIAL_W2_SHA256}
    ):
        raise DeepSeekV4MarkovExecutableBuildError(
            "official Markov resources differ from the pinned V4 release"
        )

    rank_records: list[dict[str, Any]] = []
    payload_roles: dict[str, str] = {}
    for rank, (global_ids, interval) in enumerate(zip(per_rank, intervals, strict=True)):
        selected_w1, w1_source = _extract_rows(
            application_root=application_root,
            record=w1[rank],
            tensor_name=W1_NAME,
            global_ids=global_ids,
            row_start=interval[0],
            markov_rank=dimensions["markov_rank"],
        )
        selected_w2, w2_source = _extract_rows(
            application_root=application_root,
            record=w2[rank],
            tensor_name=W2_NAME,
            global_ids=global_ids,
            row_start=interval[0],
            markov_rank=dimensions["markov_rank"],
        )
        w1_relative = f"rom/markov_w1/rank-{rank:03d}.bf16"
        w2_relative = f"rom/markov_w2/rank-{rank:03d}.bf16"
        w1_record = _write_selected_payload(
            root, relative=w1_relative, payload=selected_w1, source=w1_source
        )
        w2_record = _write_selected_payload(
            root, relative=w2_relative, payload=selected_w2, source=w2_source
        )
        rank_records.append(
            {
                "global_token_ids": list(global_ids),
                "rank": rank,
                "row_start": interval[0],
                "row_stop": interval[1],
                "w1": w1_record,
                "w2": w2_record,
            }
        )
        payload_roles[w1_relative] = f"markov_w1_rank_{rank:03d}"
        payload_roles[w2_relative] = f"markov_w2_rank_{rank:03d}"

    resources = {
        "application_id": application["application_id"],
        "full_vocabulary_size": dimensions["full_vocabulary_size"],
        "markov_rank": dimensions["markov_rank"],
        "model_parallel": dimensions["model_parallel"],
        "ranks": rank_records,
        "schema": RESOURCE_SCHEMA,
        "selected_global_token_ids": list(selected),
        "selected_vocabulary_size": dimensions["selected_vocabulary_size"],
        "source_tensor_payload_sha256": full_hashes,
    }
    write_canonical_json(root / "resource_manifest.json", resources)

    source = application.get("source")
    if not isinstance(source, Mapping):
        raise DeepSeekV4MarkovExecutableBuildError(
            "canonical application source authority is absent"
        )
    semantic = {
        "claim_boundary": CLAIM_BOUNDARY,
        "dimensions": dimensions,
        "global_token_mapping": [
            {"local_index": index, "global_token_id": token}
            for index, token in enumerate(selected)
        ],
        "model_id": MODEL_ID,
        "numeric_profile": "opentallas.deepseek_v4_markov_loop_binary32.v1",
        "operations": [
            "TOKEN_LOOKUP",
            "VOCABULARY_PROJECT",
            "BINARY32_BIAS_ADD",
            "SAMPLE_AND_CARRY",
            "COMPLETE",
        ],
        "outputs": [
            "output_global_token_ids",
            "output_local_token_ids",
            "markov_embeddings_bf16_codes",
            "markov_bias_binary32_codes",
            "adjusted_logits_binary32_codes",
            "entropy_continuation",
        ],
        "schema": SEMANTIC_SCHEMA,
        "source": {
            "application_id": application["application_id"],
            "application_status": application["status"],
            "checkpoint_lock_id": source["checkpoint_lock_id"],
            "evidence_scope": application["evidence_scope"],
            "repository": source["repository"],
            "revision": source["revision"],
            "verification_id": verification["verification_id"],
        },
    }
    write_canonical_json(root / "model.ir.json", semantic)

    program = assemble()
    program_payload = encode(program)
    if hashlib.sha256(program_payload).hexdigest() != PROGRAM_SHA256:
        raise DeepSeekV4MarkovExecutableBuildError(
            "assembled Markov program identity differs"
        )
    (root / "microcode.bin").write_bytes(program_payload)
    (root / "microcode.disasm").write_text(
        disassemble(program), encoding="ascii", newline="\n"
    )
    write_canonical_json(
        root / "program_contract.json",
        build_program_contract(program_sha256=PROGRAM_SHA256),
    )
    roundtrip = verify_deepseek_v4_markov_executable_roundtrip(
        root, application_root
    )
    write_canonical_json(root / "roundtrip_report.json", roundtrip)

    roles = {
        "microcode.bin": "microcode",
        "microcode.disasm": "microcode_disassembly",
        "model.ir.json": "semantic_ir",
        "program_contract.json": "program_contract",
        "resource_manifest.json": "resource_manifest",
        "roundtrip_report.json": "roundtrip_report",
        **payload_roles,
    }
    artifacts = [
        _artifact_record(root / relative, root, roles[relative])
        for relative in sorted(roles)
    ]
    abi = {
        "major": ABI_MAJOR,
        "minor": ABI_MINOR,
        "name": "deepseek_v4_markov",
        "program_sha256": PROGRAM_SHA256,
    }
    identity = {
        "artifacts": artifacts,
        "compiler_version": COMPILER_VERSION,
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "selected_global_token_ids": list(selected),
        "source_application_id": application["application_id"],
    }
    build_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    deployment = {
        "artifacts": artifacts,
        "build_id": build_id,
        "claim_boundary": CLAIM_BOUNDARY,
        "compiler": {
            "name": "opentallas-deepseek-v4-markov-executable-compiler",
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "microcode": "microcode.bin",
            "program_contract": "program_contract.json",
            "resource_manifest": "resource_manifest.json",
            "semantic_ir": "model.ir.json",
        },
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "schema": DEPLOYMENT_SCHEMA,
        "selected_global_token_ids": list(selected),
        "source_application_id": application["application_id"],
        "status": (
            "official_checkpoint_selected_vocabulary_markov_not_full_model"
            if official
            else "development_fixture_selected_vocabulary_markov_not_release_evidence"
        ),
    }
    write_canonical_json(root / "deployment_manifest.json", deployment)
    return deployment


def build_deepseek_v4_markov_executable_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
    selected_global_token_ids: Sequence[int],
) -> dict[str, Any]:
    """Verify canonical resources and atomically emit a bounded deployment."""

    validate_checkpoint_lock(lock)
    selected = _selected_ids(selected_global_token_ids)
    snapshot = Path(snapshot).resolve()
    application_root = Path(application_root).resolve()
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise DeepSeekV4MarkovExecutableBuildError(
            f"checkpoint snapshot is not a directory: {snapshot}"
        )
    if not application_root.is_dir():
        raise DeepSeekV4MarkovExecutableBuildError(
            f"canonical application is not a directory: {application_root}"
        )
    if output.exists():
        raise DeepSeekV4MarkovExecutableBuildError(
            f"output already exists: {output}"
        )
    if output == Path(output.anchor):
        raise DeepSeekV4MarkovExecutableBuildError(
            "output must not be a filesystem root"
        )
    try:
        application = load_strict_json(application_root / MANIFEST_FILENAME)
        retained = load_strict_json(application_root / VERIFICATION_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4MarkovExecutableBuildError(
            f"cannot load canonical application evidence: {exc}"
        ) from exc
    verification = verify_canonical_application(application_root, snapshot, lock)
    if retained != verification:
        raise DeepSeekV4MarkovExecutableBuildError(
            "retained canonical verification differs from independent replay"
        )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official:
        validate_official_checkpoint_lock(lock, load_official_config())
        source = application.get("source")
        if not isinstance(source, Mapping) or (
            source.get("repository"), source.get("revision")
        ) != (REPOSITORY, REVISION):
            raise DeepSeekV4MarkovExecutableBuildError(
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
            selected=selected,
            root=temporary,
        )
        os.replace(temporary, output)
        return deployment
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


__all__ = [
    "CLAIM_BOUNDARY",
    "DEPLOYMENT_SCHEMA",
    "DeepSeekV4MarkovExecutableBuildError",
    "RESOURCE_SCHEMA",
    "SEMANTIC_SCHEMA",
    "build_deepseek_v4_markov_executable_deployment",
]
