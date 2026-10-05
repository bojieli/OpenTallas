"""Focused mutation tests for the exact-200K DeepSeek oracle gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_deepseek_v4_200k_oracle",
    REPO / "tools" / "check_deepseek_v4_200k_oracle.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)


def _load_runner():
    runner_spec = importlib.util.spec_from_file_location(
        "run_deepseek_v4_reference_oracle_for_test",
        REPO / "tools" / "run_deepseek_v4_reference_oracle.py",
    )
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    return runner


def _identity(path: Path) -> dict[str, object]:
    return {
        "path": path.resolve().relative_to(REPO.resolve()).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


@pytest.fixture(scope="module")
def inputs() -> tuple[dict, dict, dict]:
    return (
        json.loads(tool.DEFAULT_WORKLOAD.read_text()),
        json.loads(tool.DEFAULT_INDEX.read_text()),
        json.loads(tool.DEFAULT_CHECKPOINT_SOURCE.read_text()),
    )


@pytest.fixture
def complete_report(inputs) -> dict:
    _workload, _index, checkpoint_source = inputs
    report = json.loads(tool.DEFAULT_ORACLE.read_text())
    generated = [14] * tool.MAX_NEW_TOKENS
    result = report["results"][tool.WORKLOAD_ID]
    result.update(
        {
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": "max_new_tokens",
            "raw_decoded_text": "," * len(generated),
            "visible_decoded_text": "," * len(generated),
            "max_seq_len": 200_320,
            "max_new_tokens": tool.MAX_NEW_TOKENS,
            "prefill_tiled": True,
            "vendor_sample_agreements": len(generated),
            "vendor_sample_disagreements": [],
        }
    )
    source_map = {
        relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
        for relative in tool.REQUIRED_PRODUCER_SOURCES
    }
    source_map_sha256 = tool._canonical_digest(source_map)
    launch_contract = tool._expected_gate_b_launch_contract()
    launch_contract_sha256 = tool._canonical_digest(launch_contract)
    input_identity = {
        "checkpoint_source": _identity(tool.DEFAULT_CHECKPOINT_SOURCE),
        "workload_index": _identity(tool.DEFAULT_INDEX),
        "workload_sources": {
            tool.WORKLOAD_ID: _identity(tool.DEFAULT_WORKLOAD),
        },
    }
    report.update(
        {
            "run_status": "complete",
            "prefill_tiling": {
                "enabled": True,
                "sequence_tile": 4_096,
                "index_tile_rows_fixed": 128,
                "compressor_positions_per_tile": 16_384,
                "expert_rows_per_tile": 8_192,
                "hyper_connection_residual_on_host": True,
            },
            "producer": {
                "tool": "tools/run_deepseek_v4_reference_oracle.py",
                "tool_source_sha256": source_map[
                    "tools/run_deepseek_v4_reference_oracle.py"
                ],
                "source_map": source_map,
                "source_map_sha256": source_map_sha256,
                "source_current_at_completion": True,
                "selected_workload_ids": [tool.WORKLOAD_ID],
                "command_argv": [
                    "tools/run_deepseek_v4_reference_oracle.py",
                    "--gate-b-production",
                ],
            },
            "input_identity": input_identity,
            "input_identity_current_at_completion": True,
            "production_checkpoint_preflight": {
                "completed_before_workload_execution": True,
                "source_sha256": tool.CHECKPOINT_SOURCE_SHA256,
                "expected_file_count": tool.CHECKPOINT_EXPECTED_FILE_COUNT,
                "expected_total_file_bytes": tool.CHECKPOINT_EXPECTED_TOTAL_BYTES,
                "full_byte_hash_verified": True,
                "full_byte_hash_verified_file_count": (
                    tool.CHECKPOINT_EXPECTED_FILE_COUNT
                ),
            },
            "production_launch": {
                "explicitly_requested": True,
                "contract": launch_contract,
                "contract_sha256": launch_contract_sha256,
            },
            "qualified_execution_stack": {
                "profile_id": tool.GATE_B_PROFILE_ID,
                "requirements_sha256": tool._canonical_digest(
                    launch_contract["execution_stack"]
                ),
                "validated_before_workload_execution": True,
                "problems": [],
            },
            "completion_identity": {
                "producer": {
                    "tool": "tools/run_deepseek_v4_reference_oracle.py",
                    "tool_source_sha256": source_map[
                        "tools/run_deepseek_v4_reference_oracle.py"
                    ],
                    "source_map": source_map,
                    "source_map_sha256": source_map_sha256,
                },
                "inputs": copy.deepcopy(input_identity),
                "problems": [],
            },
        }
    )
    vendor_sources = {
        relative: record["sha256"]
        for relative, record in tool._checkpoint_expected_map(
            checkpoint_source
        ).items()
        if relative in tool.REQUIRED_VENDOR_SOURCES
    }
    report["vendor_source_sha256"] = vendor_sources
    result["execution_identity"] = {
        "checkpoint_source_sha256": tool.CHECKPOINT_SOURCE_SHA256,
        "gate_b_launch_contract_sha256": launch_contract_sha256,
        "producer_source_map_sha256": source_map_sha256,
        "vendor_source_sha256": vendor_sources,
        "workload_index_sha256": tool.WORKLOAD_INDEX_SHA256,
        "workload_source": _identity(tool.DEFAULT_WORKLOAD),
    }
    return report


def _validate(report: dict, inputs) -> tuple[dict, list[str]]:
    workload, index, checkpoint_source = inputs
    return tool.validate_oracle_report(
        report,
        workload,
        index,
        checkpoint_source,
        workload_path=tool.DEFAULT_WORKLOAD,
        index_path=tool.DEFAULT_INDEX,
        checkpoint_source_path=tool.DEFAULT_CHECKPOINT_SOURCE,
        snapshot_path=tool.DEFAULT_SNAPSHOT,
        tokenizer=None,
    )


def test_cli_help_states_the_exact_contract() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "check_deepseek_v4_200k_oracle.py"),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    rendered = " ".join(completed.stdout.split())
    assert "exact natural 200,000-token prompt" in rendered
    assert "first official EOS or exactly 256 generated tokens" in rendered


def test_frozen_workload_inputs_rederive_exactly() -> None:
    workload, index, evidence, problems = tool.validate_workload_inputs(
        tool.DEFAULT_WORKLOAD, tool.DEFAULT_INDEX
    )
    assert problems == []
    assert evidence["prompt_token_count"] == 200_000
    assert evidence["prompt_ids_legal"] is True
    assert evidence["workload_digest"] == tool.WORKLOAD_DIGEST
    assert workload["max_new_tokens"] == 256
    assert index["mandatory_context_tokens"] == 200_000


def test_complete_exact_cap_result_is_accepted(complete_report, inputs) -> None:
    evidence, problems = _validate(complete_report, inputs)
    assert problems == []
    assert evidence["terminal_rule"] == "exact_256_without_eos"
    assert evidence["generated_ids_legal"] is True


def test_first_eos_is_included_and_accepted(complete_report, inputs) -> None:
    result = complete_report["results"][tool.WORKLOAD_ID]
    result["generated_token_ids"] = [14, 412, tool.EOS_TOKEN_ID]
    result["generated_token_count"] = 3
    result["stop_reason"] = "eos"
    result["vendor_sample_agreements"] = 3
    evidence, problems = _validate(complete_report, inputs)
    assert problems == []
    assert evidence["terminal_rule"] == "first_official_eos_included"
    assert evidence["first_eos_position"] == 2


def test_retained_eight_token_prefix_is_rejected(inputs) -> None:
    report = json.loads(tool.DEFAULT_ORACLE.read_text())
    evidence, problems = _validate(report, inputs)
    assert evidence["terminal_rule"] == "invalid"
    assert "oracle stopped without EOS before exactly 256 tokens" in problems
    assert "oracle run is not marked complete" in problems
    assert "oracle report has no producer identity" in problems


@pytest.mark.parametrize(
    ("mutation", "expected_problem"),
    [
        (
            lambda result: result["generated_token_ids"].__setitem__(
                7, tool.VOCABULARY_SIZE
            ),
            "oracle generated IDs are absent or outside the vocabulary",
        ),
        (
            lambda result: result["generated_token_ids"].__setitem__(
                7, tool.EOS_TOKEN_ID
            ),
            "oracle continued after the first official EOS",
        ),
        (
            lambda result: result.update(
                {
                    "generated_token_ids": result["generated_token_ids"][:-1],
                    "generated_token_count": tool.MAX_NEW_TOKENS - 1,
                    "vendor_sample_agreements": tool.MAX_NEW_TOKENS - 1,
                }
            ),
            "oracle stopped without EOS before exactly 256 tokens",
        ),
        (
            lambda result: result.update(
                {
                    "vendor_sample_agreements": tool.MAX_NEW_TOKENS - 1,
                    "vendor_sample_disagreements": [
                        {"step": 9, "greedy": 14, "vendor_sample": 15}
                    ],
                }
            ),
            "vendor temperature-zero selection did not agree at every step",
        ),
    ],
)
def test_token_and_terminal_mutations_fail_closed(
    complete_report, inputs, mutation, expected_problem
) -> None:
    result = complete_report["results"][tool.WORKLOAD_ID]
    mutation(result)
    _evidence, problems = _validate(complete_report, inputs)
    assert expected_problem in problems


def test_stale_producer_source_fails_closed(complete_report, inputs) -> None:
    source_map = complete_report["producer"]["source_map"]
    source_map["runtime/reference/deepseek_v4_oracle.py"] = "0" * 64
    complete_report["producer"]["source_map_sha256"] = tool._canonical_digest(
        source_map
    )
    complete_report["results"][tool.WORKLOAD_ID]["execution_identity"][
        "producer_source_map_sha256"
    ] = complete_report["producer"]["source_map_sha256"]
    _evidence, problems = _validate(complete_report, inputs)
    assert "producer source runtime/reference/deepseek_v4_oracle.py is stale" in problems


@pytest.mark.parametrize(
    ("mutation", "expected_problem"),
    [
        (
            lambda report: report["results"][tool.WORKLOAD_ID]["tile_geometry"].update(
                {"indexer_sub_tile": 64}
            ),
            "exact-200K prefill did not use the qualified tile geometry",
        ),
        (
            lambda report: report["adaptations"].pop(),
            "oracle report omits a required execution adaptation",
        ),
        (
            lambda report: report["fp4_gemm_verification"].update(
                {"fp8_gemm_agrees": False}
            ),
            "routed-expert FP8 fallback is not numerically qualified",
        ),
        (
            lambda report: report["environment"]["package_versions"].update(
                {"torch": "different"}
            ),
            "oracle package versions differ from the qualified stack",
        ),
        (
            lambda report: report["results"][tool.WORKLOAD_ID].update(
                {"max_seq_len": tool.PROMPT_TOKENS + tool.MAX_NEW_TOKENS}
            ),
            "oracle KV allocation is not the qualified prompt-plus-256 extent",
        ),
        (
            lambda report: report["production_launch"]["contract"].update(
                {"max_new_tokens": 8}
            ),
            "oracle launch does not match the qualified Gate-B contract",
        ),
        (
            lambda report: report["production_checkpoint_preflight"].update(
                {"full_byte_hash_verified": False}
            ),
            "runner did not fully hash the pinned checkpoint before workload execution",
        ),
    ],
)
def test_execution_qualification_mutations_fail_closed(
    complete_report, inputs, mutation, expected_problem
) -> None:
    mutation(complete_report)
    _evidence, problems = _validate(complete_report, inputs)
    assert expected_problem in problems


def test_omitted_required_producer_source_fails_closed(
    complete_report, inputs
) -> None:
    source_map = complete_report["producer"]["source_map"]
    del source_map["tools/deepseek_v4_prefill_tiling.py"]
    complete_report["producer"]["source_map_sha256"] = tool._canonical_digest(
        source_map
    )
    complete_report["results"][tool.WORKLOAD_ID]["execution_identity"][
        "producer_source_map_sha256"
    ] = complete_report["producer"]["source_map_sha256"]
    _evidence, problems = _validate(complete_report, inputs)
    assert (
        "producer does not bind required source tools/deepseek_v4_prefill_tiling.py"
        in problems
    )


def test_accelerator_paths_have_no_external_oracle_dependency() -> None:
    evidence, problems = tool.validate_dependency_separation()
    assert problems == []
    assert evidence["separated"] is True
    assert evidence["scanned_source_count"] > 0


@pytest.mark.skipif(
    not tool.DEFAULT_SNAPSHOT.is_dir(), reason="pinned DeepSeek snapshot is unavailable"
)
def test_checkpoint_manifest_closure_and_sizes_are_exact() -> None:
    evidence, problems = tool.validate_checkpoint_snapshot(
        tool.DEFAULT_CHECKPOINT_SOURCE,
        tool.DEFAULT_SNAPSHOT,
        full_hash=False,
    )
    assert problems == []
    assert evidence["checkpoint_shard_count"] == 48
    assert evidence["checkpoint_weight_count"] == 72_317
    assert evidence["expected_file_count"] == 74
    assert evidence["size_verified_file_count"] == 74
    assert evidence["content_addressed_shard_link_count"] == 48
    assert evidence["full_byte_hash_verified"] is False


def test_runner_source_identity_covers_the_required_minimum() -> None:
    runner = _load_runner()
    identity = runner._producer_identity()
    assert tuple(identity["source_map"]) == runner.PRODUCER_SOURCE_PATHS
    assert identity["source_map_sha256"] == runner._canonical_digest(
        identity["source_map"]
    )
    assert identity["tool_source_sha256"] == identity["source_map"][
        "tools/run_deepseek_v4_reference_oracle.py"
    ]
    assert set(identity["source_map"]) == set(tool.REQUIRED_PRODUCER_SOURCES)


def test_wrong_per_result_workload_binding_is_rejected(
    complete_report, inputs
) -> None:
    report = copy.deepcopy(complete_report)
    report["results"][tool.WORKLOAD_ID]["execution_identity"][
        "workload_index_sha256"
    ] = "f" * 64
    _evidence, problems = _validate(report, inputs)
    assert "200K result is not bound to the frozen workload index" in problems


def test_runner_gate_b_switch_normalises_the_complete_launch_contract() -> None:
    runner = _load_runner()
    args = SimpleNamespace(
        gate_b_production=True,
        only=None,
        max_new_tokens=None,
        append=False,
        tiling_equivalence=False,
        time_budget_seconds=None,
        head_on_device=False,
        engine_per_workload=True,
        tile_prefill=False,
        tiling_floor=99,
        seq_tile=99,
        index_tile=0,
        expert_rows=99,
        compressor_positions=99,
        host_residual=False,
        index_score_budget_mib=99,
        hc_budget_mib=99,
    )
    assert runner._configure_gate_b_production(args) == []
    assert args.only == [runner.GATE_B_WORKLOAD_ID]
    assert args.max_new_tokens == 256
    assert args.engine_per_workload is False
    assert args.tile_prefill is True
    assert args.seq_tile == 4_096
    assert args.index_tile == 128
    assert args.expert_rows == 8_192
    assert args.compressor_positions == 16_384
    assert args.host_residual is True
    assert runner._gate_b_launch_contract(runner.GATE_B_MAX_SEQ_LEN) == (
        tool._expected_gate_b_launch_contract()
    )


def test_runner_gate_b_inputs_are_pinned_before_engine_construction(inputs) -> None:
    runner = _load_runner()
    _workload, index, _checkpoint = inputs
    selected = [
        (
            runner.GATE_B_WORKLOAD_ID,
            index["workloads"][runner.GATE_B_WORKLOAD_ID],
        )
    ]
    identity = runner._input_identity(
        runner.GATE_B_WORKLOADS / "index.json",
        runner.CHECKPOINT_SOURCE_PATH,
        selected,
        runner.GATE_B_WORKLOADS,
    )
    args = SimpleNamespace(
        gate_b_production=True,
        snapshot=runner.DEFAULT_SNAPSHOT,
        workloads=runner.GATE_B_WORKLOADS,
    )
    assert runner._gate_b_input_problems(args, identity) == []

    stale = copy.deepcopy(identity)
    stale["workload_sources"][runner.GATE_B_WORKLOAD_ID]["sha256"] = "0" * 64
    assert runner._gate_b_input_problems(args, stale) == [
        "exact-200K workload source identity is not Gate-B pinned"
    ]

    wrong_snapshot = copy.copy(args)
    wrong_snapshot.snapshot = REPO
    assert any(
        "--snapshot must resolve" in problem
        for problem in runner._gate_b_input_problems(wrong_snapshot, identity)
    )


def test_runner_production_checkpoint_preflight_requires_full_hash(
    monkeypatch,
) -> None:
    runner = _load_runner()
    gate_b = importlib.import_module("check_deepseek_v4_200k_oracle")
    calls: list[bool] = []

    def verified(_source, _snapshot, *, full_hash):
        calls.append(full_hash)
        return {
            "expected_file_count": 74,
            "expected_total_file_bytes": 166_898_661_074,
            "full_byte_hash_verified": True,
            "full_byte_hash_verified_file_count": 74,
        }, []

    monkeypatch.setattr(gate_b, "validate_checkpoint_snapshot", verified)
    evidence = runner._verify_gate_b_checkpoint_before_execution(
        runner.DEFAULT_SNAPSHOT
    )
    assert calls == [True]
    assert evidence["completed_before_workload_execution"] is True
    assert evidence["full_byte_hash_verified"] is True

    monkeypatch.setattr(
        gate_b,
        "validate_checkpoint_snapshot",
        lambda *_args, **_kwargs: (
            {"full_byte_hash_verified": False},
            ["checkpoint byte differs"],
        ),
    )
    with pytest.raises(runner.OracleError, match="checkpoint byte differs"):
        runner._verify_gate_b_checkpoint_before_execution(runner.DEFAULT_SNAPSHOT)


@pytest.mark.parametrize(
    ("field", "value", "problem"),
    [
        ("max_new_tokens", 8, "requires exactly 256 new tokens"),
        ("append", True, "cannot append"),
        ("tiling_equivalence", True, "cannot run an equivalence-only job"),
        ("head_on_device", True, "requires the qualified host LM head"),
    ],
)
def test_runner_gate_b_switch_rejects_incompatible_options(
    field: str, value: object, problem: str
) -> None:
    runner = _load_runner()
    args = SimpleNamespace(
        gate_b_production=True,
        only=None,
        max_new_tokens=None,
        append=False,
        tiling_equivalence=False,
        time_budget_seconds=None,
        head_on_device=False,
    )
    setattr(args, field, value)
    assert any(
        problem in item for item in runner._configure_gate_b_production(args)
    )


def test_runner_qualified_stack_validation_is_fail_closed(complete_report) -> None:
    runner = _load_runner()
    assert runner._qualified_stack_problems(
        complete_report["environment"],
        complete_report["head_split_verification"],
        complete_report["fp4_gemm_verification"],
        complete_report["expert_numeric_path"],
        complete_report["adaptations"],
    ) == []

    stale = copy.deepcopy(complete_report["environment"])
    stale["fast_hadamard_transform"] = "opentallas_binary32_butterfly"
    problems = runner._qualified_stack_problems(
        stale,
        complete_report["head_split_verification"],
        complete_report["fp4_gemm_verification"],
        complete_report["expert_numeric_path"],
        complete_report["adaptations"],
    )
    assert problems == ["the qualified Hadamard extension is not active"]


def test_completion_time_input_drift_is_rejected(complete_report, inputs) -> None:
    complete_report["completion_identity"]["inputs"]["workload_sources"][
        tool.WORKLOAD_ID
    ]["sha256"] = "0" * 64
    _evidence, problems = _validate(complete_report, inputs)
    assert "completion-time immutable input identity differs from launch" in problems


def test_missing_explicit_production_flag_is_rejected(complete_report, inputs) -> None:
    complete_report["producer"]["command_argv"] = [
        "tools/run_deepseek_v4_reference_oracle.py",
        "--only",
        tool.WORKLOAD_ID,
    ]
    _evidence, problems = _validate(complete_report, inputs)
    assert "runner command did not explicitly select Gate-B production" in problems
