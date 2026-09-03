"""Focused evidence mutations for the correctness-qualified TPOT gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator, ValidationError

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_abi3_correctness_qualified_tpot",
    REPO / "tools/check_abi3_correctness_qualified_tpot.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)

REQUEST_SCHEMA = json.loads(
    (
        REPO / "schemas/abi3/correctness_qualified_tpot_request_v1.schema.json"
    ).read_text()
)
TRACE_SCHEMA = json.loads(
    (REPO / "schemas/abi3/target_timing_trace_v1.schema.json").read_text()
)
REPORT_SCHEMA = json.loads(
    (REPO / "schemas/abi3/correctness_qualified_tpot_report_v1.schema.json").read_text()
)
CONTRACT_SCHEMA = json.loads(
    (REPO / "schemas/abi3/comparison_contract_v1.schema.json").read_text()
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": _hash(path)}


def _lock(path: Path, digest: str) -> dict[str, object]:
    return {
        "digest": digest,
        "path": str(path.resolve()),
        "source_sha256": _hash(path),
        "status": "locked",
    }


def _role_budget(
    *,
    threshold: float,
    statistic: str = "p95",
    measurement_class: str = "abi3_cycle_model_execution",
    allow_assumptions: bool = False,
) -> dict[str, object]:
    # Thresholds here are synthetic test fixtures, never product SLOs.
    return {
        "assumption_dependent_evidence_allowed": allow_assumptions,
        "eligible_measurement_classes": [measurement_class],
        "maximum_seconds": threshold,
        "statistic": statistic,
    }


def _budget(
    batch_size: int,
    *,
    threshold: float,
    statistic: str = "p95",
    measurement_class: str = "abi3_cycle_model_execution",
    allow_assumptions: bool = False,
    role_thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    role_thresholds = role_thresholds or {}
    return {
        "schema": "opentallas.abi3.tpot_acceptance_budget.v1",
        "batch_size": batch_size,
        "metric": "per_sequence_steady_state_decode_step_latency_seconds",
        "steady_state_start_decode_step": 0,
        "roles": {
            role: _role_budget(
                threshold=role_thresholds.get(role, threshold),
                statistic=statistic,
                measurement_class=measurement_class,
                allow_assumptions=allow_assumptions,
            )
            for role in ("hbm", "rom")
        },
    }


@dataclass
class Bundle:
    request: dict[str, Any]
    contract_path: Path
    acceptance_path: Path
    record_paths: list[Path]
    trace_path: Path


def _text_evidence(
    prompt: list[int],
    generated: list[int],
    rendered_sha: str,
    tokenizer_sha: str,
    index: int,
) -> dict[str, object]:
    raw = f"synthetic answer {index}"
    return {
        "tokenizer": {
            "path": "synthetic-tokenizer.json",
            "sha256": tokenizer_sha,
            "library": "synthetic",
            "library_version": "1.0",
        },
        "input": {
            "token_count": len(prompt),
            "token_ids_sha256": tool.digest_of(prompt),
            "rendered_text": "synthetic input context",
            "rendered_text_sha256": rendered_sha,
            "decode_matches_frozen_text": True,
            "encode_round_trip_matches_ids": True,
        },
        "output": {
            "token_count": len(generated),
            "token_ids_sha256": tool.digest_of(generated),
            "raw_decoded_text": raw,
            "raw_decoded_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "visible_decoded_text": raw,
            "visible_decoded_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "raw_matches_frozen_oracle": True,
            "visible_matches_frozen_oracle": True,
            "encode_round_trip_matches_ids": True,
        },
    }


def _make_bundle(
    root: Path,
    *,
    batch_size: int = 1,
    threshold: float | None = 3.1,
    statistic: str = "p95",
    measurement_class: str = "abi3_cycle_model_execution",
    depends_on_assumptions: bool = False,
    allow_assumptions: bool = False,
    required_tier: str = "functional_accelerator_execution",
    target_role: str = "hbm",
    generated_tokens: list[int] | None = None,
    role_thresholds: dict[str, float] | None = None,
    record_mutator: Callable[[dict[str, Any]], None] | None = None,
) -> Bundle:
    root.mkdir(parents=True)
    prompt = [1, 2]
    generated = list(generated_tokens) if generated_tokens is not None else [3, 4, 5]
    rendered = "synthetic input context"
    rendered_sha = hashlib.sha256(rendered.encode()).hexdigest()
    tokenizer_sha = "1" * 64
    graph_id = "2" * 64
    workload_digest = "3" * 64
    capability_digest = "4" * 64
    deployment_digest = "5" * 64
    batch_execution_id = "6" * 64 if batch_size > 1 else None

    ir = root / "kernel-ir.json"
    workload_file = root / "workload.json"
    workload_index = root / "workload-index.json"
    oracle = root / "oracle.json"
    oracle_tool = root / "oracle-tool.py"
    capability = root / "capability.json"
    deployment = root / "deployment"
    deployment_manifest = deployment / "deployment.json"
    cost_table = root / "cost-table.json"
    source = root / "simulator-source.py"
    timing_tool = root / "timing-tool.py"
    _write(ir, {"graph_id": graph_id, "model_id": "synthetic-model"})
    _write(
        workload_file,
        {
            "workload_id": "SYNTHETIC-WORKLOAD",
            "digest": workload_digest,
            "kind": "synthetic-natural",
            "max_new_tokens": 3,
            "prompt_token_count": len(prompt),
            "token_ids": prompt,
            "rendered_text": rendered,
            "rendered_text_sha256": rendered_sha,
        },
    )
    _write(
        workload_index,
        {
            "schema": "synthetic.workload_index.v1",
            "model_id": "synthetic-model",
            "tokenizer_sha256": tokenizer_sha,
            "workloads": {
                "SYNTHETIC-WORKLOAD": {
                    "digest": workload_digest,
                    "kind": "synthetic-natural",
                    "max_new_tokens": len(generated),
                    "path": workload_file.name,
                    "prompt_token_count": len(prompt),
                }
            },
        },
    )
    _write(oracle, {"generated_token_ids": generated})
    oracle_tool.write_text("# synthetic oracle producer\n")
    _write(capability, {"digest": capability_digest})
    _write(deployment_manifest, {"digest": deployment_digest})
    _write(
        cost_table,
        {
            "schema": "opentallas.abi3.cost_table.v1",
            "cost_table_id": "synthetic-cost",
            "technology_view": "asap7",
        },
    )
    source.write_text("# synthetic simulator source\n")
    timing_tool.write_text("# synthetic timing producer\n")

    target_hbm = {
        "backend": "hbm-sram-abi3",
        "capability": _lock(capability, capability_digest),
        "cost_policy": {
            "cost_table_id": "synthetic-cost",
            "lock": _lock(cost_table, "7" * 64),
            "policy_id": "synthetic-hbm-cost-policy",
        },
        "deployment": {
            "digest": deployment_digest,
            "path": str(deployment.resolve()),
            "source_sha256": _hash(deployment_manifest),
            "status": "locked",
        },
        "node_count": 1,
        "role": "hbm",
        "storage_class": "HBM",
        "target_id": "synthetic-hbm-target",
        "topology_class": 0,
    }
    target_rom = copy.deepcopy(target_hbm)
    target_rom.update(
        {
            "backend": "rom.single_chip",
            "role": "rom",
            "storage_class": "ROM",
            "target_id": "synthetic-rom-target",
        }
    )
    target_rom["cost_policy"]["policy_id"] = "synthetic-rom-cost-policy"
    contract: dict[str, Any] = {
        "schema": "opentallas.abi3.comparison_contract.v1",
        "version": "1.0.0",
        "comparison_id": "synthetic_rom_vs_hbm",
        "execution": {
            "batch": batch_size,
            "concurrency": batch_size,
            "context_tokens": len(prompt),
            "evidence_scope": "full_workload",
            "phases": ["prefill", "decode"],
            "generation": {
                "eos_token_ids": [9],
                "include_eos_in_output": True,
                "max_new_tokens": len(generated),
                "selection_mode": "greedy_argmax_lowest_id",
                "stop_condition": "first_official_eos_or_maximum_new_tokens",
                "tie_rule": "lowest_token_id",
                "vocabulary_size": 10,
            },
        },
        "external_oracle": {
            "evidence_class": "external_reference_comparator",
            "path": str(oracle.resolve()),
            "producer": {
                "source_sha256": _hash(oracle_tool),
                "tool": str(oracle_tool.resolve()),
            },
            "schema": "opentallas.abi3.reference_oracle.v1",
            "source_sha256": _hash(oracle),
            "status": "locked",
        },
        "model": {
            "graph_id": graph_id,
            "kernel_ir_path": str(ir.resolve()),
            "kernel_ir_source_sha256": _hash(ir),
            "model_id": "synthetic-model",
            "numeric_profile": "synthetic-numeric-profile",
        },
        "policy": {
            "clock": {
                "comparison_frequency_hz": 10,
                "policy_id": "synthetic-common-clock",
                "same_frequency_required": True,
            },
            "evidence_class": "synthetic-characterized-evidence",
            "external_fabric_policy": "single-chip",
            "external_memory_policy": "source-locked-memory",
            "latency_boundary": "request-to-token-commit",
            "pvt": {
                "corner_id": "synthetic-tt",
                "process": "TT",
                "temperature_c": 25,
                "voltage_v": 0.7,
            },
            "state_boundary": "fresh-session-fail-stop",
            "technology_claim": "synthetic test fixture only",
            "technology_view": "asap7",
        },
        "targets": {"hbm": target_hbm, "rom": target_rom},
        "workload": {
            "digest": workload_digest,
            "index_path": str(workload_index.resolve()),
            "index_schema": "synthetic.workload_index.v1",
            "index_source_sha256": _hash(workload_index),
            "kind": "synthetic-natural",
            "max_new_tokens": len(generated),
            "path": str(workload_file.resolve()),
            "prompt_token_count": len(prompt),
            "rendered_text_sha256": rendered_sha,
            "source_sha256": _hash(workload_file),
            "template": {
                "mode": "none_plain_text",
                "path": None,
                "source_sha256": None,
                "template_id": "none_plain_text",
            },
            "tokenizer_sha256": tokenizer_sha,
            "workload_id": "SYNTHETIC-WORKLOAD",
        },
    }
    if threshold is not None:
        contract["execution"]["tpot_acceptance"] = _budget(
            batch_size,
            threshold=threshold,
            statistic=statistic,
            measurement_class=measurement_class,
            allow_assumptions=allow_assumptions,
            role_thresholds=role_thresholds,
        )
    contract_path = root / "comparison-contract.json"
    _write(contract_path, contract)

    implementation = {"backend": "synthetic", "version": "1"}
    source_map = {str(source.resolve()): _hash(source)}
    association_unsigned = {
        "schema": "opentallas.abi3.executed_association.v1",
        "association_policy": "implementation_and_executed_shape_pinned",
        "implementation_identity": implementation,
        "entries": [
            {
                "numeric_contract": "synthetic",
                "activation_shape": [1, 1],
                "weight_shape": [1, 1],
                "output_shape": [1, 1],
                "call_count": 1,
            }
        ],
        "distinct_association_count": 1,
        "blocked_call_count": 1,
    }
    association = {
        **association_unsigned,
        "manifest_sha256": tool.digest_of(association_unsigned),
    }
    record_paths: list[Path] = []
    text_rows: list[dict[str, object]] = []
    selected_target = target_hbm if target_role == "hbm" else target_rom
    first_eos = next(
        (offset for offset, token in enumerate(generated) if token == 9), None
    )
    terminal_kind = "eos" if first_eos is not None else "cap"
    stop_reason = "eos" if first_eos is not None else "max_new_tokens"
    for index in range(batch_size):
        steps = [
            {
                "step": offset,
                "transaction_id": offset + 1,
                "phase": "prefill" if offset == 0 else "decode",
                "status": "SUCCESS",
                "trap": "NONE",
                "produced_tokens": [token],
                "final_token_id": token,
                "eos_reason": (
                    1
                    if offset == first_eos
                    else (
                        2 if first_eos is None and offset == len(generated) - 1 else 0
                    )
                ),
                "instructions_retired": 10,
                "retired_work": 10,
                "wall_seconds": 1000.0 + offset,
            }
            for offset, token in enumerate(generated)
        ]
        record: dict[str, Any] = {
            "schema": "opentallas.abi3.accelerator_tokens.v1",
            "status": "pass",
            "evidence_class": "functional_artifact_only",
            "tool": "tools/run_accelerator_tokens.py",
            "backend": "hbm_sram" if target_role == "hbm" else "rom_qwen3",
            "target": {
                "target_id": selected_target["target_id"],
                "backend": selected_target["backend"],
                "node_count": selected_target["node_count"],
                "topology_class": selected_target["topology_class"],
                "capability_digest": capability_digest,
                "deployment_digest": deployment_digest,
                "technology_view": "asap7",
            },
            "workload": {
                "workload_id": "SYNTHETIC-WORKLOAD",
                "workload_digest": workload_digest,
                "prompt_token_ids": prompt,
                "prompt_token_count": len(prompt),
                "max_new_tokens": len(generated),
                "rendered_text_sha256": rendered_sha,
                "prompt_token_ids_sha256": tool.digest_of(prompt),
                "tokenizer_sha256": tokenizer_sha,
            },
            "model": {
                "model_id": "synthetic-model",
                "graph_id": graph_id,
                "numeric_profile": "synthetic-numeric-profile",
                "checkpoint_root": str(root),
            },
            "verification": {
                "admitted": True,
                "errors": [],
                "checks": {"capacity": True, "authentication": True},
                "state_resources": 0,
            },
            "engine_coverage": {"missing_count": 0, "missing": []},
            "implementation_identity": implementation,
            "executed_association": association,
            "source_sha256": source_map,
            "generated_token_ids": list(generated),
            "generated_token_count": len(generated),
            "stop_reason": stop_reason,
            "failure": None,
            "token_legitimacy_problems": [],
            "oracle": {
                "artifact": str(oracle.resolve()),
                "artifact_sha256": _hash(oracle),
                "evidence_class": "external_reference_comparator",
                "generated_token_ids": list(generated),
                "agreement": True,
                "first_divergence_index": None,
                "compared_tokens": len(generated),
                "oracle_token_count": len(generated),
            },
            "terminal_acceptance": {
                "contract": "exact_eos_or_cap",
                "accepted": True,
                "terminal_kind": terminal_kind,
                "failed_checks": [],
                "checks": {"exact_cap": True, "no_post_eos": True},
            },
            "per_step": steps,
            "wall_seconds": 9999.0,
        }
        if batch_size > 1:
            record["batch_execution"] = {
                "schema": "opentallas.abi3.accelerator_batch_execution_member.v1",
                "batch_execution_id": batch_execution_id,
                "batch_size": batch_size,
                "sequence_index": index,
                "shared_execution": True,
            }
        if record_mutator is not None:
            record_mutator(record)
        record_path = root / f"execution-{index}.json"
        _write(record_path, record)
        record_paths.append(record_path)
        text_rows.append(
            {
                "sequence_index": index,
                "text_evidence": _text_evidence(
                    prompt, generated, rendered_sha, tokenizer_sha, index
                ),
            }
        )

    acceptance: dict[str, Any] = {
        "schema": "opentallas.abi3.qwen3_w10_acceptance.v1",
        "status": "pass",
        "workload_id": "SYNTHETIC-WORKLOAD",
        "problems": [],
        "pair_checks": {"token_sequences_identical": True},
        "claim_boundary": {"acceptance_established": True},
        "records": [
            {
                "path": str(path.resolve()),
                "sha256": _hash(path),
                "passes": True,
                "problems": [],
            }
            for path in record_paths
        ],
    }
    if batch_size == 1:
        acceptance["text_evidence"] = text_rows[0]["text_evidence"]
    else:
        acceptance["sequence_evidence"] = text_rows
    acceptance_path = root / "correctness-acceptance.json"
    _write(acceptance_path, acceptance)

    trace: dict[str, Any] = {
        "schema": "opentallas.abi3.target_timing_trace.v1",
        "evidence_class": "executed_target_timing_trace",
        "measurement_class": measurement_class,
        "projection_only": False,
        "counterfactual_or_extrapolated": False,
        "full_workload_execution": True,
        "token_commits_from_execution": True,
        "producer": {
            "tool": str(timing_tool.resolve()),
            "source_sha256": _hash(timing_tool),
        },
        "provenance": {
            "class": "assumed" if depends_on_assumptions else "characterized",
            "depends_on_assumed_values": depends_on_assumptions,
        },
        "comparison_id": "synthetic_rom_vs_hbm",
        "comparison_contract_sha256": _hash(contract_path),
        "correctness_acceptance_sha256": _hash(acceptance_path),
        "model_id": "synthetic-model",
        "graph_id": graph_id,
        "workload_id": "SYNTHETIC-WORKLOAD",
        "workload_digest": workload_digest,
        "latency_boundary": "request-to-token-commit",
        "technology_view": "asap7",
        "pvt": {
            "corner_id": "synthetic-tt",
            "process": "TT",
            "temperature_c": 25,
            "voltage_v": 0.7,
        },
        "batch_size": batch_size,
        "concurrency": batch_size,
        "batch_execution_id": batch_execution_id,
        "target": {
            "target_id": selected_target["target_id"],
            "backend": selected_target["backend"],
            "node_count": selected_target["node_count"],
            "topology_class": selected_target["topology_class"],
            "capability_digest": capability_digest,
            "deployment_digest": deployment_digest,
            "technology_view": "asap7",
            "source_manifest_sha256": tool.digest_of(source_map),
            "implementation_identity_sha256": tool.digest_of(implementation),
        },
        "cost_table": {
            "cost_table_id": "synthetic-cost",
            "path": str(cost_table.resolve()),
            "sha256": _hash(cost_table),
        },
        "timebase": {
            "unit": "nanoseconds"
            if measurement_class == "silicon_measurement"
            else "cycles",
            "ticks_per_second": 1_000_000_000
            if measurement_class == "silicon_measurement"
            else 10,
            "clock_frequency_hz": None
            if measurement_class == "silicon_measurement"
            else 10,
        },
        "steady_state_start_decode_step": 0,
        "execution_records": [
            {
                "sequence_index": index,
                "path": str(path.resolve()),
                "sha256": _hash(path),
            }
            for index, path in enumerate(record_paths)
        ],
        "sequences": [
            {
                "sequence_index": index,
                "request_start_tick": 0,
                "token_commit_ticks": [100, 120, 150],
            }
            for index in range(batch_size)
        ],
    }
    trace_path = root / "target-timing.json"
    _write(trace_path, trace)
    request = {
        "schema": "opentallas.abi3.correctness_qualified_tpot_request.v1",
        "points": [
            {
                "point_id": "synthetic-hbm-point",
                "comparison_contract": _ref(contract_path),
                "correctness_acceptance": _ref(acceptance_path),
                "execution_records": [_ref(path) for path in record_paths],
                "batch_execution_id": batch_execution_id,
                "required_correctness_tier": required_tier,
                "target_role": target_role,
                "target_timing_trace": _ref(trace_path),
            }
        ],
    }
    return Bundle(request, contract_path, acceptance_path, record_paths, trace_path)


def _assert_report_schema(report: dict[str, Any]) -> None:
    Draft202012Validator(REPORT_SCHEMA).validate(report)


def test_new_schemas_are_valid_and_current_contracts_remain_valid() -> None:
    for schema in (REQUEST_SCHEMA, TRACE_SCHEMA, REPORT_SCHEMA, CONTRACT_SCHEMA):
        Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(CONTRACT_SCHEMA)
    for name in (
        "qwen3_rom_single_chip_vs_hbm_single_chip_v1.json",
        "deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json",
    ):
        validator.validate(
            json.loads((REPO / "configs/abi3/comparison_contracts" / name).read_text())
        )


def test_contract_schema_accepts_role_specific_budget_and_rejects_partial_role() -> (
    None
):
    contract = json.loads(
        (
            REPO
            / "configs/abi3/comparison_contracts/qwen3_rom_single_chip_vs_hbm_single_chip_v1.json"
        ).read_text()
    )
    contract["execution"]["tpot_acceptance"] = _budget(1, threshold=1.0)
    Draft202012Validator(CONTRACT_SCHEMA).validate(contract)
    del contract["execution"]["tpot_acceptance"]["roles"]["rom"]
    with pytest.raises(ValidationError):
        Draft202012Validator(CONTRACT_SCHEMA).validate(contract)


def test_budget_missing_is_explicit_after_gate1_and_timing_pass(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path / "missing", threshold=None)
    Draft202012Validator(REQUEST_SCHEMA).validate(bundle.request)
    Draft202012Validator(TRACE_SCHEMA).validate(
        json.loads(bundle.trace_path.read_text())
    )
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    assert report["status"] == "not_evaluable"
    assert point["correctness_gate"]["status"] == "pass"
    assert point["target_timing"]["status"] == "accepted"
    assert point["tpot_budget"]["status"] == "budget_missing"
    assert point["performance_verdict"]["status"] == "budget_missing"
    assert point["performance_verdict"]["observed_seconds"] is None
    assert point["claim_boundary"]["no_numeric_slo_invented"] is True


def test_derives_raw_ttft_tpot_distribution_and_distinct_aggregate_rate(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(tmp_path / "batch", batch_size=2, threshold=3.1)
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    metrics = point["target_timing"]["metrics"]
    assert report["status"] == "pass"
    assert point["batch"] == {
        "batch_size": 2,
        "concurrency": 2,
        "batch_execution_id": "6" * 64,
        "prompt_tokens_per_sequence": [2, 2],
        "generated_tokens_per_sequence": [3, 3],
        "total_prompt_tokens": 4,
        "total_generated_tokens": 6,
    }
    assert metrics["sequence_metrics"][0]["request_start_tick"] == 0
    assert metrics["sequence_metrics"][0]["token_commit_ticks"] == [100, 120, 150]
    assert metrics["sequence_metrics"][0]["ttft_seconds"] == 10.0
    assert [
        row["latency_seconds"]
        for row in metrics["sequence_metrics"][0]["raw_decode_step_latencies"]
    ] == [2.0, 3.0]
    distribution = metrics["batch_metrics"][
        "per_sequence_steady_state_decode_step_latency_seconds"
    ]
    assert distribution == {
        "sample_count": 4,
        "statistic_policy": "nearest_rank_over_raw_per_sequence_decode_intervals",
        "mean": 2.5,
        "p50": 2.0,
        "p95": 3.0,
        "p99": 3.0,
        "max": 3.0,
    }
    assert metrics["batch_metrics"][
        "aggregate_steady_state_tokens_per_second"
    ] == pytest.approx(4 / 5)
    assert point["performance_verdict"] == {
        "status": "pass",
        "metric": "per_sequence_steady_state_decode_step_latency_seconds",
        "statistic": "p95",
        "observed_seconds": 3.0,
        "maximum_seconds": 3.1,
        "meets_budget": True,
        "production_gate_closed": False,
    }
    host = point["correctness_gate"]["sequences"][0]["host_functional_timing"]
    assert host["ttft_seconds"] == 1000.0
    assert host["eligible_for_target_tpot"] is False
    assert host["used_for_target_tpot"] is False


def test_selected_statistic_can_fail_without_changing_raw_metrics(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(tmp_path / "failure", threshold=2.5, statistic="max")
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    verdict = report["points"][0]["performance_verdict"]
    assert report["status"] == "fail"
    assert verdict["statistic"] == "max"
    assert verdict["observed_seconds"] == 3.0
    assert verdict["maximum_seconds"] == 2.5
    assert verdict["meets_budget"] is False


def test_gate1_failure_prevents_any_target_tpot_derivation(tmp_path: Path) -> None:
    def corrupt(record: dict[str, Any]) -> None:
        record["generated_token_ids"][1] = 8

    bundle = _make_bundle(tmp_path / "illegal", record_mutator=corrupt)
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    assert report["status"] == "rejected"
    assert point["correctness_gate"]["status"] == "rejected"
    assert point["correctness_gate"]["sequences"][0]["first_divergence_index"] == 1
    assert point["target_timing"] == {
        "status": "not_evaluated_gate1_failed",
        "metrics": None,
    }
    assert point["performance_verdict"]["status"] == "gate1_failed"
    assert point["performance_verdict"]["observed_seconds"] is None


def test_final_eos_is_accepted_and_post_eos_execution_is_rejected(
    tmp_path: Path,
) -> None:
    final_eos = _make_bundle(tmp_path / "final-eos", generated_tokens=[3, 4, 9])
    accepted = tool.validate(final_eos.request)
    _assert_report_schema(accepted)
    sequence = accepted["points"][0]["correctness_gate"]["sequences"][0]
    assert accepted["status"] == "pass"
    assert sequence["generated_token_ids"] == [3, 4, 9]
    assert sequence["terminal_kind"] == "eos"
    assert sequence["first_eos_index"] == 2
    assert sequence["no_post_eos_step"] is True

    post_eos = _make_bundle(tmp_path / "post-eos", generated_tokens=[3, 9, 5])
    rejected = tool.validate(post_eos.request)
    _assert_report_schema(rejected)
    point = rejected["points"][0]
    assert rejected["status"] == "rejected"
    assert point["target_timing"]["status"] == "not_evaluated_gate1_failed"
    assert any(
        "first-official-EOS-included or exact-cap" in problem
        for problem in point["problems"]
    )


def test_stale_source_and_failed_admission_each_block_gate1(tmp_path: Path) -> None:
    stale = _make_bundle(tmp_path / "stale")
    (tmp_path / "stale/simulator-source.py").write_text(
        "# source changed after execution\n", encoding="utf-8"
    )
    stale_report = tool.validate(stale.request)
    _assert_report_schema(stale_report)
    assert stale_report["status"] == "rejected"
    assert any(
        "record source_sha256" in problem and "stale" in problem
        for problem in stale_report["points"][0]["problems"]
    )

    def reject_admission(record: dict[str, Any]) -> None:
        record["verification"]["admitted"] = False

    unadmitted = _make_bundle(tmp_path / "unadmitted", record_mutator=reject_admission)
    unadmitted_report = tool.validate(unadmitted.request)
    _assert_report_schema(unadmitted_report)
    assert unadmitted_report["status"] == "rejected"
    assert any(
        "capacity/admission evidence is not clean" in problem
        for problem in unadmitted_report["points"][0]["problems"]
    )


def test_record_must_use_exact_contract_oracle_even_if_alternate_file_is_current(
    tmp_path: Path,
) -> None:
    root = tmp_path / "wrong-oracle"

    def switch_oracle(record: dict[str, Any]) -> None:
        alternate = root / "capability.json"
        record["oracle"]["artifact"] = str(alternate.resolve())
        record["oracle"]["artifact_sha256"] = _hash(alternate)

    bundle = _make_bundle(root, record_mutator=switch_oracle)
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    assert report["status"] == "rejected"
    assert any(
        "not the exact comparison-contract oracle" in problem
        for problem in report["points"][0]["problems"]
    )


def test_each_role_uses_only_its_own_frozen_tpot_budget(tmp_path: Path) -> None:
    thresholds = {"hbm": 2.5, "rom": 9.0}
    hbm = _make_bundle(tmp_path / "hbm-budget", role_thresholds=thresholds)
    rom = _make_bundle(
        tmp_path / "rom-budget",
        target_role="rom",
        role_thresholds=thresholds,
    )
    hbm_report = tool.validate(hbm.request)
    rom_report = tool.validate(rom.request)
    _assert_report_schema(hbm_report)
    _assert_report_schema(rom_report)
    assert hbm_report["status"] == "fail"
    assert hbm_report["points"][0]["tpot_budget"]["target_role"] == "hbm"
    assert hbm_report["points"][0]["performance_verdict"]["maximum_seconds"] == 2.5
    assert rom_report["status"] == "pass"
    assert rom_report["points"][0]["tpot_budget"]["target_role"] == "rom"
    assert rom_report["points"][0]["performance_verdict"]["maximum_seconds"] == 9.0


def test_functional_acceptance_does_not_satisfy_required_full_rtl_gate(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(
        tmp_path / "rtl-tier", required_tier="full_rtl_generated_tokens"
    )
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    tier = report["points"][0]["correctness_gate"]["evidence_tier"]
    assert report["status"] == "rejected"
    assert tier == {
        "required": "full_rtl_generated_tokens",
        "observed": "functional_accelerator_execution",
        "functional_accelerator_tokens": True,
        "full_rtl_generated_tokens": False,
        "satisfies_required_tier": False,
    }


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ("opentallas.roofline.study.v1", "projection-only artifact"),
        ("opentallas.abi3.accelerator_tokens.v1", "functional host execution record"),
    ],
)
def test_projection_and_functional_wall_time_are_rejected_as_target_timing(
    tmp_path: Path, schema: str, message: str
) -> None:
    bundle = _make_bundle(tmp_path / schema.replace(".", "-"))
    invalid = tmp_path / f"invalid-{hashlib.sha256(schema.encode()).hexdigest()}.json"
    _write(invalid, {"schema": schema, "step_time_s": 1e-9})
    bundle.request["points"][0]["target_timing_trace"] = _ref(invalid)
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    assert report["status"] == "rejected"
    assert point["target_timing"]["status"] == "rejected"
    assert point["target_timing"]["metrics"] is None
    assert any(message in problem for problem in point["problems"])


def test_assumption_dependent_trace_is_policy_controlled_and_never_high_fidelity(
    tmp_path: Path,
) -> None:
    refused = _make_bundle(
        tmp_path / "refused",
        depends_on_assumptions=True,
        allow_assumptions=False,
    )
    refused_report = tool.validate(refused.request)
    _assert_report_schema(refused_report)
    assert refused_report["status"] == "rejected"
    assert any(
        "assumption-dependent timing is forbidden" in problem
        for problem in refused_report["points"][0]["problems"]
    )

    allowed = _make_bundle(
        tmp_path / "allowed",
        depends_on_assumptions=True,
        allow_assumptions=True,
    )
    allowed_report = tool.validate(allowed.request)
    _assert_report_schema(allowed_report)
    point = allowed_report["points"][0]
    assert allowed_report["status"] == "pass"
    assert point["target_timing"]["provenance"]["depends_on_assumed_values"] is True
    assert point["target_timing"]["production_high_fidelity"] is False
    assert point["claim_boundary"]["assumption_dependent_target_timing"] is True
    assert point["performance_verdict"]["production_gate_closed"] is False


def test_post_layout_non_assumed_trace_is_explicitly_high_fidelity(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(
        tmp_path / "post-layout",
        measurement_class="post_layout_timing_simulation",
    )
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    timing = report["points"][0]["target_timing"]
    assert report["status"] == "pass"
    assert timing["claim_class"] == "post_layout_simulated_target_tpot"
    assert timing["production_high_fidelity"] is True
    assert report["points"][0]["performance_verdict"]["production_gate_closed"] is False


def test_characterized_rtl_cycles_are_high_fidelity_timing_but_need_rtl_tokens(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(
        tmp_path / "rtl-characterized",
        measurement_class="rtl_cycle_simulation",
    )
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    assert report["status"] == "pass"
    assert point["target_timing"]["production_high_fidelity"] is True
    assert (
        point["correctness_gate"]["evidence_tier"]["full_rtl_generated_tokens"] is False
    )
    assert point["performance_verdict"]["production_gate_closed"] is False


def test_process_view_and_pvt_have_an_explicit_point_verdict(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path / "process-verdict")
    report = tool.validate(bundle.request)
    _assert_report_schema(report)
    point = report["points"][0]
    assert point["comparison"]["process_view"] == "asap7"
    assert point["comparison"]["pvt"] == {
        "corner_id": "synthetic-tt",
        "process": "TT",
        "temperature_c": 25,
        "voltage_v": 0.7,
    }
    assert point["process_node_verdict"] == {
        "technology_view": "asap7",
        "pvt": point["comparison"]["pvt"],
        "status": "pass",
        "performance_status": "pass",
    }

    mismatched = _make_bundle(tmp_path / "pvt-mismatch")
    trace = json.loads(mismatched.trace_path.read_text())
    trace["pvt"]["voltage_v"] = 0.8
    _write(mismatched.trace_path, trace)
    mismatched.request["points"][0]["target_timing_trace"] = _ref(mismatched.trace_path)
    mismatch_report = tool.validate(mismatched.request)
    _assert_report_schema(mismatch_report)
    assert mismatch_report["status"] == "rejected"
    assert any(
        "target timing pvt differs" in problem
        for problem in mismatch_report["points"][0]["problems"]
    )


def test_runtime_schema_validation_returns_valid_rejected_reports(
    tmp_path: Path,
) -> None:
    invalid_request = _make_bundle(tmp_path / "invalid-request").request
    invalid_request["unexpected"] = True
    request_report = tool.validate(invalid_request)
    _assert_report_schema(request_report)
    assert request_report["status"] == "rejected"
    assert request_report["points"] == []
    assert any(
        "additional properties" in row.lower()
        for row in request_report["request_problems"]
    )

    bad_contract = _make_bundle(tmp_path / "bad-contract")
    contract = json.loads(bad_contract.contract_path.read_text())
    contract["unexpected"] = True
    _write(bad_contract.contract_path, contract)
    bad_contract.request["points"][0]["comparison_contract"] = _ref(
        bad_contract.contract_path
    )
    contract_report = tool.validate(bad_contract.request)
    _assert_report_schema(contract_report)
    assert contract_report["status"] == "rejected"
    assert any(
        "comparison contract schema violation" in problem
        for problem in contract_report["points"][0]["problems"]
    )

    bad_trace = _make_bundle(tmp_path / "bad-trace")
    trace = json.loads(bad_trace.trace_path.read_text())
    del trace["sequences"]
    _write(bad_trace.trace_path, trace)
    bad_trace.request["points"][0]["target_timing_trace"] = _ref(bad_trace.trace_path)
    trace_report = tool.validate(bad_trace.request)
    _assert_report_schema(trace_report)
    assert trace_report["status"] == "rejected"
    assert trace_report["points"][0]["target_timing"]["status"] == "rejected"
    assert any(
        "target timing trace schema violation" in problem
        for problem in trace_report["points"][0]["problems"]
    )

    malformed_record = _make_bundle(tmp_path / "malformed-record")
    record_path = malformed_record.record_paths[0]
    record_path.write_text('{"schema":"first","schema":"second"}', encoding="utf-8")
    acceptance = json.loads(malformed_record.acceptance_path.read_text())
    acceptance["records"][0]["sha256"] = _hash(record_path)
    _write(malformed_record.acceptance_path, acceptance)
    point = malformed_record.request["points"][0]
    point["execution_records"] = [_ref(record_path)]
    point["correctness_acceptance"] = _ref(malformed_record.acceptance_path)
    malformed_report = tool.validate(malformed_record.request)
    _assert_report_schema(malformed_report)
    assert malformed_report["status"] == "rejected"
    assert any(
        "duplicate JSON key" in problem
        for problem in malformed_report["points"][0]["problems"]
    )


@pytest.mark.parametrize("payload", ['{"key": 1, "key": 2}', '{"value": NaN}'])
def test_governed_json_rejects_duplicate_keys_and_nonfinite_numbers(
    payload: str,
) -> None:
    with pytest.raises(tool.EvidenceError):
        tool._strict_json_loads(payload, source="test payload")


def test_report_supports_multiple_independently_bound_batch_points(
    tmp_path: Path,
) -> None:
    first = _make_bundle(tmp_path / "first", threshold=None)
    second = _make_bundle(tmp_path / "second", threshold=3.1)
    second_point = second.request["points"][0]
    second_point["point_id"] = "second-independent-point"
    request = {
        "schema": "opentallas.abi3.correctness_qualified_tpot_request.v1",
        "points": [first.request["points"][0], second_point],
    }
    report = tool.validate(request)
    _assert_report_schema(report)
    assert report["status"] == "not_evaluable"
    assert report["summary"] == {
        "point_count": 2,
        "gate1_pass_count": 2,
        "target_timing_accepted_count": 2,
        "budget_missing_count": 1,
        "performance_pass_count": 1,
        "performance_fail_count": 0,
    }


def test_cli_writes_canonical_report_and_uses_not_evaluable_exit(
    tmp_path: Path,
) -> None:
    bundle = _make_bundle(tmp_path / "cli-bundle", threshold=None)
    request_path = tmp_path / "request.json"
    output = tmp_path / "report.json"
    _write(request_path, bundle.request)
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/check_abi3_correctness_qualified_tpot.py"),
            "--request",
            str(request_path),
            "--output",
            str(output),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 3, completed.stderr
    raw = output.read_bytes()
    report = json.loads(raw)
    _assert_report_schema(report)
    assert raw == tool.canonical_json(report)
    assert "budget=budget_missing" in completed.stdout
