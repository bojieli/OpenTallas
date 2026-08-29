"""Validation boundary for shared ROM and HBM/SRAM Qwen workloads."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    publish_bytes_atomic_no_replace,
    require_sha256,
    sha256_bytes,
)
from .qwen_agent_protocol import (
    BASH_TOOL,
    BASH_TOOL_SHA256,
    SYSTEM_PROMPT,
    assistant_message,
    parse_assistant_output,
    tool_response,
)
from .qwen_chat import (
    EOS_TOKEN_IDS,
    EXPLICIT_VOCABULARY_SIZE,
    MODEL_VOCABULARY_SIZE,
    OFFICIAL_CHAT_TEMPLATE_SHA256,
    QwenChatTokenizer,
    SOURCE_FILES,
    SOURCE_REVISION,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_shared_workload.v1"
VERSION = "tensor-accelerator-qwen-shared-workload-0.1.0"
NATURAL_QUESTION_IDS = (
    "arithmetic",
    "geography",
    "science",
    "computer_science",
    "practical_advice",
    "reasoning",
)
AGENT_TASK_IDS = ("hello-world", "fix-permissions")
EXPECTED_ROM_FILES = {
    "agent_campaign": {
        "commit": "8753d6ff1631543ccc379a5f8ee510f5ec8a0556",
        "path": "results/compiler/qwen3-8b/terminalbench-agent/campaign.json",
        "sha256": "00147a19e12a5b72a0b1c406ba81ed0114e94ca88528570fddb8d0aa9809c19c",
    },
    "agent_runner": {
        "commit": "8753d6ff1631543ccc379a5f8ee510f5ec8a0556",
        "path": "tools/run_qwen3_terminalbench.py",
        "sha256": "6987431258e04b9c2b16eae1154da8620efd37eab3af5cd694d3f72a0a749305",
    },
    "agent_suite": {
        "commit": "8753d6ff1631543ccc379a5f8ee510f5ec8a0556",
        "path": "testdata/compiler/qwen3_8b/terminalbench_tasks.json",
        "sha256": "d7d6ff43a2983ecb7551b84b531cc6420bfc3748808e62a8b16a0cad7a17f492",
    },
    "eos_campaign": {
        "commit": "3a985ffcecfd17fb8642cdef819c22e16d8e9f4c",
        "path": "results/compiler/qwen3-8b/eos-campaign/campaign.json",
        "sha256": "668bdc5bf5790e934eb170253df2170f5e7f8d29a11218a3b947bdaf517c0b1c",
    },
    "eos_suite": {
        "commit": "3a985ffcecfd17fb8642cdef819c22e16d8e9f4c",
        "path": "testdata/compiler/qwen3_8b/eos_questions.json",
        "sha256": "5e9ac173a7eb23cb8dca3e91dcc53050cc81a3b19d9e3f5ede6549ab06872424",
    },
    "tokenizer_boundary": {
        "commit": "247a11d42022846be4bff081bc37c4997ae68e3b",
        "path": "compiler/qwen3/tokenizer.py",
        "sha256": "e2a9e219c4547cbefe935e67a73f816a2517ec995bfe837d99df63313d994232",
    },
}


class QwenWorkloadError(ArtifactError):
    """Raised when a shared semantic workload is incomplete or forged."""


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenWorkloadError(f"{label} identity differs")


def _tokens(value: object, label: str, *, maximum_count: int) -> list[int]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= maximum_count
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < EXPLICIT_VOCABULARY_SIZE
            for token in value
        )
    ):
        raise QwenWorkloadError(f"{label} differs")
    return value


def _validate_prompt(
    value: object,
    label: str,
    *,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QwenWorkloadError(f"{label} must be an object")
    exact_keys(
        value,
        {
            "prompt_text",
            "prompt_text_utf8_sha256",
            "prompt_token_count",
            "prompt_token_ids",
            "prompt_token_sha256",
        },
        set(),
        label,
    )
    for field in ("prompt_text_utf8_sha256", "prompt_token_sha256"):
        require_sha256(value[field], f"{label}.{field}")
    tokens = _tokens(value["prompt_token_ids"], f"{label}.prompt_token_ids", maximum_count=8000)
    if (
        not isinstance(value["prompt_text"], str)
        or not value["prompt_text"]
        or value["prompt_token_count"] != len(tokens)
        or (expected is not None and value != expected)
    ):
        raise QwenWorkloadError(f"{label} boundary differs")
    return value


def _validate_natural(
    records: object, chat: QwenChatTokenizer | None
) -> list[dict[str, Any]]:
    if not isinstance(records, list) or tuple(
        record.get("id") if isinstance(record, dict) else None for record in records
    ) != NATURAL_QUESTION_IDS:
        raise QwenWorkloadError("natural question coverage or ordering differs")
    for record in records:
        exact_keys(
            record,
            {"enable_thinking", "expected", "id", "messages", "prompt"},
            set(),
            f"natural question {record['id']}",
        )
        if not isinstance(record["enable_thinking"], bool):
            raise QwenWorkloadError("natural thinking mode differs")
        prompt_expected = None
        if chat is not None:
            prompt_expected = chat.prompt_record(
                record["messages"], enable_thinking=record["enable_thinking"]
            )
        prompt = _validate_prompt(
            record["prompt"],
            f"natural question {record['id']} prompt",
            expected=prompt_expected,
        )
        expected = record["expected"]
        if not isinstance(expected, dict):
            raise QwenWorkloadError("natural expected result must be an object")
        exact_keys(
            expected,
            {
                "context_tokens_committed",
                "eos_token_id",
                "generated_text_raw",
                "generated_text_visible",
                "generated_token_count",
                "generated_token_ids",
                "rom_logits_sha256",
                "rom_result_id",
                "termination",
            },
            set(),
            f"natural question {record['id']} expected result",
        )
        generated = _tokens(
            expected["generated_token_ids"],
            f"natural question {record['id']} generated tokens",
            maximum_count=8000,
        )
        logits = expected["rom_logits_sha256"]
        if not isinstance(logits, list) or len(logits) != len(generated):
            raise QwenWorkloadError("natural ROM logits coverage differs")
        for index, digest in enumerate(logits):
            require_sha256(digest, f"natural ROM logits[{index}]")
        require_sha256(expected["rom_result_id"], "natural ROM result ID")
        if (
            expected["termination"] != "eos"
            or expected["eos_token_id"] != generated[-1]
            or generated[-1] not in EOS_TOKEN_IDS
            or any(token in EOS_TOKEN_IDS for token in generated[:-1])
            or expected["generated_token_count"] != len(generated)
            or expected["context_tokens_committed"]
            != prompt["prompt_token_count"] + len(generated) - 1
            or not isinstance(expected["generated_text_raw"], str)
            or not isinstance(expected["generated_text_visible"], str)
        ):
            raise QwenWorkloadError("natural EOS or result boundary differs")
        if chat is not None and (
            chat.decode(generated, skip_special_tokens=False)
            != expected["generated_text_raw"]
            or chat.decode(generated, skip_special_tokens=True)
            != expected["generated_text_visible"]
        ):
            raise QwenWorkloadError("natural expected decode differs")
    return records


def _validate_agent(
    agent: object, chat: QwenChatTokenizer | None
) -> dict[str, Any]:
    if not isinstance(agent, dict):
        raise QwenWorkloadError("agent workload must be an object")
    exact_keys(
        agent,
        {
            "bash_tool",
            "bash_tool_sha256",
            "enable_thinking",
            "generation_mode",
            "maximum_agent_turns",
            "maximum_new_tokens_per_turn",
            "rom_campaign_id",
            "rom_suite_id",
            "system_prompt",
            "tasks",
            "terminalbench_commit",
        },
        set(),
        "agent workload",
    )
    for field in ("bash_tool_sha256", "rom_campaign_id", "rom_suite_id"):
        require_sha256(agent[field], f"agent workload.{field}")
    if (
        agent["bash_tool"] != BASH_TOOL
        or agent["bash_tool_sha256"] != BASH_TOOL_SHA256
        or agent["enable_thinking"] is not False
        or agent["generation_mode"] != "greedy"
        or agent["maximum_agent_turns"] != 4
        or agent["maximum_new_tokens_per_turn"] != 800
        or agent["system_prompt"] != SYSTEM_PROMPT
        or agent["terminalbench_commit"]
        != "d28711d0da2675d0bb1d56de45ae5df6082438a3"
    ):
        raise QwenWorkloadError("agent protocol boundary differs")
    tasks = agent["tasks"]
    if not isinstance(tasks, list) or tuple(
        task.get("id") if isinstance(task, dict) else None for task in tasks
    ) != AGENT_TASK_IDS:
        raise QwenWorkloadError("agent task coverage or ordering differs")
    for task in tasks:
        exact_keys(task, {"expected", "id", "source"}, set(), "agent task")
        source = task["source"]
        expected = task["expected"]
        if (
            not isinstance(source, dict)
            or source.get("id") != task["id"]
            or not isinstance(source.get("instruction"), str)
            or not isinstance(expected, dict)
        ):
            raise QwenWorkloadError("agent task source differs")
        exact_keys(
            expected,
            {
                "agent_termination",
                "commands",
                "final_answer",
                "rom_image_id",
                "rom_test_stderr",
                "rom_test_stdout",
                "test_exit_code",
                "turns",
            },
            set(),
            f"agent task {task['id']} expected",
        )
        if (
            expected["agent_termination"] != "eos"
            or expected["test_exit_code"] != 0
            or not isinstance(expected["final_answer"], str)
            or not expected["final_answer"]
            or not isinstance(expected["commands"], list)
            or not isinstance(expected["turns"], list)
            or not expected["turns"]
        ):
            raise QwenWorkloadError("agent expected result differs")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": source["instruction"]},
        ]
        action_index = 0
        for turn_index, turn in enumerate(expected["turns"], start=1):
            if not isinstance(turn, dict):
                raise QwenWorkloadError("agent turn must be an object")
            exact_keys(turn, {"expected", "prompt", "turn"}, set(), "agent turn")
            if turn["turn"] != turn_index:
                raise QwenWorkloadError("agent turn ordering differs")
            prompt_expected = None
            if chat is not None:
                prompt_expected = chat.prompt_record(
                    messages, tools=[BASH_TOOL], enable_thinking=False
                )
            _validate_prompt(
                turn["prompt"],
                f"agent task {task['id']} turn {turn_index} prompt",
                expected=prompt_expected,
            )
            generation = turn["expected"]
            if not isinstance(generation, dict):
                raise QwenWorkloadError("agent generation must be an object")
            generated = _tokens(
                generation.get("generated_token_ids"),
                "agent generated tokens",
                maximum_count=800,
            )
            if (
                generation.get("generated_token_count") != len(generated)
                or generation.get("termination") != "eos"
                or generated[-1] not in EOS_TOKEN_IDS
                or any(token in EOS_TOKEN_IDS for token in generated[:-1])
            ):
                raise QwenWorkloadError("agent generation EOS boundary differs")
            raw = generation.get("generated_text_raw")
            if chat is not None and (
                chat.decode(generated, skip_special_tokens=False) != raw
                or chat.decode(generated, skip_special_tokens=True)
                != generation.get("generated_text_visible")
            ):
                raise QwenWorkloadError("agent generation decode differs")
            parsed = parse_assistant_output(raw)
            if (
                list(parsed.calls) != generation.get("calls")
                or parsed.content != generation.get("content")
                or parsed.reasoning != generation.get("reasoning")
            ):
                raise QwenWorkloadError("agent parsed protocol differs")
            require_sha256(generation.get("rom_result_id"), "agent ROM result ID")
            messages.append(assistant_message(parsed))
            for call_index, call in enumerate(parsed.calls, start=1):
                if action_index >= len(expected["commands"]):
                    raise QwenWorkloadError("agent action coverage differs")
                action = expected["commands"][action_index]
                action_index += 1
                if (
                    not isinstance(action, dict)
                    or action.get("turn") != turn_index
                    or action.get("call_index") != call_index
                    or action.get("command") != call["arguments"]["command"]
                    or action.get("type") != "bash_action"
                ):
                    raise QwenWorkloadError("agent action chain differs")
                messages.append({"role": "tool", "content": tool_response(action)})
        if (
            action_index != len(expected["commands"])
            or expected["turns"][-1]["expected"]["calls"]
            or expected["turns"][-1]["expected"]["content"]
            != expected["final_answer"]
        ):
            raise QwenWorkloadError("agent terminal result differs")
    return agent


def validate_shared_workload(
    value: Mapping[str, Any], *, chat: QwenChatTokenizer | None = None
) -> dict[str, Any]:
    """Validate identities, template reproduction, EOS, decodes, and agent turns."""

    workload = dict(value)
    exact_keys(
        workload,
        {
            "agent",
            "claim_boundary",
            "generation",
            "model",
            "natural_questions",
            "official_chat_template_sha256",
            "rom_source_inventory",
            "schema",
            "workload_id",
            "workload_version",
        },
        set(),
        "Qwen shared workload",
    )
    _identity(workload, "workload_id", "Qwen shared workload")
    if (
        workload["schema"] != SCHEMA
        or workload["workload_version"] != VERSION
        or workload["official_chat_template_sha256"]
        != OFFICIAL_CHAT_TEMPLATE_SHA256
        or workload["claim_boundary"]
        != {
            "accelerator_execution_proven": False,
            "agent_environment_replayed": False,
            "rom_goldens_imported": True,
            "semantic_goldens_frozen_before_accelerator_execution": True,
            "timing_or_performance": False,
        }
        or workload["generation"]
        != {
            "eos_token_ids": list(EOS_TOKEN_IDS),
            "eos_token_included": True,
            "padded_output_rows": {
                "end_exclusive": MODEL_VOCABULARY_SIZE,
                "policy": "reject_if_selected",
                "start": EXPLICIT_VOCABULARY_SIZE,
            },
            "selection": "greedy_lowest_token_id_argmax",
            "stop_rule": "first_eos_or_maximum_generated_token_count",
        }
    ):
        raise QwenWorkloadError("Qwen shared workload boundary differs")
    model = workload["model"]
    if (
        not isinstance(model, dict)
        or model.get("id") != "qwen3-8b"
        or model.get("repository") != "Qwen/Qwen3-8B"
        or model.get("revision") != SOURCE_REVISION
        or model.get("source_files") != SOURCE_FILES
    ):
        raise QwenWorkloadError("Qwen shared model boundary differs")
    require_sha256(model.get("checkpoint_lock_id"), "shared checkpoint lock ID")
    inventory = workload["rom_source_inventory"]
    if not isinstance(inventory, list) or len(inventory) != len(EXPECTED_ROM_FILES):
        raise QwenWorkloadError("ROM source inventory coverage differs")
    for record, (role, expected) in zip(
        inventory, sorted(EXPECTED_ROM_FILES.items()), strict=True
    ):
        if (
            not isinstance(record, dict)
            or record.get("role") != role
            or record.get("commit") != expected["commit"]
            or record.get("path") != expected["path"]
            or record.get("sha256") != expected["sha256"]
            or not isinstance(record.get("size_bytes"), int)
            or record["size_bytes"] < 1
        ):
            raise QwenWorkloadError("ROM source inventory differs")
    _validate_natural(workload["natural_questions"], chat)
    _validate_agent(workload["agent"], chat)
    return workload


def load_shared_workload(
    path: Path, *, chat: QwenChatTokenizer | None = None
) -> dict[str, Any]:
    """Load only canonical, fully validated workload bytes."""

    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise QwenWorkloadError(f"cannot load Qwen shared workload: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenWorkloadError("Qwen shared workload is not canonical JSON")
    return validate_shared_workload(value, chat=chat)


def publish_shared_workload(value: Mapping[str, Any], output: Path) -> None:
    workload = validate_shared_workload(value)
    try:
        publish_bytes_atomic_no_replace(Path(output), canonical_json_bytes(workload))
    except FileExistsError as exc:
        raise QwenWorkloadError(f"Qwen shared workload already exists: {output}") from exc
    except OSError as exc:
        raise QwenWorkloadError(f"cannot publish Qwen shared workload: {exc}") from exc


__all__ = [
    "AGENT_TASK_IDS",
    "EXPECTED_ROM_FILES",
    "NATURAL_QUESTION_IDS",
    "QwenWorkloadError",
    "SCHEMA",
    "VERSION",
    "load_shared_workload",
    "publish_shared_workload",
    "validate_shared_workload",
]
