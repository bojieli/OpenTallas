#!/usr/bin/env python3
"""Run a bash-only Qwen3 agent against pinned, isolated TerminalBench tasks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence
import uuid

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.ir.model import canonical_json_bytes, load_strict_json  # noqa: E402
from compiler.qwen3.constants import SCHEMA_DIR, TARGET_CONTEXT_TOKENS  # noqa: E402
from compiler.qwen3.runtime import Qwen3ServiceEngine  # noqa: E402
from compiler.qwen3.tokenizer import Qwen3Tokenizer  # noqa: E402


SUITE_SCHEMA = "opentallas.qwen3.terminalbench_task_suite.v1"
CAMPAIGN_SCHEMA = "opentallas.qwen3.terminalbench_agent_campaign.v1"
EOS_TOKEN_IDS = (151645, 151643)
STREAM_LIMIT = 4096
TEST_STREAM_LIMIT = 16384
SYSTEM_PROMPT = (
    "You are a terminal task agent working inside an isolated container. Use the "
    "bash tool to inspect and modify only that container. When using a tool, emit "
    "only the official <tool_call> block. Verify your work with bash, then give a "
    "concise final answer."
)
BASH_TOOL: dict[str, Any] = {
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
_TOOL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_THINK_BLOCK = re.compile(r"^\s*<think>\s*(.*?)\s*</think>\s*", re.DOTALL)


class AgentProtocolError(ValueError):
    """Raised when model output does not obey the pinned tool protocol."""


class CampaignError(RuntimeError):
    """Raised when a campaign prerequisite or isolation invariant fails."""


@dataclass(frozen=True)
class ParsedAssistantOutput:
    reasoning: str
    content: str
    calls: tuple[dict[str, Any], ...]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the compiled Qwen3-8B as a bash-only TerminalBench agent"
    )
    result.add_argument("--deployment", required=True, type=Path)
    result.add_argument("--suite", required=True, type=Path)
    result.add_argument("--terminalbench-repo", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--device", default="cuda")
    result.add_argument(
        "--attention-backend", choices=("sdpa", "eager"), default="sdpa"
    )
    result.add_argument("--command-timeout-seconds", type=int, default=30)
    result.add_argument("--build-timeout-seconds", type=int, default=900)
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], identity: str) -> str:
    body = {key: item for key, item in value.items() if key != identity}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _schema(name: str) -> dict[str, Any]:
    value = load_strict_json(SCHEMA_DIR / name)
    Draft202012Validator.check_schema(value)
    return value


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def _strict_json(text: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AgentProtocolError(f"duplicate JSON field {key!r}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise AgentProtocolError(f"non-finite JSON value {token!r}")

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except AgentProtocolError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise AgentProtocolError(f"tool call is not strict JSON: {exc}") from exc


def _without_terminal_token(text: str) -> str:
    result = text
    for token in ("<|im_end|>", "<|endoftext|>"):
        if result.endswith(token):
            result = result[: -len(token)]
            break
    return result.rstrip()


def parse_assistant_output(text: str) -> ParsedAssistantOutput:
    """Parse Qwen3's official tool-call envelope and fail closed on ambiguity."""

    if not isinstance(text, str):
        raise AgentProtocolError("assistant output must be text")
    remainder = _without_terminal_token(text)
    reasoning = ""
    think = _THINK_BLOCK.match(remainder)
    if think is not None:
        reasoning = think.group(1).strip()
        remainder = remainder[think.end() :]
    elif "<think>" in remainder or "</think>" in remainder:
        raise AgentProtocolError("assistant output has a malformed think block")

    blocks = list(_TOOL_BLOCK.finditer(remainder))
    if remainder.count("<tool_call>") != len(blocks) or remainder.count(
        "</tool_call>"
    ) != len(blocks):
        raise AgentProtocolError("assistant output has a malformed tool-call envelope")
    if not blocks:
        if "<tool_call" in remainder or "</tool_call" in remainder:
            raise AgentProtocolError("assistant output has an incomplete tool call")
        return ParsedAssistantOutput(reasoning, remainder.strip(), ())

    calls: list[dict[str, Any]] = []
    cursor = 0
    content_parts: list[str] = []
    for block in blocks:
        content_parts.append(remainder[cursor : block.start()])
        cursor = block.end()
        value = _strict_json(block.group(1))
        if not isinstance(value, dict) or set(value) != {"name", "arguments"}:
            raise AgentProtocolError(
                "tool call must contain exactly name and arguments"
            )
        if value["name"] != "bash":
            raise AgentProtocolError("only the bash tool is available")
        arguments = value["arguments"]
        if not isinstance(arguments, dict) or set(arguments) != {"command"}:
            raise AgentProtocolError(
                "bash arguments must contain exactly the command field"
            )
        command = arguments["command"]
        if (
            not isinstance(command, str)
            or not command.strip()
            or "\x00" in command
            or len(command) > 8192
        ):
            raise AgentProtocolError("bash command must be nonempty bounded text")
        calls.append({"name": "bash", "arguments": {"command": command}})
    content_parts.append(remainder[cursor:])
    content = "".join(content_parts).strip()
    if "<tool_call" in content or "</tool_call" in content:
        raise AgentProtocolError("assistant output has nested tool-call markup")
    return ParsedAssistantOutput(reasoning, content, tuple(calls))


