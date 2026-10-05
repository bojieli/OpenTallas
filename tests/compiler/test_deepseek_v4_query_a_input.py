from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

import compiler.checking.deepseek_v4_query_a_executable as executable_checker_module
import compiler.checking.deepseek_v4_query_a_input as input_checker_module
import compiler.vertical_slice.deepseek_v4_query_a_input as input_builder_module
from compiler.checking.deepseek_v4_query_a_input import (
    COMPOSITION_SCHEMA,
    HC_PRE_PROGRAM_SHA256,
    QUERY_A_PROGRAM_SHA256,
    DeepSeekV4QueryAInputCheckError,
    verify_deepseek_v4_query_a_input_composition,
)
from compiler.ir.model import canonical_json_bytes
from compiler.vertical_slice.deepseek_v4_query_a_input import (
    DeepSeekV4QueryAInputBuildError,
    build_deepseek_v4_query_a_input_request,
)


MODEL_ID = "deepseek-v4-flash-0731"
HC_BUILD_ID = "b" * 64
HC_REQUEST_SHA256 = "c" * 64
QUERY_A_BUILD_ID = "a" * 64
APPLICATION_ID = "d" * 64
VERIFICATION_ID = "e" * 64
CHECKPOINT_LOCK_ID = "f" * 64
REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"

_COUNTER_NAMES = (
    "hc_pre_branch_bf16_conversions",
    "hc_pre_branch_bf16_saturations",
    "hc_pre_branch_coefficient_multiplies",
    "hc_pre_branch_reduction_adds",
    "hc_pre_coefficient_epsilon_adds",
    "hc_pre_exp_evaluations",
    "hc_pre_field_affine_adds",
    "hc_pre_field_affine_multiplies",
    "hc_pre_input_bf16_values",
    "hc_pre_post_factor_multiplies",
    "hc_pre_projection_product_accumulates",
    "hc_pre_projection_rms_multiplies",
    "hc_pre_residual_bf16_values_preserved",
    "hc_pre_rms_divides",
    "hc_pre_rms_epsilon_adds",
    "hc_pre_rms_reduction_adds",
    "hc_pre_rms_square_multiplies",
    "hc_pre_rsqrt_evaluations",
    "hc_pre_sigmoid_evaluations",
    "hc_pre_sinkhorn_column_reduction_adds",
    "hc_pre_sinkhorn_column_stages",
    "hc_pre_sinkhorn_divides",
    "hc_pre_sinkhorn_epsilon_adds",
    "hc_pre_sinkhorn_row_reduction_adds",
    "hc_pre_sinkhorn_row_stages",
    "hc_pre_softmax_max_comparisons",
    "hc_pre_softmax_subtracts",
)

_PAYLOAD_SPECS = (
    (
        "outputs",
        "attention_input",
        "outputs/attention_input.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (4096,),
        8192,
        "ATTENTION_INPUT",
    ),
    (
        "outputs",
        "attention_pre",
        "outputs/attention_pre.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        16,
        "ATTENTION_PRE",
    ),
    (
        "outputs",
        "attention_post",
        "outputs/attention_post.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        16,
        "ATTENTION_POST",
    ),
    (
        "outputs",
        "attention_combination",
        "outputs/attention_combination.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        64,
        "ATTENTION_COMBINATION",
    ),
    (
        "outputs",
        "attention_residual",
        "outputs/attention_residual.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (4, 4096),
        32768,
        "ATTENTION_RESIDUAL",
    ),
    (
        "diagnostics",
        "rms_mean_codes",
        "diagnostics/rms_mean.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        None,
    ),
    (
        "diagnostics",
        "rms_inverse_codes",
        "diagnostics/rms_inverse.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        None,
    ),
    (
        "diagnostics",
        "projection_codes",
        "diagnostics/projection.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        96,
        None,
    ),
    (
        "diagnostics",
        "mix_codes",
        "diagnostics/mix.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        96,
        None,
    ),
    (
        "diagnostics",
        "stable_softmax_codes",
        "diagnostics/stable_softmax.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        64,
        None,
    ),
)


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert type(value) is dict
    return value


