from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_agent_execution import (
    QwenAgentExecutionError,
    build_agent_task_execution,
    validate_agent_task_execution,
)
from compiler.tensor_accelerator.qwen_workload import validate_shared_workload
from tools.run_qwen3_tensor_accelerator_live_agent import _docker_run_arguments


ROOT = Path(__file__).resolve().parents[2]
WORKLOAD_PATH = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_agent_task_execution_v1.schema.json"
)
ISOLATION = {
    "cap_drop_all": True,
    "host_mounts": False,
    "network": "none",
    "no_new_privileges": True,
    "pids_limit": 128,
    "privileged": False,
    "read_only_rootfs": False,
}


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _turns(task: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for turn in task["expected"]["turns"]:
        expected = turn["expected"]
        result.append(
            {
                "base_session_id": "a" * 64,
                "content": expected["content"],
                "control_id": "b" * 64,
                "controlled_execution_id": "c" * 64,
                "generated_text_raw": expected["generated_text_raw"],
                "generated_text_visible": expected["generated_text_visible"],
                "generated_token_count": expected["generated_token_count"],
                "generated_token_ids": expected["generated_token_ids"],
                "parsed_calls": expected["calls"],
                "prompt_token_count": turn["prompt"]["prompt_token_count"],
                "prompt_token_sha256": turn["prompt"]["prompt_token_sha256"],
                "reasoning": expected["reasoning"],
                "status": "pass",
                "stop_reason": "eos",
                "turn": turn["turn"],
            }
        )
    return result


@pytest.mark.parametrize("task_id", ["hello-world", "fix-permissions"])
def test_agent_execution_reconstructs_exact_turn_action_and_test_evidence(
    task_id: str,
) -> None:
    workload = validate_shared_workload(load_strict_json(WORKLOAD_PATH))
    task = next(item for item in workload["agent"]["tasks"] if item["id"] == task_id)
    expected = task["expected"]
    execution = build_agent_task_execution(
        workload,
        task_id=task_id,
        build_id="d" * 64,
        graph_id="e" * 64,
        docker_version="28.5.2",
        image_id=expected["rom_image_id"],
        image_tag=f"opentallas-qwen3-tbench:d28711d0da26-{task_id}",
        isolation=ISOLATION,
        turns=_turns(task),
        actions=expected["commands"],
        final_answer=expected["final_answer"],
        test_exit_code=expected["test_exit_code"],
        test_stdout=expected["rom_test_stdout"],
        test_stderr=expected["rom_test_stderr"],
    )
    assert execution["status"] == "pass"
    assert execution["claim_boundary"] == {
        "all_model_turns_artifact_only": True,
        "environment_actions_model_generated": True,
        "isolated_environment_verified": True,
        "semantic_rom_golden_exact": True,
        "target_precision_reference_verified": False,
        "timing_or_performance": False,
        "withheld_task_tests_passed": True,
    }
    assert validate_agent_task_execution(execution, workload) == execution
    schema = load_strict_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(execution)


def test_agent_execution_retains_failure_and_rejects_forged_causality() -> None:
    workload = validate_shared_workload(load_strict_json(WORKLOAD_PATH))
    task = workload["agent"]["tasks"][0]
    expected = task["expected"]
    failed = build_agent_task_execution(
        workload,
        task_id=task["id"],
        build_id="d" * 64,
        graph_id="e" * 64,
        docker_version="28.5.2",
        image_id=expected["rom_image_id"],
        image_tag="opentallas-qwen3-tbench:d28711d0da26-hello-world",
        isolation=ISOLATION,
        turns=_turns(task),
        actions=expected["commands"],
        final_answer="wrong answer",
        test_exit_code=expected["test_exit_code"],
        test_stdout=expected["rom_test_stdout"],
        test_stderr=expected["rom_test_stderr"],
    )
    assert failed["status"] == "fail"
    assert failed["comparison"]["exact_rom_final_answer"] is False

    forged = copy.deepcopy(failed)
    forged["actions"][0]["command"] = "echo forged"
    forged = _reidentify(forged, "agent_execution_id")
    with pytest.raises(QwenAgentExecutionError, match="boundary differs"):
        validate_agent_task_execution(forged, workload)


def test_agent_container_arguments_have_no_network_mount_or_capabilities() -> None:
    arguments = _docker_run_arguments("container", "image")
    assert arguments[:2] == ["docker", "run"]
    assert arguments[arguments.index("--network") + 1] == "none"
    assert arguments[arguments.index("--cap-drop") + 1] == "ALL"
    assert arguments[arguments.index("--security-opt") + 1] == (
        "no-new-privileges:true"
    )
    assert not any(argument.startswith("--volume") for argument in arguments)
    assert "-v" not in arguments
