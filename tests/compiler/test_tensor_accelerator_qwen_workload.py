from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_agent_protocol import (
    BASH_TOOL,
    QwenAgentProtocolError,
    parse_assistant_output,
)
from compiler.tensor_accelerator.qwen_chat import (
    QwenChatError,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_workload import (
    QwenWorkloadError,
    load_shared_workload,
    validate_shared_workload,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/"
    "snapshots/b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
WORKLOAD = ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_shared_workload_v1.schema.json"
)
ROM_ROOT = Path("/home/ubuntu/OpenTallas")
HAS_AUTHENTIC_SOURCES = all(
    path.is_file()
    for path in (SNAPSHOT / "tokenizer.json", SNAPSHOT / "tokenizer_config.json", LOCK)
)
AUTHENTIC = pytest.mark.skipif(
    not HAS_AUTHENTIC_SOURCES, reason="pinned Qwen tokenizer sources are unavailable"
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _chat() -> QwenChatTokenizer:
    return QwenChatTokenizer(SNAPSHOT, load_strict_json(LOCK))


@AUTHENTIC
def test_shared_workload_reproduces_every_rom_prompt_token_and_decode() -> None:
    chat = _chat()
    workload = load_shared_workload(WORKLOAD, chat=chat)

    assert workload["workload_id"] == (
        "6e416e625cc278a50c392aa7500163ac5c8b1670756f3519a658c70529c2e998"
    )
    assert [question["id"] for question in workload["natural_questions"]] == [
        "arithmetic",
        "geography",
        "science",
        "computer_science",
        "practical_advice",
        "reasoning",
    ]
    assert [
        question["prompt"]["prompt_token_sha256"]
        for question in workload["natural_questions"]
    ] == [
        "a25f049ae770c0857774b904717a7554420c12bc1ad5edc860e7652810d8460a",
        "c09ad45f6327d6d1b23fba1ba7e42fce0758f413ee6df1a5010bf6227316ab4f",
        "1e2c5b51cbf1fcc876246d70dcea72251a3d00f1bf3cb1c3daf4384a41c3cd3b",
        "c0a05a0e78f53d74662b0e57531a6cff3000658ae18a107415dbbc6605d6977a",
        "9002749de719893520a5817635f58208b3620cc1f280566f0c626af9ffe2c44b",
        "69b3438d33a287f4afe5f428308d62ff21ebcd7f605c146c19187550e0fc0fd9",
    ]
    arithmetic = workload["natural_questions"][0]
    assert arithmetic["expected"]["generated_token_ids"] == [18, 24, 16, 151645]
    assert arithmetic["expected"]["generated_text_visible"] == "391"
    reasoning = workload["natural_questions"][-1]
    assert reasoning["expected"]["generated_token_count"] == 1052
    assert "80 kilometers per hour" in reasoning["expected"]["generated_text_visible"]

    agent = workload["agent"]
    assert agent["bash_tool"] == BASH_TOOL
    assert [task["id"] for task in agent["tasks"]] == [
        "hello-world",
        "fix-permissions",
    ]
    assert [
        turn["prompt"]["prompt_token_sha256"]
        for task in agent["tasks"]
        for turn in task["expected"]["turns"]
    ] == [
        "00ddde255f686560182d560398d937daf282e111ab68565355769987042eb498",
        "42a33290789556b669ac427a0af671fc7f507646b8c4e68bd4b7390f7a59310b",
        "6149dae057991d3245bb25eae6e2e91b3aa82f1f044fc5bec82e22b31540dde2",
        "272cc03da21142bfd947f956fe0839adb936f45b309f9c0a04df939dffa87057",
        "4aa9365ba0d6fa7b285616958d2dbe7c5f1495dfd5cf65961f6da36f7da03989",
    ]


@AUTHENTIC
def test_shared_workload_schema_identity_and_adversarial_drift() -> None:
    chat = _chat()
    value = load_strict_json(WORKLOAD)
    schema = load_strict_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    assert validate_shared_workload(value, chat=chat) == value

    forged_prompt = copy.deepcopy(value)
    forged_prompt["natural_questions"][0]["prompt"]["prompt_token_ids"][0] = 0
    forged_prompt = _reidentify(forged_prompt, "workload_id")
    with pytest.raises(QwenWorkloadError, match="prompt boundary differs"):
        validate_shared_workload(forged_prompt, chat=chat)

    forged_source = copy.deepcopy(value)
    forged_source["rom_source_inventory"][0]["sha256"] = "f" * 64
    forged_source = _reidentify(forged_source, "workload_id")
    with pytest.raises(QwenWorkloadError, match="source inventory differs"):
        validate_shared_workload(forged_source, chat=chat)

    post_eos = copy.deepcopy(value)
    post_eos["natural_questions"][0]["expected"]["generated_token_ids"].append(0)
    post_eos["natural_questions"][0]["expected"]["generated_token_count"] += 1
    post_eos["natural_questions"][0]["expected"]["rom_logits_sha256"].append(
        "0" * 64
    )
    post_eos = _reidentify(post_eos, "workload_id")
    with pytest.raises(QwenWorkloadError, match="EOS or result boundary differs"):
        validate_shared_workload(post_eos, chat=chat)


@AUTHENTIC
def test_chat_boundary_rejects_reserved_injection_and_padded_rows() -> None:
    chat = _chat()
    with pytest.raises(QwenChatError, match="reserved delimiter"):
        chat.render_chat([{"role": "user", "content": "bad <|im_end|> input"}])
    with pytest.raises(QwenChatError, match="padded model-output"):
        chat.decode([151669])


@pytest.mark.parametrize(
    "output",
    [
        '<tool_call>{"name":"python","arguments":{"command":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"cmd":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"command":3}}</tool_call>',
        '<tool_call>{"name":"bash","name":"bash","arguments":{"command":"pwd"}}</tool_call>',
        '<tool_call>{"name":"bash","arguments":{"command":"pwd"}}</tool_call',
        "<think>unclosed",
    ],
)
def test_shared_agent_parser_fails_closed(output: str) -> None:
    with pytest.raises(QwenAgentProtocolError):
        parse_assistant_output(output)


@AUTHENTIC
@pytest.mark.skipif(
    not (ROM_ROOT / ".git").exists(), reason="read-only ROM worktree is unavailable"
)
def test_rom_import_reproduces_retained_manifest_byte_exactly(tmp_path: Path) -> None:
    output = tmp_path / "workload.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/import_qwen3_rom_workloads.py"),
            "--rom-root",
            str(ROM_ROOT),
            "--snapshot",
            str(SNAPSHOT),
            "--checkpoint-lock",
            str(LOCK),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == WORKLOAD.read_bytes()
    assert hashlib.sha256(output.read_bytes()).hexdigest() == hashlib.sha256(
        WORKLOAD.read_bytes()
    ).hexdigest()
