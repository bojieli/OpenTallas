from __future__ import annotations

import copy
import hashlib
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
    build_agent_task_execution,
)
from compiler.tensor_accelerator.qwen_natural_agent_campaign import (
    QwenNaturalAgentCampaignError,
    build_natural_agent_campaign,
    publish_natural_agent_campaign,
    validate_natural_agent_campaign,
)
from compiler.tensor_accelerator.qwen_workload import (
    AGENT_TASK_IDS,
    NATURAL_QUESTION_IDS,
    validate_shared_workload,
)


ROOT = Path(__file__).resolve().parents[2]
WORKLOAD_PATH = ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_natural_agent_campaign_v1.schema.json"
)
BUILD_ID = "d" * 64
GRAPH_ID = "e" * 64
ISOLATION = {
    "cap_drop_all": True,
    "host_mounts": False,
    "network": "none",
    "no_new_privileges": True,
    "pids_limit": 128,
    "privileged": False,
    "read_only_rootfs": False,
}


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _controlled(
    workload: dict[str, Any],
    *,
    label: str,
    kind: str,
    case_id: str,
    turn: int | None,
    prompt: dict[str, Any],
    expected: dict[str, Any],
    base_session_id: str | None = None,
    control_id: str | None = None,
    controlled_execution_id: str | None = None,
) -> dict[str, Any]:
    generated = expected["generated_token_ids"]
    return {
        "base_session_id": base_session_id or _digest(f"session-{label}"),
        "build_id": BUILD_ID,
        "claim_boundary": {
            "artifact_only_dynamic_session_executed": True,
            "semantic_rom_golden_exact": True,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
            "token_legitimacy_verified": True,
        },
        "comparison": {
            "exact_eos": True,
            "exact_generated_text_raw": True,
            "exact_generated_text_visible": True,
            "exact_generated_token_ids": True,
            "first_token_divergence_index": None,
            "rom_result_id": expected["rom_result_id"],
            "status": "exact_match",
        },
        "control_id": control_id or _digest(f"control-{label}"),
        "controlled_execution_id": controlled_execution_id
        or _digest(f"execution-{label}"),
        "decode_transaction_count": len(generated) - 1,
        "decoded": {
            "full_text_raw": prompt["prompt_text"] + expected["generated_text_raw"],
            "full_text_visible": expected["generated_text_visible"],
            "generated_text_raw": expected["generated_text_raw"],
            "generated_text_visible": expected["generated_text_visible"],
            "prompt_text_raw": prompt["prompt_text"],
            "prompt_text_visible": prompt["prompt_text"],
        },
        "eos_observed": True,
        "generated_token_count": len(generated),
        "generated_token_ids": generated,
        "graph_id": GRAPH_ID,
        "prompt_token_count": prompt["prompt_token_count"],
        "prompt_token_ids": prompt["prompt_token_ids"],
        "schema": (
            "opentallas.tensor_accelerator.qwen_controlled_dynamic_session_execution.v1"
        ),
        "status": "pass",
        "stop_reason": "eos",
        "token_legitimacy": {
            "all_generated_token_ids_resolve": True,
            "all_generated_token_ids_within_explicit_vocabulary": True,
            "padded_model_rows_rejected": True,
        },
        "transaction_count": prompt["prompt_token_count"] + len(generated) - 1,
        "workload_binding": {
            "case_id": case_id,
            "kind": kind,
            "prompt_token_count": prompt["prompt_token_count"],
            "prompt_token_sha256": prompt["prompt_token_sha256"],
            "turn": turn,
        },
        "workload_id": workload["workload_id"],
    }


