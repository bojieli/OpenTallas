from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import runtime.service_engine.deepseek_v4_hc_pre_executable as executable_module
from runtime.service_engine.deepseek_v4_hc_pre_executable import (
    EXECUTABLE_BUILD_ID,
    EXECUTION_RESULT_SCHEMA,
    MODEL_ID,
    PROGRAM_SHA256,
    DeepSeekV4HCPreExecutableDeployment,
    DeepSeekV4HCPreExecutableServiceEngine,
    DeepSeekV4HCPreExecutableServiceError,
    execute_deepseek_v4_hc_pre_executable_deployment,
    load_deepseek_v4_hc_pre_executable_deployment,
)


_EVIDENCE_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_EVIDENCE_ROOT"
_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_SNAPSHOT"
_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
_CACHE_ROOT = Path(
    os.environ.get(
        _EVIDENCE_ENV,
        Path.home() / ".cache/opentallas/deepseek-v4-flash-0731",
    )
)
_OFFICIAL_DEPLOYMENT = _CACHE_ROOT / "hc-pre-executable"
_OFFICIAL_REQUEST = _CACHE_ROOT / "hc-pre-request"
_OFFICIAL_SNAPSHOT = Path(
    os.environ.get(
        _SNAPSHOT_ENV,
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / _REVISION,
    )
)
_OFFICIAL_APPLICATION = _CACHE_ROOT / "hc-pre-canonical"
_OFFICIAL_LOCK = _CACHE_ROOT / "checkpoint.lock.json"
_REQUEST_SHA256 = "e05d203131ef647edd1c3f4b951c4359f3f2e03690dde247f620ec092bd73184"
_INPUT_SHA256 = "f0ea58b5da876ba4fd41b5a72b2721d7d300c1bd6377db558eac08f57e7dc9e6"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _write(path: Path, value: object) -> None:
    path.write_bytes(_canonical(value))


def _require_official() -> None:
    if not (_OFFICIAL_DEPLOYMENT.is_dir() and _OFFICIAL_REQUEST.is_dir()):
        pytest.skip("official HC_PRE executable integration cache is unavailable")


@pytest.fixture
def official_copy(tmp_path: Path) -> tuple[Path, Path]:
    _require_official()
    deployment = tmp_path / "deployment"
    request = tmp_path / "request"
    shutil.copytree(_OFFICIAL_DEPLOYMENT, deployment)
    shutil.copytree(_OFFICIAL_REQUEST, request)
    return deployment, request / "request_manifest.json"


def _descriptor_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    descriptors = {item["id"]: item for item in manifest["outputs"]}
    descriptors.update({item["id"]: item for item in manifest["diagnostics"].values()})
    return descriptors


def _flatten(value: object) -> tuple[int, ...]:
    if type(value) is int:
        return (value,)
    assert type(value) is tuple
    return tuple(code for child in value for code in _flatten(child))


def _packed(value: object, bits: int) -> bytes:
    codes = _flatten(value)
    return struct.pack(f"<{len(codes)}{'H' if bits == 16 else 'I'}", *codes)


def _thaw(value: object) -> object:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _thaw(child) for key, child in value.items()}  # type: ignore[union-attr]
    if type(value) is tuple:
        return [_thaw(child) for child in value]
    return value


def _replace_identically(path: Path) -> None:
    replacement = path.with_name(path.name + ".replacement")
    replacement.write_bytes(path.read_bytes())
    os.replace(replacement, path)


def _mutate_request(
    request_manifest: Path,
    mutator: Any,
) -> None:
    manifest = _load(request_manifest)
    mutator(manifest)
    _write(request_manifest, manifest)


def test_official_builder_loader_execute_and_result_publication(
    tmp_path: Path,
) -> None:
    _require_official()
    if not (
        _OFFICIAL_SNAPSHOT.is_dir()
        and _OFFICIAL_APPLICATION.is_dir()
        and _OFFICIAL_LOCK.is_file()
    ):
        pytest.skip("official HC_PRE builder inputs are unavailable")
    from compiler.vertical_slice.deepseek_v4_hc_pre_executable import (
        build_deepseek_v4_hc_pre_executable_deployment,
    )

    deployment = tmp_path / "built"
    built = build_deepseek_v4_hc_pre_executable_deployment(
        snapshot=_OFFICIAL_SNAPSHOT,
        lock=_load(_OFFICIAL_LOCK),
        application_root=_OFFICIAL_APPLICATION,
        output=deployment,
    )
    assert built["build_id"] == EXECUTABLE_BUILD_ID
    result_root = tmp_path / "result"
    result = execute_deepseek_v4_hc_pre_executable_deployment(
        deployment,
        _OFFICIAL_REQUEST / "request_manifest.json",
        result_root,
    )
    assert result.request_sha256 == _REQUEST_SHA256
    assert len(result.logical_counters) == 27
    assert result.branch_saturation_count == 0
    assert (result_root / "result_manifest.json").is_file()


