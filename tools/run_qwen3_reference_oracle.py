#!/usr/bin/env python3
"""Independent Qwen3-8B greedy-decode oracle.

This is an *external comparator*, not part of the accelerator path.  It runs the
pinned checkpoint through the vendor modelling code to produce the token IDs a
faithful implementation should produce for each pinned workload, so that the
accelerator's own output can be checked against something it did not compute.

It is never used to produce accelerator tokens, never supplies an activation,
and its results are labelled as an external reference in every report.  ADR-003
section 18 permits exactly this use and forbids the other one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    load_strict_json,
    publish_bytes_atomic_no_replace,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    QwenChatTokenizer,
    SOURCE_REVISION,
)
from compiler.workloads.qwen3_exact_8k import (  # noqa: E402
    AuthenticatedWorkloadTokenizer,
    MAX_NEW_TOKENS as EXACT_8K_MAX_NEW_TOKENS,
    WORKLOAD_ID as EXACT_8K_WORKLOAD_ID,
    load_construction,
    validate_materialized_workload,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.agent import (  # noqa: E402
    AgentProtocolError,
    Sandbox,
    parse_turn,
    render_agent_context,
    split_thinking,
)

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)

PREFILL_ASSOCIATION_SCHEMA = "opentallas.qwen3.prefill_association.v1"
PREFILL_ASSOCIATION_POLICY = (
    "tool_framework_attention_device_backend_and_chunk_pinned_v1"
)
ORACLE_TOOL = "tools/run_qwen3_reference_oracle.py"
ORACLE_TOOL_VERSION = "qwen3_reference_oracle.py:v2"

DEFAULT_WORKLOADS = REPO / "build" / "workloads" / "qwen3-8b"
DEFAULT_CHECKPOINT_LOCK = (
    REPO
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
DEFAULT_EXACT_8K_CONSTRUCTION = (
    REPO / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
)

GATE_1_LAUNCH_SCHEMA = "opentallas.qwen3.gate1_launch.v1"
GATE_1_PROFILE_ID = "qwen3_exact_8k_external_oracle_v1"
GATE_1_WORKLOAD_INDEX_SHA256 = (
    "ce7ec985a65017e692013f056828adf16695d6ecb7747eb90970cd64978c2ee9"
)
GATE_1_WORKLOAD_SHA256 = (
    "4bd1ca5cad91a6006383c4470a16fd803e18bbfad9ec19fe8ed01373da118217"
)
GATE_1_CONSTRUCTION_SHA256 = (
    "38e4a9acc569fff5ffc23ed2187cb71a551133691acac7131f4b6a7d3c8909ca"
)
GATE_1_CHECKPOINT_LOCK_SHA256 = (
    "880782c1a160c466b39e2b4502649704819a96666f1de7abaacda30f090fbaaa"
)
GATE_1_CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)


class OracleInputError(ValueError):
    """A source or launch option cannot support governed oracle evidence."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            while block := handle.read(8 * 1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise OracleInputError(f"cannot hash oracle input {path}: {exc}") from exc
    return digest.hexdigest()