def _run(
    command: Sequence[str],
    *,
    timeout: int,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignError(f"command failed: {command[0]}: {exc}") from exc


def _require_success(
    command: Sequence[str],
    *,
    timeout: int,
    cwd: Path | None = None,
) -> str:
    result = _run(command, timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-4000:]
        raise CampaignError(
            f"command {command[0]!r} exited {result.returncode}: {detail}"
        )
    return result.stdout.strip()


def docker_run_arguments(container: str, image: str) -> list[str]:
    """Return the fixed isolation boundary used for every agent container."""

    return [
        "docker",
        "run",
        "--detach",
        "--name",
        container,
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "128",
        "--memory",
        "2g",
        "--memory-swap",
        "2g",
        "--cpus",
        "2",
        "--ulimit",
        "nofile=1024:1024",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--workdir",
        "/app",
        image,
        "sleep",
        "infinity",
    ]


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = f"\n... truncated {len(text) - limit} characters ...\n"
    retained = max(0, limit - len(marker))
    return text[:retained] + marker, True


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _load_suite(path: Path) -> dict[str, Any]:
    value = load_strict_json(path)
    Draft202012Validator(_schema("terminalbench_task_suite_v1.schema.json")).validate(
        value
    )
    if value["schema"] != SUITE_SCHEMA:
        raise CampaignError("TerminalBench suite schema differs")
    if value["suite_id"] != _body_id(value, "suite_id"):
        raise CampaignError("TerminalBench suite_id does not bind its content")
    identifiers = [task["id"] for task in value["tasks"]]
    if len(identifiers) != len(set(identifiers)):
        raise CampaignError("TerminalBench task identifiers must be unique")
    for task in value["tasks"]:
        paths = [item["path"] for item in task["runtime_files"]]
        if len(paths) != len(set(paths)):
            raise CampaignError(f"task {task['id']} repeats a runtime file")
        for path_text in paths:
            path = PurePosixPath(path_text)
            if path.is_absolute() or ".." in path.parts:
                raise CampaignError(
                    f"task {task['id']} has an unsafe runtime path {path_text!r}"
                )
    return value


def _verify_task_source(repo: Path, task: dict[str, Any]) -> Path:
    root = repo / "original-tasks" / task["id"]
    expected = {
        "Dockerfile": task["dockerfile_sha256"],
        "task.yaml": task["task_yaml_sha256"],
        "tests/test_outputs.py": task["test_sha256"],
        **{item["path"]: item["sha256"] for item in task["runtime_files"]},
    }
    for relative, sha256 in expected.items():
        path = root / relative
        if not path.is_file() or _sha256_file(path) != sha256:
            raise CampaignError(
                f"TerminalBench source differs for {task['id']}/{relative}"
            )
    return root


def _build_task_image(
    repo: Path,
    task: dict[str, Any],
    terminalbench_commit: str,
    *,
    timeout: int,
) -> tuple[str, str]:
    source = _verify_task_source(repo, task)
    tag = f"opentallas-qwen3-tbench:{terminalbench_commit[:12]}-{task['id']}"
    build_root = ROOT / "build"
    build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".qwen3-tbench-{task['id']}-", dir=build_root
    ) as temporary_text:
        temporary = Path(temporary_text)
        shutil.copyfile(source / "Dockerfile", temporary / "Dockerfile")
        for item in task["runtime_files"]:
            destination = temporary / item["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / item["path"], destination)
        result = _run(
            [
                "docker",
                "build",
                "--label",
                f"opentallas.terminalbench.commit={terminalbench_commit}",
                "--label",
                f"opentallas.terminalbench.task={task['id']}",
                "--tag",
                tag,
                ".",
            ],
            timeout=timeout,
            cwd=temporary,
        )
        if result.returncode != 0:
            raise CampaignError(
                f"Docker build failed for {task['id']}: "
                f"{(result.stderr or result.stdout)[-8000:]}"
            )
    image_id = _require_success(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag],
        timeout=30,
    )
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise CampaignError(f"Docker returned an invalid image ID for {task['id']}")
    return tag, image_id


