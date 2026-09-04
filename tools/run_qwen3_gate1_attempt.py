#!/usr/bin/env python3
"""Launch one governed Qwen exact-8K Gate-1 production attempt.

The long-running model tools deliberately remain ordinary foreground programs.
This wrapper supplies the missing attempt boundary around them: a unique
create-once namespace, an exclusive-host and memory preflight, retained logs and
``/usr/bin/time -v`` output, and a canonical diagnostic record when the child
raises, exits unsuccessfully, or is terminated.  A diagnostic failure record
is never token evidence and is never accepted as TPOT evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
from typing import Any, BinaryIO, Callable, Mapping
import uuid


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.tensor_accelerator.common import (  # noqa: E402
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    publish_bytes_atomic_no_replace,
)


LAUNCH_SCHEMA = "opentallas.qwen3.gate1_attempt_launch.v1"
PREFLIGHT_SCHEMA = "opentallas.qwen3.gate1_host_preflight.v1"
SUCCESS_SCHEMA = "opentallas.qwen3.gate1_attempt_result.v1"
FAILURE_SCHEMA = "opentallas.qwen3.gate1_failed_attempt.v1"
WRAPPER_VERSION = "qwen3_gate1_attempt.py:v1"
WORKLOAD_ID = "TA-QW-8K-1"
WORKLOAD_DIGEST = (
    "5c8fce7d61afd1e06b7a061133c0a6d639fac7d65739227f84e199d6c870297e"
)
TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
MINIMUM_AVAILABLE_BYTES = 100 << 30
HOST_LOCK = Path("/tmp/opentallas-qwen3-gate1-production.lock")
TIME_BINARY = Path("/usr/bin/time")
ATTEMPT_ID = re.compile(
    r"^(oracle|hbm-a|hbm-b|rom)-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{16}$"
)

QWEN_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
WORKLOAD = REPO / "build/workloads/qwen3-8b/TA-QW-8K-1.json"
KERNEL_IR = REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"
CHECKPOINT_LOCK = (
    REPO
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
CONSTRUCTION = REPO / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
ORACLE = REPO / "results/abi3/qwen3_reference_oracle_exact_8k_chat.json"
CANONICAL_RESULTS = {
    "oracle": ORACLE,
    "hbm-a": REPO / "results/abi3/w10/qwen3_8b_hbm_natural_a.json",
    "hbm-b": REPO / "results/abi3/w10/qwen3_8b_hbm_natural_b.json",
    "rom": REPO / "results/abi3/w10/qwen3_8b_rom_natural.json",
}
CAPABILITIES = {
    "hbm-a": REPO / "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "hbm-b": REPO / "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "rom": REPO / "configs/hardware/abi3_capability/rom_qwen3.json",
}
BACKENDS = {"hbm-a": "hbm_sram", "hbm-b": "hbm_sram", "rom": "rom_qwen3"}
PREREQUISITES = {
    "oracle": (),
    "hbm-a": ("oracle",),
    "hbm-b": ("oracle", "hbm-a"),
    "rom": ("oracle", "hbm-a", "hbm-b"),
}
CONFLICTING_PROGRAMS = frozenset(
    {
        "run_accelerator_tokens.py",
        "run_abi3_cycle.py",
        "run_deepseek_v4_reference_oracle.py",
        "run_qwen3_reference_oracle.py",
        "run_qwen3_gate1_attempt.py",
    }
)


class AttemptError(RuntimeError):
    """A governed attempt could not be launched or completed."""


@dataclass(frozen=True)
class AttemptPaths:
    attempt_id: str
    lane: str
    root: Path
    output: Path
    deployment: Path | None
    stdout: Path
    stderr: Path
    timing: Path
    launch: Path
    preflight: Path
    success: Path
    failure: Path


@dataclass(frozen=True)
class LaneSpec:
    command: tuple[str, ...]
    environment: Mapping[str, str]
    input_identity: Mapping[str, object]
    canonical_result: Path


@dataclass(frozen=True)
class ChildOutcome:
    returncode: int
    requested_signal: int | None
    started_unix_ns: int
    finished_unix_ns: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _record_path(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _file_identity(path: Path) -> dict[str, object]:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise AttemptError(f"required file is unavailable: {resolved}")
    return {
        "path": _record_path(resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _identity_if_file(path: Path) -> dict[str, object] | None:
    try:
        return _file_identity(path) if path.is_file() else None
    except OSError:
        return None


def _new_attempt_id(lane: str) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{lane}-{stamp}-{uuid.uuid4().hex[:16]}"


def allocate_attempt(attempts_root: Path, lane: str, attempt_id: str | None) -> AttemptPaths:
    identifier = attempt_id or _new_attempt_id(lane)
    if not ATTEMPT_ID.fullmatch(identifier) or not identifier.startswith(f"{lane}-"):
        raise AttemptError("attempt id does not match its governed lane and format")
    base = Path(attempts_root).resolve()
    base.mkdir(parents=True, exist_ok=True)
    root = base / identifier
    root.mkdir(mode=0o700, exist_ok=False)
    return AttemptPaths(
        attempt_id=identifier,
        lane=lane,
        root=root,
        output=root / "result.json",
        deployment=None if lane == "oracle" else root / "deployment",
        stdout=root / "stdout.log",
        stderr=root / "stderr.log",
        timing=root / "time.txt",
        launch=root / "launch.json",
        preflight=root / "preflight.json",
        success=root / "attempt.json",
        failure=root / "failure.json",
    )


def _open_evidence_files(paths: AttemptPaths) -> tuple[BinaryIO, BinaryIO]:
    stdout = paths.stdout.open("xb", buffering=0)
    stderr: BinaryIO | None = None
    try:
        stderr = paths.stderr.open("xb", buffering=0)
        # Reserve the time path without allowing /usr/bin/time to truncate a
        # pre-existing file.  ``-a`` below only appends to this exact inode.
        with paths.timing.open("xb"):
            pass
    except BaseException:
        if stderr is not None:
            stderr.close()
        stdout.close()
        raise
    assert stderr is not None
    return stdout, stderr


def _meminfo(path: Path) -> dict[str, int]:
    required = {"MemAvailable", "SwapFree", "SwapTotal"}
    values: dict[str, int] = {}
    try:
        for line in Path(path).read_text(encoding="ascii").splitlines():
            name, separator, rest = line.partition(":")
            if separator and name in required:
                fields = rest.split()
                if len(fields) != 2 or fields[1] != "kB":
                    raise AttemptError(f"/proc/meminfo field {name} is malformed")
                values[name] = int(fields[0]) * 1024
    except (OSError, UnicodeError, ValueError) as exc:
        raise AttemptError(f"cannot read host memory preflight: {exc}") from exc
    if set(values) != required:
        raise AttemptError("/proc/meminfo lacks required memory or swap fields")
    return values


def _parent_pid(proc_root: Path, pid: int) -> int | None:
    try:
        # status avoids the command-name parentheses ambiguity in /proc/PID/stat.
        for line in (proc_root / str(pid) / "status").read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _ancestor_pids(proc_root: Path, pid: int) -> set[int]:
    ancestors = {pid}
    cursor = pid
    while cursor > 1:
        parent = _parent_pid(proc_root, cursor)
        if parent is None or parent <= 0 or parent in ancestors:
            break
        ancestors.add(parent)
        cursor = parent
    return ancestors


def _conflicting_processes(proc_root: Path, own_pid: int) -> list[dict[str, object]]:
    ignored = _ancestor_pids(proc_root, own_pid)
    conflicts: list[dict[str, object]] = []
    try:
        entries = list(Path(proc_root).iterdir())
    except OSError as exc:
        raise AttemptError(f"cannot enumerate host processes: {exc}") from exc
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) in ignored:
            continue
        pid = int(entry.name)
        try:
            payload = (entry / "cmdline").read_bytes()
        except OSError:
            continue  # a process may exit during the snapshot
        arguments = [
            token.decode("utf-8", errors="replace")
            for token in payload.split(b"\0")
            if token
        ]
        matches = sorted(
            name
            for name in CONFLICTING_PROGRAMS
            if any(Path(argument).name == name for argument in arguments)
        )
        if matches:
            conflicts.append(
                {
                    "pid": pid,
                    "programs": matches,
                    "cmdline_sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    return sorted(conflicts, key=lambda item: int(item["pid"]))


def host_preflight(
    *,
    proc_root: Path = Path("/proc"),
    lock_path: Path = HOST_LOCK,
    own_pid: int | None = None,
) -> tuple[dict[str, object], list[str], BinaryIO | None]:
    """Acquire the global launch lock and prove memory/swap/process isolation."""

    pid = os.getpid() if own_pid is None else own_pid
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle: BinaryIO | None = lock_path.open("a+b", buffering=0)
    lock_acquired = False
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_acquired = True
    except BlockingIOError:
        lock_handle.close()
        lock_handle = None

    try:
        values = _meminfo(Path(proc_root) / "meminfo")
        available = values["MemAvailable"]
        swap_used = max(values["SwapTotal"] - values["SwapFree"], 0)
        conflicts = _conflicting_processes(Path(proc_root), pid)
    except BaseException:
        if lock_handle is not None:
            lock_handle.close()
        raise
    checks = {
        "global_launch_lock_acquired": lock_acquired,
        "mem_available_at_least_100_gib": available >= MINIMUM_AVAILABLE_BYTES,
        "swap_used_bytes_zero": swap_used == 0,
        "no_conflicting_model_process": not conflicts,
    }
    problems: list[str] = []
    if not lock_acquired:
        problems.append("another governed Gate-1 wrapper owns the host lock")
    if available < MINIMUM_AVAILABLE_BYTES:
        problems.append(
            f"MemAvailable is {available} bytes, below {MINIMUM_AVAILABLE_BYTES}"
        )
    if swap_used:
        problems.append(f"swap has {swap_used} bytes in use")
    if conflicts:
        problems.append("another long model or cycle process owns the host")
    return {
        "schema": PREFLIGHT_SCHEMA,
        "requirements": {
            "exclusive_host": True,
            "minimum_mem_available_bytes": MINIMUM_AVAILABLE_BYTES,
            "swap_used_bytes": 0,
        },
        "observed": {
            "mem_available_bytes": available,
            "swap_total_bytes": values["SwapTotal"],
            "swap_free_bytes": values["SwapFree"],
            "swap_used_bytes": swap_used,
            "conflicting_processes": conflicts,
            "host_lock_path": str(lock_path),
        },
        "checks": checks,
        "accepted": not problems,
        "problems": problems,
    }, problems, lock_handle


def _load_result(path: Path) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (ArtifactError, OSError, ValueError) as exc:
        raise AttemptError(f"child result is not governed JSON: {exc}") from exc


def _is_production_oracle(body: Mapping[str, Any]) -> bool:
    result = (body.get("results") or {}).get(WORKLOAD_ID)
    generated = result.get("generated_token_ids") if isinstance(result, dict) else None
    eos_positions = (
        [
            index
            for index, token in enumerate(generated)
            if token in {151_645, 151_643}
        ]
        if isinstance(generated, list)
        else []
    )
    terminal_valid = isinstance(generated, list) and (
        eos_positions == [len(generated) - 1]
        or (not eos_positions and len(generated) == 256)
    )
    producer = body.get("producer")
    checkpoint = body.get("production_checkpoint_preflight")
    return bool(
        body.get("schema") == "opentallas.abi3.reference_oracle.v1"
        and body.get("model_id") == "qwen3-8b"
        and body.get("tokenizer_sha256") == TOKENIZER_SHA256
        and isinstance(producer, dict)
        and producer.get("tool_version") == "qwen3_reference_oracle.py:v2"
        and producer.get("selected_workload_ids") == [WORKLOAD_ID]
        and isinstance(checkpoint, dict)
        and checkpoint.get("completed_before_model_framework_import") is True
        and checkpoint.get("full_byte_hash_verified") is True
        and checkpoint.get("lock_id") == CHECKPOINT_LOCK_ID
        and (body.get("production_launch") or {}).get("explicitly_requested") is True
        and isinstance(result, dict)
        and result.get("workload_digest") == WORKLOAD_DIGEST
        and result.get("prompt_token_count") == 8_000
        and isinstance(generated, list)
        and bool(generated)
        and len(generated) <= 256
        and all(
            isinstance(token, int)
            and not isinstance(token, bool)
            and 0 <= token < 151_669
            for token in generated
        )
        and result.get("generated_token_count") == len(generated)
        and terminal_valid
        and result.get("stop_reason")
        == ("eos" if eos_positions else "max_new_tokens")
    )


def _prerequisite_problems(lane: str) -> list[str]:
    problems: list[str] = []
    for prerequisite in PREREQUISITES[lane]:
        path = CANONICAL_RESULTS[prerequisite]
        if not path.is_file():
            problems.append(f"required prior {prerequisite} result is absent: {path}")
            continue
        try:
            body = _load_result(path)
        except AttemptError as exc:
            problems.append(str(exc))
            continue
        if prerequisite == "oracle":
            valid = _is_production_oracle(body)
        else:
            valid = (
                body.get("schema") == "opentallas.abi3.accelerator_tokens.v1"
                and body.get("status") == "pass"
                and (body.get("terminal_acceptance") or {}).get("accepted") is True
            )
        if not valid:
            problems.append(f"required prior {prerequisite} result is not accepted")
    if CANONICAL_RESULTS[lane].exists() or CANONICAL_RESULTS[lane].is_symlink():
        problems.append(
            f"canonical {lane} result already exists and will not be replaced"
        )
    return problems


def _lane_spec(lane: str, paths: AttemptPaths) -> LaneSpec:
    controlled_environment = {
        "PYTHONPATH": ".",
        "OMP_NUM_THREADS": "8",
        "OPENBLAS_NUM_THREADS": "8",
        "MKL_NUM_THREADS": "8",
        "NUMEXPR_NUM_THREADS": "8",
        "VECLIB_MAXIMUM_THREADS": "8",
    }
    if lane == "oracle":
        command = (
            sys.executable,
            "tools/run_qwen3_reference_oracle.py",
            "--gate-1-production",
            "--checkpoint-lock",
            _record_path(CHECKPOINT_LOCK),
            "--exact-8k-construction",
            _record_path(CONSTRUCTION),
            "--output",
            str(paths.output),
        )
        inputs = {
            "checkpoint_lock": _file_identity(CHECKPOINT_LOCK),
            "construction": _file_identity(CONSTRUCTION),
            "oracle_tool": _file_identity(REPO / "tools/run_qwen3_reference_oracle.py"),
            "workload": _file_identity(WORKLOAD),
            "workload_index": _file_identity(WORKLOAD.parent / "index.json"),
        }
    else:
        assert paths.deployment is not None
        capability = CAPABILITIES[lane]
        command = (
            sys.executable,
            "tools/run_accelerator_tokens.py",
            "--kernel-ir",
            _record_path(KERNEL_IR),
            "--backend",
            BACKENDS[lane],
            "--capability",
            _record_path(capability),
            "--workload",
            _record_path(WORKLOAD),
            "--reference",
            _record_path(ORACLE),
            "--checkpoint",
            str(QWEN_SNAPSHOT),
            "--publish",
            str(paths.deployment),
            "--max-new-tokens",
            "256",
            "--terminal-contract",
            "exact_eos_or_cap",
            "--output",
            str(paths.output),
        )
        controlled_environment["OPENTALLAS_ABI3_BACKEND"] = "numpy"
        inputs = {
            "accelerator_tool": _file_identity(REPO / "tools/run_accelerator_tokens.py"),
            "capability": _file_identity(capability),
            "checkpoint_lock": _file_identity(CHECKPOINT_LOCK),
            "kernel_ir": _file_identity(KERNEL_IR),
            # A missing or malformed prior oracle is a recorded preflight
            # refusal below, not an unclassified Python launch exception.
            "oracle": _identity_if_file(ORACLE),
            "workload": _file_identity(WORKLOAD),
        }
    return LaneSpec(command, controlled_environment, inputs, CANONICAL_RESULTS[lane])


class SignalRelay:
    """Record wrapper termination and forward it to the child's process group."""

    def __init__(self) -> None:
        self.requested_signal: int | None = None
        self.child: subprocess.Popen[bytes] | None = None
        self.previous: dict[int, Any] = {}

    def _handle(self, signum: int, _frame: object) -> None:
        if self.requested_signal is None:
            self.requested_signal = signum
        child = self.child
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass

    def install(self) -> None:
        for signum in (signal.SIGTERM, signal.SIGINT):
            self.previous[signum] = signal.getsignal(signum)
            signal.signal(signum, self._handle)

    def restore(self) -> None:
        for signum, handler in self.previous.items():
            signal.signal(signum, handler)
        self.previous.clear()