def _record_path(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _file_identity(path: Path) -> dict[str, object]:
    resolved = Path(path).resolve()
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise OracleInputError(f"oracle input is unavailable: {resolved}: {exc}") from exc
    if not resolved.is_file():
        raise OracleInputError(f"oracle input is not a regular file: {resolved}")
    return {
        "path": _record_path(resolved),
        "size_bytes": size,
        "sha256": _sha256_file(resolved),
    }


def _workload_digest(body: Mapping[str, object]) -> str:
    required = ("workload_id", "kind", "token_ids", "max_new_tokens")
    try:
        value = {name: body[name] for name in required}
    except KeyError as exc:
        raise OracleInputError(
            f"workload lacks required field {exc.args[0]!r}"
        ) from exc
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _load_selected_workloads(
    workloads: Path, only: list[str] | None
) -> tuple[
    dict[str, Any],
    list[tuple[str, dict[str, Any]]],
    dict[str, dict[str, Any]],
    dict[str, object],
]:
    """Strictly load and cross-check the workload index before model import."""

    root = Path(workloads).resolve()
    index_path = root / "index.json"
    try:
        index = load_strict_json(index_path)
    except (ArtifactError, OSError, ValueError) as exc:
        raise OracleInputError(f"cannot load workload index: {exc}") from exc
    if (
        set(index) != {"model_id", "schema", "snapshot", "tokenizer_sha256", "workloads"}
        or index.get("schema") != "opentallas.abi3.workload_index.v1"
        or index.get("model_id") != "qwen3-8b"
        or not isinstance(index.get("workloads"), dict)
    ):
        raise OracleInputError("Qwen workload index boundary differs")
    entries = index["workloads"]
    assert isinstance(entries, dict)
    if only is None:
        selected_ids = sorted(entries)
    else:
        if len(only) != len(set(only)):
            raise OracleInputError("--only contains a duplicate workload id")
        unknown = sorted(set(only) - set(entries))
        if unknown:
            raise OracleInputError(f"unknown workloads: {unknown}")
        selected_ids = sorted(only)
    if not selected_ids:
        raise OracleInputError("no workloads selected")

    selected: list[tuple[str, dict[str, Any]]] = []
    bodies: dict[str, dict[str, Any]] = {}
    sources: dict[str, object] = {}
    for workload_id in selected_ids:
        raw_entry = entries[workload_id]
        if not isinstance(raw_entry, dict) or set(raw_entry) != {
            "digest",
            "kind",
            "max_new_tokens",
            "path",
            "prompt_token_count",
        }:
            raise OracleInputError(f"{workload_id}: workload index entry differs")
        entry = dict(raw_entry)
        relative = entry.get("path")
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or Path(relative).as_posix() != relative
        ):
            raise OracleInputError(f"{workload_id}: workload path is not normalized")
        source_path = (root / relative).resolve()
        try:
            source_path.relative_to(root)
        except ValueError as exc:
            raise OracleInputError(f"{workload_id}: workload path escapes its root") from exc
        try:
            body = load_strict_json(source_path)
        except (ArtifactError, OSError, ValueError) as exc:
            raise OracleInputError(f"{workload_id}: cannot load workload: {exc}") from exc
        tokens = body.get("token_ids")
        if (
            body.get("workload_id") != workload_id
            or not isinstance(tokens, list)
            or not all(
                isinstance(token, int) and not isinstance(token, bool) and token >= 0
                for token in tokens
            )
            or body.get("prompt_token_count") != len(tokens)
            or body.get("digest") != _workload_digest(body)
            or entry
            != {
                "digest": body.get("digest"),
                "kind": body.get("kind"),
                "max_new_tokens": body.get("max_new_tokens"),
                "path": relative,
                "prompt_token_count": len(tokens),
            }
        ):
            raise OracleInputError(
                f"{workload_id}: workload body and index entry do not agree"
            )
        selected.append((workload_id, entry))
        bodies[workload_id] = body
        sources[workload_id] = _file_identity(source_path)
    return index, selected, bodies, {
        "workload_index": _file_identity(index_path),
        "workload_sources": sources,
    }


def _configure_gate_1_production(args: argparse.Namespace) -> list[str]:
    """Normalize every correctness-relevant exact-8K oracle option."""

    if not args.gate_1_production:
        return []
    problems: list[str] = []
    if args.only not in (None, [EXACT_8K_WORKLOAD_ID]):
        problems.append(
            f"--gate-1-production only permits --only {EXACT_8K_WORKLOAD_ID}"
        )
    if args.agent_episode:
        problems.append("--gate-1-production cannot run an agent episode")
    if args.force:
        problems.append("--gate-1-production cannot overwrite prior evidence")
    if args.cpu_only:
        problems.append("--gate-1-production requires the qualified GPU/CPU placement")
    if args.attention_implementation != "sdpa":
        problems.append("--gate-1-production requires SDPA attention")
    if args.prefill_chunk not in (0, 512):
        problems.append("--gate-1-production requires a 512-token prefill chunk")
    if args.cpu_gib != 80:
        problems.append("--gate-1-production requires the qualified 80 GiB CPU limit")
    if problems:
        return problems
    args.only = [EXACT_8K_WORKLOAD_ID]
    args.prefill_chunk = 512
    args.gpu_gib = 8
    return []


def _gate_1_launch_contract() -> dict[str, object]:
    return {
        "schema": GATE_1_LAUNCH_SCHEMA,
        "profile_id": GATE_1_PROFILE_ID,
        "workload_id": EXACT_8K_WORKLOAD_ID,
        "prompt_token_count": 8_000,
        "max_new_tokens": EXACT_8K_MAX_NEW_TOKENS,
        "selection": "greedy_lowest_token_id_argmax",
        "terminal": {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "include_eos_in_output": True,
            "rule": "first_official_eos_or_exact_cap",
        },
        "prefill": {
            "mode": "chunked_forward_kv_cache",
            "chunk_tokens": 512,
        },
        "numeric": {
            "dtype": "bfloat16",
            "attention_implementation": "sdpa",
        },
        "placement": {
            "policy": "auto",
            "gpu_memory_gib": 8,
            "cpu_memory_gib": 80,
        },
    }


