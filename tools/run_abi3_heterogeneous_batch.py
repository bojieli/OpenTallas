#!/usr/bin/env python3
"""Run one governed heterogeneous ABI 3.0 batch without publishing TPOT.

The request names one already-compiled deployment and B=1/2/4/8 genuinely
independent workload/reference pairs.  The deployment is loaded once; one
``BatchGenerationDriver`` drives one ``CycleBatchScheduler`` whose lanes share
immutable weights/constants and retain private mutable state.  Gold tokens are
loaded only for post-execution comparison and are never supplied to the device.

This runner owns Gate 1 evidence only.  It retains the target-cycle request and
token-commit ticks causally bound by ``CycleBatchScheduler``, but deliberately
does not convert them into seconds, TPOT, throughput, or a performance verdict.
Gate 2 stays blocked until ``check_abi3_correctness_qualified_tpot.py`` accepts
the exact records under an immutable execution release.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


CODE_REPO = Path(__file__).resolve().parents[1]
if str(CODE_REPO) not in sys.path:
    sys.path.insert(0, str(CODE_REPO))

from runtime.abi3.capability import (  # noqa: E402
    Capability,
    canonical_json,
    digest_of,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.records import EosReason  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.cycle.batch import CycleBatchScheduler  # noqa: E402
from runtime.cycle.machine import load_cost_table  # noqa: E402
from runtime.cycle.model import CycleModel  # noqa: E402
from runtime.driver import (  # noqa: E402
    BatchGenerationDriver,
    BatchGenerationRequest,
    validate_token_ids,
)
from runtime.evidence import check_token_legitimacy  # noqa: E402
from runtime.sim.backend import get_backend  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402


REQUEST_SCHEMA = "opentallas.abi3.heterogeneous_batch_request.v1"
EXECUTION_SCHEMA = "opentallas.abi3.heterogeneous_batch_execution.v1"
RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
REQUEST_SCHEMA_PATH = (
    CODE_REPO / "schemas/abi3/heterogeneous_batch_request_v1.schema.json"
)
EXECUTION_SCHEMA_PATH = (
    CODE_REPO / "schemas/abi3/heterogeneous_batch_execution_v1.schema.json"
)
RUNNER_PATH = "tools/run_abi3_heterogeneous_batch.py"
TPOT_CONSUMER = "tools/check_abi3_correctness_qualified_tpot.py"
ALLOWED_BATCH_SIZES = frozenset({1, 2, 4, 8})
OPTIONAL_UNIMPLEMENTED_ENGINES = frozenset({"SELECTION.SAMPLE"})

# Every source that can change ABI admission, functional tokens, shared-batch
# retirement, or modeled token-commit ticks.  A compiled deployment is bound
# separately by its three files and digest.
RUNTIME_SOURCE_PATHS = (
    RUNNER_PATH,
    "runtime/abi3/builder.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/request.py",
    "runtime/abi3/verifier.py",
    "runtime/cycle/batch.py",
    "runtime/cycle/fabric.py",
    "runtime/cycle/machine.py",
    "runtime/cycle/model.py",
    "runtime/driver.py",
    "runtime/evidence.py",
    "runtime/sim/backend.py",
    "runtime/sim/batch.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
    "runtime/sim/performance.py",
    "runtime/sim/weight_cache.py",
)


class GovernedBatchError(ValueError):
    """The batch request or its source identities cannot be trusted."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strict_json_loads(payload: str | bytes, *, source: object) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, value in pairs:
            if key in body:
                raise GovernedBatchError(f"duplicate JSON key {key!r} in {source}")
            body[key] = value
        return body

    def reject_constant(value: str) -> None:
        raise GovernedBatchError(f"non-finite JSON number {value!r} in {source}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=unique,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise GovernedBatchError(f"malformed JSON in {source}: {exc}") from exc


def _load_object(path: Path) -> dict[str, Any]:
    body = _strict_json_loads(path.read_bytes(), source=path)
    if not isinstance(body, dict):
        raise GovernedBatchError(f"{path} is not a JSON object")
    return body


def _schema_problems(body: object, path: Path, label: str) -> list[str]:
    schema = _load_object(path)
    Draft202012Validator.check_schema(schema)
    return [
        f"{label} schema violation at {error.json_path}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(body),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                error.message,
            ),
        )
    ]