def _inspect_isolation(container: str) -> dict[str, Any]:
    raw = _require_success(["docker", "inspect", container], timeout=30)
    value = _strict_json(raw)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise CampaignError("Docker inspect returned an unexpected document")
    inspected = value[0]
    host = inspected.get("HostConfig")
    mounts = inspected.get("Mounts")
    if not isinstance(host, dict) or not isinstance(mounts, list):
        raise CampaignError("Docker inspect lacks isolation state")
    security = host.get("SecurityOpt") or []
    cap_drop = host.get("CapDrop") or []
    state = {
        "cap_drop_all": "ALL" in cap_drop,
        "host_mounts": any(
            isinstance(item, dict) and item.get("Type") == "bind" for item in mounts
        ),
        "network": host.get("NetworkMode"),
        "no_new_privileges": "no-new-privileges:true" in security,
        "pids_limit": host.get("PidsLimit"),
        "privileged": host.get("Privileged"),
        "read_only_rootfs": host.get("ReadonlyRootfs"),
    }
    expected = {
        "cap_drop_all": True,
        "host_mounts": False,
        "network": "none",
        "no_new_privileges": True,
        "pids_limit": 128,
        "privileged": False,
        "read_only_rootfs": False,
    }
    if state != expected:
        raise CampaignError(f"container isolation differs: {state}")
    return state


