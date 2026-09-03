"""Focused mutation tests for the exact-200K DeepSeek oracle gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_deepseek_v4_200k_oracle",
    REPO / "tools" / "check_deepseek_v4_200k_oracle.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)


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
    report.update(
        {
            "run_status": "complete",
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
                    "--only",
                    tool.WORKLOAD_ID,
                ],
            },
            "input_identity": {
                "checkpoint_source": _identity(tool.DEFAULT_CHECKPOINT_SOURCE),
                "workload_index": _identity(tool.DEFAULT_INDEX),
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
    runner_spec = importlib.util.spec_from_file_location(
        "run_deepseek_v4_reference_oracle_for_test",
        REPO / "tools" / "run_deepseek_v4_reference_oracle.py",
    )
    runner = importlib.util.module_from_spec(runner_spec)
    assert runner_spec.loader is not None
    runner_spec.loader.exec_module(runner)
    identity = runner._producer_identity()
    assert tuple(identity["source_map"]) == runner.PRODUCER_SOURCE_PATHS
    assert identity["source_map_sha256"] == runner._canonical_digest(
        identity["source_map"]
    )
    assert identity["tool_source_sha256"] == identity["source_map"][
        "tools/run_deepseek_v4_reference_oracle.py"
    ]


def test_wrong_per_result_workload_binding_is_rejected(
    complete_report, inputs
) -> None:
    report = copy.deepcopy(complete_report)
    report["results"][tool.WORKLOAD_ID]["execution_identity"][
        "workload_index_sha256"
    ] = "f" * 64
    _evidence, problems = _validate(report, inputs)
    assert "200K result is not bound to the frozen workload index" in problems
