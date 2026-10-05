#!/usr/bin/env python3
"""Run one Qwen task with accelerator-generated turns in an isolated container."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence
import uuid

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    publish_bytes_atomic_no_replace,
    sha256_file,
)
from compiler.tensor_accelerator.qwen_agent_execution import (  # noqa: E402
    QwenAgentExecutionError,
    build_agent_task_execution,
    publish_agent_task_execution,
    validate_agent_task_execution,
)
from compiler.tensor_accelerator.qwen_agent_protocol import (  # noqa: E402
    BASH_TOOL,
    SYSTEM_PROMPT,
    QwenAgentProtocolError,
    assistant_message,
    parse_assistant_output,
    tool_response,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    QwenChatError,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_dynamic_control import (  # noqa: E402
    QwenDynamicControlError,
    build_dynamic_generation_control,
    publish_dynamic_generation_control,
    validate_controlled_dynamic_execution,
    validate_dynamic_generation_control,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    build_dynamic_session,
    publish_dynamic_session,
    validate_dynamic_session,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    QwenWorkloadError,
    load_shared_workload,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (  # noqa: E402
    QwenFullModelSimulationError,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DEFAULT_WORKLOAD = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
DEFAULT_TERMINALBENCH = ROOT / "build/terminal-bench-d28711d0da26"
SESSION_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_dynamic_session_v1.schema.json"
)
CONTROL_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_dynamic_generation_control_v1.schema.json"
)
AGENT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_agent_task_execution_v1.schema.json"
)
CONTROLLED_RUNNER = ROOT / "tools/run_qwen3_tensor_accelerator_controlled_session.py"
STREAM_LIMIT = 4096
TEST_STREAM_LIMIT = 16384


class LiveAgentError(ArtifactError):
    """Raised when the live task, container, or accelerator turn differs."""


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
        raise LiveAgentError(f"command failed: {command[0]}: {exc}") from exc


def _require_success(
    command: Sequence[str],
    *,
    timeout: int,
    cwd: Path | None = None,
) -> str:
    result = _run(command, timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-8000:]
        raise LiveAgentError(
            f"command {command[0]!r} exited {result.returncode}: {detail}"
        )
    return result.stdout.strip()


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = f"\n... truncated {len(text) - limit} characters ...\n"
    retained = max(0, limit - len(marker))
    return text[:retained] + marker, True


def _task(workload: dict[str, Any], task_id: str) -> dict[str, Any]:
    matches = [task for task in workload["agent"]["tasks"] if task["id"] == task_id]
    if len(matches) != 1:
        raise LiveAgentError("requested live agent task differs")
    return matches[0]


def _verify_task_source(repo: Path, task: dict[str, Any], commit: str) -> Path:
    observed = _require_success(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=30
    )
    if observed != commit:
        raise LiveAgentError(
            f"TerminalBench checkout differs: {observed} != {commit}"
        )
    root = repo / "original-tasks" / task["id"]
    expected = {
        "Dockerfile": task["source"]["dockerfile_sha256"],
        "task.yaml": task["source"]["task_yaml_sha256"],
        "tests/test_outputs.py": task["source"]["test_sha256"],
        **{
            item["path"]: item["sha256"]
            for item in task["source"]["runtime_files"]
        },
    }
    for relative, digest in expected.items():
        parsed = PurePosixPath(relative)
        if parsed.is_absolute() or ".." in parsed.parts:
            raise LiveAgentError("TerminalBench task source path is unsafe")
        path = root / relative
        try:
            observed_digest, _ = sha256_file(path)
        except OSError as exc:
            raise LiveAgentError(
                f"cannot authenticate TerminalBench source {relative}: {exc}"
            ) from exc
        if observed_digest != digest:
            raise LiveAgentError(
                f"TerminalBench source differs for {task['id']}/{relative}"
            )
    return root


def _image(
    repo: Path,
    task: dict[str, Any],
    commit: str,
    *,
    build_timeout: int,
) -> tuple[str, str, Path]:
    source = _verify_task_source(repo, task, commit)
    tag = f"opentallas-qwen3-tbench:{commit[:12]}-{task['id']}"
    inspect = _run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag], timeout=30
    )
    if inspect.returncode != 0:
        build_root = ROOT / "build"
        build_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".qwen3-tbench-{task['id']}-", dir=build_root
        ) as temporary_text:
            temporary = Path(temporary_text)
            shutil.copyfile(source / "Dockerfile", temporary / "Dockerfile")
            for item in task["source"]["runtime_files"]:
                destination = temporary / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item["path"], destination)
            result = _run(
                [
                    "docker",
                    "build",
                    "--label",
                    f"opentallas.terminalbench.commit={commit}",
                    "--label",
                    f"opentallas.terminalbench.task={task['id']}",
                    "--tag",
                    tag,
                    ".",
                ],
                timeout=build_timeout,
                cwd=temporary,
            )
            if result.returncode != 0:
                raise LiveAgentError(
                    f"Docker build failed: {(result.stderr or result.stdout)[-8000:]}"
                )
    raw = _require_success(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{json .}}",
            tag,
        ],
        timeout=30,
    )
    try:
        image = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveAgentError(f"Docker image inspect is invalid JSON: {exc}") from exc
    labels = image.get("Config", {}).get("Labels", {})
    image_id = image.get("Id")
    if (
        not isinstance(image_id, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None
        or not isinstance(labels, dict)
        or labels.get("opentallas.terminalbench.commit") != commit
        or labels.get("opentallas.terminalbench.task") != task["id"]
    ):
        raise LiveAgentError("Docker task image identity or labels differ")
    return tag, image_id, source


def _docker_run_arguments(container: str, image: str) -> list[str]:
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


def _inspect_isolation(container: str) -> dict[str, Any]:
    raw = _require_success(["docker", "inspect", container], timeout=30)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveAgentError(f"Docker inspect is invalid JSON: {exc}") from exc
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise LiveAgentError("Docker inspect returned an unexpected document")
    inspected = value[0]
    host = inspected.get("HostConfig")
    mounts = inspected.get("Mounts")
    if not isinstance(host, dict) or not isinstance(mounts, list):
        raise LiveAgentError("Docker inspect lacks isolation state")
    state = {
        "cap_drop_all": "ALL" in (host.get("CapDrop") or []),
        "host_mounts": any(
            isinstance(item, dict) and item.get("Type") == "bind" for item in mounts
        ),
        "network": host.get("NetworkMode"),
        "no_new_privileges": "no-new-privileges:true"
        in (host.get("SecurityOpt") or []),
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
        raise LiveAgentError(f"container isolation differs: {state}")
    return state


def _container_running(container: str) -> bool:
    result = _run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container],
        timeout=30,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _execute_bash(container: str, command: str, timeout: int) -> dict[str, Any]:
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
        stdout, stdout_truncated = _truncate(
            "" if exc.stdout is None else str(exc.stdout), STREAM_LIMIT
        )
        stderr, stderr_truncated = _truncate(
            "" if exc.stderr is None else str(exc.stderr), STREAM_LIMIT
        )
        return {
            "command": command,
            "exit_code": None,
            "stderr": stderr,
            "stdout": stdout,
            "timed_out": True,
            "truncated": stdout_truncated or stderr_truncated,
        }
    except OSError as exc:
        raise LiveAgentError(f"cannot execute Docker bash tool: {exc}") from exc
    stdout, stdout_truncated = _truncate(result.stdout, STREAM_LIMIT)
    stderr, stderr_truncated = _truncate(result.stderr, STREAM_LIMIT)
    return {
        "command": command,
        "exit_code": result.returncode,
        "stderr": stderr,
        "stdout": stdout,
        "timed_out": False,
        "truncated": stdout_truncated or stderr_truncated,
    }


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
    container: str, test_path: Path, timeout: int
) -> dict[str, Any]:
    _require_success(
        ["docker", "exec", container, "mkdir", "-p", "/app/.opentallas-verifier"],
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


def _load_or_build_turn(
    *,
    snapshot: Path,
    deployment: Path,
    workload_path: Path,
    workload: dict[str, Any],
    chat: QwenChatTokenizer,
    task: dict[str, Any],
    messages: list[dict[str, Any]],
    turn: int,
    turn_root: Path,
    checkpoint_interval: int,
) -> tuple[dict[str, Any], Any]:
    expected_turn = task["expected"]["turns"][turn - 1]
    prompt = chat.prompt_record(messages, tools=[BASH_TOOL], enable_thinking=False)
    if prompt != expected_turn["prompt"]:
        raise LiveAgentError(f"live agent prompt drifted before turn {turn}")
    session_path = turn_root / "session.json"
    control_path = turn_root / "control.json"
    aggregate_path = turn_root / "controlled_execution.json"
    if session_path.exists() or control_path.exists():
        if not session_path.is_file() or not control_path.is_file():
            raise LiveAgentError("existing agent turn artifacts are unsafe")
        session = validate_dynamic_session(load_strict_json(session_path))
        control = validate_dynamic_generation_control(
            load_strict_json(control_path), session, workload
        )
        if (
            session["prompt"]["text"] != prompt["prompt_text"]
            or control["workload_binding"]["case_id"] != task["id"]
            or control["workload_binding"]["turn"] != turn
        ):
            raise LiveAgentError("existing agent turn compilation differs")
    else:
        session = build_dynamic_session(
            snapshot=snapshot,
            checkpoint_lock_path=deployment / "source/checkpoint.lock.json",
            model_graph_path=deployment / "source/model_graph.v2.json",
            deployment_manifest_path=deployment / "deployment_manifest.json",
            physical_plan_path=deployment / "physical/physical_plan.json",
            prompt_text=prompt["prompt_text"],
            generated_token_limit=min(
                workload["agent"]["maximum_new_tokens_per_turn"],
                8000 - prompt["prompt_token_count"] + 1,
            ),
        )
        control = build_dynamic_generation_control(
            session,
            workload,
            kind="agent_turn",
            case_id=task["id"],
            turn=turn,
        )
        for value, schema_path in (
            (session, SESSION_SCHEMA),
            (control, CONTROL_SCHEMA),
        ):
            schema = load_strict_json(schema_path)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
        publish_dynamic_session(session, session_path)
        publish_dynamic_generation_control(
            control, session, workload, control_path
        )
    if not aggregate_path.exists():
        command = [
            sys.executable,
            str(CONTROLLED_RUNNER),
            "--snapshot",
            str(snapshot),
            "--deployment",
            str(deployment),
            "--workload",
            str(workload_path),
            "--session",
            str(session_path),
            "--control",
            str(control_path),
            "--output",
            str(turn_root),
            "--checkpoint-interval",
            str(checkpoint_interval),
        ]
        try:
            result = subprocess.run(command, check=False)
        except OSError as exc:
            raise LiveAgentError(f"cannot launch controlled turn runner: {exc}") from exc
        if result.returncode != 0:
            raise LiveAgentError(
                f"controlled accelerator turn {turn} exited {result.returncode}"
            )
    execution = validate_controlled_dynamic_execution(
        load_strict_json(aggregate_path),
        control,
        session,
        workload,
        chat=chat,
    )
    if execution["status"] != "pass" or execution["stop_reason"] != "eos":
        raise LiveAgentError(f"controlled accelerator turn {turn} did not pass")
    parsed = parse_assistant_output(execution["decoded"]["generated_text_raw"])
    summary = {
        "base_session_id": session["session_id"],
        "content": parsed.content,
        "control_id": control["control_id"],
        "controlled_execution_id": execution["controlled_execution_id"],
        "generated_text_raw": execution["decoded"]["generated_text_raw"],
        "generated_text_visible": execution["decoded"]["generated_text_visible"],
        "generated_token_count": execution["generated_token_count"],
        "generated_token_ids": execution["generated_token_ids"],
        "parsed_calls": list(parsed.calls),
        "prompt_token_count": session["prompt"]["token_count"],
        "prompt_token_sha256": expected_turn["prompt"]["prompt_token_sha256"],
        "reasoning": parsed.reasoning,
        "status": execution["status"],
        "stop_reason": execution["stop_reason"],
        "turn": turn,
    }
    return summary, parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one frozen TerminalBench task. Every assistant turn is generated "
            "by the compiled HBM/SRAM tensor-accelerator simulator; parsed bash "
            "calls execute only inside a networkless, capability-dropped container."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--terminalbench-repo", type=Path, default=DEFAULT_TERMINALBENCH)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--checkpoint-interval", type=int, default=32)
    parser.add_argument("--command-timeout-seconds", type=int, default=30)
    parser.add_argument("--build-timeout-seconds", type=int, default=900)
    arguments = parser.parse_args()
    if arguments.checkpoint_interval < 1:
        parser.error("--checkpoint-interval must be positive")
    if not 1 <= arguments.command_timeout_seconds <= 300:
        parser.error("--command-timeout-seconds must be between 1 and 300")
    if not 60 <= arguments.build_timeout_seconds <= 3600:
        parser.error("--build-timeout-seconds must be between 60 and 3600")
    started = time.monotonic()
    container: str | None = None
    try:
        checkpoint_lock = load_strict_json(
            arguments.deployment / "source/checkpoint.lock.json"
        )
        chat = QwenChatTokenizer(arguments.snapshot, checkpoint_lock)
        workload = load_shared_workload(arguments.workload, chat=chat)
        task = _task(workload, arguments.task_id)
        commit = workload["agent"]["terminalbench_commit"]
        tag, image_id, source = _image(
            arguments.terminalbench_repo.resolve(),
            task,
            commit,
            build_timeout=arguments.build_timeout_seconds,
        )
        docker_version = _require_success(
            ["docker", "version", "--format", "{{.Server.Version}}"], timeout=30
        )
        output = arguments.output.resolve()
        if output.exists() and (output.is_symlink() or not output.is_dir()):
            raise LiveAgentError("agent output root must be a regular directory")
        turns_root = output / "turns"
        actions_root = output / "actions"
        turns_root.mkdir(parents=True, exist_ok=True)
        actions_root.mkdir(exist_ok=True)
        container = f"opentallas-ta-{task['id']}-{uuid.uuid4().hex[:12]}"
        _require_success(_docker_run_arguments(container, tag), timeout=60)
        isolation = _inspect_isolation(container)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["source"]["instruction"]},
        ]
        turn_summaries: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        final_answer: str | None = None
        action_ordinal = 0
        for turn in range(1, workload["agent"]["maximum_agent_turns"] + 1):
            if turn > len(task["expected"]["turns"]):
                raise LiveAgentError("agent exceeded the frozen successful turn count")
            summary, parsed = _load_or_build_turn(
                snapshot=arguments.snapshot,
                deployment=arguments.deployment,
                workload_path=arguments.workload,
                workload=workload,
                chat=chat,
                task=task,
                messages=messages,
                turn=turn,
                turn_root=turns_root / f"turn.{turn:04d}",
                checkpoint_interval=arguments.checkpoint_interval,
            )
            turn_summaries.append(summary)
            messages.append(assistant_message(parsed))
            if not parsed.calls:
                final_answer = parsed.content
                break
            for call_index, call in enumerate(parsed.calls, start=1):
                action_ordinal += 1
                observed = _execute_bash(
                    container,
                    call["arguments"]["command"],
                    arguments.command_timeout_seconds,
                )
                observed.update(
                    {
                        "call_index": call_index,
                        "turn": turn,
                        "type": "bash_action",
                    }
                )
                action_path = actions_root / f"action.{action_ordinal:04d}.json"
                if action_path.exists():
                    retained = load_strict_json(action_path)
                    if retained != observed:
                        raise LiveAgentError(
                            f"replayed live action {action_ordinal} differs"
                        )
                    action = retained
                else:
                    publish_bytes_atomic_no_replace(
                        action_path, canonical_json_bytes(observed)
                    )
                    action = observed
                actions.append(action)
                messages.append({"role": "tool", "content": tool_response(action)})
                if action["timed_out"] or not _container_running(container):
                    raise LiveAgentError("agent tool action failed or stopped container")
        if final_answer is None:
            raise LiveAgentError("agent did not produce an EOS-terminated final answer")
        verification = _verify_official_tests(
            container,
            source / "tests/test_outputs.py",
            timeout=180,
        )
        deployment_manifest = load_strict_json(
            arguments.deployment / "deployment_manifest.json"
        )
        report = build_agent_task_execution(
            workload,
            task_id=task["id"],
            build_id=deployment_manifest["build_id"],
            graph_id=deployment_manifest["graph_id"],
            docker_version=docker_version,
            image_id=image_id,
            image_tag=tag,
            isolation=isolation,
            turns=turn_summaries,
            actions=actions,
            final_answer=final_answer,
            test_exit_code=verification["exit_code"],
            test_stdout=verification["stdout"],
            test_stderr=verification["stderr"],
        )
        schema = load_strict_json(AGENT_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
        report_path = output / "agent_execution.json"
        if report_path.exists():
            retained = validate_agent_task_execution(
                load_strict_json(report_path), workload
            )
            if retained != report:
                raise LiveAgentError("existing agent execution differs")
        else:
            publish_agent_task_execution(report, workload, report_path)
    except (
        ArtifactError,
        OSError,
        QwenAgentExecutionError,
        QwenAgentProtocolError,
        QwenChatError,
        QwenDynamicArtifactError,
        QwenDynamicControlError,
        QwenFullModelSimulationError,
        QwenWorkloadError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))
    finally:
        if container is not None:
            _run(["docker", "rm", "--force", container], timeout=30)

    elapsed = time.monotonic() - started
    print(f"status={report['status']}")
    print(f"agent_execution_id={report['agent_execution_id']}")
    print(f"task_id={report['task_id']}")
    print(f"commands={report['actions']}")
    print(f"final_answer={report['final_answer']!r}")
    print(f"test_stdout={report['test']['stdout']!r}")
    print(f"host_elapsed_seconds={elapsed:.6f}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
