"""Create-once governed timing traces from token-correct cycle batches.

This module is the narrow bridge between :class:`CycleBatchScheduler` and the
repository's correctness-qualified TPOT consumer.  It does not decide model
semantics and it cannot turn a fixture or an analytical estimate into evidence.
It publishes only after independently locked accelerator-token records agree
with the scheduler, their external oracle, decoded text, terminal rule and every
transaction-bound target-cycle timestamp.

The execution-release lock remains outside ABI 3.0.  It freezes the source,
comparison contract, checkpoint/source locks and create-once result namespace;
the exporter revalidates it and emits its file and semantic digests for the
request/checker layer to bind.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    publish_bytes_atomic_no_replace,
)
from runtime.abi3.capability import digest_of
from runtime.abi3.constants import SubmissionFlag
from runtime.abi3.records import EosReason
from runtime.abi3.descriptors import Phase, Symbol
from runtime.cycle.batch import CycleBatchScheduler
from tools.abi3_comparison_boundary import BoundaryError, load_comparison_contract
from tools.freeze_abi3_execution_release import validate_release_lock


TARGET_TIMING_TRACE_SCHEMA = "opentallas.abi3.target_timing_trace.v1"
ACCELERATOR_RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
EXECUTION_TIMING_SCHEMA = "opentallas.abi3.execution_token_commit_timing.v1"
QWEN_ACCEPTANCE_SCHEMA = "opentallas.abi3.qwen3_w10_acceptance.v1"
DEEPSEEK_ACCEPTANCE_SCHEMA = (
    "opentallas.abi3.deepseek_v4_200k_accelerator_acceptance.v1"
)
MEASUREMENT_CLASS = "abi3_cycle_model_execution"
EXPORTER_SOURCE = "runtime/cycle/governed.py"
TRACE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / (
    "schemas/abi3/target_timing_trace_v1.schema.json"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_PROCESS_VIEWS = frozenset({"sky130", "asap7"})
RELEASE_FILE_DIGEST_FIELD = "execution_release_lock_sha256"
RELEASE_SEMANTIC_DIGEST_FIELD = "execution_release_sha256"


class GovernedTimingExportError(ValueError):
    """A batch cannot be promoted to a governed target timing trace."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _integer(value: object, *, minimum: int = 0) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= minimum
    )


def _repo_path(
    repo: Path,
    raw: object,
    label: str,
    problems: list[str],
    *,
    must_exist: bool,
) -> tuple[Path | None, str | None]:
    if not isinstance(raw, (str, Path)) or not str(raw):
        problems.append(f"{label} path is absent")
        return None, None
    root = repo.resolve()
    supplied = Path(raw)
    if ".." in supplied.parts:
        problems.append(f"{label} path contains a parent traversal")
        return None, None
    unresolved = supplied if supplied.is_absolute() else root / supplied
    try:
        lexical = Path(os.path.abspath(unresolved))
        lexical_relative = lexical.relative_to(root)
    except (OSError, ValueError):
        problems.append(f"{label} path escapes the release repository")
        return None, None
    if not lexical_relative.parts:
        problems.append(f"{label} path is not a canonical repository member")
        return None, None
    cursor = root
    for component in lexical_relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            problems.append(
                f"{label} path traverses a symlink: {lexical_relative.as_posix()}"
            )
            return None, None
        if not cursor.exists():
            break
    try:
        resolved = lexical.resolve(strict=False)
        relative = resolved.relative_to(root).as_posix()
    except (OSError, ValueError):
        problems.append(f"{label} path escapes the release repository")
        return None, None
    if must_exist and not resolved.is_file():
        problems.append(f"{label} file is unavailable: {relative}")
    return resolved, relative


def _load_ref(
    raw: object,
    label: str,
    repo: Path,
    problems: list[str],
) -> tuple[Path | None, str | None, dict[str, Any]]:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "sha256"}:
        problems.append(f"{label} is not an exact path/SHA-256 file identity")
        return None, None, {}
    path, relative = _repo_path(
        repo, raw.get("path"), label, problems, must_exist=True
    )
    expected = raw.get("sha256")
    if not isinstance(expected, str) or not SHA256.fullmatch(expected):
        problems.append(f"{label} SHA-256 is malformed")
    if path is None or not path.is_file():
        return path, relative, {}
    observed = _sha256(path)
    if observed != expected:
        problems.append(
            f"{label} SHA-256 differs: expected {expected}, observed {observed}"
        )
    try:
        body = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        problems.append(f"{label} is not strict governed JSON: {exc}")
        return path, relative, {}
    return path, relative, body


def _load_bound_file(
    repo: Path,
    raw_path: object,
    expected_sha: object,
    label: str,
    problems: list[str],
) -> tuple[Path | None, str | None, dict[str, Any]]:
    return _load_ref(
        {"path": raw_path, "sha256": expected_sha}, label, repo, problems
    )


def _ref(path: Path, relative: str) -> dict[str, str]:
    return {"path": relative, "sha256": _sha256(path)}


