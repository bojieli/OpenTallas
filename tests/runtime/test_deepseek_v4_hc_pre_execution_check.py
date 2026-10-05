from __future__ import annotations

from contextlib import ExitStack
import copy
from dataclasses import dataclass
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import struct
from typing import Any

import pytest

from compiler.frontend.checkpoint import (
    load_checkpoint_lock,
    read_tensor_payload,
)
from compiler.ir.model import canonical_json_bytes
from runtime.reference import deepseek_v4_hc_pre_execution_check as checker_module
from runtime.reference.deepseek_v4_hc_pre_execution_check import (
    APPLICATION_ID,
    DIFFERENTIAL_SCHEMA,
    PROGRAM_SHA256,
    DeepSeekV4HCPreExecutionCheckError,
    verify_deepseek_v4_hc_pre_execution,
)
from runtime.service_engine.hc_pre_numeric import execute_hc_pre


REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
EVIDENCE_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_EVIDENCE_ROOT"
SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_SNAPSHOT"
BASE_NAME = "layers.0.hc_attn_base"
PROJECTION_NAME = "layers.0.hc_attn_fn"
SCALE_NAME = "layers.0.hc_attn_scale"


@dataclass(frozen=True)
class _OfficialExecution:
    snapshot: Path
    lock: dict[str, Any]
    application_root: Path
    deployment_root: Path
    request_root: Path
    result_root: Path
    service_counters: dict[str, int]


def _canonical_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _flatten(value: object) -> tuple[int, ...]:
    result: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            result.append(item)
            return
        assert isinstance(item, (tuple, list))
        for child in item:
            visit(child)

    visit(value)
    return tuple(result)


def _pack(value: object, bits: int) -> bytes:
    codes = _flatten(value)
    encoder = struct.Struct("<H" if bits == 16 else "<I")
    return b"".join(encoder.pack(code) for code in codes)


def _f32_tensor(snapshot: Path, lock: dict[str, Any], name: str) -> tuple[int, ...]:
    payload = read_tensor_payload(snapshot, lock, name)
    return tuple(code for (code,) in struct.iter_unpack("<I", payload))