def _authenticate_gate_1_inputs(
    args: argparse.Namespace,
    index: Mapping[str, Any],
    bodies: Mapping[str, Mapping[str, Any]],
    input_identity: dict[str, object],
) -> tuple[dict[str, object], QwenChatTokenizer]:
    """Fully authenticate exact-8K sources before importing model frameworks."""

    path_expectations = (
        (args.snapshot, DEFAULT_SNAPSHOT, "snapshot"),
        (args.workloads, DEFAULT_WORKLOADS, "workload root"),
        (args.checkpoint_lock, DEFAULT_CHECKPOINT_LOCK, "checkpoint lock"),
        (
            args.exact_8k_construction,
            DEFAULT_EXACT_8K_CONSTRUCTION,
            "exact-8K construction",
        ),
    )
    for observed, expected, label in path_expectations:
        if Path(observed).resolve() != expected.resolve():
            raise OracleInputError(f"{label} is not the pinned Gate-1 path {expected}")

    index_identity = input_identity.get("workload_index")
    workload_sources = input_identity.get("workload_sources")
    workload_identity = (
        workload_sources.get(EXACT_8K_WORKLOAD_ID)
        if isinstance(workload_sources, dict)
        else None
    )
    if (
        not isinstance(index_identity, dict)
        or index_identity.get("sha256") != GATE_1_WORKLOAD_INDEX_SHA256
        or not isinstance(workload_identity, dict)
        or workload_identity.get("sha256") != GATE_1_WORKLOAD_SHA256
    ):
        raise OracleInputError("exact-8K workload or index identity is not Gate-1 pinned")
    if (
        index.get("snapshot") != str(DEFAULT_SNAPSHOT)
        or index.get("tokenizer_sha256")
        != "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
    ):
        raise OracleInputError("workload index model snapshot or tokenizer differs")

    construction_identity = _file_identity(args.exact_8k_construction)
    checkpoint_lock_identity = _file_identity(args.checkpoint_lock)
    input_identity["exact_8k_construction"] = construction_identity
    input_identity["checkpoint_lock"] = checkpoint_lock_identity
    if construction_identity["sha256"] != GATE_1_CONSTRUCTION_SHA256:
        raise OracleInputError("exact-8K construction identity is not Gate-1 pinned")
    if checkpoint_lock_identity["sha256"] != GATE_1_CHECKPOINT_LOCK_SHA256:
        raise OracleInputError("checkpoint-lock source identity is not Gate-1 pinned")

    lock = load_checkpoint_lock(args.checkpoint_lock)
    source = lock.get("source")
    if (
        lock.get("lock_id") != GATE_1_CHECKPOINT_LOCK_ID
        or not isinstance(source, dict)
        or source.get("repository") != "Qwen/Qwen3-8B"
        or source.get("revision") != SOURCE_REVISION
        or source.get("remote_code_policy") != "disabled"
    ):
        raise OracleInputError("checkpoint lock does not bind the pinned Qwen release")
    verify_checkpoint_lock(args.snapshot, lock)

    chat = QwenChatTokenizer(args.snapshot, lock)
    construction = load_construction(args.exact_8k_construction)
    try:
        validate_materialized_workload(
            bodies[EXACT_8K_WORKLOAD_ID],
            AuthenticatedWorkloadTokenizer(chat),
            construction,
            construction_path=args.exact_8k_construction,
        )
    except (ArtifactError, KeyError, ValueError) as exc:
        raise OracleInputError(
            f"exact-8K workload reconstruction failed: {exc}"
        ) from exc

    checkpoint = lock["checkpoint"]
    return {
        "completed_before_model_framework_import": True,
        "full_byte_hash_verified": True,
        "lock_id": lock["lock_id"],
        "lock_source_sha256": checkpoint_lock_identity["sha256"],
        "payload_bytes": checkpoint["payload_bytes"],
        "shard_count": checkpoint["shard_count"],
        "tensor_count": checkpoint["tensor_count"],
    }, chat


def _validate_gate_1_generation(
    generated: list[int], *, eos_ids: set[int]
) -> None:
    if not generated:
        raise OracleInputError("Gate-1 oracle generated no token")
    if len(generated) > EXACT_8K_MAX_NEW_TOKENS:
        raise OracleInputError("Gate-1 oracle exceeded its 256-token cap")
    if any(
        isinstance(token, bool)
        or not isinstance(token, int)
        or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
        for token in generated
    ):
        raise OracleInputError("Gate-1 oracle selected an invalid or padded token id")
    eos_positions = [index for index, token in enumerate(generated) if token in eos_ids]
    if eos_positions and eos_positions != [len(generated) - 1]:
        raise OracleInputError("Gate-1 oracle executed or retained a token after EOS")
    if not eos_positions and len(generated) != EXACT_8K_MAX_NEW_TOKENS:
        raise OracleInputError("Gate-1 oracle stopped before EOS and before its exact cap")


