#!/usr/bin/env python3
"""Fail-closed ABI 3.0 gate for the exact DeepSeek 200K comparison.

This tool does not execute the model.  It consumes two future execution
records produced by ``run_accelerator_tokens.py``: one wafer-logical ROM run
and one run on exactly 32 identical HBM/SRAM nodes.  Acceptance requires the
strict external-oracle Gate B to be accepted first, then independently checks
the serialized deployments, the complete token transactions, decoded text,
numeric-association evidence, topology and counters.

The required execution profile is intentionally simple.  Mutable KV and
compressor data are ordinary ABI 3.0 read/write buffers.  ABI ``STATE``
descriptors, instructions, storage and permissions are forbidden; a simulator
fault stops the run rather than invoking a persistence or retry protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    ABI_MAJOR,
    ABI_MINOR,
    Major,
    Permission,
    StorageClass,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import VerificationReport, verify_deployment  # noqa: E402

SCHEMA = "opentallas.abi3.deepseek_v4_200k_accelerator_acceptance.v1"
RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
GATE_B_SCHEMA = "opentallas.abi3.deepseek_v4_200k_oracle_acceptance.v1"
ASSOCIATION_SCHEMA = "opentallas.abi3.executed_association.v1"
ASSOCIATION_POLICY = "implementation_and_executed_shape_pinned"
PAIR_POLICY = "same_implementation_shape_and_32_node_normalisation_v1"
MODEL_ID = "deepseek-v4-flash-0731"
WORKLOAD_ID = "TA-DS-CTX-200K-1"
PROMPT_TOKENS = 200_000
MAX_NEW_TOKENS = 256
VOCABULARY_SIZE = 129_280
EOS_TOKEN_ID = 1
TOKENIZERS_VERSION = "0.22.2"
NUMERIC_PROFILE = "deepseek_v4_flash_target_precision_v1"
BLOCKED_CONTRACT = "bf16_bf16_fp32_blocked_rne_v1"
NO_ID = 0xFFFF_FFFF
ABI_STATE_PERMISSIONS = int(Permission.STATE_PREPARE | Permission.STATE_COMMIT)

WORKLOAD_DIGEST = "803f0c3a3e9bf7ef68ddff00947576d2fab5703d1f4387df1eb2ec11be2c59bd"
TOKENIZER_SHA256 = "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
RENDERED_TEXT_SHA256 = (
    "6ad57114c426156f7e25341d6faa55d061033e6b98244d31ab1e8a395463527a"
)
WORKLOAD_SOURCE_SHA256 = (
    "b00dd2f461329c14e0a8c0863dbef78e066950bee0aba053aa651f91890418bb"
)
WORKLOAD_INDEX_SHA256 = (
    "45f478d457d0e617d1ef06e6f5a5b542bc567bd911be28072fa10ec6c625d310"
)
KERNEL_IR_SHA256 = "e101b3e7a63e73f7dd66b3d6c15c40d0b7b6eba7cdc387ddc5cd9623c0e0ccf1"
COMPARISON_CONTRACT_SHA256 = (
    "badcd1ed86531fc7f02ac354765a2a0b9f2cd2fa7d679be990397e0c1f6c6efb"
)
CHECKPOINT_SOURCE_SHA256 = (
    "c9cf820d5183a4de2fdd51769535b48d6a47975a6d707f5d1b2f105af64141c5"
)
CHECKPOINT_FILE_COUNT = 74
CHECKPOINT_TOTAL_BYTES = 166_898_661_074
GRAPH_ID = "9ef6c3248d23c181c774fd43c09b0de2a19c8e23f344cb9a25c43040268337d9"

KERNEL_IR = REPO / "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"
WORKLOAD = REPO / "build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-200K-1.json"
WORKLOAD_INDEX = REPO / "build/workloads/deepseek-v4-flash-0731/index.json"
ORACLE = REPO / "results/abi3/deepseek_v4_reference_oracle_context_ladder.json"
DEFAULT_GATE_B = REPO / "results/abi3/deepseek_v4_200k_oracle_acceptance_preflight.json"
COMPARISON_CONTRACT = (
    REPO / "configs/abi3/comparison_contracts/"
    "deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json"
)

CAPABILITIES = {
    "rom_deepseek_v4": REPO / "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    "hbm_sram": REPO / "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
}
CAPABILITY_SHA256 = {
    "rom_deepseek_v4": (
        "5abf26b4ef235d6083c6f6dbe48d7021068c59ecb451238569a2f660303d26b6"
    ),
    "hbm_sram": ("1eb2e92dac1d9fb8937b7724953d2f65993bd56e342e9058569442eb61d74bad"),
}
TARGET_IDS = {
    "rom_deepseek_v4": "deepseek-v4-flash-rom-wafer",
    "hbm_sram": "hbm-sram-abi3-cluster_32",
}
TARGET_BACKENDS = {
    "rom_deepseek_v4": "rom.wafer_logical_device",
    "hbm_sram": "hbm-sram-abi3",
}
TOPOLOGY_CLASS = {"rom_deepseek_v4": 2, "hbm_sram": 1}
NODE_COUNT = {"rom_deepseek_v4": 1, "hbm_sram": 32}

# A producer may record more source files, and every recorded path is checked.
# This independent minimum prevents omission from hiding a changed compiler or
# simulator implementation.
COMMON_SOURCES = (
    "tools/run_accelerator_tokens.py",
    "compiler/backends/numeric_contracts.py",
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "compiler/ir/v3/numeric.py",
    "runtime/abi3/builder.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/driver.py",
    "runtime/evidence.py",
    "runtime/reference/compression_pool.py",
    "runtime/reference/formats.py",
    "runtime/reference/hadamard.py",
    "runtime/reference/hyper_connection.py",
    "runtime/reference/normalization.py",
    "runtime/reference/quantization.py",
    "runtime/reference/sparse_attention.py",
    "runtime/reference/sqrt_softplus.py",
    "runtime/reference/swiglu.py",
    "runtime/reference/transcendental.py",
    "runtime/sim/backend.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
    "runtime/sim/performance.py",
    "runtime/sim/weight_cache.py",
    "runtime/tensor_accelerator/attention.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/tensor_accelerator/rmsnorm.py",
    "runtime/tensor_accelerator/rope.py",
    "runtime/tensor_accelerator/sparse_attention.py",
)
BACKEND_SOURCES = {
    "hbm_sram": (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    "rom_deepseek_v4": (
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
}

# These are logical model-work counters observed identically by the ROM logical
# node and every HBM/SRAM node.  Placement, routed-expert sharding, storage,
# link and instruction-schedule counters are deliberately not equated.
PAIR_LOGICAL_COUNTERS = (
    "attention.context_positions",
    "attention.heads",
    "attention.kv_bytes_read",
    "attention.score_multiplications",
    "attention.sparse_indices",
    "attention.value_multiplications",
    "dma.gather_elements",
    "dma.scatter_elements",
    "engine.attention.descriptors",
    "engine.selection.descriptors",
    "engine.tensor.descriptors",
    "engine.vector.descriptors",
    "reduction.elements",
    "reduction.ordered_sums",
    "route.dispatched_bytes",
    "route.selected_experts",
    "route.topk_candidates",
    "selection.tie_multiplicity",
    "selection.tokens_appended",
    "selection.tokens_selected",
    "selection.vocabulary_elements",
    "tensor.embedding_rows",
    "vector.activation_elements",
    "vector.compress_rows",
    "vector.conversions",
    "vector.elements",
    "vector.mhc_sites",
    "vector.norm_rows",
    "vector.rope_pairs",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError(f"{path} is not a JSON object")
    return body


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _resolved_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO / path).resolve()


def _integer(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _expected_sources(backend: str) -> set[str]:
    engines = {
        path.relative_to(REPO).as_posix()
        for path in (REPO / "runtime/sim/engines").glob("*.py")
    }
    return set(COMMON_SOURCES) | set(BACKEND_SOURCES[backend]) | engines


def _check_source_lock(record: Mapping[str, Any], backend: str) -> list[str]:
    source_map = record.get("source_sha256")
    if not isinstance(source_map, dict) or not source_map:
        return ["source_sha256 is missing or empty"]
    problems: list[str] = []
    for relative, expected in sorted(source_map.items(), key=lambda item: str(item[0])):
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or Path(relative).as_posix() != relative
        ):
            problems.append(
                f"source path is not normalized repository-relative: {relative!r}"
            )
            continue
        path = (REPO / relative).resolve()
        try:
            path.relative_to(REPO.resolve())
        except ValueError:
            problems.append(f"source path escapes repository: {relative}")
            continue
        if not path.is_file():
            problems.append(f"source file is missing: {relative}")
        elif expected != _sha256(path):
            problems.append(f"source is not current: {relative}")
    for relative in sorted(_expected_sources(backend) - set(source_map)):
        problems.append(f"record does not bind required source {relative}")
    return problems


def _check_file_identity(
    identity: object, expected_path: Path, label: str
) -> list[str]:
    if not isinstance(identity, dict):
        return [f"inputs.{label} is not an object"]
    problems: list[str] = []
    if _resolved_path(identity.get("path")) != expected_path.resolve():
        problems.append(f"inputs.{label}.path does not name {_relative(expected_path)}")
    if identity.get("sha256") != _sha256(expected_path):
        problems.append(f"inputs.{label}.sha256 is not source-current")
    if identity.get("bytes") != expected_path.stat().st_size:
        problems.append(f"inputs.{label}.bytes is not source-current")
    return problems


def _workload_digest(workload: Mapping[str, Any]) -> str:
    return _canonical_digest(
        {
            "workload_id": workload.get("workload_id"),
            "kind": workload.get("kind"),
            "token_ids": workload.get("token_ids"),
            "max_new_tokens": workload.get("max_new_tokens"),
        }
    )


def _frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], list[int], list[str]]:
    problems: list[str] = []
    fixed_hashes = (
        (WORKLOAD, WORKLOAD_SOURCE_SHA256, "workload"),
        (WORKLOAD_INDEX, WORKLOAD_INDEX_SHA256, "workload index"),
        (KERNEL_IR, KERNEL_IR_SHA256, "Kernel IR"),
        (
            COMPARISON_CONTRACT,
            COMPARISON_CONTRACT_SHA256,
            "comparison contract",
        ),
        *(
            (CAPABILITIES[backend], expected, f"{backend} capability")
            for backend, expected in CAPABILITY_SHA256.items()
        ),
    )
    for path, expected, label in fixed_hashes:
        if not path.is_file():
            problems.append(f"frozen {label} is absent: {_relative(path)}")
        elif _sha256(path) != expected:
            problems.append(f"frozen {label} byte identity differs from the contract")

    workload = _load(WORKLOAD)
    index = _load(WORKLOAD_INDEX)
    prompt = workload.get("token_ids")
    legal_prompt = (
        isinstance(prompt, list)
        and len(prompt) == PROMPT_TOKENS
        and all(_integer(token) and token < VOCABULARY_SIZE for token in prompt)
    )
    if not legal_prompt:
        prompt = []
        problems.append("frozen workload is not exactly 200,000 legal token IDs")
    if EOS_TOKEN_ID in prompt:
        problems.append("frozen natural prompt contains the official EOS token")
    expected_workload = {
        "workload_id": WORKLOAD_ID,
        "kind": "long_natural",
        "prompt_token_count": PROMPT_TOKENS,
        "max_new_tokens": MAX_NEW_TOKENS,
        "digest": WORKLOAD_DIGEST,
        "rendered_text_sha256": RENDERED_TEXT_SHA256,
    }
    for name, expected in expected_workload.items():
        if workload.get(name) != expected:
            problems.append(f"frozen workload {name} differs from the contract")
    metadata = workload.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("mandatory_contract") is not True:
        problems.append("frozen workload is not marked mandatory")
    if _workload_digest(workload) != WORKLOAD_DIGEST:
        problems.append("frozen workload logical digest cannot be rederived")
    rendered = workload.get("rendered_text")
    if not isinstance(rendered, str) or _text_sha256(rendered) != RENDERED_TEXT_SHA256:
        problems.append("frozen rendered natural context differs from the contract")

    expected_index_entry = {
        "digest": WORKLOAD_DIGEST,
        "kind": "long_natural",
        "max_new_tokens": MAX_NEW_TOKENS,
        "path": f"{WORKLOAD_ID}.json",
        "prompt_token_count": PROMPT_TOKENS,
    }
    entries = index.get("workloads")
    if (
        index.get("schema") != "opentallas.workload_index.v1"
        or index.get("model_id") != MODEL_ID
        or index.get("mandatory_context_tokens") != PROMPT_TOKENS
        or index.get("tokenizer_sha256") != TOKENIZER_SHA256
        or not isinstance(entries, dict)
        or entries.get(WORKLOAD_ID) != expected_index_entry
    ):
        problems.append("frozen workload index differs from the exact-200K contract")

    graph = _load(KERNEL_IR)
    if (
        graph.get("model_id") != MODEL_ID
        or graph.get("graph_id") != GRAPH_ID
        or graph.get("numeric_profile") != NUMERIC_PROFILE
    ):
        problems.append("frozen Kernel IR identity differs from the DeepSeek graph")

    comparison = _load(COMPARISON_CONTRACT)
    execution = comparison.get("execution")
    targets = comparison.get("targets")
    rom_target = targets.get("rom") if isinstance(targets, dict) else None
    hbm_target = targets.get("hbm") if isinstance(targets, dict) else None
    if (
        comparison.get("schema") != "opentallas.abi3.comparison_contract.v1"
        or comparison.get("comparison_id") != "deepseek_v4_rom_wafer_vs_hbm_cluster_32"
        or not isinstance(execution, dict)
        or execution.get("context_tokens") != PROMPT_TOKENS
        or execution.get("evidence_scope") != "full_workload"
        or not isinstance(rom_target, dict)
        or rom_target.get("target_id") != TARGET_IDS["rom_deepseek_v4"]
        or rom_target.get("node_count") != NODE_COUNT["rom_deepseek_v4"]
        or rom_target.get("topology_class") != TOPOLOGY_CLASS["rom_deepseek_v4"]
        or not isinstance(hbm_target, dict)
        or hbm_target.get("target_id") != TARGET_IDS["hbm_sram"]
        or hbm_target.get("node_count") != NODE_COUNT["hbm_sram"]
        or hbm_target.get("topology_class") != TOPOLOGY_CLASS["hbm_sram"]
    ):
        problems.append("frozen ROM-versus-HBM comparison contract is inconsistent")
    for backend, capability_path in CAPABILITIES.items():
        capability = Capability.from_dict(_load(capability_path))
        if (
            capability.topology_class != TOPOLOGY_CLASS[backend]
            or capability.limits.get("max_nodes") != NODE_COUNT[backend]
            or capability.limits.get("max_context_positions", 0)
            < PROMPT_TOKENS + MAX_NEW_TOKENS
            or capability.limits.get("max_vocabulary", 0) < VOCABULARY_SIZE
        ):
            problems.append(f"{backend} capability cannot hold the governed workload")
    return workload, graph, list(prompt), problems


def _terminal_kind(
    generated: Sequence[int], stop_reason: object
) -> tuple[str | None, list[str]]:
    problems: list[str] = []
    eos_positions = [
        index for index, token in enumerate(generated) if token == EOS_TOKEN_ID
    ]
    if eos_positions:
        if eos_positions[0] != len(generated) - 1:
            problems.append("token sequence continues after the first official EOS")
        if stop_reason != "eos":
            problems.append("EOS sequence does not carry the eos stop reason")
        if not problems:
            return "eos", []
    else:
        if len(generated) != MAX_NEW_TOKENS:
            problems.append("non-EOS sequence is not exactly the 256-token cap")
        if stop_reason != "max_new_tokens":
            problems.append("capped sequence has the wrong stop reason")
        if not problems:
            return "cap", []
    return None, problems


def _check_gate_b(
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[int], list[str]]:
    gate = _load(path)
    problems: list[str] = []
    if (
        gate.get("schema") != GATE_B_SCHEMA
        or gate.get("accepted") is not True
        or gate.get("status") != "accepted"
        or gate.get("problems") != []
    ):
        problems.append("strict DeepSeek exact-200K oracle Gate B is not accepted")

    work = gate.get("workload")
    expected_work = {
        "workload_path": _relative(WORKLOAD),
        "workload_source_sha256": WORKLOAD_SOURCE_SHA256,
        "workload_digest": WORKLOAD_DIGEST,
        "workload_index_path": _relative(WORKLOAD_INDEX),
        "workload_index_source_sha256": WORKLOAD_INDEX_SHA256,
        "prompt_token_count": PROMPT_TOKENS,
        "prompt_ids_legal": True,
        "rendered_text_sha256": RENDERED_TEXT_SHA256,
    }
    if work != expected_work:
        problems.append("Gate B workload evidence is not the frozen exact-200K input")

    checkpoint = gate.get("checkpoint")
    if not isinstance(checkpoint, dict):
        problems.append("Gate B checkpoint evidence is absent")
    elif (
        checkpoint.get("full_byte_hash_requested") is not True
        or checkpoint.get("full_byte_hash_verified") is not True
        or checkpoint.get("full_byte_hash_verified_file_count")
        != checkpoint.get("expected_file_count")
        or checkpoint.get("expected_file_count") != CHECKPOINT_FILE_COUNT
        or checkpoint.get("expected_total_file_bytes") != CHECKPOINT_TOTAL_BYTES
        or checkpoint.get("source_sha256") != CHECKPOINT_SOURCE_SHA256
    ):
        problems.append("Gate B did not verify every pinned checkpoint byte")

    separation = gate.get("dependency_separation")
    if (
        not isinstance(separation, dict)
        or separation.get("separated") is not True
        or separation.get("problems", []) != []
    ):
        problems.append(
            "Gate B does not prove oracle/accelerator dependency separation"
        )

    if _resolved_path(gate.get("oracle_path")) != ORACLE.resolve():
        problems.append("Gate B does not name the governed external oracle")
    oracle = _load(ORACLE)
    result = (
        oracle.get("results", {}).get(WORKLOAD_ID)
        if isinstance(oracle.get("results"), dict)
        else None
    )
    if not isinstance(result, dict):
        result = {}
        problems.append("governed external oracle has no exact-200K result")
    if (
        oracle.get("schema") != "opentallas.abi3.reference_oracle.v1"
        or oracle.get("run_status") != "complete"
        or oracle.get("evidence_class") != "external_reference_comparator"
        or oracle.get("model_id") != MODEL_ID
        or oracle.get("tokenizer_sha256") != TOKENIZER_SHA256
        or oracle.get("mandatory_context_tokens") != PROMPT_TOKENS
        or result.get("workload_digest") != WORKLOAD_DIGEST
        or result.get("prompt_token_count") != PROMPT_TOKENS
        or result.get("max_new_tokens") != MAX_NEW_TOKENS
        or result.get("expert_numeric_path") != "fp8"
    ):
        problems.append("external oracle identity is not the completed Gate-B run")
    snapshot_path = _resolved_path(oracle.get("snapshot"))
    if (
        not isinstance(checkpoint, dict)
        or _resolved_path(checkpoint.get("snapshot")) != snapshot_path
    ):
        problems.append("Gate B checkpoint snapshot differs from its external oracle")
    preflight = oracle.get("production_checkpoint_preflight")
    if (
        not isinstance(preflight, dict)
        or preflight.get("completed_before_workload_execution") is not True
        or preflight.get("full_byte_hash_verified") is not True
        or preflight.get("full_byte_hash_verified_file_count")
        != preflight.get("expected_file_count")
    ):
        problems.append("external oracle lacks its full checkpoint-byte preflight")
    launch = oracle.get("production_launch")
    contract = launch.get("contract") if isinstance(launch, dict) else None
    if (
        not isinstance(launch, dict)
        or launch.get("explicitly_requested") is not True
        or not isinstance(contract, dict)
        or contract.get("workload_id") != WORKLOAD_ID
        or contract.get("prompt_token_count") != PROMPT_TOKENS
        or contract.get("max_new_tokens") != MAX_NEW_TOKENS
        or contract.get("selection") != "greedy_lowest_token_id_argmax"
    ):
        problems.append("external oracle lacks the qualified Gate-B launch contract")

    generated = result.get("generated_token_ids")
    if not (
        isinstance(generated, list)
        and generated
        and all(_integer(token) and token < VOCABULARY_SIZE for token in generated)
    ):
        generated = []
        problems.append("external oracle generated IDs are absent or illegitimate")
    if result.get("generated_token_count") != len(generated):
        problems.append("external oracle generated-token count is inconsistent")
    terminal, terminal_problems = _terminal_kind(generated, result.get("stop_reason"))
    problems.extend(f"external oracle: {problem}" for problem in terminal_problems)

    evidence = gate.get("oracle")
    expected_terminal = (
        "first_official_eos_included" if terminal == "eos" else "exact_256_without_eos"
    )
    if (
        not isinstance(evidence, dict)
        or evidence.get("workload_id") != WORKLOAD_ID
        or evidence.get("prompt_token_count") != PROMPT_TOKENS
        or evidence.get("generated_token_count") != len(generated)
        or evidence.get("generated_ids_legal") is not True
        or evidence.get("terminal_rule") != expected_terminal
        or evidence.get("first_eos_position")
        != (len(generated) - 1 if terminal == "eos" else None)
        or evidence.get("vendor_selection_agreement_count") != len(generated)
        or evidence.get("decoded_text_exact") is not True
        or evidence.get("prompt_reencoded_exact") is not True
        or evidence.get("raw_decoded_text") != result.get("raw_decoded_text")
        or evidence.get("visible_decoded_text") != result.get("visible_decoded_text")
    ):
        problems.append("Gate B token/text evidence differs from its external oracle")
    return oracle, result, list(generated), problems


def _check_inputs(
    record: Mapping[str, Any],
    backend: str,
    prompt_digest: str,
    oracle_path: Path,
    snapshot_path: Path | None,
) -> list[str]:
    inputs = record.get("inputs")
    if not isinstance(inputs, dict):
        return ["inputs is not an object"]
    problems: list[str] = []
    problems += _check_file_identity(inputs.get("kernel_ir"), KERNEL_IR, "kernel_ir")
    problems += _check_file_identity(
        inputs.get("capability"), CAPABILITIES[backend], "capability"
    )
    problems += _check_file_identity(inputs.get("workload"), WORKLOAD, "workload")
    problems += _check_file_identity(inputs.get("reference"), oracle_path, "reference")
    work = inputs.get("workload")
    if isinstance(work, dict) and (
        work.get("declared_workload_digest") != WORKLOAD_DIGEST
        or work.get("prompt_token_ids_sha256") != prompt_digest
        or work.get("tokenizer_sha256") != TOKENIZER_SHA256
    ):
        problems.append("inputs.workload extended identity is not frozen")

    checkpoint = inputs.get("checkpoint_root")
    target = record.get("target") if isinstance(record.get("target"), dict) else {}
    if not isinstance(checkpoint, dict):
        problems.append("inputs.checkpoint_root is not an object")
    else:
        root = _resolved_path(checkpoint.get("path"))
        if checkpoint.get("kind") != "directory" or root is None or not root.is_dir():
            problems.append("checkpoint root is not an available directory")
        if snapshot_path is not None and root != snapshot_path:
            problems.append("checkpoint root differs from the accepted oracle snapshot")
        if (
            checkpoint.get("content_binding")
            != "authenticated deployment object segment SHA-256 values"
        ):
            problems.append("checkpoint root lacks the authenticated object binding")
        if checkpoint.get("deployment_digest_binding") != target.get(
            "deployment_digest"
        ):
            problems.append("checkpoint deployment binding differs from target")

    published = inputs.get("published_deployment")
    if not isinstance(published, dict):
        problems.append("inputs.published_deployment is required")
    else:
        root = _resolved_path(published.get("path"))
        if root is None:
            problems.append("published deployment has no path")
        else:
            for name, filename in (
                ("manifest", "deployment.json"),
                ("descriptors", "descriptors.bin"),
                ("program", "program.bin"),
            ):
                artifact = root / filename
                if not artifact.is_file():
                    problems.append(f"published deployment is missing {filename}")
                else:
                    problems += _check_file_identity(
                        published.get(name),
                        artifact,
                        f"published_deployment.{name}",
                    )
    return problems


def _check_published_deployment(
    record: Mapping[str, Any],
    backend: str,
    capability: Capability,
) -> tuple[Deployment | None, VerificationReport | None, list[str]]:
    inputs = record.get("inputs")
    published = inputs.get("published_deployment") if isinstance(inputs, dict) else None
    root = (
        _resolved_path(published.get("path")) if isinstance(published, dict) else None
    )
    if root is None:
        return None, None, ["serialized deployment cannot be reopened"]

    problems: list[str] = []
    try:
        manifest = _load(root / "deployment.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return (
            None,
            None,
            [
                "serialized deployment manifest cannot be decoded: "
                f"{type(exc).__name__}: {exc}"
            ],
        )
    if manifest.get("schema") != "opentallas.abi3.deployment.v1" or manifest.get(
        "abi"
    ) != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        problems.append("serialized deployment is not ABI 3.0")
    try:
        deployment = Deployment.read(root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return (
            None,
            None,
            problems
            + [
                "serialized deployment failed authenticated readback: "
                f"{type(exc).__name__}: {exc}"
            ],
        )

    target = record.get("target") if isinstance(record.get("target"), dict) else {}
    source = (
        deployment.source_identity
        if isinstance(deployment.source_identity, Mapping)
        else {}
    )
    identity_checks = {
        "digest": deployment.deployment_digest.hex() == target.get("deployment_digest"),
        "target id": deployment.target_id == TARGET_IDS[backend],
        "backend": deployment.backend == TARGET_BACKENDS[backend],
        "model id": deployment.model_id == MODEL_ID,
        "capability digest": deployment.capability_digest == capability.digest,
        "topology class": deployment.topology_class == TOPOLOGY_CLASS[backend],
        "graph id": source.get("graph_id") == GRAPH_ID,
    }
    for name, passed in identity_checks.items():
        if not passed:
            problems.append(f"serialized deployment {name} differs from the record")

    try:
        header, body = split_program(deployment.program)
        instructions = decode_body(body)
    except (ValueError, KeyError, TypeError) as exc:
        return (
            deployment,
            None,
            problems
            + [
                "serialized deployment program cannot be decoded: "
                f"{type(exc).__name__}: {exc}"
            ],
        )
    if header.abi_major != ABI_MAJOR or header.abi_minor != ABI_MINOR:
        problems.append("serialized program header is not ABI 3.0")
    if manifest.get("descriptor_count") != len(deployment.table):
        problems.append("serialized manifest descriptor count is inconsistent")
    if manifest.get("instruction_count") != len(instructions):
        problems.append("serialized manifest instruction count is inconsistent")
    if manifest.get("entrypoints") != [dict(entry) for entry in deployment.entrypoints]:
        problems.append("serialized manifest entrypoints are inconsistent")
    if header.entrypoint_count != len(deployment.entrypoints):
        problems.append("serialized program entrypoint count is inconsistent")

    entries = list(deployment.entrypoints)
    mappings = all(isinstance(entry, Mapping) for entry in entries)
    phases = [entry.get("phase") for entry in entries] if mappings else []
    ids = [entry.get("entrypoint_id") for entry in entries] if mappings else []
    if not (
        len(entries) == 2
        and mappings
        and sorted(phases) == [0, 1]
        and sorted(ids) == [0, 1]
    ):
        problems.append("serialized deployment lacks exact prefill/decode entrypoints")
    for entry in entries if mappings else ():
        policy_id = entry.get("generation_policy_id")
        if not _integer(policy_id) or policy_id >= len(deployment.table):
            problems.append("serialized entrypoint has an invalid generation policy")
        elif deployment.table[int(policy_id)].descriptor_type != int(
            ExtendedDescriptorType.GENERATION_POLICY
        ):
            problems.append("serialized entrypoint does not name a generation policy")

    topology_ids = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)
    if len(topology_ids) != 1:
        problems.append("serialized deployment does not have one topology descriptor")
    else:
        topology = deployment.table[topology_ids[0]].payload
        if (
            topology.get("topology_class") != TOPOLOGY_CLASS[backend]
            or topology.get("node_count") != NODE_COUNT[backend]
        ):
            problems.append("serialized topology differs from the governed target")

    descriptors = list(deployment.table.descriptors())
    memory_objects = [
        descriptor
        for descriptor in descriptors
        if descriptor.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
    ]
    state_descriptors = deployment.table.ids_of_type(ExtendedDescriptorType.STATE)
    state_instructions = [
        instruction
        for instruction in instructions
        if instruction.major == int(Major.STATE)
    ]
    state_storage = [
        descriptor
        for descriptor in memory_objects
        if int(descriptor.payload["storage_class"]) == int(StorageClass.STATE)
    ]
    state_permissions = [
        descriptor
        for descriptor in descriptors
        if int(descriptor.permissions) & ABI_STATE_PERMISSIONS
    ]
    live_buffers = [
        descriptor
        for descriptor in memory_objects
        if int(descriptor.payload["storage_class"])
        in {int(StorageClass.HBM), int(StorageClass.SRAM)}
        and int(descriptor.permissions) & int(Permission.READ)
        and int(descriptor.permissions) & int(Permission.WRITE)
    ]
    if state_descriptors:
        problems.append("deployment contains an ABI STATE descriptor")
    if state_instructions:
        problems.append("deployment contains an ABI STATE instruction")
    if state_storage:
        problems.append("deployment contains a STATE storage object")
    if state_permissions:
        problems.append("deployment contains prepare/commit permissions")
    if not live_buffers:
        problems.append("deployment contains no ordinary read/write HBM/SRAM buffer")

    try:
        independent = verify_deployment(deployment, capability)
    except (ValueError, KeyError, TypeError) as exc:
        return (
            deployment,
            None,
            problems
            + [
                "serialized deployment independent admission failed: "
                f"{type(exc).__name__}: {exc}"
            ],
        )
    if not independent.admitted:
        problems.append("serialized deployment fails independent admission")
    if independent.state_resources != 0:
        problems.append("independent admission found nonzero ABI STATE resources")
    if record.get("verification") != independent.to_dict():
        problems.append(
            "producer verification differs from independent readback admission"
        )
    return deployment, independent, problems


def _association_digest(manifest: Mapping[str, Any]) -> str:
    return _canonical_digest(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )


def _association_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("numeric_contract"),
        tuple(entry.get("activation_shape") or ()),
        tuple(entry.get("weight_shape") or ()),
        tuple(entry.get("output_shape") or ()),
    )


def _check_association(record: Mapping[str, Any]) -> list[str]:
    manifest = record.get("executed_association")
    if not isinstance(manifest, dict):
        return ["executed_association is not an object"]
    problems: list[str] = []
    if manifest.get("schema") != ASSOCIATION_SCHEMA:
        problems.append("executed association schema is not governed v1")
    if manifest.get("association_policy") != ASSOCIATION_POLICY:
        problems.append("executed association policy is not shape-pinned")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        problems.append("executed association manifest has no entries")
        entries = []
    keys: list[tuple[Any, ...]] = []
    calls = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"association entry {index} is not an object")
            continue
        shapes = (
            entry.get("activation_shape"),
            entry.get("weight_shape"),
            entry.get("output_shape"),
        )
        if entry.get("numeric_contract") != BLOCKED_CONTRACT:
            problems.append(f"association entry {index} uses the wrong contract")
        if not all(
            isinstance(shape, list)
            and len(shape) == 2
            and all(_integer(value, minimum=1) for value in shape)
            for shape in shapes
        ):
            problems.append(f"association entry {index} has invalid shapes")
        else:
            activation, weight, output = shapes
            if activation[1] != weight[1] or output != [activation[0], weight[0]]:
                problems.append(f"association entry {index} shapes do not contract")
        count = entry.get("call_count")
        if not _integer(count, minimum=1):
            problems.append(f"association entry {index} has invalid call_count")
        else:
            calls += int(count)
        keys.append(_association_key(entry))
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        problems.append("association entries are not unique canonical order")
    if manifest.get("distinct_association_count") != len(entries):
        problems.append("association distinct count is inconsistent")
    if manifest.get("blocked_call_count") != calls or calls <= 0:
        problems.append("association blocked call count is inconsistent or empty")
    if manifest.get("manifest_sha256") != _association_digest(manifest):
        problems.append("association manifest digest is invalid")

    identity = record.get("implementation_identity")
    expected_identity = dict(identity) if isinstance(identity, dict) else {}
    expected_identity.pop("device_memory_bytes", None)
    if not expected_identity or expected_identity.get("unavailable"):
        problems.append("implementation identity is unavailable")
    if manifest.get("implementation_identity") != expected_identity:
        problems.append("association implementation identity differs from record")

    host = record.get("host_performance")
    if not isinstance(host, dict):
        problems.append("host_performance evidence is absent")
        return problems
    if (
        host.get("schema") != "opentallas.abi3.host_performance.device_epoch.v1"
        or host.get("scope") != "one_activated_device_including_all_logical_nodes"
        or host.get("architectural_counter_registry_unchanged") is not True
        or host.get("implementation_identity") != identity
    ):
        problems.append("host_performance identity or scope is invalid")
    ordered = host.get("ordered_executed_associations")
    ordered_counts: dict[tuple[Any, ...], int] = defaultdict(int)
    ordered_calls = 0
    if not isinstance(ordered, dict):
        problems.append("ordered executed-association evidence is absent")
    else:
        runs = ordered.get("runs")
        if not isinstance(runs, list) or not runs:
            problems.append("ordered executed-association evidence has no runs")
            runs = []
        for run in runs:
            if not isinstance(run, dict) or not _integer(
                run.get("call_count"), minimum=1
            ):
                problems.append("ordered executed-association run is invalid")
                continue
            count = int(run["call_count"])
            ordered_counts[_association_key(run)] += count
            ordered_calls += count
        expected_ordered_digest = _canonical_digest(
            {key: value for key, value in ordered.items() if key != "manifest_sha256"}
        )
        if (
            ordered.get("association_policy") != "executed_order_adjacent_run_length"
            or ordered.get("run_count") != len(runs)
            or ordered.get("blocked_call_count") != ordered_calls
            or ordered.get("manifest_sha256") != expected_ordered_digest
        ):
            problems.append("ordered executed-association manifest is inconsistent")
    aggregate_counts = {
        _association_key(entry): int(entry.get("call_count", 0))
        for entry in entries
        if isinstance(entry, dict)
    }
    if ordered_counts != aggregate_counts:
        problems.append("ordered and aggregate association shapes/counts differ")
    reconciliation = host.get("association_reconciliation")
    if (
        not isinstance(reconciliation, dict)
        or reconciliation.get("ordered_blocked_call_count") != ordered_calls
        or reconciliation.get("aggregated_blocked_call_count") != calls
        or reconciliation.get("counts_equal") is not True
        or ordered_calls != calls
    ):
        problems.append("host/aggregate association reconciliation is invalid")
    return problems


def _check_verification(record: Mapping[str, Any]) -> list[str]:
    report = record.get("verification")
    if not isinstance(report, dict):
        return ["verification is not an object"]
    problems: list[str] = []
    checks = report.get("checks")
    if report.get("admitted") is not True or report.get("errors") != []:
        problems.append("deployment was not cleanly admitted")
    if (
        not isinstance(checks, dict)
        or not checks
        or any(value is not True for value in checks.values())
    ):
        problems.append("verification checks are missing or not all true")
    proved = report.get("proved_retired_work")
    if not _integer(proved, minimum=1) or proved != report.get("declared_retired_work"):
        problems.append("admission did not exactly prove declared retired work")
    if report.get("state_resources") != 0:
        problems.append("admission reports nonzero ABI STATE resources")
    return problems


def _state_counter(name: str) -> bool:
    return name.startswith("state.") or name == "engine.state.descriptors"


def _replicated_engine_counter(name: str) -> bool:
    return (
        not name.startswith(
            (
                "hbm.",
                "rom.",
                "sram.",
                "host.",
                "state.",
                "link.",
                "control.",
                "queue.",
                "instructions.",
            )
        )
        and name != "engine.state.descriptors"
    )


def _check_steps_and_counters(
    record: Mapping[str, Any],
    generated: Sequence[int],
    terminal: str,
    node_count: int,
) -> list[str]:
    problems: list[str] = []
    steps = record.get("per_step")
    if not isinstance(steps, list) or len(steps) != len(generated):
        return ["per_step count does not equal generated token count"]
    retired = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"per_step[{index}] is not an object")
            continue
        if step.get("step") != index or step.get("transaction_id") != index + 1:
            problems.append(f"per_step[{index}] has the wrong step/transaction id")
        if step.get("phase") != ("prefill" if index == 0 else "decode"):
            problems.append(f"per_step[{index}] has the wrong phase")
        if step.get("status") != "SUCCESS" or step.get("trap") != "NONE":
            problems.append(f"per_step[{index}] did not complete successfully")
        if (
            step.get("produced_tokens") != [generated[index]]
            or step.get("final_token_id") != generated[index]
        ):
            problems.append(f"per_step[{index}] does not bind its generated token")
        value = step.get("instructions_retired")
        if not _integer(value, minimum=1) or step.get("retired_work") != value:
            problems.append(f"per_step[{index}] retired-work evidence is invalid")
        else:
            retired += int(value)
        if not _positive_number(step.get("wall_seconds")):
            problems.append(f"per_step[{index}] host wall_seconds is invalid")
        is_last = index == len(steps) - 1
        allowed_reason = (
            {1}
            if terminal == "eos" and is_last
            else ({0, 2} if terminal == "cap" and is_last else {0})
        )
        if step.get("eos_reason") not in allowed_reason:
            problems.append(f"per_step[{index}] has inconsistent EOS reason")
    if not _positive_number(record.get("wall_seconds")):
        problems.append("host functional-simulator wall_seconds is invalid")

    counters = record.get("counters")
    if not isinstance(counters, dict):
        return problems + ["counters is not an object"]
    if any(not _integer(value) for value in counters.values()):
        problems.append(
            "architectural counters contain a negative or non-integer value"
        )
    required = {
        "selection.tokens_selected": len(generated) * node_count,
        "selection.tokens_appended": len(generated) * node_count,
        "selection.vocabulary_elements": (
            len(generated) * VOCABULARY_SIZE * node_count
        ),
        "instructions.retired": retired,
    }
    for name, expected in required.items():
        if counters.get(name) != expected:
            problems.append(
                f"counter {name} is {counters.get(name)!r}, expected {expected}"
            )
    if counters.get("selection.invalid_tokens", 0) != 0:
        problems.append("selection.invalid_tokens is nonzero")
    for name in (
        "instructions.issued",
        "dma.scatter_elements",
        "attention.kv_bytes_read",
        "hbm.bytes_written",
    ):
        if not _integer(counters.get(name), minimum=1):
            problems.append(f"counter {name} is missing or not positive")
    for name, value in counters.items():
        if _state_counter(name) and value != 0:
            problems.append(
                f"counter {name} is nonzero in the ABI 3.0 live-buffer design"
            )

    scope = record.get("counter_scope")
    nodes = record.get("node_counters")
    if (
        not isinstance(scope, dict)
        or scope.get("aggregate") != "cluster_total"
        or scope.get("per_node") != "engine_work_by_node_id"
        or scope.get("node_count") != node_count
        or scope.get("node_counters_index") != "NODE_ID"
    ):
        problems.append("counter scope is not the governed measured-node split")
    if (
        not isinstance(nodes, list)
        or len(nodes) != node_count
        or any(not isinstance(node, dict) for node in nodes)
    ):
        return problems + [f"node_counters is not exactly {node_count} measured nodes"]
    for index, node in enumerate(nodes):
        if any(not _integer(value) for value in node.values()):
            problems.append(f"node_counters[{index}] contains an invalid value")
        for name in PAIR_LOGICAL_COUNTERS:
            if not _integer(node.get(name), minimum=1):
                problems.append(
                    f"node_counters[{index}] logical counter {name} is missing or zero"
                )
        expected_node = {
            "selection.tokens_selected": len(generated),
            "selection.tokens_appended": len(generated),
            "selection.vocabulary_elements": len(generated) * VOCABULARY_SIZE,
        }
        for name, expected in expected_node.items():
            if node.get(name) != expected:
                problems.append(f"node_counters[{index}] {name} is inconsistent")
        for name, value in node.items():
            if _state_counter(name) and value != 0:
                problems.append(f"node_counters[{index}] {name} is nonzero")
    node_keys = set().union(*(node.keys() for node in nodes))
    for name in sorted(node_keys):
        if not _replicated_engine_counter(name):
            continue
        total = sum(int(node.get(name, 0)) for node in nodes)
        if counters.get(name) != total:
            problems.append(
                f"aggregate counter {name} does not equal measured node sum"
            )
    return problems


def _check_token_text(
    record: Mapping[str, Any],
    workload: Mapping[str, Any],
    oracle_result: Mapping[str, Any],
    prompt: Sequence[int],
    generated: Sequence[int],
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    checkpoint = inputs.get("checkpoint_root") if isinstance(inputs, dict) else None
    root = (
        _resolved_path(checkpoint.get("path")) if isinstance(checkpoint, dict) else None
    )
    tokenizer_path = root / "tokenizer.json" if root is not None else None
    evidence: dict[str, Any] = {
        "tokenizer": {
            "path": _relative(tokenizer_path) if tokenizer_path is not None else None,
            "sha256": None,
            "library": "tokenizers",
            "library_version": None,
        }
    }
    if tokenizer_path is None or not tokenizer_path.is_file():
        return evidence, ["checkpoint tokenizer.json is unavailable"]
    actual_hash = _sha256(tokenizer_path)
    evidence["tokenizer"]["sha256"] = actual_hash
    if actual_hash != TOKENIZER_SHA256:
        problems.append(
            "checkpoint tokenizer.json is not the pinned DeepSeek tokenizer"
        )
    try:
        library_version = importlib.metadata.version("tokenizers")
    except importlib.metadata.PackageNotFoundError:
        return evidence, problems + ["pinned tokenizers library is unavailable"]
    evidence["tokenizer"]["library_version"] = library_version
    if library_version != TOKENIZERS_VERSION:
        problems.append(
            f"tokenizers library is {library_version}, expected {TOKENIZERS_VERSION}"
        )
    try:
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        prompt_text = tokenizer.decode(list(prompt), skip_special_tokens=False)
        raw_output = tokenizer.decode(list(generated), skip_special_tokens=False)
        visible_output = tokenizer.decode(list(generated), skip_special_tokens=True)
        prompt_round_trip = tokenizer.encode(
            str(workload.get("rendered_text", "")), add_special_tokens=False
        ).ids
    except (OSError, TypeError, ValueError) as exc:
        return evidence, problems + [
            "checkpoint tokenizer cannot decode exact-200K tokens: "
            f"{type(exc).__name__}: {exc}"
        ]
    rendered = workload.get("rendered_text")
    if prompt_text != rendered:
        problems.append("decoded prompt does not equal the frozen natural context")
    if list(prompt_round_trip) != list(prompt):
        problems.append("frozen natural context does not round-trip to prompt IDs")
    if raw_output != oracle_result.get("raw_decoded_text"):
        problems.append("decoded raw output does not equal the Gate-B oracle text")
    if visible_output != oracle_result.get("visible_decoded_text"):
        problems.append("decoded visible output does not equal the Gate-B oracle text")
    if not visible_output.strip():
        problems.append("decoded visible output is empty or whitespace-only")
    if "\ufffd" in raw_output or "\ufffd" in visible_output:
        problems.append("decoded output contains a Unicode replacement character")
    evidence.update(
        {
            "input": {
                "token_count": len(prompt),
                "token_ids_sha256": digest_of(list(prompt)),
                "rendered_text_sha256": _text_sha256(prompt_text),
                "rendered_character_count": len(prompt_text),
                "decode_matches_frozen_text": prompt_text == rendered,
                "encode_round_trip_matches_ids": list(prompt_round_trip)
                == list(prompt),
            },
            "output": {
                "token_count": len(generated),
                "token_ids": list(generated),
                "token_ids_sha256": digest_of(list(generated)),
                "raw_decoded_text": raw_output,
                "raw_decoded_text_sha256": _text_sha256(raw_output),
                "visible_decoded_text": visible_output,
                "visible_decoded_text_sha256": _text_sha256(visible_output),
                "raw_matches_gate_b_oracle": raw_output
                == oracle_result.get("raw_decoded_text"),
                "visible_matches_gate_b_oracle": visible_output
                == oracle_result.get("visible_decoded_text"),
            },
        }
    )
    return evidence, problems


def _check_record(
    path: Path,
    backend: str,
    workload: Mapping[str, Any],
    oracle: Mapping[str, Any],
    oracle_result: Mapping[str, Any],
    prompt: Sequence[int],
    gold: Sequence[int],
) -> dict[str, Any]:
    record = _load(path)
    problems: list[str] = []
    if record.get("schema") != RECORD_SCHEMA or record.get("status") != "pass":
        problems.append("record is not a passing accelerator_tokens.v1 artifact")
    if (
        record.get("evidence_class") != "functional_artifact_only"
        or record.get("tool") != "tools/run_accelerator_tokens.py"
        or record.get("backend") != backend
    ):
        problems.append("record has the wrong producer, evidence class, or backend")

    capability_path = CAPABILITIES[backend]
    capability = Capability.from_dict(_load(capability_path))
    target = record.get("target")
    if not isinstance(target, dict) or (
        target.get("target_id") != TARGET_IDS[backend]
        or target.get("backend") != TARGET_BACKENDS[backend]
        or target.get("topology_class") != TOPOLOGY_CLASS[backend]
        or target.get("node_count") != NODE_COUNT[backend]
        or target.get("capability_digest") != capability.digest
        or target.get("technology_view") != capability.technology_view
        or _resolved_path(target.get("capability")) != capability_path.resolve()
        or not isinstance(target.get("deployment_digest"), str)
        or len(target.get("deployment_digest", "")) != 64
    ):
        problems.append("target is not the source-current governed topology")

    prompt_digest = digest_of(list(prompt))
    work = record.get("workload")
    expected_work = {
        "workload_id": WORKLOAD_ID,
        "workload_digest": WORKLOAD_DIGEST,
        "prompt_token_count": PROMPT_TOKENS,
        "max_new_tokens": MAX_NEW_TOKENS,
        "prompt_token_ids_sha256": prompt_digest,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "rendered_text_sha256": RENDERED_TEXT_SHA256,
    }
    if not isinstance(work, dict):
        problems.append("workload is not an object")
    else:
        for name, expected in expected_work.items():
            if work.get(name) != expected:
                problems.append(f"workload.{name} is not the frozen value")
        if work.get("prompt_token_ids") != list(prompt):
            problems.append("workload prompt tokens are not the frozen 200K prompt")

    model = record.get("model")
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    checkpoint = inputs.get("checkpoint_root") if isinstance(inputs, dict) else None
    if not isinstance(model, dict) or (
        model.get("model_id") != MODEL_ID
        or model.get("graph_id") != GRAPH_ID
        or model.get("numeric_profile") != NUMERIC_PROFILE
        or _resolved_path(model.get("checkpoint_root"))
        != _resolved_path(
            checkpoint.get("path") if isinstance(checkpoint, dict) else None
        )
    ):
        problems.append("model identity is not the source-current DeepSeek graph")

    generated = record.get("generated_token_ids")
    if not (
        isinstance(generated, list)
        and generated
        and all(_integer(token) and token < VOCABULARY_SIZE for token in generated)
    ):
        generated = []
        problems.append("generated token sequence is empty or illegitimate")
    if record.get("generated_token_count") != len(generated):
        problems.append("generated_token_count is inconsistent")
    if generated != list(gold):
        problems.append("generated tokens are not exactly the accepted Gate-B oracle")
    if (
        record.get("failure") is not None
        or record.get("token_legitimacy_problems") != []
    ):
        problems.append("record carries a failure or token-legitimacy problem")

    oracle_path = ORACLE.resolve()
    oracle_evidence = record.get("oracle")
    if not isinstance(oracle_evidence, dict) or (
        _resolved_path(oracle_evidence.get("artifact")) != oracle_path
        or oracle_evidence.get("artifact_sha256") != _sha256(ORACLE)
        or oracle_evidence.get("evidence_class") != "external_reference_comparator"
        or oracle_evidence.get("expert_numeric_path") != "fp8"
        or oracle_evidence.get("generated_token_ids") != list(gold)
        or oracle_evidence.get("agreement") is not True
        or oracle_evidence.get("first_divergence_index") is not None
        or oracle_evidence.get("compared_tokens") != len(generated)
        or oracle_evidence.get("oracle_token_count") != len(gold)
    ):
        problems.append("oracle evidence is not exact and source-current")

    terminal, terminal_problems = _terminal_kind(generated, record.get("stop_reason"))
    problems.extend(terminal_problems)
    producer_terminal = record.get("terminal_acceptance")
    checks = (
        producer_terminal.get("checks") if isinstance(producer_terminal, dict) else None
    )
    if (
        not isinstance(producer_terminal, dict)
        or producer_terminal.get("contract") != "exact_eos_or_cap"
        or producer_terminal.get("accepted") is not True
        or producer_terminal.get("terminal_kind") != terminal
        or producer_terminal.get("failed_checks") != []
        or not isinstance(checks, dict)
        or not checks
        or any(value is not True for value in checks.values())
    ):
        problems.append("producer terminal_acceptance is absent or inconsistent")

    policy = record.get("generation_policy")
    expected_policy = {
        "selection_mode": 0,
        "tie_rule": 0,
        "eos_count": 1,
        "eos_token_0": EOS_TOKEN_ID,
        "eos_token_1": NO_ID,
        "eos_token_2": NO_ID,
        "eos_token_3": NO_ID,
        "eos_token_4": NO_ID,
        "eos_token_5": NO_ID,
        "eos_token_6": NO_ID,
        "eos_token_7": NO_ID,
        "vocabulary_size": VOCABULARY_SIZE,
        "rng_seed_hi": 0,
        "rng_seed_lo": 0,
    }
    if not isinstance(policy, dict):
        problems.append("generation_policy is not an object")
    else:
        if record.get("generation_policy_digest") != digest_of(policy):
            problems.append("generation policy digest is invalid")
        for name, expected in expected_policy.items():
            if policy.get(name) != expected:
                problems.append(f"generation policy {name} is not frozen")
        if not _integer(policy.get("max_new_tokens"), minimum=MAX_NEW_TOKENS):
            problems.append("generation policy cannot represent the 256-token cap")

    snapshot_path = _resolved_path(oracle.get("snapshot"))
    problems += _check_verification(record)
    problems += _check_inputs(
        record, backend, prompt_digest, oracle_path, snapshot_path
    )
    _deployment, _report, deployment_problems = _check_published_deployment(
        record, backend, capability
    )
    problems += deployment_problems
    problems += _check_source_lock(record, backend)
    problems += _check_association(record)
    problems += _check_steps_and_counters(
        record,
        generated,
        terminal or "invalid",
        NODE_COUNT[backend],
    )
    text_evidence, text_problems = _check_token_text(
        record, workload, oracle_result, prompt, generated
    )
    problems += text_problems
    return {
        "path": _relative(path),
        "sha256": _sha256(path),
        "backend": backend,
        "generated_token_ids": list(generated),
        "terminal_kind": terminal,
        "text_evidence": text_evidence,
        "record": record,
        "passes": not problems,
        "problems": problems,
    }


def _normalised_association(record: Mapping[str, Any], divisor: int) -> dict[str, Any]:
    manifest = record.get("executed_association")
    if not isinstance(manifest, dict):
        return {}
    entries: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict) or not _integer(entry.get("call_count")):
            continue
        count = int(entry["call_count"])
        entries.append(
            {
                "numeric_contract": entry.get("numeric_contract"),
                "activation_shape": entry.get("activation_shape"),
                "weight_shape": entry.get("weight_shape"),
                "output_shape": entry.get("output_shape"),
                "call_count": count // divisor if count % divisor == 0 else None,
            }
        )
    calls = manifest.get("blocked_call_count")
    return {
        "implementation_identity": manifest.get("implementation_identity"),
        "entries": entries,
        "distinct_association_count": manifest.get("distinct_association_count"),
        "blocked_call_count": (
            int(calls) // divisor
            if _integer(calls) and int(calls) % divisor == 0
            else None
        ),
    }


def _step_semantics(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = (
        "step",
        "transaction_id",
        "phase",
        "status",
        "trap",
        "produced_tokens",
        "final_token_id",
        "eos_reason",
    )
    steps = record.get("per_step")
    if not isinstance(steps, list):
        return []
    return [
        {name: step.get(name) for name in fields}
        for step in steps
        if isinstance(step, dict)
    ]


def _logical_node_counters(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes = record.get("node_counters")
    if not isinstance(nodes, list):
        return []
    return [
        {name: node.get(name) for name in PAIR_LOGICAL_COUNTERS}
        for node in nodes
        if isinstance(node, dict)
    ]


def validate(
    rom_record: Path,
    hbm_record: Path,
    oracle_acceptance: Path = DEFAULT_GATE_B,
) -> dict[str, Any]:
    workload, _graph, prompt, problems = _frozen_inputs()
    oracle, oracle_result, gold, gate_problems = _check_gate_b(oracle_acceptance)
    problems.extend(gate_problems)
    rows = [
        _check_record(
            rom_record,
            "rom_deepseek_v4",
            workload,
            oracle,
            oracle_result,
            prompt,
            gold,
        ),
        _check_record(
            hbm_record,
            "hbm_sram",
            workload,
            oracle,
            oracle_result,
            prompt,
            gold,
        ),
    ]
    for row in rows:
        problems.extend(
            f"{Path(row['path']).name}: {problem}" for problem in row["problems"]
        )

    rom = rows[0]["record"]
    hbm = rows[1]["record"]
    rom_nodes = _logical_node_counters(rom)
    hbm_nodes = _logical_node_counters(hbm)
    logical_counter_match = (
        bool(rom_nodes)
        and len(hbm_nodes) == 32
        and all(node == rom_nodes[0] for node in hbm_nodes)
    )
    pair_checks = {
        "full_token_sequences_identical": (
            rows[0]["generated_token_ids"] == rows[1]["generated_token_ids"] == gold
        ),
        "decoded_text_evidence_identical": (
            rows[0]["text_evidence"] == rows[1]["text_evidence"]
        ),
        "implementation_identities_identical": (
            rom.get("implementation_identity") == hbm.get("implementation_identity")
        ),
        "association_equal_after_32_node_normalisation": (
            _normalised_association(rom, 1) == _normalised_association(hbm, 32)
        ),
        "per_step_model_semantics_identical": (
            _step_semantics(rom) == _step_semantics(hbm)
        ),
        "logical_node_counters_identical": logical_counter_match,
    }
    for name, passed in pair_checks.items():
        if not passed:
            problems.append(f"pair check failed: {name}")

    accepted = not problems
    return {
        "schema": SCHEMA,
        "status": "accepted" if accepted else "rejected",
        "accepted": accepted,
        "workload_id": WORKLOAD_ID,
        "oracle_acceptance": {
            "path": _relative(oracle_acceptance),
            "sha256": _sha256(oracle_acceptance),
            "accepted": not gate_problems,
        },
        "association_pair_policy": PAIR_POLICY,
        "records": [
            {
                key: row[key]
                for key in (
                    "path",
                    "sha256",
                    "backend",
                    "terminal_kind",
                    "passes",
                    "problems",
                )
            }
            for row in rows
        ],
        "pair_checks": pair_checks,
        "abi_profile": {
            "version": "3.0",
            "execution_state": "ordinary_live_hbm_sram_buffers",
            "abi_state_descriptors": 0,
            "abi_state_instructions": 0,
            "durable_journal_checkpoint_or_model_retry": False,
            "run_failure_model": "uninterrupted_fail_stop",
        },
        "token_evidence": rows[0]["text_evidence"],
        "problems": problems,
        "claim_boundary": {
            "acceptance_established": accepted,
            "required_execution_scope": (
                "full_causal_model_execution_from_serialized_abi3_artifacts"
            ),
            "exact_prompt_tokens": PROMPT_TOKENS,
            "terminal_contract": "first_official_eos_included_or_exactly_256",
            "rom_topology": "one_wafer_logical_device",
            "hbm_topology": "exactly_32_identical_hbm_sram_nodes",
            "oracle_token_injection": False,
            "host_functional_timing_is_not_rtl_or_silicon_performance": True,
            "cycle_accurate_or_physical_closure": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom-record", required=True, type=Path)
    parser.add_argument("--hbm-record", required=True, type=Path)
    parser.add_argument("--oracle-acceptance", type=Path, default=DEFAULT_GATE_B)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        document = validate(args.rom_record, args.hbm_record, args.oracle_acceptance)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for problem in document["problems"]:
        print(f"PROBLEM {problem}")
    print(f"DeepSeek exact-200K accelerator acceptance: {document['status']}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(document))
        print(f"wrote {args.output}")
    return 0 if document["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
