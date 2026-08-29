from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import struct
from typing import Any

import pytest

from runtime.service_engine import deepseek_v4_query_a_executable as service
from runtime.service_engine.deepseek_v4_query_a_executable import (
    EXECUTABLE_BUILD_ID,
    EXECUTION_REQUEST_SCHEMA,
    EXECUTION_RESULT_SCHEMA,
    HC_PRE_EXECUTABLE_BUILD_ID,
    PROGRAM_SHA256,
    DeepSeekV4QueryAExecutableServiceEngine,
    DeepSeekV4QueryAExecutableServiceError,
    load_deepseek_v4_query_a_executable_deployment,
)
from runtime.service_engine.query_a_numeric import (
    HIDDEN_SIZE,
    QueryAServiceNumericResult,
    query_a_functional_counters,
)
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureFile,
    canonical_json_bytes,
    parse_canonical_json,
)


_CACHE_ROOT = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"


def _json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    value = parse_canonical_json(
        payload,
        label=str(path),
        maximum_bytes=max(1, len(payload)),
    )
    assert type(value) is dict
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _discover_official_package() -> Path | None:
    candidates: list[Path] = []
    configured = os.environ.get("OPENTALLAS_QUERY_A_EXECUTABLE_PACKAGE")
    if configured:
        candidates.append(Path(configured))
    if _CACHE_ROOT.is_dir():
        candidates.extend(sorted(_CACHE_ROOT.glob("query-a-executable-*")))
    for candidate in candidates:
        manifest = candidate / "deployment_manifest.json"
        if not manifest.is_file():
            continue
        try:
            value = json.loads(manifest.read_bytes())
        except (OSError, UnicodeError, ValueError):
            continue
        if (
            type(value) is dict
            and value.get("schema") == "opentallas.deepseek_v4_query_a_executable.v1"
            and value.get("build_id") == EXECUTABLE_BUILD_ID
        ):
            return candidate
    return None


def _discover_composed_request() -> Path | None:
    candidates: list[Path] = []
    configured = os.environ.get("OPENTALLAS_QUERY_A_REQUEST_MANIFEST")
    if configured:
        candidates.append(Path(configured))
    if _CACHE_ROOT.is_dir():
        candidates.extend(sorted(_CACHE_ROOT.rglob("request_manifest.json")))
    for candidate in candidates:
        try:
            value = json.loads(candidate.read_bytes())
        except (OSError, UnicodeError, ValueError):
            continue
        if (
            type(value) is dict
            and value.get("schema") == EXECUTION_REQUEST_SCHEMA
            and value.get("build_id") == EXECUTABLE_BUILD_ID
            and (candidate.parent / "input/attention_input.bf16le").is_file()
        ):
            return candidate
    return None


@pytest.fixture(scope="module")
def official_package() -> Path:
    package = _discover_official_package()
    if package is None:
        pytest.skip("frozen official Query-A executable package is not cached")
    return package


def _snapshot(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            payload = path.read_bytes()
            result[path.relative_to(root).as_posix()] = (
                stat.S_IMODE(path.stat().st_mode),
                hashlib.sha256(payload).hexdigest(),
            )
    return result


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(child) for child in value]
    return value


def _copy_request(source_manifest: Path, destination: Path) -> Path:
    shutil.copytree(source_manifest.parent, destination)
    return destination / "request_manifest.json"


@pytest.fixture(scope="module")
def official_request() -> Path:
    request = _discover_composed_request()
    if request is None:
        pytest.skip("verified HC_PRE-derived Query-A request is not cached")
    return request


