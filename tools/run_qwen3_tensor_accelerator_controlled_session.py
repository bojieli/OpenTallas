#!/usr/bin/env python3
"""Run or resume one first-EOS-controlled Qwen natural or agent-turn session."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping, Sequence
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
)
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    EOS_TOKEN_IDS,
    QwenChatError,
    QwenChatTokenizer,
)
from compiler.tensor_accelerator.qwen_dynamic_control import (  # noqa: E402
    QwenDynamicControlError,
    build_controlled_dynamic_execution,
    generated_token_record,
    publish_controlled_dynamic_execution,
    validate_dynamic_generation_control,
)
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    build_dynamic_request,
    publish_dynamic_request,
    validate_dynamic_request,
    validate_dynamic_session,
    validate_dynamic_transaction_report,
)
from compiler.tensor_accelerator.qwen_workload import (  # noqa: E402
    QwenWorkloadError,
    load_shared_workload,
)
from runtime.tensor_accelerator.qwen_full_model_checkpoint import (  # noqa: E402
    MANIFEST_NAME,
    QwenFullModelCheckpointError,
    load_dynamic_runtime_checkpoint,
    validate_dynamic_checkpoint_manifest,
    validate_dynamic_checkpoint_predecessor,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (  # noqa: E402
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
    publish_qwen_full_model_dynamic_execution_report,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DEFAULT_WORKLOAD = (
    ROOT / "testdata/compiler/tensor_accelerator_qwen_natural/workload.json"
)
TRANSACTION_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_dynamic_execution_v1.schema.json"
)
CONTROL_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_dynamic_generation_control_v1.schema.json"
)
AGGREGATE_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_controlled_dynamic_session_execution_v1.schema.json"
)
CHECKPOINT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_runtime_checkpoint_v2.schema.json"
)
_CHECKPOINT = re.compile(r"^checkpoint\.(?P<step>[0-9]{4})$")
_REQUEST = re.compile(r"^request\.(?P<step>[0-9]{4})\.json$")
_EXECUTION = re.compile(r"^execution\.(?P<step>[0-9]{4})\.json$")
_CHECKPOINT_STAGING = re.compile(
    r"^\.checkpoint\.(?P<step>[0-9]{4})\.tmp-[A-Za-z0-9_-]+$"
)
_REQUEST_STAGING = re.compile(
    r"^\.request\.(?P<step>[0-9]{4})\.json\.tmp-[A-Za-z0-9_-]+$"
)
_EXECUTION_STAGING = re.compile(
    r"^\.execution\.(?P<step>[0-9]{4})\.json\.tmp-[A-Za-z0-9_-]+$"
)
_AGGREGATE_STAGING = re.compile(
    r"^\.controlled_execution\.json\.tmp-[A-Za-z0-9_-]+$"
)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelSimulationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenFullModelSimulationError(f"{label} is not canonical JSON")
    return value


def _remove_staging(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise QwenFullModelSimulationError(f"unsafe incomplete {label}: {path}")
    path.unlink()
    _fsync_directory(path.parent)
    print(f"removed_incomplete_{label}={path}", flush=True)


class _ArtifactSequence(Sequence[Mapping[str, Any]]):
    """Lazy canonical artifact sequence so 8,000-step aggregation stays bounded."""

    def __init__(self, directory: Path, prefix: str, count: int) -> None:
        self._directory = Path(directory)
        self._prefix = prefix
        self._count = count

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index: int | slice) -> Mapping[str, Any]:
        if isinstance(index, slice):
            raise TypeError("artifact sequence slicing is not supported")
        normalized = index + self._count if index < 0 else index
        if not 0 <= normalized < self._count:
            raise IndexError(index)
        return _load_canonical(
            self._directory / f"{self._prefix}.{normalized:04d}.json",
            f"controlled {self._prefix} artifact {normalized}",
        )

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        for index in range(self._count):
            yield self[index]


def _indexed_files(
    directory: Path,
    pattern: re.Pattern[str],
    label: str,
    maximum_transactions: int,
) -> set[int]:
    if not directory.exists():
        return set()
    if not directory.is_dir() or directory.is_symlink():
        raise QwenFullModelSimulationError(f"{label} must be a regular directory")
    result: set[int] = set()
    for path in directory.iterdir():
        match = pattern.fullmatch(path.name)
        staging_pattern = _REQUEST_STAGING if pattern is _REQUEST else _EXECUTION_STAGING
        if match is None and staging_pattern.fullmatch(path.name):
            _remove_staging(path, f"{label.replace(' ', '_')}_staging")
            continue
        if match is None or path.is_symlink() or not path.is_file():
            raise QwenFullModelSimulationError(
                f"unexpected or unsafe {label} artifact: {path}"
            )
        index = int(match.group("step"))
        if index >= maximum_transactions or index in result:
            raise QwenFullModelSimulationError(f"{label} index differs: {path}")
        result.add(index)
    return result


def _frontier(
    requests: Path, executions: Path, maximum_transactions: int
) -> tuple[int, bool]:
    request_indices = _indexed_files(
        requests, _REQUEST, "controlled request", maximum_transactions
    )
    execution_indices = _indexed_files(
        executions, _EXECUTION, "controlled execution", maximum_transactions
    )
    completed = 0
    while completed in request_indices and completed in execution_indices:
        completed += 1
    expected_prefix = set(range(completed))
    if execution_indices - expected_prefix:
        raise QwenFullModelSimulationError(
            "controlled execution reports are noncontiguous or lack requests"
        )
    request_only = completed in request_indices
    allowed_requests = expected_prefix | ({completed} if request_only else set())
    if request_indices != allowed_requests:
        raise QwenFullModelSimulationError(
            "controlled requests are noncontiguous or exceed the durable frontier"
        )
    return completed, request_only


def _checkpoint_directories(
    directory: Path, maximum_transactions: int
) -> list[tuple[int, Path]]:
    if not directory.exists():
        return []
    if not directory.is_dir() or directory.is_symlink():
        raise QwenFullModelSimulationError(
            "controlled checkpoint root must be a regular directory"
        )
    checkpoints: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        match = _CHECKPOINT.fullmatch(path.name)
        if match is None:
            if _CHECKPOINT_STAGING.fullmatch(path.name):
                if path.is_symlink() or not path.is_dir():
                    raise QwenFullModelSimulationError(
                        f"unsafe incomplete checkpoint staging path: {path}"
                    )
                shutil.rmtree(path)
                _fsync_directory(directory)
                print(f"removed_incomplete_checkpoint_staging={path}", flush=True)
                continue
            raise QwenFullModelSimulationError(
                f"unexpected controlled checkpoint artifact: {path}"
            )
        step = int(match.group("step"))
        if (
            not 1 <= step <= maximum_transactions
            or path.is_symlink()
            or not path.is_dir()
        ):
            raise QwenFullModelSimulationError(
                f"unsafe controlled checkpoint directory: {path}"
            )
        checkpoints.append((step, path))
    checkpoints.sort()
    return checkpoints


def _checkpoint_bindings(
    session: Mapping[str, Any], deployment: Path
) -> dict[str, str]:
    manifest = _load_canonical(
        deployment / "deployment_manifest.json", "deployment manifest"
    )
    plan = _load_canonical(
        deployment / "physical/physical_plan.json", "physical plan"
    )
    return {
        "build_id": str(session["build_id"]),
        "capability_id": str(manifest["capability_id"]),
        "checkpoint_lock_id": str(session["checkpoint_lock_id"]),
        "command_program_sha256": str(session["command_program_sha256"]),
        "graph_id": str(session["graph_id"]),
        "hbm_logical_sha256": str(plan["hbm"]["image"]["logical_sha256"]),
        "kernel_ir_id": str(manifest["kernel_ir_id"]),
        "physical_plan_id": str(plan["physical_plan_id"]),
        "session_id": str(session["session_id"]),
    }


def _load_checkpoint_manifest(
    path: Path,
    *,
    bindings: Mapping[str, str],
    context_capacity: int,
    checkpoint_validator: Draft202012Validator,
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise QwenFullModelSimulationError(
            "dynamic runtime checkpoint must be a regular directory"
        )
    manifest_path = path / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise QwenFullModelSimulationError(
            "dynamic runtime checkpoint manifest must be a regular file"
        )
    value = validate_dynamic_checkpoint_manifest(
        _load_canonical(manifest_path, "dynamic runtime checkpoint manifest"),
        expected_bindings=bindings,
        expected_context_capacity=context_capacity,
    )
    checkpoint_validator.validate(value)
    if value["next_step_index"] != int(path.name.rsplit(".", 1)[-1]):
        raise QwenFullModelSimulationError(
            "checkpoint directory and next-step identities differ"
        )
    return value


def _audit_prefix(
    *,
    session: Mapping[str, Any],
    control: Mapping[str, Any],
    workload: Mapping[str, Any],
    chat: QwenChatTokenizer,
    requests: Path,
    executions: Path,
    count: int,
    transaction_validator: Draft202012Validator,
    capture_step: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int, str | None]:
    previous: dict[str, Any] | None = None
    captured: dict[str, Any] | None = None
    generated_count = 0
    stop_reason: str | None = None
    maximum_generated = control["generation"]["maximum_generated_token_count"]
    for step in range(count):
        request = _load_canonical(
            requests / f"request.{step:04d}.json", f"controlled request {step}"
        )
        report = _load_canonical(
            executions / f"execution.{step:04d}.json", f"controlled execution {step}"
        )
        validate_dynamic_request(request, session, previous)
        transaction_validator.validate(report)
        validate_dynamic_transaction_report(report, session, request, previous)
        if request["output_role"] == "generated_token":
            token = report["outputs"]["committed_logits"]["greedy_token_id"]
            generated_token_record(
                control,
                session,
                workload,
                chat,
                generated_token_index=generated_count,
                token_id=token,
            )
            generated_count += 1
            if token in EOS_TOKEN_IDS:
                stop_reason = "eos"
            elif generated_count == maximum_generated:
                stop_reason = "maximum_generated_token_count"
            if stop_reason is not None and step != count - 1:
                raise QwenFullModelSimulationError(
                    "durable controlled artifacts continue after terminal decision"
                )
        previous = report
        if step + 1 == capture_step:
            captured = report
    return previous, captured, generated_count, stop_reason


def _publish_checkpoint(
    *,
    simulator: QwenFullModelSimulator,
    checkpoint_root: Path,
    retain: int,
    previous_report: Mapping[str, Any],
    bindings: Mapping[str, str],
    context_capacity: int,
    checkpoint_validator: Draft202012Validator,
    maximum_transactions: int,
) -> tuple[dict[str, Any], Path]:
    next_step = simulator.state_lengths[0]
    path = checkpoint_root / f"checkpoint.{next_step:04d}"
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise QwenFullModelSimulationError(f"existing checkpoint is unsafe: {path}")
        manifest, _ = load_dynamic_runtime_checkpoint(
            path,
            expected_bindings=bindings,
            expected_context_capacity=context_capacity,
        )
    else:
        manifest = simulator.checkpoint_dynamic_session(path)
    checkpoint_validator.validate(manifest)
    validate_dynamic_checkpoint_predecessor(manifest, previous_report)
    checkpoints = _checkpoint_directories(checkpoint_root, maximum_transactions)
    for _, old in checkpoints[:-retain]:
        if old.resolve().parent != checkpoint_root.resolve() or old.is_symlink():
            raise QwenFullModelSimulationError(
                f"refusing to prune unsafe checkpoint: {old}"
            )
        shutil.rmtree(old)
        _fsync_directory(checkpoint_root)
        print(f"pruned_superseded_checkpoint={old}", flush=True)
    return manifest, path


def _validators() -> tuple[
    Draft202012Validator,
    Draft202012Validator,
    Draft202012Validator,
]:
    transaction_schema = load_strict_json(TRANSACTION_SCHEMA)
    control_schema = load_strict_json(CONTROL_SCHEMA)
    aggregate_schema = load_strict_json(AGGREGATE_SCHEMA)
    checkpoint_schema = load_strict_json(CHECKPOINT_SCHEMA)
    for schema in (
        transaction_schema,
        control_schema,
        aggregate_schema,
        checkpoint_schema,
    ):
        Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(
        control_schema["$id"], Resource.from_contents(control_schema)
    )
    return (
        Draft202012Validator(transaction_schema),
        Draft202012Validator(aggregate_schema, registry=registry),
        Draft202012Validator(checkpoint_schema),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute or resume one exact official-template Qwen natural or agent "
            "turn through the complete compiled tensor-accelerator command stream. "
            "Every selected token is authenticated before publication; EOS is "
            "retained and no post-EOS model request is issued."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--checkpoint-interval", type=int, default=32)
    parser.add_argument("--retain-checkpoints", type=int, default=2)
    parser.add_argument(
        "--max-transactions",
        type=int,
        help="execute at most this many new or replayed transactions before checkpointing",
    )
    arguments = parser.parse_args()
    if arguments.checkpoint_interval < 1:
        parser.error("--checkpoint-interval must be positive")
    if arguments.retain_checkpoints < 2:
        parser.error("--retain-checkpoints must be at least two")
    if arguments.max_transactions is not None and arguments.max_transactions < 1:
        parser.error("--max-transactions must be positive")

    output = arguments.output.resolve()
    requests_directory = output / "requests"
    executions_directory = output / "executions"
    checkpoints_directory = output / "checkpoints"
    aggregate_path = output / "controlled_execution.json"
    invocation_start = time.perf_counter()
    work_done = 0
    try:
        session = validate_dynamic_session(
            _load_canonical(arguments.session, "controlled dynamic session")
        )
        checkpoint_lock = _load_canonical(
            arguments.deployment / "source/checkpoint.lock.json", "checkpoint lock"
        )
        chat = QwenChatTokenizer(arguments.snapshot, checkpoint_lock)
        workload = load_shared_workload(arguments.workload, chat=chat)
        control = validate_dynamic_generation_control(
            _load_canonical(arguments.control, "dynamic generation control"),
            session,
            workload,
        )
        transaction_validator, aggregate_validator, checkpoint_validator = _validators()
        maximum_transactions = (
            session["prompt"]["token_count"]
            + control["generation"]["maximum_generated_token_count"]
            - 1
        )
        bindings = _checkpoint_bindings(session, arguments.deployment)
        if output.exists() and (output.is_symlink() or not output.is_dir()):
            raise QwenFullModelSimulationError(
                "controlled output root must be a regular directory"
            )
        output.mkdir(parents=True, exist_ok=True)
        _fsync_directory(output.parent)
        for directory, label in (
            (requests_directory, "controlled request root"),
            (executions_directory, "controlled execution root"),
            (checkpoints_directory, "controlled checkpoint root"),
        ):
            if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
                raise QwenFullModelSimulationError(
                    f"{label} must be a regular directory"
                )
            directory.mkdir(exist_ok=True)
            _fsync_directory(directory)
        _fsync_directory(output)
        allowed_files = {
            arguments.session.resolve(),
            arguments.control.resolve(),
            aggregate_path.resolve(),
        }
        for path in output.iterdir():
            if path.name in {"requests", "executions", "checkpoints"}:
                continue
            if path.resolve() in allowed_files:
                if path.is_symlink() or not path.is_file():
                    raise QwenFullModelSimulationError(
                        f"unsafe controlled root artifact: {path}"
                    )
                continue
            if _AGGREGATE_STAGING.fullmatch(path.name):
                _remove_staging(path, "controlled_aggregate_staging")
                continue
            raise QwenFullModelSimulationError(
                f"unexpected controlled output artifact: {path}"
            )

        completed, _ = _frontier(
            requests_directory, executions_directory, maximum_transactions
        )
        checkpoints = _checkpoint_directories(
            checkpoints_directory, maximum_transactions
        )
        checkpoint_manifest: dict[str, Any] | None = None
        checkpoint_path: Path | None = None
        checkpoint_step = 0
        if checkpoints:
            checkpoint_step, checkpoint_path = checkpoints[-1]
            checkpoint_manifest = _load_checkpoint_manifest(
                checkpoint_path,
                bindings=bindings,
                context_capacity=session["context_capacity"],
                checkpoint_validator=checkpoint_validator,
            )
            if checkpoint_step > completed:
                raise QwenFullModelSimulationError(
                    "latest checkpoint exceeds the durable report frontier"
                )
        durable_previous, checkpoint_previous, durable_generated, durable_stop = (
            _audit_prefix(
                session=session,
                control=control,
                workload=workload,
                chat=chat,
                requests=requests_directory,
                executions=executions_directory,
                count=completed,
                transaction_validator=transaction_validator,
                capture_step=checkpoint_step,
            )
        )
        if checkpoint_manifest is not None:
            if checkpoint_previous is None:
                raise QwenFullModelSimulationError(
                    "checkpoint predecessor differs from durable report prefix"
                )
            validate_dynamic_checkpoint_predecessor(
                checkpoint_manifest, checkpoint_previous
            )

        if durable_stop is None:
            previous = checkpoint_previous
            generated_count = sum(
                _load_canonical(
                    requests_directory / f"request.{step:04d}.json",
                    f"controlled request {step}",
                )["output_role"]
                == "generated_token"
                for step in range(checkpoint_step)
            )
            with QwenFullModelSimulator.load(
                arguments.deployment, verify_hbm_hashes=True
            ) as simulator:
                simulator.begin_dynamic_session(arguments.session)
                if checkpoint_path is not None:
                    simulator.restore_dynamic_session(checkpoint_path)
                step = checkpoint_step
                while step < maximum_transactions:
                    if (
                        arguments.max_transactions is not None
                        and work_done >= arguments.max_transactions
                    ):
                        break
                    request_path = requests_directory / f"request.{step:04d}.json"
                    expected_request = build_dynamic_request(session, previous)
                    if request_path.exists():
                        request = validate_dynamic_request(
                            _load_canonical(
                                request_path, f"controlled request {step}"
                            ),
                            session,
                            previous,
                        )
                        if request != expected_request:
                            raise QwenFullModelSimulationError(
                                f"published controlled request differs at step {step}"
                            )
                    else:
                        request = expected_request
                        publish_dynamic_request(
                            request, session, previous, request_path
                        )
                    report = simulator.execute_dynamic(request_path)
                    transaction_validator.validate(report)
                    validate_dynamic_transaction_report(
                        report, session, request, previous
                    )
                    stop_reason: str | None = None
                    if request["output_role"] == "generated_token":
                        token = report["outputs"]["committed_logits"][
                            "greedy_token_id"
                        ]
                        generated_token_record(
                            control,
                            session,
                            workload,
                            chat,
                            generated_token_index=generated_count,
                            token_id=token,
                        )
                        generated_count += 1
                        if token in EOS_TOKEN_IDS:
                            stop_reason = "eos"
                        elif (
                            generated_count
                            == control["generation"]["maximum_generated_token_count"]
                        ):
                            stop_reason = "maximum_generated_token_count"
                    report_path = (
                        executions_directory / f"execution.{step:04d}.json"
                    )
                    if report_path.exists():
                        observed = _load_canonical(
                            report_path, f"controlled execution {step}"
                        )
                        if observed != report:
                            raise QwenFullModelSimulationError(
                                f"replayed controlled report differs at step {step}"
                            )
                    else:
                        publish_qwen_full_model_dynamic_execution_report(
                            report, report_path
                        )
                    previous = report
                    step += 1
                    work_done += 1
                    token = report["outputs"]["committed_logits"]["greedy_token_id"]
                    print(
                        f"step={step - 1} complete={step}/{maximum_transactions} "
                        f"generated={generated_count}/"
                        f"{control['generation']['maximum_generated_token_count']} "
                        f"input={request['token_id']} output={token} "
                        f"report_id={report['report_id']}",
                        flush=True,
                    )
                    if stop_reason is not None:
                        durable_stop = stop_reason
                        break
                    if step % arguments.checkpoint_interval == 0:
                        checkpoint_manifest, checkpoint_path = _publish_checkpoint(
                            simulator=simulator,
                            checkpoint_root=checkpoints_directory,
                            retain=arguments.retain_checkpoints,
                            previous_report=previous,
                            bindings=bindings,
                            context_capacity=session["context_capacity"],
                            checkpoint_validator=checkpoint_validator,
                            maximum_transactions=maximum_transactions,
                        )
                        print(
                            f"checkpoint_step={step} "
                            f"checkpoint_id={checkpoint_manifest['checkpoint_id']} "
                            f"checkpoint_path={checkpoint_path}",
                            flush=True,
                        )
                if (
                    durable_stop is None
                    and work_done
                    and previous is not None
                    and (
                        checkpoint_manifest is None
                        or checkpoint_manifest["next_step_index"] != step
                    )
                ):
                    checkpoint_manifest, checkpoint_path = _publish_checkpoint(
                        simulator=simulator,
                        checkpoint_root=checkpoints_directory,
                        retain=arguments.retain_checkpoints,
                        previous_report=previous,
                        bindings=bindings,
                        context_capacity=session["context_capacity"],
                        checkpoint_validator=checkpoint_validator,
                        maximum_transactions=maximum_transactions,
                    )
                    print(
                        f"checkpoint_step={step} "
                        f"checkpoint_id={checkpoint_manifest['checkpoint_id']} "
                        f"checkpoint_path={checkpoint_path}",
                        flush=True,
                    )
            completed, request_only = _frontier(
                requests_directory, executions_directory, maximum_transactions
            )
            if request_only:
                raise QwenFullModelSimulationError(
                    "controlled durable frontier ends with an unexecuted request"
                )
        else:
            step = completed
            previous = durable_previous
            generated_count = durable_generated

        if durable_stop is None:
            elapsed = time.perf_counter() - invocation_start
            rate = work_done / elapsed if elapsed else 0.0
            print(f"status=checkpointed_incomplete next_step={step}")
            print(f"host_elapsed_seconds={elapsed:.9f}")
            print(f"host_transactions_per_second={rate:.9f}")
            return 0
        if previous is None or completed != step:
            raise QwenFullModelSimulationError(
                "terminal controlled artifact frontier differs"
            )
        result = build_controlled_dynamic_execution(
            control,
            session,
            workload,
            _ArtifactSequence(requests_directory, "request", completed),
            _ArtifactSequence(executions_directory, "execution", completed),
            chat=chat,
        )
        aggregate_validator.validate(result)
        if aggregate_path.exists():
            observed = _load_canonical(aggregate_path, "controlled aggregate")
            if observed != result:
                raise QwenFullModelSimulationError(
                    "existing controlled aggregate differs from reconstruction"
                )
        else:
            publish_controlled_dynamic_execution(
                result, control, session, workload, aggregate_path
            )
    except (
        ArtifactError,
        OSError,
        QwenChatError,
        QwenDynamicArtifactError,
        QwenDynamicControlError,
        QwenFullModelCheckpointError,
        QwenFullModelSimulationError,
        QwenWorkloadError,
        SchemaError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))

    elapsed = time.perf_counter() - invocation_start
    rate = work_done / elapsed if elapsed else 0.0
    print(f"status={result['status']}")
    print(f"controlled_execution_id={result['controlled_execution_id']}")
    print(f"stop_reason={result['stop_reason']}")
    print(f"prompt_text_raw={result['decoded']['prompt_text_raw']!r}")
    print(f"generated_token_ids={result['generated_token_ids']}")
    print(f"generated_text_visible={result['decoded']['generated_text_visible']!r}")
    print(f"host_elapsed_seconds={elapsed:.9f}")
    print(f"host_transactions_per_second={rate:.9f}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