def _payload(seed: int, size: int) -> bytes:
    block = bytes(((seed * 29 + index * 17) % 251 for index in range(251)))
    return (block * ((size + len(block) - 1) // len(block)))[:size]


def _write_hc_result(root: Path, batch_size: int, sequence_length: int) -> bytes:
    root.mkdir()
    (root / "outputs").mkdir()
    (root / "diagnostics").mkdir()
    token_count = batch_size * sequence_length
    outputs: list[dict[str, Any]] = []
    diagnostics: dict[str, dict[str, Any]] = {}
    selected = b""
    for seed, spec in enumerate(_PAYLOAD_SPECS, start=1):
        section, identifier, relative, dtype, encoding, suffix, per_token, register = (
            spec
        )
        payload = _payload(seed, token_count * per_token)
        (root / relative).write_bytes(payload)
        descriptor: dict[str, Any] = {
            "dtype": dtype,
            "encoding": encoding,
            "id": identifier,
            "path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "shape": [batch_size, sequence_length, *suffix],
            "size_bytes": len(payload),
        }
        if register is not None:
            descriptor["register"] = register
        if section == "outputs":
            outputs.append(descriptor)
        else:
            diagnostics[identifier] = descriptor
        if identifier == "attention_input":
            selected = payload
    counters = {
        name: (0 if name == "hc_pre_branch_bf16_saturations" else token_count * index)
        for index, name in enumerate(_COUNTER_NAMES, start=1)
    }
    result = {
        "batch_size": batch_size,
        "build_id": HC_BUILD_ID,
        "counter_reconciliation": "exact",
        "deployment_status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
        ),
        "diagnostics": diagnostics,
        "evidence_scope": "official_checkpoint",
        "execution_scope": "exact_hc_pre_site_only",
        "logical_counters": counters,
        "model_id": MODEL_ID,
        "numeric_status": {"branch_saturation_count": 0, "poison": False},
        "outputs": outputs,
        "program_sha256": HC_PRE_PROGRAM_SHA256,
        "request_sha256": HC_REQUEST_SHA256,
        "schema": "opentallas.deepseek_v4_hc_pre_execution_result.v1",
        "sequence_length": sequence_length,
        "source_application_status": (
            "partial_official_transform_application_not_release_evidence"
        ),
        "status": "pass",
        "token_count": token_count,
    }
    _write_json(root / "result_manifest.json", result)
    return selected


def _environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    batch_size: int = 1,
    sequence_length: int = 1,
) -> dict[str, Any]:
    hc_result = tmp_path / "hc-result"
    selected = _write_hc_result(hc_result, batch_size, sequence_length)
    deployment = tmp_path / "query-a-deployment"
    application = tmp_path / "query-a-application"
    snapshot = tmp_path / "snapshot"
    deployment.mkdir()
    application.mkdir()
    snapshot.mkdir()
    deployment_manifest = {
        "build_id": QUERY_A_BUILD_ID,
        "model_id": MODEL_ID,
        "program_sha256": QUERY_A_PROGRAM_SHA256,
        "schema": "opentallas.deepseek_v4_query_a_executable.v1",
    }
    _write_json(deployment / "deployment_manifest.json", deployment_manifest)
    lock = {
        "lock_id": CHECKPOINT_LOCK_ID,
        "source": {"repository": REPOSITORY, "revision": REVISION},
    }
    verified: dict[str, Any] = {
        "application_id": APPLICATION_ID,
        "build_id": QUERY_A_BUILD_ID,
        "program_sha256": QUERY_A_PROGRAM_SHA256,
        "status": "package_identity_verified_execution_not_evidenced",
        "verification_id": VERIFICATION_ID,
    }
    calls: list[tuple[Path, Path, Path, dict[str, Any]]] = []
    state: dict[str, Any] = {"error": None, "verified": verified}

    def fake_verify(
        deployment_root: Path,
        application_root: Path,
        snapshot_root: Path,
        observed_lock: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append(
            (
                Path(deployment_root),
                Path(application_root),
                Path(snapshot_root),
                observed_lock,
            )
        )
        if state["error"] is not None:
            raise state["error"]
        return dict(state["verified"])

    monkeypatch.setattr(
        executable_checker_module,
        "verify_deepseek_v4_query_a_executable_deployment",
        fake_verify,
    )
    return {
        "application": application,
        "calls": calls,
        "deployment": deployment,
        "hc_result": hc_result,
        "lock": lock,
        "report": tmp_path / "composition.json",
        "request": tmp_path / "query-a-request",
        "selected": selected,
        "snapshot": snapshot,
        "state": state,
    }


def _build(environment: dict[str, Any], *, suffix: str = "") -> dict[str, Any]:
    request = environment["request"]
    report = environment["report"]
    if suffix:
        request = request.with_name(f"{request.name}-{suffix}")
        report = report.with_name(f"{report.stem}-{suffix}{report.suffix}")
    return build_deepseek_v4_query_a_input_request(
        hc_result_root=environment["hc_result"],
        executable_deployment_root=environment["deployment"],
        executable_application_root=environment["application"],
        snapshot=environment["snapshot"],
        lock=environment["lock"],
        output=request,
        report_output=report,
    )


def _verify(
    environment: dict[str, Any],
    *,
    request: Path | None = None,
    report: Path | None = None,
) -> dict[str, Any]:
    return verify_deepseek_v4_query_a_input_composition(
        hc_result_root=environment["hc_result"],
        executable_deployment_root=environment["deployment"],
        executable_application_root=environment["application"],
        snapshot=environment["snapshot"],
        lock=environment["lock"],
        request_root=request or environment["request"],
        report_path=report or environment["report"],
    )


@pytest.mark.parametrize(
    ("batch_size", "sequence_length"), [(1, 1), (1, 4), (2, 2), (4, 1)]
)
def test_composition_is_exact_byte_identity_and_hash_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    batch_size: int,
    sequence_length: int,
) -> None:
    environment = _environment(
        tmp_path,
        monkeypatch,
        batch_size=batch_size,
        sequence_length=sequence_length,
    )
    report = _build(environment)
    token_count = batch_size * sequence_length
    request = _read_json(environment["request"] / "request_manifest.json")
    payload = (environment["request"] / "input/attention_input.bf16le").read_bytes()
    source_manifest_payload = (
        environment["hc_result"] / "result_manifest.json"
    ).read_bytes()

    assert payload == environment["selected"]
    assert request == {
        "build_id": QUERY_A_BUILD_ID,
        "input": {
            "dtype": "BF16",
            "encoding": "bfloat16_little_endian",
            "id": "attention_input",
            "path": "input/attention_input.bf16le",
            "register": "ATTENTION_INPUT",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "shape": [token_count, 4096],
            "size_bytes": len(payload),
        },
        "model_id": MODEL_ID,
        "program_sha256": QUERY_A_PROGRAM_SHA256,
        "provenance": {
            "kind": "verified_hc_pre_execution_result",
            "source_batch_size": batch_size,
            "source_build_id": HC_BUILD_ID,
            "source_output_path": "outputs/attention_input.bf16le",
            "source_output_sha256": hashlib.sha256(payload).hexdigest(),
            "source_request_sha256": HC_REQUEST_SHA256,
            "source_result_manifest_sha256": hashlib.sha256(
                source_manifest_payload
            ).hexdigest(),
            "source_schema": "opentallas.deepseek_v4_hc_pre_execution_result.v1",
            "source_sequence_length": sequence_length,
        },
        "schema": "opentallas.deepseek_v4_query_a_execution_request.v1",
        "token_count": token_count,
    }
    assert report["schema"] == COMPOSITION_SCHEMA
    assert report["flatten"] == {
        "destination_shape": [token_count, 4096],
        "destination_sha256": hashlib.sha256(payload).hexdigest(),
        "destination_size_bytes": len(payload),
        "operation": "contiguous_token_major_byte_identity",
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_shape": [batch_size, sequence_length, 4096],
        "source_size_bytes": len(payload),
        "status": "exact_byte_identity",
    }
    assert report["verification_dependencies"] == {
        "application_id": APPLICATION_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "dependency_policy": "identity_only_no_checkpoint_payload_copied",
        "repository": REPOSITORY,
        "revision": REVISION,
        "verification_id": VERIFICATION_ID,
    }
    assert _read_json(environment["report"]) == report
    integrity = _verify(environment)
    assert integrity["composition_id"] == report["composition_id"]
    assert integrity["token_count"] == token_count
    assert len(environment["calls"]) == 3
    assert all(
        call[0] == environment["deployment"].absolute() for call in environment["calls"]
    )
    assert all(call[1] == environment["application"] for call in environment["calls"])
    assert all(call[2] == environment["snapshot"] for call in environment["calls"])
    assert all(call[3] is environment["lock"] for call in environment["calls"])


