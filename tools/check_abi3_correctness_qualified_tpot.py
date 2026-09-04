#!/usr/bin/env python3
"""Publish TPOT only after an ABI 3.0 execution passes token correctness.

The input is a manifest of independently source-bound batch points.  Every
point must name a comparison contract, an accepted model-specific correctness
artifact, and the exact ``accelerator_tokens.v1`` records covered by that
artifact.  Target timing is optional, but when present it must be a raw
``target_timing_trace.v1`` containing request and token-commit ticks.  This
tool derives TTFT and TPOT from those ticks; it never accepts precomputed rate
fields.

Host functional-simulator and RTL-simulator wall time are retained as campaign
diagnostics only.  Analytical/roofline artifacts, extrapolated rows, and those
wall times are categorically ineligible as target TPOT.  Production-simulation
closure may use an explicitly labeled RTL-bound accelerated co-simulation only
when its token path, execution identity, characterized target cycles, and every
accelerated engine's bit/cycle equivalence are digest-bound.  It is never
reported as monolithic full RTL.  A numeric TPOT threshold is never invented:
if ``execution.tpot_acceptance`` is absent from the comparison contract, the
explicit verdict is ``budget_missing`` / ``not_evaluable``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json, digest_of  # noqa: E402


REQUEST_SCHEMA = "opentallas.abi3.correctness_qualified_tpot_request.v1"
REPORT_SCHEMA = "opentallas.abi3.correctness_qualified_tpot_report.v1"
TRACE_SCHEMA = "opentallas.abi3.target_timing_trace.v1"
COSIM_PROOF_SCHEMA = "opentallas.abi3.rtl_bound_accelerated_cosimulation_proof.v1"
RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
OPTIONAL_UNIMPLEMENTED_ENGINES = frozenset({"SELECTION.SAMPLE"})
EXECUTION_TIMING_SCHEMA = "opentallas.abi3.execution_token_commit_timing.v1"
CONTRACT_SCHEMA = "opentallas.abi3.comparison_contract.v1"
COSIM_TIER = "rtl_bound_accelerated_cosimulation"

REQUEST_SCHEMA_PATH = (
    REPO / "schemas/abi3/correctness_qualified_tpot_request_v1.schema.json"
)
REPORT_SCHEMA_PATH = (
    REPO / "schemas/abi3/correctness_qualified_tpot_report_v1.schema.json"
)
TRACE_SCHEMA_PATH = REPO / "schemas/abi3/target_timing_trace_v1.schema.json"
COSIM_PROOF_SCHEMA_PATH = (
    REPO / "schemas/abi3/rtl_bound_accelerated_cosimulation_proof_v1.schema.json"
)
CONTRACT_SCHEMA_PATH = REPO / "schemas/abi3/comparison_contract_v1.schema.json"

ACCEPTANCE_SCHEMAS = {
    "opentallas.abi3.qwen3_w10_acceptance.v1",
    "opentallas.abi3.deepseek_v4_200k_accelerator_acceptance.v1",
}
TARGET_MEASUREMENT_CLASSES = {
    "abi3_cycle_model_execution": "cycle_model_target_tpot",
    COSIM_TIER: "rtl_bound_accelerated_cosimulation_target_tpot",
    "rtl_cycle_simulation": "rtl_simulated_target_tpot",
    "post_layout_timing_simulation": "post_layout_simulated_target_tpot",
    "silicon_measurement": "silicon_measured_target_tpot",
}
PROJECTION_SCHEMAS = {
    "opentallas.abi3.cycle_sweep.v1",
    "opentallas.roofline.study.v1",
    "opentallas.iso_node.study.v1",
}
SHA256_CHARS = frozenset("0123456789abcdef")
REQUIRED_COSIM_RTL_COMPONENTS = frozenset(
    {
        "abi3_microsequencer",
        "address_generator",
        "descriptor_view_resolver",
        "dma_memory_transaction_path",
        "link_fabric",
        "queue_event_fence_control",
        "selection",
        "token_append_eos",
        "token_commit_counter",
    }
)


class EvidenceError(ValueError):
    """A request or referenced artifact is structurally unusable."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in SHA256_CHARS for character in value)
    )


