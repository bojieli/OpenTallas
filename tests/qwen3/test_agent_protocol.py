from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from compiler.ir.model import canonical_json_bytes
from tools.run_qwen3_terminalbench import (
    AgentProtocolError,
    BASH_TOOL,
    _assistant_message,
    docker_run_arguments,
    parse_assistant_output,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas/compiler/qwen3"


def test_official_qwen_tool_call_parser_accepts_one_or_more_strict_calls() -> None:
    parsed = parse_assistant_output(
        "<think>Inspect, then repair.</think>\n"
        "<tool_call>\n"
        '{"name":"bash","arguments":{"command":"pwd"}}\n'
        "</tool_call>\n"
        "<tool_call>\n"
        '{"name":"bash","arguments":{"command":"ls -la"}}\n'
        "</tool_call><|im_end|>"
    )

    assert parsed.reasoning == "Inspect, then repair."
    assert parsed.content == ""
    assert parsed.calls == (
        {"name": "bash", "arguments": {"command": "pwd"}},
        {"name": "bash", "arguments": {"command": "ls -la"}},
    )
    message = _assistant_message(parsed)
    assert message["tool_calls"] == [
        {
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": {"command": "pwd"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": {"command": "ls -la"},
            },
        },
    ]


def test_official_qwen_tool_call_parser_preserves_a_final_answer() -> None:
    parsed = parse_assistant_output(
        "<think>The command succeeded.</think>\nDone and verified.<|im_end|>"
    )

    assert parsed.reasoning == "The command succeeded."
    assert parsed.content == "Done and verified."
    assert parsed.calls == ()


@pytest.mark.parametrize(
    "output",
    [
        '<tool_call>{"name":"python","arguments":{"command":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"cmd":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"command":3}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"command":"pwd"},"extra":1}</tool_call>',
        '<tool_call>{"name":"bash","name":"bash","arguments":{"command":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"command":"pwd"}}</tool_call',
        "<think>unclosed",
    ],
)
def test_tool_call_parser_fails_closed(output: str) -> None:
    with pytest.raises(AgentProtocolError):
        parse_assistant_output(output)


def test_only_bash_is_advertised_with_a_closed_argument_schema() -> None:
    assert BASH_TOOL == {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command inside the isolated TerminalBench task container."
            ),
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    }


def test_agent_container_has_no_network_capabilities_or_host_mount() -> None:
    arguments = docker_run_arguments("bounded-container", "sha256:" + "0" * 64)

    assert arguments[:3] == ["docker", "run", "--detach"]
    assert arguments[arguments.index("--network") + 1] == "none"
    assert arguments[arguments.index("--cap-drop") + 1] == "ALL"
    assert arguments[arguments.index("--security-opt") + 1] == "no-new-privileges:true"
    assert arguments[arguments.index("--pids-limit") + 1] == "128"
    assert not ({"--volume", "-v", "--mount", "--privileged"} & set(arguments))
    assert arguments[-2:] == ["sleep", "infinity"]