@pytest.mark.parametrize(
    "case",
    [
        "batch_bool",
        "sequence_float",
        "token_mismatch",
        "unknown_field",
        "missing_field",
        "bad_status",
        "bad_program",
        "uppercase_build",
        "input_shape",
        "input_size",
        "input_path",
        "poison_integer",
        "counter_bool",
        "output_order",
        "noncanonical",
        "duplicate_key",
        "nonfinite",
    ],
)
def test_hc_result_manifest_is_type_exact_canonical_and_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    manifest_path = environment["hc_result"] / "result_manifest.json"
    manifest = _read_json(manifest_path)
    if case == "batch_bool":
        manifest["batch_size"] = True
    elif case == "sequence_float":
        manifest["sequence_length"] = 1.0
    elif case == "token_mismatch":
        manifest["token_count"] = 2
    elif case == "unknown_field":
        manifest["unexpected"] = None
    elif case == "missing_field":
        manifest.pop("execution_scope")
    elif case == "bad_status":
        manifest["status"] = "passed"
    elif case == "bad_program":
        manifest["program_sha256"] = "0" * 64
    elif case == "uppercase_build":
        manifest["build_id"] = "B" * 64
    elif case == "input_shape":
        manifest["outputs"][0]["shape"] = [1, 4096]
    elif case == "input_size":
        manifest["outputs"][0]["size_bytes"] += 2
    elif case == "input_path":
        manifest["outputs"][0]["path"] = "../attention_input.bf16le"
    elif case == "poison_integer":
        manifest["numeric_status"]["poison"] = 0
    elif case == "counter_bool":
        manifest["logical_counters"][_COUNTER_NAMES[0]] = True
    elif case == "output_order":
        manifest["outputs"][0], manifest["outputs"][1] = (
            manifest["outputs"][1],
            manifest["outputs"][0],
        )
    elif case == "noncanonical":
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    elif case == "duplicate_key":
        payload = canonical_json_bytes(manifest)
        manifest_path.write_bytes(b'{"batch_size":1,' + payload[1:])
    elif case == "nonfinite":
        payload = canonical_json_bytes(manifest)
        manifest_path.write_bytes(
            payload.replace(b'"token_count":1', b'"token_count":NaN')
        )
    else:  # pragma: no cover - parametrization closure
        raise AssertionError(case)
    if case not in {"noncanonical", "duplicate_key", "nonfinite"}:
        _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4QueryAInputBuildError):
        _build(environment)
    assert not environment["request"].exists()
    assert not environment["report"].exists()