def test_complete_official_result_bytes_shapes_hashes_and_counters(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment_root, request_manifest = official_copy
    result_root = tmp_path / "result"
    with DeepSeekV4HCPreExecutableServiceEngine.load(deployment_root) as engine:
        result = engine.execute(request_manifest, result_root)

    manifest_payload = (result_root / "result_manifest.json").read_bytes()
    manifest = json.loads(manifest_payload)
    assert manifest_payload == _canonical(manifest)
    assert manifest == _thaw(result.manifest)
    assert manifest["schema"] == EXECUTION_RESULT_SCHEMA
    assert manifest["build_id"] == EXECUTABLE_BUILD_ID
    assert manifest["model_id"] == MODEL_ID
    assert manifest["program_sha256"] == PROGRAM_SHA256
    assert manifest["request_sha256"] == _REQUEST_SHA256
    assert manifest["batch_size"] == 1
    assert manifest["sequence_length"] == 1
    assert manifest["token_count"] == 1
    assert manifest["counter_reconciliation"] == "exact"
    assert result.counter_reconciliation == "exact"
    assert dict(result.numeric_status) == manifest["numeric_status"]
    assert manifest["execution_scope"] == "exact_hc_pre_site_only"
    assert manifest["status"] == "pass"
    assert manifest["numeric_status"] == {
        "branch_saturation_count": result.branch_saturation_count,
        "poison": False,
    }
    assert (
        manifest["logical_counters"]["hc_pre_branch_bf16_saturations"]
        == result.branch_saturation_count
    )

    result_schema = _load(
        deployment_root / "interfaces/execution_result_v1.schema.json"
    )
    Draft202012Validator(result_schema).validate(manifest)
    request_schema = _load(
        deployment_root / "interfaces/execution_request_v1.schema.json"
    )
    Draft202012Validator(request_schema).validate(_load(request_manifest))

    descriptors = _descriptor_map(manifest)
    expected = {
        "attention_input": (result.attention_input_codes, 16, [1, 1, 4096]),
        "attention_pre": (result.attention_pre_codes, 32, [1, 1, 4]),
        "attention_post": (result.attention_post_codes, 32, [1, 1, 4]),
        "attention_combination": (
            result.attention_combination_codes,
            32,
            [1, 1, 4, 4],
        ),
        "attention_residual": (
            result.attention_residual_codes,
            16,
            [1, 1, 4, 4096],
        ),
        "rms_mean_codes": (result.rms_mean_codes, 32, [1, 1]),
        "rms_inverse_codes": (result.rms_inverse_codes, 32, [1, 1]),
        "projection_codes": (result.projection_codes, 32, [1, 1, 24]),
        "mix_codes": (result.mix_codes, 32, [1, 1, 24]),
        "stable_softmax_codes": (
            result.stable_softmax_codes,
            32,
            [1, 1, 4, 4],
        ),
    }
    assert set(descriptors) == set(expected)
    for identifier, (codes, bits, shape) in expected.items():
        descriptor = descriptors[identifier]
        payload = (result_root / descriptor["path"]).read_bytes()
        assert descriptor["shape"] == shape
        assert descriptor["size_bytes"] == len(payload)
        assert descriptor["sha256"] == hashlib.sha256(payload).hexdigest()
        assert payload == _packed(codes, bits)
    assert (result_root / descriptors["attention_residual"]["path"]).read_bytes() == (
        request_manifest.parent / "input/hc_hidden.bf16le"
    ).read_bytes()
    assert _load(request_manifest)["input"]["sha256"] == _INPUT_SHA256

    counter_contract = _load(deployment_root / "parameters/counter_contract.json")
    expected_counters = counter_contract["per_successfully_committed_token"]
    expected_counters["hc_pre_branch_bf16_saturations"] = result.branch_saturation_count
    assert dict(result.logical_counters) == expected_counters
    assert manifest["logical_counters"] == expected_counters

    expected_tree = {
        "diagnostics",
        "diagnostics/mix.f32le",
        "diagnostics/projection.f32le",
        "diagnostics/rms_inverse.f32le",
        "diagnostics/rms_mean.f32le",
        "diagnostics/stable_softmax.f32le",
        "outputs",
        "outputs/attention_combination.f32le",
        "outputs/attention_input.bf16le",
        "outputs/attention_post.f32le",
        "outputs/attention_pre.f32le",
        "outputs/attention_residual.bf16le",
        "result_manifest.json",
    }
    assert {
        path.relative_to(result_root).as_posix() for path in result_root.rglob("*")
    } == expected_tree


def test_result_and_nested_manifest_are_immutable(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    with DeepSeekV4HCPreExecutableServiceEngine.load(deployment) as engine:
        result = engine.execute(request, tmp_path / "result")
    with pytest.raises(TypeError):
        result.logical_counters["hc_pre_rms_divides"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        result.manifest["status"] = "fail"  # type: ignore[index]
    diagnostics = result.manifest["diagnostics"]
    with pytest.raises(TypeError):
        diagnostics["mix_codes"] = {}  # type: ignore[index]
    assert type(result.manifest["outputs"]) is tuple


def test_runtime_executes_packaged_program_without_host_assembly(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    import compiler.microcode.deepseek_v4_hc_pre as compiler_microcode

    monkeypatch.setattr(
        compiler_microcode,
        "assemble",
        lambda: (_ for _ in ()).throw(AssertionError("host assembly called")),
    )
    result = execute_deepseek_v4_hc_pre_executable_deployment(
        deployment,
        request,
        tmp_path / "result",
    )
    assert result.status == "pass"
    source = inspect.getsource(executable_module)
    assert "compiler.microcode" not in source
    assert "runtime.reference" not in source


def test_one_shot_and_context_manager_close_owned_mappings(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    engine = DeepSeekV4HCPreExecutableServiceEngine.load(deployment)
    payloads = engine.deployment._mapped_payloads
    with engine:
        engine.execute(request, tmp_path / "result")
    assert all(payload._descriptor == -1 for payload in payloads)
    engine.close()
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="closed"):
        engine.execute(request, tmp_path / "second")


def test_one_shot_closes_mappings_on_success_and_request_failure(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    original = executable_module._MappedF32Payload.close
    closed: set[int] = set()

    def tracked_close(payload: Any) -> None:
        if payload._descriptor >= 0:
            closed.add(id(payload))
        original(payload)

    monkeypatch.setattr(executable_module._MappedF32Payload, "close", tracked_close)
    execute_deepseek_v4_hc_pre_executable_deployment(
        deployment,
        request,
        tmp_path / "result",
    )
    assert len(closed) == 3

    closed.clear()
    _mutate_request(request, lambda value: value.__setitem__("build_id", "0" * 64))
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "failed",
        )
    assert len(closed) == 3


def test_engine_rejects_hostile_deployment_subclass() -> None:
    class HostileDeployment(DeepSeekV4HCPreExecutableDeployment):
        def _verify_snapshot(self) -> None:
            return None

    hostile = object.__new__(HostileDeployment)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="invalid"):
        DeepSeekV4HCPreExecutableServiceEngine(hostile)


@pytest.mark.parametrize(
    ("relative", "replacement"),
    [
        ("program/hc_pre.bin", b"X"),
        ("program/program_contract.json", b"{}\n"),
        ("schedule/logical_schedule.json", b"{}\n"),
        ("schedule/logical_schedule_certificate.json", b"{}\n"),
        ("execution_coverage.json", b"{}\n"),
        ("interfaces/execution_request_v1.schema.json", b"{}\n"),
        ("interfaces/execution_result_v1.schema.json", b"{}\n"),
    ],
)
def test_loader_rejects_mutated_executable_contract_artifacts(
    official_copy: tuple[Path, Path],
    relative: str,
    replacement: bytes,
) -> None:
    deployment, _ = official_copy
    (deployment / relative).write_bytes(replacement)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)


@pytest.mark.parametrize(
    "role",
    ["hc_base_parameter", "hc_projection_parameter", "hc_scale_parameter"],
)
def test_loader_rejects_one_bit_learned_payload_mutation(
    official_copy: tuple[Path, Path],
    role: str,
) -> None:
    deployment, _ = official_copy
    manifest = _load(deployment / "deployment_manifest.json")
    relative = next(
        record["path"] for record in manifest["artifacts"] if record["role"] == role
    )
    path = deployment / relative
    payload = bytearray(path.read_bytes())
    payload[len(payload) // 2] ^= 1
    path.write_bytes(payload)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "device"])
def test_loader_rejects_nonregular_executable_artifact(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    kind: str,
) -> None:
    deployment, _ = official_copy
    artifact = deployment / "execution_coverage.json"
    payload = artifact.read_bytes()
    artifact.unlink()
    if kind == "symlink":
        outside = tmp_path / "outside.json"
        outside.write_bytes(payload)
        artifact.symlink_to(outside)
    elif kind == "fifo":
        os.mkfifo(artifact)
    else:
        try:
            os.mknod(artifact, stat.S_IFCHR | 0o600, os.makedev(1, 3))
        except PermissionError:
            pytest.skip("creating a temporary device node is not permitted")
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)


