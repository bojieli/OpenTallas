#!/usr/bin/env python3
"""Run or resume the exact Qwen3-8B 8,000+32 acceptance campaign."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping, Sequence
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError
from tokenizers import Tokenizer, __version__ as tokenizers_version


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from compiler.tensor_accelerator.qwen_full_model_long_acceptance import (  # noqa: E402
    GENERATED_TOKEN_COUNT,
    QwenLongAcceptanceArtifactError,
    TRANSACTION_COUNT,
    build_long_acceptance_request,
    build_long_acceptance_session_execution,
    publish_long_acceptance_request,
    publish_long_acceptance_session_execution,
    validate_long_acceptance_request,
    validate_long_acceptance_session,
    validate_long_acceptance_transaction_report,
)
from runtime.tensor_accelerator.qwen_full_model_checkpoint import (  # noqa: E402
    MANIFEST_NAME,
    QwenFullModelCheckpointError,
    load_runtime_checkpoint,
    validate_checkpoint_predecessor,
    validate_checkpoint_manifest,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (  # noqa: E402
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
    publish_qwen_full_model_long_acceptance_execution_report,
)


DEFAULT_DEPLOYMENT = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_physical_v1"
)
TRANSACTION_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_long_acceptance_execution_v1.schema.json"
)
AGGREGATE_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_long_acceptance_session_execution_v1.schema.json"
)
CHECKPOINT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_runtime_checkpoint_v1.schema.json"
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
    r"^\.session_execution\.json\.tmp-[A-Za-z0-9_-]+$"
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
    """Lazy canonical report/request sequence for bounded aggregate memory."""

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
            f"long {self._prefix} artifact {normalized}",
        )

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        for index in range(self._count):
            yield self[index]


def _tokenizer(snapshot: Path, session: Mapping[str, Any]) -> Tokenizer:
    record = session["tokenizer"]
    path = Path(snapshot) / str(record["path"])
    try:
        digest, size = sha256_file(path)
    except OSError as exc:
        raise QwenFullModelSimulationError(
            f"cannot authenticate long acceptance tokenizer: {exc}"
        ) from exc
    if (
        tokenizers_version != record["library_version"]
        or digest != record["sha256"]
        or size < 1
    ):
        raise QwenFullModelSimulationError(
            "long acceptance tokenizer differs from its immutable manifest"
        )
    try:
        tokenizer = Tokenizer.from_file(str(path))
    except Exception as exc:
        raise QwenFullModelSimulationError(
            f"cannot load long acceptance tokenizer: {exc}"
        ) from exc
    if tokenizer.get_vocab_size(with_added_tokens=True) != 151_669:
        raise QwenFullModelSimulationError(
            "long acceptance tokenizer vocabulary differs"
        )
    return tokenizer


def _indexed_files(directory: Path, pattern: re.Pattern[str], label: str) -> set[int]:
    if not directory.exists():
        return set()
    if not directory.is_dir() or directory.is_symlink():
        raise QwenFullModelSimulationError(f"{label} must be a regular directory")
    result: set[int] = set()
    for path in directory.iterdir():
        match = pattern.fullmatch(path.name)
        staging_pattern = (
            _REQUEST_STAGING if pattern is _REQUEST else _EXECUTION_STAGING
        )
        if match is None and staging_pattern.fullmatch(path.name):
            _remove_staging(path, f"{label.replace(' ', '_')}_staging")
            continue
        if match is None or path.is_symlink() or not path.is_file():
            raise QwenFullModelSimulationError(
                f"unexpected or unsafe {label} artifact: {path}"
            )
        index = int(match.group("step"))
        if index >= TRANSACTION_COUNT or index in result:
            raise QwenFullModelSimulationError(f"{label} index differs: {path}")
        result.add(index)
    return result


def _frontier(requests: Path, executions: Path) -> tuple[int, bool]:
    request_indices = _indexed_files(requests, _REQUEST, "long request")
    execution_indices = _indexed_files(executions, _EXECUTION, "long execution")
    completed = 0
    while completed in request_indices and completed in execution_indices:
        completed += 1
    expected_prefix = set(range(completed))
    if execution_indices - expected_prefix:
        raise QwenFullModelSimulationError(
            "long execution reports are noncontiguous or lack requests"
        )
    request_only = completed in request_indices
    allowed_requests = expected_prefix | ({completed} if request_only else set())
    if request_indices != allowed_requests:
        raise QwenFullModelSimulationError(
            "long requests are noncontiguous or exceed the durable frontier"
        )
    return completed, request_only


def _checkpoint_directories(directory: Path) -> list[tuple[int, Path]]:
    if not directory.exists():
        return []
    if not directory.is_dir() or directory.is_symlink():
        raise QwenFullModelSimulationError(
            "long checkpoint root must be a regular directory"
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
                f"unexpected long checkpoint artifact: {path}"
            )
        if path.is_symlink() or not path.is_dir():
            raise QwenFullModelSimulationError(
                f"unsafe long checkpoint directory: {path}"
            )
        checkpoints.append((int(match.group("step")), path))
    checkpoints.sort()
    return checkpoints


def _load_checkpoint_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise QwenFullModelSimulationError(
            "runtime checkpoint must be a regular directory"
        )
    manifest_path = path / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise QwenFullModelSimulationError(
            "runtime checkpoint manifest must be a regular file"
        )
    value = validate_checkpoint_manifest(
        _load_canonical(manifest_path, "runtime checkpoint manifest")
    )
    schema = load_strict_json(CHECKPOINT_SCHEMA)
    Draft202012Validator(schema).validate(value)
    if value["next_step_index"] != int(path.name.rsplit(".", 1)[-1]):
        raise QwenFullModelSimulationError(
            "checkpoint directory and next-step identities differ"
        )
    return value


def _audit_prefix(
    *,
    session: Mapping[str, Any],
    requests: Path,
    executions: Path,
    count: int,
    transaction_validator: Draft202012Validator,
) -> dict[str, Any] | None:
    previous: dict[str, Any] | None = None
    for step in range(count):
        request = _load_canonical(
            requests / f"request.{step:04d}.json", f"long request {step}"
        )
        report = _load_canonical(
            executions / f"execution.{step:04d}.json", f"long execution {step}"
        )
        validate_long_acceptance_request(request, session, previous)
        transaction_validator.validate(report)
        validate_long_acceptance_transaction_report(
            report, session, request, previous
        )
        previous = report
    return previous


def _checkpoint_bindings(session: Mapping[str, Any]) -> dict[str, str]:
    return {
        field: str(session[field])
        for field in (
            "build_id",
            "capability_id",
            "checkpoint_lock_id",
            "command_program_sha256",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "physical_plan_id",
            "session_id",
        )
    }


def _publish_checkpoint(
    *,
    simulator: QwenFullModelSimulator,
    checkpoint_root: Path,
    retain: int,
    previous_report: Mapping[str, Any],
    session: Mapping[str, Any],
) -> tuple[dict[str, Any], Path]:
    next_step = simulator.state_lengths[0]
    path = checkpoint_root / f"checkpoint.{next_step:04d}"
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise QwenFullModelSimulationError(
                f"existing checkpoint is unsafe: {path}"
            )
        manifest, _ = load_runtime_checkpoint(
            path, expected_bindings=_checkpoint_bindings(session)
        )
        Draft202012Validator(load_strict_json(CHECKPOINT_SCHEMA)).validate(manifest)
    else:
        manifest = simulator.checkpoint_long_acceptance(path)
        schema = load_strict_json(CHECKPOINT_SCHEMA)
        Draft202012Validator(schema).validate(manifest)
    validate_checkpoint_predecessor(manifest, previous_report)
    checkpoints = _checkpoint_directories(checkpoint_root)
    for _, old in checkpoints[:-retain]:
        if old.resolve().parent != checkpoint_root.resolve() or old.is_symlink():
            raise QwenFullModelSimulationError(
                f"refusing to prune unsafe checkpoint: {old}"
            )
        shutil.rmtree(old)
        _fsync_directory(checkpoint_root)
        print(f"pruned_superseded_checkpoint={old}", flush=True)
    return manifest, path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute or resume all 8,031 causally chained full-model transactions "
            "for the exact Qwen 8,000-token prompt plus 32 greedy decisions. "
            "Requests and reports are append-only; byte-exact rolling KV "
            "checkpoints make the multi-day campaign restartable."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--checkpoint-interval", type=int, default=64)
    parser.add_argument("--retain-checkpoints", type=int, default=2)
    parser.add_argument(
        "--max-transactions",
        type=int,
        help="execute at most this many new/replayed transactions before checkpointing",
    )
    arguments = parser.parse_args()
    if arguments.checkpoint_interval < 1:
        parser.error("--checkpoint-interval must be positive")
    if arguments.retain_checkpoints < 2:
        parser.error("--retain-checkpoints must be at least two")
    if arguments.max_transactions is not None and arguments.max_transactions < 1:
        parser.error("--max-transactions must be positive")

    raw_output = arguments.output
    if raw_output.exists() and (raw_output.is_symlink() or not raw_output.is_dir()):
        parser.error("--output must name a regular directory or an absent path")
    output = raw_output.resolve()
    requests_directory = output / "requests"
    executions_directory = output / "executions"
    checkpoints_directory = output / "checkpoints"
    try:
        session = validate_long_acceptance_session(
            _load_canonical(arguments.session, "long acceptance session")
        )
        transaction_schema = load_strict_json(TRANSACTION_SCHEMA)
        aggregate_schema = load_strict_json(AGGREGATE_SCHEMA)
        checkpoint_schema = load_strict_json(CHECKPOINT_SCHEMA)
        for schema in (transaction_schema, aggregate_schema, checkpoint_schema):
            Draft202012Validator.check_schema(schema)
        transaction_validator = Draft202012Validator(transaction_schema)
        aggregate_validator = Draft202012Validator(aggregate_schema)
        tokenizer = _tokenizer(arguments.snapshot, session)
        if output.exists() and (output.is_symlink() or not output.is_dir()):
            raise QwenFullModelSimulationError(
                "long output root must be a regular directory"
            )
        output.mkdir(parents=True, exist_ok=True)
        _fsync_directory(output.parent)
        for directory, label in (
            (requests_directory, "long request root"),
            (executions_directory, "long execution root"),
            (checkpoints_directory, "long checkpoint root"),
        ):
            if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
                raise QwenFullModelSimulationError(
                    f"{label} must be a regular directory"
                )
            directory.mkdir(exist_ok=True)
            _fsync_directory(directory)
        _fsync_directory(output)
        for path in output.iterdir():
            if path.name in {"requests", "executions", "checkpoints"}:
                continue
            if path.name == "session_execution.json":
                if path.is_symlink() or not path.is_file():
                    raise QwenFullModelSimulationError(
                        f"unsafe long aggregate artifact: {path}"
                    )
                continue
            if _AGGREGATE_STAGING.fullmatch(path.name):
                _remove_staging(path, "long_aggregate_staging")
                continue
            raise QwenFullModelSimulationError(
                f"unexpected long output artifact: {path}"
            )
        completed, _ = _frontier(requests_directory, executions_directory)
        checkpoints = _checkpoint_directories(checkpoints_directory)
        checkpoint_manifest: dict[str, Any] | None = None
        checkpoint_path: Path | None = None
        checkpoint_step = 0
        if checkpoints:
            checkpoint_step, checkpoint_path = checkpoints[-1]
            checkpoint_manifest = _load_checkpoint_manifest(checkpoint_path)
            if checkpoint_step > completed:
                raise QwenFullModelSimulationError(
                    "latest checkpoint exceeds the durable report frontier"
                )
        previous = _audit_prefix(
            session=session,
            requests=requests_directory,
            executions=executions_directory,
            count=checkpoint_step,
            transaction_validator=transaction_validator,
        )
        if checkpoint_manifest is not None:
            if (
                previous is None
            ):
                raise QwenFullModelSimulationError(
                    "checkpoint predecessor differs from durable report prefix"
                )
            validate_checkpoint_predecessor(checkpoint_manifest, previous)

        work_done = 0
        generated_count = sum(
            _load_canonical(
                executions_directory / f"execution.{step:04d}.json",
                f"long execution {step}",
            )[
                "input"
            ]["output_role"]
            == "generated_token"
            for step in range(checkpoint_step)
        )
        with QwenFullModelSimulator.load(
            arguments.deployment, verify_hbm_hashes=True
        ) as simulator:
            simulator.begin_long_acceptance_session(arguments.session)
            if checkpoint_path is not None and checkpoint_step < TRANSACTION_COUNT:
                simulator.restore_long_acceptance(checkpoint_path)
            step = checkpoint_step
            while step < TRANSACTION_COUNT:
                if (
                    arguments.max_transactions is not None
                    and work_done >= arguments.max_transactions
                ):
                    break
                request_path = requests_directory / f"request.{step:04d}.json"
                expected_request = build_long_acceptance_request(session, previous)
                if request_path.exists():
                    request = validate_long_acceptance_request(
                        _load_canonical(request_path, f"long request {step}"),
                        session,
                        previous,
                    )
                    if request != expected_request:
                        raise QwenFullModelSimulationError(
                            f"published long request differs at step {step}"
                        )
                else:
                    request = expected_request
                    publish_long_acceptance_request(
                        request, session, previous, request_path
                    )
                report = simulator.execute_long_acceptance(request_path)
                transaction_validator.validate(report)
                validate_long_acceptance_transaction_report(
                    report, session, request, previous
                )
                report_path = executions_directory / f"execution.{step:04d}.json"
                if report_path.exists():
                    observed = _load_canonical(
                        report_path, f"long execution {step}"
                    )
                    if observed != report:
                        raise QwenFullModelSimulationError(
                            f"replayed long report differs at step {step}"
                        )
                else:
                    publish_qwen_full_model_long_acceptance_execution_report(
                        report, report_path
                    )
                if request["output_role"] == "generated_token":
                    generated_count += 1
                    token = report["outputs"]["committed_logits"]["greedy_token_id"]
                    if token in session["generation"]["eos_token_ids"]:
                        raise QwenFullModelSimulationError(
                            f"unexpected early EOS at long step {step}"
                        )
                previous = report
                step += 1
                work_done += 1
                print(
                    f"step={step - 1} complete={step}/{TRANSACTION_COUNT} "
                    f"generated={generated_count}/{GENERATED_TOKEN_COUNT} "
                    f"input={request['token_id']} "
                    f"output={report['outputs']['committed_logits']['greedy_token_id']} "
                    f"report_id={report['report_id']}",
                    flush=True,
                )
                if step % arguments.checkpoint_interval == 0:
                    checkpoint_manifest, checkpoint_path = _publish_checkpoint(
                        simulator=simulator,
                        checkpoint_root=checkpoints_directory,
                        retain=arguments.retain_checkpoints,
                        previous_report=previous,
                        session=session,
                    )
                    print(
                        f"checkpoint_step={step} "
                        f"checkpoint_id={checkpoint_manifest['checkpoint_id']} "
                        f"checkpoint_path={checkpoint_path}",
                        flush=True,
                    )
            if work_done and (
                checkpoint_manifest is None
                or checkpoint_manifest["next_step_index"] != step
            ):
                checkpoint_manifest, checkpoint_path = _publish_checkpoint(
                    simulator=simulator,
                    checkpoint_root=checkpoints_directory,
                    retain=arguments.retain_checkpoints,
                    previous_report=previous,
                    session=session,
                )
                print(
                    f"checkpoint_step={step} "
                    f"checkpoint_id={checkpoint_manifest['checkpoint_id']} "
                    f"checkpoint_path={checkpoint_path}",
                    flush=True,
                )

        if step != TRANSACTION_COUNT:
            print(f"status=checkpointed_incomplete next_step={step}")
            return 0
        completed, request_only = _frontier(requests_directory, executions_directory)
        if completed != TRANSACTION_COUNT or request_only:
            raise QwenFullModelSimulationError(
                "completed long campaign artifact frontier differs"
            )
        result = build_long_acceptance_session_execution(
            session,
            _ArtifactSequence(requests_directory, "request", TRANSACTION_COUNT),
            _ArtifactSequence(executions_directory, "execution", TRANSACTION_COUNT),
            decode_token_ids=lambda token_ids: tokenizer.decode(
                token_ids, skip_special_tokens=False
            ),
        )
        aggregate_validator.validate(result)
        aggregate_path = output / "session_execution.json"
        if aggregate_path.exists():
            if _load_canonical(aggregate_path, "long aggregate") != result:
                raise QwenFullModelSimulationError(
                    "existing long aggregate differs from reconstruction"
                )
        else:
            publish_long_acceptance_session_execution(
                result, session, aggregate_path
            )
    except (
        OSError,
        ArtifactError,
        QwenFullModelCheckpointError,
        QwenLongAcceptanceArtifactError,
        QwenFullModelSimulationError,
        ValidationError,
        SchemaError,
    ) as exc:
        parser.error(str(exc))
    print(f"status={result['status']}")
    print(f"session_execution_id={result['session_execution_id']}")
    print(f"generated_token_ids={result['generated_token_ids']}")
    print(f"generated_text={result['decoded']['generated_text']!r}")
    print(f"aggregate_counter_sha256={result['aggregate_counter_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