def _integer(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _positive_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _round(value: float) -> float:
    """Keep reports stable while retaining sub-nanosecond-scale precision."""

    return float(f"{value:.15g}")


def _strict_json_loads(payload: str | bytes, *, source: object) -> Any:
    """Parse governed JSON without duplicate-key or non-finite ambiguity."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, value in pairs:
            if key in body:
                raise EvidenceError(f"duplicate JSON key {key!r} in {source}")
            body[key] = value
        return body

    def reject_constant(value: str) -> None:
        raise EvidenceError(f"non-finite JSON number {value!r} in {source}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"malformed JSON in {source}: {exc}") from exc


def _load(path: Path) -> dict[str, Any]:
    body = _strict_json_loads(path.read_bytes(), source=path)
    if not isinstance(body, dict):
        raise EvidenceError(f"{path} is not a JSON object")
    return body


def _schema_problems(body: object, schema_path: Path, label: str) -> list[str]:
    """Return deterministic Draft 2020-12 violations for one governed object."""

    schema = _load(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(body),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )
    return [
        f"{label} schema violation at {error.json_path}: {error.message}"
        for error in errors
    ]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _resolve(value: object, *, base: Path = REPO) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def _file_ref(
    raw: object, label: str, problems: list[str], *, base: Path = REPO
) -> tuple[Path | None, str | None]:
    if not isinstance(raw, dict):
        problems.append(f"{label} is not a file identity")
        return None, None
    path = _resolve(raw.get("path"), base=base)
    expected = raw.get("sha256")
    if path is None:
        problems.append(f"{label}.path is missing")
        return None, None
    if not _is_sha256(expected):
        problems.append(f"{label}.sha256 is not a lowercase SHA-256")
        return path, None
    if not path.is_file():
        problems.append(f"{label}.path does not identify a file: {_display(path)}")
        return path, None
    actual = _sha256(path)
    if actual != expected:
        problems.append(
            f"{label} SHA-256 mismatch: expected {expected}, observed {actual}"
        )
    return path, actual


def _source_identity(
    sources: object, label: str, problems: list[str]
) -> tuple[dict[str, str], str | None]:
    if not isinstance(sources, dict) or not sources:
        problems.append(f"{label} is absent or empty")
        return {}, None
    checked: dict[str, str] = {}
    for raw_path, expected in sorted(sources.items()):
        path = _resolve(raw_path)
        if path is None or not path.is_file() or not _is_sha256(expected):
            problems.append(
                f"{label}[{raw_path!r}] is not a valid current file identity"
            )
            continue
        actual = _sha256(path)
        if actual != expected:
            problems.append(f"{label}[{raw_path!r}] is stale")
            continue
        checked[str(raw_path)] = str(expected)
    return checked, digest_of(checked) if checked and len(checked) == len(
        sources
    ) else None


def _load_contract(
    raw_ref: object, problems: list[str]
) -> tuple[Path | None, dict[str, Any], str | None]:
    path, identity = _file_ref(raw_ref, "comparison_contract", problems)
    if path is None or not path.is_file():
        return path, {}, identity
    try:
        contract = _load(path)
    except (OSError, EvidenceError) as exc:
        problems.append(f"comparison contract is not valid governed JSON: {exc}")
        return path, {}, identity
    schema_errors = _schema_problems(
        contract, CONTRACT_SCHEMA_PATH, "comparison contract"
    )
    problems.extend(schema_errors)
    if schema_errors:
        return path, {}, identity
    return path, contract, identity


def _check_bound_file(
    value: object, expected_sha: object, label: str, problems: list[str]
) -> Path | None:
    path = _resolve(value)
    if path is None or not path.is_file():
        problems.append(f"{label} is unavailable")
        return path
    if not _is_sha256(expected_sha) or _sha256(path) != expected_sha:
        problems.append(f"{label} is not source-current")
    return path


def _check_bound_deployment(
    value: object, expected_sha: object, label: str, problems: list[str]
) -> Path | None:
    root = _resolve(value)
    if root is None or not root.is_dir():
        problems.append(f"{label} is not an available deployment directory")
        return root
    manifest = root / "deployment.json"
    if not manifest.is_file():
        problems.append(f"{label}/deployment.json is unavailable")
    elif not _is_sha256(expected_sha) or _sha256(manifest) != expected_sha:
        problems.append(f"{label}/deployment.json is not source-current")
    return root


def _check_contract_sources(
    contract: Mapping[str, Any], problems: list[str]
) -> dict[str, Any]:
    model = _mapping(contract.get("model"))
    workload = _mapping(contract.get("workload"))
    oracle = _mapping(contract.get("external_oracle"))
    execution = _mapping(contract.get("execution"))
    generation = _mapping(execution.get("generation"))
    ir_path = _check_bound_file(
        model.get("kernel_ir_path"),
        model.get("kernel_ir_source_sha256"),
        "contract kernel IR",
        problems,
    )
    workload_path = _check_bound_file(
        workload.get("path"),
        workload.get("source_sha256"),
        "contract workload",
        problems,
    )
    index_path = _check_bound_file(
        workload.get("index_path"),
        workload.get("index_source_sha256"),
        "contract workload index",
        problems,
    )
    template = _mapping(workload.get("template"))
    template_path: Path | None = None
    if template.get("mode") == "none_plain_text":
        if (
            template.get("template_id") != "none_plain_text"
            or template.get("path") is not None
            or template.get("source_sha256") is not None
        ):
            problems.append("plain-text workload template identity is inconsistent")
    else:
        template_path = _check_bound_file(
            template.get("path"),
            template.get("source_sha256"),
            "contract workload template",
            problems,
        )
    oracle_path: Path | None = None
    if oracle.get("status") != "locked":
        problems.append("comparison contract external oracle is not locked")
    else:
        oracle_path = _check_bound_file(
            oracle.get("path"),
            oracle.get("source_sha256"),
            "contract external oracle",
            problems,
        )
        producer = _mapping(oracle.get("producer"))
        _check_bound_file(
            producer.get("tool"),
            producer.get("source_sha256"),
            "contract oracle producer",
            problems,
        )
    workload_body: dict[str, Any] = {}
    if workload_path is not None and workload_path.is_file():
        try:
            workload_body = _load(workload_path)
        except (OSError, EvidenceError) as exc:
            problems.append(f"contract workload is not valid governed JSON: {exc}")
        else:
            tokens = workload_body.get("token_ids")
            rendered = workload_body.get("rendered_text")
            expected = {
                "workload_id": workload.get("workload_id"),
                "digest": workload.get("digest"),
                "kind": workload.get("kind"),
                "prompt_token_count": workload.get("prompt_token_count"),
                "max_new_tokens": workload.get("max_new_tokens"),
                "rendered_text_sha256": workload.get("rendered_text_sha256"),
            }
            for name, value in expected.items():
                if workload_body.get(name) != value:
                    problems.append(
                        f"contract workload file {name} does not match contract"
                    )
            if (
                not isinstance(tokens, list)
                or len(tokens) != workload.get("prompt_token_count")
                or not _integer(generation.get("vocabulary_size"), minimum=1)
                or any(
                    not _integer(token) or token >= int(generation["vocabulary_size"])
                    for token in tokens
                )
            ):
                problems.append("contract workload prompt token list is inconsistent")
            if not isinstance(rendered, str) or not rendered:
                problems.append(
                    "contract workload does not retain a nonempty input context"
                )
            elif hashlib.sha256(rendered.encode("utf-8")).hexdigest() != workload.get(
                "rendered_text_sha256"
            ):
                problems.append(
                    "contract workload input-context digest is inconsistent"
                )
    if index_path is not None and index_path.is_file():
        try:
            index = _load(index_path)
        except (OSError, EvidenceError) as exc:
            problems.append(
                f"contract workload index is not valid governed JSON: {exc}"
            )
        else:
            index_entry = _mapping(
                _mapping(index.get("workloads")).get(workload.get("workload_id"))
            )
            if index.get("schema") != workload.get("index_schema"):
                problems.append("contract workload-index schema is inconsistent")
            if index.get("model_id") != model.get("model_id"):
                problems.append("contract workload-index model ID is inconsistent")
            if index.get("tokenizer_sha256") != workload.get("tokenizer_sha256"):
                problems.append("contract workload-index tokenizer is inconsistent")
            expected_entry = {
                "digest": workload.get("digest"),
                "kind": workload.get("kind"),
                "prompt_token_count": workload.get("prompt_token_count"),
                "max_new_tokens": workload.get("max_new_tokens"),
                "path": Path(str(workload.get("path"))).name,
            }
            for name, value in expected_entry.items():
                if index_entry.get(name) != value:
                    problems.append(
                        f"contract workload-index entry {name} is inconsistent"
                    )
    if ir_path is not None and ir_path.is_file():
        try:
            ir = _load(ir_path)
        except (OSError, EvidenceError) as exc:
            problems.append(f"contract kernel IR is not valid governed JSON: {exc}")
        else:
            if ir.get("graph_id") != model.get("graph_id"):
                problems.append("contract graph ID differs from the kernel IR")
            if ir.get("model_id") != model.get("model_id"):
                problems.append("contract model ID differs from the kernel IR")
    return {
        "workload_path": workload_path,
        "workload_index_path": index_path,
        "workload_template_path": template_path,
        "workload": workload_body,
        "oracle_path": oracle_path,
    }


def _acceptance_passed(acceptance: Mapping[str, Any], problems: list[str]) -> bool:
    schema = acceptance.get("schema")
    if schema not in ACCEPTANCE_SCHEMAS:
        problems.append(f"unsupported correctness acceptance schema {schema!r}")
        return False
    expected_status = (
        "pass" if schema == "opentallas.abi3.qwen3_w10_acceptance.v1" else "accepted"
    )
    if acceptance.get("status") != expected_status:
        problems.append("model-specific correctness gate did not pass")
    if (
        schema.endswith("deepseek_v4_200k_accelerator_acceptance.v1")
        and acceptance.get("accepted") is not True
    ):
        problems.append("DeepSeek accelerator-pair acceptance is not true")
    if acceptance.get("problems") != []:
        problems.append("model-specific correctness artifact carries problems")
    pairs = acceptance.get("pair_checks")
    if (
        not isinstance(pairs, dict)
        or not pairs
        or any(value is not True for value in pairs.values())
    ):
        problems.append(
            "model-specific correctness pair checks are absent or not all true"
        )
    claim = acceptance.get("claim_boundary")
    if not isinstance(claim, dict) or claim.get("acceptance_established") is not True:
        problems.append("correctness acceptance claim boundary is not established")
    return not problems


def _acceptance_text_evidence(
    acceptance: Mapping[str, Any], sequence_index: int, batch_size: int
) -> object:
    if batch_size == 1:
        return acceptance.get("text_evidence", acceptance.get("token_evidence"))
    rows = acceptance.get("sequence_evidence")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("sequence_index") == sequence_index:
            return row.get("text_evidence")
    return None


def _target_for_role(contract: Mapping[str, Any], role: object) -> dict[str, Any]:
    targets = contract.get("targets")
    if not isinstance(targets, dict) or role not in {"rom", "hbm"}:
        return {}
    target = targets.get(role)
    return target if isinstance(target, dict) else {}


def _check_current_artifact_identity(
    raw: object, expected_sha: object, label: str, problems: list[str]
) -> None:
    path = _resolve(raw)
    if path is None or not path.is_file():
        problems.append(f"{label} artifact is unavailable")
    elif not _is_sha256(expected_sha) or _sha256(path) != expected_sha:
        problems.append(f"{label} artifact identity is stale or malformed")


def _terminal_kind(
    record: Mapping[str, Any], generated: Sequence[int], generation: Mapping[str, Any]
) -> tuple[str | None, int | None, list[str]]:
    problems: list[str] = []
    eos_values = generation.get("eos_token_ids")
    eos = set(eos_values) if isinstance(eos_values, list) else set()
    cap = generation.get("max_new_tokens")
    first_eos = next(
        (index for index, token in enumerate(generated) if token in eos), None
    )
    stop = record.get("stop_reason")
    terminal: str | None = None
    if (
        first_eos is not None
        and first_eos == len(generated) - 1
        and stop == "eos"
        and _integer(cap, minimum=1)
        and len(generated) <= int(cap)
    ):
        terminal = "eos"
    elif (
        first_eos is None
        and _integer(cap, minimum=1)
        and len(generated) == cap
        and stop == "max_new_tokens"
    ):
        terminal = "cap"
    else:
        problems.append("execution is not first-official-EOS-included or exact-cap")

    steps = record.get("per_step")
    if not isinstance(steps, list) or len(steps) != len(generated):
        problems.append("per_step does not contain exactly one row per generated token")
        steps = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"per_step[{index}] is not an object")
            continue
        if (
            step.get("step") != index
            or step.get("transaction_id") != index + 1
            or step.get("phase") != ("prefill" if index == 0 else "decode")
        ):
            problems.append(f"per_step[{index}] ordering/phase is invalid")
        if step.get("status") != "SUCCESS" or step.get("trap") != "NONE":
            problems.append(f"per_step[{index}] did not succeed without a trap")
        if (
            step.get("produced_tokens") != [generated[index]]
            or step.get("final_token_id") != generated[index]
        ):
            problems.append(f"per_step[{index}] does not bind its output token")
        is_last = index == len(steps) - 1
        expected_reasons = (
            {1}
            if terminal == "eos" and is_last
            else ({0, 2} if terminal == "cap" and is_last else {0})
        )
        if step.get("eos_reason") not in expected_reasons:
            problems.append(f"per_step[{index}] has inconsistent EOS state")

    producer = record.get("terminal_acceptance")
    checks = producer.get("checks") if isinstance(producer, dict) else None
    if (
        not isinstance(producer, dict)
        or producer.get("accepted") is not True
        or producer.get("terminal_kind") != terminal
        or producer.get("failed_checks") != []
        or not isinstance(checks, dict)
        or not checks
        or any(value is not True for value in checks.values())
    ):
        problems.append("producer terminal acceptance is absent or inconsistent")
    return terminal, first_eos, problems


def _record_execution_timing(
    record: Mapping[str, Any], generated: Sequence[int]
) -> tuple[dict[str, Any], list[str]]:
    """Authenticate raw commit events retained by the token-producing run.

    Binding a timing JSON to an execution-record hash proves which token file
    it cites, but it does not prove that the timeline inside the timing JSON
    came from that execution.  The accelerator record therefore retains the
    decoded ABI completion timestamps themselves; this consumer independently
    reconciles the compact list against every per-step completion.
    """

    evidence = record.get("execution_timing")
    if not isinstance(evidence, dict):
        return {}, ["execution record has no raw token-commit timing binding"]
    problems: list[str] = []
    if evidence.get("schema") != EXECUTION_TIMING_SCHEMA:
        problems.append("execution timing schema is not governed v1")
    if evidence.get("unit") not in {"cycles", "nanoseconds"}:
        problems.append("execution timing unit is absent or unsupported")
    if evidence.get("token_commits_from_execution") is not True:
        problems.append("execution timing is not marked as captured from execution")
    if evidence.get("problems") != []:
        problems.append("execution timing producer reported problems")
    if (
        evidence.get("request_start_source")
        != "driver_counter_before_fresh_prefill_submission"
    ):
        problems.append("execution request-start source is not the fresh request")
    if (
        evidence.get("token_commit_source")
        != "decoded_abi3_completion.completion_timestamp"
    ):
        problems.append("execution token-commit source is not the ABI completion")

    request_start = evidence.get("request_start_tick")
    commits = evidence.get("token_commit_ticks")
    if not _integer(request_start):
        problems.append("execution request-start tick is invalid")
    if (
        not isinstance(commits, list)
        or len(commits) != len(generated)
        or any(not _integer(value, minimum=1) for value in commits)
    ):
        problems.append("execution token-commit ticks are incomplete or invalid")
        commits = []

    steps = record.get("per_step")
    step_ticks = (
        [
            step.get("completion_timestamp")
            if isinstance(step, dict)
            else None
            for step in steps
        ]
        if isinstance(steps, list)
        else []
    )
    if step_ticks != commits:
        problems.append(
            "execution token-commit ticks differ from per-step ABI completions"
        )
    if commits and _integer(request_start):
        if commits[0] <= int(request_start) or any(
            right <= left for left, right in zip(commits, commits[1:])
        ):
            problems.append("execution token-commit timing is not strictly causal")
    return {
        "unit": evidence.get("unit"),
        "request_start_tick": request_start,
        "token_commit_ticks": list(commits),
    }, problems


def _check_text_evidence(
    evidence: object,
    record: Mapping[str, Any],
    contract: Mapping[str, Any],
    workload_body: Mapping[str, Any],
    generated: Sequence[int],
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    if not isinstance(evidence, dict):
        return {}, ["accepted correctness artifact has no decoded-text evidence"]
    tokenizer = evidence.get("tokenizer")
    input_row = evidence.get("input")
    output = evidence.get("output")
    if (
        not isinstance(tokenizer, dict)
        or not isinstance(input_row, dict)
        or not isinstance(output, dict)
    ):
        return {}, ["decoded-text evidence is structurally incomplete"]
    contract_workload = _mapping(contract.get("workload"))
    expected_tokenizer = contract_workload.get("tokenizer_sha256")
    if tokenizer.get("sha256") != expected_tokenizer:
        problems.append("decoded-text evidence uses the wrong tokenizer")
    prompt = _mapping(record.get("workload")).get("prompt_token_ids")
    if not isinstance(prompt, list):
        prompt = []
    frozen_input = workload_body.get("rendered_text")
    decoded_input = input_row.get("rendered_text")
    decoded_input_characters = input_row.get("rendered_character_count")
    input_text_retained = isinstance(decoded_input, str)
    if (
        input_row.get("token_count") != len(prompt)
        or input_row.get("token_ids_sha256") != digest_of(prompt)
        or input_row.get("rendered_text_sha256")
        != contract_workload.get("rendered_text_sha256")
        or input_row.get("decode_matches_frozen_text") is not True
        or input_row.get("encode_round_trip_matches_ids") is not True
    ):
        problems.append("decoded input context is not the exact frozen prompt")
    if not isinstance(frozen_input, str) or not frozen_input:
        problems.append("frozen input context is unavailable for decoded-text audit")
    elif input_text_retained:
        if decoded_input != frozen_input or hashlib.sha256(
            decoded_input.encode("utf-8")
        ).hexdigest() != input_row.get("rendered_text_sha256"):
            problems.append(
                "retained decoded input text differs from the frozen context"
            )
    elif decoded_input_characters != len(frozen_input):
        problems.append(
            "decoded input text is neither retained nor length-bound to the frozen context"
        )
    if workload_body.get("token_ids") != prompt:
        problems.append("execution prompt IDs differ from the retained input context")
    raw_text = output.get("raw_decoded_text")
    visible_text = output.get("visible_decoded_text")
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
        or not isinstance(raw_text, str)
        or not isinstance(visible_text, str)
        or not visible_text.strip()
        or "\ufffd" in raw_text
        or "\ufffd" in visible_text
        or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        != output.get("raw_decoded_text_sha256")
        or hashlib.sha256(visible_text.encode("utf-8")).hexdigest()
        != output.get("visible_decoded_text_sha256")
        or not raw_match
        or not visible_match
    ):
        problems.append(
            "decoded output text is absent, invalid, or differs from the oracle"
        )
    if "token_ids" in output and output.get("token_ids") != list(generated):
        problems.append("decoded output evidence carries different generated token IDs")
    return {
        "tokenizer_sha256": tokenizer.get("sha256"),
        "input_token_count": input_row.get("token_count"),
        "input_token_ids_sha256": input_row.get("token_ids_sha256"),
        "input_context_path": contract_workload.get("path"),
        "input_context_sha256": contract_workload.get("source_sha256"),
        "input_rendered_text": decoded_input if input_text_retained else None,
        "input_rendered_text_sha256": input_row.get("rendered_text_sha256"),
        "input_rendered_character_count": (
            len(decoded_input) if input_text_retained else decoded_input_characters
        ),
        "raw_decoded_text": raw_text,
        "raw_decoded_text_sha256": output.get("raw_decoded_text_sha256"),
        "visible_decoded_text": visible_text,
        "visible_decoded_text_sha256": output.get("visible_decoded_text_sha256"),
    }, problems


def _check_record(
    path: Path,
    artifact_sha256: str,
    sequence_index: int,
    batch_size: int,
    batch_execution_id: str | None,
    role: str,
    contract: Mapping[str, Any],
    contract_sources: Mapping[str, Any],
    acceptance: Mapping[str, Any],
) -> dict[str, Any]:
    record = _load(path)
    problems: list[str] = []
    execution = (
        contract.get("execution") if isinstance(contract.get("execution"), dict) else {}
    )
    generation = (
        execution.get("generation")
        if isinstance(execution.get("generation"), dict)
        else {}
    )
    model = contract.get("model") if isinstance(contract.get("model"), dict) else {}
    workload = (
        contract.get("workload") if isinstance(contract.get("workload"), dict) else {}
    )
    target_contract = _target_for_role(contract, role)

    if (
        record.get("schema") != RECORD_SCHEMA
        or record.get("status") != "pass"
        or record.get("evidence_class") != "functional_artifact_only"
        or record.get("tool") != "tools/run_accelerator_tokens.py"
    ):
        problems.append("record is not a passing accelerator execution artifact")
    target = record.get("target") if isinstance(record.get("target"), dict) else {}
    expected_target = {
        "target_id": target_contract.get("target_id"),
        "backend": target_contract.get("backend"),
        "node_count": target_contract.get("node_count"),
        "topology_class": target_contract.get("topology_class"),
    }
    for name, expected in expected_target.items():
        if target.get(name) != expected:
            problems.append(
                f"record target.{name} differs from the comparison contract"
            )
    for name in ("capability_digest", "deployment_digest"):
        if not _is_sha256(target.get(name)):
            problems.append(f"record target.{name} is not a SHA-256 identity")
    for name in ("capability", "deployment"):
        lock = _mapping(target_contract.get(name))
        if lock.get("status") != "locked":
            problems.append(f"comparison target {name} lock is not frozen")
            continue
        if name == "deployment":
            _check_bound_deployment(
                lock.get("path"),
                lock.get("source_sha256"),
                "comparison target deployment",
                problems,
            )
        else:
            _check_bound_file(
                lock.get("path"),
                lock.get("source_sha256"),
                "comparison target capability",
                problems,
            )
        if target.get(f"{name}_digest") != lock.get("digest"):
            problems.append(
                f"record target.{name}_digest differs from the locked target"
            )
    if target.get("technology_view") != _mapping(contract.get("policy")).get(
        "technology_view"
    ):
        problems.append("record target technology view differs from the contract")

    record_model = record.get("model") if isinstance(record.get("model"), dict) else {}
    for name in ("model_id", "graph_id", "numeric_profile"):
        if record_model.get(name) != model.get(name):
            problems.append(f"record model.{name} differs from the comparison contract")
    record_workload = (
        record.get("workload") if isinstance(record.get("workload"), dict) else {}
    )
    expected_workload = {
        "workload_id": workload.get("workload_id"),
        "workload_digest": workload.get("digest"),
        "prompt_token_count": workload.get("prompt_token_count"),
        "max_new_tokens": workload.get("max_new_tokens"),
        "rendered_text_sha256": workload.get("rendered_text_sha256"),
        "tokenizer_sha256": workload.get("tokenizer_sha256"),
    }
    for name, expected in expected_workload.items():
        if record_workload.get(name) != expected:
            problems.append(f"record workload.{name} differs from the contract")
    prompt = record_workload.get("prompt_token_ids")
    if (
        not isinstance(prompt, list)
        or len(prompt) != workload.get("prompt_token_count")
        or record_workload.get("prompt_token_ids_sha256") != digest_of(prompt)
    ):
        problems.append("record prompt-token identity is invalid")

    generated = record.get("generated_token_ids")
    vocabulary = generation.get("vocabulary_size")
    if not (
        isinstance(generated, list)
        and generated
        and _integer(vocabulary, minimum=1)
        and all(_integer(token) and token < int(vocabulary) for token in generated)
    ):
        generated = []
        problems.append("generated token IDs are empty or illegal")
    if record.get("generated_token_count") != len(generated):
        problems.append("generated token count is inconsistent")
    oracle = record.get("oracle") if isinstance(record.get("oracle"), dict) else {}
    oracle_tokens = oracle.get("generated_token_ids")
    correct = 0
    if isinstance(oracle_tokens, list):
        for left, right in zip(generated, oracle_tokens):
            if left != right:
                break
            correct += 1
    first_divergence = None if generated == oracle_tokens else correct
    if (
        generated != oracle_tokens
        or oracle.get("agreement") is not True
        or oracle.get("first_divergence_index") is not None
        or oracle.get("compared_tokens") != len(generated)
        or oracle.get("oracle_token_count") != len(generated)
        or oracle.get("evidence_class") != "external_reference_comparator"
    ):
        problems.append("generated tokens are not exactly equal to the complete oracle")
    _check_current_artifact_identity(
        oracle.get("artifact"), oracle.get("artifact_sha256"), "record oracle", problems
    )
    contract_oracle = _mapping(contract.get("external_oracle"))
    contract_oracle_path = contract_sources.get("oracle_path")
    if (
        not isinstance(contract_oracle_path, Path)
        or _resolve(oracle.get("artifact")) != contract_oracle_path.resolve()
        or oracle.get("artifact_sha256") != contract_oracle.get("source_sha256")
    ):
        problems.append("record oracle is not the exact comparison-contract oracle")
    if (
        record.get("failure") is not None
        or record.get("token_legitimacy_problems") != []
    ):
        problems.append("record carries a failure or token-legitimacy problem")

    terminal, first_eos, terminal_problems = _terminal_kind(
        record, generated, generation
    )
    problems.extend(terminal_problems)
    verification = (
        record.get("verification")
        if isinstance(record.get("verification"), dict)
        else {}
    )
    checks = verification.get("checks")
    if (
        verification.get("admitted") is not True
        or verification.get("errors") != []
        or verification.get("state_resources") != 0
        or not isinstance(checks, dict)
        or not checks
        or any(value is not True for value in checks.values())
    ):
        problems.append("deployment capacity/admission evidence is not clean")
    coverage = (
        record.get("engine_coverage")
        if isinstance(record.get("engine_coverage"), dict)
        else {}
    )
    missing_engines = coverage.get("missing")
    if (
        not isinstance(missing_engines, list)
        or any(not isinstance(name, str) for name in missing_engines)
        or coverage.get("missing_count") != len(missing_engines)
    ):
        problems.append("accelerator engine coverage is malformed")
    else:
        required_missing = sorted(
            set(missing_engines) - OPTIONAL_UNIMPLEMENTED_ENGINES
        )
        if required_missing:
            problems.append(
                "accelerator required engine coverage is incomplete: "
                + ", ".join(required_missing)
            )

    implementation = record.get("implementation_identity")
    if (
        not isinstance(implementation, dict)
        or not implementation
        or implementation.get("unavailable")
    ):
        problems.append("implementation identity is unavailable")
        implementation = {}
    sources, source_digest = _source_identity(
        record.get("source_sha256"), "record source_sha256", problems
    )
    association = record.get("executed_association")
    association_digest = None
    if not isinstance(association, dict) or not association:
        problems.append("executed numeric-association identity is absent")
    else:
        association_digest = association.get("manifest_sha256")
        unsigned = {
            key: value for key, value in association.items() if key != "manifest_sha256"
        }
        if not _is_sha256(association_digest) or association_digest != digest_of(
            unsigned
        ):
            problems.append("executed numeric-association identity is invalid")

    if batch_size > 1:
        batch = record.get("batch_execution")
        if (
            not isinstance(batch, dict)
            or batch.get("schema")
            != "opentallas.abi3.accelerator_batch_execution_member.v1"
            or batch.get("batch_execution_id") != batch_execution_id
            or batch.get("batch_size") != batch_size
            or batch.get("sequence_index") != sequence_index
            or batch.get("shared_execution") is not True
        ):
            problems.append(
                "record is not a bound member of the shared batch execution"
            )

    evidence = _acceptance_text_evidence(acceptance, sequence_index, batch_size)
    text_summary, text_problems = _check_text_evidence(
        evidence,
        record,
        contract,
        contract_sources.get("workload", {}),
        generated,
    )
    problems.extend(text_problems)

    host_steps: list[float] = []
    for step in (
        record.get("per_step", []) if isinstance(record.get("per_step"), list) else []
    ):
        wall = step.get("wall_seconds") if isinstance(step, dict) else None
        if _positive_number(wall):
            host_steps.append(_round(float(wall)))
        else:
            host_steps = []
            break
    host_wall = record.get("wall_seconds")
    host_observation = {
        "measurement_class": "host_functional_simulator_observation",
        "eligible_for_target_tpot": False,
        "used_for_target_tpot": False,
        "wall_seconds": _round(float(host_wall))
        if _positive_number(host_wall)
        else None,
        "ttft_seconds": host_steps[0]
        if len(host_steps) == len(generated) and host_steps
        else None,
        "decode_step_latencies_seconds": host_steps[1:]
        if len(host_steps) == len(generated)
        else [],
    }
    return {
        "sequence_index": sequence_index,
        "path": _display(path),
        "sha256": artifact_sha256,
        "record": record,
        "generated": list(generated),
        "generated_token_ids_sha256": digest_of(list(generated)),
        "prompt_count": len(prompt) if isinstance(prompt, list) else 0,
        "correct_token_count": correct,
        "first_divergence_index": first_divergence,
        "stop_reason": record.get("stop_reason"),
        "terminal_kind": terminal,
        "first_eos_index": first_eos,
        "no_post_eos_step": terminal == "cap"
        or (terminal == "eos" and first_eos == len(generated) - 1),
        "text_evidence": text_summary,
        "host_functional_timing": host_observation,
        "source_manifest_sha256": source_digest,
        "implementation_identity_sha256": digest_of(implementation)
        if implementation
        else None,
        "association_manifest_sha256": association_digest,
        "sources": sources,
        "problems": problems,
        "passes": not problems,
    }


def _rejected_record_row(
    sequence_index: int, path: Path, artifact_sha256: str, problem: str
) -> dict[str, Any]:
    """Keep malformed referenced records inside a schema-valid rejected report."""

    return {
        "sequence_index": sequence_index,
        "path": _display(path),
        "sha256": artifact_sha256,
        "record": {},
        "generated": [],
        "generated_token_ids_sha256": digest_of([]),
        "prompt_count": 0,
        "correct_token_count": 0,
        "first_divergence_index": None,
        "stop_reason": None,
        "terminal_kind": None,
        "first_eos_index": None,
        "no_post_eos_step": False,
        "text_evidence": {},
        "host_functional_timing": {
            "measurement_class": "host_functional_simulator_observation",
            "eligible_for_target_tpot": False,
            "used_for_target_tpot": False,
            "wall_seconds": None,
            "ttft_seconds": None,
            "decode_step_latencies_seconds": [],
        },
        "source_manifest_sha256": None,
        "implementation_identity_sha256": None,
        "association_manifest_sha256": None,
        "sources": {},
        "problems": [problem],
        "passes": False,
    }


def _acceptance_binds_records(
    acceptance: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    problems: list[str],
) -> None:
    accepted_rows = acceptance.get("records")
    if not isinstance(accepted_rows, list):
        problems.append("correctness acceptance has no record bindings")
        return
    for row in rows:
        path = _resolve(row["path"])
        digest = row["sha256"]
        matches = []
        for accepted in accepted_rows:
            if not isinstance(accepted, dict):
                continue
            accepted_path = _resolve(accepted.get("path"))
            if accepted.get("sha256") == digest and accepted_path == path:
                matches.append(accepted)
        if len(matches) != 1:
            problems.append(
                f"correctness acceptance does not uniquely bind sequence {row['sequence_index']}"
            )
        elif matches[0].get("passes") is not True or matches[0].get("problems") != []:
            problems.append(
                f"correctness acceptance record {row['sequence_index']} did not pass"
            )
        else:
            accepted = matches[0]
            record = _mapping(row.get("record"))
            optional_identities = {
                "backend": record.get("backend"),
                "terminal_kind": row.get("terminal_kind"),
                "association_manifest_sha256": row.get("association_manifest_sha256"),
            }
            for name, expected in optional_identities.items():
                if name in accepted and accepted.get(name) != expected:
                    problems.append(
                        f"correctness acceptance record {row['sequence_index']} "
                        f"has a mismatched {name}"
                    )


def _check_cosimulation_proof(
    raw_ref: object,
    contract: Mapping[str, Any],
    contract_sha256: str,
    acceptance_sha256: str,
    role: str,
    rows: Sequence[Mapping[str, Any]],
    batch_size: int,
    concurrency: int,
    batch_execution_id: str | None,
) -> tuple[dict[str, Any], list[str]]:
    """Authenticate the distinct RTL-bound accelerated co-simulation tier.

    The ordinary accelerator-token records remain the independently
    oracle-qualified numerical evidence. This proof binds the same token
    sequences and execution identity to an RTL-owned system run, and binds each
    accelerated engine to current bit- and cycle-equivalence artifacts. It is
    intentionally not a way to rename that run as monolithic full RTL.
    """

    problems: list[str] = []
    empty = {
        "status": "missing",
        "path": None,
        "sha256": None,
        "cosimulation_execution_id": None,
        "accelerated_engine_families": [],
        "engine_proof_count": 0,
        "proof": {},
    }
    path, artifact_sha = _file_ref(
        raw_ref,
        "rtl_bound_accelerated_cosimulation_proof",
        problems,
    )
    if path is None or not path.is_file() or artifact_sha is None:
        return {**empty, "status": "rejected"}, problems
    try:
        proof = _load(path)
    except (OSError, EvidenceError) as exc:
        problems.append(
            "RTL-bound accelerated co-simulation proof is not valid governed "
            f"JSON: {exc}"
        )
        return {
            **empty,
            "status": "rejected",
            "path": _display(path),
            "sha256": artifact_sha,
        }, problems

    problems.extend(
        _schema_problems(
            proof,
            COSIM_PROOF_SCHEMA_PATH,
            "RTL-bound accelerated co-simulation proof",
        )
    )
    if proof.get("schema") != COSIM_PROOF_SCHEMA:
        problems.append("unsupported RTL-bound co-simulation proof schema")
    if proof.get("evidence_tier") != COSIM_TIER:
        problems.append(
            "co-simulation evidence cannot be relabeled as full RTL-generated tokens"
        )
    if proof.get("monolithic_full_rtl") is not False:
        problems.append(
            "RTL-bound accelerated co-simulation is not monolithic full RTL"
        )
    if (
        proof.get("status") != "pass"
        or proof.get("problems") != []
        or proof.get("full_workload_execution") is not True
        or proof.get("token_source") != "rtl_selection_token_append_eos_path"
    ):
        problems.append("co-simulation proof is not a passing full-workload proof")

    injection = _mapping(proof.get("injection_policy"))
    if (
        injection.get("host_tensor_or_result_injection") is not False
        or injection.get("oracle_tensor_or_result_injection") is not False
        or injection.get("precomputed_activations_logits_routes_or_tokens") is not False
        or injection.get("accelerated_models_can_read_oracle") is not False
        or injection.get("harness_only_transports_handshakes") is not True
    ):
        problems.append(
            "co-simulation proof permits host/oracle tensor or model-result injection"
        )

    _file_ref(proof.get("producer"), "co-simulation proof producer", problems)

    model = _mapping(contract.get("model"))
    workload = _mapping(contract.get("workload"))
    policy = _mapping(contract.get("policy"))
    target_contract = _target_for_role(contract, role)

    def one_identity(name: str, values: set[object]) -> object:
        if len(values) != 1 or None in values:
            problems.append(
                f"co-simulation proof cannot bind one {name} execution identity"
            )
            return None
        return next(iter(values))

    capability_digest = one_identity(
        "capability",
        {
            _mapping(_mapping(row.get("record")).get("target")).get("capability_digest")
            for row in rows
        },
    )
    deployment_digest = one_identity(
        "deployment",
        {
            _mapping(_mapping(row.get("record")).get("target")).get("deployment_digest")
            for row in rows
        },
    )
    source_manifest = one_identity(
        "source manifest", {row.get("source_manifest_sha256") for row in rows}
    )
    implementation_identity = one_identity(
        "implementation", {row.get("implementation_identity_sha256") for row in rows}
    )
    expected_target = {
        "target_id": target_contract.get("target_id"),
        "backend": target_contract.get("backend"),
        "node_count": target_contract.get("node_count"),
        "topology_class": target_contract.get("topology_class"),
        "capability_digest": capability_digest,
        "deployment_digest": deployment_digest,
        "technology_view": policy.get("technology_view"),
        "source_manifest_sha256": source_manifest,
        "implementation_identity_sha256": implementation_identity,
    }
    expected_identity = {
        "batch_execution_id": batch_execution_id,
        "batch_size": batch_size,
        "comparison_contract_sha256": contract_sha256,
        "comparison_id": contract.get("comparison_id"),
        "concurrency": concurrency,
        "correctness_acceptance_sha256": acceptance_sha256,
        "external_oracle_sha256": _mapping(contract.get("external_oracle")).get(
            "source_sha256"
        ),
        "graph_id": model.get("graph_id"),
        "kernel_ir_source_sha256": model.get("kernel_ir_source_sha256"),
        "latency_boundary": policy.get("latency_boundary"),
        "model_id": model.get("model_id"),
        "numeric_profile": model.get("numeric_profile"),
        "pvt": policy.get("pvt"),
        "target": expected_target,
        "tokenizer_sha256": workload.get("tokenizer_sha256"),
        "workload_digest": workload.get("digest"),
        "workload_id": workload.get("workload_id"),
    }
    identity = _mapping(proof.get("execution_identity"))
    for name, expected in expected_identity.items():
        if identity.get(name) != expected:
            problems.append(
                f"co-simulation proof execution identity {name} is not exact"
            )

    bindings = proof.get("execution_records")
    expected_bindings = [
        {
            "sequence_index": row.get("sequence_index"),
            "path": row.get("path"),
            "sha256": row.get("sha256"),
        }
        for row in rows
    ]
    normalized: list[dict[str, Any]] = []
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            binding_path = _resolve(binding.get("path"))
            normalized.append(
                {
                    "sequence_index": binding.get("sequence_index"),
                    "path": _display(binding_path)
                    if binding_path is not None
                    else None,
                    "sha256": binding.get("sha256"),
                }
            )
    if sorted(normalized, key=lambda item: str(item.get("sequence_index"))) != sorted(
        expected_bindings, key=lambda item: str(item.get("sequence_index"))
    ):
        problems.append("co-simulation proof accelerator-record bindings are not exact")

    sequence_rows = proof.get("sequences")
    sequence_by_index = (
        {
            item.get("sequence_index"): item
            for item in sequence_rows
            if isinstance(item, dict) and _integer(item.get("sequence_index"))
        }
        if isinstance(sequence_rows, list)
        else {}
    )
    if len(sequence_by_index) != len(rows):
        problems.append(
            "co-simulation proof sequence identities are not unique and complete"
        )
    for row in rows:
        sequence_index = row.get("sequence_index")
        sequence = _mapping(sequence_by_index.get(sequence_index))
        expected_sequence = {
            "sequence_index": sequence_index,
            "generated_token_ids": row.get("generated"),
            "generated_token_ids_sha256": row.get("generated_token_ids_sha256"),
            "generated_token_count": len(row.get("generated", [])),
            "terminal_kind": row.get("terminal_kind"),
            "first_eos_index": row.get("first_eos_index"),
            "no_post_eos_execution": row.get("no_post_eos_step"),
            "token_source": "rtl_selection_token_append_eos_path",
        }
        for name, expected in expected_sequence.items():
            if sequence.get(name) != expected:
                problems.append(
                    f"co-simulation sequence {sequence_index} {name} is not exact"
                )

    rtl_components = proof.get("rtl_owned_components")
    rtl_component_set = (
        {value for value in rtl_components if isinstance(value, str)}
        if isinstance(rtl_components, list)
        else set()
    )
    if (
        not isinstance(rtl_components, list)
        or len(rtl_components) != len(rtl_component_set)
        or rtl_component_set != REQUIRED_COSIM_RTL_COMPONENTS
    ):
        problems.append(
            "co-simulation proof does not bind every required RTL-owned system component"
        )

    declared_families = proof.get("accelerated_engine_families")
    declared_set = (
        {value for value in declared_families if isinstance(value, str)}
        if isinstance(declared_families, list)
        else set()
    )
    engine_rows = proof.get("engine_equivalence_proofs")
    engine_rows = engine_rows if isinstance(engine_rows, list) else []
    proved_families = [
        engine.get("engine_family")
        for engine in engine_rows
        if isinstance(engine, dict)
    ]
    proved_set = {value for value in proved_families if isinstance(value, str)}
    if (
        not declared_set
        or len(proved_families) != len(proved_set)
        or proved_set != declared_set
    ):
        problems.append(
            "accelerated engine families do not have one proof row per engine"
        )
    equivalence_fields = {
        "all_executed_modes_covered",
        "architectural_counters_exact",
        "backpressure_and_stalls_exact",
        "completion_cycle_exact",
        "fault_and_refusal_exact",
        "memory_transactions_exact",
        "result_bits_exact",
        "start_cycle_exact",
    }
    for index, raw_engine in enumerate(engine_rows):
        engine = _mapping(raw_engine)
        label = f"engine_equivalence_proofs[{index}]"
        for name in (
            "accelerated_model_source",
            "bit_equivalence_proof",
            "cycle_equivalence_proof",
            "executed_mode_manifest",
            "synthesizable_rtl_manifest",
        ):
            _file_ref(engine.get(name), f"{label}.{name}", problems)
        equivalence = _mapping(engine.get("equivalence"))
        if (
            engine.get("status") != "pass"
            or engine.get("problems") != []
            or any(equivalence.get(name) is not True for name in equivalence_fields)
        ):
            problems.append(f"{label} is not a complete bit/cycle equivalence proof")

    timing = _mapping(proof.get("timing_qualification"))
    _file_ref(
        timing.get("characterization_artifact"),
        "co-simulation timing characterization",
        problems,
    )
    cost_lock = _mapping(_mapping(target_contract.get("cost_policy")).get("lock"))
    expected_timing = {
        "clock_frequency_hz": _mapping(policy.get("clock")).get(
            "comparison_frequency_hz"
        ),
        "cost_table_sha256": cost_lock.get("source_sha256"),
        "depends_on_assumed_values": False,
        "implementation_identity_sha256": implementation_identity,
        "measurement_class": COSIM_TIER,
        "pvt": policy.get("pvt"),
        "simulator_wall_time_used_as_target_time": False,
        "status": "characterized",
        "target_cycles_from_architectural_events": True,
        "technology_view": policy.get("technology_view"),
    }
    for name, expected in expected_timing.items():
        if timing.get(name) != expected:
            problems.append(
                f"co-simulation timing qualification {name} is not characterized "
                "for the exact execution"
            )

    return {
        "status": "accepted" if not problems else "rejected",
        "path": _display(path),
        "sha256": artifact_sha,
        "cosimulation_execution_id": proof.get("cosimulation_execution_id")
        if _is_sha256(proof.get("cosimulation_execution_id"))
        else None,
        "accelerated_engine_families": sorted(
            str(value) for value in declared_set if isinstance(value, str)
        ),
        "engine_proof_count": len(engine_rows),
        "proof": proof,
    }, problems


def _budget(contract: Mapping[str, Any], role: str | None) -> dict[str, Any]:
    execution = contract.get("execution")
    raw = execution.get("tpot_acceptance") if isinstance(execution, dict) else None
    if not isinstance(raw, dict):
        return {
            "status": "budget_missing",
            "target_role": role,
            "batch_size": execution.get("batch")
            if isinstance(execution, dict)
            else None,
            "metric": "per_sequence_steady_state_decode_step_latency_seconds",
            "statistic": None,
            "maximum_seconds": None,
            "steady_state_start_decode_step": None,
            "eligible_measurement_classes": [],
            "assumption_dependent_evidence_allowed": None,
        }
    roles = raw.get("roles")
    role_budget = (
        roles.get(role) if isinstance(roles, dict) and role is not None else None
    )
    if not isinstance(role_budget, dict):
        return {
            "status": "budget_missing",
            "target_role": role,
            "batch_size": raw.get("batch_size"),
            "metric": "per_sequence_steady_state_decode_step_latency_seconds",
            "statistic": None,
            "maximum_seconds": None,
            "steady_state_start_decode_step": raw.get("steady_state_start_decode_step"),
            "eligible_measurement_classes": [],
            "assumption_dependent_evidence_allowed": None,
        }
    valid = (
        raw.get("schema") == "opentallas.abi3.tpot_acceptance_budget.v1"
        and raw.get("batch_size") == execution.get("batch")
        and raw.get("metric") == "per_sequence_steady_state_decode_step_latency_seconds"
        and _integer(raw.get("steady_state_start_decode_step"))
        and role_budget.get("statistic") in {"p50", "p95", "p99", "max"}
        and _positive_number(role_budget.get("maximum_seconds"))
        and isinstance(role_budget.get("eligible_measurement_classes"), list)
        and bool(role_budget.get("eligible_measurement_classes"))
        and len(set(role_budget["eligible_measurement_classes"]))
        == len(role_budget["eligible_measurement_classes"])
        and all(
            item in TARGET_MEASUREMENT_CLASSES
            for item in role_budget["eligible_measurement_classes"]
        )
        and isinstance(role_budget.get("assumption_dependent_evidence_allowed"), bool)
    )
    return {
        "status": "present" if valid else "invalid",
        "target_role": role,
        "batch_size": raw.get("batch_size"),
        "metric": raw.get("metric"),
        "statistic": role_budget.get("statistic"),
        "maximum_seconds": role_budget.get("maximum_seconds"),
        "steady_state_start_decode_step": raw.get("steady_state_start_decode_step"),
        "eligible_measurement_classes": role_budget.get(
            "eligible_measurement_classes", []
        ),
        "assumption_dependent_evidence_allowed": role_budget.get(
            "assumption_dependent_evidence_allowed"
        ),
    }


def _check_target_locks(
    target: Mapping[str, Any], trace: Mapping[str, Any], problems: list[str]
) -> None:
    trace_target = trace.get("target")
    if not isinstance(trace_target, dict):
        trace_target = {}
    for name in ("capability", "deployment"):
        lock = target.get(name)
        if not isinstance(lock, dict) or lock.get("status") != "locked":
            problems.append(f"comparison target {name} lock is not frozen")
            continue
        if name == "deployment":
            _check_bound_deployment(
                lock.get("path"),
                lock.get("source_sha256"),
                "target deployment",
                problems,
            )
        else:
            _check_bound_file(
                lock.get("path"),
                lock.get("source_sha256"),
                "target capability",
                problems,
            )
        expected_digest = lock.get("digest")
        trace_key = f"{name}_digest"
        if (
            not _is_sha256(expected_digest)
            or trace_target.get(trace_key) != expected_digest
        ):
            problems.append(f"target timing {trace_key} differs from its locked target")
    cost = target.get("cost_policy")
    lock = cost.get("lock") if isinstance(cost, dict) else None
    if not isinstance(lock, dict) or lock.get("status") != "locked":
        problems.append("comparison target cost-table lock is not frozen")
    else:
        cost_path = _check_bound_file(
            lock.get("path"), lock.get("source_sha256"), "target cost table", problems
        )
        if cost_path is not None and cost_path.is_file():
            try:
                cost_body = _load(cost_path)
            except (OSError, EvidenceError) as exc:
                problems.append(f"target cost table is not valid governed JSON: {exc}")
            else:
                if (
                    cost_body.get("schema") != "opentallas.abi3.cost_table.v1"
                    or cost_body.get("cost_table_id") != cost.get("cost_table_id")
                    or cost_body.get("technology_view") != trace.get("technology_view")
                ):
                    problems.append(
                        "target cost table does not bind the same process view"
                    )
        timing_cost = trace.get("cost_table")
        if not isinstance(timing_cost, dict) or (
            timing_cost.get("cost_table_id") != cost.get("cost_table_id")
            or timing_cost.get("path") != lock.get("path")
            or timing_cost.get("sha256") != lock.get("source_sha256")
        ):
            problems.append(
                "target timing cost-table identity is not the locked policy"
            )


def _timing_metrics(
    trace: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    steady_start: int,
    problems: list[str],
) -> dict[str, Any]:
    def distribution(samples: Sequence[int], frequency: float) -> dict[str, Any]:
        ordered = sorted(samples)

        def nearest_rank(percentile: float) -> float:
            index = max(0, math.ceil(percentile * len(ordered)) - 1)
            return _round(ordered[index] / frequency)

        return {
            "sample_count": len(ordered),
            "statistic_policy": "nearest_rank_over_raw_per_sequence_decode_intervals",
            "mean": _round(sum(ordered) / len(ordered) / frequency),
            "p50": nearest_rank(0.50),
            "p95": nearest_rank(0.95),
            "p99": nearest_rank(0.99),
            "max": _round(ordered[-1] / frequency),
        }

    timebase = trace.get("timebase") if isinstance(trace.get("timebase"), dict) else {}
    ticks_per_second = timebase.get("ticks_per_second")
    if not _positive_number(ticks_per_second):
        problems.append("target timing trace has no positive ticks_per_second")
        return {}
    frequency = float(ticks_per_second)
    trace_sequences = trace.get("sequences")
    if not isinstance(trace_sequences, list) or len(trace_sequences) != len(rows):
        problems.append("target timing trace sequence count differs from the batch")
        return {}
    by_index = {
        item.get("sequence_index"): item
        for item in trace_sequences
        if isinstance(item, dict) and _integer(item.get("sequence_index"))
    }
    if len(by_index) != len(rows):
        problems.append(
            "target timing trace sequence indices are not unique and complete"
        )
        return {}
    sequence_metrics: list[dict[str, Any]] = []
    steady_windows: list[tuple[int, int]] = []
    end_to_end_start: list[int] = []
    end_to_end_end: list[int] = []
    total_generated = 0
    for row in rows:
        index = int(row["sequence_index"])
        timing = by_index.get(index)
        if not isinstance(timing, dict):
            problems.append(f"target timing has no sequence {index}")
            continue
        execution_timing, execution_timing_problems = _record_execution_timing(
            row["record"], row["generated"]
        )
        if execution_timing_problems:
            problems.extend(
                f"sequence {index}: {problem}"
                for problem in execution_timing_problems
            )
            continue
        request_start = timing.get("request_start_tick")
        commits = timing.get("token_commit_ticks")
        if (
            not _integer(request_start)
            or not isinstance(commits, list)
            or len(commits) != len(row["generated"])
        ):
            problems.append(
                f"target timing sequence {index} has the wrong raw timeline"
            )
            continue
        if not commits or any(not _integer(value) for value in commits):
            problems.append(f"target timing sequence {index} has invalid commit ticks")
            continue
        values = [int(value) for value in commits]
        if (
            execution_timing.get("unit") != timebase.get("unit")
            or execution_timing.get("request_start_tick") != request_start
            or execution_timing.get("token_commit_ticks") != values
        ):
            problems.append(
                f"target timing sequence {index} differs from the raw timeline "
                "retained by its token-producing execution"
            )
            continue
        if values[0] <= int(request_start) or any(
            values[offset] <= values[offset - 1] for offset in range(1, len(values))
        ):
            problems.append(f"target timing sequence {index} is not strictly causal")
            continue
        decode_ticks = [
            values[offset] - values[offset - 1] for offset in range(1, len(values))
        ]
        if steady_start >= len(decode_ticks):
            problems.append(
                f"target timing sequence {index} has no interval in its steady-state window"
            )
            continue
        steady = decode_ticks[steady_start:]
        raw = [
            {
                "generated_token_index": offset + 1,
                "latency_ticks": ticks,
                "latency_seconds": _round(ticks / frequency),
            }
            for offset, ticks in enumerate(decode_ticks)
        ]
        selected_start_tick = values[steady_start]
        selected_end_tick = values[-1]
        steady_windows.extend(
            (values[offset - 1], values[offset])
            for offset in range(steady_start + 1, len(values))
        )
        end_to_end_start.append(int(request_start))
        end_to_end_end.append(values[-1])
        total_generated += len(values)
        sequence_metrics.append(
            {
                "sequence_index": index,
                "request_start_tick": int(request_start),
                "token_commit_ticks": values,
                "ttft_ticks": values[0] - int(request_start),
                "ttft_seconds": _round((values[0] - int(request_start)) / frequency),
                "raw_decode_step_latencies": raw,
                "warm_decode_step_count": steady_start,
                "steady_state_decode_step_count": len(steady),
                "steady_state_window_start_tick": selected_start_tick,
                "steady_state_window_end_tick": selected_end_tick,
                "steady_state_tpot_seconds": _round(
                    sum(steady) / len(steady) / frequency
                ),
                "steady_state_tpot_distribution_seconds": distribution(
                    steady, frequency
                ),
            }
        )
    if problems or len(sequence_metrics) != len(rows):
        return {}
    tpot_values = [
        float(item["steady_state_tpot_seconds"]) for item in sequence_metrics
    ]
    steady_tick_samples = [end - start for start, end in steady_windows]
    aggregate_start = min(start for start, _end in steady_windows)
    aggregate_end = max(end for _start, end in steady_windows)
    steady_tokens = len(steady_windows)
    return {
        "timebase": {
            "unit": timebase.get("unit"),
            "ticks_per_second": ticks_per_second,
            "clock_frequency_hz": timebase.get("clock_frequency_hz"),
        },
        "sequence_metrics": sorted(
            sequence_metrics, key=lambda item: item["sequence_index"]
        ),
        "batch_metrics": {
            "batch_size": len(rows),
            "total_generated_tokens": total_generated,
            "total_steady_state_decode_tokens": steady_tokens,
            "per_sequence_steady_state_decode_step_latency_seconds": distribution(
                steady_tick_samples, frequency
            ),
            "mean_per_sequence_steady_state_tpot_seconds": _round(
                sum(tpot_values) / len(tpot_values)
            ),
            "maximum_per_sequence_steady_state_tpot_seconds": _round(max(tpot_values)),
            "aggregate_steady_state_window_seconds": _round(
                (aggregate_end - aggregate_start) / frequency
            ),
            "aggregate_steady_state_tokens_per_second": _round(
                steady_tokens * frequency / (aggregate_end - aggregate_start)
            ),
            "aggregate_end_to_end_window_seconds": _round(
                (max(end_to_end_end) - min(end_to_end_start)) / frequency
            ),
            "aggregate_end_to_end_generated_tokens_per_second": _round(
                total_generated
                * frequency
                / (max(end_to_end_end) - min(end_to_end_start))
            ),
        },
    }


def _check_timing(
    raw_ref: object,
    contract: Mapping[str, Any],
    contract_sha256: str,
    acceptance_sha256: str,
    role: str,
    rows: Sequence[Mapping[str, Any]],
    budget: Mapping[str, Any],
    required_tier: str,
    cosimulation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    if raw_ref is None:
        return {"status": "missing", "metrics": None}, problems
    path, artifact_sha = _file_ref(raw_ref, "target_timing_trace", problems)
    if path is None or not path.is_file() or artifact_sha is None:
        return {"status": "rejected", "metrics": None}, problems
    try:
        trace = _load(path)
    except (OSError, EvidenceError) as exc:
        problems.append(f"target timing trace is not valid governed JSON: {exc}")
        return {
            "status": "rejected",
            "path": _display(path),
            "sha256": artifact_sha,
            "metrics": None,
        }, problems
    schema = trace.get("schema")
    if schema != TRACE_SCHEMA:
        if schema in PROJECTION_SCHEMAS or "roofline" in str(schema).lower():
            problems.append("projection-only artifact is ineligible for target TPOT")
        elif schema == RECORD_SCHEMA:
            problems.append(
                "functional host execution record is ineligible as target timing"
            )
        else:
            problems.append(f"unsupported target timing schema {schema!r}")
        return {
            "status": "rejected",
            "path": _display(path),
            "sha256": artifact_sha,
            "metrics": None,
        }, problems
    trace_schema_problems = _schema_problems(
        trace, TRACE_SCHEMA_PATH, "target timing trace"
    )
    if trace_schema_problems:
        problems.extend(trace_schema_problems)
        return {
            "status": "rejected",
            "path": _display(path),
            "sha256": artifact_sha,
            "measurement_class": (
                trace.get("measurement_class")
                if trace.get("measurement_class") in TARGET_MEASUREMENT_CLASSES
                else None
            ),
            "claim_class": TARGET_MEASUREMENT_CLASSES.get(
                str(trace.get("measurement_class"))
            ),
            "projection_only": (
                trace.get("projection_only")
                if isinstance(trace.get("projection_only"), bool)
                else None
            ),
            "provenance": None,
            "production_high_fidelity": False,
            "metrics": None,
        }, problems
    measurement_class = trace.get("measurement_class")
    if measurement_class not in TARGET_MEASUREMENT_CLASSES:
        problems.append("target timing measurement class is absent or ineligible")
    if measurement_class == COSIM_TIER:
        if required_tier != COSIM_TIER:
            problems.append(
                "RTL-bound accelerated co-simulation timing cannot qualify a "
                "different correctness tier"
            )
        if cosimulation.get("status") != "accepted":
            problems.append(
                "RTL-bound accelerated co-simulation timing has no accepted proof"
            )
        trace_proof = _mapping(trace.get("rtl_bound_accelerated_cosimulation_proof"))
        trace_proof_path = _resolve(trace_proof.get("path"))
        expected_proof_path = _resolve(cosimulation.get("path"))
        if (
            trace.get("execution_tier") != COSIM_TIER
            or trace.get("cosimulation_execution_id")
            != cosimulation.get("cosimulation_execution_id")
            or trace_proof.get("sha256") != cosimulation.get("sha256")
            or trace_proof_path is None
            or expected_proof_path is None
            or trace_proof_path != expected_proof_path
        ):
            problems.append(
                "target timing does not bind the exact co-simulation execution proof"
            )
        if trace.get("simulator_wall_time_used_as_target_time") is not False:
            problems.append(
                "co-simulation simulator wall time is ineligible as target timing"
            )
    elif required_tier == COSIM_TIER:
        problems.append(
            "RTL-bound accelerated co-simulation correctness requires its explicit "
            "co-simulation timing class"
        )
    if (
        trace.get("evidence_class") != "executed_target_timing_trace"
        or trace.get("projection_only") is not False
        or trace.get("counterfactual_or_extrapolated") is not False
        or trace.get("full_workload_execution") is not True
        or trace.get("token_commits_from_execution") is not True
    ):
        problems.append("timing trace is not a raw, executed full-workload trace")
    producer = trace.get("producer") if isinstance(trace.get("producer"), dict) else {}
    _check_current_artifact_identity(
        producer.get("tool"), producer.get("source_sha256"), "timing producer", problems
    )
    provenance = (
        trace.get("provenance") if isinstance(trace.get("provenance"), dict) else {}
    )
    if provenance.get("class") not in {
        "assumed",
        "characterized",
        "mixed",
        "measured",
    } or not isinstance(provenance.get("depends_on_assumed_values"), bool):
        problems.append("target timing provenance is absent or invalid")
    if measurement_class == COSIM_TIER and (
        provenance.get("class") not in {"characterized", "measured"}
        or provenance.get("depends_on_assumed_values") is not False
    ):
        problems.append(
            "RTL-bound accelerated co-simulation timing is not characterized"
        )
    timebase = trace.get("timebase") if isinstance(trace.get("timebase"), dict) else {}
    if measurement_class == "silicon_measurement":
        if (
            timebase.get("unit") != "nanoseconds"
            or timebase.get("ticks_per_second") != 1_000_000_000
            or timebase.get("clock_frequency_hz") is not None
        ):
            problems.append("silicon timing must use the explicit nanosecond timebase")
    elif measurement_class in TARGET_MEASUREMENT_CLASSES:
        if (
            timebase.get("unit") != "cycles"
            or not _integer(timebase.get("clock_frequency_hz"), minimum=1)
            or timebase.get("ticks_per_second") != timebase.get("clock_frequency_hz")
        ):
            problems.append(
                "simulated target timing must use its exact clock-cycle timebase"
            )
    execution = (
        contract.get("execution") if isinstance(contract.get("execution"), dict) else {}
    )
    policy = contract.get("policy") if isinstance(contract.get("policy"), dict) else {}
    clock_policy = _mapping(policy.get("clock"))
    if measurement_class != "silicon_measurement" and (
        not _integer(clock_policy.get("comparison_frequency_hz"), minimum=1)
        or timebase.get("clock_frequency_hz")
        != clock_policy.get("comparison_frequency_hz")
    ):
        problems.append(
            "simulated target clock differs from the frozen same-process clock policy"
        )
    target_contract = _target_for_role(contract, role)
    trace_target = trace.get("target") if isinstance(trace.get("target"), dict) else {}
    expected_trace = {
        "comparison_id": contract.get("comparison_id"),
        "comparison_contract_sha256": contract_sha256,
        "correctness_acceptance_sha256": acceptance_sha256,
        "model_id": (contract.get("model") or {}).get("model_id"),
        "graph_id": (contract.get("model") or {}).get("graph_id"),
        "workload_id": (contract.get("workload") or {}).get("workload_id"),
        "workload_digest": (contract.get("workload") or {}).get("digest"),
        "latency_boundary": policy.get("latency_boundary"),
        "technology_view": policy.get("technology_view"),
        "pvt": policy.get("pvt"),
        "batch_size": execution.get("batch"),
        "concurrency": execution.get("concurrency"),
        "batch_execution_id": (
            rows[0]["record"].get("batch_execution", {}).get("batch_execution_id")
            if len(rows) > 1
            and isinstance(rows[0]["record"].get("batch_execution"), dict)
            else None
        ),
    }
    for name, expected in expected_trace.items():
        if trace.get(name) != expected:
            problems.append(
                f"target timing {name} differs from the comparison contract"
            )
    for name in ("target_id", "backend", "node_count", "topology_class"):
        if trace_target.get(name) != target_contract.get(name):
            problems.append(f"target timing target.{name} differs from the contract")
    bindings = trace.get("execution_records")
    if not isinstance(bindings, list) or len(bindings) != len(rows):
        problems.append(
            "target timing does not bind every accelerator execution record"
        )
    else:
        expected_bindings = [
            {
                "sequence_index": row["sequence_index"],
                "path": row["path"],
                "sha256": row["sha256"],
            }
            for row in rows
        ]
        normalized = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            path_value = _resolve(binding.get("path"))
            normalized.append(
                {
                    "sequence_index": binding.get("sequence_index"),
                    "path": _display(path_value) if path_value is not None else None,
                    "sha256": binding.get("sha256"),
                }
            )
        if sorted(normalized, key=lambda item: str(item["sequence_index"])) != sorted(
            expected_bindings, key=lambda item: str(item["sequence_index"])
        ):
            problems.append("target timing accelerator-record bindings are not exact")
    common_identities = {
        "capability_digest": {
            row["record"].get("target", {}).get("capability_digest") for row in rows
        },
        "deployment_digest": {
            row["record"].get("target", {}).get("deployment_digest") for row in rows
        },
        "source_manifest_sha256": {row.get("source_manifest_sha256") for row in rows},
        "implementation_identity_sha256": {
            row.get("implementation_identity_sha256") for row in rows
        },
    }
    for name, values in common_identities.items():
        if (
            len(values) != 1
            or None in values
            or trace_target.get(name) != next(iter(values))
        ):
            problems.append(
                f"target timing {name} does not bind one execution identity"
            )
    if trace_target.get("technology_view") != rows[0]["record"].get("target", {}).get(
        "technology_view"
    ):
        problems.append(
            "target timing technology view differs from the execution record"
        )
    _check_target_locks(target_contract, trace, problems)

    trace_start = trace.get("steady_state_start_decode_step")
    if not _integer(trace_start):
        problems.append("target timing has no valid steady-state start index")
        trace_start = 0
    if budget.get("status") == "present" and trace_start != budget.get(
        "steady_state_start_decode_step"
    ):
        problems.append("timing steady-state window differs from the frozen budget")
    if budget.get("status") == "present" and measurement_class not in budget.get(
        "eligible_measurement_classes", []
    ):
        problems.append(
            "timing measurement class is not eligible under the frozen budget"
        )
    if (
        budget.get("status") == "present"
        and provenance.get("depends_on_assumed_values") is True
        and budget.get("assumption_dependent_evidence_allowed") is not True
    ):
        problems.append("assumption-dependent timing is forbidden by the frozen budget")
    metrics: dict[str, Any] = {}
    if not problems:
        metrics = _timing_metrics(trace, rows, int(trace_start), problems)
    return {
        "status": "accepted" if not problems else "rejected",
        "path": _display(path),
        "sha256": artifact_sha,
        "measurement_class": measurement_class,
        "claim_class": TARGET_MEASUREMENT_CLASSES.get(str(measurement_class)),
        "projection_only": trace.get("projection_only"),
        "provenance": provenance or None,
        "production_high_fidelity": (
            not problems
            and provenance.get("depends_on_assumed_values") is False
            and (
                (
                    measurement_class
                    in {
                        COSIM_TIER,
                        "rtl_cycle_simulation",
                        "post_layout_timing_simulation",
                    }
                    and provenance.get("class") in {"characterized", "measured"}
                )
                or (
                    measurement_class == "silicon_measurement"
                    and provenance.get("class") == "measured"
                )
            )
        ),
        "cosimulation_execution_id": trace.get("cosimulation_execution_id")
        if measurement_class == COSIM_TIER
        else None,
        "cosimulation_proof_sha256": (
            _mapping(trace.get("rtl_bound_accelerated_cosimulation_proof")).get(
                "sha256"
            )
            if measurement_class == COSIM_TIER
            else None
        ),
        "metrics": metrics or None,
    }, problems


def _point(raw: Mapping[str, Any]) -> dict[str, Any]:
    point_id = str(raw.get("point_id"))
    role = raw.get("target_role")
    problems: list[str] = []
    contract_path, contract, contract_sha = _load_contract(
        raw.get("comparison_contract"), problems
    )
    contract_sources = _check_contract_sources(contract, problems) if contract else {}
    acceptance_path, acceptance_sha = _file_ref(
        raw.get("correctness_acceptance"), "correctness_acceptance", problems
    )
    acceptance: dict[str, Any] = {}
    if acceptance_path is not None and acceptance_path.is_file():
        try:
            acceptance = _load(acceptance_path)
        except (OSError, EvidenceError) as exc:
            problems.append(f"correctness acceptance is not valid governed JSON: {exc}")
    if acceptance:
        acceptance_problems: list[str] = []
        _acceptance_passed(acceptance, acceptance_problems)
        problems.extend(acceptance_problems)
        if acceptance.get("workload_id") != _mapping(contract.get("workload")).get(
            "workload_id"
        ):
            problems.append(
                "correctness acceptance workload differs from the comparison contract"
            )
    execution = (
        contract.get("execution") if isinstance(contract.get("execution"), dict) else {}
    )
    batch_size = execution.get("batch")
    concurrency = execution.get("concurrency")
    if not _integer(batch_size, minimum=1):
        problems.append("comparison contract batch size is invalid")
        batch_size = 0
    if not _integer(concurrency, minimum=1):
        problems.append("comparison contract concurrency is invalid")
    if role not in {"rom", "hbm"} or not _target_for_role(contract, role):
        problems.append("target_role does not select a comparison-contract target")

    refs = raw.get("execution_records")
    record_paths: list[tuple[Path, str]] = []
    if not isinstance(refs, list) or len(refs) != batch_size:
        problems.append(
            "execution_records count must equal the independently executed batch size"
        )
    else:
        for index, ref in enumerate(refs):
            path, identity = _file_ref(ref, f"execution_records[{index}]", problems)
            if path is not None and path.is_file() and identity is not None:
                record_paths.append((path, identity))
    batch_execution_id = raw.get("batch_execution_id")
    if batch_size > 1 and not _is_sha256(batch_execution_id):
        problems.append("multi-sequence point has no shared batch_execution_id")
    if batch_size == 1:
        if batch_execution_id is not None:
            problems.append("single-sequence point must use a null batch_execution_id")
        batch_execution_id = None

    required_tier = raw.get("required_correctness_tier")
    if required_tier not in {
        "functional_accelerator_execution",
        COSIM_TIER,
        "full_rtl_generated_tokens",
    }:
        problems.append("required_correctness_tier is absent or unsupported")

    rows: list[dict[str, Any]] = []
    if len(record_paths) == batch_size and contract and acceptance:
        for index, (path, identity) in enumerate(record_paths):
            try:
                rows.append(
                    _check_record(
                        path,
                        identity,
                        index,
                        int(batch_size),
                        str(batch_execution_id) if batch_execution_id else None,
                        str(role),
                        contract,
                        contract_sources,
                        acceptance,
                    )
                )
            except (OSError, EvidenceError, KeyError, TypeError, ValueError) as exc:
                rows.append(
                    _rejected_record_row(
                        index,
                        path,
                        identity,
                        f"execution record is not usable governed evidence: {exc}",
                    )
                )
        for row in rows:
            problems.extend(
                f"sequence {row['sequence_index']}: {problem}"
                for problem in row["problems"]
            )
        _acceptance_binds_records(acceptance, rows, problems)

    cosimulation: dict[str, Any] = {
        "status": "not_requested",
        "path": None,
        "sha256": None,
        "cosimulation_execution_id": None,
        "accelerated_engine_families": [],
        "engine_proof_count": 0,
        "proof": {},
    }
    if required_tier == COSIM_TIER:
        if (
            contract_sha is not None
            and acceptance_sha is not None
            and len(rows) == batch_size
            and _integer(concurrency, minimum=1)
        ):
            cosimulation, cosimulation_problems = _check_cosimulation_proof(
                raw.get("rtl_bound_accelerated_cosimulation_proof"),
                contract,
                contract_sha,
                acceptance_sha,
                str(role),
                rows,
                int(batch_size),
                int(concurrency),
                str(batch_execution_id) if batch_execution_id else None,
            )
            problems.extend(cosimulation_problems)
        else:
            problems.append(
                "RTL-bound accelerated co-simulation proof cannot be checked "
                "without exact execution identities"
            )
    elif raw.get("rtl_bound_accelerated_cosimulation_proof") is not None:
        problems.append(
            "co-simulation proof cannot be relabeled as a different correctness tier"
        )

    observed_tier = (
        COSIM_TIER
        if cosimulation.get("status") == "accepted"
        else (
            "functional_accelerator_execution"
            if acceptance.get("schema") in ACCEPTANCE_SCHEMAS
            else None
        )
    )
    rtl_bound_accelerated_cosimulation = observed_tier == COSIM_TIER
    full_rtl_generated_tokens = False
    if required_tier == "full_rtl_generated_tokens" and not full_rtl_generated_tokens:
        problems.append(
            "full RTL-generated token correctness was required but only functional "
            "accelerator-token acceptance was supplied"
        )

    gate1_pass = (
        not problems and len(rows) == batch_size and all(row["passes"] for row in rows)
    )
    budget = _budget(contract, role if role in {"rom", "hbm"} else None)
    if budget["status"] == "invalid":
        problems.append("comparison contract TPOT budget is malformed")
    timing: dict[str, Any] = {"status": "not_evaluated_gate1_failed", "metrics": None}
    timing_problems: list[str] = []
    if gate1_pass and contract_sha is not None and acceptance_sha is not None:
        timing, timing_problems = _check_timing(
            raw.get("target_timing_trace"),
            contract,
            contract_sha,
            acceptance_sha,
            str(role),
            rows,
            budget,
            str(required_tier),
            cosimulation,
        )
        problems.extend(timing_problems)

    if not gate1_pass:
        verdict = {
            "status": "gate1_failed",
            "metric": budget.get("metric"),
            "statistic": budget.get("statistic"),
            "observed_seconds": None,
            "maximum_seconds": budget.get("maximum_seconds"),
            "meets_budget": None,
        }
        point_status = "rejected"
    elif timing.get("status") == "missing":
        verdict = {
            "status": "timing_evidence_missing",
            "metric": budget.get("metric"),
            "statistic": budget.get("statistic"),
            "observed_seconds": None,
            "maximum_seconds": budget.get("maximum_seconds"),
            "meets_budget": None,
        }
        point_status = "not_evaluable"
    elif timing.get("status") != "accepted":
        verdict = {
            "status": "timing_evidence_rejected",
            "metric": budget.get("metric"),
            "statistic": budget.get("statistic"),
            "observed_seconds": None,
            "maximum_seconds": budget.get("maximum_seconds"),
            "meets_budget": None,
        }
        point_status = "rejected"
    elif budget["status"] == "budget_missing":
        verdict = {
            "status": "budget_missing",
            "metric": budget.get("metric"),
            "statistic": None,
            "observed_seconds": None,
            "maximum_seconds": None,
            "meets_budget": None,
        }
        point_status = "not_evaluable"
    elif budget["status"] != "present":
        verdict = {
            "status": "budget_invalid",
            "metric": budget.get("metric"),
            "statistic": budget.get("statistic"),
            "observed_seconds": None,
            "maximum_seconds": budget.get("maximum_seconds"),
            "meets_budget": None,
        }
        point_status = "rejected"
    else:
        metric = str(budget["metric"])
        statistic = str(budget["statistic"])
        observed = timing["metrics"]["batch_metrics"][metric][statistic]
        passed = float(observed) <= float(budget["maximum_seconds"])
        verdict = {
            "status": "pass" if passed else "fail",
            "metric": metric,
            "statistic": statistic,
            "observed_seconds": observed,
            "maximum_seconds": budget["maximum_seconds"],
            "meets_budget": passed,
        }
        point_status = "pass" if passed else "fail"

    verdict["production_gate_closed"] = bool(
        point_status == "pass"
        and timing.get("production_high_fidelity") is True
        and (rtl_bound_accelerated_cosimulation or full_rtl_generated_tokens)
    )

    sequence_summaries = [
        {
            key: row[key]
            for key in (
                "sequence_index",
                "path",
                "sha256",
                "prompt_count",
                "generated_token_ids_sha256",
                "correct_token_count",
                "first_divergence_index",
                "stop_reason",
                "terminal_kind",
                "first_eos_index",
                "no_post_eos_step",
                "text_evidence",
                "host_functional_timing",
                "source_manifest_sha256",
                "implementation_identity_sha256",
                "association_manifest_sha256",
                "passes",
                "problems",
            )
        }
        | {
            "generated_token_ids": row["generated"],
            "generated_token_count": len(row["generated"]),
        }
        for row in rows
    ]
    return {
        "point_id": point_id,
        "status": point_status,
        "comparison": {
            "comparison_id": contract.get("comparison_id"),
            "contract_path": _display(contract_path) if contract_path else None,
            "contract_sha256": contract_sha,
            "target_role": role,
            "target_id": _target_for_role(contract, role).get("target_id"),
            "process_view": (contract.get("policy") or {}).get("technology_view"),
            "pvt": (contract.get("policy") or {}).get("pvt"),
        },
        "batch": {
            "batch_size": batch_size,
            "concurrency": concurrency,
            "batch_execution_id": batch_execution_id,
            "prompt_tokens_per_sequence": [row["prompt_count"] for row in rows],
            "generated_tokens_per_sequence": [len(row["generated"]) for row in rows],
            "total_prompt_tokens": sum(row["prompt_count"] for row in rows),
            "total_generated_tokens": sum(len(row["generated"]) for row in rows),
        },
        "correctness_gate": {
            "status": "pass" if gate1_pass else "rejected",
            "gate_precedes_tpot": True,
            "acceptance_schema": acceptance.get("schema"),
            "acceptance_path": _display(acceptance_path) if acceptance_path else None,
            "acceptance_sha256": acceptance_sha,
            "producer": {
                "class": "model_specific_independent_acceptance_checker",
                "schema": acceptance.get("schema"),
            },
            "evidence_tier": {
                "required": required_tier,
                "observed": observed_tier,
                "functional_accelerator_tokens": observed_tier
                in {"functional_accelerator_execution", COSIM_TIER},
                "rtl_bound_accelerated_cosimulation": (
                    rtl_bound_accelerated_cosimulation
                ),
                "full_rtl_generated_tokens": full_rtl_generated_tokens,
                "cosimulation_proof_path": cosimulation.get("path"),
                "cosimulation_proof_sha256": cosimulation.get("sha256"),
                "cosimulation_execution_id": cosimulation.get(
                    "cosimulation_execution_id"
                ),
                "satisfies_required_tier": (
                    (
                        required_tier == "functional_accelerator_execution"
                        and observed_tier
                        in {"functional_accelerator_execution", COSIM_TIER}
                    )
                    or (required_tier == COSIM_TIER and observed_tier == COSIM_TIER)
                    or (
                        required_tier == "full_rtl_generated_tokens"
                        and full_rtl_generated_tokens
                    )
                ),
            },
            "sequences": sequence_summaries,
        },
        "tpot_budget": budget,
        "target_timing": timing,
        "performance_verdict": verdict,
        "process_node_verdict": {
            "technology_view": (contract.get("policy") or {}).get("technology_view"),
            "pvt": (contract.get("policy") or {}).get("pvt"),
            "status": point_status,
            "performance_status": verdict["status"],
        },
        "problems": problems,
        "claim_boundary": {
            "correctness_uses_exact_independent_oracle_tokens": True,
            "accelerated_engine_models_require_digest_bound_bit_cycle_equivalence": True,
            "cosimulation_token_acceptance_is_full_rtl_token_acceptance": False,
            "functional_host_wall_time_is_target_tpot": False,
            "functional_token_acceptance_is_full_rtl_token_acceptance": False,
            "roofline_or_analytical_projection_is_target_tpot": False,
            "rtl_simulator_wall_time_is_target_tpot": False,
            "target_tpot_uses_bound_token_commit_ticks_only": True,
            "unprovenanced_cycles_are_target_tpot": False,
            "cycle_model_target_tpot_is_silicon_measurement": False,
            "per_sequence_tpot_is_aggregate_throughput": False,
            "assumption_dependent_target_timing": (
                (timing.get("provenance") or {}).get("depends_on_assumed_values")
                if isinstance(timing.get("provenance"), dict)
                else None
            ),
            "production_high_fidelity_timing": timing.get(
                "production_high_fidelity", False
            ),
            "production_tpot_gate_closed": verdict["production_gate_closed"],
            "production_tpot_requires_rtl_bound_tokens_and_characterized_timing": True,
            "no_numeric_slo_invented": budget["status"] == "budget_missing",
        },
    }


def _finalize_report(
    points: list[dict[str, Any]], request_problems: list[str]
) -> dict[str, Any]:
    statuses = [point["status"] for point in points]
    if request_problems or "rejected" in statuses:
        status = "rejected"
    elif "fail" in statuses:
        status = "fail"
    elif "not_evaluable" in statuses:
        status = "not_evaluable"
    elif points and all(value == "pass" for value in statuses):
        status = "pass"
    else:
        status = "rejected"
    report = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "points": points,
        "summary": {
            "point_count": len(points),
            "gate1_pass_count": sum(
                point["correctness_gate"]["status"] == "pass" for point in points
            ),
            "target_timing_accepted_count": sum(
                point["target_timing"]["status"] == "accepted" for point in points
            ),
            "budget_missing_count": sum(
                point["tpot_budget"]["status"] == "budget_missing" for point in points
            ),
            "performance_pass_count": sum(
                point["performance_verdict"]["status"] == "pass" for point in points
            ),
            "performance_fail_count": sum(
                point["performance_verdict"]["status"] == "fail" for point in points
            ),
        },
        "request_problems": request_problems,
        "claim_boundary": {
            "abi_version": "3.0",
            "correct_tokens_are_gate_1": True,
            "cosimulation_is_monolithic_full_rtl": False,
            "exact_independent_oracle_equality_required": True,
            "desired_tpot_is_gate_2": True,
            "projection_only_artifacts_eligible": False,
            "functional_host_wall_time_eligible": False,
            "rtl_simulator_wall_time_eligible": False,
            "rtl_bound_accelerated_cosimulation_requires_explicit_proof": True,
            "same_bound_execution_required_for_tpot": True,
            "unprovenanced_target_cycles_eligible": False,
            "thresholds_are_contract_supplied_only": True,
        },
    }
    report_problems = _schema_problems(
        report, REPORT_SCHEMA_PATH, "generated TPOT report"
    )
    if report_problems:
        raise EvidenceError("; ".join(report_problems))
    return report


def validate(request: Mapping[str, Any]) -> dict[str, Any]:
    request_problems = _schema_problems(request, REQUEST_SCHEMA_PATH, "TPOT request")
    if request_problems:
        return _finalize_report([], request_problems)
    raw_points = request["points"]
    ids = [row["point_id"] for row in raw_points]
    if len(set(ids)) != len(ids):
        request_problems.append("point_id values must be unique")
    points: list[dict[str, Any]] = []
    for raw in raw_points:
        try:
            points.append(_point(raw))
        except (OSError, EvidenceError, KeyError, TypeError, ValueError) as exc:
            request_problems.append(
                f"point {raw['point_id']!r} could not be evaluated safely: "
                f"{type(exc).__name__}: {exc}"
            )
    return _finalize_report(points, request_problems)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing report"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.output.exists() and not args.force:
        print(
            f"REFUSED: {args.output} exists; pass --force to overwrite", file=sys.stderr
        )
        return 4
    try:
        request = _load(args.request)
        report = validate(request)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report))
    print(f"wrote {args.output}")
    print(f"correctness-qualified TPOT: {report['status']}")
    for point in report["points"]:
        print(
            f"  {point['point_id']}: gate1={point['correctness_gate']['status']} "
            f"timing={point['target_timing']['status']} "
            f"budget={point['tpot_budget']['status']} "
            f"verdict={point['performance_verdict']['status']}"
        )
    return {"pass": 0, "fail": 1, "rejected": 2, "not_evaluable": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