def _prefill_association_digest(association: Mapping[str, object]) -> str:
    """Canonical identity of the association-affecting oracle configuration."""
    body = {
        key: value
        for key, value in association.items()
        if key != "identity_sha256"
    }
    return hashlib.sha256(canonical_json(body)).hexdigest()


def _backend_flag(owner, name: str) -> bool | str:
    """Read one optional PyTorch backend flag without silently inventing it."""
    value = getattr(owner, name, None)
    if value is None:
        return "unavailable"
    try:
        return bool(value() if callable(value) else value)
    except (RuntimeError, TypeError):
        return "unavailable"


def _model_device_map(model) -> dict[str, str]:
    """The actual module placement, normalized to stable JSON strings."""
    declared = getattr(model, "hf_device_map", None)
    if isinstance(declared, Mapping) and declared:
        return {
            str(name): str(device)
            for name, device in sorted(declared.items(), key=lambda item: str(item[0]))
        }
    return {"": str(model.device)}


def _oracle_execution_identity(
    model,
    torch,
    transformers,
    *,
    cpu_only: bool,
    attention_implementation: str,
) -> dict[str, object]:
    """Identity of choices which may change a BF16 reduction association.

    A vendor-model token sequence is not independent of how its 8,000-token
    prefill was evaluated.  In particular, PyTorch and Transformers versions,
    SDPA's selected kernels, device placement, and CPU thread/BLAS build can all
    change the legal BF16 association.  Record them rather than letting a gold
    sequence appear implementation-free.
    """
    cuda = getattr(torch.backends, "cuda", None)
    sdpa_flags = {
        name: _backend_flag(cuda, name)
        for name in (
            "flash_sdp_enabled",
            "math_sdp_enabled",
            "mem_efficient_sdp_enabled",
            "cudnn_sdp_enabled",
        )
    }
    hardware: list[dict[str, object]] = [
        {
            "type": "cpu",
            "name": platform.processor() or platform.machine() or "unknown",
            "machine": platform.machine() or "unknown",
        }
    ]
    if not cpu_only and torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            hardware.append(
                {
                    "type": "cuda",
                    "index": index,
                    "name": str(torch.cuda.get_device_name(index)),
                    "compute_capability": list(
                        torch.cuda.get_device_capability(index)
                    ),
                }
            )
    cpu_backend = getattr(torch.backends, "cpu", None)
    cpu_capability = getattr(cpu_backend, "get_cpu_capability", None)
    cpu_capability_name = (
        str(cpu_capability()) if callable(cpu_capability) else "unavailable"
    )
    cudnn = getattr(torch.backends, "cudnn", None)
    cudnn_version_fn = getattr(cudnn, "version", None)
    cudnn_version = cudnn_version_fn() if callable(cudnn_version_fn) else None
    cuda_matmul = getattr(cuda, "matmul", None)
    allow_tf32 = getattr(cuda_matmul, "allow_tf32", "unavailable")
    if not isinstance(allow_tf32, bool):
        allow_tf32 = "unavailable"
    matmul_precision_fn = getattr(torch, "get_float32_matmul_precision", None)
    matmul_precision = (
        str(matmul_precision_fn())
        if callable(matmul_precision_fn)
        else "unavailable"
    )
    actual_attention = str(
        getattr(model.config, "_attn_implementation", attention_implementation)
    )
    return {
        "producer": {
            "tool": ORACLE_TOOL,
            "tool_version": ORACLE_TOOL_VERSION,
            "source_sha256": hashlib.sha256(
                (REPO / ORACLE_TOOL).read_bytes()
            ).hexdigest(),
        },
        "framework": {
            "python_version": platform.python_version(),
            "torch_version": str(torch.__version__),
            "transformers_version": str(transformers.__version__),
        },
        "attention": {
            "requested_implementation": attention_implementation,
            "model_config_implementation": actual_attention,
            "sdpa_kernel_flags": sdpa_flags,
        },
        "device": {
            "placement_policy": "cpu" if cpu_only else "auto",
            "model_device": str(model.device),
            "model_device_map": _model_device_map(model),
            "hardware": hardware,
        },
        "backend": {
            "cuda_runtime_version": (
                str(torch.version.cuda) if torch.version.cuda is not None else "none"
            ),
            "cudnn_version": (
                str(cudnn_version) if cudnn_version is not None else "none"
            ),
            "cpu_capability": cpu_capability_name,
            "torch_build_config_sha256": hashlib.sha256(
                torch.__config__.show().encode("utf-8")
            ).hexdigest(),
            "torch_num_threads": int(torch.get_num_threads()),
            "torch_num_interop_threads": int(torch.get_num_interop_threads()),
            "thread_environment": {
                name: os.environ.get(name, "unset")
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                )
            },
        },
        "numeric": {
            "dtype": "bfloat16",
            "allow_tf32": allow_tf32,
            "float32_matmul_precision": matmul_precision,
        },
        "model_class": (
            f"{model.__class__.__module__}.{model.__class__.__qualname__}"
        ),
    }