def _container_running(container: str) -> bool:
    result = _run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container],
        timeout=30,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _execute_bash(container: str, command: str, *, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "--workdir",
                "/app",
                container,
                "/bin/bash",
                "-lc",
                command,
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = _truncate(_timeout_text(exc.stdout), STREAM_LIMIT)
        stderr, stderr_truncated = _truncate(_timeout_text(exc.stderr), STREAM_LIMIT)
        return {
            "command": command,
            "exit_code": None,
            "stderr": stderr,
            "stdout": stdout,
            "timed_out": True,
            "truncated": stdout_truncated or stderr_truncated,
            "wall_time_seconds": round(time.monotonic() - started, 6),
        }
    except OSError as exc:
        raise CampaignError(f"cannot execute Docker bash tool: {exc}") from exc
    stdout, stdout_truncated = _truncate(result.stdout, STREAM_LIMIT)
    stderr, stderr_truncated = _truncate(result.stderr, STREAM_LIMIT)
    return {
        "command": command,
        "exit_code": result.returncode,
        "stderr": stderr,
        "stdout": stdout,
        "timed_out": False,
        "truncated": stdout_truncated or stderr_truncated,
        "wall_time_seconds": round(time.monotonic() - started, 6),
    }


def _tool_response(action: dict[str, Any]) -> str:
    public = {
        key: action[key]
        for key in ("exit_code", "stderr", "stdout", "timed_out", "truncated")
    }
    return json.dumps(public, sort_keys=True, separators=(",", ":"), allow_nan=False)


_OFFICIAL_TEST_RUNNER = r"""
import importlib.util
import os
from pathlib import Path
import traceback

path = Path("/app/.opentallas-verifier/test_outputs.py")
os.chdir("/app")
spec = importlib.util.spec_from_file_location("terminalbench_official_tests", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load official TerminalBench tests")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tests = [
    (name, value)
    for name, value in vars(module).items()
    if name.startswith("test_") and callable(value)
]
if not tests:
    raise RuntimeError("official TerminalBench test module contains no tests")
failures = 0
for name, test in sorted(tests):
    try:
        test()
    except Exception:
        failures += 1
        print(f"FAILED {name}")
        traceback.print_exc()
    else:
        print(f"PASSED {name}")
print(f"{len(tests) - failures} passed, {failures} failed")
raise SystemExit(1 if failures else 0)
""".strip()


def _verify_official_tests(
    container: str,
    test_path: Path,
    *,
    timeout: int,
) -> dict[str, Any]:
    _require_success(
        [
            "docker",
            "exec",
            container,
            "mkdir",
            "-p",
            "/app/.opentallas-verifier",
        ],
        timeout=30,
    )
    _require_success(
        [
            "docker",
            "cp",
            str(test_path),
            f"{container}:/app/.opentallas-verifier/test_outputs.py",
        ],
        timeout=30,
    )
    result = _run(
        [
            "docker",
            "exec",
            "--workdir",
            "/app",
            container,
            "python3",
            "-c",
            _OFFICIAL_TEST_RUNNER,
        ],
        timeout=timeout,
    )
    stdout, _ = _truncate(result.stdout, TEST_STREAM_LIMIT)
    stderr, _ = _truncate(result.stderr, TEST_STREAM_LIMIT)
    return {"exit_code": result.returncode, "stderr": stderr, "stdout": stdout}


def _assistant_message(parsed: ParsedAssistantOutput) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": parsed.content,
        "reasoning_content": parsed.reasoning,
        "tool_calls": [
            {
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["arguments"],
                },
            }
            for call in parsed.calls
        ],
    }