@pytest.mark.parametrize("relative", [spec[2] for spec in _PAYLOAD_SPECS])
def test_every_hc_result_payload_is_verified_even_when_not_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    path = environment["hc_result"] / relative
    payload = bytearray(path.read_bytes())
    payload[len(payload) // 2] ^= 0x80
    path.write_bytes(payload)
    with pytest.raises(DeepSeekV4QueryAInputBuildError, match="differs from its hash"):
        _build(environment)


@pytest.mark.parametrize(
    "case",
    ["extra_file", "missing_file", "symlink", "fifo", "directory", "root_symlink"],
)
def test_hc_result_tree_and_file_types_fail_closed_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    selected = environment["hc_result"] / "outputs/attention_input.bf16le"
    if case == "extra_file":
        (environment["hc_result"] / "diagnostics/unlisted.bin").write_bytes(b"x")
    elif case == "missing_file":
        (environment["hc_result"] / "diagnostics/mix.f32le").unlink()
    elif case == "symlink":
        selected.unlink()
        selected.symlink_to("/dev/null")
    elif case == "fifo":
        selected.unlink()
        os.mkfifo(selected)
    elif case == "directory":
        selected.unlink()
        selected.mkdir()
    elif case == "root_symlink":
        actual = environment["hc_result"].with_name("actual-hc-result")
        environment["hc_result"].rename(actual)
        environment["hc_result"].symlink_to(actual, target_is_directory=True)
    with pytest.raises(DeepSeekV4QueryAInputBuildError):
        _build(environment)


@pytest.mark.parametrize(
    "case",
    [
        "verifier_error",
        "verifier_build",
        "verifier_program",
        "verifier_application",
        "verifier_verification",
        "verifier_status",
        "manifest_build",
        "manifest_program",
        "manifest_model",
        "manifest_schema",
        "lock_id",
        "lock_repository_type",
    ],
)
def test_query_a_executable_and_verification_dependency_identity_is_mandatory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    manifest_path = environment["deployment"] / "deployment_manifest.json"
    manifest = _read_json(manifest_path)
    if case == "verifier_error":
        environment["state"]["error"] = RuntimeError("independent replay failed")
    elif case == "verifier_build":
        environment["state"]["verified"]["build_id"] = "0" * 64
    elif case == "verifier_program":
        environment["state"]["verified"]["program_sha256"] = "0" * 64
    elif case == "verifier_application":
        environment["state"]["verified"]["application_id"] = "D" * 64
    elif case == "verifier_verification":
        environment["state"]["verified"].pop("verification_id")
    elif case == "verifier_status":
        environment["state"]["verified"]["status"] = ""
    elif case == "manifest_build":
        manifest["build_id"] = "0" * 64
    elif case == "manifest_program":
        manifest["program_sha256"] = "0" * 64
    elif case == "manifest_model":
        manifest["model_id"] = "another-model"
    elif case == "manifest_schema":
        manifest["schema"] = "opentallas.deepseek_v4_query_a_executable.v2"
    elif case == "lock_id":
        environment["lock"]["lock_id"] = "F" * 64
    elif case == "lock_repository_type":
        environment["lock"]["source"]["repository"] = True
    if case.startswith("manifest_"):
        _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4QueryAInputBuildError):
        _build(environment)


