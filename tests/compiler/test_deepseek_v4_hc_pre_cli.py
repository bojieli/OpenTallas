from __future__ import annotations

import importlib
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from compiler.ir.model import load_strict_json
from runtime.service_engine.deepseek_v4_hc_pre_executable import (
    DeepSeekV4HCPreExecutableServiceError,
)


cli_module = importlib.import_module("compiler.cli.main")

OFFICIAL_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_SNAPSHOT"
OFFICIAL_EVIDENCE_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"


def test_compose_cli_preserves_exact_repeatable_source_text_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"alpha\n")
    second.write_bytes("\N{GREEK SMALL LETTER BETA}".encode("utf-8"))
    captured: dict[str, Any] = {}
    lock = {"lock_id": "a" * 64}

    monkeypatch.setattr(cli_module, "load_checkpoint_lock", lambda path: lock)

    def compose(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "composition_id": "b" * 64,
            "request": {"shape": [2, 1, 4, 4096]},
            "status": "official_tokenizer_lookup_differential_composition_verified",
        }

    monkeypatch.setattr(
        cli_module,
        "build_deepseek_v4_hc_pre_input_request",
        compose,
    )
    output = tmp_path / "request"
    report = tmp_path / "report.json"
    status = cli_module.main(
        [
            "compose-deepseek-v4-hc-pre-input",
            "--snapshot",
            str(tmp_path / "snapshot"),
            "--lock",
            str(tmp_path / "lock.json"),
            "--lookup-deployment",
            str(tmp_path / "lookup-deployment"),
            "--lookup-request",
            str(tmp_path / "lookup-request.json"),
            "--lookup-result",
            str(tmp_path / "lookup-result.json"),
            "--lookup-differential",
            str(tmp_path / "lookup-differential.json"),
            "--executable-deployment",
            str(tmp_path / "executable"),
            "--executable-application",
            str(tmp_path / "application"),
            "--source-text-file",
            str(first),
            "--source-text-file",
            str(second),
            "--output",
            str(output),
            "--report-output",
            str(report),
        ]
    )

    assert status == 0
    assert captured["lock"] is lock
    assert captured["source_texts"] == ("alpha\n", "\N{GREEK SMALL LETTER BETA}")
    assert captured["output"] == output
    assert captured["report_output"] == report
    assert "composed 2x1 V4 HC_PRE input" in capsys.readouterr().out


def test_source_text_reader_rejects_nonregular_invalid_oversize_and_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="regular file"):
        cli_module._read_source_text_file(tmp_path)

    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff")
    with pytest.raises(RuntimeError, match="UTF-8"):
        cli_module._read_source_text_file(invalid)

    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * (cli_module._MAX_SOURCE_TEXT_FILE_BYTES + 1))
    with pytest.raises(RuntimeError, match="bound"):
        cli_module._read_source_text_file(oversized)

    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    symlink = tmp_path / "symlink.txt"
    symlink.symlink_to(target)
    with pytest.raises(RuntimeError, match="symlink"):
        cli_module._read_source_text_file(symlink)

    raced = tmp_path / "raced.txt"
    raced.write_text("before", encoding="utf-8")
    replacement = tmp_path / "replacement.txt"
    replacement.write_text("before", encoding="utf-8")
    real_pread = cli_module.os.pread
    replaced = False

    def replacing_pread(descriptor: int, count: int, offset: int) -> bytes:
        nonlocal replaced
        payload = real_pread(descriptor, count, offset)
        if not replaced:
            replacement.replace(raced)
            replaced = True
        return payload

    monkeypatch.setattr(cli_module.os, "pread", replacing_pread)
    with pytest.raises(RuntimeError, match="replaced"):
        cli_module._read_source_text_file(raced)
    assert replaced