def _run_agent_task(
    engine: Qwen3ServiceEngine,
    tokenizer: Qwen3Tokenizer,
    task: dict[str, Any],
    image: str,
    image_id: str,
    task_source: Path,
    *,
    maximum_turns: int,
    maximum_new_tokens: int,
    enable_thinking: bool,
    command_timeout: int,
) -> dict[str, Any]:
    started = time.monotonic()
    container = f"opentallas-qwen3-{task['id']}-{uuid.uuid4().hex[:12]}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task["instruction"]},
    ]
    transcript: list[dict[str, Any]] = [
        {"content": SYSTEM_PROMPT, "role": "system", "type": "message"},
        {
            "content": task["instruction"],
            "role": "user",
            "type": "message",
        },
    ]
    command_count = 0
    generated_total = 0
    turn_count = 0
    final_answer: str | None = None
    agent_termination = "maximum_turns"
    isolation: dict[str, Any] | None = None
    try:
        _require_success(docker_run_arguments(container, image), timeout=60)
        isolation = _inspect_isolation(container)
        for turn in range(1, maximum_turns + 1):
            turn_count = turn
            prompt_ids = tokenizer.encode_chat(
                messages,
                tools=[BASH_TOOL],
                enable_thinking=enable_thinking,
            )
            context_capacity = TARGET_CONTEXT_TOKENS - len(prompt_ids) + 1
            effective_maximum = min(maximum_new_tokens, context_capacity)
            if effective_maximum <= 0:
                agent_termination = "context_limit"
                break
            generated_started = time.monotonic()
            generation = engine.generate_greedy(
                prompt_ids,
                max_new_tokens=effective_maximum,
                eos_token_ids=EOS_TOKEN_IDS,
                capture_layer_hashes=False,
            )
            generated_text = tokenizer.decode(
                generation["generated_token_ids"], skip_special_tokens=False
            )
            generated_count = len(generation["generated_token_ids"])
            generated_total += generated_count
            transcript.append(
                {
                    "effective_maximum_new_tokens": effective_maximum,
                    "generated_text": generated_text,
                    "generated_token_count": generated_count,
                    "generated_token_ids": generation["generated_token_ids"],
                    "prompt_token_count": len(prompt_ids),
                    "prompt_token_sha256": hashlib.sha256(
                        canonical_json_bytes(prompt_ids)
                    ).hexdigest(),
                    "result_id": generation["result_id"],
                    "termination": generation["termination"],
                    "turn": turn,
                    "type": "assistant_generation",
                    "wall_time_seconds": round(time.monotonic() - generated_started, 6),
                }
            )
            if generation["termination"] != "eos":
                agent_termination = (
                    "context_limit"
                    if effective_maximum == context_capacity
                    else "length"
                )
                break
            try:
                parsed = parse_assistant_output(generated_text)
            except AgentProtocolError as exc:
                transcript.append(
                    {"error": str(exc), "turn": turn, "type": "protocol_error"}
                )
                agent_termination = "malformed_tool_call"
                break
            messages.append(_assistant_message(parsed))
            if not parsed.calls:
                final_answer = parsed.content
                agent_termination = "eos"
                break
            tool_failed = False
            for call_index, call in enumerate(parsed.calls, start=1):
                command_count += 1
                action = _execute_bash(
                    container,
                    call["arguments"]["command"],
                    timeout=command_timeout,
                )
                action.update(
                    {
                        "call_index": call_index,
                        "turn": turn,
                        "type": "bash_action",
                    }
                )
                transcript.append(action)
                response = _tool_response(action)
                messages.append({"role": "tool", "content": response})
                transcript.append(
                    {
                        "content": response,
                        "role": "tool",
                        "turn": turn,
                        "type": "message",
                    }
                )
                if action["timed_out"] or not _container_running(container):
                    tool_failed = True
                    break
            if tool_failed:
                agent_termination = "tool_error"
                break
        if isolation is None:
            raise CampaignError("container isolation was not inspected")
        if not _container_running(container):
            verification = {
                "exit_code": 125,
                "stderr": "agent container was not running for verification",
                "stdout": "",
            }
        else:
            verification = _verify_official_tests(
                container,
                task_source / "tests/test_outputs.py",
                timeout=180,
            )
        passed = (
            agent_termination == "eos"
            and command_count > 0
            and verification["exit_code"] == 0
        )
        return {
            "agent_termination": agent_termination,
            "command_count": command_count,
            "container_isolation": isolation,
            "final_answer": final_answer,
            "id": task["id"],
            "image_id": image_id,
            "model_generated_tokens": generated_total,
            "passed": passed,
            "task_wall_time_seconds": round(time.monotonic() - started, 6),
            "test_exit_code": verification["exit_code"],
            "test_stderr": verification["stderr"],
            "test_stdout": verification["stdout"],
            "transcript": transcript,
            "turn_count": turn_count,
        }
    finally:
        _run(["docker", "rm", "--force", container], timeout=30)


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not 1 <= arguments.command_timeout_seconds <= 300:
        parser().error("--command-timeout-seconds must be between 1 and 300")
    if not 60 <= arguments.build_timeout_seconds <= 3600:
        parser().error("--build-timeout-seconds must be between 60 and 3600")
    output = arguments.output.resolve()
    if output.exists():
        parser().error(f"--output already exists: {output}")
    suite = _load_suite(arguments.suite)
    repo = arguments.terminalbench_repo.resolve()
    observed_commit = _require_success(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=30
    )
    if observed_commit != suite["terminalbench_commit"]:
        parser().error(
            "TerminalBench checkout differs from suite commit: "
            f"{observed_commit} != {suite['terminalbench_commit']}"
        )
    docker_version = _require_success(
        ["docker", "version", "--format", "{{.Server.Version}}"], timeout=30
    )
    images: dict[str, tuple[str, str, Path]] = {}
    for task in suite["tasks"]:
        print(f"[build] {task['id']}", file=sys.stderr, flush=True)
        image, image_id = _build_task_image(
            repo,
            task,
            suite["terminalbench_commit"],
            timeout=arguments.build_timeout_seconds,
        )
        images[task["id"]] = (
            image,
            image_id,
            _verify_task_source(repo, task),
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    engine: Qwen3ServiceEngine | None = None
    started = time.monotonic()
    try:
        tokenizer = Qwen3Tokenizer(arguments.deployment)
        engine = Qwen3ServiceEngine(
            arguments.deployment,
            device=arguments.device,
            attention_backend=arguments.attention_backend,
        )
        task_results: list[dict[str, Any]] = []
        for ordinal, task in enumerate(suite["tasks"], start=1):
            print(
                f"[{ordinal}/{len(suite['tasks'])}] agent {task['id']}",
                file=sys.stderr,
                flush=True,
            )
            image, image_id, source = images[task["id"]]
            result = _run_agent_task(
                engine,
                tokenizer,
                task,
                image,
                image_id,
                source,
                maximum_turns=suite["maximum_agent_turns"],
                maximum_new_tokens=suite["maximum_new_tokens_per_turn"],
                enable_thinking=suite["enable_thinking"],
                command_timeout=arguments.command_timeout_seconds,
            )
            task_results.append(result)
            print(
                f"[{ordinal}/{len(suite['tasks'])}] {task['id']}: "
                f"termination={result['agent_termination']} "
                f"commands={result['command_count']} passed={result['passed']}",
                file=sys.stderr,
                flush=True,
            )
        all_passed = all(task["passed"] for task in task_results)
        body = {
            "all_tasks_passed": all_passed,
            "attention_backend": arguments.attention_backend,
            "bash_tool_schema_sha256": hashlib.sha256(
                canonical_json_bytes(BASH_TOOL)
            ).hexdigest(),
            "build_id": engine.manifest["build_id"],
            "context_limit_tokens": TARGET_CONTEXT_TOKENS,
            "device": str(engine.device),
            "docker_version": docker_version,
            "enable_thinking": suite["enable_thinking"],
            "generation_mode": suite["generation_mode"],
            "maximum_agent_turns": suite["maximum_agent_turns"],
            "maximum_new_tokens_per_turn": suite["maximum_new_tokens_per_turn"],
            "official_chat_template_sha256": hashlib.sha256(
                tokenizer.chat_template.encode("utf-8")
            ).hexdigest(),
            "runner_sha256": _sha256_file(Path(__file__)),
            "schema": CAMPAIGN_SCHEMA,
            "status": "pass" if all_passed else "fail",
            "suite_id": suite["suite_id"],
            "tasks": task_results,
            "terminalbench_commit": suite["terminalbench_commit"],
            "tool_names": ["bash"],
            "total_wall_time_seconds": round(time.monotonic() - started, 6),
        }
        report = {
            **body,
            "campaign_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
        }
        Draft202012Validator(
            _schema("terminalbench_agent_campaign_v1.schema.json")
        ).validate(report)
        _write_new(temporary / "campaign.json", report)
        temporary.rename(output)
        print(report["campaign_id"])
        return 0 if all_passed else 1
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        if engine is not None:
            engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