def _prefill_association(
    execution_identity: Mapping[str, object],
    *,
    prompt_token_count: int,
    configured_chunk_tokens: int,
    mode: str,
) -> dict[str, object]:
    """Bind one result to the exact prefill partition and execution identity."""
    if mode == "chunked_forward_kv_cache":
        effective = min(configured_chunk_tokens, prompt_token_count)
        chunks = (
            prompt_token_count + configured_chunk_tokens - 1
        ) // configured_chunk_tokens
        cache_transport = "past_key_values"
    else:
        effective = prompt_token_count
        chunks = 1
        cache_transport = (
            "transformers_generate_cache"
            if mode == "generate_single_prefill"
            else "past_key_values"
        )
    association: dict[str, object] = {
        "schema": PREFILL_ASSOCIATION_SCHEMA,
        "association_policy": PREFILL_ASSOCIATION_POLICY,
        **execution_identity,
        "prefill": {
            "mode": mode,
            "configured_chunk_tokens": configured_chunk_tokens,
            "effective_chunk_tokens": effective,
            "chunk_count": chunks,
            "prompt_token_count": prompt_token_count,
            "cache_transport": cache_transport,
        },
    }
    association["identity_sha256"] = _prefill_association_digest(association)
    return association



def _chunked_greedy(model, input_ids, *, max_new_tokens, chunk, eos_ids):
    """Greedy decode with a chunked prefill.

    Feeding an 8,000-token prompt in one pass materialises an activation
    working set this GPU does not have spare beside its other tenants.  Chunking
    carries the KV cache forward instead, which bounds the working set to one
    chunk while attention still sees the full accumulated cache.  The BF16
    reduction association can nevertheless change with the chunk partition,
    so the oracle records that partition as part of its numerical identity.
    """
    import torch

    device = model.device
    ids = input_ids.to(device)
    past = None
    with torch.inference_mode():
        for start in range(0, ids.shape[1], chunk):
            piece = ids[:, start : start + chunk]
            out = model(input_ids=piece, past_key_values=past, use_cache=True)
            past = out.past_key_values
            if start % (chunk * 8) == 0:
                print(
                    f"  prefill {min(start + chunk, ids.shape[1])}/{ids.shape[1]}",
                    flush=True,
                )
        generated: list[int] = []
        logits = out.logits[:, -1, :]
        for _ in range(max_new_tokens):
            token = int(torch.argmax(logits[0]).item())
            generated.append(token)
            if token in eos_ids:
                break
            step = torch.tensor([[token]], dtype=torch.long, device=device)
            out = model(input_ids=step, past_key_values=past, use_cache=True)
            past = out.past_key_values
            logits = out.logits[:, -1, :]
    return generated


def _greedy(model, input_ids, *, max_new_tokens, eos_ids):
    """One greedy generation, EOS included in the returned ids.

    The device's generation policy is
    ``greedy_argmax_lowest_id_first_eos_v1`` with
    ``include_eos_in_output: true``, so the comparator must include it too --
    otherwise every EOS-terminated generation would differ from the
    accelerator's by exactly one trailing token and the difference would look
    like a divergence.
    """
    import torch

    ids = input_ids.to(model.device)
    generated: list[int] = []
    with torch.inference_mode():
        out = model(input_ids=ids, use_cache=True)
        past = out.past_key_values
        logits = out.logits[:, -1, :]
        for _ in range(max_new_tokens):
            token = int(torch.argmax(logits[0]).item())
            generated.append(token)
            if token in eos_ids:
                break
            step = torch.tensor([[token]], dtype=torch.long, device=model.device)
            out = model(input_ids=step, past_key_values=past, use_cache=True)
            past = out.past_key_values
            logits = out.logits[:, -1, :]
    return generated


