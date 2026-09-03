"""Fail-closed tests for the ABI 3 closed-loop agent runner.

The tests deliberately use scripted adapters, driver results and sandboxes.
They exercise the orchestration and provenance boundaries without loading a
checkpoint, lowering a graph, or launching either supported model workload.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import pytest

from compiler.frontend.deepseek_v4_encoding import DSML_TOKEN, EOS_TOKEN
from runtime.agent import CommandResult
from tools import run_abi3_agent_episode as runner


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = "bolts,24\nnuts,17\nwashers,58\nscrews,131\nrivets,9\n"
AWK_COMMAND = "awk -F, '{sum += $2} END {print sum}' inventory.txt"
EOS_ID = 9
VOCABULARY_SIZE = 16


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Scripted closed-loop dependencies
# ---------------------------------------------------------------------------


class _ScriptedAdapter:
    model_id = "qwen3-8b"

    def __init__(self) -> None:
        self.rendered_messages: list[list[dict[str, Any]]] = []
        self.rendered_texts: list[str] = []
        self.parse_index = 0
        command_content = (
            f"<think>Inspect and total the file.</think>\n\n```bash\n{AWK_COMMAND}\n```"
        )
        self.turns = [
            runner.ParsedModelTurn(
                kind="command",
                raw_decoded_text=command_content,
                visible_text=f"```bash\n{AWK_COMMAND}\n```",
                thinking_text="Inspect and total the file.",
                parsed={
                    "kind": "command",
                    "command": AWK_COMMAND,
                    "answer": None,
                },
                assistant_message={"role": "assistant", "content": command_content},
                command=AWK_COMMAND,
            ),
            runner.ParsedModelTurn(
                kind="answer",
                raw_decoded_text="ANSWER: 239",
                visible_text="ANSWER: 239",
                thinking_text=None,
                parsed={"kind": "answer", "command": None, "answer": "239"},
                assistant_message={"role": "assistant", "content": "ANSWER: 239"},
                answer="239",
            ),
        ]

    def initial_messages(self) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": "Use the inventory."},
            {"role": "user", "content": "Return its total."},
        ]

    def render(self, messages: Sequence[Mapping[str, Any]]) -> tuple[str, list[int]]:
        snapshot = [dict(message) for message in messages]
        self.rendered_messages.append(snapshot)
        if len(self.rendered_messages) == 1:
            rendered = "initial rendered prompt"
            tokens = [1, 2]
        else:
            rendered = "follow-up rendered prompt\n" + str(snapshot[-1]["content"])
            tokens = [1, 2, 3]
        self.rendered_texts.append(rendered)
        return rendered, tokens

    def parse_generated(self, token_ids: Sequence[int]) -> runner.ParsedModelTurn:
        del token_ids
        turn = self.turns[self.parse_index]
        self.parse_index += 1
        return turn

    def append_observation(
        self,
        messages: Sequence[Mapping[str, Any]],
        turn: runner.ParsedModelTurn,
        observation: str,
    ) -> list[dict[str, Any]]:
        result = [dict(message) for message in messages]
        result.append(dict(turn.assistant_message))
        result.append({"role": "user", "content": observation})
        return result

    def tokenizer_identities(self) -> dict[str, Any]:
        return {}


class _RecordingSandbox:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[str] = []

    def run(self, command: str) -> CommandResult:
        self.commands.append(command)
        assert command == self.result.command
        return self.result


def _valid_execution(
    prompt: Sequence[int],
    generated: Sequence[int],
    *,
    turn_index: int,
    session_id: int,
) -> runner.TurnExecution:
    transaction_base = turn_index * 10 + 1
    per_step = [
        {
            "step": index,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "produced_tokens": [token],
            "final_token_id": token,
            "transaction_id": transaction_base + index,
        }
        for index, token in enumerate(generated)
    ]
    result = SimpleNamespace(
        generated_token_ids=list(generated),
        prompt_token_ids=list(prompt),
        stop_reason="eos",
        eos_token_id=EOS_ID,
        failure=None,
        per_step=per_step,
        transactions=len(per_step),
        prefill_tokens=len(prompt),
        decode_steps=max(0, len(generated) - 1),
        counters={"transactions": len(per_step)},
    )
    before = turn_index * 2
    after = before + len(per_step)
    return runner.TurnExecution(
        result=result,
        session_id=session_id,
        generation_policy={"selection": "argmax", "temperature": 0.0},
        counters_before={"transactions": before},
        counters_after={"transactions": after},
        node_counters_before=[{"engine_calls": before}],
        node_counters_after=[{"engine_calls": after}],
    )


class _ScriptedGenerator:
    def __init__(
        self,
        *,
        generated: Sequence[Sequence[int]] = ((4, EOS_ID), (5, EOS_ID)),
        session_ids: Sequence[int] = (101, 102),
        mutate: Callable[[int, runner.TurnExecution], runner.TurnExecution]
        | None = None,
    ) -> None:
        self.generated = [list(tokens) for tokens in generated]
        self.session_ids = list(session_ids)
        self.mutate = mutate
        self.calls: list[tuple[list[int], int]] = []

    def __call__(self, prompt: Sequence[int], limit: int) -> runner.TurnExecution:
        index = len(self.calls)
        self.calls.append((list(prompt), limit))
        execution = _valid_execution(
            prompt,
            self.generated[index],
            turn_index=index,
            session_id=self.session_ids[index],
        )
        return self.mutate(index, execution) if self.mutate else execution


@dataclass
class _LoopCase:
    adapter: _ScriptedAdapter
    workload: dict[str, Any]
    oracle: dict[str, Any]
    sandbox: _RecordingSandbox
    observation: CommandResult


def _loop_case() -> _LoopCase:
    observation = CommandResult(
        command=AWK_COMMAND,
        exit_code=0,
        stdout="239\n",
        stderr="",
        timed_out=False,
        truncated=False,
    )
    adapter = _ScriptedAdapter()
    initial_text = "initial rendered prompt"
    followup_text = "follow-up rendered prompt\n" + observation.rendered()
    parsed_command = {
        "kind": "command",
        "command": AWK_COMMAND,
        "answer": None,
    }
    parsed_answer = {"kind": "answer", "command": None, "answer": "239"}
    oracle = {
        "answer": "239",
        "turns": [
            {
                "turn": 0,
                "prompt_token_ids": [1, 2],
                "rendered_prompt_sha256": _text_sha256(initial_text),
                "max_new_tokens": 4,
                "generated_token_ids": [4, EOS_ID],
                "stop_reason": "eos",
                "parsed": parsed_command,
                "outcome": "executed",
                "observation": observation.to_dict(),
            },
            {
                "turn": 1,
                "prompt_token_ids": [1, 2, 3],
                "rendered_prompt_sha256": _text_sha256(followup_text),
                "max_new_tokens": 4,
                "generated_token_ids": [5, EOS_ID],
                "stop_reason": "eos",
                "parsed": parsed_answer,
                "outcome": "answered",
            },
        ],
    }
    workload = {
        "token_ids": [1, 2],
        "rendered_text": initial_text,
        "max_new_tokens": 4,
    }
    return _LoopCase(
        adapter=adapter,
        workload=workload,
        oracle=oracle,
        sandbox=_RecordingSandbox(observation),
        observation=observation,
    )


def _run_loop(
    case: _LoopCase,
    generator: _ScriptedGenerator,
    *,
    context_capacity: int = 8,
) -> runner.EpisodeOutcome:
    return runner.run_episode(
        adapter=case.adapter,
        workload=case.workload,
        oracle_episode=case.oracle,
        expected_total=239,
        max_turns=4,
        context_capacity=context_capacity,
        vocabulary_size=VOCABULARY_SIZE,
        eos_token_ids=(EOS_ID,),
        generate_turn=generator,
        sandbox=case.sandbox,
    )


def test_closed_loop_executes_exact_command_and_renders_real_observation() -> None:
    case = _loop_case()
    generator = _ScriptedGenerator()

    outcome = _run_loop(case, generator)

    assert outcome.status == "pass"
    assert outcome.stop_reason == "answered"
    assert outcome.answer == "239"
    assert outcome.task_solved is True
    assert outcome.oracle_agreement is True
    assert outcome.executed_command_count == 1
    assert case.sandbox.commands == [AWK_COMMAND]
    assert [turn["session_id"] for turn in outcome.turns] == [101, 102]
    assert case.adapter.rendered_messages[1][-1] == {
        "role": "user",
        "content": case.observation.rendered(),
    }
    assert case.observation.rendered() in case.adapter.rendered_texts[1]
    assert case.observation.rendered() in outcome.turns[1]["rendered_prompt_text"]
    assert (
        _text_sha256(outcome.turns[1]["rendered_prompt_text"])
        == outcome.turns[1]["rendered_prompt_sha256"]
    )
    assert outcome.turns[0]["parsed"] == case.oracle["turns"][0]["parsed"]
    assert outcome.turns[0]["observation"] == case.observation.to_dict()


def test_oracle_token_divergence_stops_before_sandbox() -> None:
    case = _loop_case()
    generator = _ScriptedGenerator(generated=((6, EOS_ID), (5, EOS_ID)))

    outcome = _run_loop(case, generator)

    assert outcome.status == "diverged"
    assert outcome.stop_reason == "oracle_divergence"
    assert outcome.turns[0]["outcome"] == "oracle_token_divergence"
    assert case.sandbox.commands == []
    assert len(generator.calls) == 1


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("prompt_token_ids", [1, 7]),
        ("rendered_prompt_sha256", "0" * 64),
        ("max_new_tokens", 3),
    ],
)
def test_prompt_hash_or_limit_divergence_stops_before_generation(
    field: str, replacement: Any
) -> None:
    case = _loop_case()
    case.oracle["turns"][0][field] = replacement
    generator = _ScriptedGenerator()

    outcome = _run_loop(case, generator)

    assert outcome.status == "diverged"
    assert outcome.turns[0]["outcome"] == "oracle_prompt_divergence"
    assert outcome.turns[0]["rendered_prompt_text"] == "initial rendered prompt"
    assert (
        _text_sha256(outcome.turns[0]["rendered_prompt_text"])
        == outcome.turns[0]["rendered_prompt_sha256"]
    )
    assert generator.calls == []
    assert case.sandbox.commands == []


def test_context_exhaustion_stops_before_generation() -> None:
    case = _loop_case()
    generator = _ScriptedGenerator()

    outcome = _run_loop(case, generator, context_capacity=2)

    assert outcome.status == "failed"
    assert outcome.stop_reason == "context_exhausted"
    assert outcome.turns == []
    assert generator.calls == []
    assert case.sandbox.commands == []


def test_out_of_vocabulary_rendered_prompt_stops_before_generation() -> None:
    case = _loop_case()
    case.workload["token_ids"] = [1, VOCABULARY_SIZE]
    case.adapter.render = lambda messages: (  # type: ignore[method-assign]
        "initial rendered prompt",
        [1, VOCABULARY_SIZE],
    )
    generator = _ScriptedGenerator()
    with pytest.raises(runner.EpisodeRefusal, match="invalid prompt tokens"):
        _run_loop(case, generator)
    assert generator.calls == []
    assert case.sandbox.commands == []


def _erase_per_step(
    index: int, execution: runner.TurnExecution
) -> runner.TurnExecution:
    del index
    execution.result.per_step = []
    return execution


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(
            _ScriptedGenerator(generated=((VOCABULARY_SIZE, EOS_ID), (5, EOS_ID))),
            id="out-of-vocabulary-token",
        ),
        pytest.param(_ScriptedGenerator(mutate=_erase_per_step), id="per-step-shape"),
    ],
)
def test_invalid_tokens_or_step_evidence_stop_before_sandbox(
    generator: _ScriptedGenerator,
) -> None:
    case = _loop_case()

    outcome = _run_loop(case, generator)

    assert outcome.status == "failed"
    assert outcome.turns[0]["outcome"] == "invalid_execution_evidence"
    assert outcome.turns[0]["token_legitimacy_problems"]
    assert case.sandbox.commands == []


def test_reused_accelerator_session_is_invalid_evidence() -> None:
    case = _loop_case()
    generator = _ScriptedGenerator(session_ids=(101, 101))

    outcome = _run_loop(case, generator)

    assert outcome.status == "failed"
    assert outcome.executed_command_count == 1
    assert case.sandbox.commands == [AWK_COMMAND]
    assert "accelerator session id was reused" in outcome.problems[-1]
    assert outcome.turns[1]["outcome"] == "invalid_execution_evidence"


def test_node_counter_snapshot_count_change_is_refused() -> None:
    def mutate(index: int, execution: runner.TurnExecution) -> runner.TurnExecution:
        del index
        return replace(execution, node_counters_after=[])

    case = _loop_case()
    with pytest.raises(runner.EpisodeRefusal, match="snapshot count changed"):
        _run_loop(case, _ScriptedGenerator(mutate=mutate))
    assert case.sandbox.commands == []


def test_decreasing_counter_is_refused() -> None:
    def mutate(index: int, execution: runner.TurnExecution) -> runner.TurnExecution:
        del index
        return replace(
            execution,
            counters_before={"transactions": 8},
            counters_after={"transactions": 7},
        )

    case = _loop_case()
    with pytest.raises(runner.EpisodeRefusal, match="malformed or decreased"):
        _run_loop(case, _ScriptedGenerator(mutate=mutate))
    assert case.sandbox.commands == []


def test_generation_policy_change_prevents_a_pass() -> None:
    def mutate(index: int, execution: runner.TurnExecution) -> runner.TurnExecution:
        if index == 1:
            return replace(execution, generation_policy={"selection": "sample"})
        return execution

    case = _loop_case()
    outcome = _run_loop(case, _ScriptedGenerator(mutate=mutate))
    assert outcome.status == "failed"
    assert "generation policy changed between turns" in outcome.problems


# ---------------------------------------------------------------------------
# Qwen and DeepSeek completion protocols
# ---------------------------------------------------------------------------


def test_qwen_ignores_draft_action_inside_closed_thinking_block() -> None:
    visible = (
        "<think>\nMaybe run ```bash\ncat inventory.txt\n``` first.\n</think>\n\n"
        f"```bash\n{AWK_COMMAND}\n```"
    )
    parsed = runner.parse_qwen_completion(visible, visible)
    assert parsed.kind == "command"
    assert parsed.command == AWK_COMMAND
    assert parsed.thinking_text is not None
    assert "cat inventory.txt" in parsed.thinking_text
    assert parsed.assistant_message == {"role": "assistant", "content": visible}


def test_qwen_thinking_and_full_assistant_content_are_retained_for_history() -> None:
    visible = "<think>\nThe exact total is now known.\n</think>\n\nANSWER: 239"
    parsed = runner.parse_qwen_completion("raw-with-eos", visible)
    assert parsed.kind == "answer"
    assert parsed.answer == "239"
    assert parsed.raw_decoded_text == "raw-with-eos"
    assert parsed.visible_text == "ANSWER: 239"
    assert parsed.thinking_text == "The exact total is now known."
    assert parsed.assistant_message["content"] == visible


@pytest.mark.parametrize(
    "text",
    [
        f"```bash\n{AWK_COMMAND}\n```\nANSWER: 239",
        "The result is clear.\nANSWER: 239",
        "ANSWER: 239\nThanks.",
    ],
)
def test_qwen_rejects_ambiguous_or_nonexact_final_answer(text: str) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.parse_qwen_completion(text, text)


@pytest.mark.parametrize(
    "text",
    [
        "```bash\ncat inventory.txt\n```\n```bash\ncat inventory.txt\n```",
        "```bash\n\n```",
        "```bash\ncat inventory.txt\ncat inventory.txt\n```",
    ],
)
def test_qwen_rejects_multiple_empty_or_multiline_committed_commands(
    text: str,
) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.parse_qwen_completion(text, text)


@pytest.mark.parametrize(
    "text",
    [
        "<think>draft ```bash\ncat inventory.txt\n```",
        "orphan thought</think>ANSWER: 239",
        "<think>one</think><think>two</think>ANSWER: 239",
        "prefix<think>reason</think>ANSWER: 239",
    ],
)
def test_qwen_rejects_malformed_thinking_delimiters(text: str) -> None:
    with pytest.raises(runner.EpisodeRefusal, match="thinking delimiters"):
        runner.parse_qwen_completion(text, text)


def _deepseek_tool_completion(
    calls: Sequence[tuple[str, Sequence[tuple[str, bool, Any]]]],
    *,
    thinking_mode: str = "thinking",
    reasoning: str = "I should inspect the inventory.",
    content: str = "",
    include_eos: bool = True,
) -> str:
    pieces = [content, f"\n\n<{DSML_TOKEN}tool_calls>\n"]
    for tool_name, parameters in calls:
        pieces.append(f'<{DSML_TOKEN}invoke name="{tool_name}">\n')
        for name, is_string, value in parameters:
            raw = str(value) if is_string else json.dumps(value)
            flag = "true" if is_string else "false"
            pieces.append(
                f'<{DSML_TOKEN}parameter name="{name}" string="{flag}">'
                f"{raw}</{DSML_TOKEN}parameter>\n"
            )
        if not parameters:
            pieces.append("\n")
        pieces.append(f"</{DSML_TOKEN}invoke>\n")
    pieces.append(f"</{DSML_TOKEN}tool_calls>")
    body = "".join(pieces)
    if thinking_mode == "thinking":
        body = reasoning + "</think>" + body
    if include_eos:
        body += EOS_TOKEN
    return body


def _run_shell_dsml(
    command: str = AWK_COMMAND, *, thinking_mode: str = "thinking"
) -> str:
    return _deepseek_tool_completion(
        [("run_shell", [("command", True, command)])],
        thinking_mode=thinking_mode,
    )


def test_deepseek_accepts_exact_one_call_dsml_and_exact_answer() -> None:
    command_text = _run_shell_dsml()
    command = runner.parse_deepseek_completion(command_text, "thinking")
    assert command.kind == "command"
    assert command.command == AWK_COMMAND
    assert command.thinking_text == "I should inspect the inventory."
    assert command.visible_text == ""
    assert command.parsed == {
        "kind": "command",
        "tool_name": "run_shell",
        "command": AWK_COMMAND,
        "answer": None,
    }
    assert command.assistant_message["tool_calls"][0]["function"]["name"] == (
        "run_shell"
    )

    answer_text = "The command returned the total.</think>ANSWER: 239" + EOS_TOKEN
    answer = runner.parse_deepseek_completion(answer_text, "thinking")
    assert answer.kind == "answer"
    assert answer.answer == "239"
    assert answer.thinking_text == "The command returned the total."
    assert answer.parsed == {
        "kind": "answer",
        "tool_name": None,
        "command": None,
        "answer": "239",
    }


@pytest.mark.parametrize(
    "completion",
    [
        pytest.param(
            _deepseek_tool_completion(
                [
                    ("run_shell", [("command", True, "cat inventory.txt")]),
                    ("run_shell", [("command", True, AWK_COMMAND)]),
                ]
            ),
            id="multiple-calls",
        ),
        pytest.param(
            _deepseek_tool_completion(
                [("read_file", [("command", True, "cat inventory.txt")])]
            ),
            id="wrong-tool",
        ),
        pytest.param(
            _deepseek_tool_completion(
                [
                    (
                        "run_shell",
                        [
                            ("command", True, "cat inventory.txt"),
                            ("timeout", False, 1),
                        ],
                    )
                ]
            ),
            id="extra-argument",
        ),
        pytest.param(
            _deepseek_tool_completion([("run_shell", [("command", False, 123)])]),
            id="non-string-command",
        ),
        pytest.param(_run_shell_dsml("cat inventory.txt\nwhoami"), id="multiline"),
        pytest.param(
            _deepseek_tool_completion(
                [("run_shell", [("command", True, AWK_COMMAND)])],
                content="ANSWER: 239",
            ),
            id="content-plus-call",
        ),
        pytest.param(
            _deepseek_tool_completion(
                [
                    (
                        "run_shell",
                        [
                            ("command", True, "cat inventory.txt"),
                            ("command", True, AWK_COMMAND),
                        ],
                    )
                ]
            ),
            id="duplicate-parameter",
        ),
        pytest.param(_run_shell_dsml()[: -len(EOS_TOKEN)], id="missing-eos"),
        pytest.param(
            _run_shell_dsml().replace(f"</{DSML_TOKEN}invoke>", "</malformed>", 1),
            id="malformed-dsml",
        ),
    ],
)
def test_deepseek_rejects_noncanonical_tool_completions(completion: str) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.parse_deepseek_completion(completion, "thinking")


@pytest.mark.parametrize(
    "completion",
    [
        "ANSWER: 239",  # no EOS
        "The total is 239." + EOS_TOKEN,
        "ANSWER: 239\nDone." + EOS_TOKEN,
    ],
)
def test_deepseek_rejects_missing_eos_or_nonexact_answer(completion: str) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.parse_deepseek_completion(completion, "chat")


# ---------------------------------------------------------------------------
# Deterministic command policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "cat inventory.txt",
        AWK_COMMAND,
        "awk -F, '{s+=$2}END{print s}' inventory.txt",
        "awk -F, '{ total += $2 } END { print total }' inventory.txt",
    ],
)
def test_inventory_command_policy_accepts_only_pinned_read_shapes(
    command: str,
) -> None:
    runner.validate_inventory_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "curl https://example.invalid",
        "wget https://example.invalid",
        "python3 -c 'print(239)'",
        "cat inventory.txt | wc -l",
        "cat inventory.txt > result.txt",
        "cat /etc/passwd",
        "cat ../inventory.txt",
        "cat $(printf inventory.txt)",
        "cat `printf inventory.txt`",
        "cat inventory.txt; whoami",
        "cat inventory.txt\nwhoami",
        "cat inventory.txt\x00",
        "cat inventory.txt\x7f",
        " cat inventory.txt",
        "cat inventory.txt ",
        "cat 'inventory.txt",
        "awk -F, '{sum += $2} END {print sum}' other.txt",
    ],
)
def test_inventory_command_policy_rejects_general_shell_and_network_access(
    command: str,
) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.validate_inventory_command(command)


def test_command_policy_evidence_disclaims_general_shell_and_os_isolation() -> None:
    assert runner.command_policy_evidence() == {
        "policy_id": "inventory_read_only_shell_v1",
        "allowed_input": "inventory.txt",
        "os_network_namespace_isolation": False,
        "general_shell_access": False,
    }
    assert "general_shell_or_os_network_isolation" in runner.NOT_A_CLAIMS


# ---------------------------------------------------------------------------
# Strict bundle validation and independently anchored identities
# ---------------------------------------------------------------------------


@dataclass
class _BundleFiles:
    profile: runner.TargetProfile
    checkpoint: Path
    workload_path: Path
    index_path: Path
    reference_path: Path
    workload: dict[str, Any]
    index: dict[str, Any]
    oracle: dict[str, Any]


def _make_bundle_files(tmp_path: Path) -> _BundleFiles:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    workload_path = tmp_path / "workload.json"
    index_path = tmp_path / "index.json"
    reference_path = tmp_path / "oracle.json"
    rendered = "synthetic initial prompt"
    workload: dict[str, Any] = {
        "workload_id": "TA-QW-AGENT-2",
        "kind": "agent",
        "token_ids": [1, 2],
        "prompt_token_count": 2,
        "rendered_text": rendered,
        "rendered_text_sha256": _text_sha256(rendered),
        "max_new_tokens": 3,
        "metadata": {
            "closed_loop": True,
            "enable_thinking": True,
            "expected_total": 239,
            "max_turns": 4,
            "session_context_capacity": 8,
            "sandbox_files": {"inventory.txt": INVENTORY},
        },
    }
    workload["digest"] = runner.workload_digest(workload)
    _write_json(workload_path, workload)

    base = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    index: dict[str, Any] = {
        "schema": base.workload_index_schema,
        "model_id": base.model_id,
        "tokenizer_sha256": base.tokenizer_sha256,
        "snapshot": str(checkpoint.resolve()),
        "workloads": {
            workload["workload_id"]: {
                "path": workload_path.name,
                "kind": workload["kind"],
                "digest": workload["digest"],
                "prompt_token_count": workload["prompt_token_count"],
                "max_new_tokens": workload["max_new_tokens"],
            }
        },
    }
    _write_json(index_path, index)

    observation = CommandResult(
        command=AWK_COMMAND,
        exit_code=0,
        stdout="239\n",
        stderr="",
        timed_out=False,
        truncated=False,
    )
    followup = "synthetic follow-up prompt"
    oracle: dict[str, Any] = {
        "schema": runner.ORACLE_SCHEMA,
        "evidence_class": "external_reference_comparator",
        "model_id": base.model_id,
        "tokenizer_sha256": base.tokenizer_sha256,
        "results": {
            workload["workload_id"]: {
                "workload_digest": workload["digest"],
                "episode": {
                    "turn_count": 2,
                    "stop_reason": "answered",
                    "answer": "239",
                    "turns": [
                        {
                            "turn": 0,
                            "prompt_token_ids": [1, 2],
                            "prompt_token_count": 2,
                            "rendered_prompt_sha256": _text_sha256(rendered),
                            "max_new_tokens": 3,
                            "generated_token_ids": [4, EOS_ID],
                            "generated_token_count": 2,
                            "stop_reason": "eos",
                            "outcome": "executed",
                            "parsed": {
                                "kind": "command",
                                "command": AWK_COMMAND,
                                "answer": None,
                            },
                            "observation": observation.to_dict(),
                        },
                        {
                            "turn": 1,
                            "prompt_token_ids": [1, 2, 3],
                            "prompt_token_count": 3,
                            "rendered_prompt_sha256": _text_sha256(followup),
                            "max_new_tokens": 3,
                            "generated_token_ids": [5, EOS_ID],
                            "generated_token_count": 2,
                            "stop_reason": "eos",
                            "outcome": "answered",
                            "parsed": {
                                "kind": "answer",
                                "command": None,
                                "answer": "239",
                            },
                            "answer": "239",
                        },
                    ],
                },
            }
        },
    }
    _write_json(reference_path, oracle)
    profile = replace(
        base,
        workload_digest=str(workload["digest"]),
        workload_sha256=_file_sha256(workload_path),
        workload_index_sha256=_file_sha256(index_path),
        eos_token_ids=(EOS_ID,),
    )
    return _BundleFiles(
        profile=profile,
        checkpoint=checkpoint,
        workload_path=workload_path,
        index_path=index_path,
        reference_path=reference_path,
        workload=workload,
        index=index,
        oracle=oracle,
    )


def _validate_bundle(files: _BundleFiles) -> runner.ValidatedBundle:
    return runner.validate_bundle(
        profile=files.profile,
        checkpoint=files.checkpoint,
        workload_path=files.workload_path,
        index_path=files.index_path,
        reference_path=files.reference_path,
    )


def test_synthetic_closed_loop_bundle_is_valid(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    bundle = _validate_bundle(files)
    assert bundle.expected_total == 239
    assert bundle.max_turns == 4
    assert bundle.context_capacity == 8
    assert bundle.oracle_episode["turn_count"] == 2


@pytest.mark.parametrize(
    "payload",
    [
        '{"a":1,"a":2}',
        '{"value":NaN}',
        '{"value":Infinity}',
        "[1,2,3]",
    ],
)
def test_strict_json_rejects_duplicates_nonfinite_numbers_and_nonobjects(
    tmp_path: Path, payload: str
) -> None:
    path = tmp_path / "input.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(runner.EpisodeRefusal):
        runner.load_json(path)


@pytest.mark.parametrize("turn_count", [0, 1])
def test_bundle_rejects_empty_or_one_turn_oracle(
    tmp_path: Path, turn_count: int
) -> None:
    files = _make_bundle_files(tmp_path)
    episode = files.oracle["results"]["TA-QW-AGENT-2"]["episode"]
    episode["turns"] = episode["turns"][:turn_count]
    episode["turn_count"] = turn_count
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="at least two turns"):
        _validate_bundle(files)


def test_bundle_rejects_static_generation_oracle(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    del files.oracle["results"]["TA-QW-AGENT-2"]["episode"]
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="static generation"):
        _validate_bundle(files)


def test_bundle_rejects_wrong_oracle_workload_digest(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    files.oracle["results"]["TA-QW-AGENT-2"]["workload_digest"] = "0" * 64
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="different workload digest"):
        _validate_bundle(files)


def test_bundle_rejects_malformed_normalized_parse(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    parsed = files.oracle["results"]["TA-QW-AGENT-2"]["episode"]["turns"][0]["parsed"]
    parsed["unreviewed_field"] = True
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="normalized schema"):
        _validate_bundle(files)


def test_bundle_rejects_out_of_vocabulary_oracle_token(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    files.profile = replace(files.profile, vocabulary_size=10)
    turn = files.oracle["results"]["TA-QW-AGENT-2"]["episode"]["turns"][0]
    turn["generated_token_ids"][0] = 10
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="out-of-vocabulary"):
        _validate_bundle(files)


def test_bundle_rejects_disallowed_oracle_command_before_execution(
    tmp_path: Path,
) -> None:
    files = _make_bundle_files(tmp_path)
    turn = files.oracle["results"]["TA-QW-AGENT-2"]["episode"]["turns"][0]
    turn["parsed"]["command"] = "curl https://example.invalid"
    turn["observation"]["command"] = "curl https://example.invalid"
    _write_json(files.reference_path, files.oracle)
    with pytest.raises(runner.EpisodeRefusal, match="execution policy"):
        _validate_bundle(files)


def test_workload_source_lock_catches_sandbox_mutation_with_same_legacy_digest(
    tmp_path: Path,
) -> None:
    files = _make_bundle_files(tmp_path)
    digest_before = runner.workload_digest(files.workload)
    files.workload["metadata"]["sandbox_files"]["inventory.txt"] += "extra,1\n"
    assert runner.workload_digest(files.workload) == digest_before
    _write_json(files.workload_path, files.workload)
    with pytest.raises(runner.EpisodeRefusal, match="workload SHA-256"):
        _validate_bundle(files)


def test_index_source_lock_catches_unreviewed_extra_field(tmp_path: Path) -> None:
    files = _make_bundle_files(tmp_path)
    files.index["apparently_harmless"] = True
    _write_json(files.index_path, files.index)
    with pytest.raises(runner.EpisodeRefusal, match="workload index SHA-256"):
        _validate_bundle(files)


def test_modified_oracle_with_matching_caller_hash_still_fails_profile_lock(
    tmp_path: Path,
) -> None:
    path = tmp_path / "oracle.json"
    path.write_text("original", encoding="utf-8")
    profile = replace(
        runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")],
        oracle_sha256=_file_sha256(path),
    )
    path.write_text("modified", encoding="utf-8")
    caller_hash = _file_sha256(path)
    with pytest.raises(runner.EpisodeRefusal, match="target profile lock"):
        runner.validate_reference_identity(profile, path, caller_hash)


def test_unpublished_deepseek_oracle_profile_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "oracle.json"
    path.write_text("{}", encoding="utf-8")
    profile = runner.TARGET_PROFILES[("deepseek-v4-flash-0731", "rom_deepseek_v4")]
    assert profile.oracle_sha256 is None
    with pytest.raises(runner.EpisodeRefusal, match="no published closed-loop oracle"):
        runner.validate_reference_identity(profile, path, _file_sha256(path))


def test_current_qwen_oracle_is_refused_as_stale_for_closed_loop_workload() -> None:
    profile = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    index_path = ROOT / "build/workloads/qwen3-8b/index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    with pytest.raises(runner.EpisodeRefusal, match="different workload digest"):
        runner.validate_bundle(
            profile=profile,
            checkpoint=Path(index["snapshot"]),
            workload_path=ROOT / "build/workloads/qwen3-8b/TA-QW-AGENT-2.json",
            index_path=index_path,
            reference_path=ROOT / "results/abi3/qwen3_reference_oracle_reasoning.json",
        )


def test_current_deepseek_agent_workload_is_refused_until_closed_loop_publish() -> None:
    profile = runner.TARGET_PROFILES[("deepseek-v4-flash-0731", "hbm_sram")]
    with pytest.raises(runner.EpisodeRefusal, match="closed_loop=true"):
        runner.validate_bundle(
            profile=profile,
            checkpoint=ROOT / "unused-checkpoint",
            workload_path=(
                ROOT / "build/workloads/deepseek-v4-flash-0731/TA-DS-AGENT-1.json"
            ),
            index_path=ROOT / "build/workloads/deepseek-v4-flash-0731/index.json",
            reference_path=ROOT
            / "results/abi3/deepseek_v4_reference_oracle_short.json",
        )


# ---------------------------------------------------------------------------
# Fixed target, checkpoint and functional-source boundaries
# ---------------------------------------------------------------------------


def _target_inputs(
    profile: runner.TargetProfile,
) -> tuple[SimpleNamespace, SimpleNamespace, dict[str, str], dict[str, str]]:
    graph = SimpleNamespace(
        model_id=profile.model_id,
        graph_id=profile.graph_id,
        to_dict=lambda: {"numeric_profile": profile.numeric_profile},
    )
    capability = SimpleNamespace(
        topology_class=profile.topology_class,
        limits={"max_nodes": profile.node_count},
        digest=profile.capability_sha256,
    )
    return (
        graph,
        capability,
        {"sha256": profile.kernel_ir_sha256},
        {"sha256": profile.capability_sha256},
    )


def test_target_input_baseline_accepts_exact_profile() -> None:
    profile = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    graph, capability, kernel_identity, capability_identity = _target_inputs(profile)
    runner.validate_target_inputs(
        profile=profile,
        graph=graph,
        kernel_ir_identity=kernel_identity,
        capability=capability,
        capability_identity=capability_identity,
    )


@pytest.mark.parametrize(
    ("target", "attribute", "replacement"),
    [
        ("graph", "graph_id", "0" * 64),
        ("graph", "model_id", "another-model"),
        ("kernel", "sha256", "0" * 64),
        ("capability", "digest", "0" * 64),
        ("capability_identity", "sha256", "0" * 64),
        ("capability", "topology_class", 7),
    ],
)
def test_target_input_rejects_alternate_graph_or_capability(
    target: str, attribute: str, replacement: Any
) -> None:
    profile = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    graph, capability, kernel_identity, capability_identity = _target_inputs(profile)
    values: dict[str, Any] = {
        "graph": graph,
        "capability": capability,
        "kernel": kernel_identity,
        "capability_identity": capability_identity,
    }
    selected = values[target]
    if isinstance(selected, dict):
        selected[attribute] = replacement
    else:
        setattr(selected, attribute, replacement)
    with pytest.raises(runner.EpisodeRefusal):
        runner.validate_target_inputs(
            profile=profile,
            graph=graph,
            kernel_ir_identity=kernel_identity,
            capability=capability,
            capability_identity=capability_identity,
        )


@pytest.mark.parametrize(("topology", "max_nodes"), [(False, 1), (0, True)])
def test_boolean_topology_or_node_count_is_not_an_integer(
    topology: Any, max_nodes: Any
) -> None:
    profile = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    graph, capability, kernel_identity, capability_identity = _target_inputs(profile)
    capability.topology_class = topology
    capability.limits["max_nodes"] = max_nodes
    with pytest.raises(runner.EpisodeRefusal, match="integer"):
        runner.validate_target_inputs(
            profile=profile,
            graph=graph,
            kernel_ir_identity=kernel_identity,
            capability=capability,
            capability_identity=capability_identity,
        )


def test_target_profiles_are_exactly_the_four_governed_lanes() -> None:
    assert set(runner.TARGET_PROFILES) == {
        ("qwen3-8b", "hbm_sram"),
        ("qwen3-8b", "rom_qwen3"),
        ("deepseek-v4-flash-0731", "hbm_sram"),
        ("deepseek-v4-flash-0731", "rom_deepseek_v4"),
    }
    assert {profile.graph_id for profile in runner.TARGET_PROFILES.values()} == {
        "84bb97dd1243553f170fde014c15c76c6adf0b80f0ef3bdad27a015577b6c24b",
        "9ef6c3248d23c181c774fd43c09b0de2a19c8e23f344cb9a25c43040268337d9",
    }
    assert {
        profile.capability_sha256 for profile in runner.TARGET_PROFILES.values()
    } == {
        "fa70dd44a1b532a99d103968b31b743bbed324d002fbe0214c9541fb1687e23d",
        "5b5770fa766cd89d7a236a62722ef33d1db9f87be7403a8f8c55fc9ec8c8458e",
        "1eb2e92dac1d9fb8937b7724953d2f65993bd56e342e9058569442eb61d74bad",
        "5abf26b4ef235d6083c6f6dbe48d7021068c59ecb451238569a2f660303d26b6",
    }


@pytest.mark.parametrize(
    ("model_id", "backend", "capability_name"),
    [
        ("qwen3-8b", "hbm_sram", "hbm_sram_single_chip.json"),
        ("qwen3-8b", "rom_qwen3", "rom_qwen3.json"),
        (
            "deepseek-v4-flash-0731",
            "hbm_sram",
            "hbm_sram_cluster_32.json",
        ),
        (
            "deepseek-v4-flash-0731",
            "rom_deepseek_v4",
            "rom_deepseek_v4.json",
        ),
    ],
)
def test_profile_source_locks_match_the_published_repository_artifacts(
    model_id: str, backend: str, capability_name: str
) -> None:
    profile = runner.TARGET_PROFILES[(model_id, backend)]
    workload_name = (
        "TA-QW-AGENT-2.json" if model_id == "qwen3-8b" else "TA-DS-AGENT-1.json"
    )
    assert (
        _file_sha256(ROOT / f"build/ir-v3/{model_id}/kernel_ir.v3.json")
        == profile.kernel_ir_sha256
    )
    assert (
        _file_sha256(ROOT / "configs/hardware/abi3_capability" / capability_name)
        == profile.capability_sha256
    )
    assert (
        _file_sha256(ROOT / "build/workloads" / model_id / workload_name)
        == profile.workload_sha256
    )
    assert (
        _file_sha256(ROOT / "build/workloads" / model_id / "index.json")
        == profile.workload_index_sha256
    )
    assert (
        _file_sha256(ROOT / "compiler/models" / model_id / "checkpoint_source.json")
        == profile.checkpoint_source_sha256
    )
    if model_id == "qwen3-8b":
        assert (
            _file_sha256(ROOT / "results/abi3/qwen3_reference_oracle_reasoning.json")
            == profile.oracle_sha256
        )
    else:
        assert profile.oracle_sha256 is None


def test_profile_topology_and_deployment_identities_are_exact() -> None:
    actual = {
        key: (
            profile.topology_class,
            profile.node_count,
            profile.deployment_backend,
            profile.target_id,
        )
        for key, profile in runner.TARGET_PROFILES.items()
    }
    assert actual == {
        ("qwen3-8b", "hbm_sram"): (
            0,
            1,
            "hbm-sram-abi3",
            "hbm-sram-abi3-single_chip",
        ),
        ("qwen3-8b", "rom_qwen3"): (
            0,
            1,
            "rom.single_chip",
            "qwen3-8b-rom-single-chip",
        ),
        ("deepseek-v4-flash-0731", "hbm_sram"): (
            1,
            32,
            "hbm-sram-abi3",
            "hbm-sram-abi3-cluster_32",
        ),
        ("deepseek-v4-flash-0731", "rom_deepseek_v4"): (
            2,
            1,
            "rom.wafer_logical_device",
            "deepseek-v4-flash-rom-wafer",
        ),
    }


@pytest.mark.parametrize(
    ("model_id", "backend"),
    [
        ("qwen3-8b", "rom_deepseek_v4"),
        ("deepseek-v4-flash-0731", "rom_qwen3"),
        ("unsupported", "hbm_sram"),
    ],
)
def test_wrong_model_backend_pairing_is_refused(model_id: str, backend: str) -> None:
    with pytest.raises(runner.EpisodeRefusal):
        runner.select_target_profile(model_id, backend)


def _make_checkpoint_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[runner.TargetProfile, Path, Path]:
    repository = tmp_path / "repo"
    source_path = repository / "compiler/models/qwen3-8b/checkpoint_source.json"
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    file_rows: list[tuple[str, int, str]] = []
    expected_files: list[dict[str, Any]] = []
    for name in (
        "config.json",
        "generation_config.json",
        "model.safetensors.index.json",
        "tokenizer.json",
        "tokenizer_config.json",
    ):
        payload = ("pinned:" + name).encode("utf-8")
        (checkpoint / name).write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        file_rows.append((name, len(payload), digest))
        expected_files.append(
            {"path": name, "size_bytes": len(payload), "sha256": digest}
        )
    source = {
        "schema": "opentallas.checkpoint_source.v1",
        "repository": "Qwen/Qwen3-8B",
        "revision": "b968826d9c46dd6066d109eabc6255188de91218",
        "remote_code_policy": "disabled",
        "expected_files": expected_files,
    }
    _write_json(source_path, source)
    profile = replace(
        runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")],
        checkpoint_source_sha256=_file_sha256(source_path),
        checkpoint_files=tuple(file_rows),
    )
    monkeypatch.setattr(runner, "REPO", repository)
    return profile, checkpoint, source_path


def test_checkpoint_index_mutation_is_refused_with_tokenizer_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, checkpoint, _ = _make_checkpoint_fixture(tmp_path, monkeypatch)
    identity = runner.validate_checkpoint_identity(profile, checkpoint)
    tokenizer_before = identity["files"]["tokenizer.json"]
    (checkpoint / "model.safetensors.index.json").write_text(
        "mutated", encoding="utf-8"
    )
    assert runner.file_identity(checkpoint / "tokenizer.json") == tokenizer_before
    with pytest.raises(runner.EpisodeRefusal, match="pinned release"):
        runner.validate_checkpoint_identity(profile, checkpoint)


def test_checkpoint_source_mutation_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile, checkpoint, source_path = _make_checkpoint_fixture(tmp_path, monkeypatch)
    runner.validate_checkpoint_identity(profile, checkpoint)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["unreviewed"] = True
    _write_json(source_path, source)
    with pytest.raises(runner.EpisodeRefusal, match="checkpoint source SHA-256"):
        runner.validate_checkpoint_identity(profile, checkpoint)


@pytest.mark.parametrize(
    ("model_id", "backend", "expected_count"),
    [
        ("qwen3-8b", "hbm_sram", 114),
        ("qwen3-8b", "rom_qwen3", 135),
        ("deepseek-v4-flash-0731", "hbm_sram", 122),
        ("deepseek-v4-flash-0731", "rom_deepseek_v4", 123),
    ],
)
def test_functional_source_map_has_exact_lane_keys(
    model_id: str, backend: str, expected_count: int
) -> None:
    source_map = runner.source_sha256(backend, model_id)
    patterns = (
        *runner.FUNCTIONAL_SOURCE_GLOBS,
        *runner.MODEL_SOURCE_GLOBS[model_id],
        *runner.BACKEND_SOURCE_GLOBS[backend],
    )
    expected_paths = {
        Path(runner.__file__).resolve().relative_to(ROOT).as_posix(),
        *runner.FUNCTIONAL_SOURCE_PATHS,
        *runner.BACKEND_SOURCE_PATHS[backend],
        *runner.MODEL_SOURCE_PATHS[model_id],
        *(
            path.relative_to(ROOT).as_posix()
            for pattern in patterns
            for path in ROOT.glob(pattern)
        ),
    }
    assert set(source_map) == expected_paths
    assert len(source_map) == expected_count
    assert "compiler/workloads/__init__.py" in source_map
    assert "compiler/workloads/qwen3.py" in source_map
    assert "schemas/runtime/abi3_agent_episode_v3.schema.json" in source_map
    assert "runtime/agent.py" in source_map
    if model_id != "qwen3-8b":
        assert "compiler/workloads/deepseek_v4.py" in source_map
        assert "compiler/frontend/deepseek_v4_encoding.py" in source_map
        assert "compiler/frontend/deepseek_v4_tokenizer.py" in source_map
    for relative, expected_sha in source_map.items():
        assert _file_sha256(ROOT / relative) == expected_sha


def test_functional_source_map_changes_on_mutation_and_refuses_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    paths = {
        "tools/runner.py": "runner",
        "core.py": "core-v1",
        "backend.py": "backend",
        "model.py": "model",
        "globbed/helper.py": "helper",
    }
    for relative, text in paths.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(runner, "REPO", repository)
    monkeypatch.setattr(runner, "__file__", str(repository / "tools/runner.py"))
    monkeypatch.setattr(runner, "FUNCTIONAL_SOURCE_PATHS", ("core.py",))
    monkeypatch.setattr(runner, "FUNCTIONAL_SOURCE_GLOBS", ("globbed/*.py",))
    monkeypatch.setattr(runner, "BACKEND_SOURCE_PATHS", {"fake": ("backend.py",)})
    monkeypatch.setattr(runner, "BACKEND_SOURCE_GLOBS", {"fake": ()})
    monkeypatch.setattr(runner, "MODEL_SOURCE_PATHS", {"model": ("model.py",)})
    monkeypatch.setattr(runner, "MODEL_SOURCE_GLOBS", {"model": ()})

    before = runner.source_sha256("fake", "model")
    assert set(before) == set(paths)
    (repository / "core.py").write_text("core-v2", encoding="utf-8")
    after = runner.source_sha256("fake", "model")
    assert after["core.py"] != before["core.py"]
    (repository / "core.py").unlink()
    with pytest.raises(runner.EpisodeRefusal, match="missing"):
        runner.source_sha256("fake", "model")


# ---------------------------------------------------------------------------
# Closed output schema and semantic bindings
# ---------------------------------------------------------------------------


def _artifact_file_identity(
    path: str, *, sha256: str | None = None, byte_count: int = 1
) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": byte_count,
        "sha256": sha256 if sha256 is not None else _text_sha256(path),
    }


def _artifact_steps(
    tokens: Sequence[int], transaction_base: int
) -> list[dict[str, Any]]:
    return [
        {
            "step": index,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "transaction_id": transaction_base + index,
            "retired_work": 100 + index,
            "produced_tokens": [token],
            "final_token_id": token,
            "eos_reason": 1 if index == len(tokens) - 1 else 0,
            "instructions_retired": 10 + index,
            "instructions_predicated_off": index,
            "wall_seconds": 0.001 * (index + 1),
        }
        for index, token in enumerate(tokens)
    ]


def _artifact_turn(
    *,
    index: int,
    prompt: list[int],
    rendered: str,
    generated: list[int],
    outcome: str,
    parsed: dict[str, Any],
    raw_decoded_text: str,
    visible_text: str,
    thinking_text: str | None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counter_before = index * 2
    counter_after = counter_before + len(generated)
    record: dict[str, Any] = {
        "turn": index,
        "session_id": index + 1,
        "prompt_token_ids": prompt,
        "prompt_token_count": len(prompt),
        "rendered_prompt_text": rendered,
        "rendered_prompt_sha256": _text_sha256(rendered),
        "max_new_tokens": 8,
        "generated_token_ids": generated,
        "generated_token_count": len(generated),
        "stop_reason": "eos",
        "eos_token_id": generated[-1],
        "failure": None,
        "token_legitimacy_problems": [],
        "per_step": _artifact_steps(generated, index * 10 + 1),
        "transactions": len(generated),
        "prefill_tokens": len(prompt),
        "decode_steps": len(generated) - 1,
        "driver_counters": {"transactions": len(generated)},
        "counters_before": {"transactions": counter_before},
        "counters_after": {"transactions": counter_after},
        "counter_delta": {"transactions": len(generated)},
        "node_counters_before": [{"engine_calls": counter_before}],
        "node_counters_after": [{"engine_calls": counter_after}],
        "node_counter_delta": [{"engine_calls": len(generated)}],
        "oracle_comparison": {
            "prompt_exact": True,
            "rendered_prompt_exact": True,
            "token_limit_exact": True,
            "generated_exact": True,
            "stop_reason_exact": True,
            "oracle_generated_token_count": len(generated),
        },
        "outcome": outcome,
        "raw_decoded_text": raw_decoded_text,
        "visible_text": visible_text,
        "thinking_text": thinking_text,
        "parsed": parsed,
    }
    if observation is not None:
        record["observation"] = observation
    return record


def _valid_output_artifact() -> tuple[dict[str, Any], dict[str, str]]:
    profile = runner.TARGET_PROFILES[("qwen3-8b", "hbm_sram")]
    assert profile.oracle_sha256 is not None
    source_identity = runner.source_sha256(profile.backend, profile.model_id)
    checkpoint_files = {
        name: _artifact_file_identity(
            f"checkpoint/{name}", sha256=digest, byte_count=size
        )
        for name, size, digest in profile.checkpoint_files
    }
    tokenizer_files = {
        name: copy.deepcopy(checkpoint_files[name])
        for name in (
            "tokenizer.json",
            "tokenizer_config.json",
            "generation_config.json",
        )
    }
    implementation_identity = {
        "backend": "numpy",
        "library": "numpy",
        "library_version": "2.0.0",
        "device": "host",
        "device_name": "test-host",
        "blas": {"name": "test-blas", "version": "1.0"},
        "flags": {
            "allow_tf32": False,
            "float32_matmul_precision": "highest",
            "OMP_NUM_THREADS": "8",
            "OPENBLAS_NUM_THREADS": "8",
            "MKL_NUM_THREADS": "8",
            "VECLIB_MAXIMUM_THREADS": "",
            "NUMEXPR_NUM_THREADS": "",
        },
        "blocked_association": "test blocked binary32 association",
    }
    association: dict[str, Any] = {
        "schema": "opentallas.abi3.executed_association.v1",
        "association_policy": "implementation_and_executed_shape_pinned",
        "implementation_identity": copy.deepcopy(implementation_identity),
        "entries": [
            {
                "numeric_contract": "bf16_bf16_fp32_blocked_rne_v1",
                "activation_shape": [1, 8],
                "weight_shape": [16, 8],
                "output_shape": [1, 16],
                "call_count": 4,
            }
        ],
        "distinct_association_count": 1,
        "blocked_call_count": 4,
    }
    association["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            association,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()

    observation_result = CommandResult(
        command=AWK_COMMAND,
        exit_code=0,
        stdout="239\n",
        stderr="",
        timed_out=False,
        truncated=False,
    )
    observation = observation_result.to_dict()
    initial_rendered = "<|im_start|>user\nTotal inventory.txt.<|im_end|>"
    followup_rendered = initial_rendered + "\n" + observation_result.rendered()
    eos_token = profile.eos_token_ids[0]
    turns = [
        _artifact_turn(
            index=0,
            prompt=[101, 102],
            rendered=initial_rendered,
            generated=[103, eos_token],
            outcome="executed",
            parsed={"kind": "command", "command": AWK_COMMAND, "answer": None},
            raw_decoded_text=(
                f"<think>Total the inventory.</think>\n\n```bash\n{AWK_COMMAND}\n```"
            ),
            visible_text=f"```bash\n{AWK_COMMAND}\n```",
            thinking_text="Total the inventory.",
            observation=observation,
        ),
        _artifact_turn(
            index=1,
            prompt=[101, 102, 104],
            rendered=followup_rendered,
            generated=[105, eos_token],
            outcome="answered",
            parsed={"kind": "answer", "command": None, "answer": "239"},
            raw_decoded_text="ANSWER: 239",
            visible_text="ANSWER: 239",
            thinking_text=None,
        ),
    ]
    generation_policy = {
        "counter_class_id": 1,
        "eos_count": len(profile.eos_token_ids),
        "eos_token_0": profile.eos_token_ids[0],
        "eos_token_1": profile.eos_token_ids[1],
        "eos_token_2": 0,
        "eos_token_3": 0,
        "eos_token_4": 0,
        "eos_token_5": 0,
        "eos_token_6": 0,
        "eos_token_7": 0,
        "max_new_tokens": 8,
        "rng_seed_hi": 0,
        "rng_seed_lo": 0,
        "selection_mode": 0,
        "tie_rule": 0,
        "token_ring_object_id": 7,
        "vocabulary_size": profile.vocabulary_size,
    }
    deployment_digest = _text_sha256("deployment")
    body: dict[str, Any] = {
        "schema": runner.SCHEMA,
        "status": "pass",
        "evidence_class": runner.EVIDENCE_CLASS,
        "not_a_claim": list(runner.NOT_A_CLAIMS),
        "tool": "tools/run_abi3_agent_episode.py",
        "target_profile": {
            "profile_id": profile.profile_id,
            "expected_kernel_ir_sha256": profile.kernel_ir_sha256,
            "expected_capability_sha256": profile.capability_sha256,
            "expected_reference_sha256": profile.oracle_sha256,
        },
        "backend": profile.backend,
        "model": {
            "model_id": profile.model_id,
            "graph_id": profile.graph_id,
            "numeric_profile": profile.numeric_profile,
        },
        "target": {
            "target_id": profile.target_id,
            "backend": profile.deployment_backend,
            "topology_class": profile.topology_class,
            "node_count": profile.node_count,
            "capability": "capabilities/hbm_sram.json",
            "capability_digest": profile.capability_sha256,
            "deployment_digest": deployment_digest,
            "technology_view": "functional_simulation",
        },
        "workload": {
            "workload_id": profile.workload_id,
            "workload_digest": profile.workload_digest,
            "kind": "agent",
            "prompt_token_ids": turns[0]["prompt_token_ids"],
            "prompt_token_count": turns[0]["prompt_token_count"],
            "rendered_text_sha256": turns[0]["rendered_prompt_sha256"],
            "max_new_tokens_per_turn": 8,
            "max_turns": 2,
            "session_context_capacity": 32,
            "tokenizer_sha256": profile.tokenizer_sha256,
        },
        "command_policy": runner.command_policy_evidence(),
        "generation_policy": generation_policy,
        "generation_policy_digest": runner.digest_of(generation_policy),
        "verification": {
            "admitted": True,
            "instruction_count": 2,
            "descriptor_count": 2,
            "proved_retired_work": 200,
            "declared_retired_work": 200,
            "loop_depth": 1,
            "event_count": 0,
            "state_resources": 1,
            "checks": {"admission": True},
            "errors": [],
            "warnings": [],
        },
        "engine_coverage": {
            "implemented_count": 12,
            "missing_count": 0,
            "missing": [],
        },
        "implementation_identity": implementation_identity,
        "executed_association": association,
        "inputs": {
            "kernel_ir": _artifact_file_identity(
                "artifacts/kernel_ir.json", sha256=profile.kernel_ir_sha256
            ),
            "capability": _artifact_file_identity(
                "capabilities/hbm_sram.json", sha256=profile.capability_sha256
            ),
            "workload": {
                **_artifact_file_identity(
                    "workloads/qwen-agent.json", sha256=profile.workload_sha256
                ),
                "declared_workload_digest": profile.workload_digest,
                "prompt_token_ids_sha256": runner.digest_of(
                    turns[0]["prompt_token_ids"]
                ),
            },
            "workload_index": _artifact_file_identity(
                "workloads/index.json", sha256=profile.workload_index_sha256
            ),
            "reference": _artifact_file_identity(
                "reference/qwen-agent.json", sha256=profile.oracle_sha256
            ),
            "tokenizer_files": tokenizer_files,
            "checkpoint_root": {
                "path": "checkpoint",
                "kind": "read_only_directory",
                "content_binding": (
                    "authenticated deployment object segment SHA-256 values"
                ),
                "deployment_digest_binding": deployment_digest,
                "identity": {
                    "source": _artifact_file_identity(
                        "compiler/models/qwen3-8b/checkpoint_source.json",
                        sha256=profile.checkpoint_source_sha256,
                    ),
                    "files": checkpoint_files,
                },
            },
            "published_deployment": {
                "path": "publication",
                "manifest": _artifact_file_identity("publication/deployment.json"),
                "descriptors": _artifact_file_identity("publication/descriptors.bin"),
                "program": _artifact_file_identity("publication/program.bin"),
            },
        },
        "source_sha256": source_identity,
        "reference": {
            "artifact": "reference/qwen-agent.json",
            "artifact_sha256": profile.oracle_sha256,
            "schema": runner.ORACLE_SCHEMA,
            "evidence_class": "external_reference_comparator",
            "workload_digest": profile.workload_digest,
            "oracle_turn_count": 2,
            "note": "Used only for exact post-generation comparison.",
        },
        "oracle_agreement": True,
        "expected_total": profile.expected_total,
        "answer": str(profile.expected_total),
        "task_solved": True,
        "stop_reason": "answered",
        "turns": turns,
        "turn_count": len(turns),
        "executed_command_count": 1,
        "problems": [],
        "counters": {"transactions": 4},
        "counter_scope": {
            "aggregate": "cluster_total",
            "per_node": "engine_work_by_node_id",
            "node_count": profile.node_count,
            "node_counters_index": "NODE_ID",
            "reconciliation": (
                "cluster total equals per-node engine work plus cluster-only "
                "LINK, STATE, control, and host bookkeeping"
            ),
        },
        "node_counters": [{"engine_calls": 4}],
        "lowering_seconds": 0.5,
        "wall_seconds": 1.0,
        "note": "Source-bound functional closed-loop evidence.",
    }
    return body, dict(source_identity)


@dataclass(frozen=True)
class _OutputArtifactCase:
    body: dict[str, Any]
    source_sha256: dict[str, str]
    validator: Any


@pytest.fixture(scope="module")
def output_artifact_case() -> _OutputArtifactCase:
    body, source_identity = _valid_output_artifact()
    validator = runner.load_output_validator()
    runner.validate_output_artifact(
        body,
        validator=validator,
        expected_source_sha256=source_identity,
    )
    return _OutputArtifactCase(body, source_identity, validator)


def _validate_artifact(body: Mapping[str, Any], case: _OutputArtifactCase) -> None:
    runner.validate_output_artifact(
        body,
        validator=case.validator,
        expected_source_sha256=case.source_sha256,
    )


def _artifact_member(
    body: dict[str, Any], path: Sequence[str | int]
) -> tuple[Any, str | int]:
    parent: Any = body
    for member in path[:-1]:
        parent = parent[member]
    return parent, path[-1]


def test_complete_output_artifact_is_schema_and_semantically_valid(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    _validate_artifact(case.body, case)
    observation = case.body["turns"][0]["observation"]
    rendered = case.body["turns"][1]["rendered_prompt_text"]
    assert CommandResult(**observation).rendered() in rendered
    assert _text_sha256(rendered) == case.body["turns"][1]["rendered_prompt_sha256"]


def _replace_implementation_identity(body: dict[str, Any], backend: str) -> None:
    if backend == "numpy":
        identity = copy.deepcopy(body["implementation_identity"])
    else:
        identity = {
            "backend": backend,
            "library": "torch",
            "library_version": "2.10.0",
            "device": "cpu" if backend == "torch_cpu" else "cuda:0",
            "device_name": "test-device",
            "flags": {
                "float32_matmul_precision": "highest",
                "cublas_workspace_config": ":4096:8",
                "torch.backends.cuda.matmul.allow_tf32": False,
                "torch.backends.cudnn.allow_tf32": False,
                "torch_num_threads": 8,
                "torch_num_interop_threads": 2,
            },
            "blocked_association": "test torch binary32 association",
        }
        if backend == "torch_cuda":
            identity.update(
                {
                    "cuda_version": "12.8",
                    "compute_capability": "9.0",
                    "device_memory_bytes": {"free": 1024, "total": 2048},
                }
            )
    body["implementation_identity"] = identity
    association = body["executed_association"]
    association_identity = copy.deepcopy(identity)
    association_identity.pop("device_memory_bytes", None)
    association["implementation_identity"] = association_identity
    unsigned = {
        key: value for key, value in association.items() if key != "manifest_sha256"
    }
    association["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()


@pytest.mark.parametrize("backend", ["numpy", "torch_cpu", "torch_cuda"])
def test_output_schema_is_numeric_backend_neutral(
    output_artifact_case: _OutputArtifactCase, backend: str
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    _replace_implementation_identity(body, backend)
    _validate_artifact(body, case)


@pytest.mark.parametrize("backend", ["numpy", "torch_cpu", "torch_cuda"])
def test_output_validation_refuses_mixed_implementation_identity_shapes(
    output_artifact_case: _OutputArtifactCase, backend: str
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    _replace_implementation_identity(body, backend)
    identity = body["implementation_identity"]
    if backend == "numpy":
        del identity["blas"]
    elif backend == "torch_cpu":
        identity["blas"] = {"name": "wrong", "version": "1"}
    else:
        del identity["device_memory_bytes"]
    association_identity = copy.deepcopy(identity)
    association_identity.pop("device_memory_bytes", None)
    body["executed_association"]["implementation_identity"] = association_identity
    with pytest.raises(
        runner.EpisodeRefusal, match="implementation backend-specific fields"
    ):
        _validate_artifact(body, case)


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        pytest.param(
            {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": 7},
            "output JSON Schema is invalid",
            id="invalid-meta-schema",
        ),
        pytest.param(
            {"$schema": "http://json-schema.org/draft-07/schema#"},
            "Draft 2020-12",
            id="wrong-draft",
        ),
    ],
)
def test_output_schema_loader_requires_valid_draft_2020_12(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema: dict[str, Any],
    message: str,
) -> None:
    path = tmp_path / "schema.json"
    _write_json(path, schema)
    monkeypatch.setattr(runner, "OUTPUT_SCHEMA_PATH", path)
    with pytest.raises(runner.EpisodeRefusal, match=message):
        runner.load_output_validator()


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(("schema",), id="top-level"),
        pytest.param(("target", "target_id"), id="nested"),
        pytest.param(("turns", 1, "rendered_prompt_text"), id="retained-rendered-text"),
    ],
)
def test_output_schema_refuses_missing_required_members(
    output_artifact_case: _OutputArtifactCase, path: tuple[str | int, ...]
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    parent, member = _artifact_member(body, path)
    del parent[member]
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param((), id="top-level"),
        pytest.param(("target",), id="nested"),
        pytest.param(("turns", 0), id="turn"),
    ],
)
def test_output_schema_refuses_extra_members(
    output_artifact_case: _OutputArtifactCase, path: tuple[str | int, ...]
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    target: Any = body
    for member in path:
        target = target[member]
    target["unreviewed"] = True
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


def test_output_schema_refuses_wrong_evidence_class(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    body["evidence_class"] = "performance_evidence"
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(("target", "topology_class"), id="topology-class"),
        pytest.param(("target", "node_count"), id="node-count"),
        pytest.param(("turns", 0, "turn"), id="turn-index"),
        pytest.param(("turn_count",), id="turn-count"),
        pytest.param(
            ("turns", 0, "observation", "exit_code"), id="observation-exit-code"
        ),
        pytest.param(("inputs", "kernel_ir", "bytes"), id="input-byte-count"),
        pytest.param(
            ("inputs", "checkpoint_root", "identity", "source", "bytes"),
            id="checkpoint-source-byte-count",
        ),
    ],
)
def test_output_schema_refuses_boolean_where_integer_is_required(
    output_artifact_case: _OutputArtifactCase, path: tuple[str | int, ...]
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    parent, member = _artifact_member(body, path)
    parent[member] = True
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


def test_output_schema_refuses_wrong_turn_shape(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    body["turns"][0]["outcome"] = "oracle_prompt_divergence"
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong-type"])
def test_invalid_output_is_never_created_or_replaced(
    output_artifact_case: _OutputArtifactCase,
    tmp_path: Path,
    mutation: str,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    if mutation == "missing":
        del body["target"]["target_id"]
    elif mutation == "extra":
        body["turns"][0]["unreviewed"] = True
    else:
        body["turns"][0]["prompt_token_count"] = "two"

    output = tmp_path / "existing.json"
    output.write_bytes(b"previous artifact")
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        runner.write_validated_output(
            body,
            output=output,
            validator=case.validator,
            expected_source_sha256=case.source_sha256,
        )
    assert output.read_bytes() == b"previous artifact"


def test_validated_output_is_canonical_json(
    output_artifact_case: _OutputArtifactCase, tmp_path: Path
) -> None:
    case = output_artifact_case
    output = tmp_path / "new" / "artifact.json"
    runner.write_validated_output(
        case.body,
        output=output,
        validator=case.validator,
        expected_source_sha256=case.source_sha256,
    )
    assert output.read_bytes() == runner.canonical_json(case.body)


def test_driver_failure_turn_is_a_publishable_failed_artifact(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    turn = body["turns"][0]
    for name in (
        "observation",
        "parsed",
        "raw_decoded_text",
        "thinking_text",
        "visible_text",
    ):
        del turn[name]
    turn.update(
        {
            "outcome": "invalid_execution_evidence",
            "generated_token_ids": [],
            "generated_token_count": 0,
            "stop_reason": "failed",
            "eos_token_id": None,
            "failure": "prefill failed: test fault",
            "token_legitimacy_problems": [
                "per_step evidence does not contain exactly one row per token",
                "prefill failed: test fault",
            ],
            "transactions": 1,
            "decode_steps": 0,
            "driver_counters": {"transactions": 1},
            "counters_after": {"transactions": 1},
            "counter_delta": {"transactions": 1},
            "node_counters_after": [{"engine_calls": 1}],
            "node_counter_delta": [{"engine_calls": 1}],
            "oracle_comparison": {
                "prompt_exact": True,
                "rendered_prompt_exact": True,
                "token_limit_exact": True,
                "generated_exact": False,
                "stop_reason_exact": False,
                "oracle_generated_token_count": 2,
            },
        }
    )
    step = turn["per_step"][0]
    turn["per_step"] = [
        {
            **step,
            "status": "FAULT",
            "trap": "ENGINE",
            "produced_tokens": [],
            "final_token_id": None,
            "eos_reason": 0,
        }
    ]
    body.update(
        {
            "status": "failed",
            "oracle_agreement": False,
            "answer": None,
            "task_solved": False,
            "stop_reason": "failed",
            "turns": [turn],
            "turn_count": 1,
            "executed_command_count": 0,
            "problems": ["turn 0: prefill failed: test fault"],
            "counters": {"transactions": 1},
            "node_counters": [{"engine_calls": 1}],
        }
    )
    _validate_artifact(body, case)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong-type"])
def test_output_schema_refuses_invalid_observation_placement_or_type(
    output_artifact_case: _OutputArtifactCase, mutation: str
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    if mutation == "missing":
        del body["turns"][0]["observation"]
    elif mutation == "extra":
        body["turns"][1]["observation"] = copy.deepcopy(body["turns"][0]["observation"])
    else:
        body["turns"][0]["observation"] = "not an observation"
    with pytest.raises(runner.EpisodeRefusal, match="output schema violation"):
        _validate_artifact(body, case)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong"])
def test_output_validation_refuses_inexact_source_hash_map(
    output_artifact_case: _OutputArtifactCase, mutation: str
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    first = next(iter(body["source_sha256"]))
    if mutation == "missing":
        del body["source_sha256"][first]
    elif mutation == "extra":
        body["source_sha256"]["unreviewed.py"] = "0" * 64
    else:
        body["source_sha256"][first] = "0" * 64
    with pytest.raises(runner.EpisodeRefusal, match="functional source map"):
        _validate_artifact(body, case)


def test_output_validation_refuses_rendered_prompt_hash_mismatch(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    body["turns"][1]["rendered_prompt_text"] += "\nmutation"
    with pytest.raises(runner.EpisodeRefusal, match="rendered prompt identity"):
        _validate_artifact(body, case)


def test_output_validation_refuses_node_counter_count_mismatch(
    output_artifact_case: _OutputArtifactCase,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    body["turns"][0]["node_counters_after"].append({"engine_calls": 1})
    with pytest.raises(runner.EpisodeRefusal, match="node_counters_after count"):
        _validate_artifact(body, case)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        pytest.param(
            ("target_profile", "profile_id"), "unreviewed_profile", id="profile"
        ),
        pytest.param(("target", "target_id"), "unreviewed_target", id="target"),
    ],
)
def test_output_validation_refuses_wrong_target_or_profile_binding(
    output_artifact_case: _OutputArtifactCase,
    path: tuple[str | int, ...],
    replacement: str,
) -> None:
    case = output_artifact_case
    body = copy.deepcopy(case.body)
    parent, member = _artifact_member(body, path)
    parent[member] = replacement
    with pytest.raises(runner.EpisodeRefusal, match="not bound to its source value"):
        _validate_artifact(body, case)


def test_file_mutation_after_identity_capture_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(b"before")
    identity = runner.file_identity(path)
    path.write_bytes(b"after")
    with pytest.raises(runner.EpisodeRefusal, match="changed"):
        runner.require_unchanged_file(path, identity, "test input")


# ---------------------------------------------------------------------------
# Checkpoint/publication/output separation and CLI import safety
# ---------------------------------------------------------------------------


def test_checkpoint_and_publication_overlap_is_refused_both_directions(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    with pytest.raises(runner.EpisodeRefusal, match="checkpoint"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=checkpoint / "publication",
            output=tmp_path / "out.json",
            force=False,
        )

    publication = tmp_path / "publication"
    nested_checkpoint = publication / "checkpoint"
    nested_checkpoint.mkdir(parents=True)
    with pytest.raises(runner.EpisodeRefusal, match="contain the checkpoint"):
        runner.validate_output_boundaries(
            checkpoint=nested_checkpoint,
            publish=publication,
            output=tmp_path / "out.json",
            force=False,
        )


def test_output_must_be_separate_from_checkpoint_and_publication(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    publication = tmp_path / "publication"
    for output in (checkpoint / "out.json", publication / "out.json"):
        with pytest.raises(runner.EpisodeRefusal, match="--output"):
            runner.validate_output_boundaries(
                checkpoint=checkpoint,
                publish=publication,
                output=output,
                force=False,
            )
    output_root = tmp_path / "output-root"
    with pytest.raises(runner.EpisodeRefusal, match="--publish"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=output_root / "publication",
            output=output_root,
            force=False,
        )


def test_existing_publication_or_output_requires_force(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    publication = tmp_path / "publication"
    publication.mkdir()
    with pytest.raises(runner.EpisodeRefusal, match="pass --force"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication,
            output=tmp_path / "out.json",
            force=False,
        )

    publication.rmdir()
    output = tmp_path / "out.json"
    output.write_text("old", encoding="utf-8")
    with pytest.raises(runner.EpisodeRefusal, match="pass --force"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication,
            output=output,
            force=False,
        )


def test_force_refuses_unrelated_or_nonfile_publication_members(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    publication = tmp_path / "publication"
    publication.mkdir()
    (publication / "unrelated.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(runner.EpisodeRefusal, match="unrelated entries"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication,
            output=tmp_path / "out.json",
            force=True,
        )

    (publication / "unrelated.txt").unlink()
    (publication / "deployment.json").mkdir()
    with pytest.raises(runner.EpisodeRefusal, match="is not a file"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication,
            output=tmp_path / "out.json",
            force=True,
        )


def test_force_accepts_only_previous_deployment_files_and_regular_output(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    publication = tmp_path / "publication"
    publication.mkdir()
    for name in ("deployment.json", "descriptors.bin", "program.bin"):
        (publication / name).write_bytes(b"old")
    output = tmp_path / "out.json"
    output.write_text("old", encoding="utf-8")
    runner.validate_output_boundaries(
        checkpoint=checkpoint,
        publish=publication,
        output=output,
        force=True,
    )


def test_force_refuses_directory_at_output_path(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    output = tmp_path / "out.json"
    output.mkdir()
    with pytest.raises(runner.EpisodeRefusal, match="regular file"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=tmp_path / "publication",
            output=output,
            force=True,
        )


def test_force_refuses_symbolic_link_outputs_and_publication_members(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    publication_target = tmp_path / "publication-target"
    publication_target.mkdir()
    publication_link = tmp_path / "publication-link"
    publication_link.symlink_to(publication_target, target_is_directory=True)
    with pytest.raises(runner.EpisodeRefusal, match="symbolic link"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication_link,
            output=tmp_path / "out.json",
            force=True,
        )

    output_target = tmp_path / "old-output.json"
    output_target.write_text("old", encoding="utf-8")
    output_link = tmp_path / "output-link.json"
    output_link.symlink_to(output_target)
    with pytest.raises(runner.EpisodeRefusal, match="symbolic link"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=tmp_path / "publication",
            output=output_link,
            force=True,
        )

    publication = tmp_path / "publication"
    publication.mkdir()
    (publication / "deployment.json").symlink_to(output_target)
    with pytest.raises(runner.EpisodeRefusal, match="symbolic link"):
        runner.validate_output_boundaries(
            checkpoint=checkpoint,
            publish=publication,
            output=tmp_path / "fresh-output.json",
            force=True,
        )


def test_cli_help_succeeds_without_loading_a_model_or_tokenizer() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/run_abi3_agent_episode.py"), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--checkpoint" in completed.stdout
    assert "--publish" in completed.stdout
    assert "--expected-reference-sha256" in completed.stdout