def _run_child(
    spec: LaneSpec,
    paths: AttemptPaths,
    stdout: BinaryIO,
    stderr: BinaryIO,
    relay: SignalRelay,
) -> ChildOutcome:
    environment = os.environ.copy()
    environment.update(spec.environment)
    command = (
        str(TIME_BINARY),
        "-v",
        "-a",
        "-o",
        str(paths.timing),
        *spec.command,
    )
    started = time.time_ns()
    if relay.requested_signal is not None:
        return ChildOutcome(
            128 + relay.requested_signal,
            relay.requested_signal,
            started,
            time.time_ns(),
        )
    child = subprocess.Popen(
        command,
        cwd=REPO,
        env=environment,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )
    relay.child = child
    # If a signal arrived while Popen was between fork and returning, the
    # handler recorded it but could not yet see the child.  Close that narrow
    # race immediately after assigning the process-group owner.
    if relay.requested_signal is not None and child.poll() is None:
        try:
            os.killpg(child.pid, relay.requested_signal)
        except ProcessLookupError:
            pass
    returncode = child.wait()
    relay.child = None
    return ChildOutcome(returncode, relay.requested_signal, started, time.time_ns())


def _validate_success(lane: str, output: Path) -> dict[str, Any]:
    body = _load_result(output)
    if lane == "oracle":
        if not _is_production_oracle(body):
            raise AttemptError("oracle child result does not satisfy Gate-1 structure")
    elif (
        body.get("schema") != "opentallas.abi3.accelerator_tokens.v1"
        or body.get("status") != "pass"
        or body.get("failure") is not None
        or body.get("token_legitimacy_problems") != []
        or (body.get("terminal_acceptance") or {}).get("accepted") is not True
        or (body.get("oracle") or {}).get("agreement") is not True
    ):
        raise AttemptError("accelerator child result does not satisfy Gate-1 structure")
    return body


