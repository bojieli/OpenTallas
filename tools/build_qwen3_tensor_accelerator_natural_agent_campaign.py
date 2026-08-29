#!/usr/bin/env python3
"""Aggregate the complete Qwen natural and live-agent accelerator campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
)
from compiler.tensor_accelerator.qwen_agent_execution import (  # noqa: E402
    QwenAgentExecutionError,
    validate_agent_task_execution,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    QwenChatError,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_dynamic_control import (  # noqa: E402
    QwenDynamicControlError,
    validate_controlled_dynamic_execution,
    validate_dynamic_generation_control,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    validate_dynamic_session,
)
from compiler.tensor_accelerator.qwen_natural_agent_campaign import (  # noqa: E402
    QwenNaturalAgentCampaignError,
    build_natural_agent_campaign,
    publish_natural_agent_campaign,
    validate_natural_agent_campaign,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    AGENT_TASK_IDS,
    NATURAL_QUESTION_IDS,
    QwenWorkloadError,
    load_shared_workload,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DEFAULT_WORKLOAD = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
DEFAULT_RUNS_ROOT = ROOT / "runs/tensor_accelerator"
CAMPAIGN_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_natural_agent_campaign_v1.schema.json"
)


class CampaignBuilderError(ArtifactError):
    """Raised when retained child evidence cannot form one campaign."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise CampaignBuilderError(f"{label} is missing or unsafe: {path}")
        value = load_strict_json(path)
        if path.read_bytes() != canonical_json_bytes(value):
            raise CampaignBuilderError(f"{label} is not canonical JSON: {path}")
    except OSError as exc:
        raise CampaignBuilderError(f"cannot authenticate {label}: {exc}") from exc
    return value


def _controlled_execution(
    root: Path,
    workload: dict[str, Any],
    chat: QwenChatTokenizer,
) -> dict[str, Any]:
    session = validate_dynamic_session(
        _load_canonical(root / "session.json", "session")
    )
    control = validate_dynamic_generation_control(
        _load_canonical(root / "control.json", "generation control"),
        session,
        workload,
    )
    return validate_controlled_dynamic_execution(
        _load_canonical(root / "controlled_execution.json", "controlled execution"),
        control,
        session,
        workload,
        chat=chat,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and aggregate all six official-template natural cases and "
            "both live isolated agent tasks. The command fails until every child "
            "artifact exists and passes exactly."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        checkpoint_lock = _load_canonical(
            arguments.deployment / "source/checkpoint.lock.json",
            "checkpoint lock",
        )
        chat = QwenChatTokenizer(arguments.snapshot, checkpoint_lock)
        workload = load_shared_workload(arguments.workload, chat=chat)
        runs_root = arguments.runs_root.resolve()
        natural_executions: dict[str, dict[str, Any]] = {}
        for case_id in NATURAL_QUESTION_IDS:
            natural_executions[case_id] = _controlled_execution(
                runs_root / f"qwen3_natural_{case_id}_controlled_v1",
                workload,
                chat,
            )
        agent_executions: dict[str, dict[str, Any]] = {}
        agent_turn_executions: dict[str, list[dict[str, Any]]] = {}
        for task_id in AGENT_TASK_IDS:
            task_root = runs_root / f"qwen3_agent_{task_id}_controlled_v1"
            agent_execution = validate_agent_task_execution(
                _load_canonical(
                    task_root / "agent_execution.json", "agent task execution"
                ),
                workload,
            )
            agent_executions[task_id] = agent_execution
            agent_turn_executions[task_id] = [
                _controlled_execution(
                    task_root / "turns" / f"turn.{turn:04d}",
                    workload,
                    chat,
                )
                for turn in range(1, agent_execution["turn_count"] + 1)
            ]
        campaign = build_natural_agent_campaign(
            workload,
            natural_executions=natural_executions,
            agent_executions=agent_executions,
            agent_turn_executions=agent_turn_executions,
        )
        schema = load_strict_json(CAMPAIGN_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(campaign)
        output = arguments.output.resolve()
        if output.exists():
            retained = validate_natural_agent_campaign(
                _load_canonical(output, "retained campaign"), workload
            )
            if retained != campaign:
                raise CampaignBuilderError(
                    "retained natural and agent campaign differs"
                )
        else:
            publish_natural_agent_campaign(campaign, workload, output)
    except (
        ArtifactError,
        OSError,
        QwenAgentExecutionError,
        QwenChatError,
        QwenDynamicArtifactError,
        QwenDynamicControlError,
        QwenNaturalAgentCampaignError,
        QwenWorkloadError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))

    print(f"status={campaign['status']}")
    print(f"campaign_id={campaign['campaign_id']}")
    print(f"workload_id={campaign['workload_id']}")
    print(f"natural_cases={campaign['scope']['natural_case_count']}")
    print(f"agent_tasks={campaign['scope']['agent_task_count']}")
    print(f"agent_turns={campaign['scope']['agent_turn_count']}")
    print(f"model_transactions={campaign['totals']['model_transaction_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