def _terminal(
    generated: Sequence[int], generation: Mapping[str, Any], stop_reason: object
) -> tuple[str | None, int | None, int | None, list[str]]:
    problems: list[str] = []
    eos_values = generation.get("eos_token_ids")
    eos = set(eos_values) if isinstance(eos_values, list) else set()
    cap = generation.get("max_new_tokens")
    if cap != 256:
        problems.append("comparison generation cap is not exactly 256")
    first_eos = next(
        (index for index, token in enumerate(generated) if token in eos), None
    )
    if (
        first_eos is not None
        and first_eos == len(generated) - 1
        and stop_reason == "eos"
        and len(generated) <= 256
    ):
        return "eos", first_eos, int(EosReason.OFFICIAL_EOS), problems
    if first_eos is None and len(generated) == 256 and stop_reason == "max_new_tokens":
        return "cap", None, int(EosReason.LENGTH_STOP), problems
    problems.append("execution is neither first-official-EOS-included nor exact-256")
    return None, first_eos, None, problems


def _acceptance_text(
    acceptance: Mapping[str, Any], sequence_index: int, batch_size: int
) -> Mapping[str, Any]:
    if batch_size == 1:
        return _mapping(
            acceptance.get("text_evidence", acceptance.get("token_evidence"))
        )
    rows = acceptance.get("sequence_evidence")
    if isinstance(rows, list):
        for row in rows:
            if (
                isinstance(row, Mapping)
                and row.get("sequence_index") == sequence_index
            ):
                return _mapping(row.get("text_evidence"))
    return {}


def _validate_text(
    evidence: Mapping[str, Any],
    *,
    prompt: Sequence[int],
    generated: Sequence[int],
    workload: Mapping[str, Any],
    workload_file: Mapping[str, Any],
    oracle_result: Mapping[str, Any],
    problems: list[str],
) -> None:
    tokenizer = _mapping(evidence.get("tokenizer"))
    input_row = _mapping(evidence.get("input"))
    output = _mapping(evidence.get("output"))
    if not tokenizer or not input_row or not output:
        problems.append("decoded-text evidence is structurally incomplete")
        return
    if tokenizer.get("sha256") != workload.get("tokenizer_sha256"):
        problems.append("decoded-text evidence uses the wrong tokenizer")
    frozen_text = workload_file.get("rendered_text")
    decoded_input = input_row.get("rendered_text")
    if (
        not isinstance(frozen_text, str)
        or not frozen_text
        or decoded_input != frozen_text
        or input_row.get("token_count") != len(prompt)
        or input_row.get("token_ids_sha256") != digest_of(list(prompt))
        or input_row.get("rendered_text_sha256")
        != workload.get("rendered_text_sha256")
        or hashlib.sha256(frozen_text.encode("utf-8")).hexdigest()
        != workload.get("rendered_text_sha256")
        or input_row.get("decode_matches_frozen_text") is not True
        or input_row.get("encode_round_trip_matches_ids") is not True
    ):
        problems.append("decoded input is not the exact legal frozen context")

    raw = output.get("raw_decoded_text")
    visible = output.get("visible_decoded_text")
    raw_match = (
        output.get("raw_matches_frozen_oracle") is True
        or output.get("raw_matches_gate_b_oracle") is True
    )
    visible_match = (
        output.get("visible_matches_frozen_oracle") is True
        or output.get("visible_matches_gate_b_oracle") is True
    )
    if (
        output.get("token_count") != len(generated)
        or output.get("token_ids_sha256") != digest_of(list(generated))
        or ("token_ids" in output and output.get("token_ids") != list(generated))
        or not isinstance(raw, str)
        or not isinstance(visible, str)
        or not visible.strip()
        or "\ufffd" in raw
        or "\ufffd" in visible
        or hashlib.sha256(raw.encode("utf-8")).hexdigest()
        != output.get("raw_decoded_text_sha256")
        or hashlib.sha256(visible.encode("utf-8")).hexdigest()
        != output.get("visible_decoded_text_sha256")
        or not raw_match
        or not visible_match
    ):
        problems.append("decoded output text is illegal or not oracle-exact")
    oracle_raw = oracle_result.get("raw_decoded_text")
    oracle_visible = oracle_result.get("visible_decoded_text")
    if not isinstance(oracle_raw, str) or not isinstance(oracle_visible, str):
        problems.append("locked oracle does not retain decoded output text")
    elif (
        not oracle_visible.strip()
        or "\ufffd" in oracle_raw
        or "\ufffd" in oracle_visible
    ):
        problems.append("locked oracle decoded output text is illegal")
    if raw != oracle_raw:
        problems.append("raw decoded output differs from the locked oracle")
    if visible != oracle_visible:
        problems.append("visible decoded output differs from the locked oracle")


def _source_manifest(
    raw: object,
    repo: Path,
    frozen_source_paths: frozenset[str],
    label: str,
    problems: list[str],
) -> str | None:
    if not isinstance(raw, Mapping) or not raw:
        problems.append(f"{label} is absent")
        return None
    checked: dict[str, str] = {}
    for name, expected in sorted(raw.items()):
        path, relative = _repo_path(
            repo, name, f"{label}[{name!r}]", problems, must_exist=True
        )
        if relative not in frozen_source_paths:
            problems.append(f"{label}[{name!r}] is absent from the release source map")
        if (
            path is None
            or not path.is_file()
            or not isinstance(expected, str)
            or not SHA256.fullmatch(expected)
            or _sha256(path) != expected
        ):
            problems.append(f"{label}[{name!r}] is not source-current")
            continue
        checked[str(name)] = expected
    return digest_of(checked) if len(checked) == len(raw) else None