def test_loader_rejects_oversized_manifest(
    official_copy: tuple[Path, Path],
) -> None:
    deployment, _ = official_copy
    manifest = deployment / "deployment_manifest.json"
    with manifest.open("ab") as stream:
        stream.truncate(executable_module._MAX_MANIFEST_BYTES + 1)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="exceeds"):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)


def test_loader_rejects_extra_tree_entry(
    official_copy: tuple[Path, Path],
) -> None:
    deployment, _ = official_copy
    (deployment / "unexpected").write_bytes(b"x")
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="unlisted"):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)


def test_loader_rejects_identical_artifact_replacement_during_load(
    official_copy: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, _ = official_copy
    original = executable_module._read_bytes
    replaced = False

    def replacing_read(source: Any, label: str, maximum: int) -> bytes:
        nonlocal replaced
        payload = original(source, label, maximum)
        if "program/hc_pre.bin" in label and not replaced:
            _replace_identically(deployment / "program/hc_pre.bin")
            replaced = True
        return payload

    monkeypatch.setattr(executable_module, "_read_bytes", replacing_read)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="changed|replaced"):
        load_deepseek_v4_hc_pre_executable_deployment(deployment)
    assert replaced


def test_loaded_engine_rejects_identical_artifact_replacement(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    with DeepSeekV4HCPreExecutableServiceEngine.load(deployment) as engine:
        _replace_identically(deployment / "program/hc_pre.bin")
        with pytest.raises(
            DeepSeekV4HCPreExecutableServiceError, match="changed|replaced"
        ):
            engine.execute(request, tmp_path / "result")
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.__setitem__("batch_size", True),
        lambda value: value.__setitem__("token_count", False),
        lambda value: value.__setitem__("build_id", "0" * 64),
        lambda value: value.__setitem__("program_sha256", "0" * 64),
        lambda value: value.__setitem__("model_id", "deepseek-v3"),
        lambda value: value.__setitem__("schema", "wrong"),
        lambda value: value.__setitem__("sequence_length", 2),
        lambda value: value.__setitem__("unknown", 0),
        lambda value: value["input"].__setitem__("shape", [1, 1, 4, True]),
        lambda value: value["input"].__setitem__("register", "ATTENTION_INPUT"),
        lambda value: value["input"].__setitem__("path", "../hidden.bf16le"),
        lambda value: value["input"].__setitem__("sha256", "0" * 64),
        lambda value: value["input"].__setitem__("size_bytes", True),
    ],
)
def test_request_identity_shape_and_type_confusion_fail_closed(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    mutator: Any,
) -> None:
    deployment, request = official_copy
    _mutate_request(request, mutator)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()