def run_agent_episode_oracle(
    model,
    tokenizer,
    *,
    sandbox_files,
    system_prompt: str,
    task_prompt: str,
    enable_thinking: bool,
    max_turns: int,
    max_new_tokens: int,
    eos_ids: set[int],
    context_capacity: int,
) -> dict:
    """Drive the closed agent loop through the vendor model.

    This produces the *gold episode*: for every turn, the exact prompt token
    ids the loop rendered and the exact ids a faithful implementation decodes
    from them.  The accelerator then runs the same loop under its own power and
    is compared turn by turn -- both the prompt it built and the tokens it
    produced.  Comparing only the final answer would let an accelerator that
    decoded different text still agree by luck, because several commands sum a
    column.

    The oracle runs its own sandbox.  It is a separate execution of the same
    frozen protocol, not a recording replayed into the accelerator's loop.
    """
    import torch

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt},
    ]
    turns: list[dict] = []
    answer = None
    stop_reason = "max_turns"
    with Sandbox(sandbox_files) as sandbox:
        for index in range(max_turns):
            rendered, prompt_ids = render_agent_context(
                tokenizer, messages, enable_thinking=enable_thinking
            )
            budget = context_capacity - len(prompt_ids)
            if budget <= 0:
                stop_reason = "context_exhausted"
                break
            limit = min(max_new_tokens, budget)
            started = time.perf_counter()
            generated = _greedy(
                model,
                torch.tensor([prompt_ids], dtype=torch.long),
                max_new_tokens=limit,
                eos_ids=eos_ids,
            )
            elapsed = time.perf_counter() - started
            text = tokenizer.decode(generated, skip_special_tokens=True)
            thinking, visible = split_thinking(text)
            record = {
                "turn": index,
                "prompt_token_ids": prompt_ids,
                "prompt_token_count": len(prompt_ids),
                "rendered_prompt_sha256": hashlib.sha256(
                    rendered.encode()
                ).hexdigest(),
                "max_new_tokens": limit,
                "generated_token_ids": generated,
                "generated_token_count": len(generated),
                "generated_text": text,
                "thinking_text": thinking,
                "visible_text": visible,
                "stop_reason": (
                    "eos" if generated and generated[-1] in eos_ids else "max_new_tokens"
                ),
                "wall_seconds": round(elapsed, 3),
            }
            print(
                f"  turn {index}: {len(prompt_ids)} prompt, "
                f"{len(generated)} generated in {elapsed:.1f}s, "
                f"stop={record['stop_reason']}",
                flush=True,
            )
            print(f"    visible: {visible[:300]!r}", flush=True)
            try:
                parsed = parse_turn(visible)
            except AgentProtocolError as exc:
                record["outcome"] = "protocol_violation"
                record["protocol_violation"] = str(exc)
                turns.append(record)
                stop_reason = "protocol_violation"
                break
            record["parsed"] = parsed.to_dict()
            if parsed.kind == "answer":
                answer = parsed.answer
                record["outcome"] = "answered"
                turns.append(record)
                stop_reason = "answered"
                break
            if parsed.kind == "neither":
                record["outcome"] = "no_action"
                turns.append(record)
                stop_reason = "no_action"
                break
            observation = sandbox.run(parsed.command)
            record["outcome"] = "executed"
            record["observation"] = observation.to_dict()
            print(
                f"    ran {parsed.command!r} -> {observation.stdout.strip()!r}",
                flush=True,
            )
            turns.append(record)
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": observation.rendered()})
    return {
        "turns": turns,
        "turn_count": len(turns),
        "answer": answer,
        "stop_reason": stop_reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workloads", type=Path, default=DEFAULT_WORKLOADS
    )
    parser.add_argument(
        "--checkpoint-lock", type=Path, default=DEFAULT_CHECKPOINT_LOCK
    )
    parser.add_argument(
        "--exact-8k-construction",
        type=Path,
        default=DEFAULT_EXACT_8K_CONSTRUCTION,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results" / "abi3" / "qwen3_reference_oracle.json",
    )
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--gpu-gib", type=int, default=9)
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help=(
            "Run entirely on CPU. Slower, but immune to the GPU memory "
            "fluctuation caused by other tenants on this machine, which is what "
            "matters for a long-prefill oracle that must not be evicted."
        ),
    )
    parser.add_argument("--cpu-gib", type=int, default=80)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--agent-episode",
        action="append",
        default=None,
        metavar="WORKLOAD_ID",
        help=(
            "Treat this workload as the opening turn of a closed agent "
            "episode: drive the loop through the sandbox and record every "
            "turn's prompt and generated token ids, rather than generating "
            "once from a fixed prompt."
        ),
    )
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--context-capacity", type=int, default=8192)
    parser.add_argument(
        "--prefill-chunk",
        type=int,
        default=0,
        help=(
            "Feed the prompt in chunks of this many tokens, carrying the KV "
            "cache between chunks. Zero uses one pass. Chunking bounds the "
            "activation working set, which is what makes an 8,000-token "
            "prefill fit beside other tenants on this GPU. The configured and "
            "effective chunk geometry is recorded as association provenance "
            "because it can change BF16 reduction order."
        ),
    )
    parser.add_argument(
        "--attention-implementation",
        choices=("sdpa", "eager"),
        default="sdpa",
        help=(
            "Transformers attention implementation. The requested and effective "
            "values, SDPA backend flags, framework versions, and device identity "
            "are recorded with every result."
        ),
    )
    parser.add_argument(
        "--gate-1-production",
        action="store_true",
        help=(
            "run only the governed exact-8K Gate-1 workload after fully "
            "hashing the pinned checkpoint and reconstructing the prompt from "
            "its authenticated tokenizer, template, corpus, and semantic source"
        ),
    )
    args = parser.parse_args()

    gate_1_option_problems = _configure_gate_1_production(args)
    if gate_1_option_problems:
        parser.error("; ".join(gate_1_option_problems))
    if args.prefill_chunk < 0:
        parser.error("--prefill-chunk must be zero or a positive token count")

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    try:
        index, selected, bodies, input_identity = _load_selected_workloads(
            args.workloads, args.only
        )
        checkpoint_preflight = None
        authenticated_tokenizer = None
        if args.gate_1_production:
            checkpoint_preflight, authenticated_tokenizer = (
                _authenticate_gate_1_inputs(args, index, bodies, input_identity)
            )
    except (ArtifactError, OSError, ValueError) as exc:
        print(f"oracle input preflight failed: {exc}", file=sys.stderr)
        return 2

    # Model frameworks are deliberately imported only after the immutable
    # sources above have been authenticated.  A stale prompt or checkpoint must
    # fail before allocating model weights.
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from compiler.workloads.qwen3 import AGENT_SYSTEM, AGENT_TASK  # noqa: E402

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False
    )

    print(
        "loading Qwen3-8B in bfloat16 "
        + ("on CPU ..." if args.cpu_only else "with GPU/CPU sharding ..."),
        flush=True,
    )
    started = time.perf_counter()
    placement = (
        {"device_map": {"": "cpu"}}
        if args.cpu_only
        else {
            "device_map": "auto",
            "max_memory": {0: f"{args.gpu_gib}GiB", "cpu": f"{args.cpu_gib}GiB"},
        }
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(args.snapshot),
        dtype=torch.bfloat16,
        **placement,
        local_files_only=True,
        trust_remote_code=False,
        attn_implementation=args.attention_implementation,
    )
    model.eval()
    print(f"loaded in {time.perf_counter() - started:.1f}s", flush=True)

    execution_identity = _oracle_execution_identity(
        model,
        torch,
        transformers,
        cpu_only=args.cpu_only,
        attention_implementation=args.attention_implementation,
    )

    report = {
        "schema": "opentallas.abi3.reference_oracle.v1",
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
        ],
        "model_id": "qwen3-8b",
        "snapshot": str(args.snapshot),
        "tokenizer_sha256": index["tokenizer_sha256"],
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "dtype": "bfloat16",
        "selection": "greedy_lowest_token_id_argmax",
        "device_map": "cpu bfloat16" if args.cpu_only else "auto (gpu+cpu bfloat16)",
        "attention_implementation": args.attention_implementation,
        "producer": {
            "tool": ORACLE_TOOL,
            "tool_version": ORACLE_TOOL_VERSION,
            "command_argv": [ORACLE_TOOL, *sys.argv[1:]],
            "selected_workload_ids": [workload_id for workload_id, _ in selected],
        },
        "input_identity": input_identity,
        "production_checkpoint_preflight": checkpoint_preflight,
        "production_launch": (
            {
                "explicitly_requested": True,
                "contract": _gate_1_launch_contract(),
            }
            if args.gate_1_production
            else {"explicitly_requested": False}
        ),
        "results": {},
    }

    for wid, entry in selected:
        body = bodies[wid]
        ids = body["token_ids"]
        print(
            f"\n=== {wid} ({entry['kind']}, {len(ids)} prompt tokens, "
            f"max_new={entry['max_new_tokens']}) ===",
            flush=True,
        )
        input_ids = torch.tensor([ids], dtype=torch.long)
        step_started = time.perf_counter()
        eos_set = {151645, 151643}
        if tokenizer.eos_token_id is not None:
            eos_set.add(int(tokenizer.eos_token_id))
        if args.agent_episode and wid in args.agent_episode:
            metadata = body.get("metadata", {})
            episode = run_agent_episode_oracle(
                model,
                tokenizer,
                sandbox_files=metadata["sandbox_files"],
                system_prompt=AGENT_SYSTEM,
                task_prompt=AGENT_TASK,
                enable_thinking=bool(metadata.get("enable_thinking", False)),
                max_turns=int(metadata.get("max_turns", args.max_turns)),
                max_new_tokens=entry["max_new_tokens"],
                eos_ids=eos_set,
                context_capacity=args.context_capacity,
            )
            elapsed = time.perf_counter() - step_started
            first = episode["turns"][0] if episode["turns"] else {}
            if first.get("prompt_token_ids", ids) != ids:
                raise SystemExit(
                    f"{wid}: the episode's turn-0 prompt does not match the "
                    f"pinned workload prompt; the workload and the loop "
                    f"disagree about the opening context"
                )
            report["results"][wid] = {
                "kind": entry["kind"],
                "workload_digest": entry["digest"],
                "prompt_token_count": len(ids),
                "generated_token_ids": first.get("generated_token_ids", []),
                "generated_token_count": len(first.get("generated_token_ids", [])),
                "stop_reason": first.get("stop_reason", "none"),
                "raw_decoded_text": first.get("generated_text", ""),
                "visible_decoded_text": first.get("visible_text", ""),
                "wall_seconds": round(elapsed, 3),
                "episode": episode,
                "enable_thinking": bool(metadata.get("enable_thinking", False)),
                "prefill_association": _prefill_association(
                    execution_identity,
                    prompt_token_count=len(ids),
                    # run_agent_episode_oracle uses _greedy: one unchunked
                    # forward pass per turn.  Record the path actually run,
                    # irrespective of a chunk option used by other workloads.
                    configured_chunk_tokens=0,
                    mode="single_forward_kv_cache",
                ),
            }
            print(
                f"episode: {episode['turn_count']} turns in {elapsed:.1f}s, "
                f"stop={episode['stop_reason']}, answer={episode['answer']!r}",
                flush=True,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json(report))
            continue
        if args.prefill_chunk:
            generated = _chunked_greedy(
                model,
                input_ids,
                max_new_tokens=entry["max_new_tokens"],
                chunk=args.prefill_chunk,
                eos_ids=eos_set,
            )
        else:
            with torch.inference_mode():
                out = model.generate(
                    input_ids=input_ids.to(model.device),
                    max_new_tokens=entry["max_new_tokens"],
                    do_sample=False,
                    num_beams=1,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    return_dict_in_generate=True,
                    output_scores=False,
                )
            generated = out.sequences[0][len(ids) :].tolist()
        elapsed = time.perf_counter() - step_started
        if args.gate_1_production:
            _validate_gate_1_generation(generated, eos_ids=eos_set)
        text = tokenizer.decode(generated, skip_special_tokens=False)
        visible = tokenizer.decode(generated, skip_special_tokens=True)
        if authenticated_tokenizer is not None:
            authenticated_raw = authenticated_tokenizer.decode(
                generated, skip_special_tokens=False
            )
            authenticated_visible = authenticated_tokenizer.decode(
                generated, skip_special_tokens=True
            )
            if text != authenticated_raw or visible != authenticated_visible:
                raise OracleInputError(
                    "vendor and authenticated tokenizer decoding differ"
                )
        eos_ids = set(
            [tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else []
        )
        eos_ids |= {151645, 151643}
        stop = "eos" if generated and generated[-1] in eos_ids else "max_new_tokens"
        report["results"][wid] = {
            "kind": entry["kind"],
            "workload_digest": entry["digest"],
            "prompt_token_count": len(ids),
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": stop,
            "raw_decoded_text": text,
            "visible_decoded_text": visible,
            "wall_seconds": round(elapsed, 3),
            "prefill_association": _prefill_association(
                execution_identity,
                prompt_token_count=len(ids),
                configured_chunk_tokens=args.prefill_chunk,
                mode=(
                    "chunked_forward_kv_cache"
                    if args.prefill_chunk
                    else "generate_single_prefill"
                ),
            ),
        }
        print(f"generated {len(generated)} tokens in {elapsed:.1f}s, stop={stop}")
        print(f"first 24 ids: {generated[:24]}")
        print(f"text: {visible[:400]!r}", flush=True)
        if not args.gate_1_production:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json(report))

    if args.gate_1_production:
        try:
            publish_bytes_atomic_no_replace(args.output, canonical_json(report))
        except FileExistsError:
            print(
                f"refusing to replace concurrently published {args.output}",
                file=sys.stderr,
            )
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report))
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
