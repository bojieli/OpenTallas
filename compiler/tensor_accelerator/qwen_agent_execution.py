"""Governed live-agent evidence above controlled Qwen accelerator turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import re
from typing import Any

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
)
from .qwen_agent_protocol import parse_assistant_output
from .qwen_chat import EOS_TOKEN_IDS
from .qwen_workload import QwenWorkloadError, validate_shared_workload


SCHEMA = "opentallas.tensor_accelerator.qwen_agent_task_execution.v1"
VERSION = "tensor-accelerator-qwen-live-agent-runner-0.1.0"
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class QwenAgentExecutionError(ArtifactError):
    """Raised when live agent turns, actions, or task verification differ."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenAgentExecutionError(f"{label} identity differs")


def _task(workload: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    matches = [task for task in workload["agent"]["tasks"] if task["id"] == task_id]
    if len(matches) != 1:
        raise QwenAgentExecutionError("agent task binding differs")
    return matches[0]


def _turn_comparison(
    turns: Sequence[Mapping[str, Any]], expected_turns: Sequence[Mapping[str, Any]]
) -> tuple[bool, list[dict[str, Any]]]:
    comparisons: list[dict[str, Any]] = []
    exact = len(turns) == len(expected_turns)
    for index, turn in enumerate(turns):
        if not isinstance(turn, Mapping):
            raise QwenAgentExecutionError("agent turn evidence must be an object")
        expected = expected_turns[index] if index < len(expected_turns) else None
        required = {
            "base_session_id",
            "content",
            "control_id",
            "controlled_execution_id",
            "generated_text_raw",
            "generated_text_visible",
            "generated_token_count",
            "generated_token_ids",
            "parsed_calls",
            "prompt_token_count",
            "prompt_token_sha256",
            "reasoning",
            "status",
            "stop_reason",
            "turn",
        }
        exact_keys(dict(turn), required, set(), f"agent turn evidence {index + 1}")
        for field in (
            "base_session_id",
            "control_id",
            "controlled_execution_id",
            "prompt_token_sha256",
        ):
            require_sha256(turn[field], f"agent turn evidence {index + 1}.{field}")
        generated = turn["generated_token_ids"]
        if (
            not isinstance(generated, list)
            or not generated
            or any(
                isinstance(token, bool)
                or not isinstance(token, int)
                or not 0 <= token < 151_669
                for token in generated
            )
            or turn["generated_token_count"] != len(generated)
            or generated[-1] not in EOS_TOKEN_IDS
            or any(token in EOS_TOKEN_IDS for token in generated[:-1])
            or turn["turn"] != index + 1
            or turn["status"] not in {"fail", "pass"}
            or turn["stop_reason"] != "eos"
            or not isinstance(turn["generated_text_raw"], str)
            or not isinstance(turn["generated_text_visible"], str)
            or not isinstance(turn["reasoning"], str)
            or not isinstance(turn["content"], str)
            or not isinstance(turn["parsed_calls"], list)
        ):
            raise QwenAgentExecutionError("agent turn evidence boundary differs")
        parsed = parse_assistant_output(turn["generated_text_raw"])
        if (
            list(parsed.calls) != turn["parsed_calls"]
            or parsed.content != turn["content"]
            or parsed.reasoning != turn["reasoning"]
        ):
            raise QwenAgentExecutionError("agent turn parsed evidence differs")
        expected_generation = None if expected is None else expected["expected"]
        turn_exact = bool(
            expected is not None
            and turn["turn"] == expected["turn"]
            and turn["prompt_token_count"] == expected["prompt"]["prompt_token_count"]
            and turn["prompt_token_sha256"] == expected["prompt"]["prompt_token_sha256"]
            and turn["generated_token_ids"]
            == expected_generation["generated_token_ids"]
            and turn["generated_text_raw"]
            == expected_generation["generated_text_raw"]
            and turn["generated_text_visible"]
            == expected_generation["generated_text_visible"]
            and turn["parsed_calls"] == expected_generation["calls"]
            and turn["content"] == expected_generation["content"]
            and turn["reasoning"] == expected_generation["reasoning"]
            and turn["status"] == "pass"
        )
        comparisons.append({"exact_rom_golden": turn_exact, "turn": index + 1})
        exact = exact and turn_exact
    return exact, comparisons


def _action_causality(
    actions: Sequence[Mapping[str, Any]], turns: Sequence[Mapping[str, Any]]
) -> bool:
    expected_calls = [
        {
            "call_index": call_index,
            "command": call["arguments"]["command"],
            "turn": turn["turn"],
        }
        for turn in turns
        for call_index, call in enumerate(turn["parsed_calls"], start=1)
    ]
    if len(actions) != len(expected_calls):
        return False
    required = {
        "call_index",
        "command",
        "exit_code",
        "stderr",
        "stdout",
        "timed_out",
        "truncated",
        "turn",
        "type",
    }
    for index, (action, expected) in enumerate(
        zip(actions, expected_calls, strict=True), start=1
    ):
        if not isinstance(action, Mapping):
            raise QwenAgentExecutionError("agent action evidence must be an object")
        exact_keys(dict(action), required, set(), f"agent action evidence {index}")
        if (
            action["call_index"] != expected["call_index"]
            or action["command"] != expected["command"]
            or action["turn"] != expected["turn"]
            or action["type"] != "bash_action"
            or (
                action["exit_code"] is not None
                and (
                    isinstance(action["exit_code"], bool)
                    or not isinstance(action["exit_code"], int)
                )
            )
            or not isinstance(action["stderr"], str)
            or not isinstance(action["stdout"], str)
            or not isinstance(action["timed_out"], bool)
            or not isinstance(action["truncated"], bool)
        ):
            return False
    return True


def build_agent_task_execution(
    workload_value: Mapping[str, Any],
    *,
    task_id: str,
    build_id: str,
    graph_id: str,
    docker_version: str,
    image_id: str,
    image_tag: str,
    isolation: Mapping[str, Any],
    turns: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    final_answer: str | None,
    test_exit_code: int,
    test_stdout: str,
    test_stderr: str,
) -> dict[str, Any]:
    """Build one task result from accelerator generations and live actions."""

    try:
        workload = validate_shared_workload(workload_value)
    except QwenWorkloadError as exc:
        raise QwenAgentExecutionError(f"agent workload differs: {exc}") from exc
    task = _task(workload, task_id)
    expected = task["expected"]
    normalized_turns = [dict(turn) for turn in turns]
    normalized_actions = [dict(action) for action in actions]
    exact_turns, turn_comparisons = _turn_comparison(
        normalized_turns, expected["turns"]
    )
    causal_actions = _action_causality(normalized_actions, normalized_turns)
    exact_actions = normalized_actions == expected["commands"]
    exact_final = final_answer == expected["final_answer"]
    exact_tests = (
        test_exit_code == expected["test_exit_code"]
        and test_stdout == expected["rom_test_stdout"]
        and test_stderr == expected["rom_test_stderr"]
    )
    exact_image = image_id == expected["rom_image_id"]
    passed = (
        exact_turns
        and causal_actions
        and exact_actions
        and exact_final
        and exact_tests
        and exact_image
    )
    body: dict[str, Any] = {
        "actions": normalized_actions,
        "build_id": require_sha256(build_id, "agent execution build ID"),
        "claim_boundary": {
            "all_model_turns_artifact_only": exact_turns,
            "environment_actions_model_generated": causal_actions,
            "isolated_environment_verified": True,
            "semantic_rom_golden_exact": passed,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
            "withheld_task_tests_passed": exact_tests,
        },
        "command_count": len(normalized_actions),
        "comparison": {
            "exact_rom_actions": exact_actions,
            "exact_rom_final_answer": exact_final,
            "exact_rom_image": exact_image,
            "exact_rom_tests": exact_tests,
            "exact_rom_turns": exact_turns,
            "turns": turn_comparisons,
        },
        "docker": {
            "image_id": image_id,
            "image_tag": image_tag,
            "server_version": docker_version,
        },
        "final_answer": final_answer,
        "graph_id": require_sha256(graph_id, "agent execution graph ID"),
        "instruction": task["source"]["instruction"],
        "isolation": dict(isolation),
        "model_generated_token_count": sum(
            turn["generated_token_count"] for turn in normalized_turns
        ),
        "runner_version": VERSION,
        "schema": SCHEMA,
        "status": "pass" if passed else "fail",
        "task_id": task_id,
        "terminalbench_commit": workload["agent"]["terminalbench_commit"],
        "test": {
            "exit_code": test_exit_code,
            "stderr": test_stderr,
            "stdout": test_stdout,
        },
        "turn_count": len(normalized_turns),
        "turns": normalized_turns,
        "workload_id": workload["workload_id"],
    }
    return validate_agent_task_execution(
        _identified(body, "agent_execution_id"), workload
    )


def validate_agent_task_execution(
    value: Mapping[str, Any], workload_value: Mapping[str, Any]
) -> dict[str, Any]:
    """Independently reconstruct all live-agent comparison and claim fields."""

    try:
        workload = validate_shared_workload(workload_value)
    except QwenWorkloadError as exc:
        raise QwenAgentExecutionError(f"agent workload differs: {exc}") from exc
    execution = dict(value)
    exact_keys(
        execution,
        {
            "actions",
            "agent_execution_id",
            "build_id",
            "claim_boundary",
            "command_count",
            "comparison",
            "docker",
            "final_answer",
            "graph_id",
            "instruction",
            "isolation",
            "model_generated_token_count",
            "runner_version",
            "schema",
            "status",
            "task_id",
            "terminalbench_commit",
            "test",
            "turn_count",
            "turns",
            "workload_id",
        },
        set(),
        "Qwen agent task execution",
    )
    _identity(execution, "agent_execution_id", "Qwen agent task execution")
    for field in ("build_id", "graph_id", "workload_id"):
        require_sha256(execution[field], f"Qwen agent task execution.{field}")
    task = _task(workload, execution["task_id"])
    expected = task["expected"]
    turns = execution["turns"]
    actions = execution["actions"]
    if not isinstance(turns, list) or not isinstance(actions, list):
        raise QwenAgentExecutionError("agent turn or action coverage differs")
    exact_turns, turn_comparisons = _turn_comparison(turns, expected["turns"])
    causal_actions = _action_causality(actions, turns)
    exact_actions = actions == expected["commands"]
    test = execution["test"]
    if not isinstance(test, dict):
        raise QwenAgentExecutionError("agent test evidence must be an object")
    exact_keys(test, {"exit_code", "stderr", "stdout"}, set(), "agent test evidence")
    exact_tests = test == {
        "exit_code": expected["test_exit_code"],
        "stderr": expected["rom_test_stderr"],
        "stdout": expected["rom_test_stdout"],
    }
    docker = execution["docker"]
    if not isinstance(docker, dict):
        raise QwenAgentExecutionError("agent Docker evidence must be an object")
    exact_keys(
        docker,
        {"image_id", "image_tag", "server_version"},
        set(),
        "agent Docker evidence",
    )
    if (
        not isinstance(docker["image_id"], str)
        or IMAGE_ID.fullmatch(docker["image_id"]) is None
        or not isinstance(docker["image_tag"], str)
        or not docker["image_tag"]
        or not isinstance(docker["server_version"], str)
        or not docker["server_version"]
    ):
        raise QwenAgentExecutionError("agent Docker boundary differs")
    exact_image = docker["image_id"] == expected["rom_image_id"]
    isolation = execution["isolation"]
    expected_isolation = {
        "cap_drop_all": True,
        "host_mounts": False,
        "network": "none",
        "no_new_privileges": True,
        "pids_limit": 128,
        "privileged": False,
        "read_only_rootfs": False,
    }
    if isolation != expected_isolation:
        raise QwenAgentExecutionError("agent isolation boundary differs")
    exact_final = execution["final_answer"] == expected["final_answer"]
    passed = (
        exact_turns
        and causal_actions
        and exact_actions
        and exact_final
        and exact_tests
        and exact_image
    )
    expected_comparison = {
        "exact_rom_actions": exact_actions,
        "exact_rom_final_answer": exact_final,
        "exact_rom_image": exact_image,
        "exact_rom_tests": exact_tests,
        "exact_rom_turns": exact_turns,
        "turns": turn_comparisons,
    }
    if (
        execution["schema"] != SCHEMA
        or execution["runner_version"] != VERSION
        or execution["workload_id"] != workload["workload_id"]
        or execution["terminalbench_commit"]
        != workload["agent"]["terminalbench_commit"]
        or execution["instruction"] != task["source"]["instruction"]
        or execution["turn_count"] != len(turns)
        or execution["command_count"] != len(actions)
        or execution["model_generated_token_count"]
        != sum(turn["generated_token_count"] for turn in turns)
        or execution["comparison"] != expected_comparison
        or execution["status"] != ("pass" if passed else "fail")
        or execution["claim_boundary"]
        != {
            "all_model_turns_artifact_only": exact_turns,
            "environment_actions_model_generated": causal_actions,
            "isolated_environment_verified": True,
            "semantic_rom_golden_exact": passed,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
            "withheld_task_tests_passed": exact_tests,
        }
    ):
        raise QwenAgentExecutionError("agent execution boundary differs")
    return execution


def publish_agent_task_execution(
    value: Mapping[str, Any], workload: Mapping[str, Any], output: Path
) -> None:
    execution = validate_agent_task_execution(value, workload)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(execution))
    except FileExistsError as exc:
        raise QwenAgentExecutionError(
            f"agent task execution already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenAgentExecutionError(
            f"cannot publish agent task execution: {exc}"
        ) from exc


__all__ = [
    "QwenAgentExecutionError",
    "SCHEMA",
    "VERSION",
    "build_agent_task_execution",
    "publish_agent_task_execution",
    "validate_agent_task_execution",
]