def test_terminalbench_suite_is_schema_valid_content_bound_and_pinned() -> None:
    path = ROOT / "testdata/compiler/qwen3_8b/terminalbench_tasks.json"
    suite = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(
        (SCHEMA_DIR / "terminalbench_task_suite_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(suite)
    body = {key: value for key, value in suite.items() if key != "suite_id"}
    assert suite["suite_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert suite["terminalbench_commit"] == ("d28711d0da2675d0bb1d56de45ae5df6082438a3")
    assert suite["maximum_new_tokens_per_turn"] == 800
    assert suite["maximum_agent_turns"] == 4
    assert suite["enable_thinking"] is False
    assert suite["generation_mode"] == "greedy"
    assert [task["id"] for task in suite["tasks"]] == [
        "hello-world",
        "fix-permissions",
    ]
    assert all(
        "solution" not in item["path"] and "tests" not in item["path"]
        for task in suite["tasks"]
        for item in task["runtime_files"]
    )


def test_retained_eos_campaign_reaches_official_eos_and_reconciles() -> None:
    output = ROOT / "results/compiler/qwen3-8b/eos-campaign"
    report = json.loads((output / "campaign.json").read_text(encoding="utf-8"))
    campaign_schema = json.loads(
        (SCHEMA_DIR / "eos_campaign_v1.schema.json").read_text(encoding="utf-8")
    )
    generation_schema = json.loads(
        (SCHEMA_DIR / "generation_result_v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator(campaign_schema).validate(report)
    body = {key: value for key, value in report.items() if key != "report_id"}
    assert report["report_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert (
        report["runner_sha256"]
        == hashlib.sha256(
            (ROOT / "tools/run_qwen3_eos_campaign.py").read_bytes()
        ).hexdigest()
    )
    assert report["status"] == "pass"
    assert report["all_reached_eos"] is True
    assert report["maximum_new_tokens"] == 8000
    assert report["warning_token_threshold"] == 800
    assert len(report["questions"]) == 6

    for summary in report["questions"]:
        generation = json.loads(
            (output / summary["result_path"]).read_text(encoding="utf-8")
        )
        Draft202012Validator(generation_schema).validate(generation)
        generation_body = {
            key: value for key, value in generation.items() if key != "result_id"
        }
        assert (
            generation["result_id"]
            == hashlib.sha256(canonical_json_bytes(generation_body)).hexdigest()
        )
        assert generation["result_id"] == summary["result_id"]
        assert generation["termination"] == summary["termination"] == "eos"
        assert generation["generated_token_ids"][-1] in report["eos_token_ids"]
        assert (
            len(generation["generated_token_ids"]) == summary["generated_token_count"]
        )
        assert len(generation["spans"]) == summary["span_count"]
        assert generation["context_tokens_committed"] <= 8000
        assert generation["context_tokens_committed"] == (
            generation["prompt_token_count"]
            + len(generation["generated_token_ids"])
            - 1
        )
        assert all(
            span["counter_reconciliation"]["exact"]
            and span["counters"] == span["counter_reconciliation"]["expected"]
            for span in generation["spans"]
        )

    warning_cases = [
        question
        for question in report["questions"]
        if not question["reached_eos_within_warning_threshold"]
    ]
    assert [(item["id"], item["generated_token_count"]) for item in warning_cases] == [
        ("reasoning", 1052)
    ]


def test_retained_terminalbench_campaign_is_isolated_agentic_and_passing() -> None:
    path = ROOT / "results/compiler/qwen3-8b/terminalbench-agent/campaign.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(
        (SCHEMA_DIR / "terminalbench_agent_campaign_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(report)
    body = {key: value for key, value in report.items() if key != "campaign_id"}
    assert (
        report["campaign_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    assert (
        report["campaign_id"]
        == "853bced4fdbc0ed88519678e8b92d22c7059fb9a8c10226525e182d81e22c17b"
    )
    assert (
        report["runner_sha256"]
        == hashlib.sha256(
            (ROOT / "tools/run_qwen3_terminalbench.py").read_bytes()
        ).hexdigest()
    )
    assert (
        report["bash_tool_schema_sha256"]
        == hashlib.sha256(canonical_json_bytes(BASH_TOOL)).hexdigest()
    )
    assert report["official_chat_template_sha256"] == (
        "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"
    )
    assert report["build_id"] == (
        "2b28af60c3d99597b2f6ec654ca9f49c95fb182c58d9f3779e147a7ca34ae7bf"
    )
    assert report["status"] == "pass"
    assert report["all_tasks_passed"] is True
    assert report["tool_names"] == ["bash"]
    assert report["generation_mode"] == "greedy"
    assert report["enable_thinking"] is False
    assert report["maximum_new_tokens_per_turn"] == 800
    assert report["context_limit_tokens"] == 8000

    tasks = {task["id"]: task for task in report["tasks"]}
    assert set(tasks) == {"hello-world", "fix-permissions"}
    assert [
        action["command"]
        for action in tasks["hello-world"]["transcript"]
        if action["type"] == "bash_action"
    ] == ["echo 'Hello, world!' > /app/hello.txt"]
    assert [
        action["command"]
        for action in tasks["fix-permissions"]["transcript"]
        if action["type"] == "bash_action"
    ] == ["ls -l /app/process_data.sh", "chmod +x /app/process_data.sh"]

    expected_isolation = {
        "cap_drop_all": True,
        "host_mounts": False,
        "network": "none",
        "no_new_privileges": True,
        "pids_limit": 128,
        "privileged": False,
        "read_only_rootfs": False,
    }
    for task in tasks.values():
        assert task["passed"] is True
        assert task["agent_termination"] == "eos"
        assert task["test_exit_code"] == 0
        assert "failed" in task["test_stdout"]
        assert task["test_stderr"] == ""
        assert task["container_isolation"] == expected_isolation
        generations = [
            entry
            for entry in task["transcript"]
            if entry["type"] == "assistant_generation"
        ]
        actions = [
            entry for entry in task["transcript"] if entry["type"] == "bash_action"
        ]
        assert len(generations) == task["turn_count"]
        assert len(actions) == task["command_count"]
        assert (
            sum(generation["generated_token_count"] for generation in generations)
            == task["model_generated_tokens"]
        )
        assert all(
            generation["termination"] == "eos"
            and generation["generated_token_ids"][-1] in {151643, 151645}
            and generation["generated_token_count"] <= 800
            and generation["prompt_token_count"]
            + generation["generated_token_count"]
            - 1
            <= 8000
            for generation in generations
        )
        assert all(not action["timed_out"] for action in actions)
        assert all(
            "test_outputs" not in json.dumps(entry) for entry in task["transcript"]
        )