def test_platform_without_bounded_descriptor_reads_fails_before_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    monkeypatch.delattr(input_checker_module.os, "pread")
    with pytest.raises(
        DeepSeekV4QueryAInputBuildError,
        match="secure descriptor operations are unavailable",
    ):
        _build(environment)


def test_unlisted_source_entry_added_after_package_replay_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    verified = dict(environment["state"]["verified"])

    def add_entry_during_replay(
        deployment_root: Path,
        application_root: Path,
        snapshot_root: Path,
        lock: dict[str, Any],
    ) -> dict[str, Any]:
        del deployment_root, application_root, snapshot_root, lock
        (environment["hc_result"] / "diagnostics/late-unlisted.bin").write_bytes(b"x")
        return verified

    monkeypatch.setattr(
        executable_checker_module,
        "verify_deepseek_v4_query_a_executable_deployment",
        add_entry_during_replay,
    )
    with pytest.raises(
        DeepSeekV4QueryAInputBuildError,
        match="tree changed after causal verification",
    ):
        _build(environment)


@pytest.mark.parametrize(
    "case",
    [
        "input_bytes",
        "manifest_value",
        "manifest_noncanonical",
        "report_value",
        "report_duplicate",
        "extra_file",
        "missing_input",
    ],
)
def test_published_request_report_and_closed_tree_tampering_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    _build(environment)
    input_path = environment["request"] / "input/attention_input.bf16le"
    manifest_path = environment["request"] / "request_manifest.json"
    if case == "input_bytes":
        payload = bytearray(input_path.read_bytes())
        payload[0] ^= 1
        input_path.write_bytes(payload)
    elif case == "manifest_value":
        manifest = _read_json(manifest_path)
        manifest["token_count"] = 2
        _write_json(manifest_path, manifest)
    elif case == "manifest_noncanonical":
        manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    elif case == "report_value":
        report = _read_json(environment["report"])
        report["status"] = "pass"
        _write_json(environment["report"], report)
    elif case == "report_duplicate":
        payload = environment["report"].read_bytes()
        environment["report"].write_bytes(b'{"schema":"duplicate",' + payload[1:])
    elif case == "extra_file":
        (environment["request"] / "input/unlisted.bin").write_bytes(b"x")
    elif case == "missing_input":
        input_path.unlink()
    with pytest.raises(DeepSeekV4QueryAInputCheckError):
        _verify(environment)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory"])