def _attempt_artifacts(paths: AttemptPaths) -> dict[str, object]:
    deployment = None
    if paths.deployment is not None and paths.deployment.is_dir():
        deployment = {
            name: _identity_if_file(paths.deployment / name)
            for name in ("deployment.json", "descriptors.bin", "program.bin")
        }
    return {
        "launch": _identity_if_file(paths.launch),
        "preflight": _identity_if_file(paths.preflight),
        "stdout_log": _identity_if_file(paths.stdout),
        "stderr_log": _identity_if_file(paths.stderr),
        "time_verbose": _identity_if_file(paths.timing),
        "child_result": _identity_if_file(paths.output),
        "deployment": deployment,
    }


def _publish_failure(
    paths: AttemptPaths,
    *,
    kind: str,
    detail: str,
    returncode: int | None = None,
    termination_signal: int | None = None,
) -> None:
    body = {
        "schema": FAILURE_SCHEMA,
        "status": "terminated" if termination_signal is not None else "failed",
        "evidence_class": "diagnostic_failed_attempt_only",
        "attempt_id": paths.attempt_id,
        "lane": paths.lane,
        "failure": {
            "kind": kind,
            "detail": detail,
            "returncode": returncode,
            "termination_signal": termination_signal,
        },
        "claim_boundary": {
            "token_evidence_eligible": False,
            "tpot_evidence_eligible": False,
            "accepted_generated_tokens": None,
            "may_satisfy_gate_1": False,
            "may_satisfy_gate_2": False,
        },
        "artifacts": _attempt_artifacts(paths),
    }
    publish_bytes_atomic_no_replace(paths.failure, canonical_json_bytes(body))