def _request_input(request_root: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    request_payload = (request_root / "request_manifest.json").read_bytes()
    request = json.loads(request_payload)
    payload = (request_root / request["input"]["path"]).read_bytes()
    flat = tuple(code for (code,) in struct.iter_unpack("<H", payload))
    offset = 0
    batches: list[tuple[Any, ...]] = []
    for _ in range(request["batch_size"]):
        sequence: list[tuple[Any, ...]] = []
        for _ in range(request["sequence_length"]):
            streams = []
            for _ in range(4):
                streams.append(tuple(flat[offset : offset + 4096]))
                offset += 4096
            sequence.append(tuple(streams))
        batches.append(tuple(sequence))
    assert offset == len(flat)
    return request, tuple(batches)


def _descriptor(
    *,
    identifier: str,
    path: str,
    dtype: str,
    shape: list[int],
    payload: bytes,
    register: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "dtype": dtype,
        "encoding": (
            "bfloat16_little_endian"
            if dtype == "BF16"
            else "ieee754_binary32_little_endian"
        ),
        "id": identifier,
        "path": path,
        "sha256": _sha(payload),
        "shape": shape,
        "size_bytes": len(payload),
    }
    if register is not None:
        value["register"] = register
    return value


def _materialize_service_result(
    *,
    root: Path,
    request_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> dict[str, int]:
    request, inputs = _request_input(request_root)
    base = _f32_tensor(snapshot, lock, BASE_NAME)
    projection_flat = _f32_tensor(snapshot, lock, PROJECTION_NAME)
    projection = tuple(
        projection_flat[row * 16_384 : (row + 1) * 16_384] for row in range(24)
    )
    scale = _f32_tensor(snapshot, lock, SCALE_NAME)
    service = execute_hc_pre(inputs, projection, scale, base)
    batch = request["batch_size"]
    sequence = request["sequence_length"]

    payload_values = {
        "attention_input": (
            "outputs/attention_input.bf16le",
            "BF16",
            [batch, sequence, 4096],
            service.branch_codes,
            16,
            "ATTENTION_INPUT",
        ),
        "attention_pre": (
            "outputs/attention_pre.f32le",
            "F32",
            [batch, sequence, 4],
            service.pre_codes,
            32,
            "ATTENTION_PRE",
        ),
        "attention_post": (
            "outputs/attention_post.f32le",
            "F32",
            [batch, sequence, 4],
            service.post_codes,
            32,
            "ATTENTION_POST",
        ),
        "attention_combination": (
            "outputs/attention_combination.f32le",
            "F32",
            [batch, sequence, 4, 4],
            service.combination_codes,
            32,
            "ATTENTION_COMBINATION",
        ),
        "attention_residual": (
            "outputs/attention_residual.bf16le",
            "BF16",
            [batch, sequence, 4, 4096],
            service.residual_codes,
            16,
            "ATTENTION_RESIDUAL",
        ),
        "rms_mean_codes": (
            "diagnostics/rms_mean.f32le",
            "F32",
            [batch, sequence],
            service.rms_mean_codes,
            32,
            None,
        ),
        "rms_inverse_codes": (
            "diagnostics/rms_inverse.f32le",
            "F32",
            [batch, sequence],
            service.rms_inverse_codes,
            32,
            None,
        ),
        "projection_codes": (
            "diagnostics/projection.f32le",
            "F32",
            [batch, sequence, 24],
            service.projection_codes,
            32,
            None,
        ),
        "mix_codes": (
            "diagnostics/mix.f32le",
            "F32",
            [batch, sequence, 24],
            service.mix_codes,
            32,
            None,
        ),
        "stable_softmax_codes": (
            "diagnostics/stable_softmax.f32le",
            "F32",
            [batch, sequence, 4, 4],
            service.stable_softmax_codes,
            32,
            None,
        ),
    }
    descriptors: dict[str, dict[str, Any]] = {}
    for identifier, (
        relative,
        dtype,
        shape,
        values,
        bits,
        register,
    ) in payload_values.items():
        payload = _pack(values, bits)
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        descriptors[identifier] = _descriptor(
            identifier=identifier,
            path=relative,
            dtype=dtype,
            shape=shape,
            payload=payload,
            register=register,
        )
    manifest = {
        "batch_size": batch,
        "build_id": request["build_id"],
        "counter_reconciliation": "exact",
        "deployment_status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
        ),
        "diagnostics": {
            identifier: descriptors[identifier]
            for identifier in (
                "mix_codes",
                "projection_codes",
                "rms_inverse_codes",
                "rms_mean_codes",
                "stable_softmax_codes",
            )
        },
        "evidence_scope": "official_checkpoint",
        "execution_scope": "exact_hc_pre_site_only",
        "logical_counters": dict(service.logical_counters),
        "model_id": "deepseek-v4-flash-0731",
        "numeric_status": {
            "branch_saturation_count": service.branch_saturation_count,
            "poison": False,
        },
        "outputs": [
            descriptors[identifier]
            for identifier in (
                "attention_input",
                "attention_pre",
                "attention_post",
                "attention_combination",
                "attention_residual",
            )
        ],
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": _sha((request_root / "request_manifest.json").read_bytes()),
        "schema": "opentallas.deepseek_v4_hc_pre_execution_result.v1",
        "sequence_length": sequence,
        "source_application_status": (
            "partial_official_transform_application_not_release_evidence"
        ),
        "status": "pass",
        "token_count": request["token_count"],
    }
    _canonical_write(root / "result_manifest.json", manifest)
    return dict(service.logical_counters)


def _official_paths() -> tuple[Path, Path, Path, Path, Path]:
    default_evidence = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"
    default_snapshot = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / REVISION
    )
    evidence = Path(os.environ.get(EVIDENCE_ENV, default_evidence))
    snapshot = Path(os.environ.get(SNAPSHOT_ENV, default_snapshot))
    paths = (
        snapshot,
        evidence / "checkpoint.lock.json",
        evidence / "hc-pre-canonical",
        evidence / "hc-pre-executable",
        evidence / "hc-pre-request",
    )
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        pytest.skip(
            f"set {EVIDENCE_ENV} and {SNAPSHOT_ENV} for the official HC_PRE "
            f"execution differential; missing {missing}"
        )
    return paths