def _agent_report_turns(task: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for expected_turn in task["expected"]["turns"]:
        turn = expected_turn["turn"]
        expected = expected_turn["expected"]
        label = f"{task['id']}-{turn}"
        result.append(
            {
                "base_session_id": _digest(f"session-{label}"),
                "content": expected["content"],
                "control_id": _digest(f"control-{label}"),
                "controlled_execution_id": _digest(f"execution-{label}"),
                "generated_text_raw": expected["generated_text_raw"],
                "generated_text_visible": expected["generated_text_visible"],
                "generated_token_count": expected["generated_token_count"],
                "generated_token_ids": expected["generated_token_ids"],
                "parsed_calls": expected["calls"],
                "prompt_token_count": expected_turn["prompt"]["prompt_token_count"],
                "prompt_token_sha256": expected_turn["prompt"]["prompt_token_sha256"],
                "reasoning": expected["reasoning"],
                "status": "pass",
                "stop_reason": "eos",
                "turn": turn,
            }
        )
    return result


def _evidence() -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
    workload = validate_shared_workload(load_strict_json(WORKLOAD_PATH))
    natural: dict[str, dict[str, Any]] = {}
    for case in workload["natural_questions"]:
        natural[case["id"]] = _controlled(
            workload,
            label=case["id"],
            kind="natural_question",
            case_id=case["id"],
            turn=None,
            prompt=case["prompt"],
            expected=case["expected"],
        )
    agents: dict[str, dict[str, Any]] = {}
    agent_turns: dict[str, list[dict[str, Any]]] = {}
    for task in workload["agent"]["tasks"]:
        report_turns = _agent_report_turns(task)
        expected = task["expected"]
        agents[task["id"]] = build_agent_task_execution(
            workload,
            task_id=task["id"],
            build_id=BUILD_ID,
            graph_id=GRAPH_ID,
            docker_version="28.5.2",
            image_id=expected["rom_image_id"],
            image_tag=("opentallas-qwen3-tbench:d28711d0da26-" + task["id"]),
            isolation=ISOLATION,
            turns=report_turns,
            actions=expected["commands"],
            final_answer=expected["final_answer"],
            test_exit_code=expected["test_exit_code"],
            test_stdout=expected["rom_test_stdout"],
            test_stderr=expected["rom_test_stderr"],
        )
        agent_turns[task["id"]] = [
            _controlled(
                workload,
                label=f"{task['id']}-{expected_turn['turn']}",
                kind="agent_turn",
                case_id=task["id"],
                turn=expected_turn["turn"],
                prompt=expected_turn["prompt"],
                expected=expected_turn["expected"],
                base_session_id=report_turn["base_session_id"],
                control_id=report_turn["control_id"],
                controlled_execution_id=report_turn["controlled_execution_id"],
            )
            for expected_turn, report_turn in zip(
                task["expected"]["turns"], report_turns, strict=True
            )
        ]
    assert tuple(natural) == NATURAL_QUESTION_IDS
    assert tuple(agents) == AGENT_TASK_IDS
    assert tuple(agent_turns) == AGENT_TASK_IDS
    return workload, natural, agents, agent_turns


def test_campaign_covers_exact_natural_and_live_agent_evidence() -> None:
    workload, natural, agents, agent_turns = _evidence()
    campaign = build_natural_agent_campaign(
        workload,
        natural_executions=natural,
        agent_executions=agents,
        agent_turn_executions=agent_turns,
    )

    assert campaign["status"] == "pass"
    assert campaign["scope"] == {
        "agent_command_count": 3,
        "agent_task_count": 2,
        "agent_turn_count": 5,
        "natural_case_count": 6,
    }
    assert campaign["totals"] == {
        "agent_decode_transaction_count": 151,
        "agent_generated_token_count": 156,
        "agent_prompt_token_count": 1492,
        "agent_transaction_count": 1643,
        "generated_token_count": 1529,
        "model_transaction_count": 3182,
        "natural_decode_transaction_count": 1367,
        "natural_generated_token_count": 1373,
        "natural_prompt_token_count": 172,
        "natural_transaction_count": 1539,
    }
    assert validate_natural_agent_campaign(campaign, workload) == campaign
    schema = load_strict_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)


def test_campaign_rejects_reordered_coverage_and_forged_semantics() -> None:
    workload, natural, agents, agent_turns = _evidence()
    reordered = dict(reversed(tuple(natural.items())))
    with pytest.raises(
        QwenNaturalAgentCampaignError, match="coverage or ordering differs"
    ):
        build_natural_agent_campaign(
            workload,
            natural_executions=reordered,
            agent_executions=agents,
            agent_turn_executions=agent_turns,
        )

    campaign = build_natural_agent_campaign(
        workload,
        natural_executions=natural,
        agent_executions=agents,
        agent_turn_executions=agent_turns,
    )
    forged = copy.deepcopy(campaign)
    forged["natural_executions"][0]["generation"]["generated_text_visible"] = (
        "random output"
    )
    forged = _reidentify(forged, "campaign_id")
    with pytest.raises(QwenNaturalAgentCampaignError, match="result differs"):
        validate_natural_agent_campaign(forged, workload)


def test_campaign_rejects_noncausal_agent_turn_and_duplicate_child() -> None:
    workload, natural, agents, agent_turns = _evidence()
    noncausal = copy.deepcopy(agent_turns)
    noncausal["hello-world"][0]["controlled_execution_id"] = "f" * 64
    with pytest.raises(QwenNaturalAgentCampaignError, match="report and controlled"):
        build_natural_agent_campaign(
            workload,
            natural_executions=natural,
            agent_executions=agents,
            agent_turn_executions=noncausal,
        )

    duplicate = copy.deepcopy(natural)
    duplicate["geography"]["controlled_execution_id"] = natural["arithmetic"][
        "controlled_execution_id"
    ]
    duplicate["geography"]["base_session_id"] = natural["arithmetic"]["base_session_id"]
    duplicate["geography"]["control_id"] = natural["arithmetic"]["control_id"]
    with pytest.raises(QwenNaturalAgentCampaignError, match="not unique"):
        build_natural_agent_campaign(
            workload,
            natural_executions=duplicate,
            agent_executions=agents,
            agent_turn_executions=agent_turns,
        )


def test_campaign_publication_is_canonical_and_no_replace(tmp_path: Path) -> None:
    workload, natural, agents, agent_turns = _evidence()
    campaign = build_natural_agent_campaign(
        workload,
        natural_executions=natural,
        agent_executions=agents,
        agent_turn_executions=agent_turns,
    )
    output = tmp_path / "campaign.json"
    publish_natural_agent_campaign(campaign, workload, output)
    assert output.read_bytes() == canonical_json_bytes(campaign)
    with pytest.raises(QwenNaturalAgentCampaignError, match="already exists"):
        publish_natural_agent_campaign(campaign, workload, output)