def run_attempt(
    paths: AttemptPaths,
    *,
    preflight_fn: Callable[
        [], tuple[dict[str, object], list[str], BinaryIO | None]
    ] = host_preflight,
    lane_spec_fn: Callable[[str, AttemptPaths], LaneSpec] = _lane_spec,
) -> int:
    stdout: BinaryIO | None = None
    stderr: BinaryIO | None = None
    lock_handle: BinaryIO | None = None
    relay = SignalRelay()
    relay.install()
    try:
        stdout, stderr = _open_evidence_files(paths)
        spec = lane_spec_fn(paths.lane, paths)
        launch = {
            "schema": LAUNCH_SCHEMA,
            "wrapper": {
                "path": _record_path(Path(__file__)),
                "version": WRAPPER_VERSION,
                "source_sha256": _sha256_file(Path(__file__)),
            },
            "attempt_id": paths.attempt_id,
            "lane": paths.lane,
            "command": list(spec.command),
            "environment": dict(sorted(spec.environment.items())),
            "input_identity": spec.input_identity,
            "paths": {
                "root": _record_path(paths.root),
                "child_result": _record_path(paths.output),
                "deployment": (
                    None if paths.deployment is None else _record_path(paths.deployment)
                ),
                "stdout_log": _record_path(paths.stdout),
                "stderr_log": _record_path(paths.stderr),
                "time_verbose": _record_path(paths.timing),
                "canonical_result": _record_path(spec.canonical_result),
            },
            "launcher_identity": {
                "python": _file_identity(Path(sys.executable)),
                "time": _file_identity(TIME_BINARY),
            },
        }
        publish_bytes_atomic_no_replace(paths.launch, canonical_json_bytes(launch))

        preflight, problems, lock_handle = preflight_fn()
        problems = [*problems, *_prerequisite_problems(paths.lane)]
        preflight = {
            **preflight,
            "accepted": not problems,
            "problems": problems,
            "prerequisites": list(PREREQUISITES[paths.lane]),
        }
        publish_bytes_atomic_no_replace(
            paths.preflight, canonical_json_bytes(preflight)
        )
        if relay.requested_signal is not None:
            _publish_failure(
                paths,
                kind="wrapper_signal_before_child",
                detail="wrapper received a termination signal before child launch",
                termination_signal=relay.requested_signal,
            )
            return 128 + relay.requested_signal
        if problems:
            _publish_failure(
                paths,
                kind="preflight_refusal",
                detail="; ".join(problems),
            )
            return 2

        outcome = _run_child(spec, paths, stdout, stderr, relay)
        stdout.flush()
        stderr.flush()
        if outcome.returncode != 0 or outcome.requested_signal is not None:
            terminated_by = outcome.requested_signal
            if terminated_by is None and outcome.returncode < 0:
                terminated_by = -outcome.returncode
            if terminated_by is None:
                for candidate in (signal.SIGTERM, signal.SIGINT):
                    if outcome.returncode == 128 + candidate:
                        terminated_by = candidate
                        break
            _publish_failure(
                paths,
                kind=("external_termination" if terminated_by else "child_exit"),
                detail=(
                    "production child did not complete successfully; logs and time "
                    "are retained for diagnosis"
                ),
                returncode=outcome.returncode,
                termination_signal=terminated_by,
            )
            return (
                128 + terminated_by
                if terminated_by is not None
                else max(1, outcome.returncode)
            )

        _validate_success(paths.lane, paths.output)
        payload = paths.output.read_bytes()
        publish_bytes_atomic_no_replace(spec.canonical_result, payload)
        success = {
            "schema": SUCCESS_SCHEMA,
            "status": "completed",
            "evidence_class": "production_attempt_wrapper",
            "attempt_id": paths.attempt_id,
            "lane": paths.lane,
            "child": {
                "returncode": outcome.returncode,
                "started_unix_ns": outcome.started_unix_ns,
                "finished_unix_ns": outcome.finished_unix_ns,
            },
            "canonical_result": _file_identity(spec.canonical_result),
            "artifacts": _attempt_artifacts(paths),
            "claim_boundary": {
                "wrapper_itself_is_token_evidence": False,
                "child_result_requires_independent_gate_check": True,
                "wrapper_wall_time_is_target_tpot": False,
            },
        }
        publish_bytes_atomic_no_replace(paths.success, canonical_json_bytes(success))
        return 0
    except Exception as exc:
        child = relay.child
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            finally:
                relay.child = None
        if stderr is not None:
            stderr.write(traceback.format_exc().encode("utf-8", errors="replace"))
            stderr.flush()
        try:
            _publish_failure(
                paths,
                kind="python_exception",
                detail=f"{type(exc).__name__}: {exc}"[:2000],
                termination_signal=relay.requested_signal,
            )
        except FileExistsError:
            pass
        return 3
    finally:
        relay.restore()
        if stdout is not None:
            stdout.close()
        if stderr is not None:
            stderr.close()
        if lock_handle is not None:
            lock_handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", choices=tuple(CANONICAL_RESULTS))
    parser.add_argument(
        "--attempts-root",
        type=Path,
        default=REPO / "results/abi3/w10/attempts",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="optional governed id; omitted creates a UTC-plus-random unique id",
    )
    args = parser.parse_args()
    try:
        paths = allocate_attempt(args.attempts_root, args.lane, args.attempt_id)
    except (AttemptError, FileExistsError, OSError) as exc:
        print(f"cannot allocate unique Gate-1 attempt: {exc}", file=sys.stderr)
        return 1
    print(f"Gate-1 attempt {paths.attempt_id}: {paths.root}", flush=True)
    result = run_attempt(paths)
    if result == 0:
        print(f"completed {paths.lane}: {paths.success}", flush=True)
    else:
        print(f"failed {paths.lane}: {paths.failure}", file=sys.stderr, flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