def _validate_acceptance(
    acceptance: Mapping[str, Any], batch_size: int, problems: list[str]
) -> None:
    schema = acceptance.get("schema")
    if schema not in {QWEN_ACCEPTANCE_SCHEMA, DEEPSEEK_ACCEPTANCE_SCHEMA}:
        problems.append("correctness acceptance schema is unsupported")
        return
    wanted = "pass" if schema == QWEN_ACCEPTANCE_SCHEMA else "accepted"
    if acceptance.get("status") != wanted:
        problems.append("model-specific correctness acceptance did not pass")
    if schema == DEEPSEEK_ACCEPTANCE_SCHEMA and acceptance.get("accepted") is not True:
        problems.append("DeepSeek correctness acceptance is not accepted")
    if acceptance.get("problems") != []:
        problems.append("correctness acceptance carries problems")
    pairs = acceptance.get("pair_checks")
    if (
        not isinstance(pairs, Mapping)
        or not pairs
        or any(value is not True for value in pairs.values())
    ):
        problems.append("correctness acceptance pair checks are incomplete")
    claim = _mapping(acceptance.get("claim_boundary"))
    if claim.get("acceptance_established") is not True:
        problems.append("correctness acceptance claim boundary is not established")
    records = acceptance.get("records")
    if not isinstance(records, list) or len(records) != batch_size:
        problems.append("correctness acceptance does not bind exactly the batch records")


def _record_binding_in_acceptance(
    acceptance: Mapping[str, Any],
    path: Path,
    sha256: str,
    sequence_index: int,
    repo: Path,
    problems: list[str],
) -> None:
    rows = acceptance.get("records")
    matches = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            candidate, _relative = _repo_path(
                repo,
                row.get("path"),
                "correctness acceptance record",
                [],
                must_exist=True,
            )
            if candidate == path and row.get("sha256") == sha256:
                matches.append(row)
    if len(matches) != 1:
        problems.append(
            f"correctness acceptance does not uniquely bind sequence {sequence_index}"
        )
    elif matches[0].get("passes") is not True or matches[0].get("problems") != []:
        problems.append(
            f"correctness acceptance sequence {sequence_index} did not pass"
        )


def _trace_schema_problems(trace: Mapping[str, Any]) -> list[str]:
    """Validate the complete release-bound target timing trace."""

    schema = json.loads(TRACE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return [
        f"target timing trace schema violation at {error.json_path}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(trace),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                error.message,
            ),
        )
    ]