@pytest.fixture(scope="module")
def official_execution(tmp_path_factory: pytest.TempPathFactory) -> _OfficialExecution:
    snapshot, lock_path, application, deployment, request = _official_paths()
    lock = load_checkpoint_lock(lock_path)
    result = tmp_path_factory.mktemp("hc-pre-check") / "result"
    counters = _materialize_service_result(
        root=result,
        request_root=request,
        snapshot=snapshot,
        lock=lock,
    )
    return _OfficialExecution(
        snapshot,
        lock,
        application,
        deployment,
        request,
        result,
        counters,
    )


def _verify(
    execution: _OfficialExecution,
    *,
    application_root: Path | None = None,
    request_root: Path | None = None,
    result_root: Path | None = None,
    report_path: Path | None = None,
    lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return verify_deepseek_v4_hc_pre_execution(
        snapshot=execution.snapshot,
        lock=execution.lock if lock is None else lock,
        application_root=(
            execution.application_root if application_root is None else application_root
        ),
        deployment_root=execution.deployment_root,
        request_root=execution.request_root if request_root is None else request_root,
        result_root=execution.result_root if result_root is None else result_root,
        report_path=report_path,
    )


def _copy_tree(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _flip_one_bit(path: Path, offset: int = 0) -> None:
    with path.open("r+b") as handle:
        handle.seek(offset)
        original = handle.read(1)
        assert len(original) == 1
        handle.seek(offset)
        handle.write(bytes((original[0] ^ 1,)))


def test_checker_has_no_service_engine_or_compiler_arithmetic_dependency() -> None:
    source = inspect.getsource(checker_module)
    assert "runtime.service_engine" not in source
    assert "hc_pre_numeric" not in source
    assert "from runtime.reference.hyper_connection import" in source
    assert source.count("hc_pre_bf16(") == 1


def test_frozen_result_interface_has_exact_axes_payloads_and_counters() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas/compiler/deepseek_v4_hc_pre_executable/execution_result_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    counters = schema["$defs"]["logicalCounters"]
    assert set(counters["required"]) == checker_module._COUNTERS
    assert len(counters["required"]) == 27
    assert "hc_pre_token_count" not in counters["required"]
    assert len(checker_module._PAYLOAD_SPECS) == 10
    assert all(
        definition["properties"]["shape"]["prefixItems"][0]["type"] == "integer"
        for name, definition in schema["$defs"].items()
        if name
        in {
            "attentionCombination",
            "attentionInput",
            "attentionPost",
            "attentionPre",
            "attentionResidual",
            "mixCodes",
            "projectionCodes",
            "rmsInverseCodes",
            "rmsMeanCodes",
            "stableSoftmaxCodes",
        }
    )


def test_strict_json_rejects_duplicate_noncanonical_and_nonfinite_values() -> None:
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="duplicate"):
        checker_module._strict_json(b'{"a":1,"a":2}\n', "test JSON")
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="canonical"):
        checker_module._strict_json(b'{"b":2, "a":1}\n', "test JSON")
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="non-finite"):
        checker_module._strict_json(b'{"a":NaN}\n', "test JSON")


def test_descriptor_guards_reject_symlink_fifo_and_replacement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    regular = root / "regular.bin"
    regular.write_bytes(b"abcd")
    (root / "link.bin").symlink_to(regular)
    os.mkfifo(root / "fifo.bin")
    with ExitStack() as stack:
        guarded_root = checker_module._open_root(stack, root, "test root")
        with pytest.raises(
            DeepSeekV4HCPreExecutionCheckError, match="symlink|following"
        ):
            checker_module._safe_file(stack, guarded_root, "link.bin", "link")
        with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="regular file"):
            checker_module._safe_file(stack, guarded_root, "fifo.bin", "fifo")
        source = checker_module._safe_file(
            stack, guarded_root, "regular.bin", "regular", exact_size=4
        )
        replacement = root / "replacement.bin"
        replacement.write_bytes(b"abcd")
        replacement.replace(regular)
        with pytest.raises(
            DeepSeekV4HCPreExecutionCheckError, match="changed|replaced"
        ):
            checker_module._verify_file(source, "regular")


def test_atomic_report_publication_allows_its_own_parent_metadata_change(
    tmp_path: Path,
) -> None:
    output = tmp_path / "report.json"
    payload = canonical_json_bytes({"status": "exact"})

    checker_module._publish_report(output, payload)

    assert output.read_bytes() == payload
    assert not list(tmp_path.glob(".hc-pre-differential.tmp-*"))


