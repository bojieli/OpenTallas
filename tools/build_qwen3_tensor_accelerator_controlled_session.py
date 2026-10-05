#!/usr/bin/env python3
"""Compile one frozen natural or agent-turn workload into a controlled session."""

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
    load_strict_json,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    QwenChatError,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_dynamic_control import (  # noqa: E402
    QwenDynamicControlError,
    build_dynamic_generation_control,
    publish_dynamic_generation_control,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    build_dynamic_session,
    publish_dynamic_session,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    QwenWorkloadError,
    load_shared_workload,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DEFAULT_WORKLOAD = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
SESSION_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_dynamic_session_v1.schema.json"
)
CONTROL_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_dynamic_generation_control_v1.schema.json"
)


def _case(
    workload: dict[str, Any], kind: str, case_id: str, turn: int | None
) -> dict[str, Any]:
    if kind == "natural_question" and turn is None:
        matches = [
            record for record in workload["natural_questions"] if record["id"] == case_id
        ]
        if len(matches) == 1:
            return matches[0]["prompt"]
    elif kind == "agent_turn" and turn is not None:
        tasks = [record for record in workload["agent"]["tasks"] if record["id"] == case_id]
        if len(tasks) == 1:
            matches = [
                record
                for record in tasks[0]["expected"]["turns"]
                if record["turn"] == turn
            ]
            if len(matches) == 1:
                return matches[0]["prompt"]
    raise QwenDynamicControlError("requested controlled workload case differs")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate the shared ROM/tensor-accelerator workload and official "
            "Qwen chat boundary, then compile exactly one natural question or "
            "agent turn into an immutable dynamic session plus first-EOS control. "
            "This compiles artifacts and does not execute the model."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument(
        "--kind", required=True, choices=("natural_question", "agent_turn")
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--turn", type=int)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if (arguments.kind == "natural_question") != (arguments.turn is None):
        parser.error("--turn is required only for --kind agent_turn")
    session_path = arguments.output / "session.json"
    control_path = arguments.output / "control.json"

    try:
        checkpoint_lock_path = arguments.deployment / "source/checkpoint.lock.json"
        checkpoint_lock = load_strict_json(checkpoint_lock_path)
        chat = QwenChatTokenizer(arguments.snapshot, checkpoint_lock)
        workload = load_shared_workload(arguments.workload, chat=chat)
        prompt = _case(workload, arguments.kind, arguments.case_id, arguments.turn)
        generated_limit = (
            8000 - prompt["prompt_token_count"] + 1
            if arguments.kind == "natural_question"
            else min(
                workload["agent"]["maximum_new_tokens_per_turn"],
                8000 - prompt["prompt_token_count"] + 1,
            )
        )
        session = build_dynamic_session(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=checkpoint_lock_path,
            model_graph_path=arguments.deployment / "source/model_graph.v2.json",
            deployment_manifest_path=arguments.deployment / "deployment_manifest.json",
            physical_plan_path=arguments.deployment / "physical/physical_plan.json",
            prompt_text=prompt["prompt_text"],
            generated_token_limit=generated_limit,
        )
        control = build_dynamic_generation_control(
            session,
            workload,
            kind=arguments.kind,
            case_id=arguments.case_id,
            turn=arguments.turn,
        )
        for value, path in ((session, SESSION_SCHEMA), (control, CONTROL_SCHEMA)):
            schema = load_strict_json(path)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
        publish_dynamic_session(session, session_path)
        publish_dynamic_generation_control(
            control, session, workload, control_path
        )
    except (
        ArtifactError,
        OSError,
        QwenChatError,
        QwenDynamicArtifactError,
        QwenDynamicControlError,
        QwenWorkloadError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))

    print(f"session_id={session['session_id']}")
    print(f"control_id={control['control_id']}")
    print(f"workload_id={workload['workload_id']}")
    print(f"kind={arguments.kind}")
    print(f"case_id={arguments.case_id}")
    print(f"turn={arguments.turn}")
    print(f"prompt_token_count={session['prompt']['token_count']}")
    print(f"generated_token_limit={session['generation']['generated_token_limit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