def publish_governed_target_timing_trace(
    scheduler: CycleBatchScheduler,
    *,
    repo: Path,
    output_path: Path | str,
    execution_release_lock: Mapping[str, Any],
    comparison_id: str,
    correctness_acceptance: Mapping[str, Any],
    execution_records: Sequence[Mapping[str, Any]],
    target_role: str,
    producer_path: Path | str = EXPORTER_SOURCE,
) -> dict[str, Any]:
    """Validate and create one raw target timing trace without replacement.

    The returned document is exactly the document written to ``output_path``.
    Any missing or inconsistent correctness, identity, terminal or timing fact
    raises :class:`GovernedTimingExportError` before the output path is created.
    """

    if not isinstance(scheduler, CycleBatchScheduler):
        raise GovernedTimingExportError("a real CycleBatchScheduler is required")
    root = Path(repo).resolve()
    problems: list[str] = []

    lock_path, _lock_relative, release = _load_ref(
        execution_release_lock, "execution release lock", root, problems
    )
    if release:
        problems.extend(validate_release_lock(release, repo=root))
    release_file_sha = _sha256(lock_path) if lock_path is not None and lock_path.is_file() else None
    release_sha = release.get("release_sha256") if release else None
    if not isinstance(release_sha, str) or not SHA256.fullmatch(release_sha):
        problems.append("execution release semantic SHA-256 is absent")

    selected = [
        row
        for row in release.get("comparison_contracts", [])
        if isinstance(row, Mapping) and row.get("comparison_id") == comparison_id
    ] if release else []
    if len(selected) != 1:
        problems.append("execution release does not contain one selected comparison row")
        release_row: Mapping[str, Any] = {}
    else:
        release_row = selected[0]

    contract_path, contract_relative, contract = _load_bound_file(
        root,
        release_row.get("path"),
        release_row.get("source_sha256"),
        "release comparison contract",
        problems,
    )
    if contract:
        try:
            loaded, validation, registered = load_comparison_contract(
                comparison_id,
                repo=root,
                path=contract_path,
                require_ready=True,
            )
        except (BoundaryError, OSError) as exc:
            problems.append(f"comparison contract is not release-ready: {exc}")
        else:
            if loaded != contract or registered.resolve() != contract_path:
                problems.append("selected comparison contract is not the registered file")
            if validation.get("contract_sha256") != release_row.get("semantic_sha256"):
                problems.append("selected comparison semantic digest differs from release")
    if contract.get("comparison_id") != comparison_id:
        problems.append("comparison ID differs from the selected release row")

    namespace_row = _mapping(release.get("result_namespace"))
    namespace, _namespace_relative = _repo_path(
        root,
        namespace_row.get("path"),
        "release result namespace",
        problems,
        must_exist=False,
    )
    output, output_relative = _repo_path(
        root, output_path, "target timing output", problems, must_exist=False
    )
    if namespace is not None and output is not None:
        try:
            inside = output.relative_to(namespace)
        except ValueError:
            problems.append("target timing output is outside the release namespace")
        else:
            if not inside.parts:
                problems.append("target timing output must be below the release namespace")
    if output is not None and (output.exists() or output.is_symlink()):
        problems.append("target timing output already exists; publication is create-once")

    producer, producer_relative = _repo_path(
        root, producer_path, "timing producer", problems, must_exist=True
    )
    source_rows = _mapping(release.get("source")).get("tracked_source_map", [])
    frozen_source_paths = frozenset(
        str(row.get("path"))
        for row in source_rows
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    )
    if producer_relative is not None and not any(
        isinstance(row, Mapping) and row.get("path") == producer_relative
        for row in source_rows
    ):
        problems.append("timing producer is absent from the frozen source map")

    model = _mapping(contract.get("model"))
    workload = _mapping(contract.get("workload"))
    execution = _mapping(contract.get("execution"))
    generation = _mapping(execution.get("generation"))
    policy = _mapping(contract.get("policy"))
    target = _mapping(_mapping(contract.get("targets")).get(target_role))
    if target_role not in {"hbm", "rom"} or not target:
        problems.append("target role is not one locked HBM/ROM comparison side")
    if release_row.get("model_id") != model.get("model_id"):
        problems.append("release model ID differs from the comparison contract")
    if release_row.get("workload_id") != workload.get("workload_id"):
        problems.append("release workload ID differs from the comparison contract")
    if release_row.get("batch_size") != execution.get("batch"):
        problems.append("release batch size differs from the comparison contract")
    if release_row.get("process_view") != policy.get("technology_view"):
        problems.append("release process view differs from the comparison contract")
    released_targets = [
        row
        for row in release_row.get("targets", [])
        if isinstance(row, Mapping) and row.get("role") == target_role
    ]
    wanted_target = {
        name: target.get(name)
        for name in ("backend", "node_count", "role", "target_id", "topology_class")
    }
    if len(released_targets) != 1 or dict(released_targets[0]) != wanted_target:
        problems.append("release target row differs from the selected comparison target")

    batch_size = execution.get("batch")
    concurrency = execution.get("concurrency")
    context_tokens = execution.get("context_tokens")
    if batch_size != scheduler.batch_size:
        problems.append("scheduler physical batch differs from the comparison contract")
    if concurrency != scheduler.batch_size:
        problems.append("comparison concurrency differs from the physical scheduler batch")
    if not _integer(context_tokens, minimum=1):
        problems.append("comparison context length is invalid")
    if workload.get("prompt_token_count") != context_tokens:
        problems.append("workload prompt count differs from comparison context length")
    if workload.get("max_new_tokens") != 256 or generation.get("max_new_tokens") != 256:
        problems.append("workload and generation must both freeze exact-256 output cap")
    vocabulary = generation.get("vocabulary_size")
    if not _integer(vocabulary, minimum=1):
        problems.append("comparison vocabulary size is invalid")

    workload_path, _workload_relative, workload_file = _load_bound_file(
        root,
        workload.get("path"),
        workload.get("source_sha256"),
        "comparison workload",
        problems,
    )
    del workload_path
    prompt = workload_file.get("token_ids") if workload_file else None
    if (
        not isinstance(prompt, list)
        or len(prompt) != context_tokens
        or not _integer(vocabulary, minimum=1)
        or any(not _integer(token) or token >= int(vocabulary) for token in prompt)
    ):
        problems.append("frozen prompt token IDs are incomplete or illegal")
        prompt = []

    oracle_lock = _mapping(contract.get("external_oracle"))
    oracle_path, _oracle_relative, oracle = _load_bound_file(
        root,
        oracle_lock.get("path"),
        oracle_lock.get("source_sha256"),
        "comparison external oracle",
        problems,
    )
    if oracle_lock.get("status") != "locked":
        problems.append("comparison external oracle is not locked")
    oracle_result = _mapping(_mapping(oracle.get("results")).get(workload.get("workload_id")))

    acceptance_path, acceptance_relative, acceptance = _load_ref(
        correctness_acceptance, "correctness acceptance", root, problems
    )
    _validate_acceptance(acceptance, scheduler.batch_size, problems)
    if acceptance.get("workload_id") != workload.get("workload_id"):
        problems.append("correctness acceptance workload differs from contract")

    if len(execution_records) != scheduler.batch_size:
        problems.append("execution record count differs from physical batch")
    record_rows: list[tuple[Path, str, dict[str, Any], str]] = []
    for index, raw in enumerate(execution_records):
        path, relative, record = _load_ref(
            raw, f"execution record {index}", root, problems
        )
        if path is not None and relative is not None and path.is_file():
            record_rows.append((path, relative, record, _sha256(path)))

    generated_rows: list[list[int]] = []
    eos_rows: list[int] = []
    source_manifests: list[str | None] = []
    implementation_digests: list[str | None] = []
    terminal_rows: list[str | None] = []
    for index, (path, _relative, record, artifact_sha) in enumerate(record_rows):
        _record_binding_in_acceptance(
            acceptance, path, artifact_sha, index, root, problems
        )
        if (
            record.get("schema") != ACCELERATOR_RECORD_SCHEMA
            or record.get("status") != "pass"
            or record.get("evidence_class") != "functional_artifact_only"
            or record.get("tool") != "tools/run_accelerator_tokens.py"
        ):
            problems.append(f"execution record {index} is not a passing ABI artifact")
        record_target = _mapping(record.get("target"))
        expected_target = {
            "target_id": target.get("target_id"),
            "backend": target.get("backend"),
            "node_count": target.get("node_count"),
            "topology_class": target.get("topology_class"),
            "capability_digest": scheduler.model.capability.digest,
            "deployment_digest": scheduler.model.deployment.deployment_digest.hex(),
            "technology_view": policy.get("technology_view"),
        }
        for name, expected in expected_target.items():
            if record_target.get(name) != expected:
                problems.append(f"execution record {index} target.{name} differs")
        record_model = _mapping(record.get("model"))
        for name in ("model_id", "graph_id", "numeric_profile"):
            if record_model.get(name) != model.get(name):
                problems.append(f"execution record {index} model.{name} differs")
        record_workload = _mapping(record.get("workload"))
        expected_workload = {
            "workload_id": workload.get("workload_id"),
            "workload_digest": workload.get("digest"),
            "prompt_token_ids": prompt,
            "prompt_token_count": context_tokens,
            "max_new_tokens": 256,
            "rendered_text_sha256": workload.get("rendered_text_sha256"),
            "prompt_token_ids_sha256": digest_of(prompt),
            "tokenizer_sha256": workload.get("tokenizer_sha256"),
        }
        for name, expected in expected_workload.items():
            if record_workload.get(name) != expected:
                problems.append(f"execution record {index} workload.{name} differs")

        generated = record.get("generated_token_ids")
        if (
            not isinstance(generated, list)
            or not generated
            or not _integer(vocabulary, minimum=1)
            or any(not _integer(token) or token >= int(vocabulary) for token in generated)
        ):
            problems.append(f"execution record {index} generated IDs are illegal")
            generated = []
        generated = [int(token) for token in generated]
        generated_rows.append(generated)
        if record.get("generated_token_count") != len(generated):
            problems.append(f"execution record {index} generated count differs")
        oracle_row = _mapping(record.get("oracle"))
        if (
            generated != oracle_row.get("generated_token_ids")
            or generated != oracle_result.get("generated_token_ids")
            or oracle_result.get("generated_token_count") != len(generated)
            or oracle_result.get("workload_digest") != workload.get("digest")
            or oracle_result.get("prompt_token_count") != context_tokens
            or oracle_result.get("stop_reason") != record.get("stop_reason")
            or oracle_row.get("agreement") is not True
            or oracle_row.get("first_divergence_index") is not None
            or oracle_row.get("compared_tokens") != len(generated)
            or oracle_row.get("oracle_token_count") != len(generated)
            or oracle_row.get("evidence_class") != "external_reference_comparator"
            or oracle_path is None
            or _repo_path(root, oracle_row.get("artifact"), "record oracle", [], must_exist=True)[0]
            != oracle_path
            or oracle_row.get("artifact_sha256") != oracle_lock.get("source_sha256")
        ):
            problems.append(
                f"execution record {index} is not exactly equal to the locked oracle"
            )
        if record.get("failure") is not None or record.get("token_legitimacy_problems") != []:
            problems.append(f"execution record {index} carries a failure/legitimacy problem")

        verification = _mapping(record.get("verification"))
        checks = verification.get("checks")
        if (
            verification.get("admitted") is not True
            or verification.get("errors") != []
            or verification.get("state_resources") != 0
            or not isinstance(checks, Mapping)
            or not checks
            or any(value is not True for value in checks.values())
        ):
            problems.append(f"execution record {index} admission evidence is not clean")
        coverage = _mapping(record.get("engine_coverage"))
        missing = coverage.get("missing")
        if (
            not isinstance(missing, list)
            or any(not isinstance(name, str) for name in missing)
            or coverage.get("missing_count") != len(missing)
            or any(name != "SELECTION.SAMPLE" for name in missing)
        ):
            problems.append(f"execution record {index} required engine coverage is incomplete")

        terminal, _first_eos, eos_reason, terminal_problems = _terminal(
            generated, generation, record.get("stop_reason")
        )
        problems.extend(f"execution record {index}: {item}" for item in terminal_problems)
        terminal_rows.append(terminal)
        eos_rows.append(eos_reason if eos_reason is not None else int(EosReason.NONE))
        producer_acceptance = _mapping(record.get("terminal_acceptance"))
        checks = producer_acceptance.get("checks")
        if (
            producer_acceptance.get("accepted") is not True
            or producer_acceptance.get("terminal_kind") != terminal
            or producer_acceptance.get("failed_checks") != []
            or not isinstance(checks, Mapping)
            or not checks
            or any(value is not True for value in checks.values())
        ):
            problems.append(f"execution record {index} terminal acceptance differs")

        implementation = record.get("implementation_identity")
        if not isinstance(implementation, Mapping) or not implementation or implementation.get("unavailable"):
            problems.append(f"execution record {index} implementation identity is absent")
            implementation_digests.append(None)
        else:
            implementation_digests.append(digest_of(dict(implementation)))
        source_manifests.append(
            _source_manifest(
                record.get("source_sha256"),
                root,
                frozen_source_paths,
                f"execution record {index} source map",
                problems,
            )
        )
        association = record.get("executed_association")
        if not isinstance(association, Mapping) or not association:
            problems.append(f"execution record {index} numeric association is absent")
        else:
            unsigned = dict(association)
            manifest = unsigned.pop("manifest_sha256", None)
            if manifest != digest_of(unsigned):
                problems.append(f"execution record {index} numeric association differs")

        if scheduler.batch_size > 1:
            batch = _mapping(record.get("batch_execution"))
            if (
                batch.get("schema")
                != "opentallas.abi3.accelerator_batch_execution_member.v1"
                or batch.get("batch_execution_id") != scheduler.batch_execution_id
                or batch.get("batch_size") != scheduler.batch_size
                or batch.get("sequence_index") != index
                or batch.get("shared_execution") is not True
            ):
                problems.append(f"execution record {index} batch binding differs")
        _validate_text(
            _acceptance_text(acceptance, index, scheduler.batch_size),
            prompt=prompt,
            generated=generated,
            workload=workload,
            workload_file=workload_file,
            oracle_result=oracle_result,
            problems=problems,
        )

    evidence = scheduler.evidence(
        generated_rows if len(generated_rows) == scheduler.batch_size else None,
        expected_eos_reasons=(
            eos_rows if len(eos_rows) == scheduler.batch_size else None
        ),
        full_model_execution=True,
    )
    gate1 = _mapping(_mapping(evidence.get("acceptance_gates")).get("gate1_correctness"))
    gate2 = _mapping(_mapping(evidence.get("acceptance_gates")).get("gate2_tpot"))
    if gate1.get("status") != "pass":
        problems.append("CycleBatchScheduler full-model correctness gate did not pass")
    if gate2.get("eligible_for_target_tpot") is not True:
        problems.append("CycleBatchScheduler target timing is not characterized/eligible")
    if evidence.get("problems") != []:
        problems.extend(f"scheduler: {item}" for item in evidence.get("problems", []))

    technology_view = policy.get("technology_view")
    timebase = _mapping(_mapping(evidence.get("timing")).get("timebase"))
    if (
        technology_view not in ALLOWED_PROCESS_VIEWS
        or scheduler.model.capability.technology_view != technology_view
        or scheduler.model.machine.cost_table.technology_view != technology_view
        or timebase.get("same_process_view") is not True
        or timebase.get("process_timebase_characterized") is not True
        or timebase.get("all_timing_inputs_characterized") is not True
        or timebase.get("clock_provenance") != "characterized"
        or timebase.get("host_wall_time_used") is not False
        or timebase.get("retired_instruction_count_used_as_time") is not False
        or timebase.get("projection_used_as_qualified_tpot") is not False
    ):
        problems.append(
            "timing is not fully characterized target-cycle time on SKY130 or ASAP7"
        )
    frequency = timebase.get("clock_frequency_hz")
    frozen_frequency = _mapping(policy.get("clock")).get("comparison_frequency_hz")
    if (
        not isinstance(frequency, (int, float))
        or isinstance(frequency, bool)
        or not math.isfinite(float(frequency))
        or int(frequency) != frequency
        or int(frequency) < 1
        or frozen_frequency != int(frequency)
    ):
        problems.append("characterized clock differs from the frozen comparison clock")
        frequency = 0
    else:
        frequency = int(frequency)

    deployment = scheduler.model.deployment
    capability = scheduler.model.capability
    if "fixture" in deployment.source_identity:
        problems.append("fixture deployment is explicitly not qualified for export")
    if deployment.model_id != model.get("model_id"):
        problems.append("scheduler deployment model differs from comparison model")
    if deployment.target_id != target.get("target_id"):
        problems.append("scheduler deployment target differs from comparison target")
    if deployment.backend != target.get("backend"):
        problems.append("scheduler deployment backend differs from comparison target")
    if deployment.source_identity.get("graph_id") != model.get("graph_id"):
        problems.append("scheduler deployment does not bind the comparison graph")
    if deployment.topology_class != target.get("topology_class"):
        problems.append("scheduler topology class differs from comparison target")
    if scheduler.device.node_count != target.get("node_count"):
        problems.append("scheduler node count differs from comparison target")

    capability_lock = _mapping(target.get("capability"))
    _cap_path, _cap_relative, _cap_body = _load_bound_file(
        root,
        capability_lock.get("path"),
        capability_lock.get("source_sha256"),
        "target capability lock",
        problems,
    )
    if capability_lock.get("status") != "locked" or capability_lock.get("digest") != capability.digest:
        problems.append("scheduler capability differs from the locked target")
    deployment_lock = _mapping(target.get("deployment"))
    deployment_root, deployment_relative = _repo_path(
        root,
        deployment_lock.get("path"),
        "target deployment lock",
        problems,
        must_exist=False,
    )
    deployment_manifest = deployment_root / "deployment.json" if deployment_root else None
    if (
        deployment_lock.get("status") != "locked"
        or deployment_lock.get("digest") != deployment.deployment_digest.hex()
        or deployment_manifest is None
        or not deployment_manifest.is_file()
        or _sha256(deployment_manifest) != deployment_lock.get("source_sha256")
    ):
        problems.append("scheduler deployment differs from the locked target")
    del deployment_relative

    cost_policy = _mapping(target.get("cost_policy"))
    cost_lock = _mapping(cost_policy.get("lock"))
    cost_path, cost_relative, _cost_body = _load_bound_file(
        root,
        cost_lock.get("path"),
        cost_lock.get("source_sha256"),
        "target cost-table lock",
        problems,
    )
    cost_table = scheduler.model.machine.cost_table
    if (
        cost_lock.get("status") != "locked"
        or cost_policy.get("cost_table_id") != cost_table.cost_table_id
        or cost_lock.get("digest") != cost_table.digest
        or cost_path is None
        or cost_table.path is None
        or cost_path != Path(cost_table.path).resolve()
    ):
        problems.append("scheduler cost table differs from the locked target")

    records_by_lane: list[list[Any]] = [[] for _ in range(scheduler.batch_size)]
    for timing in scheduler.timing_records:
        if 0 <= timing.lane_index < scheduler.batch_size:
            records_by_lane[timing.lane_index].append(timing)
    trace_by_key = {
        (trace.session_id, trace.transaction_id): trace
        for trace in scheduler.device.transaction_traces
    }
    performance_sequences = _mapping(_mapping(evidence.get("timing")).get("performance")).get("sequences", [])
    timelines: list[dict[str, Any]] = []
    steady_start = _mapping(execution.get("tpot_acceptance")).get(
        "steady_state_start_decode_step"
    )
    role_budget = _mapping(
        _mapping(_mapping(execution.get("tpot_acceptance")).get("roles")).get(
            target_role
        )
    )
    if (
        not _integer(steady_start)
        or MEASUREMENT_CLASS not in role_budget.get("eligible_measurement_classes", [])
        or role_budget.get("assumption_dependent_evidence_allowed") is not False
    ):
        problems.append("frozen TPOT budget does not admit characterized cycle timing")
        steady_start = 0
    for lane, sequence in enumerate(evidence.get("sequences", [])):
        timings = sorted(records_by_lane[lane], key=lambda row: row.wave_index)
        transactions = sequence.get("transaction_ids", [])
        generated = generated_rows[lane] if lane < len(generated_rows) else []
        if len(timings) != len(generated) or len(transactions) != len(generated):
            problems.append(f"sequence {lane} does not have one timing binding per token")
            continue
        if _integer(steady_start) and len(generated) < int(steady_start) + 2:
            problems.append(f"sequence {lane} has no steady-state TPOT interval")
        elif len(generated) < 2:
            problems.append(f"sequence {lane} has no output-token interval for TPOT")
        perf = (
            performance_sequences[lane]
            if isinstance(performance_sequences, list)
            and lane < len(performance_sequences)
            and isinstance(performance_sequences[lane], Mapping)
            else {}
        )
        commits = [int(row.token_commit_tick) for row in timings]
        starts = [int(row.request_start_tick) for row in timings]
        if perf.get("token_commit_ticks") != commits or perf.get("transaction_request_start_ticks") != starts:
            problems.append(f"sequence {lane} performance timeline differs from bindings")
        if sequence.get("no_post_eos_transaction") is not True:
            problems.append(f"sequence {lane} executed after EOS/length retirement")
        for step_index, (transaction_id, timing) in enumerate(zip(transactions, timings, strict=True)):
            if (
                timing.transaction_id != transaction_id
                or timing.transaction_id != step_index + 1
                or timing.produced_token_id != generated[step_index]
            ):
                problems.append(f"sequence {lane} timing/token transaction binding differs")
            key = (sequence.get("session_id"), transaction_id)
            functional = trace_by_key.get(key)
            symbols = dict(functional.request_symbols) if functional is not None else {}
            expected_phase = int(Phase.PREFILL if step_index == 0 else Phase.DECODE)
            expected_span = int(context_tokens) if step_index == 0 and _integer(context_tokens, minimum=1) else 1
            expected_position = 0 if step_index == 0 else int(context_tokens) + step_index - 1
            expected_flags = int(
                SubmissionFlag.PREFILL_PHASE
                if step_index == 0
                else SubmissionFlag.DECODE_PHASE
            )
            wanted_symbols = {
                int(Symbol.PHASE): expected_phase,
                int(Symbol.SPAN_TOKENS): expected_span,
                int(Symbol.POSITION_START): expected_position,
                int(Symbol.POSITION_END): expected_position + expected_span,
                int(Symbol.CONTEXT_LENGTH): expected_position + expected_span,
                int(Symbol.GENERATION_INDEX): step_index,
                int(Symbol.MAX_NEW_TOKENS): 256,
                int(Symbol.BATCH): scheduler.batch_size,
                int(Symbol.SPAN_LAST_INDEX): expected_span - 1,
            }
            if functional is None or any(symbols.get(name) != value for name, value in wanted_symbols.items()):
                problems.append(f"sequence {lane} transaction {transaction_id} is not the frozen full-model trajectory")
            if functional is not None and (
                timing.request_symbols_digest
                != digest_of(
                    [
                        [symbol, value]
                        for symbol, value in functional.request_symbols
                    ]
                )
                or timing.entrypoint_id != functional.entrypoint_id
                or timing.generation_policy_id != functional.generation_policy_id
                or timing.submission_flags != functional.submission_flags
            ):
                problems.append(
                    f"sequence {lane} transaction {transaction_id} request binding differs"
                )
            if functional is not None and functional.submission_flags & expected_flags != expected_flags:
                problems.append(f"sequence {lane} transaction {transaction_id} phase flag differs")
        if lane < len(record_rows):
            record = record_rows[lane][2]
            steps = record.get("per_step")
            if not isinstance(steps, list) or len(steps) != len(timings):
                problems.append(f"execution record {lane} per_step is incomplete")
            else:
                for step_index, (step, timing) in enumerate(zip(steps, timings, strict=True)):
                    expected_phase_name = "prefill" if step_index == 0 else "decode"
                    expected_eos = (
                        int(EosReason.OFFICIAL_EOS)
                        if terminal_rows[lane] == "eos" and step_index == len(steps) - 1
                        else int(EosReason.LENGTH_STOP)
                        if terminal_rows[lane] == "cap" and step_index == len(steps) - 1
                        else int(EosReason.NONE)
                    )
                    if (
                        not isinstance(step, Mapping)
                        or step.get("step") != step_index
                        or step.get("transaction_id") != timing.transaction_id
                        or step.get("phase") != expected_phase_name
                        or step.get("status") != "SUCCESS"
                        or step.get("trap") != "NONE"
                        or step.get("produced_tokens") != [generated_rows[lane][step_index]]
                        or step.get("final_token_id") != generated_rows[lane][step_index]
                        or step.get("eos_reason") != expected_eos
                        or step.get("completion_timestamp") != timing.token_commit_tick
                    ):
                        problems.append(f"execution record {lane} per_step[{step_index}] differs from scheduler")
                execution_timing = _mapping(record.get("execution_timing"))
                if (
                    execution_timing.get("schema") != EXECUTION_TIMING_SCHEMA
                    or execution_timing.get("unit") != "cycles"
                    or execution_timing.get("clock_domain") != "abi3_device_cycle_counter"
                    or execution_timing.get("request_start_tick") != starts[0]
                    or execution_timing.get("request_start_source")
                    != "driver_counter_before_fresh_prefill_submission"
                    or execution_timing.get("token_commit_ticks") != commits
                    or execution_timing.get("token_commit_source")
                    != "decoded_abi3_completion.completion_timestamp"
                    or execution_timing.get("token_commits_from_execution") is not True
                    or execution_timing.get("problems") != []
                ):
                    problems.append(f"execution record {lane} raw timing differs from scheduler")
        if timings:
            timelines.append(
                {
                    "sequence_index": lane,
                    "request_start_tick": starts[0],
                    "token_commit_ticks": commits,
                }
            )

    if len(set(source_manifests)) != 1 or None in source_manifests:
        problems.append("execution records do not bind one complete source manifest")
    if len(set(implementation_digests)) != 1 or None in implementation_digests:
        problems.append("execution records do not bind one implementation identity")
    source_manifest = source_manifests[0] if source_manifests else None
    implementation_digest = implementation_digests[0] if implementation_digests else None

    trace: dict[str, Any] = {
        "schema": TARGET_TIMING_TRACE_SCHEMA,
        "evidence_class": "executed_target_timing_trace",
        "measurement_class": MEASUREMENT_CLASS,
        "projection_only": False,
        "counterfactual_or_extrapolated": False,
        "full_workload_execution": True,
        "token_commits_from_execution": True,
        "producer": {
            "tool": producer_relative,
            "source_sha256": _sha256(producer) if producer and producer.is_file() else "",
        },
        "provenance": {
            "class": "characterized",
            "depends_on_assumed_values": False,
        },
        "comparison_id": comparison_id,
        "comparison_contract_sha256": release_row.get("source_sha256"),
        "correctness_acceptance_sha256": (
            _sha256(acceptance_path)
            if acceptance_path is not None and acceptance_path.is_file()
            else ""
        ),
        "model_id": model.get("model_id"),
        "graph_id": model.get("graph_id"),
        "workload_id": workload.get("workload_id"),
        "workload_digest": workload.get("digest"),
        "latency_boundary": policy.get("latency_boundary"),
        "technology_view": technology_view,
        "pvt": policy.get("pvt"),
        "batch_size": scheduler.batch_size,
        "concurrency": concurrency,
        "batch_execution_id": scheduler.batch_execution_id,
        "target": {
            "target_id": target.get("target_id"),
            "backend": target.get("backend"),
            "node_count": target.get("node_count"),
            "topology_class": target.get("topology_class"),
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
            "technology_view": technology_view,
            "source_manifest_sha256": source_manifest,
            "implementation_identity_sha256": implementation_digest,
        },
        "cost_table": {
            "cost_table_id": cost_table.cost_table_id,
            "path": cost_relative,
            "sha256": _sha256(cost_path) if cost_path and cost_path.is_file() else "",
        },
        "timebase": {
            "unit": "cycles",
            "ticks_per_second": frequency,
            "clock_frequency_hz": frequency,
        },
        "steady_state_start_decode_step": steady_start,
        "execution_records": [
            {
                "sequence_index": index,
                "path": relative,
                "sha256": artifact_sha,
            }
            for index, (_path, relative, _record, artifact_sha) in enumerate(record_rows)
        ],
        "sequences": timelines,
        RELEASE_FILE_DIGEST_FIELD: release_file_sha,
        RELEASE_SEMANTIC_DIGEST_FIELD: release_sha,
    }
    problems.extend(_trace_schema_problems(trace))
    if problems:
        raise GovernedTimingExportError(
            "governed target timing export refused:\n  "
            + "\n  ".join(sorted(set(problems)))
        )
    if output is None or output_relative is None:
        raise GovernedTimingExportError("target timing output path was not resolved")
    payload = canonical_json_bytes(trace)
    try:
        publish_bytes_atomic_no_replace(output, payload)
    except (FileExistsError, OSError) as exc:
        raise GovernedTimingExportError(
            f"create-once target timing publication failed: {exc}"
        ) from exc
    if output.read_bytes() != payload:
        raise GovernedTimingExportError("published target timing bytes differ")
    return trace


__all__ = [
    "GovernedTimingExportError",
    "MEASUREMENT_CLASS",
    "RELEASE_FILE_DIGEST_FIELD",
    "RELEASE_SEMANTIC_DIGEST_FIELD",
    "TARGET_TIMING_TRACE_SCHEMA",
    "publish_governed_target_timing_trace",
]