def test_published_request_special_input_files_are_rejected_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    _build(environment)
    input_path = environment["request"] / "input/attention_input.bf16le"
    input_path.unlink()
    if kind == "symlink":
        input_path.symlink_to("/dev/null")
    elif kind == "fifo":
        os.mkfifo(input_path)
    else:
        input_path.mkdir()
    with pytest.raises(DeepSeekV4QueryAInputCheckError):
        _verify(environment)


@pytest.mark.parametrize(
    "target", ["source_payload", "deployment_manifest", "request_input"]
)
def test_retained_inode_replacement_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    if target == "deployment_manifest":
        original_verify = environment["state"]
        replaced = False

        def replace_during_verification(
            deployment_root: Path,
            application_root: Path,
            snapshot_root: Path,
            lock: dict[str, Any],
        ) -> dict[str, Any]:
            nonlocal replaced
            del application_root, snapshot_root, lock
            if not replaced:
                path = Path(deployment_root) / "deployment_manifest.json"
                payload = path.read_bytes()
                path.unlink()
                path.write_bytes(payload)
                replaced = True
            return dict(original_verify["verified"])

        monkeypatch.setattr(
            executable_checker_module,
            "verify_deepseek_v4_query_a_executable_deployment",
            replace_during_verification,
        )
        with pytest.raises(DeepSeekV4QueryAInputBuildError, match="changed|replaced"):
            _build(environment)
        return

    if target == "request_input":
        _build(environment)
    original_read = input_checker_module._read_file
    replaced = False

    def replacing_read(
        source: input_checker_module._StableFile, label: str, maximum: int
    ) -> bytes:
        nonlocal replaced
        payload = original_read(source, label, maximum)
        wanted = (
            "HC_PRE result payload 'attention_input'"
            if target == "source_payload"
            else "Query-A request input"
        )
        if not replaced and label == wanted:
            root = (
                environment["hc_result"]
                if target == "source_payload"
                else environment["request"]
            )
            path = root / source.relative_path
            path.unlink()
            path.write_bytes(payload)
            replaced = True
        return payload

    monkeypatch.setattr(input_checker_module, "_read_file", replacing_read)
    error: type[Exception] = (
        DeepSeekV4QueryAInputBuildError
        if target == "source_payload"
        else DeepSeekV4QueryAInputCheckError
    )
    with pytest.raises(error, match="changed|replaced"):
        _build(environment) if target == "source_payload" else _verify(environment)


def test_create_once_destinations_are_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    environment["request"].write_bytes(b"foreign-request")
    with pytest.raises(DeepSeekV4QueryAInputBuildError, match="already exists"):
        _build(environment)
    assert environment["request"].read_bytes() == b"foreign-request"
    assert not environment["report"].exists()

    environment["request"].unlink()
    environment["report"].write_bytes(b"foreign-report")
    with pytest.raises(DeepSeekV4QueryAInputBuildError, match="already exists"):
        _build(environment)
    assert environment["report"].read_bytes() == b"foreign-report"
    assert not environment["request"].exists()