def test_request_rejects_noncanonical_duplicate_json(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    request.write_bytes(request.read_bytes()[:-2] + b',"token_count":1}\n')
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="duplicate"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )


def test_request_rejects_nonfinite_bf16_even_with_matching_hash(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    input_path = request.parent / "input/hc_hidden.bf16le"
    payload = bytearray(input_path.read_bytes())
    payload[:2] = struct.pack("<H", 0x7F80)
    input_path.write_bytes(payload)
    manifest = _load(request)
    manifest["input"]["sha256"] = hashlib.sha256(payload).hexdigest()
    _write(request, manifest)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="nonfinite"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()


def test_batch_and_sequence_axes_remain_distinct_end_to_end(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    input_path = request.parent / "input/hc_hidden.bf16le"
    one_token = input_path.read_bytes()
    payload = one_token * 4
    input_path.write_bytes(payload)
    manifest = _load(request)
    manifest["batch_size"] = 2
    manifest["sequence_length"] = 2
    manifest["token_count"] = 4
    manifest["input"]["shape"] = [2, 2, 4, 4096]
    manifest["input"]["size_bytes"] = len(payload)
    manifest["input"]["sha256"] = hashlib.sha256(payload).hexdigest()
    _write(request, manifest)

    result_root = tmp_path / "result"
    result = execute_deepseek_v4_hc_pre_executable_deployment(
        deployment,
        request,
        result_root,
    )
    assert (result.batch_size, result.sequence_length, result.token_count) == (2, 2, 4)
    assert len(result.attention_input_codes) == 2
    assert all(len(batch) == 2 for batch in result.attention_input_codes)
    published = _load(result_root / "result_manifest.json")
    descriptors = _descriptor_map(published)
    assert descriptors["attention_input"]["shape"] == [2, 2, 4096]
    assert descriptors["attention_residual"]["shape"] == [2, 2, 4, 4096]
    assert descriptors["stable_softmax_codes"]["shape"] == [2, 2, 4, 4]
    coefficients = _load(deployment / "parameters/counter_contract.json")[
        "per_successfully_committed_token"
    ]
    for name, coefficient in coefficients.items():
        assert result.logical_counters[name] == coefficient * 4


@pytest.mark.parametrize("kind", ["symlink", "fifo", "device"])
def test_request_rejects_nonregular_input(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    kind: str,
) -> None:
    deployment, request = official_copy
    input_path = request.parent / "input/hc_hidden.bf16le"
    payload = input_path.read_bytes()
    input_path.unlink()
    if kind == "symlink":
        target = tmp_path / "outside.bf16le"
        target.write_bytes(payload)
        input_path.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(input_path)
    else:
        try:
            os.mknod(input_path, stat.S_IFCHR | 0o600, os.makedev(1, 3))
        except PermissionError:
            pytest.skip("creating a temporary device node is not permitted")
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()


def test_request_rejects_oversized_manifest_before_decode(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    with request.open("ab") as stream:
        stream.truncate(executable_module._MAX_REQUEST_JSON_BYTES + 1)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="exceeds"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )


def test_request_rejects_extra_tree_entry(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    (request.parent / "unexpected").write_bytes(b"x")
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="unlisted"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )


def test_request_rejects_identical_replacement_during_load(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    original = executable_module._read_bytes
    replaced = False

    def replacing_read(source: Any, label: str, maximum: int) -> bytes:
        nonlocal replaced
        payload = original(source, label, maximum)
        if label == "HC_PRE request BF16 input" and not replaced:
            _replace_identically(request.parent / "input/hc_hidden.bf16le")
            replaced = True
        return payload

    monkeypatch.setattr(executable_module, "_read_bytes", replacing_read)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="changed|replaced"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert replaced
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize("source_kind", ["request", "deployment"])
def test_identical_source_replacement_during_arithmetic_blocks_publication(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    deployment, request = official_copy
    original = executable_module.hc_pre_numeric.execute_hc_pre

    def execute_then_replace(*args: Any, **kwargs: Any) -> Any:
        numeric = original(*args, **kwargs)
        if source_kind == "request":
            target = request.parent / "input/hc_hidden.bf16le"
        else:
            target = deployment / "program/hc_pre.bin"
        _replace_identically(target)
        return numeric

    monkeypatch.setattr(
        executable_module.hc_pre_numeric,
        "execute_hc_pre",
        execute_then_replace,
    )
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="changed|replaced"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()


def test_numeric_poison_leaves_no_result_or_staging_directory(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy

    def poison(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise executable_module.hc_pre_numeric.HCPreServiceNumericError("poison")

    monkeypatch.setattr(executable_module.hc_pre_numeric, "execute_hc_pre", poison)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="poisoned"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


def test_hostile_numeric_result_subclass_cannot_publish(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy

    class HostileNumericResult(executable_module.hc_pre_numeric.HCPreServiceResult):
        pass

    hostile = object.__new__(HostileNumericResult)
    monkeypatch.setattr(
        executable_module.hc_pre_numeric,
        "execute_hc_pre",
        lambda *args, **kwargs: hostile,
    )
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="invalid result"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()


def test_late_result_verification_failure_is_atomic(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy

    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise DeepSeekV4HCPreExecutableServiceError("late result failure")

    monkeypatch.setattr(executable_module, "_verify_staged_result", fail)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="late"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            tmp_path / "result",
        )
    assert not (tmp_path / "result").exists()
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


def test_create_once_race_preserves_competing_output_and_cleans_staging(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    result_root = tmp_path / "result"
    original = executable_module._publish_create_once

    def collide(**kwargs: Any) -> None:
        result_root.mkdir()
        (result_root / "competitor").write_bytes(b"preserve")
        original(**kwargs)

    monkeypatch.setattr(executable_module, "_publish_create_once", collide)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="already exists"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            result_root,
        )
    assert (result_root / "competitor").read_bytes() == b"preserve"
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


def test_post_rename_parent_fsync_failure_rolls_back_publication(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    result_root = tmp_path / "result"
    original = executable_module.os.fsync
    injected = False

    def fail_after_rename(descriptor: int) -> None:
        nonlocal injected
        descriptor_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if descriptor_path == tmp_path and result_root.exists() and not injected:
            injected = True
            raise OSError("injected parent fsync failure")
        original(descriptor)

    monkeypatch.setattr(executable_module.os, "fsync", fail_after_rename)
    with pytest.raises(
        DeepSeekV4HCPreExecutableServiceError, match="synchronize published"
    ):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            result_root,
        )
    assert injected
    assert not result_root.exists()
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


def test_post_rename_identity_race_preserves_sentinel_and_removes_our_tree(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, request = official_copy
    result_root = tmp_path / "result"
    original = executable_module._publish_create_once
    raced = False

    def replace_after_rename(**kwargs: Any) -> None:
        nonlocal raced
        original(**kwargs)
        if raced:
            return
        raced = True
        os.rename(
            kwargs["output_name"],
            kwargs["temporary_name"],
            src_dir_fd=kwargs["parent_descriptor"],
            dst_dir_fd=kwargs["parent_descriptor"],
        )
        os.mkdir(kwargs["output_name"], dir_fd=kwargs["parent_descriptor"])
        (result_root / "sentinel").write_bytes(b"preserve")

    monkeypatch.setattr(
        executable_module,
        "_publish_create_once",
        replace_after_rename,
    )
    with pytest.raises(
        DeepSeekV4HCPreExecutableServiceError,
        match="does not name the verified result directory",
    ):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            result_root,
        )
    assert raced
    assert (result_root / "sentinel").read_bytes() == b"preserve"
    assert not (result_root / "result_manifest.json").exists()
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


@pytest.mark.parametrize("collision", ["directory", "file", "symlink"])
def test_result_publication_is_create_once(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
    collision: str,
) -> None:
    deployment, request = official_copy
    result = tmp_path / "result"
    marker = tmp_path / "marker"
    marker.write_bytes(b"preserve")
    if collision == "directory":
        result.mkdir()
        (result / "marker").write_bytes(b"preserve")
    elif collision == "file":
        result.write_bytes(b"preserve")
    else:
        result.symlink_to(marker)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="already exists"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            result,
        )
    assert marker.read_bytes() == b"preserve"
    if collision == "directory":
        assert (result / "marker").read_bytes() == b"preserve"
    elif collision == "file":
        assert result.read_bytes() == b"preserve"
    else:
        assert result.is_symlink()
    assert not list(tmp_path.glob(".hc-pre-result.tmp-*"))


def test_request_manifest_name_is_fixed(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    wrong = request.with_name("request.json")
    request.rename(wrong)
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="named"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            wrong,
            tmp_path / "result",
        )


def test_result_root_name_rejects_noncanonical_backslash(
    official_copy: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    deployment, request = official_copy
    output = tmp_path / "bad\\name"
    with pytest.raises(DeepSeekV4HCPreExecutableServiceError, match="safe child"):
        execute_deepseek_v4_hc_pre_executable_deployment(
            deployment,
            request,
            output,
        )
    assert not output.exists()