def _integer(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _repo_member(
    repo: Path,
    raw: object,
    label: str,
    *,
    kind: str,
    allow_absolute: bool = False,
) -> Path:
    """Resolve one non-symlink repository member without path aliases."""

    if not isinstance(raw, (str, Path)) or not str(raw) or "\\" in str(raw):
        raise GovernedBatchError(f"{label} is not a canonical repository path")
    supplied = Path(raw)
    if supplied.is_absolute() and not allow_absolute:
        raise GovernedBatchError(f"{label} must be repository-relative")
    if ".." in supplied.parts:
        raise GovernedBatchError(f"{label} contains a parent traversal")
    root = repo.resolve()
    unresolved = supplied if supplied.is_absolute() else root / supplied
    lexical = Path(os.path.abspath(unresolved))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise GovernedBatchError(f"{label} escapes the repository") from exc
    if not relative.parts:
        raise GovernedBatchError(f"{label} is not a repository member")
    cursor = root
    for component in relative.parts:
        cursor /= component
        if cursor.is_symlink():
            raise GovernedBatchError(f"{label} traverses a symlink")
        if not cursor.exists():
            break
    path = lexical.resolve(strict=False)
    if kind == "file" and not path.is_file():
        raise GovernedBatchError(f"{label} is not a file")
    if kind == "directory" and not path.is_dir():
        raise GovernedBatchError(f"{label} is not a directory")
    if kind == "absent" and (path.exists() or path.is_symlink()):
        raise GovernedBatchError(f"{label} already exists; publication is create-once")
    return path


def _display(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _file_ref(raw: object, label: str, repo: Path) -> tuple[Path, dict[str, str]]:
    if not isinstance(raw, Mapping):
        raise GovernedBatchError(f"{label} is not a file identity")
    path = _repo_member(repo, raw.get("path"), label, kind="file")
    expected = raw.get("sha256")
    actual = _sha256(path)
    if expected != actual:
        raise GovernedBatchError(
            f"{label} SHA-256 mismatch: expected {expected}, observed {actual}"
        )
    return path, {"path": _display(path, repo), "sha256": actual}


def _workload_digest(workload: Mapping[str, Any]) -> str:
    payload = json.dumps(
        {
            "workload_id": workload.get("workload_id"),
            "kind": workload.get("kind"),
            "token_ids": workload.get("token_ids"),
            "max_new_tokens": workload.get("max_new_tokens"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_sha256() -> dict[str, str]:
    paths = {
        *(CODE_REPO / relative for relative in RUNTIME_SOURCE_PATHS),
        *(CODE_REPO / "runtime/sim/engines").glob("*.py"),
    }
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise GovernedBatchError(
            "runtime source boundary is incomplete: "
            + ", ".join(str(path) for path in sorted(missing))
        )
    return {
        path.relative_to(CODE_REPO).as_posix(): _sha256(path)
        for path in sorted(paths)
    }


def _source_repository(source_paths: Sequence[str]) -> dict[str, Any]:
    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=CODE_REPO,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    try:
        commit = git("rev-parse", "--verify", "HEAD^{commit}")
        tree = git("rev-parse", "HEAD^{tree}")
        status = git("status", "--porcelain=v1", "--untracked-files=no")
        tracked = set(git("ls-files", "-z").split("\0"))
    except (OSError, subprocess.CalledProcessError):
        return {
            "commit": None,
            "tree": None,
            "tracked_worktree_clean": False,
            "sources_tracked": False,
        }
    return {
        "commit": commit,
        "tree": tree,
        "tracked_worktree_clean": not bool(status),
        "sources_tracked": all(path in tracked for path in source_paths),
    }


def _implementation_identity() -> dict[str, Any]:
    try:
        identity = dict(get_backend().implementation_identity())
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        identity = {"unavailable": f"{type(exc).__name__}: {exc}"}
    identity["tokenizers_version"] = importlib.metadata.version("tokenizers")
    return identity


def _decode(tokenizer: Any, token_ids: Sequence[int], *, special: bool) -> str:
    try:
        return str(
            tokenizer.decode(
                [int(token) for token in token_ids],
                skip_special_tokens=not special,
            )
        )
    except Exception as exc:
        raise GovernedBatchError(
            f"authenticated tokenizer cannot decode token IDs: {exc}"
        ) from exc


def _comparison(got: Sequence[int], gold: Sequence[int]) -> dict[str, Any]:
    common = min(len(got), len(gold))
    first = next(
        (index for index in range(common) if int(got[index]) != int(gold[index])),
        None,
    )
    if first is None and len(got) != len(gold):
        first = common
    divergence = None
    if first is not None:
        divergence = {
            "index": first,
            "accelerator_token_id": int(got[first]) if first < len(got) else None,
            "oracle_token_id": int(gold[first]) if first < len(gold) else None,
        }
    return {
        "agreement": bool(got) and list(got) == list(gold),
        "compared_token_count": common,
        "first_divergence_index": first,
        "first_divergence": divergence,
    }


def _terminal_evidence(
    *,
    generated: Sequence[int],
    stop_reason: str,
    oracle_stop_reason: str,
    max_new_tokens: int,
    eos_token_ids: Sequence[int],
    per_step: Sequence[Mapping[str, Any]],
    scheduler_sequence: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    eos = {int(token) for token in eos_token_ids}
    first_eos = next(
        (index for index, token in enumerate(generated) if int(token) in eos), None
    )
    exact_eos = bool(
        stop_reason == "eos"
        and oracle_stop_reason == "eos"
        and first_eos == len(generated) - 1
    )
    exact_cap = bool(
        stop_reason == "max_new_tokens"
        and oracle_stop_reason == "max_new_tokens"
        and len(generated) == max_new_tokens
        and first_eos is None
    )
    no_post = bool(
        scheduler_sequence.get("no_post_eos_transaction") is True
        and scheduler_sequence.get("post_retirement_transaction_count") == 0
    )
    per_step_exact = bool(
        len(per_step) == len(generated)
        and all(
            step.get("step") == index
            and step.get("produced_tokens") == [int(generated[index])]
            and step.get("final_token_id") == int(generated[index])
            and step.get("status") == "SUCCESS"
            and step.get("trap") == "NONE"
            for index, step in enumerate(per_step)
        )
    )
    checks = {
        "device_terminal_reason_matches_oracle": stop_reason == oracle_stop_reason,
        "eos_or_exact_cap": exact_eos or exact_cap,
        "no_post_terminal_execution": no_post,
        "one_successful_step_per_token": per_step_exact,
    }
    problems = [name for name, passed in checks.items() if not passed]
    return (
        {
            "accepted": not problems,
            "terminal_kind": "eos" if exact_eos else "cap" if exact_cap else None,
            "first_eos_index": first_eos,
            "exact_cap": exact_cap,
            "no_post_terminal_execution": no_post,
            "checks": checks,
            "failed_checks": problems,
        },
        problems,
    )


def _timing_evidence(
    *,
    lane: int,
    generated: Sequence[int],
    generation: Any,
    scheduler_sequence: Mapping[str, Any],
    scheduler: CycleBatchScheduler,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    records = sorted(
        (record for record in scheduler.timing_records if record.lane_index == lane),
        key=lambda record: record.wave_index,
    )
    commits = [int(record.token_commit_tick) for record in records]
    transactions = [int(record.transaction_id) for record in records]
    starts = [int(record.request_start_tick) for record in records]
    per_step = generation.per_step
    problems: list[str] = []
    expected_commits = [
        step.get("completion_timestamp")
        for step in per_step
        if isinstance(step, Mapping)
    ]
    expected_transactions = [
        step.get("transaction_id") for step in per_step if isinstance(step, Mapping)
    ]
    if len(records) != len(generated):
        problems.append("bound timing record count differs from generated tokens")
    if [record.produced_token_id for record in records] != list(generated):
        problems.append("bound timing record tokens differ from generated tokens")
    if commits != expected_commits or commits != scheduler_sequence.get(
        "token_commit_ticks"
    ):
        problems.append("raw token-commit ticks differ across execution bindings")
    if transactions != expected_transactions or transactions != scheduler_sequence.get(
        "transaction_ids"
    ):
        problems.append("transaction IDs differ across execution bindings")
    if not starts or generation.request_start_tick != starts[0]:
        problems.append("fresh request-start tick differs across execution bindings")
    if any(right <= left for left, right in zip(commits, commits[1:])):
        problems.append("raw token-commit ticks are not strictly increasing")
    timing = {
        "clock_domain": "abi3_device_cycle_counter",
        "request_start_tick": starts[0] if starts else 0,
        "token_commit_ticks": commits,
        "transaction_ids": transactions,
        "same_execution_bindings_complete": not problems,
        "target_performance_interpretation": False,
    }
    bindings = [
        {
            "wave_index": int(record.wave_index),
            "transaction_id": int(record.transaction_id),
            "produced_token_id": int(record.produced_token_id),
            "eos_reason": int(record.eos_reason),
            "request_start_tick": int(record.request_start_tick),
            "token_commit_tick": int(record.token_commit_tick),
            "completion_digest": record.completion_digest,
            "functional_result_digest": record.functional_result_digest,
            "trace_digest": record.trace_digest,
        }
        for record in records
    ]
    return timing, bindings, problems


def _load_tokenizer(path: Path) -> Any:
    try:
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(path))
    except Exception as exc:
        raise GovernedBatchError(f"cannot load authenticated tokenizer: {exc}") from exc
    if tokenizer.get_vocab_size(with_added_tokens=True) < 1:
        raise GovernedBatchError("authenticated tokenizer has an empty vocabulary")
    return tokenizer


def _load_pairs(
    request: Mapping[str, Any],
    *,
    repo: Path,
    tokenizer: Any,
    tokenizer_sha256: str,
) -> tuple[list[dict[str, Any]], list[tuple[Path, str]]]:
    pairs: list[dict[str, Any]] = []
    stable_files: list[tuple[Path, str]] = []
    for index, sequence_spec in enumerate(request["sequences"]):
        workload_path, workload_file = _file_ref(
            sequence_spec["workload"], f"sequences[{index}].workload", repo
        )
        reference_path, reference_file = _file_ref(
            sequence_spec["reference"], f"sequences[{index}].reference", repo
        )
        stable_files.extend(
            [
                (workload_path, workload_file["sha256"]),
                (reference_path, reference_file["sha256"]),
            ]
        )
        workload = _load_object(workload_path)
        required_workload = {
            "workload_id",
            "kind",
            "digest",
            "prompt_token_count",
            "max_new_tokens",
            "rendered_text_sha256",
            "token_ids",
            "rendered_text",
        }
        if not required_workload <= set(workload):
            missing = sorted(required_workload - set(workload))
            raise GovernedBatchError(
                f"sequences[{index}] workload is missing {missing}"
            )
        prompt = workload["token_ids"]
        if (
            not isinstance(prompt, list)
            or not prompt
            or any(not _integer(token) for token in prompt)
            or workload.get("prompt_token_count") != len(prompt)
        ):
            raise GovernedBatchError(
                f"sequences[{index}] workload prompt IDs are incomplete or illegal"
            )
        if workload.get("digest") != _workload_digest(workload):
            raise GovernedBatchError(
                f"sequences[{index}] workload semantic digest is inconsistent"
            )
        rendered = workload.get("rendered_text")
        if not isinstance(rendered, str) or _text_sha256(rendered) != workload.get(
            "rendered_text_sha256"
        ):
            raise GovernedBatchError(
                f"sequences[{index}] workload rendered-text identity is inconsistent"
            )
        if not _integer(workload.get("max_new_tokens"), minimum=1):
            raise GovernedBatchError(
                f"sequences[{index}] workload max_new_tokens is invalid"
            )
        decoded_prompt = _decode(tokenizer, prompt, special=True)
        try:
            encoded_prompt = list(
                tokenizer.encode(rendered, add_special_tokens=False).ids
            )
        except Exception as exc:
            raise GovernedBatchError(
                f"sequences[{index}] tokenizer cannot re-encode rendered prompt: {exc}"
            ) from exc
        if decoded_prompt != rendered or encoded_prompt != prompt:
            raise GovernedBatchError(
                f"sequences[{index}] workload does not round-trip through the "
                "authenticated tokenizer"
            )

        reference = _load_object(reference_path)
        if reference.get("schema") != "opentallas.abi3.reference_oracle.v1":
            raise GovernedBatchError(
                f"sequences[{index}] reference is not an ABI 3.0 external oracle"
            )
        if reference.get("model_id") != request["model"]["model_id"]:
            raise GovernedBatchError(
                f"sequences[{index}] reference names a different model"
            )
        if reference.get("tokenizer_sha256") != tokenizer_sha256:
            raise GovernedBatchError(
                f"sequences[{index}] reference names a different tokenizer"
            )
        results = reference.get("results")
        workload_id = workload.get("workload_id")
        if not isinstance(results, Mapping) or workload_id not in results:
            raise GovernedBatchError(
                f"sequences[{index}] reference has no result for {workload_id!r}"
            )
        oracle = results[workload_id]
        if not isinstance(oracle, Mapping):
            raise GovernedBatchError(
                f"sequences[{index}] oracle result is not an object"
            )
        gold = oracle.get("generated_token_ids")
        if (
            not isinstance(gold, list)
            or not gold
            or any(not _integer(token) for token in gold)
            or oracle.get("generated_token_count") != len(gold)
            or oracle.get("workload_digest") != workload.get("digest")
            or oracle.get("prompt_token_count") != len(prompt)
            or oracle.get("stop_reason") not in {"eos", "max_new_tokens"}
        ):
            raise GovernedBatchError(
                f"sequences[{index}] oracle result is incomplete or bound to a "
                "different workload"
            )
        raw_text = oracle.get("raw_decoded_text")
        visible_text = oracle.get("visible_decoded_text")
        if (
            not isinstance(raw_text, str)
            or not isinstance(visible_text, str)
            or raw_text != _decode(tokenizer, gold, special=True)
            or visible_text != _decode(tokenizer, gold, special=False)
        ):
            raise GovernedBatchError(
                f"sequences[{index}] oracle decoded text is inconsistent with its "
                "authenticated token IDs"
            )
        pairs.append(
            {
                "sequence_id": sequence_spec["sequence_id"],
                "terminal_contract": sequence_spec["terminal_contract"],
                "workload_path": workload_path,
                "workload_file": workload_file,
                "workload": workload,
                "prompt": [int(token) for token in prompt],
                "prompt_decoded": decoded_prompt,
                "prompt_sha256": digest_of(prompt),
                "reference_path": reference_path,
                "reference_file": reference_file,
                "reference": reference,
                "oracle": dict(oracle),
                "oracle_sha256": digest_of(dict(oracle)),
                "gold": [int(token) for token in gold],
            }
        )

    uniqueness = {
        "sequence IDs": [pair["sequence_id"] for pair in pairs],
        "workload files": [str(pair["workload_path"]) for pair in pairs],
        "workload IDs": [pair["workload"]["workload_id"] for pair in pairs],
        "workload digests": [pair["workload"]["digest"] for pair in pairs],
        "prompt token identities": [pair["prompt_sha256"] for pair in pairs],
        "oracle result identities": [pair["oracle_sha256"] for pair in pairs],
    }
    for label, values in uniqueness.items():
        if len(set(values)) != len(values):
            raise GovernedBatchError(
                f"heterogeneous batch does not have independent {label}"
            )
    return pairs, stable_files


def _stable(paths: Sequence[tuple[Path, str]]) -> bool:
    return all(path.is_file() and _sha256(path) == expected for path, expected in paths)


def _immutable_manifest(
    deployment: Deployment, object_ids: Sequence[int]
) -> tuple[list[dict[str, Any]], str]:
    rows = [
        {
            "object_id": int(object_id),
            "source": deployment.objects[int(object_id)].to_dict(),
        }
        for object_id in sorted(set(int(value) for value in object_ids))
    ]
    return rows, digest_of(rows)


def execute_request_file(
    request_path: Path,
    *,
    repo: Path,
    output_directory: Path,
) -> tuple[dict[str, Any], Path]:
    """Execute, validate, and create-once publish one governed batch."""

    root = Path(repo).resolve()
    request_file = _repo_member(
        root,
        request_path,
        "batch request",
        kind="file",
        allow_absolute=True,
    )
    request_sha = _sha256(request_file)
    request = _load_object(request_file)
    schema_problems = _schema_problems(
        request, REQUEST_SCHEMA_PATH, "heterogeneous batch request"
    )
    if schema_problems:
        raise GovernedBatchError("; ".join(schema_problems))
    if request.get("schema") != REQUEST_SCHEMA:
        raise GovernedBatchError("unsupported heterogeneous batch request schema")
    batch_size = int(request["batch_size"])
    if batch_size not in ALLOWED_BATCH_SIZES or len(request["sequences"]) != batch_size:
        raise GovernedBatchError(
            "batch_size must be B=1/2/4/8 and equal the sequence count"
        )
    output = _repo_member(
        root,
        output_directory,
        "batch output directory",
        kind="absent",
        allow_absolute=True,
    )

    stable_files: list[tuple[Path, str]] = [(request_file, request_sha)]
    capability_path, capability_file = _file_ref(
        request["capability"], "capability", root
    )
    cost_path, cost_file = _file_ref(request["cost_table"], "cost table", root)
    checkpoint_lock_path, checkpoint_lock_file = _file_ref(
        request["checkpoint_lock"], "checkpoint lock", root
    )
    _load_object(checkpoint_lock_path)
    checkpoint_root = _repo_member(
        root, request["checkpoint_root"], "checkpoint root", kind="directory"
    )
    tokenizer_path, tokenizer_file = _file_ref(
        request["tokenizer"], "tokenizer", root
    )
    deployment_files: dict[str, tuple[Path, dict[str, str]]] = {}
    for name in ("manifest", "descriptors", "program"):
        deployment_files[name] = _file_ref(
            request["deployment"][name], f"deployment {name}", root
        )
    deployment_roots = {path.parent for path, _identity in deployment_files.values()}
    if len(deployment_roots) != 1:
        raise GovernedBatchError("deployment files do not share one bundle root")
    deployment_root = next(iter(deployment_roots))
    expected_names = {
        "manifest": "deployment.json",
        "descriptors": "descriptors.bin",
        "program": "program.bin",
    }
    for name, expected_name in expected_names.items():
        if deployment_files[name][0].name != expected_name:
            raise GovernedBatchError(
                f"deployment {name} must name {expected_name}, not "
                f"{deployment_files[name][0].name}"
            )
    stable_files.extend(
        [
            (capability_path, capability_file["sha256"]),
            (cost_path, cost_file["sha256"]),
            (checkpoint_lock_path, checkpoint_lock_file["sha256"]),
            (tokenizer_path, tokenizer_file["sha256"]),
            *(
                (path, identity["sha256"])
                for path, identity in deployment_files.values()
            ),
        ]
    )

    capability = Capability.from_dict(_load_object(capability_path))
    cost_table = load_cost_table(cost_path)
    deployment = Deployment.read(deployment_root)
    target = request["target"]
    model = request["model"]
    expected_target = {
        "target_id": deployment.target_id,
        "backend": deployment.backend,
        "topology_class": int(deployment.topology_class),
        "technology_view": capability.technology_view,
    }
    for name, expected in expected_target.items():
        if target.get(name) != expected:
            raise GovernedBatchError(
                f"request target.{name} differs from the compiled deployment"
            )
    if deployment.capability_digest != capability.digest:
        raise GovernedBatchError("compiled deployment binds a different capability")
    if deployment.model_id != model.get("model_id"):
        raise GovernedBatchError("request model differs from the compiled deployment")
    if cost_table.technology_view != capability.technology_view:
        raise GovernedBatchError(
            "cost table and capability do not use one technology view"
        )
    if request["execution_scope"] == "full_model":
        source = deployment.source_identity
        if (
            source.get("graph_id") != model.get("graph_id")
            or source.get("model_id") != model.get("model_id")
            or "fixture" in source
        ):
            raise GovernedBatchError(
                "full-model request is not bound to the compiled graph identity"
            )

    tokenizer = _load_tokenizer(tokenizer_path)
    pairs, pair_files = _load_pairs(
        request,
        repo=root,
        tokenizer=tokenizer,
        tokenizer_sha256=tokenizer_file["sha256"],
    )
    stable_files.extend(pair_files)

    report = verify_deployment(deployment, capability)
    if not report.admitted:
        raise GovernedBatchError(
            "compiled deployment failed independent ABI admission: "
            + "; ".join(report.errors)
        )
    coverage = load_engines()
    required_missing = sorted(
        set(coverage["missing"]) - OPTIONAL_UNIMPLEMENTED_ENGINES
    )
    if required_missing:
        raise GovernedBatchError(
            "required functional engines are unavailable: "
            + ", ".join(required_missing)
        )

    source_sha = _source_sha256()
    source_repository = _source_repository(tuple(source_sha))
    source_before = dict(source_sha)
    numeric_backend = get_backend()
    numeric_backend.reset_executed_associations()
    cycle_model = CycleModel(
        deployment,
        capability,
        cost_table,
        root=checkpoint_root,
    )
    scheduler = CycleBatchScheduler(cycle_model, batch_size)
    if scheduler.device.node_count != target.get("node_count"):
        raise GovernedBatchError(
            "request target.node_count differs from the compiled topology"
        )
    driver = BatchGenerationDriver(scheduler)
    tokenizer_vocabulary = tokenizer.get_vocab_size(with_added_tokens=True)
    if tokenizer_vocabulary > driver.vocabulary_size:
        raise GovernedBatchError(
            "authenticated tokenizer vocabulary exceeds the deployment policy"
        )
    for index, pair in enumerate(pairs):
        illegal_prompt = validate_token_ids(pair["prompt"], tokenizer_vocabulary)
        illegal_gold = validate_token_ids(pair["gold"], tokenizer_vocabulary)
        if illegal_prompt or illegal_gold:
            raise GovernedBatchError(
                f"sequences[{index}] has tokenizer-illegal prompt/oracle IDs: "
                + "; ".join([*illegal_prompt, *illegal_gold])
            )
        if pair["workload"]["max_new_tokens"] > int(driver.policy["max_new_tokens"]):
            raise GovernedBatchError(
                f"sequences[{index}] output cap exceeds the deployment policy"
            )

    result = driver.generate_batch(
        tuple(
            BatchGenerationRequest(
                sequence_id=pair["sequence_id"],
                prompt_token_ids=tuple(pair["prompt"]),
                max_new_tokens=int(pair["workload"]["max_new_tokens"]),
            )
            for pair in pairs
        )
    )
    expected_tokens = [pair["gold"] for pair in pairs]
    expected_eos = [
        EosReason.OFFICIAL_EOS
        if pair["oracle"]["stop_reason"] == "eos"
        else EosReason.MAX_NEW_TOKENS
        for pair in pairs
    ]
    scheduler_evidence = scheduler.evidence(
        expected_tokens,
        expected_eos_reasons=expected_eos,
        full_model_execution=request["execution_scope"] == "full_model",
    )
    scheduler_sequences = scheduler_evidence["sequences"]
    source_after = _source_sha256()
    source_stable = source_before == source_after and _stable(stable_files)
    executed_association = numeric_backend.executed_association_manifest()
    implementation = _implementation_identity()

    memory_contract = scheduler.memory_contract
    shared_ids = list(memory_contract.get("shared_immutable_object_ids", []))
    immutable_rows, immutable_digest = _immutable_manifest(deployment, shared_ids)
    shared_exact = bool(
        memory_contract.get("immutable_objects_are_shared") is True
        and memory_contract.get("mutable_objects_are_session_private") is True
        and shared_ids
        and len(result.sequences) == batch_size
        and result.physical_batch_size == batch_size
        and result.batch_execution_id == scheduler.batch_execution_id
    )

    sequence_records: list[dict[str, Any]] = []
    sequence_rows: list[dict[str, Any]] = []
    all_sequence_problems: list[str] = []
    for lane, (pair, sequence, scheduler_sequence) in enumerate(
        zip(pairs, result.sequences, scheduler_sequences, strict=True)
    ):
        generation = sequence.generation
        got = [int(token) for token in generation.generated_token_ids]
        legitimacy = check_token_legitimacy(
            got,
            vocabulary_size=tokenizer_vocabulary,
            eos_token_ids=driver.eos_token_ids,
            stop_reason=generation.stop_reason,
        )
        legitimacy.extend(validate_token_ids(got, tokenizer_vocabulary))
        comparison = _comparison(got, pair["gold"])
        raw_text = _decode(tokenizer, got, special=True)
        visible_text = _decode(tokenizer, got, special=False)
        text_evidence = {
            "tokenizer_sha256": tokenizer_file["sha256"],
            "input_rendered_text": pair["workload"]["rendered_text"],
            "input_decode_matches_rendered_text": (
                pair["prompt_decoded"] == pair["workload"]["rendered_text"]
            ),
            "input_encode_round_trip_matches_ids": True,
            "raw_decoded_text": raw_text,
            "visible_decoded_text": visible_text,
            "raw_matches_oracle": raw_text
            == pair["oracle"]["raw_decoded_text"],
            "visible_matches_oracle": visible_text
            == pair["oracle"]["visible_decoded_text"],
        }
        terminal, terminal_problems = _terminal_evidence(
            generated=got,
            stop_reason=generation.stop_reason,
            oracle_stop_reason=pair["oracle"]["stop_reason"],
            max_new_tokens=int(pair["workload"]["max_new_tokens"]),
            eos_token_ids=driver.eos_token_ids,
            per_step=generation.per_step,
            scheduler_sequence=scheduler_sequence,
        )
        timing, timing_bindings, timing_problems = _timing_evidence(
            lane=lane,
            generated=got,
            generation=generation,
            scheduler_sequence=scheduler_sequence,
            scheduler=scheduler,
        )
        sequence_problems = [
            *(f"token legitimacy: {problem}" for problem in legitimacy),
            *(f"terminal: {problem}" for problem in terminal_problems),
            *(f"timing: {problem}" for problem in timing_problems),
        ]
        if not comparison["agreement"]:
            sequence_problems.append("generated tokens differ from the complete oracle")
        if not text_evidence["raw_matches_oracle"]:
            sequence_problems.append("raw decoded text differs from the oracle")
        if not text_evidence["visible_matches_oracle"]:
            sequence_problems.append("visible decoded text differs from the oracle")
        if generation.failure is not None:
            sequence_problems.append(f"driver failure: {generation.failure}")
        passes = not sequence_problems
        all_sequence_problems.extend(
            f"sequence {lane}: {problem}" for problem in sequence_problems
        )
        oracle_evidence = {
            "file": pair["reference_file"],
            "result_sha256": pair["oracle_sha256"],
            "generated_token_ids": pair["gold"],
            "stop_reason": pair["oracle"]["stop_reason"],
            "raw_decoded_text": pair["oracle"]["raw_decoded_text"],
            "visible_decoded_text": pair["oracle"]["visible_decoded_text"],
            **comparison,
        }
        architectural_steps = [
            {
                key: value
                for key, value in step.items()
                if key not in {"wall_seconds", "host_performance"}
            }
            for step in generation.per_step
        ]
        record = {
            "schema": RECORD_SCHEMA,
            "status": "pass" if passes else "diverged",
            "evidence_class": "functional_artifact_only",
            "tool": RUNNER_PATH,
            "backend": target["backend"],
            "target": {
                **target,
                "capability_digest": capability.digest,
                "deployment_digest": deployment.deployment_digest.hex(),
            },
            "model": dict(model),
            "workload": {
                "workload_id": pair["workload"]["workload_id"],
                "workload_digest": pair["workload"]["digest"],
                "prompt_token_ids": pair["prompt"],
                "prompt_token_count": len(pair["prompt"]),
                "max_new_tokens": pair["workload"]["max_new_tokens"],
                "rendered_text_sha256": pair["workload"]["rendered_text_sha256"],
                "prompt_token_ids_sha256": pair["prompt_sha256"],
                "tokenizer_sha256": tokenizer_file["sha256"],
            },
            "generation_policy": dict(driver.policy),
            "generation_policy_digest": digest_of(driver.policy),
            "verification": report.to_dict(),
            "engine_coverage": {
                "implemented_count": coverage["implemented_count"],
                "missing_count": coverage["missing_count"],
                "missing": list(coverage["missing"]),
            },
            "implementation_identity": implementation,
            "executed_association": executed_association,
            "source_sha256": source_after,
            "inputs": {
                "workload": pair["workload_file"],
                "reference": pair["reference_file"],
                "reference_result_sha256": pair["oracle_sha256"],
                "tokenizer": tokenizer_file,
                "checkpoint_lock": checkpoint_lock_file,
            },
            "shared_execution": {
                "deployment_digest": deployment.deployment_digest.hex(),
                "batch_execution_id": result.batch_execution_id,
                "physical_batch_size": batch_size,
                "shared_immutable_object_ids": shared_ids,
                "immutable_source_manifest_sha256": immutable_digest,
            },
            "generated_token_ids": got,
            "generated_token_count": len(got),
            "stop_reason": generation.stop_reason,
            "failure": generation.failure,
            "token_ids_legal": not legitimacy,
            "token_legitimacy_problems": legitimacy,
            "oracle": {
                "artifact": pair["reference_file"]["path"],
                "artifact_sha256": pair["reference_file"]["sha256"],
                "evidence_class": "external_reference_comparator",
                "generated_token_ids": pair["gold"],
                "agreement": comparison["agreement"],
                "first_divergence_index": comparison["first_divergence_index"],
                "divergence": comparison["first_divergence"],
                "compared_tokens": comparison["compared_token_count"],
                "oracle_token_count": len(pair["gold"]),
            },
            "terminal_acceptance": terminal,
            "text_evidence": text_evidence,
            "counters": dict(sorted(generation.counters.items())),
            "per_step": architectural_steps,
            "execution_timing": {
                "schema": "opentallas.abi3.execution_token_commit_timing.v1",
                "unit": "cycles",
                "clock_domain": timing["clock_domain"],
                "request_start_tick": timing["request_start_tick"],
                "request_start_source": (
                    "driver_counter_before_fresh_prefill_submission"
                ),
                "token_commit_ticks": timing["token_commit_ticks"],
                "token_commit_source": (
                    "decoded_abi3_completion.completion_timestamp"
                ),
                "token_commits_from_execution": timing[
                    "same_execution_bindings_complete"
                ],
                "bindings": timing_bindings,
                "problems": timing_problems,
            },
        }
        if batch_size > 1:
            record["batch_execution"] = {
                "schema": "opentallas.abi3.accelerator_batch_execution_member.v1",
                "batch_execution_id": result.batch_execution_id,
                "batch_size": batch_size,
                "sequence_index": lane,
                "shared_execution": True,
            }
        sequence_records.append(record)
        sequence_rows.append(
            {
                "sequence_index": lane,
                "sequence_id": pair["sequence_id"],
                "workload": {
                    "file": pair["workload_file"],
                    "workload_id": pair["workload"]["workload_id"],
                    "kind": pair["workload"]["kind"],
                    "digest": pair["workload"]["digest"],
                    "prompt_token_ids": pair["prompt"],
                    "prompt_token_count": len(pair["prompt"]),
                    "prompt_token_ids_sha256": pair["prompt_sha256"],
                    "max_new_tokens": pair["workload"]["max_new_tokens"],
                    "rendered_text_sha256": pair["workload"][
                        "rendered_text_sha256"
                    ],
                },
                "generated_token_ids": got,
                "generated_token_count": len(got),
                "stop_reason": generation.stop_reason,
                "token_ids_legal": not legitimacy,
                "token_legitimacy_problems": legitimacy,
                "decoded_text": text_evidence,
                "oracle": oracle_evidence,
                "terminal": terminal,
                "execution_timing": timing,
                "passes": passes,
                "problems": sequence_problems,
                # Filled with a content identity before publication.
                "record": {},
            }
        )

    scheduler_gate = scheduler_evidence["acceptance_gates"]["gate1_correctness"]
    scheduler_exact = bool(
        scheduler_gate.get("exact_token_equality") is True
        and scheduler_gate.get("exact_eos_equality") is True
        and scheduler_gate.get("all_lanes_terminal") is True
        and scheduler_gate.get("same_execution_timing_records_complete") is True
    )
    global_problems = list(all_sequence_problems)
    global_problems.extend(
        f"scheduler: {problem}" for problem in scheduler_evidence.get("problems", [])
    )
    if not shared_exact:
        global_problems.append(
            "one deployment/shared immutable and private mutable memory contract failed"
        )
    if not source_stable:
        global_problems.append(
            "governed inputs or runtime sources changed during execution"
        )
    if not scheduler_exact:
        global_problems.append("cycle scheduler did not bind exact tokens/EOS/ticks")
    full_model = request["execution_scope"] == "full_model"
    if full_model and scheduler_gate.get("status") != "pass":
        global_problems.append("cycle scheduler did not qualify a full-model Gate 1 run")
    if full_model and not (
        source_repository["tracked_worktree_clean"]
        and source_repository["sources_tracked"]
    ):
        global_problems.append(
            "full-model Gate 1 requires clean, committed runtime sources"
        )
    gate1_pass = not global_problems

    record_bytes = [canonical_json(record) for record in sequence_records]
    for lane, payload in enumerate(record_bytes):
        record_path = output / f"sequence-{lane}.json"
        sequence_rows[lane]["record"] = {
            "path": _display(record_path, root),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    request_identity = {
        "path": _display(request_file, root),
        "sha256": request_sha,
        "semantic_sha256": digest_of(request),
    }
    body = {
        "schema": EXECUTION_SCHEMA,
        "abi_version": "3.0",
        "status": "pass" if gate1_pass else "failed",
        "campaign_id": request["campaign_id"],
        "execution_scope": request["execution_scope"],
        "request": request_identity,
        "physical_batch_size": batch_size,
        "batch_execution_id": result.batch_execution_id,
        "model": dict(model),
        "target": {
            **target,
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
        },
        "shared_execution": {
            "deployment_loaded_once": True,
            "one_physical_batch": True,
            "batch_generation_driver": "BatchGenerationDriver",
            "cycle_batch_scheduler": "CycleBatchScheduler",
            "genuinely_independent_workload_reference_pairs": True,
            "oracle_values_supplied_to_device": False,
            "shared_immutable_weights_and_constants": True,
            "shared_immutable_object_ids": shared_ids,
            "immutable_source_manifest_sha256": immutable_digest,
            "memory_contract": memory_contract,
            "deployment": {
                "deployment_digest": deployment.deployment_digest.hex(),
                "capability_digest": capability.digest,
                "cost_table_digest": cost_table.digest,
            },
            "wave_count": len(result.waves),
        },
        "source": {
            "repository": source_repository,
            "source_sha256": source_after,
            "source_manifest_sha256": digest_of(source_after),
        },
        "sequences": sequence_rows,
        "acceptance_gates": {
            "order": [
                "exact_heterogeneous_output_tokens_text_and_terminal",
                "release_bound_same_execution_tpot",
            ],
            "gate1_correctness": {
                "status": "pass" if gate1_pass else "fail",
                "all_sequences_exact": all(row["passes"] for row in sequence_rows),
                "shared_execution_exact": shared_exact and scheduler_exact,
                "source_stable_during_execution": source_stable,
                "full_model_execution": full_model,
                "production_qualified": gate1_pass and full_model,
            },
            "gate2_tpot": {
                "status": "blocked",
                "consumer": TPOT_CONSUMER,
                "consumer_report": None,
                "exact_execution_consumer_acceptance_required": True,
                "raw_token_commit_ticks_retained": True,
                "target_performance_metrics_published": False,
            },
        },
        "problems": global_problems,
    }
    execution_schema_problems = _schema_problems(
        body, EXECUTION_SCHEMA_PATH, "heterogeneous batch execution"
    )
    if execution_schema_problems:
        raise GovernedBatchError("; ".join(execution_schema_problems))

    output.mkdir(parents=True)
    for lane, payload in enumerate(record_bytes):
        with (output / f"sequence-{lane}.json").open("xb") as handle:
            handle.write(payload)
    execution_path = output / "batch-execution.json"
    with execution_path.open("xb") as handle:
        handle.write(canonical_json(body))
    return body, execution_path


def _discover_repo(path: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GovernedBatchError(
            "request is not inside a Git repository; pass --repo explicitly"
        ) from exc
    return Path(completed.stdout.strip()).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=None)
    args = parser.parse_args(argv)
    repo = args.repo.resolve() if args.repo is not None else _discover_repo(args.request)
    try:
        body, execution_path = execute_request_file(
            args.request,
            repo=repo,
            output_directory=args.output_directory,
        )
    except (GovernedBatchError, OSError, ValueError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    print(f"wrote {execution_path}")
    print(
        f"heterogeneous batch Gate 1: {body['acceptance_gates']['gate1_correctness']['status']}"
    )
    print("Gate 2 TPOT: blocked pending exact release-bound consumer acceptance")
    return 0 if body["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
