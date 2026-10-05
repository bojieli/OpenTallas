#!/usr/bin/env python3
"""Import the committed ROM Qwen natural and agentic goldens immutably."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    publish_bytes_atomic_no_replace,
    sha256_bytes,
    sha256_file,
)
from compiler.tensor_accelerator.qwen_agent_protocol import (  # noqa: E402
    BASH_TOOL,
    BASH_TOOL_SHA256,
    SYSTEM_PROMPT,
    assistant_message,
    parse_assistant_output,
    tool_response,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    MODEL_VOCABULARY_SIZE,
    OFFICIAL_CHAT_TEMPLATE_SHA256,
    QwenChatError,
    QwenChatTokenizer,
    SOURCE_REVISION,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    EXPECTED_ROM_FILES,
    SCHEMA,
    VERSION,
    validate_shared_workload,
)


SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_shared_workload_v1.schema.json"
)
class WorkloadImportError(ArtifactError):
    """Raised when ROM goldens or their local reproduction differ."""


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Authenticate committed ROM natural/agentic evidence, reproduce every "
            "official-template prompt, and publish one backend-neutral workload"
        )
    )
    result.add_argument("--rom-root", required=True, type=Path)
    result.add_argument("--snapshot", required=True, type=Path)
    result.add_argument("--checkpoint-lock", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _body_id(value: dict[str, Any], identity: str) -> str:
    return sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != identity})
    )


def _load_json(
    path: Path, label: str, *, require_canonical: bool = False
) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise WorkloadImportError(f"cannot load {label}: {exc}") from exc
    if require_canonical and payload != canonical_json_bytes(value):
        raise WorkloadImportError(f"{label} is not canonical JSON")
    return value


def _git(*arguments: str, root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise WorkloadImportError(f"cannot authenticate ROM Git state: {exc}") from exc
    if result.returncode != 0:
        raise WorkloadImportError(
            f"ROM Git authentication failed: {(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


def _source_inventory(rom_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for role, expected in sorted(EXPECTED_ROM_FILES.items()):
        path = rom_root / expected["path"]
        try:
            digest, size = sha256_file(path)
        except OSError as exc:
            raise WorkloadImportError(f"cannot authenticate ROM {role}: {exc}") from exc
        commit = _git("log", "-1", "--format=%H", "--", expected["path"], root=rom_root)
        unstaged = _git("diff", "--name-only", "--", expected["path"], root=rom_root)
        staged = _git(
            "diff", "--cached", "--name-only", "--", expected["path"], root=rom_root
        )
        if (
            digest != expected["sha256"]
            or commit != expected["commit"]
            or unstaged
            or staged
            or size < 1
        ):
            raise WorkloadImportError(f"ROM source {role!r} differs")
        records.append(
            {
                "commit": commit,
                "path": expected["path"],
                "role": role,
                "sha256": digest,
                "size_bytes": size,
            }
        )
    return records


def _natural_questions(
    rom_root: Path,
    chat: QwenChatTokenizer,
    suite: dict[str, Any],
    campaign: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        suite.get("schema") != "opentallas.qwen3.eos_question_suite.v1"
        or suite.get("suite_id") != _body_id(suite, "suite_id")
        or campaign.get("schema") != "opentallas.qwen3.eos_campaign.v1"
        or campaign.get("report_id") != _body_id(campaign, "report_id")
        or campaign.get("suite_id") != suite["suite_id"]
        or campaign.get("status") != "pass"
        or campaign.get("all_reached_eos") is not True
    ):
        raise WorkloadImportError("ROM natural question suite or campaign differs")
    summaries = {record["id"]: record for record in campaign["questions"]}
    if set(summaries) != {record["id"] for record in suite["questions"]}:
        raise WorkloadImportError("ROM natural question coverage differs")
    result: list[dict[str, Any]] = []
    for question in suite["questions"]:
        identifier = question["id"]
        summary = summaries[identifier]
        generation_path = rom_root / "results/compiler/qwen3-8b/eos-campaign" / summary[
            "result_path"
        ]
        generation = _load_json(
            generation_path,
            f"ROM natural result {identifier}",
            require_canonical=True,
        )
        prompt = chat.prompt_record(
            question["messages"], enable_thinking=question["enable_thinking"]
        )
        generated_ids = generation["generated_token_ids"]
        raw_text = chat.decode(generated_ids, skip_special_tokens=False)
        visible_text = chat.decode(generated_ids, skip_special_tokens=True)
        if (
            generation.get("result_id") != _body_id(generation, "result_id")
            or generation.get("result_id") != summary["result_id"]
            or prompt["prompt_token_count"] != summary["prompt_token_count"]
            or prompt["prompt_token_sha256"] != summary["prompt_token_sha256"]
            or generation.get("prompt_token_count") != prompt["prompt_token_count"]
            or generation.get("termination") != "eos"
            or not isinstance(generated_ids, list)
            or not generated_ids
            or generated_ids[-1] not in EOS_TOKEN_IDS
            or any(token in EOS_TOKEN_IDS for token in generated_ids[:-1])
            or raw_text != generation.get("generated_text")
            or generation.get("context_tokens_committed")
            != prompt["prompt_token_count"] + len(generated_ids) - 1
            or len(generation.get("spans", [])) != len(generated_ids)
        ):
            raise WorkloadImportError(f"ROM natural result {identifier!r} differs")
        result.append(
            {
                "enable_thinking": question["enable_thinking"],
                "expected": {
                    "context_tokens_committed": generation[
                        "context_tokens_committed"
                    ],
                    "eos_token_id": generated_ids[-1],
                    "generated_text_raw": raw_text,
                    "generated_text_visible": visible_text,
                    "generated_token_count": len(generated_ids),
                    "generated_token_ids": generated_ids,
                    "rom_logits_sha256": [
                        span["logits"]["sha256"] for span in generation["spans"]
                    ],
                    "rom_result_id": generation["result_id"],
                    "termination": "eos",
                },
                "id": identifier,
                "messages": question["messages"],
                "prompt": prompt,
            }
        )
    return result


def _agent_tasks(
    chat: QwenChatTokenizer,
    suite: dict[str, Any],
    campaign: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        suite.get("schema") != "opentallas.qwen3.terminalbench_task_suite.v1"
        or suite.get("suite_id") != _body_id(suite, "suite_id")
        or campaign.get("schema")
        != "opentallas.qwen3.terminalbench_agent_campaign.v1"
        or campaign.get("campaign_id") != _body_id(campaign, "campaign_id")
        or campaign.get("suite_id") != suite["suite_id"]
        or campaign.get("status") != "pass"
        or campaign.get("all_tasks_passed") is not True
        or campaign.get("official_chat_template_sha256")
        != OFFICIAL_CHAT_TEMPLATE_SHA256
        or campaign.get("bash_tool_schema_sha256") != BASH_TOOL_SHA256
        or campaign.get("terminalbench_commit") != suite["terminalbench_commit"]
    ):
        raise WorkloadImportError("ROM agent suite or campaign differs")
    source_tasks = {record["id"]: record for record in suite["tasks"]}
    golden_tasks = {record["id"]: record for record in campaign["tasks"]}
    if set(source_tasks) != set(golden_tasks):
        raise WorkloadImportError("ROM agent task coverage differs")

    result: list[dict[str, Any]] = []
    for identifier in [record["id"] for record in suite["tasks"]]:
        source = source_tasks[identifier]
        golden = golden_tasks[identifier]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": source["instruction"]},
        ]
        transcript = golden["transcript"]
        expected_initial = [
            {"content": SYSTEM_PROMPT, "role": "system", "type": "message"},
            {
                "content": source["instruction"],
                "role": "user",
                "type": "message",
            },
        ]
        if transcript[:2] != expected_initial:
            raise WorkloadImportError(f"ROM agent task {identifier!r} opening differs")
        turns: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        pending_action: dict[str, Any] | None = None
        for entry in transcript[2:]:
            entry_type = entry.get("type")
            if entry_type == "assistant_generation":
                prompt = chat.prompt_record(
                    messages,
                    tools=[BASH_TOOL],
                    enable_thinking=suite["enable_thinking"],
                )
                generated_ids = entry["generated_token_ids"]
                generated_text = chat.decode(
                    generated_ids, skip_special_tokens=False
                )
                parsed = parse_assistant_output(generated_text)
                if (
                    prompt["prompt_token_count"] != entry["prompt_token_count"]
                    or prompt["prompt_token_sha256"]
                    != entry["prompt_token_sha256"]
                    or generated_text != entry["generated_text"]
                    or entry["generated_token_count"] != len(generated_ids)
                    or entry["termination"] != "eos"
                    or generated_ids[-1] not in EOS_TOKEN_IDS
                    or any(token in EOS_TOKEN_IDS for token in generated_ids[:-1])
                ):
                    raise WorkloadImportError(
                        f"ROM agent task {identifier!r} turn differs"
                    )
                turns.append(
                    {
                        "expected": {
                            "calls": list(parsed.calls),
                            "content": parsed.content,
                            "generated_text_raw": generated_text,
                            "generated_text_visible": chat.decode(
                                generated_ids, skip_special_tokens=True
                            ),
                            "generated_token_count": len(generated_ids),
                            "generated_token_ids": generated_ids,
                            "reasoning": parsed.reasoning,
                            "rom_result_id": entry["result_id"],
                            "termination": "eos",
                        },
                        "prompt": prompt,
                        "turn": entry["turn"],
                    }
                )
                messages.append(assistant_message(parsed))
            elif entry_type == "bash_action":
                public_action = {
                    key: entry[key]
                    for key in (
                        "call_index",
                        "command",
                        "exit_code",
                        "stderr",
                        "stdout",
                        "timed_out",
                        "truncated",
                        "turn",
                        "type",
                    )
                }
                actions.append(public_action)
                pending_action = public_action
            elif entry_type == "message" and entry.get("role") == "tool":
                if (
                    pending_action is None
                    or entry.get("content") != tool_response(pending_action)
                ):
                    raise WorkloadImportError(
                        f"ROM agent task {identifier!r} tool response differs"
                    )
                messages.append({"role": "tool", "content": entry["content"]})
                pending_action = None
            else:
                raise WorkloadImportError(
                    f"ROM agent task {identifier!r} has unexpected transcript entry"
                )
        if (
            pending_action is not None
            or golden.get("passed") is not True
            or golden.get("agent_termination") != "eos"
            or golden.get("test_exit_code") != 0
            or golden.get("turn_count") != len(turns)
            or golden.get("command_count") != len(actions)
            or golden.get("model_generated_tokens")
            != sum(turn["expected"]["generated_token_count"] for turn in turns)
            or turns[-1]["expected"]["calls"]
            or turns[-1]["expected"]["content"] != golden.get("final_answer")
        ):
            raise WorkloadImportError(f"ROM agent task {identifier!r} result differs")
        result.append(
            {
                "expected": {
                    "agent_termination": "eos",
                    "commands": actions,
                    "final_answer": golden["final_answer"],
                    "rom_image_id": golden["image_id"],
                    "rom_test_stderr": golden["test_stderr"],
                    "rom_test_stdout": golden["test_stdout"],
                    "test_exit_code": 0,
                    "turns": turns,
                },
                "id": identifier,
                "source": source,
            }
        )
    return result


def main() -> int:
    arguments = parser().parse_args()
    rom_root = arguments.rom_root.resolve()
    try:
        inventory = _source_inventory(rom_root)
        checkpoint_lock = _load_json(
            arguments.checkpoint_lock.resolve(),
            "Qwen checkpoint lock",
            require_canonical=True,
        )
        chat = QwenChatTokenizer(arguments.snapshot, checkpoint_lock)
        eos_suite = _load_json(
            rom_root / EXPECTED_ROM_FILES["eos_suite"]["path"], "ROM EOS suite"
        )
        eos_campaign = _load_json(
            rom_root / EXPECTED_ROM_FILES["eos_campaign"]["path"],
            "ROM EOS campaign",
        )
        agent_suite = _load_json(
            rom_root / EXPECTED_ROM_FILES["agent_suite"]["path"],
            "ROM agent suite",
        )
        agent_campaign = _load_json(
            rom_root / EXPECTED_ROM_FILES["agent_campaign"]["path"],
            "ROM agent campaign",
        )
        body: dict[str, Any] = {
            "agent": {
                "bash_tool": BASH_TOOL,
                "bash_tool_sha256": BASH_TOOL_SHA256,
                "enable_thinking": agent_suite["enable_thinking"],
                "generation_mode": agent_suite["generation_mode"],
                "maximum_agent_turns": agent_suite["maximum_agent_turns"],
                "maximum_new_tokens_per_turn": agent_suite[
                    "maximum_new_tokens_per_turn"
                ],
                "rom_campaign_id": agent_campaign["campaign_id"],
                "rom_suite_id": agent_suite["suite_id"],
                "system_prompt": SYSTEM_PROMPT,
                "tasks": _agent_tasks(chat, agent_suite, agent_campaign),
                "terminalbench_commit": agent_suite["terminalbench_commit"],
            },
            "claim_boundary": {
                "accelerator_execution_proven": False,
                "agent_environment_replayed": False,
                "rom_goldens_imported": True,
                "semantic_goldens_frozen_before_accelerator_execution": True,
                "timing_or_performance": False,
            },
            "generation": {
                "eos_token_ids": list(EOS_TOKEN_IDS),
                "eos_token_included": True,
                "padded_output_rows": {
                    "end_exclusive": MODEL_VOCABULARY_SIZE,
                    "policy": "reject_if_selected",
                    "start": EXPLICIT_VOCABULARY_SIZE,
                },
                "selection": "greedy_lowest_token_id_argmax",
                "stop_rule": "first_eos_or_maximum_generated_token_count",
            },
            "model": {
                "checkpoint_lock_id": checkpoint_lock["lock_id"],
                "id": "qwen3-8b",
                "repository": "Qwen/Qwen3-8B",
                "revision": SOURCE_REVISION,
                "source_files": chat.source_records,
            },
            "natural_questions": _natural_questions(
                rom_root, chat, eos_suite, eos_campaign
            ),
            "official_chat_template_sha256": OFFICIAL_CHAT_TEMPLATE_SHA256,
            "rom_source_inventory": inventory,
            "schema": SCHEMA,
            "workload_version": VERSION,
        }
        manifest = {**body, "workload_id": sha256_bytes(canonical_json_bytes(body))}
        validate_shared_workload(manifest, chat=chat)
        schema = load_strict_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(manifest)
        publish_bytes_atomic_no_replace(
            arguments.output, canonical_json_bytes(manifest)
        )
    except (
        OSError,
        QwenChatError,
        ValidationError,
        WorkloadImportError,
    ) as exc:
        parser().error(str(exc))
    print(f"workload_id={manifest['workload_id']}")
    print(f"natural_question_count={len(manifest['natural_questions'])}")
    print(f"agent_task_count={len(manifest['agent']['tasks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