def test_atomic_report_publication_rejects_parent_replacement_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    moved = tmp_path / "moved-parent"
    real_link = checker_module.os.link

    def replace_parent_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        parent.rename(moved)
        parent.mkdir()
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(checker_module.os, "link", replace_parent_then_link)
    # Replacing ``os.link`` changes its object identity, so the platform
    # capability probe can no longer find it in ``os.supports_dir_fd``.
    monkeypatch.setattr(checker_module, "_require_secure_operations", lambda: None)
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="replaced"):
        checker_module._publish_report(
            parent / "report.json", canonical_json_bytes({"status": "exact"})
        )

    assert not (parent / "report.json").exists()
    assert not (moved / "report.json").exists()


def test_atomic_report_publication_preserves_replacement_after_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "report.json"
    sentinel = b"competing report\n"
    real_link = checker_module.os.link

    def replace_destination_after_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        os.unlink(destination, dir_fd=dst_dir_fd)
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
            dir_fd=dst_dir_fd,
        )
        try:
            assert os.write(descriptor, sentinel) == len(sentinel)
        finally:
            os.close(descriptor)

    monkeypatch.setattr(checker_module.os, "link", replace_destination_after_link)
    monkeypatch.setattr(checker_module, "_require_secure_operations", lambda: None)
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="replaced"):
        checker_module._publish_report(
            output,
            canonical_json_bytes({"status": "exact"}),
        )

    assert output.read_bytes() == sentinel
    assert not list(tmp_path.glob(".hc-pre-differential.tmp-*"))


def test_official_execution_matches_all_outputs_diagnostics_and_counters(
    official_execution: _OfficialExecution,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "hc-pre-differential.json"
    report = _verify(official_execution, report_path=report_path)

    assert report["schema"] == DIFFERENTIAL_SCHEMA
    assert report["status"] == "exact_locked_checkpoint_hc_pre_differential"
    assert report["application_id"] == APPLICATION_ID
    assert report["program_sha256"] == PROGRAM_SHA256
    assert report["token_count"] == (report["batch_size"] * report["sequence_length"])
    assert report["logical_counters"] == official_execution.service_counters
    assert len(report["logical_counters"]) == 27
    assert len(report["comparisons"]) == 10
    assert {item["payload"] for item in report["comparisons"]} == {
        "attention_input",
        "attention_pre",
        "attention_post",
        "attention_combination",
        "attention_residual",
        "rms_mean_codes",
        "rms_inverse_codes",
        "projection_codes",
        "mix_codes",
        "stable_softmax_codes",
    }
    assert all(item["status"] == "exact" for item in report["comparisons"])
    assert all(
        item["expected_sha256"] == item["observed_sha256"]
        for item in report["comparisons"]
    )
    assert all("values" not in item for item in report["comparisons"])
    body = dict(report)
    differential_id = body.pop("differential_id")
    assert differential_id == _sha(canonical_json_bytes(body))
    assert report_path.read_bytes() == canonical_json_bytes(report)
    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="already exists"):
        checker_module._publish_report(report_path, canonical_json_bytes(report))


@pytest.mark.parametrize(
    ("tensor_name", "relative"),
    [
        (BASE_NAME, f"ranks/rank-000/{BASE_NAME}.bin"),
        (PROJECTION_NAME, f"ranks/rank-000/{PROJECTION_NAME}.bin"),
        (SCALE_NAME, f"ranks/rank-000/{SCALE_NAME}.bin"),
    ],
)
def test_one_bit_source_application_mutation_is_detected_for_each_learned_class(
    official_execution: _OfficialExecution,
    tmp_path: Path,
    tensor_name: str,
    relative: str,
) -> None:
    application = _copy_tree(
        official_execution.application_root, tmp_path / tensor_name.replace(".", "-")
    )
    _flip_one_bit(application / relative)

    with pytest.raises(
        DeepSeekV4HCPreExecutionCheckError, match="verification|differs"
    ):
        _verify(official_execution, application_root=application)


