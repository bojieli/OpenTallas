"""Focused tests for the Qwen Gate-1 production-attempt boundary."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "run_qwen3_gate1_attempt",
    REPO / "tools/run_qwen3_gate1_attempt.py",
)
attempt = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules[_spec.name] = attempt
_spec.loader.exec_module(attempt)


def _id(lane: str, suffix: str = "0123456789abcdef") -> str:
    return f"{lane}-20260904T010203Z-{suffix}"


def _meminfo(*, available_gib: int, swap_total_gib: int, swap_free_gib: int) -> str:
    return (
        f"MemAvailable: {available_gib * 1024 * 1024} kB\n"
        f"SwapTotal: {swap_total_gib * 1024 * 1024} kB\n"
        f"SwapFree: {swap_free_gib * 1024 * 1024} kB\n"
    )


def _process(proc: Path, pid: int, command: list[str], parent: int = 0) -> None:
    root = proc / str(pid)
    root.mkdir()
    (root / "status").write_text(f"Name:\ttest\nPPid:\t{parent}\n")
    (root / "cmdline").write_bytes(b"\0".join(s.encode() for s in command) + b"\0")


def _accepted_preflight():
    return (
        {
            "schema": attempt.PREFLIGHT_SCHEMA,
            "requirements": {},
            "observed": {},
            "checks": {"synthetic": True},
            "accepted": True,
            "problems": [],
        },
        [],
        None,
    )


def _spec_for(command: tuple[str, ...], canonical: Path) -> attempt.LaneSpec:
    return attempt.LaneSpec(
        command=command,
        environment={"PYTHONPATH": "."},
        input_identity={},
        canonical_result=canonical,
    )


def test_attempt_namespace_is_unique_create_once(tmp_path: Path) -> None:
    first = attempt.allocate_attempt(tmp_path, "hbm-a", _id("hbm-a"))

    assert first.root.is_dir()
    assert first.output.parent == first.root
    assert first.deployment == first.root / "deployment"
    assert len(
        {
            first.output,
            first.deployment,
            first.stdout,
            first.stderr,
            first.timing,
        }
    ) == 5
    with pytest.raises(FileExistsError):
        attempt.allocate_attempt(tmp_path, "hbm-a", _id("hbm-a"))
    with pytest.raises(attempt.AttemptError, match="governed lane"):
        attempt.allocate_attempt(tmp_path, "rom", _id("hbm-a", "f" * 16))


def test_accelerator_lane_uses_unique_paths_and_no_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(attempt, "ORACLE", tmp_path / "pending-oracle.json")
    paths = attempt.allocate_attempt(
        tmp_path, "hbm-a", _id("hbm-a", "aaaaaaaaaaaaaaaa")
    )
    spec = attempt._lane_spec("hbm-a", paths)

    assert "--force" not in spec.command
    assert spec.command[spec.command.index("--output") + 1] == str(paths.output)
    assert spec.command[spec.command.index("--publish") + 1] == str(
        paths.deployment
    )
    assert spec.command[spec.command.index("--max-new-tokens") + 1] == "256"
    assert spec.command[spec.command.index("--terminal-contract") + 1] == (
        "exact_eos_or_cap"
    )
    assert spec.canonical_result == attempt.CANONICAL_RESULTS["hbm-a"]
    assert spec.input_identity["oracle"] is None


def test_host_preflight_accepts_100_gib_and_fully_free_swap(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "meminfo").write_text(
        _meminfo(available_gib=100, swap_total_gib=8, swap_free_gib=8)
    )
    _process(proc, 100, ["python3", "tools/run_qwen3_gate1_attempt.py"], 50)
    _process(proc, 50, ["bash"], 0)
    _process(proc, 200, ["python3", "unrelated.py"], 0)

    evidence, problems, lock = attempt.host_preflight(
        proc_root=proc, lock_path=tmp_path / "host.lock", own_pid=100
    )
    try:
        assert problems == []
        assert evidence["accepted"] is True
        assert all(evidence["checks"].values())
        assert evidence["observed"]["mem_available_bytes"] == 100 << 30
        assert evidence["observed"]["swap_used_bytes"] == 0
    finally:
        assert lock is not None
        lock.close()


def test_host_preflight_rejects_low_memory_used_swap_and_model_owner(
    tmp_path: Path,
) -> None:
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "meminfo").write_text(
        _meminfo(available_gib=99, swap_total_gib=8, swap_free_gib=7)
    )
    _process(proc, 100, ["python3", "tools/run_qwen3_gate1_attempt.py"], 0)
    _process(proc, 27419, ["python3", "tools/run_accelerator_tokens.py"], 0)

    evidence, problems, lock = attempt.host_preflight(
        proc_root=proc, lock_path=tmp_path / "host.lock", own_pid=100
    )
    try:
        assert evidence["accepted"] is False
        assert evidence["checks"]["mem_available_at_least_100_gib"] is False
        assert evidence["checks"]["swap_used_bytes_zero"] is False
        assert evidence["checks"]["no_conflicting_model_process"] is False
        assert any("MemAvailable" in problem for problem in problems)
        assert any("swap" in problem for problem in problems)
        assert any("owns the host" in problem for problem in problems)
        assert evidence["observed"]["conflicting_processes"] == [
            {
                "pid": 27419,
                "programs": ["run_accelerator_tokens.py"],
                "cmdline_sha256": attempt.hashlib.sha256(
                    b"python3\0tools/run_accelerator_tokens.py\0"
                ).hexdigest(),
            }
        ]
    finally:
        assert lock is not None
        lock.close()


def test_preflight_refusal_retains_diagnostic_only_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(tmp_path, "oracle", _id("oracle"))
    canonical = tmp_path / "canonical.json"
    invoked = False

    def refused():
        return (
            {
                "schema": attempt.PREFLIGHT_SCHEMA,
                "checks": {"mem_available_at_least_100_gib": False},
            },
            ["MemAvailable is below the production minimum"],
            None,
        )

    def lane_spec(_lane, _paths):
        nonlocal invoked
        invoked = True
        return _spec_for((sys.executable, "-c", "raise AssertionError"), canonical)

    monkeypatch.setattr(attempt, "_prerequisite_problems", lambda _lane: [])
    assert attempt.run_attempt(
        paths, preflight_fn=refused, lane_spec_fn=lane_spec
    ) == 2
    assert invoked is True
    failure = attempt.load_strict_json(paths.failure)
    assert failure["failure"]["kind"] == "preflight_refusal"
    assert failure["claim_boundary"] == {
        "accepted_generated_tokens": None,
        "may_satisfy_gate_1": False,
        "may_satisfy_gate_2": False,
        "token_evidence_eligible": False,
        "tpot_evidence_eligible": False,
    }
    assert "generated_token_ids" not in failure
    assert not paths.output.exists()
    assert not canonical.exists()


def test_python_exception_retains_canonical_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(tmp_path, "oracle", _id("oracle"))

    def broken(_lane, _paths):
        raise RuntimeError("synthetic launch exception")

    monkeypatch.setattr(attempt, "_prerequisite_problems", lambda _lane: [])
    assert attempt.run_attempt(
        paths, preflight_fn=_accepted_preflight, lane_spec_fn=broken
    ) == 3
    raw = paths.failure.read_bytes()
    failure = attempt.load_strict_json(paths.failure)
    assert raw == attempt.canonical_json_bytes(failure)
    assert failure["failure"]["kind"] == "python_exception"
    assert "synthetic launch exception" in failure["failure"]["detail"]
    assert failure["claim_boundary"]["token_evidence_eligible"] is False
    assert b"RuntimeError: synthetic launch exception" in paths.stderr.read_bytes()


def test_child_sigterm_retains_termination_not_token_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(tmp_path, "oracle", _id("oracle"))
    canonical = tmp_path / "canonical.json"
    command = (
        sys.executable,
        "-c",
        "import os,signal; os.kill(os.getpid(), signal.SIGTERM)",
    )
    monkeypatch.setattr(attempt, "_prerequisite_problems", lambda _lane: [])

    assert attempt.run_attempt(
        paths,
        preflight_fn=_accepted_preflight,
        lane_spec_fn=lambda _lane, _paths: _spec_for(command, canonical),
    ) == 128 + signal.SIGTERM
    failure = attempt.load_strict_json(paths.failure)
    assert failure["status"] == "terminated"
    assert failure["failure"]["kind"] == "external_termination"
    assert failure["failure"]["termination_signal"] == signal.SIGTERM
    assert failure["claim_boundary"]["token_evidence_eligible"] is False
    assert failure["claim_boundary"]["tpot_evidence_eligible"] is False
    assert paths.timing.stat().st_size > 0
    assert not canonical.exists()


def test_child_python_exception_retains_logs_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(
        tmp_path, "oracle", _id("oracle", "1111111111111111")
    )
    canonical = tmp_path / "canonical.json"
    command = (
        sys.executable,
        "-c",
        "raise RuntimeError('synthetic child exception')",
    )
    monkeypatch.setattr(attempt, "_prerequisite_problems", lambda _lane: [])

    assert attempt.run_attempt(
        paths,
        preflight_fn=_accepted_preflight,
        lane_spec_fn=lambda _lane, _paths: _spec_for(command, canonical),
    ) == 1
    failure = attempt.load_strict_json(paths.failure)
    assert failure["failure"] == {
        "detail": (
            "production child did not complete successfully; logs and time "
            "are retained for diagnosis"
        ),
        "kind": "child_exit",
        "returncode": 1,
        "termination_signal": None,
    }
    assert b"RuntimeError: synthetic child exception" in paths.stderr.read_bytes()
    assert failure["artifacts"]["stderr_log"]["sha256"] == attempt._sha256_file(
        paths.stderr
    )
    assert not canonical.exists()


def test_success_keeps_unique_result_and_publishes_no_replace_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(tmp_path, "oracle", _id("oracle"))
    canonical = tmp_path / "canonical.json"
    result = {
        "schema": "opentallas.abi3.reference_oracle.v1",
        "model_id": "qwen3-8b",
        "tokenizer_sha256": attempt.TOKENIZER_SHA256,
        "producer": {
            "tool_version": "qwen3_reference_oracle.py:v2",
            "selected_workload_ids": [attempt.WORKLOAD_ID],
        },
        "production_checkpoint_preflight": {
            "completed_before_model_framework_import": True,
            "full_byte_hash_verified": True,
            "lock_id": attempt.CHECKPOINT_LOCK_ID,
        },
        "production_launch": {"explicitly_requested": True},
        "results": {
            attempt.WORKLOAD_ID: {
                "workload_digest": attempt.WORKLOAD_DIGEST,
                "prompt_token_count": 8_000,
                "generated_token_ids": [18, 24, 16, 151645],
                "generated_token_count": 4,
                "stop_reason": "eos",
            }
        },
    }
    program = (
        "from pathlib import Path; "
        f"Path({str(paths.output)!r}).write_text({json.dumps(json.dumps(result))})"
    )
    monkeypatch.setattr(attempt, "_prerequisite_problems", lambda _lane: [])

    assert attempt.run_attempt(
        paths,
        preflight_fn=_accepted_preflight,
        lane_spec_fn=lambda _lane, _paths: _spec_for(
            (sys.executable, "-c", program), canonical
        ),
    ) == 0
    assert canonical.read_bytes() == paths.output.read_bytes()
    success = attempt.load_strict_json(paths.success)
    assert success["status"] == "completed"
    assert success["claim_boundary"]["wrapper_itself_is_token_evidence"] is False
    assert success["claim_boundary"]["wrapper_wall_time_is_target_tpot"] is False
    assert not paths.failure.exists()


def test_signal_relay_records_and_forwards_sigterm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []

    class Child:
        pid = 1234

        @staticmethod
        def poll():
            return None

    relay = attempt.SignalRelay()
    relay.child = Child()
    monkeypatch.setattr(os, "killpg", lambda pid, sig: calls.append((pid, sig)))

    relay._handle(signal.SIGTERM, None)

    assert relay.requested_signal == signal.SIGTERM
    assert calls == [(1234, signal.SIGTERM)]


def test_signal_before_spawn_cannot_start_a_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = attempt.allocate_attempt(
        tmp_path, "oracle", _id("oracle", "2222222222222222")
    )
    stdout, stderr = attempt._open_evidence_files(paths)
    relay = attempt.SignalRelay()
    relay.requested_signal = signal.SIGTERM
    monkeypatch.setattr(
        attempt.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("a child was started after SIGTERM"),
    )
    try:
        outcome = attempt._run_child(
            _spec_for((sys.executable, "-c", "pass"), tmp_path / "canonical"),
            paths,
            stdout,
            stderr,
            relay,
        )
    finally:
        stdout.close()
        stderr.close()

    assert outcome.returncode == 128 + signal.SIGTERM
    assert outcome.requested_signal == signal.SIGTERM
