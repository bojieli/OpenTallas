"""Coherent acceptance evidence for Qwen natural and live-agent workloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
)
from .qwen_agent_execution import (
    QwenAgentExecutionError,
    validate_agent_task_execution,
)
from .qwen_chat import EOS_TOKEN_IDS
from .qwen_workload import (
    AGENT_TASK_IDS,
    NATURAL_QUESTION_IDS,
    QwenWorkloadError,
    validate_shared_workload,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_natural_agent_campaign.v1"
VERSION = "tensor-accelerator-qwen-natural-agent-campaign-0.1.0"
CONTROLLED_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_controlled_dynamic_session_execution.v1"
)


class QwenNaturalAgentCampaignError(ArtifactError):
    """Raised when the governed natural and agent campaign is incoherent."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenNaturalAgentCampaignError(f"{label} identity differs")


def _artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = canonical_json_bytes(value)
    return {"sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def _natural_case(workload: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    matches = [
        record for record in workload["natural_questions"] if record["id"] == case_id
    ]
    if len(matches) != 1:
        raise QwenNaturalAgentCampaignError("natural campaign binding differs")
    return matches[0]


def _agent_task(workload: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    matches = [task for task in workload["agent"]["tasks"] if task["id"] == task_id]
    if len(matches) != 1:
        raise QwenNaturalAgentCampaignError("agent campaign binding differs")
    return matches[0]


def _require_passed_controlled_execution(
    execution_value: Mapping[str, Any],
    workload: Mapping[str, Any],
    *,
    kind: str,
    case_id: str,
    turn: int | None,
    expected_prompt: Mapping[str, Any],
    expected_generation: Mapping[str, Any],
) -> dict[str, Any]:
    execution = dict(execution_value)
    for field in (
        "base_session_id",
        "build_id",
        "control_id",
        "controlled_execution_id",
        "graph_id",
        "workload_id",
    ):
        require_sha256(execution.get(field), f"controlled execution.{field}")
    binding = execution.get("workload_binding")
    decoded = execution.get("decoded")
    comparison = execution.get("comparison")
    legitimacy = execution.get("token_legitimacy")
    claim = execution.get("claim_boundary")
    generated = execution.get("generated_token_ids")
    if not all(
        isinstance(value, dict)
        for value in (binding, decoded, comparison, legitimacy, claim)
    ) or not isinstance(generated, list):
        raise QwenNaturalAgentCampaignError(
            "controlled execution evidence is incomplete"
        )
    expected_ids = expected_generation["generated_token_ids"]
    transaction_count = expected_prompt["prompt_token_count"] + len(expected_ids) - 1
    if (
        execution.get("schema") != CONTROLLED_EXECUTION_SCHEMA
        or execution["workload_id"] != workload["workload_id"]
        or binding.get("kind") != kind
        or binding.get("case_id") != case_id
        or binding.get("turn") != turn
        or binding.get("prompt_token_count") != expected_prompt["prompt_token_count"]
        or binding.get("prompt_token_sha256") != expected_prompt["prompt_token_sha256"]
        or execution.get("prompt_token_count") != expected_prompt["prompt_token_count"]
        or execution.get("prompt_token_ids") != expected_prompt["prompt_token_ids"]
        or decoded.get("prompt_text_raw") != expected_prompt["prompt_text"]
        or generated != expected_ids
        or execution.get("generated_token_count") != len(expected_ids)
        or decoded.get("generated_text_raw")
        != expected_generation["generated_text_raw"]
        or decoded.get("generated_text_visible")
        != expected_generation["generated_text_visible"]
        or execution.get("status") != "pass"
        or execution.get("stop_reason") != "eos"
        or execution.get("eos_observed") is not True
        or expected_ids[-1] not in EOS_TOKEN_IDS
        or any(token in EOS_TOKEN_IDS for token in expected_ids[:-1])
        or execution.get("transaction_count") != transaction_count
        or execution.get("decode_transaction_count") != len(expected_ids) - 1
        or comparison.get("status") != "exact_match"
        or comparison.get("exact_eos") is not True
        or comparison.get("exact_generated_token_ids") is not True
        or comparison.get("exact_generated_text_raw") is not True
        or comparison.get("exact_generated_text_visible") is not True
        or claim.get("artifact_only_dynamic_session_executed") is not True
        or claim.get("semantic_rom_golden_exact") is not True
        or claim.get("token_legitimacy_verified") is not True
        or claim.get("timing_or_performance") is not False
        or legitimacy.get("all_generated_token_ids_resolve") is not True
        or legitimacy.get("all_generated_token_ids_within_explicit_vocabulary")
        is not True
        or legitimacy.get("padded_model_rows_rejected") is not True
    ):
        raise QwenNaturalAgentCampaignError(
            f"controlled execution for {case_id} turn {turn} did not pass exactly"
        )
    return execution


def _natural_summary(
    execution_value: Mapping[str, Any],
    workload: Mapping[str, Any],
    case_id: str,
) -> dict[str, Any]:
    case = _natural_case(workload, case_id)
    expected = case["expected"]
    execution = _require_passed_controlled_execution(
        execution_value,
        workload,
        kind="natural_question",
        case_id=case_id,
        turn=None,
        expected_prompt=case["prompt"],
        expected_generation=expected,
    )
    return {
        "artifact": _artifact(execution),
        "artifact_only_model_forwards": True,
        "base_session_id": execution["base_session_id"],
        "build_id": execution["build_id"],
        "case_id": case_id,
        "control_id": execution["control_id"],
        "controlled_execution_id": execution["controlled_execution_id"],
        "decode_transaction_count": execution["decode_transaction_count"],
        "enable_thinking": case["enable_thinking"],
        "exact_rom_golden": True,
        "first_eos_stop_verified": True,
        "graph_id": execution["graph_id"],
        "generation": {
            "eos_token_id": expected["eos_token_id"],
            "generated_text_raw": execution["decoded"]["generated_text_raw"],
            "generated_text_visible": execution["decoded"]["generated_text_visible"],
            "generated_token_count": execution["generated_token_count"],
            "generated_token_ids": execution["generated_token_ids"],
            "stop_reason": execution["stop_reason"],
            "token_legitimacy_verified": True,
        },
        "prompt": case["prompt"],
        "rom_result_id": expected["rom_result_id"],
        "source_messages": case["messages"],
        "status": "pass",
        "transaction_count": execution["transaction_count"],
    }


def _agent_turn_summary(
    execution_value: Mapping[str, Any],
    report_turn: Mapping[str, Any],
    workload: Mapping[str, Any],
    task: Mapping[str, Any],
    expected_turn: Mapping[str, Any],
    *,
    expected_build_id: str,
    expected_graph_id: str,
) -> dict[str, Any]:
    expected = expected_turn["expected"]
    execution = _require_passed_controlled_execution(
        execution_value,
        workload,
        kind="agent_turn",
        case_id=task["id"],
        turn=expected_turn["turn"],
        expected_prompt=expected_turn["prompt"],
        expected_generation=expected,
    )
    if (
        execution["build_id"] != expected_build_id
        or execution["graph_id"] != expected_graph_id
        or report_turn["turn"] != expected_turn["turn"]
        or report_turn["base_session_id"] != execution["base_session_id"]
        or report_turn["control_id"] != execution["control_id"]
        or report_turn["controlled_execution_id"]
        != execution["controlled_execution_id"]
        or report_turn["prompt_token_count"]
        != expected_turn["prompt"]["prompt_token_count"]
        or report_turn["prompt_token_sha256"]
        != expected_turn["prompt"]["prompt_token_sha256"]
        or report_turn["generated_token_ids"] != expected["generated_token_ids"]
        or report_turn["generated_text_raw"] != expected["generated_text_raw"]
        or report_turn["generated_text_visible"] != expected["generated_text_visible"]
        or report_turn["parsed_calls"] != expected["calls"]
        or report_turn["content"] != expected["content"]
        or report_turn["reasoning"] != expected["reasoning"]
        or report_turn["status"] != "pass"
        or report_turn["stop_reason"] != "eos"
    ):
        raise QwenNaturalAgentCampaignError(
            f"agent report and controlled turn differ for {task['id']} "
            f"turn {expected_turn['turn']}"
        )
    return {
        "artifact": _artifact(execution),
        "base_session_id": execution["base_session_id"],
        "build_id": execution["build_id"],
        "content": report_turn["content"],
        "control_id": execution["control_id"],
        "controlled_execution_id": execution["controlled_execution_id"],
        "decode_transaction_count": execution["decode_transaction_count"],
        "exact_rom_golden": True,
        "generation": {
            "generated_text_raw": report_turn["generated_text_raw"],
            "generated_text_visible": report_turn["generated_text_visible"],
            "generated_token_count": report_turn["generated_token_count"],
            "generated_token_ids": report_turn["generated_token_ids"],
            "stop_reason": "eos",
            "token_legitimacy_verified": True,
        },
        "graph_id": execution["graph_id"],
        "parsed_calls": report_turn["parsed_calls"],
        "prompt": expected_turn["prompt"],
        "reasoning": report_turn["reasoning"],
        "rom_result_id": expected["rom_result_id"],
        "status": "pass",
        "transaction_count": execution["transaction_count"],
        "turn": expected_turn["turn"],
    }


def _agent_summary(
    execution_value: Mapping[str, Any],
    turn_execution_values: Sequence[Mapping[str, Any]],
    workload: Mapping[str, Any],
    task_id: str,
) -> dict[str, Any]:
    try:
        execution = validate_agent_task_execution(execution_value, workload)
    except QwenAgentExecutionError as exc:
        raise QwenNaturalAgentCampaignError(
            f"agent task execution differs: {exc}"
        ) from exc
    task = _agent_task(workload, task_id)
    expected_turns = task["expected"]["turns"]
    if (
        execution["task_id"] != task_id
        or execution["status"] != "pass"
        or len(turn_execution_values) != len(expected_turns)
        or len(execution["turns"]) != len(expected_turns)
    ):
        raise QwenNaturalAgentCampaignError(
            f"agent task {task_id} did not complete exactly"
        )
    turns = [
        _agent_turn_summary(
            turn_execution,
            report_turn,
            workload,
            task,
            expected_turn,
            expected_build_id=execution["build_id"],
            expected_graph_id=execution["graph_id"],
        )
        for turn_execution, report_turn, expected_turn in zip(
            turn_execution_values,
            execution["turns"],
            expected_turns,
            strict=True,
        )
    ]
    return {
        "actions": execution["actions"],
        "agent_execution_id": execution["agent_execution_id"],
        "artifact": _artifact(execution),
        "build_id": execution["build_id"],
        "command_count": execution["command_count"],
        "docker_image_id": execution["docker"]["image_id"],
        "environment_actions_model_generated": True,
        "final_answer": execution["final_answer"],
        "graph_id": execution["graph_id"],
        "instruction": execution["instruction"],
        "isolated_environment_verified": True,
        "semantic_rom_golden_exact": True,
        "status": "pass",
        "task_id": task_id,
        "test": execution["test"],
        "turn_count": execution["turn_count"],
        "turns": turns,
        "withheld_task_tests_passed": True,
    }


def _totals(
    natural: Sequence[Mapping[str, Any]], agent: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    agent_turns = [turn for task in agent for turn in task["turns"]]
    natural_prompt = sum(item["prompt"]["prompt_token_count"] for item in natural)
    natural_generated = sum(
        item["generation"]["generated_token_count"] for item in natural
    )
    natural_transactions = sum(item["transaction_count"] for item in natural)
    natural_decode = sum(item["decode_transaction_count"] for item in natural)
    agent_prompt = sum(item["prompt"]["prompt_token_count"] for item in agent_turns)
    agent_generated = sum(
        item["generation"]["generated_token_count"] for item in agent_turns
    )
    agent_transactions = sum(item["transaction_count"] for item in agent_turns)
    agent_decode = sum(item["decode_transaction_count"] for item in agent_turns)
    return {
        "agent_decode_transaction_count": agent_decode,
        "agent_generated_token_count": agent_generated,
        "agent_prompt_token_count": agent_prompt,
        "agent_transaction_count": agent_transactions,
        "generated_token_count": natural_generated + agent_generated,
        "model_transaction_count": natural_transactions + agent_transactions,
        "natural_decode_transaction_count": natural_decode,
        "natural_generated_token_count": natural_generated,
        "natural_prompt_token_count": natural_prompt,
        "natural_transaction_count": natural_transactions,
    }


def _claim_boundary() -> dict[str, bool]:
    return {
        "all_generated_tokens_legitimate": True,
        "all_model_forwards_artifact_only": True,
        "deepseek_200000_token_acceptance": False,
        "exact_8000_token_acceptance": False,
        "first_eos_termination_verified": True,
        "live_agent_environment_actions_causal": True,
        "live_agent_suite_complete": True,
        "live_agent_withheld_tests_passed": True,
        "natural_chat_reasoning_suite_complete": True,
        "official_chat_template_verified": True,
        "release_admission_claimed": False,
        "semantic_rom_golden_exact": True,
        "target_precision_reference_verified": False,
        "timing_or_performance": False,
    }


def _validate_unique_children(
    natural: Sequence[Mapping[str, Any]], agent: Sequence[Mapping[str, Any]]
) -> None:
    turns = [turn for task in agent for turn in task["turns"]]
    controlled = [item["controlled_execution_id"] for item in natural] + [
        item["controlled_execution_id"] for item in turns
    ]
    sessions = [item["base_session_id"] for item in natural] + [
        item["base_session_id"] for item in turns
    ]
    controls = [item["control_id"] for item in natural] + [
        item["control_id"] for item in turns
    ]
    agent_ids = [item["agent_execution_id"] for item in agent]
    if any(
        len(values) != len(set(values))
        for values in (controlled, sessions, controls, agent_ids)
    ):
        raise QwenNaturalAgentCampaignError("campaign child identities are not unique")


def build_natural_agent_campaign(
    workload_value: Mapping[str, Any],
    *,
    natural_executions: Mapping[str, Mapping[str, Any]],
    agent_executions: Mapping[str, Mapping[str, Any]],
    agent_turn_executions: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Build one exact six-question and two-task campaign aggregate.

    Callers must first run the full child-artifact validators. This builder then
    cross-checks their identities, prompt/generation semantics, and task causality
    before producing the compact campaign evidence.
    """

    try:
        workload = validate_shared_workload(workload_value)
    except QwenWorkloadError as exc:
        raise QwenNaturalAgentCampaignError(
            f"campaign workload differs: {exc}"
        ) from exc
    if tuple(natural_executions) != NATURAL_QUESTION_IDS:
        raise QwenNaturalAgentCampaignError(
            "natural campaign coverage or ordering differs"
        )
    if (
        tuple(agent_executions) != AGENT_TASK_IDS
        or tuple(agent_turn_executions) != AGENT_TASK_IDS
    ):
        raise QwenNaturalAgentCampaignError(
            "agent campaign coverage or ordering differs"
        )
    natural = [
        _natural_summary(natural_executions[case_id], workload, case_id)
        for case_id in NATURAL_QUESTION_IDS
    ]
    agent = [
        _agent_summary(
            agent_executions[task_id],
            agent_turn_executions[task_id],
            workload,
            task_id,
        )
        for task_id in AGENT_TASK_IDS
    ]
    _validate_unique_children(natural, agent)
    child_build_ids = {
        execution["build_id"] for execution in natural_executions.values()
    } | {execution["build_id"] for execution in agent_executions.values()}
    child_graph_ids = {
        execution["graph_id"] for execution in natural_executions.values()
    } | {execution["graph_id"] for execution in agent_executions.values()}
    if len(child_build_ids) != 1 or len(child_graph_ids) != 1:
        raise QwenNaturalAgentCampaignError(
            "campaign deployment build or graph identity differs"
        )
    build_id = require_sha256(child_build_ids.pop(), "campaign build ID")
    graph_id = require_sha256(child_graph_ids.pop(), "campaign graph ID")
    body: dict[str, Any] = {
        "agent_executions": agent,
        "build_id": build_id,
        "campaign_version": VERSION,
        "claim_boundary": _claim_boundary(),
        "graph_id": graph_id,
        "model_id": workload["model"]["id"],
        "natural_executions": natural,
        "schema": SCHEMA,
        "scope": {
            "agent_command_count": sum(item["command_count"] for item in agent),
            "agent_task_count": len(agent),
            "agent_turn_count": sum(item["turn_count"] for item in agent),
            "natural_case_count": len(natural),
        },
        "source_binding": {
            "bash_tool_sha256": workload["agent"]["bash_tool_sha256"],
            "checkpoint_lock_id": workload["model"]["checkpoint_lock_id"],
            "model_revision": workload["model"]["revision"],
            "official_chat_template_sha256": workload["official_chat_template_sha256"],
            "rom_agent_campaign_id": workload["agent"]["rom_campaign_id"],
            "rom_agent_suite_id": workload["agent"]["rom_suite_id"],
            "terminalbench_commit": workload["agent"]["terminalbench_commit"],
        },
        "status": "pass",
        "totals": _totals(natural, agent),
        "workload_id": workload["workload_id"],
    }
    return validate_natural_agent_campaign(_identified(body, "campaign_id"), workload)


def _validate_artifact(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenNaturalAgentCampaignError(f"{label} must be an object")
    exact_keys(value, {"sha256", "size_bytes"}, set(), label)
    require_sha256(value["sha256"], f"{label}.sha256")
    if (
        isinstance(value["size_bytes"], bool)
        or not isinstance(value["size_bytes"], int)
        or value["size_bytes"] < 1
    ):
        raise QwenNaturalAgentCampaignError(f"{label} size differs")
    return value


def _validate_prompt(value: object, expected: Mapping[str, Any], label: str) -> None:
    if not isinstance(value, dict) or value != expected:
        raise QwenNaturalAgentCampaignError(f"{label} differs")


def _validate_natural_summary(
    value: object, expected_case: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenNaturalAgentCampaignError("natural campaign record must be an object")
    exact_keys(
        value,
        {
            "artifact",
            "artifact_only_model_forwards",
            "base_session_id",
            "build_id",
            "case_id",
            "control_id",
            "controlled_execution_id",
            "decode_transaction_count",
            "enable_thinking",
            "exact_rom_golden",
            "first_eos_stop_verified",
            "generation",
            "graph_id",
            "prompt",
            "rom_result_id",
            "source_messages",
            "status",
            "transaction_count",
        },
        set(),
        f"natural campaign record {expected_case['id']}",
    )
    _validate_artifact(value["artifact"], "natural child artifact")
    for field in (
        "base_session_id",
        "build_id",
        "control_id",
        "controlled_execution_id",
        "graph_id",
        "rom_result_id",
    ):
        require_sha256(value[field], f"natural campaign record.{field}")
    expected = expected_case["expected"]
    expected_generation = {
        "eos_token_id": expected["eos_token_id"],
        "generated_text_raw": expected["generated_text_raw"],
        "generated_text_visible": expected["generated_text_visible"],
        "generated_token_count": expected["generated_token_count"],
        "generated_token_ids": expected["generated_token_ids"],
        "stop_reason": "eos",
        "token_legitimacy_verified": True,
    }
    prompt_count = expected_case["prompt"]["prompt_token_count"]
    generated_count = expected["generated_token_count"]
    if (
        value["case_id"] != expected_case["id"]
        or value["source_messages"] != expected_case["messages"]
        or value["enable_thinking"] is not expected_case["enable_thinking"]
        or value["generation"] != expected_generation
        or value["rom_result_id"] != expected["rom_result_id"]
        or value["transaction_count"] != prompt_count + generated_count - 1
        or value["decode_transaction_count"] != generated_count - 1
        or value["artifact_only_model_forwards"] is not True
        or value["exact_rom_golden"] is not True
        or value["first_eos_stop_verified"] is not True
        or value["status"] != "pass"
    ):
        raise QwenNaturalAgentCampaignError(
            f"natural campaign result differs for {expected_case['id']}"
        )
    _validate_prompt(
        value["prompt"], expected_case["prompt"], f"{expected_case['id']} prompt"
    )
    return value


def _validate_agent_turn_summary(
    value: object, expected_turn: Mapping[str, Any], task_id: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenNaturalAgentCampaignError("agent turn summary must be an object")
    exact_keys(
        value,
        {
            "artifact",
            "base_session_id",
            "build_id",
            "content",
            "control_id",
            "controlled_execution_id",
            "decode_transaction_count",
            "exact_rom_golden",
            "generation",
            "graph_id",
            "parsed_calls",
            "prompt",
            "reasoning",
            "rom_result_id",
            "status",
            "transaction_count",
            "turn",
        },
        set(),
        f"agent campaign {task_id} turn summary",
    )
    _validate_artifact(value["artifact"], "agent turn child artifact")
    for field in (
        "base_session_id",
        "build_id",
        "control_id",
        "controlled_execution_id",
        "graph_id",
        "rom_result_id",
    ):
        require_sha256(value[field], f"agent turn summary.{field}")
    expected = expected_turn["expected"]
    expected_generation = {
        "generated_text_raw": expected["generated_text_raw"],
        "generated_text_visible": expected["generated_text_visible"],
        "generated_token_count": expected["generated_token_count"],
        "generated_token_ids": expected["generated_token_ids"],
        "stop_reason": "eos",
        "token_legitimacy_verified": True,
    }
    prompt_count = expected_turn["prompt"]["prompt_token_count"]
    generated_count = expected["generated_token_count"]
    if (
        value["turn"] != expected_turn["turn"]
        or value["generation"] != expected_generation
        or value["parsed_calls"] != expected["calls"]
        or value["content"] != expected["content"]
        or value["reasoning"] != expected["reasoning"]
        or value["rom_result_id"] != expected["rom_result_id"]
        or value["transaction_count"] != prompt_count + generated_count - 1
        or value["decode_transaction_count"] != generated_count - 1
        or value["exact_rom_golden"] is not True
        or value["status"] != "pass"
    ):
        raise QwenNaturalAgentCampaignError(
            f"agent campaign result differs for {task_id} turn {expected_turn['turn']}"
        )
    _validate_prompt(
        value["prompt"],
        expected_turn["prompt"],
        f"{task_id} turn {expected_turn['turn']} prompt",
    )
    return value


def _validate_agent_summary(
    value: object, expected_task: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenNaturalAgentCampaignError("agent campaign record must be an object")
    exact_keys(
        value,
        {
            "actions",
            "agent_execution_id",
            "artifact",
            "build_id",
            "command_count",
            "docker_image_id",
            "environment_actions_model_generated",
            "final_answer",
            "graph_id",
            "instruction",
            "isolated_environment_verified",
            "semantic_rom_golden_exact",
            "status",
            "task_id",
            "test",
            "turn_count",
            "turns",
            "withheld_task_tests_passed",
        },
        set(),
        f"agent campaign record {expected_task['id']}",
    )
    _validate_artifact(value["artifact"], "agent child artifact")
    for field in ("agent_execution_id", "build_id", "graph_id"):
        require_sha256(value[field], f"agent campaign.{field}")
    expected = expected_task["expected"]
    expected_test = {
        "exit_code": expected["test_exit_code"],
        "stderr": expected["rom_test_stderr"],
        "stdout": expected["rom_test_stdout"],
    }
    turns = value["turns"]
    if not isinstance(turns, list) or len(turns) != len(expected["turns"]):
        raise QwenNaturalAgentCampaignError("agent turn coverage differs")
    for turn, expected_turn in zip(turns, expected["turns"], strict=True):
        _validate_agent_turn_summary(turn, expected_turn, expected_task["id"])
    if (
        value["task_id"] != expected_task["id"]
        or value["instruction"] != expected_task["source"]["instruction"]
        or value["docker_image_id"] != expected["rom_image_id"]
        or value["actions"] != expected["commands"]
        or value["final_answer"] != expected["final_answer"]
        or value["test"] != expected_test
        or value["turn_count"] != len(turns)
        or value["command_count"] != len(expected["commands"])
        or value["environment_actions_model_generated"] is not True
        or value["isolated_environment_verified"] is not True
        or value["semantic_rom_golden_exact"] is not True
        or value["withheld_task_tests_passed"] is not True
        or value["status"] != "pass"
    ):
        raise QwenNaturalAgentCampaignError(
            f"agent campaign result differs for {expected_task['id']}"
        )
    return value


def validate_natural_agent_campaign(
    value: Mapping[str, Any], workload_value: Mapping[str, Any]
) -> dict[str, Any]:
    """Independently reconstruct the campaign scope, totals, and exact goldens."""

    try:
        workload = validate_shared_workload(workload_value)
    except QwenWorkloadError as exc:
        raise QwenNaturalAgentCampaignError(
            f"campaign workload differs: {exc}"
        ) from exc
    campaign = dict(value)
    exact_keys(
        campaign,
        {
            "agent_executions",
            "build_id",
            "campaign_id",
            "campaign_version",
            "claim_boundary",
            "graph_id",
            "model_id",
            "natural_executions",
            "schema",
            "scope",
            "source_binding",
            "status",
            "totals",
            "workload_id",
        },
        set(),
        "Qwen natural and agent campaign",
    )
    _identity(campaign, "campaign_id", "Qwen natural and agent campaign")
    for field in ("build_id", "graph_id", "workload_id"):
        require_sha256(campaign[field], f"Qwen campaign.{field}")
    natural_values = campaign["natural_executions"]
    agent_values = campaign["agent_executions"]
    if (
        not isinstance(natural_values, list)
        or len(natural_values) != len(NATURAL_QUESTION_IDS)
        or not isinstance(agent_values, list)
        or len(agent_values) != len(AGENT_TASK_IDS)
    ):
        raise QwenNaturalAgentCampaignError("campaign coverage differs")
    natural = [
        _validate_natural_summary(observed, expected)
        for observed, expected in zip(
            natural_values,
            workload["natural_questions"],
            strict=True,
        )
    ]
    agent = [
        _validate_agent_summary(observed, expected)
        for observed, expected in zip(
            agent_values,
            workload["agent"]["tasks"],
            strict=True,
        )
    ]
    _validate_unique_children(natural, agent)
    expected_source = {
        "bash_tool_sha256": workload["agent"]["bash_tool_sha256"],
        "checkpoint_lock_id": workload["model"]["checkpoint_lock_id"],
        "model_revision": workload["model"]["revision"],
        "official_chat_template_sha256": workload["official_chat_template_sha256"],
        "rom_agent_campaign_id": workload["agent"]["rom_campaign_id"],
        "rom_agent_suite_id": workload["agent"]["rom_suite_id"],
        "terminalbench_commit": workload["agent"]["terminalbench_commit"],
    }
    expected_scope = {
        "agent_command_count": sum(item["command_count"] for item in agent),
        "agent_task_count": len(agent),
        "agent_turn_count": sum(item["turn_count"] for item in agent),
        "natural_case_count": len(natural),
    }
    child_build_ids = (
        {item["build_id"] for item in natural}
        | {item["build_id"] for item in agent}
        | {turn["build_id"] for item in agent for turn in item["turns"]}
    )
    child_graph_ids = (
        {item["graph_id"] for item in natural}
        | {item["graph_id"] for item in agent}
        | {turn["graph_id"] for item in agent for turn in item["turns"]}
    )
    if (
        campaign["schema"] != SCHEMA
        or campaign["campaign_version"] != VERSION
        or campaign["model_id"] != workload["model"]["id"]
        or campaign["workload_id"] != workload["workload_id"]
        or child_build_ids != {campaign["build_id"]}
        or child_graph_ids != {campaign["graph_id"]}
        or campaign["source_binding"] != expected_source
        or campaign["scope"] != expected_scope
        or campaign["claim_boundary"] != _claim_boundary()
        or campaign["totals"] != _totals(natural, agent)
        or campaign["status"] != "pass"
    ):
        raise QwenNaturalAgentCampaignError("campaign boundary differs")
    return campaign


def publish_natural_agent_campaign(
    value: Mapping[str, Any], workload: Mapping[str, Any], output: Path
) -> None:
    campaign = validate_natural_agent_campaign(value, workload)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(campaign))
    except FileExistsError as exc:
        raise QwenNaturalAgentCampaignError(
            f"natural and agent campaign already exists: {output}"
        ) from exc
    except OSError as exc:
        raise QwenNaturalAgentCampaignError(
            f"cannot publish natural and agent campaign: {exc}"
        ) from exc


__all__ = [
    "QwenNaturalAgentCampaignError",
    "SCHEMA",
    "VERSION",
    "build_natural_agent_campaign",
    "publish_natural_agent_campaign",
    "validate_natural_agent_campaign",
]