def test_execute_and_verify_cli_map_exact_artifact_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    execution: dict[str, Any] = {}

    def execute(deployment: Path, request: Path, output: Path) -> Any:
        execution.update(
            deployment=deployment,
            request=request,
            output=output,
        )
        return SimpleNamespace(
            token_count=1,
            build_id="c" * 64,
            request_sha256="d" * 64,
            status="pass",
        )

    monkeypatch.setattr(
        cli_module,
        "execute_deepseek_v4_hc_pre_executable_deployment",
        execute,
    )
    deployment = tmp_path / "deployment"
    request = tmp_path / "request"
    result = tmp_path / "result"
    assert (
        cli_module.main(
            [
                "execute-deepseek-v4-hc-pre",
                "--deployment",
                str(deployment),
                "--request",
                str(request),
                "--output",
                str(result),
            ]
        )
        == 0
    )
    assert execution == {
        "deployment": deployment,
        "request": request / "request_manifest.json",
        "output": result,
    }
    assert "executed 1 token(s)" in capsys.readouterr().out

    lock = {"lock_id": "e" * 64}
    verification: dict[str, Any] = {}
    monkeypatch.setattr(cli_module, "load_checkpoint_lock", lambda path: lock)

    def verify(**kwargs: Any) -> dict[str, Any]:
        verification.update(kwargs)
        return {
            "comparisons": [{}] * 10,
            "logical_counters": {str(index): index for index in range(27)},
            "differential_id": "f" * 64,
            "status": "exact_locked_checkpoint_hc_pre_differential",
        }

    monkeypatch.setattr(cli_module, "verify_deepseek_v4_hc_pre_execution", verify)
    differential = tmp_path / "differential.json"
    assert (
        cli_module.main(
            [
                "verify-deepseek-v4-hc-pre-execution",
                "--snapshot",
                str(tmp_path / "snapshot"),
                "--lock",
                str(tmp_path / "lock.json"),
                "--application",
                str(tmp_path / "application"),
                "--deployment",
                str(deployment),
                "--request",
                str(request),
                "--result",
                str(result),
                "--output",
                str(differential),
            ]
        )
        == 0
    )
    assert verification["lock"] is lock
    assert verification["deployment_root"] == deployment
    assert verification["request_root"] == request
    assert verification["result_root"] == result
    assert verification["report_path"] == differential
    assert "verified 10 HC_PRE payloads and 27 counters" in capsys.readouterr().out


def test_hc_pre_cli_maps_service_poison_to_status_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def poison(*args: Any, **kwargs: Any) -> Any:
        raise DeepSeekV4HCPreExecutableServiceError("numeric poison")

    monkeypatch.setattr(
        cli_module,
        "execute_deepseek_v4_hc_pre_executable_deployment",
        poison,
    )
    assert (
        cli_module.main(
            [
                "execute-deepseek-v4-hc-pre",
                "--deployment",
                str(tmp_path / "deployment"),
                "--request",
                str(tmp_path / "request"),
                "--output",
                str(tmp_path / "result"),
            ]
        )
        == 2
    )
    assert "compiler error: numeric poison" in capsys.readouterr().err


def _tree_payloads(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_official_cli_composes_executes_replays_and_differential_checks(
    tmp_path: Path,
) -> None:
    raw_snapshot = os.environ.get(OFFICIAL_SNAPSHOT_ENV)
    raw_evidence = os.environ.get(OFFICIAL_EVIDENCE_ENV)
    if not raw_snapshot or not raw_evidence:
        pytest.skip(
            f"set {OFFICIAL_SNAPSHOT_ENV} and {OFFICIAL_EVIDENCE_ENV} "
            "for official CLI integration"
        )
    snapshot = Path(raw_snapshot)
    evidence = Path(raw_evidence)
    source = tmp_path / "source.txt"
    source.write_bytes(b"Hello")
    request = tmp_path / "request"
    composition = tmp_path / "composition.json"
    common = [
        "--snapshot",
        str(snapshot),
        "--lock",
        str(evidence / "checkpoint.lock.json"),
    ]
    assert (
        cli_module.main(
            [
                "compose-deepseek-v4-hc-pre-input",
                *common,
                "--lookup-deployment",
                str(evidence / "lookup-deployment"),
                "--lookup-request",
                str(evidence / "hc-pre-lookup-request.json"),
                "--lookup-result",
                str(evidence / "hc-pre-lookup-result.json"),
                "--lookup-differential",
                str(evidence / "hc-pre-lookup-differential.json"),
                "--executable-deployment",
                str(evidence / "hc-pre-executable"),
                "--executable-application",
                str(evidence / "hc-pre-canonical"),
                "--source-text-file",
                str(source),
                "--output",
                str(request),
                "--report-output",
                str(composition),
            ]
        )
        == 0
    )
    composition_report = load_strict_json(composition)
    assert composition_report["status"] == (
        "official_tokenizer_lookup_differential_composition_verified"
    )
    assert composition_report["tokenizer"]["token_ids"] == [[19923]]

    results = [tmp_path / "result-a", tmp_path / "result-b"]
    for result in results:
        assert (
            cli_module.main(
                [
                    "execute-deepseek-v4-hc-pre",
                    "--deployment",
                    str(evidence / "hc-pre-executable"),
                    "--request",
                    str(request),
                    "--output",
                    str(result),
                ]
            )
            == 0
        )
    assert _tree_payloads(results[0]) == _tree_payloads(results[1])

    differential = tmp_path / "differential.json"
    assert (
        cli_module.main(
            [
                "verify-deepseek-v4-hc-pre-execution",
                *common,
                "--application",
                str(evidence / "hc-pre-canonical"),
                "--deployment",
                str(evidence / "hc-pre-executable"),
                "--request",
                str(request),
                "--result",
                str(results[0]),
                "--output",
                str(differential),
            ]
        )
        == 0
    )
    differential_report = load_strict_json(differential)
    assert differential_report["status"] == (
        "exact_locked_checkpoint_hc_pre_differential"
    )
    assert len(differential_report["comparisons"]) == 10
    assert len(differential_report["logical_counters"]) == 27
