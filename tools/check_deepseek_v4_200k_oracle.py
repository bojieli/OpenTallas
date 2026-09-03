#!/usr/bin/env python3
"""Fail-closed acceptance check for the exact DeepSeek V4 Flash 200K oracle.

This checks an external reference result; it does not execute, seed, or repair
an accelerator run.  Acceptance requires the exact natural 200,000-token
prompt, current producer sources, the pinned vendor checkpoint, legal decoded
tokens, vendor-selection agreement at every step, and termination at the first
official EOS or exactly 256 generated tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v4_tokenizer import (  # noqa: E402
    load_verified_deepseek_v4_tokenizer,
)

SCHEMA = "opentallas.abi3.deepseek_v4_200k_oracle_acceptance.v1"
ORACLE_SCHEMA = "opentallas.abi3.reference_oracle.v1"
MODEL_ID = "deepseek-v4-flash-0731"
WORKLOAD_ID = "TA-DS-CTX-200K-1"
OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
PROMPT_TOKENS = 200_000
MAX_NEW_TOKENS = 256
VOCABULARY_SIZE = 129_280
EOS_TOKEN_ID = 1
SELECTION = "greedy_lowest_token_id_argmax"

WORKLOAD_DIGEST = "803f0c3a3e9bf7ef68ddff00947576d2fab5703d1f4387df1eb2ec11be2c59bd"
WORKLOAD_SOURCE_SHA256 = (
    "b00dd2f461329c14e0a8c0863dbef78e066950bee0aba053aa651f91890418bb"
)
WORKLOAD_INDEX_SHA256 = (
    "45f478d457d0e617d1ef06e6f5a5b542bc567bd911be28072fa10ec6c625d310"
)
RENDERED_TEXT_SHA256 = (
    "6ad57114c426156f7e25341d6faa55d061033e6b98244d31ab1e8a395463527a"
)
TOKENIZER_SHA256 = (
    "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
)
CHECKPOINT_SOURCE_SHA256 = (
    "c9cf820d5183a4de2fdd51769535b48d6a47975a6d707f5d1b2f105af64141c5"
)

DEFAULT_ORACLE = (
    REPO / "results" / "abi3" / "deepseek_v4_reference_oracle_context_ladder.json"
)
DEFAULT_WORKLOAD = REPO / "build" / "workloads" / MODEL_ID / f"{WORKLOAD_ID}.json"
DEFAULT_INDEX = REPO / "build" / "workloads" / MODEL_ID / "index.json"
DEFAULT_CHECKPOINT_SOURCE = (
    REPO / "compiler" / "models" / MODEL_ID / "checkpoint_source.json"
)
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    f"{OFFICIAL_REVISION}"
)

# The producer records this non-removable set.  Every recorded extra source is
# also checked, so neither omission nor an ignored addition can make a stale
# oracle appear source-current.
REQUIRED_PRODUCER_SOURCES = (
    "compiler/frontend/deepseek_v4_tokenizer.py",
    "runtime/reference/deepseek_v4_oracle.py",
    "tools/deepseek_v4_prefill_tiling.py",
    "tools/run_deepseek_v4_reference_oracle.py",
)

REQUIRED_VENDOR_SOURCES = (
    "encoding/encoding_dsv4.py",
    "inference/config.json",
    "inference/kernel.py",
    "inference/model.py",
    "tokenizer.json",
)

QUALIFIED_PACKAGE_VERSIONS = {
    "apache-tvm-ffi": "0.1.8.post2",
    "safetensors": "0.8.0",
    "tilelang": "0.1.8",
    "tokenizers": "0.22.2",
    "torch": "2.10.0+cu128",
    "transformers": "4.57.6",
}
QUALIFIED_TILE_GEOMETRY = {
    "compressor_positions_per_tile": 16_384,
    "expert_rows_per_tile": 8_192,
    "hyper_connection_residual_on_host": True,
    "hyper_connection_tile": 2_048,
    "indexer_score_block_bytes": 819_200_000,
    "indexer_sub_tile": 128,
    "sequence_tile": 4_096,
    "sequence_tiles": 49,
}
REQUIRED_ADAPTATIONS = {
    "dspark_stages_not_built",
    "endpoint_residency",
    "hadamard_fallback_available_but_unused",
    "layer_streaming",
    "prefill_sequence_tiling",
    "routed_experts_via_vendor_fp8_recast",
    "sparse_attn_head_split",
}

# These are the executable accelerator/compiler regions in which importing the
# external comparator would turn an independent check into oracle injection.
ACCELERATOR_SOURCE_ROOTS = (
    "compiler/backends",
    "compiler/ir",
    "runtime/abi3",
    "runtime/driver.py",
    "runtime/sim",
    "runtime/tensor_accelerator",
    "tools/run_accelerator_tokens.py",
)
FORBIDDEN_ORACLE_DEPENDENCIES = (
    "deepseek_v4_oracle",
    "run_deepseek_v4_reference_oracle",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return _sha256_bytes(encoded)


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def _is_int(value: object, *, minimum: int = 0) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= minimum
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _workload_digest(workload: Mapping[str, Any]) -> str:
    body = {
        "workload_id": workload.get("workload_id"),
        "kind": workload.get("kind"),
        "token_ids": workload.get("token_ids"),
        "max_new_tokens": workload.get("max_new_tokens"),
    }
    return _canonical_digest(body)


def validate_workload_inputs(
    workload_path: Path, index_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    problems: list[str] = []
    workload = _load_object(workload_path)
    index = _load_object(index_path)
    workload_source_sha256 = _sha256(workload_path)
    index_source_sha256 = _sha256(index_path)

    if workload_source_sha256 != WORKLOAD_SOURCE_SHA256:
        problems.append("200K workload file is not the frozen source byte sequence")
    if index_source_sha256 != WORKLOAD_INDEX_SHA256:
        problems.append("DeepSeek workload index is not the frozen source byte sequence")
    if workload.get("workload_id") != WORKLOAD_ID:
        problems.append("workload_id is not TA-DS-CTX-200K-1")
    if workload.get("kind") != "long_natural":
        problems.append("200K workload is not the natural-context workload")
    if workload.get("max_new_tokens") != MAX_NEW_TOKENS:
        problems.append("200K workload does not declare a 256-token generation cap")
    if workload.get("prompt_token_count") != PROMPT_TOKENS:
        problems.append("workload prompt_token_count is not exactly 200,000")
    metadata = workload.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("mandatory_contract") is not True:
        problems.append("workload is not marked as the mandatory contract")

    token_ids = workload.get("token_ids")
    legal_prompt = (
        isinstance(token_ids, list)
        and len(token_ids) == PROMPT_TOKENS
        and all(_is_int(token) and token < VOCABULARY_SIZE for token in token_ids)
    )
    if not legal_prompt:
        problems.append("prompt is not exactly 200,000 legal vocabulary IDs")
    elif EOS_TOKEN_ID in token_ids:
        problems.append("natural prompt unexpectedly embeds the official EOS token")
    if workload.get("digest") != WORKLOAD_DIGEST:
        problems.append("workload does not carry the frozen logical digest")
    if _workload_digest(workload) != WORKLOAD_DIGEST:
        problems.append("independently recomputed workload digest does not match")

    rendered_text = workload.get("rendered_text")
    rendered_sha256 = (
        _sha256_bytes(rendered_text.encode("utf-8"))
        if isinstance(rendered_text, str)
        else None
    )
    if rendered_sha256 != RENDERED_TEXT_SHA256:
        problems.append("natural rendered text does not match its frozen SHA-256")
    if workload.get("rendered_text_sha256") != RENDERED_TEXT_SHA256:
        problems.append("workload rendered_text_sha256 field is not frozen")

    if index.get("schema") != "opentallas.workload_index.v1":
        problems.append("workload index schema is not opentallas.workload_index.v1")
    if index.get("model_id") != MODEL_ID:
        problems.append("workload index model_id is wrong")
    if index.get("mandatory_context_tokens") != PROMPT_TOKENS:
        problems.append("workload index does not require exactly 200,000 tokens")
    if index.get("tokenizer_sha256") != TOKENIZER_SHA256:
        problems.append("workload index tokenizer identity is wrong")
    source = index.get("source")
    if not isinstance(source, dict) or source != {
        "repository": OFFICIAL_REPOSITORY,
        "revision": OFFICIAL_REVISION,
    }:
        problems.append("workload index does not bind the official model revision")
    entries = index.get("workloads")
    expected_entry = {
        "digest": WORKLOAD_DIGEST,
        "kind": "long_natural",
        "max_new_tokens": MAX_NEW_TOKENS,
        "path": f"{WORKLOAD_ID}.json",
        "prompt_token_count": PROMPT_TOKENS,
    }
    if not isinstance(entries, dict) or entries.get(WORKLOAD_ID) != expected_entry:
        problems.append("workload index entry for the exact 200K target is wrong")

    evidence = {
        "workload_path": _relative(workload_path),
        "workload_source_sha256": workload_source_sha256,
        "workload_digest": _workload_digest(workload),
        "workload_index_path": _relative(index_path),
        "workload_index_source_sha256": index_source_sha256,
        "prompt_token_count": len(token_ids) if isinstance(token_ids, list) else None,
        "prompt_ids_legal": legal_prompt,
        "rendered_text_sha256": rendered_sha256,
    }
    return workload, index, evidence, problems


def _check_file_identity(
    record: object,
    *,
    expected_path: Path,
    expected_sha256: str,
    label: str,
    problems: list[str],
) -> None:
    expected_relative = _relative(expected_path)
    if not isinstance(record, dict):
        problems.append(f"oracle has no {label} identity record")
        return
    if record.get("path") != expected_relative:
        problems.append(f"oracle {label} path is not {expected_relative}")
    if record.get("sha256") != expected_sha256:
        problems.append(f"oracle {label} SHA-256 is not source-current")
    if record.get("size_bytes") != expected_path.stat().st_size:
        problems.append(f"oracle {label} size is not source-current")


def validate_producer(
    report: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    workload_path: Path,
    index_path: Path,
    checkpoint_source_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    producer = report.get("producer")
    if not isinstance(producer, dict):
        producer = {}
        problems.append("oracle report has no producer identity")
    if producer.get("tool") != "tools/run_deepseek_v4_reference_oracle.py":
        problems.append("oracle producer is not the DeepSeek reference runner")

    source_map = producer.get("source_map")
    if not isinstance(source_map, dict):
        source_map = {}
        problems.append("oracle producer has no source map")
    checked_sources: dict[str, str] = {}
    for relative, expected in sorted(source_map.items(), key=lambda item: str(item[0])):
        candidate = Path(relative) if isinstance(relative, str) else Path("")
        source = (REPO / candidate).resolve()
        normalized = (
            isinstance(relative, str)
            and bool(relative)
            and not candidate.is_absolute()
            and candidate.as_posix() == relative
        )
        try:
            source.relative_to(REPO.resolve())
        except ValueError:
            normalized = False
        if not normalized:
            problems.append(f"producer source path is not safe and normalized: {relative!r}")
            continue
        if not _is_sha256(expected):
            problems.append(f"producer source {relative} has an invalid SHA-256")
        elif not source.is_file():
            problems.append(f"producer source {relative} does not exist")
        else:
            observed = _sha256(source)
            checked_sources[relative] = observed
            if observed != expected:
                problems.append(f"producer source {relative} is stale")
    for relative in REQUIRED_PRODUCER_SOURCES:
        if relative not in source_map:
            problems.append(f"producer does not bind required source {relative}")

    source_map_digest = _canonical_digest(source_map)
    if producer.get("source_map_sha256") != source_map_digest:
        problems.append("producer source-map digest is wrong")
    runner_sha256 = source_map.get("tools/run_deepseek_v4_reference_oracle.py")
    if producer.get("tool_source_sha256") != runner_sha256:
        problems.append("producer tool digest does not match its source map")
    if producer.get("source_current_at_completion") is not True:
        problems.append("runner did not prove its sources stayed fixed through completion")
    selected = producer.get("selected_workload_ids")
    if not isinstance(selected, list) or WORKLOAD_ID not in selected:
        problems.append("runner invocation did not select the exact 200K workload")
    argv = producer.get("command_argv")
    if (
        not isinstance(argv, list)
        or not argv
        or argv[0] != "tools/run_deepseek_v4_reference_oracle.py"
        or not all(isinstance(item, str) for item in argv)
    ):
        problems.append("runner command identity is missing or malformed")

    inputs = report.get("input_identity")
    if not isinstance(inputs, dict):
        inputs = {}
        problems.append("oracle report has no immutable input identity")
    _check_file_identity(
        inputs.get("workload_index"),
        expected_path=index_path,
        expected_sha256=WORKLOAD_INDEX_SHA256,
        label="workload index",
        problems=problems,
    )
    _check_file_identity(
        inputs.get("checkpoint_source"),
        expected_path=checkpoint_source_path,
        expected_sha256=CHECKPOINT_SOURCE_SHA256,
        label="checkpoint source",
        problems=problems,
    )

    execution = result.get("execution_identity")
    if not isinstance(execution, dict):
        execution = {}
        problems.append("200K result has no per-result execution identity")
    if execution.get("producer_source_map_sha256") != source_map_digest:
        problems.append("200K result is not bound to this producer source map")
    if execution.get("workload_index_sha256") != WORKLOAD_INDEX_SHA256:
        problems.append("200K result is not bound to the frozen workload index")
    if execution.get("checkpoint_source_sha256") != CHECKPOINT_SOURCE_SHA256:
        problems.append("200K result is not bound to the frozen checkpoint manifest")
    _check_file_identity(
        execution.get("workload_source"),
        expected_path=workload_path,
        expected_sha256=WORKLOAD_SOURCE_SHA256,
        label="200K workload source",
        problems=problems,
    )

    return {
        "tool": producer.get("tool"),
        "source_map_sha256": source_map_digest,
        "recorded_source_count": len(source_map),
        "current_source_count": len(checked_sources),
        "selected_workload_ids": selected,
    }, problems


def _checkpoint_expected_map(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = source.get("expected_files")
    if not isinstance(records, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("path"), str):
            result[record["path"]] = record
    return result


def validate_checkpoint_snapshot(
    source_path: Path,
    snapshot: Path,
    *,
    full_hash: bool,
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    source_sha256 = _sha256(source_path)
    source = _load_object(source_path)
    if source_sha256 != CHECKPOINT_SOURCE_SHA256:
        problems.append("checkpoint source manifest is not the frozen byte sequence")
    if source.get("schema") != "opentallas.checkpoint_source.v1":
        problems.append("checkpoint source schema is wrong")
    if source.get("repository") != OFFICIAL_REPOSITORY:
        problems.append("checkpoint source repository is wrong")
    if source.get("revision") != OFFICIAL_REVISION:
        problems.append("checkpoint source revision is wrong")
    if source.get("remote_code_policy") != "disabled":
        problems.append("checkpoint source does not disable remote code")

    raw_expected = source.get("expected_files")
    expected = _checkpoint_expected_map(source)
    if not isinstance(raw_expected, list) or len(expected) != len(raw_expected):
        problems.append("checkpoint source has duplicate or malformed file records")
    if not snapshot.is_dir():
        problems.append(f"checkpoint snapshot does not exist: {snapshot}")
        return {
            "source_sha256": source_sha256,
            "full_byte_hash_requested": full_hash,
            "full_byte_hash_verified": False,
        }, problems

    index_name = source.get("checkpoint_index")
    index = None
    if not isinstance(index_name, str) or index_name not in expected:
        problems.append("checkpoint index is not declared in expected_files")
    else:
        index_path = snapshot / index_name
        if not index_path.is_file():
            problems.append("checkpoint index is missing from the snapshot")
        else:
            try:
                index = _load_object(index_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                problems.append(f"checkpoint index cannot be parsed: {exc}")

    shard_names: set[str] = set()
    weight_count = 0
    if isinstance(index, dict):
        weight_map = index.get("weight_map")
        if not isinstance(weight_map, dict):
            problems.append("checkpoint index has no weight_map")
        else:
            weight_count = len(weight_map)
            for shard in weight_map.values():
                if not isinstance(shard, str):
                    problems.append("checkpoint index contains a non-string shard path")
                    continue
                shard_names.add(shard)
        metadata = index.get("metadata")
        if not isinstance(metadata, dict) or not _is_int(
            metadata.get("total_size"), minimum=1
        ):
            problems.append("checkpoint index has no valid total payload size")

    required = source.get("required_files")
    required_names = {
        item for item in required if isinstance(item, str)
    } if isinstance(required, list) else set()
    if not isinstance(required, list) or len(required_names) != len(required):
        problems.append("checkpoint required_files contains a non-string path")
    declared = required_names | shard_names
    if isinstance(index_name, str):
        declared.add(index_name)
    if declared != set(expected):
        problems.append("checkpoint index/required-file closure differs from expected_files")

    size_verified = 0
    byte_verified = 0
    total_expected_bytes = 0
    content_addressed_shards = 0
    for relative, record in sorted(expected.items()):
        candidate = Path(relative)
        if candidate.is_absolute() or candidate.as_posix() != relative or ".." in candidate.parts:
            problems.append(f"checkpoint path is not safe and normalized: {relative!r}")
            continue
        size = record.get("size_bytes")
        digest = record.get("sha256")
        if not _is_int(size) or not _is_sha256(digest):
            problems.append(f"checkpoint expectation is malformed: {relative}")
            continue
        total_expected_bytes += size
        path = snapshot / candidate
        if not path.is_file():
            problems.append(f"checkpoint file is missing: {relative}")
            continue
        if path.stat().st_size != size:
            problems.append(f"checkpoint file size differs: {relative}")
            continue
        size_verified += 1
        if relative in shard_names and path.is_symlink() and path.resolve().name == digest:
            content_addressed_shards += 1
        if full_hash:
            if _sha256(path) != digest:
                problems.append(f"checkpoint file SHA-256 differs: {relative}")
            else:
                byte_verified += 1

    full_verified = (
        full_hash
        and not problems
        and byte_verified == len(expected)
        and len(expected) > 0
    )
    evidence = {
        "snapshot": str(snapshot.resolve()),
        "source_path": _relative(source_path),
        "source_sha256": source_sha256,
        "expected_file_count": len(expected),
        "expected_total_file_bytes": total_expected_bytes,
        "size_verified_file_count": size_verified,
        "checkpoint_weight_count": weight_count,
        "checkpoint_shard_count": len(shard_names),
        "content_addressed_shard_link_count": content_addressed_shards,
        "full_byte_hash_requested": full_hash,
        "full_byte_hash_verified_file_count": byte_verified,
        "full_byte_hash_verified": full_verified,
    }
    return evidence, problems


def validate_dependency_separation() -> tuple[dict[str, Any], list[str]]:
    scanned: list[str] = []
    violations: list[dict[str, str]] = []
    for relative in ACCELERATOR_SOURCE_ROOTS:
        root = REPO / relative
        paths = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            name = _relative(path)
            scanned.append(name)
            for forbidden in FORBIDDEN_ORACLE_DEPENDENCIES:
                if forbidden in text:
                    violations.append({"path": name, "dependency": forbidden})
    problems = [
        "accelerator/compiler source depends on the external DeepSeek oracle: "
        f"{row['path']} contains {row['dependency']}"
        for row in violations
    ]
    return {
        "policy": "external_oracle_is_comparator_only_v1",
        "scanned_source_count": len(scanned),
        "forbidden_dependencies": list(FORBIDDEN_ORACLE_DEPENDENCIES),
        "violations": violations,
        "separated": not violations,
    }, problems


def validate_oracle_report(
    report: Mapping[str, Any],
    workload: Mapping[str, Any],
    index: Mapping[str, Any],
    checkpoint_source: Mapping[str, Any],
    *,
    workload_path: Path,
    index_path: Path,
    checkpoint_source_path: Path,
    tokenizer: object | None = None,
) -> tuple[dict[str, Any], list[str]]:
    del index  # Its independently checked identity is consumed through hashes.
    problems: list[str] = []
    if report.get("schema") != ORACLE_SCHEMA:
        problems.append("oracle schema is wrong")
    if report.get("run_status") != "complete":
        problems.append("oracle run is not marked complete")
    if report.get("evidence_class") != "external_reference_comparator":
        problems.append("oracle is not labelled as an external comparator")
    if report.get("model_id") != MODEL_ID:
        problems.append("oracle model_id is wrong")
    if report.get("selection") != SELECTION:
        problems.append("oracle did not use greedy lowest-ID argmax")
    if report.get("tokenizer_sha256") != TOKENIZER_SHA256:
        problems.append("oracle tokenizer identity is wrong")
    if report.get("mandatory_context_tokens") != PROMPT_TOKENS:
        problems.append("oracle does not retain the mandatory 200K target")
    source = report.get("source")
    if not isinstance(source, dict) or source != {
        "repository": OFFICIAL_REPOSITORY,
        "revision": OFFICIAL_REVISION,
    }:
        problems.append("oracle does not bind the official model revision")
    not_a_claim = report.get("not_a_claim")
    required_disclaimers = {
        "accelerator_execution",
        "artifact_only_execution",
        "timing_or_performance",
    }
    if (
        not isinstance(not_a_claim, list)
        or not all(isinstance(item, str) for item in not_a_claim)
        or not required_disclaimers <= set(not_a_claim)
    ):
        problems.append("oracle does not preserve the external-comparator claim boundary")

    results = report.get("results")
    result = results.get(WORKLOAD_ID) if isinstance(results, dict) else None
    if not isinstance(result, dict):
        problems.append("oracle has no executed exact-200K result")
        result = {}
    if result.get("kind") != "long_natural":
        problems.append("oracle 200K result is not the natural workload")
    if result.get("workload_digest") != WORKLOAD_DIGEST:
        problems.append("oracle 200K result used the wrong workload digest")
    if result.get("prompt_token_count") != PROMPT_TOKENS:
        problems.append("oracle did not execute exactly 200,000 prompt tokens")

    generated = result.get("generated_token_ids")
    legal_generated = (
        isinstance(generated, list)
        and bool(generated)
        and all(_is_int(token) and token < VOCABULARY_SIZE for token in generated)
    )
    if not legal_generated:
        problems.append("oracle generated IDs are absent or outside the vocabulary")
        generated = []
    if result.get("generated_token_count") != len(generated):
        problems.append("oracle generated-token count disagrees with its ID list")
    if len(generated) > MAX_NEW_TOKENS:
        problems.append("oracle generated more than the exact 256-token cap")

    eos_positions = [index for index, token in enumerate(generated) if token == EOS_TOKEN_ID]
    terminal_rule = "invalid"
    if eos_positions:
        first_eos_is_terminal = eos_positions[0] == len(generated) - 1
        eos_reason = result.get("stop_reason") == "eos"
        if not first_eos_is_terminal:
            problems.append("oracle continued after the first official EOS")
        if not eos_reason:
            problems.append("oracle emitted EOS without the eos stop reason")
        if first_eos_is_terminal and eos_reason:
            terminal_rule = "first_official_eos_included"
    else:
        exact_cap = len(generated) == MAX_NEW_TOKENS
        cap_reason = result.get("stop_reason") == "max_new_tokens"
        if not exact_cap:
            problems.append("oracle stopped without EOS before exactly 256 tokens")
        if not cap_reason:
            problems.append("oracle cap termination has the wrong stop reason")
        if exact_cap and cap_reason:
            terminal_rule = "exact_256_without_eos"

    if result.get("vendor_sample_agreements") != len(generated):
        problems.append("vendor temperature-zero selection did not agree at every step")
    if result.get("vendor_sample_disagreements") != []:
        problems.append("oracle records a vendor selection disagreement")
    if not isinstance(result.get("raw_decoded_text"), str):
        problems.append("oracle has no raw decoded text")
    if not isinstance(result.get("visible_decoded_text"), str):
        problems.append("oracle has no visible decoded text")
    if not _is_int(result.get("max_seq_len"), minimum=PROMPT_TOKENS + MAX_NEW_TOKENS):
        problems.append("oracle KV allocation did not cover prompt plus the full cap")
    if result.get("prefill_tiled") is not True:
        problems.append("exact-200K prefill did not use the qualified tiled path")
    if result.get("tile_geometry") != QUALIFIED_TILE_GEOMETRY:
        problems.append("exact-200K prefill did not use the qualified tile geometry")
    for name in ("prefill_seconds", "wall_seconds", "peak_device_bytes"):
        value = result.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            problems.append(f"oracle has no positive {name} observation")

    tiling = report.get("prefill_tiling")
    if not isinstance(tiling, dict) or tiling.get("enabled") is not True:
        problems.append("oracle report does not identify the tiled prefill as enabled")
    elif (
        tiling.get("sequence_tile") != QUALIFIED_TILE_GEOMETRY["sequence_tile"]
        or tiling.get("index_tile_rows_fixed")
        != QUALIFIED_TILE_GEOMETRY["indexer_sub_tile"]
        or tiling.get("compressor_positions_per_tile")
        != QUALIFIED_TILE_GEOMETRY["compressor_positions_per_tile"]
        or tiling.get("expert_rows_per_tile")
        != QUALIFIED_TILE_GEOMETRY["expert_rows_per_tile"]
        or tiling.get("hyper_connection_residual_on_host") is not True
    ):
        problems.append("oracle report's tiled-prefill configuration is not qualified")

    adaptation_rows = report.get("adaptations")
    adaptation_ids = {
        row.get("id")
        for row in adaptation_rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    } if isinstance(adaptation_rows, list) else set()
    if not REQUIRED_ADAPTATIONS <= adaptation_ids:
        problems.append("oracle report omits a required execution adaptation")

    head_split = report.get("head_split_verification")
    if (
        not isinstance(head_split, dict)
        or head_split.get("bitwise_identical") is not True
        or head_split.get("max_abs_difference") != 0
        or head_split.get("heads_per_launch") != 16
    ):
        problems.append("sparse-attention head split is not bitwise qualified")
    fp4 = report.get("fp4_gemm_verification")
    if (
        not isinstance(fp4, dict)
        or fp4.get("fp8_gemm_agrees") is not True
        or fp4.get("fp4_gemm_agrees") is not False
        or not isinstance(fp4.get("fp4_path_max_abs_error"), (int, float))
        or not isinstance(fp4.get("tolerance"), (int, float))
        or fp4.get("fp4_path_max_abs_error", 0) <= fp4.get("tolerance", 0)
        or report.get("expert_numeric_path") != "fp8"
        or result.get("expert_numeric_path") != "fp8"
    ):
        problems.append("routed-expert FP8 fallback is not numerically qualified")

    environment = report.get("environment")
    if not isinstance(environment, dict):
        problems.append("oracle has no execution environment record")
    else:
        if environment.get("package_versions") != QUALIFIED_PACKAGE_VERSIONS:
            problems.append("oracle package versions differ from the qualified stack")
        if environment.get("torch_cuda") != "12.8":
            problems.append("oracle CUDA runtime is not the qualified 12.8 stack")
        if environment.get("compute_capability") != [12, 0]:
            problems.append("oracle GPU compute capability is not the qualified sm_120")
        if environment.get("tf32_allowed") is not False:
            problems.append("oracle allowed TF32 in a float32 arithmetic path")
        if environment.get("fast_hadamard_transform") != "fast_hadamard_transform":
            problems.append("oracle did not use the qualified Hadamard extension")

    expected_vendor = {
        relative: record.get("sha256")
        for relative, record in _checkpoint_expected_map(checkpoint_source).items()
        if relative in REQUIRED_VENDOR_SOURCES
    }
    vendor_sources = report.get("vendor_source_sha256")
    if vendor_sources != expected_vendor:
        problems.append("oracle vendor-source map is incomplete or wrong")
    execution = result.get("execution_identity")
    if not isinstance(execution, dict) or execution.get("vendor_source_sha256") != expected_vendor:
        problems.append("200K result is not bound to the vendor-source map")

    decoded_exact = None
    prompt_reencoded_exact = None
    if tokenizer is not None and legal_generated:
        raw = tokenizer.decode(generated)
        visible = tokenizer.decode(generated, skip_special_tokens=True)
        decoded_exact = (
            raw == result.get("raw_decoded_text")
            and visible == result.get("visible_decoded_text")
        )
        if not decoded_exact:
            problems.append("recorded decoded text does not match the generated IDs")
        rendered_text = workload.get("rendered_text")
        prompt_ids = workload.get("token_ids")
        if isinstance(rendered_text, str) and isinstance(prompt_ids, list):
            prompt_reencoded_exact = tokenizer.encode(rendered_text) == prompt_ids
        if prompt_reencoded_exact is not True:
            problems.append("official tokenizer does not reproduce the 200K prompt IDs")

    producer_evidence, producer_problems = validate_producer(
        report,
        result,
        workload_path=workload_path,
        index_path=index_path,
        checkpoint_source_path=checkpoint_source_path,
    )
    problems.extend(producer_problems)
    evidence = {
        "workload_id": WORKLOAD_ID,
        "prompt_token_count": result.get("prompt_token_count"),
        "generated_token_count": len(generated),
        "generated_ids_legal": legal_generated,
        "terminal_rule": terminal_rule,
        "first_eos_position": eos_positions[0] if eos_positions else None,
        "vendor_selection_agreement_count": result.get("vendor_sample_agreements"),
        "decoded_text_exact": decoded_exact,
        "prompt_reencoded_exact": prompt_reencoded_exact,
        "raw_decoded_text": result.get("raw_decoded_text"),
        "visible_decoded_text": result.get("visible_decoded_text"),
        "producer": producer_evidence,
    }
    return evidence, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--workload-index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument(
        "--checkpoint-source", type=Path, default=DEFAULT_CHECKPOINT_SOURCE
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help=(
            "stat the checkpoint closure without hashing its 166.9 GB of files; "
            "this is preflight only and can never produce acceptance"
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    problems: list[str] = []
    try:
        workload, index, workload_evidence, input_problems = validate_workload_inputs(
            args.workload, args.workload_index
        )
        problems.extend(input_problems)
        checkpoint_source = _load_object(args.checkpoint_source)
        report = _load_object(args.oracle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "accepted": False, "problems": [str(exc)]}))
        return 1

    tokenizer = None
    tokenizer_evidence: dict[str, Any] = {"verified": False}
    try:
        tokenizer = load_verified_deepseek_v4_tokenizer(
            args.snapshot, args.checkpoint_source
        )
        tokenizer_evidence = {
            "verified": True,
            "validation": tokenizer.validation_report,
        }
    except Exception as exc:  # fail closed at the external package boundary
        problems.append(f"official tokenizer verification failed: {type(exc).__name__}: {exc}")
        tokenizer_evidence = {
            "verified": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    oracle_evidence, oracle_problems = validate_oracle_report(
        report,
        workload,
        index,
        checkpoint_source,
        workload_path=args.workload,
        index_path=args.workload_index,
        checkpoint_source_path=args.checkpoint_source,
        tokenizer=tokenizer,
    )
    problems.extend(oracle_problems)
    separation_evidence, separation_problems = validate_dependency_separation()
    problems.extend(separation_problems)

    checkpoint_evidence, checkpoint_problems = validate_checkpoint_snapshot(
        args.checkpoint_source,
        args.snapshot,
        full_hash=False,
    )
    problems.extend(checkpoint_problems)
    if not args.manifest_only and not problems:
        checkpoint_evidence, checkpoint_problems = validate_checkpoint_snapshot(
            args.checkpoint_source,
            args.snapshot,
            full_hash=True,
        )
        problems.extend(checkpoint_problems)
    elif args.manifest_only:
        problems.append(
            "manifest-only preflight does not verify every checkpoint byte"
        )

    accepted = not problems and checkpoint_evidence.get("full_byte_hash_verified") is True
    result = {
        "schema": SCHEMA,
        "accepted": accepted,
        "status": "accepted" if accepted else "rejected",
        "oracle_path": _relative(args.oracle),
        "workload": workload_evidence,
        "tokenizer": tokenizer_evidence,
        "oracle": oracle_evidence,
        "checkpoint": checkpoint_evidence,
        "dependency_separation": separation_evidence,
        "problems": problems,
    }
    encoded = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded)
    print(encoded.decode("ascii"))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