def test_one_bit_request_mutation_with_rehashed_manifests_reaches_differential(
    official_execution: _OfficialExecution,
    tmp_path: Path,
) -> None:
    request_root = _copy_tree(official_execution.request_root, tmp_path / "request")
    result_root = _copy_tree(official_execution.result_root, tmp_path / "result")
    input_path = request_root / "input/hc_hidden.bf16le"
    _flip_one_bit(input_path)
    request = json.loads((request_root / "request_manifest.json").read_bytes())
    request["input"]["sha256"] = _sha(input_path.read_bytes())
    _canonical_write(request_root / "request_manifest.json", request)
    result = json.loads((result_root / "result_manifest.json").read_bytes())
    result["request_sha256"] = _sha(
        (request_root / "request_manifest.json").read_bytes()
    )
    _canonical_write(result_root / "result_manifest.json", result)

    with pytest.raises(
        DeepSeekV4HCPreExecutionCheckError,
        match="differs from locked-checkpoint semantics",
    ):
        _verify(
            official_execution,
            request_root=request_root,
            result_root=result_root,
        )


def test_result_payload_one_bit_mutation_fails_before_report_publication(
    official_execution: _OfficialExecution,
    tmp_path: Path,
) -> None:
    result_root = _copy_tree(official_execution.result_root, tmp_path / "result")
    _flip_one_bit(result_root / "outputs/attention_post.f32le")
    report_path = tmp_path / "must-not-exist.json"

    with pytest.raises(
        DeepSeekV4HCPreExecutionCheckError, match="differs from its hash"
    ):
        _verify(
            official_execution,
            result_root=result_root,
            report_path=report_path,
        )
    assert not report_path.exists()
    assert not list(tmp_path.glob(".hc-pre-differential.tmp-*"))


def test_result_counter_bool_integer_alias_is_rejected(
    official_execution: _OfficialExecution,
    tmp_path: Path,
) -> None:
    result_root = _copy_tree(official_execution.result_root, tmp_path / "result")
    manifest_path = result_root / "result_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["logical_counters"]["hc_pre_rms_divides"] = True
    _canonical_write(manifest_path, manifest)

    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="integer bound"):
        _verify(official_execution, result_root=result_root)


@pytest.mark.parametrize(
    "attack", ["symlink", "fifo", "extra", "noncanonical", "oversize"]
)
def test_result_tree_security_attacks_fail_closed(
    official_execution: _OfficialExecution,
    tmp_path: Path,
    attack: str,
) -> None:
    result_root = _copy_tree(official_execution.result_root, tmp_path / "result")
    payload = result_root / "outputs/attention_pre.f32le"
    manifest = result_root / "result_manifest.json"
    if attack == "symlink":
        payload.unlink()
        payload.symlink_to("/dev/null")
    elif attack == "fifo":
        payload.unlink()
        os.mkfifo(payload)
    elif attack == "extra":
        (result_root / "diagnostics/unlisted.bin").write_bytes(b"x")
    elif attack == "noncanonical":
        manifest.write_bytes(manifest.read_bytes() + b" ")
    else:
        manifest.write_bytes(b" " * (1024 * 1024 + 1))

    with pytest.raises(DeepSeekV4HCPreExecutionCheckError):
        _verify(official_execution, result_root=result_root)


def test_result_manifest_program_mutation_fails_identity_check(
    official_execution: _OfficialExecution,
    tmp_path: Path,
) -> None:
    result_root = _copy_tree(official_execution.result_root, tmp_path / "result")
    manifest_path = result_root / "result_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["program_sha256"] = "0" * 64
    _canonical_write(manifest_path, manifest)

    with pytest.raises(DeepSeekV4HCPreExecutionCheckError, match="identity differs"):
        _verify(official_execution, result_root=result_root)


@pytest.mark.parametrize("tensor_name", [BASE_NAME, PROJECTION_NAME, SCALE_NAME])
def test_official_lock_one_bit_identity_mutations_fail_for_all_tensor_classes(
    official_execution: _OfficialExecution,
    tensor_name: str,
) -> None:
    lock = copy.deepcopy(official_execution.lock)
    record = next(
        tensor
        for shard in lock["shards"]
        for tensor in shard["tensors"]
        if tensor["name"] == tensor_name
    )
    original = record["payload_sha256"]
    record["payload_sha256"] = ("1" if original[0] == "0" else "0") + original[1:]

    with pytest.raises(DeepSeekV4HCPreExecutionCheckError):
        _verify(official_execution, lock=lock)