def test_report_publication_is_rolled_back_if_request_publication_loses_a_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    original_publish = input_builder_module._publish_create_once
    calls = 0

    def racing_publish(**kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            Path(kwargs["destination"]).mkdir()
        original_publish(**kwargs)

    monkeypatch.setattr(input_builder_module, "_publish_create_once", racing_publish)
    with pytest.raises(DeepSeekV4QueryAInputBuildError, match="already exists"):
        _build(environment)
    assert environment["request"].is_dir()
    assert list(environment["request"].iterdir()) == []
    assert not environment["report"].exists()
    assert not list(tmp_path.glob(".query-a-input.tmp-*"))
    assert not list(tmp_path.glob(".query-a-input-report.tmp-*"))


def test_rollback_refuses_to_remove_a_replaced_foreign_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch)
    original_publish = input_builder_module._publish_create_once
    calls = 0

    def adversarial_publish(**kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            original_publish(**kwargs)
            return
        environment["report"].unlink()
        environment["report"].write_bytes(b"foreign-report")
        raise DeepSeekV4QueryAInputBuildError("request publication lost")

    monkeypatch.setattr(
        input_builder_module, "_publish_create_once", adversarial_publish
    )
    with pytest.raises(
        DeepSeekV4QueryAInputBuildError,
        match="refusing to remove a replaced Query-A composition report",
    ):
        _build(environment)
    assert environment["report"].read_bytes() == b"foreign-report"
    assert not environment["request"].exists()


def test_two_compositions_are_byte_deterministic_and_copy_no_checkpoint_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = _environment(tmp_path, monkeypatch, batch_size=2, sequence_length=2)
    first = _build(environment, suffix="one")
    second = _build(environment, suffix="two")
    first_root = environment["request"].with_name("query-a-request-one")
    second_root = environment["request"].with_name("query-a-request-two")
    first_report = environment["report"].with_name("composition-one.json")
    second_report = environment["report"].with_name("composition-two.json")
    assert first == second
    assert first_report.read_bytes() == second_report.read_bytes()
    assert (first_root / "request_manifest.json").read_bytes() == (
        second_root / "request_manifest.json"
    ).read_bytes()
    assert (first_root / "input/attention_input.bf16le").read_bytes() == (
        second_root / "input/attention_input.bf16le"
    ).read_bytes()
    assert {
        path.relative_to(first_root).as_posix() for path in first_root.rglob("*")
    } == {
        "input",
        "input/attention_input.bf16le",
        "request_manifest.json",
    }
    serialized = canonical_json_bytes(first)
    assert str(environment["snapshot"]).encode() not in serialized
    assert b'"checkpoint_payload":' not in serialized
    assert b"expected_output" not in serialized
    assert b"source_text" not in serialized
    assert b"cycle_count" not in serialized
    assert b"latency_ns" not in serialized
    assert b"area_mm2" not in serialized
    assert b"nvidia_speedup" not in serialized


def _cached_query_a_inputs() -> tuple[Path, Path, Path, Path] | None:
    cache = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"
    deployments = [
        candidate.parent
        for candidate in sorted(cache.glob("query-a*/deployment_manifest.json"))
        if candidate.is_file()
    ]
    if not deployments:
        return None
    deployment = deployments[-1]
    manifest = _read_json(deployment / "deployment_manifest.json")
    source = manifest.get("source")
    if type(source) is not dict or type(source.get("application_id")) is not str:
        return None
    application = None
    for candidate in sorted(cache.glob("query-a-canonical*")):
        path = candidate / "canonical_application.json"
        if (
            path.is_file()
            and _read_json(path).get("application_id") == source["application_id"]
        ):
            application = candidate
            break
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / REVISION
    )
    lock = cache / "checkpoint.lock.json"
    hc_result = cache / "hc-pre-result-composed-v1"
    if (
        application is None
        or not snapshot.is_dir()
        or not lock.is_file()
        or not hc_result.is_dir()
    ):
        return None
    return hc_result, deployment, application, snapshot


def test_real_cached_hc_result_and_query_a_package_compose_when_available(
    tmp_path: Path,
) -> None:
    inputs = _cached_query_a_inputs()
    if inputs is None:
        pytest.skip(
            "complete cached official Query-A executable evidence is unavailable"
        )
    hc_result, deployment, application, snapshot = inputs
    lock = _read_json(
        Path.home() / ".cache/opentallas/deepseek-v4-flash-0731/checkpoint.lock.json"
    )
    output = tmp_path / "official-query-a-request"
    report_path = tmp_path / "official-query-a-composition.json"
    report = build_deepseek_v4_query_a_input_request(
        hc_result_root=hc_result,
        executable_deployment_root=deployment,
        executable_application_root=application,
        snapshot=snapshot,
        lock=lock,
        output=output,
        report_output=report_path,
    )
    assert report["source_result"]["status"] == "pass"
    assert report["verification_dependencies"]["checkpoint_lock_id"] == lock["lock_id"]
    assert (
        verify_deepseek_v4_query_a_input_composition(
            hc_result_root=hc_result,
            executable_deployment_root=deployment,
            executable_application_root=application,
            snapshot=snapshot,
            lock=lock,
            request_root=output,
            report_path=report_path,
        )["composition_id"]
        == report["composition_id"]
    )