@pytest.fixture(scope="module")
def completed_execution(
    official_package: Path,
    official_request: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    workspace = tmp_path_factory.mktemp("query-a-execution")
    request_manifest = _copy_request(official_request, workspace / "request")

    package_before = _snapshot(official_package)
    request_before = _snapshot(request_manifest.parent)
    first_dir = workspace / "first-result"
    second_dir = workspace / "second-result"
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        first = engine.execute(request_manifest, first_dir)
        second = engine.execute(request_manifest, second_dir)
    return {
        "first": first,
        "first_dir": first_dir,
        "package_before": package_before,
        "package_after": _snapshot(official_package),
        "request_before": request_before,
        "request_after": _snapshot(request_manifest.parent),
        "request_manifest": request_manifest,
        "second": second,
        "second_dir": second_dir,
    }


def test_official_package_decodes_the_exact_program_without_build_time_imports(
    official_package: Path,
) -> None:
    with load_deepseek_v4_query_a_executable_deployment(official_package) as package:
        assert package.build_id == EXECUTABLE_BUILD_ID
        assert package.program_sha256 == PROGRAM_SHA256
        assert [instruction.opcode_name for instruction in package.instructions] == [
            "RMS_NORM",
            "FP8_LINEAR",
            "COMPLETE",
        ]
        assert package.instructions[0].source == 3
        assert package.instructions[0].destinations[0] == 8
        assert package.instructions[1].source == 8
        assert package.instructions[1].destinations[0] == 9
        assert package.instructions[1].resources[:3] == (8, 9, 10)
        assert package.exhaustive_rows == tuple(range(1024))
        assert package.weight_row(0) == package.weight_payload[:HIDDEN_SIZE]
        assert package.scale_code(128, 7) == package.scale_codes[39]


@pytest.mark.parametrize(
    "case",
    [
        "metadata",
        "artifacts",
        "instructions",
        "norm_weight",
        "linear_weight",
        "scale",
        "rows",
        "root",
    ],
)
def test_held_deployment_rejects_in_memory_snapshot_substitution(
    official_package: Path,
    case: str,
) -> None:
    package = load_deepseek_v4_query_a_executable_deployment(official_package)
    try:
        if case == "metadata":
            package.build_id = "0" * 64
        elif case == "artifacts":
            package.artifacts = package.artifacts[:-1]
        elif case == "instructions":
            first = package.instructions[0]
            package.instructions = (
                replace(first, immediates=(HIDDEN_SIZE - 1, *first.immediates[1:])),
                *package.instructions[1:],
            )
        elif case == "norm_weight":
            package.norm_weight_codes = (
                package.norm_weight_codes[0] ^ 1,
                *package.norm_weight_codes[1:],
            )
        elif case == "linear_weight":
            package.weight_payload = (
                bytes([package.weight_payload[0] ^ 1]) + (package.weight_payload[1:])
            )
        elif case == "scale":
            package.scale_codes = (
                package.scale_codes[0] ^ 1,
                *package.scale_codes[1:],
            )
        elif case == "rows":
            package.exhaustive_rows = (
                package.exhaustive_rows[1],
                package.exhaustive_rows[0],
                *package.exhaustive_rows[2:],
            )
        elif case == "root":
            package.root = package.root / "replacement"
        else:  # pragma: no cover - parametrization is closed
            raise AssertionError(case)
        with pytest.raises(
            DeepSeekV4QueryAExecutableServiceError,
            match="snapshot differs",
        ):
            package.verify()
    finally:
        package.close()


def test_service_source_has_no_forbidden_execution_dependency() -> None:
    source = inspect.getsource(service)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(name.startswith("compiler") for name in imports)
    assert not any(name.startswith("runtime.reference") for name in imports)
    assert not any("safetensors" in name for name in imports)
    assert "expected_output" not in source
    assert "callback" not in source
    assert "fallback arithmetic" not in source
    assert "checkpoint reader" not in source.lower()


def test_complete_execution_persists_exact_closed_result_contract(
    completed_execution: dict[str, Any],
) -> None:
    result = completed_execution["first"]
    root = completed_execution["first_dir"]
    manifest = _json(root / "result_manifest.json")
    assert set(manifest) == {
        "build_id",
        "counter_reconciliation",
        "diagnostics",
        "execution_scope",
        "logical_counters",
        "model_id",
        "numeric_status",
        "outputs",
        "program_sha256",
        "request_sha256",
        "schema",
        "status",
        "token_count",
    }
    assert manifest["schema"] == EXECUTION_RESULT_SCHEMA
    assert manifest["execution_scope"] == "exact_complete_query_a_fragment"
    assert manifest["counter_reconciliation"] == "exact"
    assert manifest["status"] == "pass"
    assert manifest["logical_counters"] == query_a_functional_counters(
        manifest["token_count"]
    )
    assert manifest["numeric_status"]["poison"] is False
    assert _plain_json(result.manifest) == manifest
    assert result.logical_counters == manifest["logical_counters"]

    descriptors = [*manifest["outputs"], *manifest["diagnostics"].values()]
    assert {descriptor["path"] for descriptor in descriptors} == {
        "outputs/attention_normalized.bf16le",
        "outputs/query_a.bf16le",
        "diagnostics/rms_mean.f32le",
        "diagnostics/rms_inverse.f32le",
    }
    for descriptor in descriptors:
        payload = (root / descriptor["path"]).read_bytes()
        assert len(payload) == descriptor["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == descriptor["sha256"]
    assert set(_snapshot(root)) == {
        "diagnostics/rms_inverse.f32le",
        "diagnostics/rms_mean.f32le",
        "outputs/attention_normalized.bf16le",
        "outputs/query_a.bf16le",
        "result_manifest.json",
    }


def test_repeated_execution_is_byte_deterministic_and_inputs_are_immutable(
    completed_execution: dict[str, Any],
) -> None:
    assert _snapshot(completed_execution["first_dir"]) == _snapshot(
        completed_execution["second_dir"]
    )
    assert completed_execution["first"] == completed_execution["second"]
    assert completed_execution["package_before"] == completed_execution["package_after"]
    assert completed_execution["request_before"] == completed_execution["request_after"]


def test_execution_uses_a_real_hc_pre_composed_request(
    completed_execution: dict[str, Any],
) -> None:
    request = _json(completed_execution["request_manifest"])
    assert request["provenance"]["kind"] == "verified_hc_pre_execution_result"
    assert request["provenance"]["source_output_sha256"] == request["input"]["sha256"]


@pytest.mark.parametrize(
    "case",
    [
        "schema",
        "build_id",
        "program_sha256",
        "token_count_bool",
        "input_dtype",
        "input_encoding",
        "input_path",
        "input_shape",
        "input_size",
        "input_hash",
        "provenance_product",
        "provenance_build_id",
        "provenance_output_hash",
        "provenance_schema",
    ],
)
def test_request_contract_mutations_fail_before_publication(
    official_package: Path,
    official_request: Path,
    tmp_path: Path,
    case: str,
) -> None:
    manifest_path = _copy_request(official_request, tmp_path / "request")
    request = _json(manifest_path)
    if case == "schema":
        request["schema"] = "wrong"
    elif case == "build_id":
        request["build_id"] = "0" * 64
    elif case == "program_sha256":
        request["program_sha256"] = "0" * 64
    elif case == "token_count_bool":
        request["token_count"] = True
    elif case == "input_dtype":
        request["input"]["dtype"] = "F16"
    elif case == "input_encoding":
        request["input"]["encoding"] = "native"
    elif case == "input_path":
        request["input"]["path"] = "../escape"
    elif case == "input_shape":
        request["input"]["shape"] = [1, HIDDEN_SIZE - 1]
    elif case == "input_size":
        request["input"]["size_bytes"] += 2
    elif case == "input_hash":
        request["input"]["sha256"] = "a" * 64
    elif case == "provenance_product":
        request["provenance"]["source_sequence_length"] = 2
    elif case == "provenance_build_id":
        assert request["provenance"]["source_build_id"] == HC_PRE_EXECUTABLE_BUILD_ID
        request["provenance"]["source_build_id"] = "a" * 64
    elif case == "provenance_output_hash":
        request["provenance"]["source_output_sha256"] = "a" * 64
    elif case == "provenance_schema":
        request["provenance"]["source_schema"] = "wrong"
    else:  # pragma: no cover - parametrization is closed
        raise AssertionError(case)
    _write_json(manifest_path, request)

    output = tmp_path / "result"
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(DeepSeekV4QueryAExecutableServiceError):
            engine.execute(manifest_path, output)
    assert not output.exists()


def test_nonfinite_request_bf16_poison_fails_closed(
    official_package: Path,
    official_request: Path,
    tmp_path: Path,
) -> None:
    manifest = _copy_request(official_request, tmp_path / "request")
    input_path = manifest.parent / "input/attention_input.bf16le"
    payload = struct.pack("<H", 0x7F80) + input_path.read_bytes()[2:]
    input_path.write_bytes(payload)
    request = _json(manifest)
    digest = hashlib.sha256(payload).hexdigest()
    request["input"]["sha256"] = digest
    request["provenance"]["source_output_sha256"] = digest
    _write_json(manifest, request)
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(
            DeepSeekV4QueryAExecutableServiceError, match="nonfinite BF16"
        ):
            engine.execute(manifest, tmp_path / "result")
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize(
    ("relative", "poison"),
    [
        ("resources/attn_norm_weight.bf16le", b"\x80\x7f"),
        ("resources/query_a_weight.f8e4m3fn", b"\x7f"),
        ("resources/query_a_scale.e8m0", b"\xff"),
    ],
)
def test_packaged_numeric_resource_poison_cannot_cross_identity_boundary(
    official_package: Path,
    tmp_path: Path,
    relative: str,
    poison: bytes,
) -> None:
    package = tmp_path / "package"
    shutil.copytree(official_package, package)
    with (package / relative).open("r+b") as destination:
        destination.write(poison)
    with pytest.raises(DeepSeekV4QueryAExecutableServiceError, match="SHA-256"):
        load_deepseek_v4_query_a_executable_deployment(package)


@pytest.mark.parametrize("case", ["role", "path", "schedule", "counter", "program"])
def test_package_role_path_program_and_contract_mutations_fail_closed(
    official_package: Path,
    tmp_path: Path,
    case: str,
) -> None:
    package = tmp_path / "package"
    shutil.copytree(official_package, package)
    if case in {"role", "path"}:
        manifest_path = package / "deployment_manifest.json"
        manifest = _json(manifest_path)
        if case == "role":
            manifest["artifacts"][0]["role"] = "query_a_weight"
        else:
            manifest["artifacts"][0]["path"] = "../escape"
        _write_json(manifest_path, manifest)
    elif case == "schedule":
        path = package / "schedule/logical_schedule.json"
        schedule = _json(path)
        schedule["slots"][0]["opcode"] = "COMPLETE"
        _write_json(path, schedule)
    elif case == "counter":
        path = package / "interfaces/functional_counter_contract.json"
        counter = _json(path)
        counter["fixed_counters"]["complete_events"] = 2
        _write_json(path, counter)
    elif case == "program":
        path = package / "program/query_a.bin"
        payload = bytearray(path.read_bytes())
        payload[0] ^= 1
        path.write_bytes(payload)
    with pytest.raises(DeepSeekV4QueryAExecutableServiceError):
        load_deepseek_v4_query_a_executable_deployment(package)


@pytest.mark.parametrize("entry_kind", ["symlink", "fifo", "oversize"])
def test_request_rejects_nonregular_and_oversize_input_entries(
    official_package: Path,
    official_request: Path,
    tmp_path: Path,
    entry_kind: str,
) -> None:
    manifest = _copy_request(official_request, tmp_path / "request")
    input_path = manifest.parent / "input/attention_input.bf16le"
    original_payload = input_path.read_bytes()
    input_path.unlink()
    if entry_kind == "symlink":
        outside = tmp_path / "outside.bf16le"
        outside.write_bytes(original_payload)
        input_path.symlink_to(outside)
    elif entry_kind == "fifo":
        os.mkfifo(input_path)
    else:
        input_path.write_bytes(original_payload + b"\x00\x00")
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(DeepSeekV4QueryAExecutableServiceError):
            engine.execute(manifest, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_request_descriptor_replacement_race_is_detected(
    official_package: Path,
    official_request: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _copy_request(official_request, tmp_path / "request")
    input_path = manifest.parent / "input/attention_input.bf16le"
    original = SecureFile.read_bytes
    replaced = False

    def racing_read(self: SecureFile, *, label: str, maximum_bytes: int) -> bytes:
        nonlocal replaced
        payload = original(self, label=label, maximum_bytes=maximum_bytes)
        if self.relative_path == "input/attention_input.bf16le" and not replaced:
            peer = input_path.with_suffix(".replacement")
            peer.write_bytes(payload)
            os.replace(peer, input_path)
            replaced = True
        return payload

    monkeypatch.setattr(SecureFile, "read_bytes", racing_read)
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(DeepSeekV4QueryAExecutableServiceError, match="failed"):
            engine.execute(manifest, tmp_path / "result")
    assert replaced
    assert not (tmp_path / "result").exists()


def test_package_descriptor_replacement_race_is_detected(
    official_package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "package"
    shutil.copytree(official_package, package)
    scale_path = package / "resources/query_a_scale.e8m0"
    original = SecureFile.read_bytes
    replaced = False

    def racing_read(self: SecureFile, *, label: str, maximum_bytes: int) -> bytes:
        nonlocal replaced
        payload = original(self, label=label, maximum_bytes=maximum_bytes)
        if self.relative_path == "resources/query_a_scale.e8m0" and not replaced:
            peer = scale_path.with_suffix(".replacement")
            peer.write_bytes(payload)
            os.replace(peer, scale_path)
            replaced = True
        return payload

    monkeypatch.setattr(SecureFile, "read_bytes", racing_read)
    with pytest.raises(DeepSeekV4QueryAExecutableServiceError, match="failed"):
        load_deepseek_v4_query_a_executable_deployment(package)
    assert replaced


def _publisher_only_numeric(
    completed_execution: dict[str, Any],
) -> QueryAServiceNumericResult:
    result = completed_execution["first"]
    return QueryAServiceNumericResult(
        normalized_codes=result.attention_normalized_codes,
        query_a_codes=result.query_a_codes,
        mean_square_codes=result.rms_mean_codes,
        inverse_rms_codes=result.rms_inverse_codes,
        rms_output_saturation_count=result.numeric_status[
            "rms_output_saturation_count"
        ],
        activation_saturated_block_count=result.numeric_status[
            "activation_saturated_block_count"
        ],
        query_output_saturated_element_count=result.numeric_status[
            "query_output_saturated_element_count"
        ],
    )


def test_create_once_output_preserves_existing_tree_without_reexecution(
    official_package: Path,
    completed_execution: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _copy_request(
        completed_execution["request_manifest"], tmp_path / "request"
    )
    output = tmp_path / "result"
    output.mkdir()
    marker = output / "peer.txt"
    marker.write_bytes(b"peer-owned\n")
    monkeypatch.setattr(
        service,
        "_execute_program",
        lambda *_: _publisher_only_numeric(completed_execution),
    )
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(
            DeepSeekV4QueryAExecutableServiceError,
            match="already exists",
        ):
            engine.execute(manifest, output)
    assert marker.read_bytes() == b"peer-owned\n"
    assert _snapshot(output) == {
        "peer.txt": (
            stat.S_IMODE(marker.stat().st_mode),
            hashlib.sha256(b"peer-owned\n").hexdigest(),
        )
    }


def test_competing_peer_at_publication_is_preserved(
    official_package: Path,
    completed_execution: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _copy_request(
        completed_execution["request_manifest"], tmp_path / "request"
    )
    output = tmp_path / "result"
    original_publish = service.publish_payload_tree

    def racing_publish(path: Path, **kwargs: object) -> None:
        path.mkdir()
        (path / "peer.txt").write_bytes(b"won-race\n")
        original_publish(path, **kwargs)

    monkeypatch.setattr(
        service,
        "_execute_program",
        lambda *_: _publisher_only_numeric(completed_execution),
    )
    monkeypatch.setattr(service, "publish_payload_tree", racing_publish)
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(DeepSeekV4QueryAExecutableServiceError, match="failed"):
            engine.execute(manifest, output)
    assert (output / "peer.txt").read_bytes() == b"won-race\n"
    assert list(output.iterdir()) == [output / "peer.txt"]


def test_failed_staged_publication_cleans_only_its_private_tree(
    official_package: Path,
    completed_execution: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runtime.service_engine import secure_artifacts

    manifest = _copy_request(
        completed_execution["request_manifest"], tmp_path / "request"
    )
    output = tmp_path / "result"
    original_write = secure_artifacts._write_exclusive_bytes
    writes = 0

    def failing_write(root_descriptor: int, relative: str, payload: bytes) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise SecureArtifactError("injected staged write failure")
        original_write(root_descriptor, relative, payload)

    monkeypatch.setattr(
        service,
        "_execute_program",
        lambda *_: _publisher_only_numeric(completed_execution),
    )
    monkeypatch.setattr(secure_artifacts, "_write_exclusive_bytes", failing_write)
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(DeepSeekV4QueryAExecutableServiceError, match="failed"):
            engine.execute(manifest, output)
    assert writes == 2
    assert not output.exists()
    assert not list(tmp_path.glob(".result.tmp-*"))


def test_published_result_is_create_once_and_unchanged_on_retry(
    official_package: Path,
    completed_execution: dict[str, Any],
) -> None:
    output = completed_execution["first_dir"]
    before = _snapshot(output)
    with DeepSeekV4QueryAExecutableServiceEngine.load(official_package) as engine:
        with pytest.raises(
            DeepSeekV4QueryAExecutableServiceError, match="already exists"
        ):
            engine.execute(completed_execution["request_manifest"], output)
    assert _snapshot(output) == before


def test_result_payload_encodings_match_returned_architectural_codes(
    completed_execution: dict[str, Any],
) -> None:
    root = completed_execution["first_dir"]
    result = completed_execution["first"]
    normalized = tuple(
        code
        for (code,) in struct.iter_unpack(
            "<H",
            (root / "outputs/attention_normalized.bf16le").read_bytes(),
        )
    )
    query_a = tuple(
        code
        for (code,) in struct.iter_unpack(
            "<H",
            (root / "outputs/query_a.bf16le").read_bytes(),
        )
    )
    rms_mean = tuple(
        code
        for (code,) in struct.iter_unpack(
            "<I",
            (root / "diagnostics/rms_mean.f32le").read_bytes(),
        )
    )
    rms_inverse = tuple(
        code
        for (code,) in struct.iter_unpack(
            "<I",
            (root / "diagnostics/rms_inverse.f32le").read_bytes(),
        )
    )
    assert normalized == tuple(
        code for row in result.attention_normalized_codes for code in row
    )
    assert query_a == tuple(code for row in result.query_a_codes for code in row)
    assert rms_mean == result.rms_mean_codes
    assert rms_inverse == result.rms_inverse_codes


def test_result_and_request_manifests_are_canonical_bytes(
    completed_execution: dict[str, Any],
) -> None:
    for path in (
        completed_execution["request_manifest"],
        completed_execution["first_dir"] / "result_manifest.json",
        completed_execution["second_dir"] / "result_manifest.json",
    ):
        payload = path.read_bytes()
        assert canonical_json_bytes(json.loads(payload)) == payload


def test_complete_result_does_not_expand_the_evidence_claim(
    completed_execution: dict[str, Any],
) -> None:
    manifest = _json(completed_execution["first_dir"] / "result_manifest.json")
    serialized = canonical_json_bytes(manifest).lower()
    for forbidden_claim in (
        b"cycles",
        b"bandwidth",
        b"physical_schedule",
        b"ppa",
        b"full_model_execution",
        b"nvidia_comparison",
    ):
        assert forbidden_claim not in serialized
    assert manifest["execution_scope"] == "exact_complete_query_a_fragment"
