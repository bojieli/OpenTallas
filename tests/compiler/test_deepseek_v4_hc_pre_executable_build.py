from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import compiler.checking.deepseek_v4_hc_pre_executable as executable_checker_module
import compiler.vertical_slice.deepseek_v4_hc_pre_executable as executable_builder_module
from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_hc_pre_executable import (
    DeepSeekV4HCPreExecutableCheckError,
    verify_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.checking.deepseek_v4_hc_pre_slice import (
    verify_deepseek_v4_hc_pre_deployment,
)
from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.ir.model import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.microcode.deepseek_v4_hc_pre import (
    assemble,
    build_program_contract,
    disassemble,
    encode,
)
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    BASE_NAME,
    PROJECTION_NAME,
    SCALE_NAME,
)
from compiler.vertical_slice.deepseek_v4_hc_pre_executable import (
    CLAIM_BOUNDARY,
    DEPLOYMENT_STATUS,
    ENTRYPOINT,
    DeepSeekV4HCPreExecutableBuildError,
    build_deepseek_v4_hc_pre_executable_deployment,
)


FIXTURE_REVISION = "abcdef0123456789abcdef0123456789abcdef01"
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/compiler/deepseek_v4_hc_pre_executable"
SHAPES = {
    BASE_NAME: [24],
    PROJECTION_NAME: [24, 16384],
    SCALE_NAME: [3],
}
PROGRAM_SHA256 = "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
PROGRAM_CONTRACT_ID = "08446f291c0080b5fdfeffb8165cf5939e09f43c2d6ac77216b65a01a56b5428"
SCHEDULE_ID = "40015466a3736ad3c94d84029e1ad1d65d4a80ad9ad75511a1d81626e573c4f9"
CERTIFICATE_ID = "c4c0e29e7caf015bfc4dba54a7ea4e974b1c935f9c3926163ed4a23147bd1e32"


def _safetensors(tensors: list[tuple[str, str, list[int], bytes]]) -> bytes:
    header: dict[str, Any] = {}
    payload = bytearray()
    for name, dtype, shape, tensor_payload in tensors:
        start = len(payload)
        payload.extend(tensor_payload)
        header[name] = {
            "data_offsets": [start, len(payload)],
            "dtype": dtype,
            "shape": shape,
        }
    raw_header = json.dumps(
        header,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    raw_header += b" " * (-len(raw_header) % 8)
    return struct.pack("<Q", len(raw_header)) + raw_header + bytes(payload)


def _finite_payload(element_count: int, seed: int) -> bytes:
    patterns = (
        (0x00000000, 0x80000000, 0x00000001, 0x3F000000),
        (0x3F800000, 0xBF400000, 0x3EAAAAAB, 0x00800000),
        (0x40000000, 0x3DCCCCCD, 0xC0000000, 0x007FFFFF),
    )
    packed = struct.pack("<4I", *patterns[seed % len(patterns)])
    return (packed * ((element_count + 3) // 4))[: element_count * 4]


def _output(name: str, rank: int, shape: list[int]) -> dict[str, Any]:
    elements = 1
    for extent in shape:
        elements *= extent
    return {
        "logical_dtype": "FP32",
        "name": name,
        "payload_bytes": elements * 4,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": shape,
        "source_slice": None,
        "storage_dtype": "F32",
        "transform": "identity",
    }


def _plan() -> list[dict[str, Any]]:
    roles = {
        BASE_NAME: "hyper_connection.attn.base",
        PROJECTION_NAME: "hyper_connection.attn.projection",
        SCALE_NAME: "hyper_connection.attn.scale",
    }
    records: list[dict[str, Any]] = []
    for name in (BASE_NAME, PROJECTION_NAME, SCALE_NAME):
        shape = SHAPES[name]
        elements = 1
        for extent in shape:
            elements *= extent
        records.append(
            {
                "action": "replicate_identity",
                "logical_dtype": "FP32",
                "name": name,
                "outputs": [_output(name, rank, shape) for rank in range(4)],
                "semantic_role": roles[name],
                "shape": shape,
                "size_bytes": elements * 4,
                "storage_dtype": "F32",
            }
        )
    return records


def _materialize_application(
    root: Path,
) -> tuple[Path, dict[str, Any], Path, dict[str, bytes]]:
    plan = _plan()
    root.mkdir(parents=True)
    snapshot = root / "snapshot"
    snapshot.mkdir()
    tensors: list[tuple[str, str, list[int], bytes]] = []
    payloads_by_name: dict[str, bytes] = {}
    for index, record in enumerate(plan):
        name = record["name"]
        payload = _finite_payload(record["size_bytes"] // 4, index)
        payloads_by_name[name] = payload
        tensors.append((name, "F32", record["shape"], payload))

    checkpoint_files = {
        "config.json": canonical_json_bytes({"architectures": ["HCPreFixture"]}),
        "model.safetensors": _safetensors(tensors),
    }
    checkpoint_files["model.safetensors.index.json"] = canonical_json_bytes(
        {
            "metadata": {"total_size": sum(len(item[3]) for item in tensors)},
            "weight_map": {name: "model.safetensors" for name, _, _, _ in tensors},
        }
    )
    for name, payload in checkpoint_files.items():
        (snapshot / name).write_bytes(payload)
    source = validate_checkpoint_source(
        {
            "checkpoint_index": "model.safetensors.index.json",
            "expected_files": [
                {
                    "path": name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
                for name, payload in sorted(checkpoint_files.items())
            ],
            "remote_code_policy": "disabled",
            "repository": "OpenTallas/deepseek-v4-hc-pre-fixture",
            "required_files": ["config.json"],
            "revision": FIXTURE_REVISION,
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    application = root / "canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_hc_pre_fixture_plan.v1",
        plan_inputs=plan,
        output=application,
    )
    return snapshot, lock, application, payloads_by_name


@pytest.fixture
def hc_pre_application(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], Path, dict[str, bytes]]:
    return _materialize_application(tmp_path / "source")


def _build(
    source: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    output: Path,
) -> dict[str, Any]:
    snapshot, lock, application, _ = source
    return build_deepseek_v4_hc_pre_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _rehash_outer_artifact(output: Path, relative: str) -> None:
    payload = (output / relative).read_bytes()
    manifest_path = output / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    for record in manifest["artifacts"]:
        if record["path"] == relative:
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["size_bytes"] = len(payload)
            break
    else:  # pragma: no cover - test helper assertion
        raise AssertionError(f"artifact {relative!r} is absent")
    body = dict(manifest)
    body.pop("build_id")
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(manifest_path, manifest)


def _rehash_manifest(output: Path, manifest: dict[str, Any]) -> None:
    body = dict(manifest)
    body.pop("build_id", None)
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(output / "deployment_manifest.json", manifest)


def _assert_recursive_schema_closure(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        raw_type = value.get("type")
        if raw_type == "object" or (
            isinstance(raw_type, list) and "object" in raw_type
        ):
            assert value.get("additionalProperties") is False, path
        for key, child in value.items():
            _assert_recursive_schema_closure(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_recursive_schema_closure(child, f"{path}[{index}]")


def test_executable_package_is_deterministic_closed_and_independently_verified(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = _build(hc_pre_application, first)
    second_manifest = _build(hc_pre_application, second)
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)

    assert first_manifest["status"] == DEPLOYMENT_STATUS
    assert first_manifest["claim_boundary"] == CLAIM_BOUNDARY
    assert first_manifest["entrypoint"] == ENTRYPOINT
    assert len(first_manifest["artifacts"]) == 18
    assert [record["path"] for record in first_manifest["artifacts"]] == sorted(
        record["path"] for record in first_manifest["artifacts"]
    )
    assert {record["role"] for record in first_manifest["artifacts"]} == {
        "hc_base_parameter",
        "hc_projection_parameter",
        "hc_scale_parameter",
        "execution_coverage",
        "execution_request_schema",
        "execution_result_schema",
        "logical_schedule",
        "logical_schedule_certificate",
        "microcode_disassembly",
        "microcode_program",
        "parameter_counter_contract",
        "parameter_deployment_manifest",
        "parameter_numeric_profile",
        "parameter_operator_coverage",
        "parameter_roundtrip_report",
        "parameter_semantic_ir",
        "parameter_tensor_manifest",
        "program_contract",
    }
    assert set(_tree(first)) == {
        "deployment_manifest.json",
        *(record["path"] for record in first_manifest["artifacts"]),
    }

    program = (first / ENTRYPOINT["program"]).read_bytes()
    assert len(program) == 136
    assert hashlib.sha256(program).hexdigest() == PROGRAM_SHA256
    assert program == encode(assemble())
    assert (first / ENTRYPOINT["program_disassembly"]).read_text("ascii") == (
        disassemble(assemble())
    )
    assert load_strict_json(first / ENTRYPOINT["program_contract"]) == (
        build_program_contract()
    )
    assert first_manifest["program_contract_id"] == PROGRAM_CONTRACT_ID
    assert first_manifest["schedule_id"] == SCHEDULE_ID
    assert first_manifest["schedule_certificate_id"] == CERTIFICATE_ID

    parameter_integrity = verify_deepseek_v4_hc_pre_deployment(
        first / "parameters", hc_pre_application[2]
    )
    assert parameter_integrity["checked_artifact_count"] == 9
    integrity = verify_deepseek_v4_hc_pre_executable_deployment(
        first, hc_pre_application[2]
    )
    assert integrity["build_id"] == first_manifest["build_id"]
    assert integrity["checked_artifact_count"] == 18


def test_executable_package_contains_all_three_exact_f32_resources(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    tensors = load_strict_json(output / "parameters/tensor_manifest.json")
    expected = {
        "base": (BASE_NAME, 96),
        "projection": (PROJECTION_NAME, 1_572_864),
        "scale": (SCALE_NAME, 12),
    }
    for resource, (name, size) in expected.items():
        record = tensors[resource]
        assert record["name"] == name
        assert record["dtype"] == "F32"
        assert record["size_bytes"] == size
        payload = (output / "parameters" / record["path"]).read_bytes()
        assert len(payload) == size
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert payload == hc_pre_application[3][name]


def test_executable_schemas_are_draft_2020_strict_and_validate_package(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    schemas = sorted(SCHEMA_ROOT.glob("*.schema.json"))
    assert schemas
    by_identifier: dict[str, dict[str, Any]] = {}
    for schema_path in schemas:
        schema = json.loads(schema_path.read_text("utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        _assert_recursive_schema_closure(schema)
        by_identifier[schema["$id"]] = schema

    manifest = load_strict_json(output / "deployment_manifest.json")
    deployment_schemas = [
        schema
        for schema in by_identifier.values()
        if schema.get("properties", {}).get("schema", {}).get("const")
        == manifest["schema"]
    ]
    assert len(deployment_schemas) == 1
    Draft202012Validator(deployment_schemas[0]).validate(manifest)

    packaged_schema_files = {
        "execution_request_v1.schema.json": (
            output / "interfaces/execution_request_v1.schema.json"
        ),
        "execution_result_v1.schema.json": (
            output / "interfaces/execution_result_v1.schema.json"
        ),
    }
    for source_name, packaged_path in packaged_schema_files.items():
        source_schema = json.loads((SCHEMA_ROOT / source_name).read_text("utf-8"))
        packaged_schema = load_strict_json(packaged_path)
        assert packaged_schema == source_schema
        Draft202012Validator.check_schema(packaged_schema)
        _assert_recursive_schema_closure(packaged_schema)

    coverage = load_strict_json(output / "execution_coverage.json")
    coverage_schema = json.loads(
        (SCHEMA_ROOT / "execution_coverage_v1.schema.json").read_text("utf-8")
    )
    Draft202012Validator(coverage_schema).validate(coverage)
    assert coverage["program_execution_authority"] == "complete"
    assert coverage["execution_evidence"] == "none"


def test_packaged_result_contract_closes_all_outputs_diagnostics_and_counters(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    request_schema = load_strict_json(
        output / "interfaces/execution_request_v1.schema.json"
    )
    result_schema = load_strict_json(
        output / "interfaces/execution_result_v1.schema.json"
    )

    assert request_schema["properties"]["batch_size"] == {
        "maximum": 4,
        "minimum": 1,
        "type": "integer",
    }
    assert request_schema["properties"]["sequence_length"] == {
        "maximum": 4,
        "minimum": 1,
        "type": "integer",
    }
    assert request_schema["properties"]["token_count"] == {
        "maximum": 4,
        "minimum": 1,
        "type": "integer",
    }
    request_input = request_schema["$defs"]["inputDescriptor"]
    assert request_input["properties"]["path"] == {"const": "input/hc_hidden.bf16le"}
    assert request_input["properties"]["shape"]["prefixItems"] == [
        {"maximum": 4, "minimum": 1, "type": "integer"},
        {"maximum": 4, "minimum": 1, "type": "integer"},
        {"const": 4},
        {"const": 4096},
    ]

    assert len(result_schema["properties"]["outputs"]["prefixItems"]) == 5
    diagnostics = result_schema["$defs"]["diagnostics"]
    assert set(diagnostics["required"]) == {
        "mix_codes",
        "projection_codes",
        "rms_inverse_codes",
        "rms_mean_codes",
        "stable_softmax_codes",
    }
    counters = result_schema["$defs"]["logicalCounters"]
    assert len(counters["required"]) == 27
    assert set(counters["required"]) == set(counters["properties"])
    assert result_schema["$defs"]["numericStatus"] == {
        "additionalProperties": False,
        "properties": {
            "branch_saturation_count": {
                "maximum": 16_384,
                "minimum": 0,
                "type": "integer",
            },
            "poison": {"const": False},
        },
        "required": ["branch_saturation_count", "poison"],
        "type": "object",
    }
    assert result_schema["properties"]["counter_reconciliation"] == {"const": "exact"}


@pytest.mark.parametrize(
    ("relative", "mutate"),
    [
        (
            "program/hc_pre.bin",
            lambda payload: payload[:-1] + bytes([payload[-1] ^ 1]),
        ),
        (
            "program/hc_pre.disassembly.txt",
            lambda payload: payload.replace(b"HC_PRE", b"HC_POST", 1),
        ),
    ],
)
def test_checker_rejects_rehashed_program_or_disassembly_mutation(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    relative: str,
    mutate: Any,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    path = output / relative
    path.write_bytes(mutate(path.read_bytes()))
    _rehash_outer_artifact(output, relative)
    with pytest.raises(DeepSeekV4HCPreExecutableCheckError):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


@pytest.mark.parametrize(
    ("relative", "path", "replacement"),
    [
        (
            "program/program_contract.json",
            ("dimensions", "maximum_token_count"),
            True,
        ),
        ("schedule/logical_schedule.json", ("slots", 0, "slot"), False),
        (
            "schedule/logical_schedule_certificate.json",
            ("checks", "terminal_complete"),
            1,
        ),
        (
            "interfaces/execution_request_v1.schema.json",
            ("properties", "token_count", "maximum"),
            True,
        ),
        (
            "interfaces/execution_result_v1.schema.json",
            (
                "$defs",
                "logicalCounters",
                "properties",
                "hc_pre_input_bf16_values",
                "minimum",
            ),
            False,
        ),
        ("execution_coverage.json", ("site", "layer"), False),
    ],
)
def test_checker_rejects_type_aliases_inside_rehashed_contracts(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    relative: str,
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    artifact_path = output / relative
    value = load_strict_json(artifact_path)
    target: Any = value
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement
    write_canonical_json(artifact_path, value)
    _rehash_outer_artifact(output, relative)
    with pytest.raises(DeepSeekV4HCPreExecutableCheckError):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


def test_checker_rejects_rehashed_parameter_payload_mutation(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    manifest = _build(hc_pre_application, output)
    record = next(
        item for item in manifest["artifacts"] if item["role"] == "hc_scale_parameter"
    )
    path = output / record["path"]
    payload = bytearray(path.read_bytes())
    payload[0] ^= 1
    path.write_bytes(payload)
    _rehash_outer_artifact(output, record["path"])
    with pytest.raises(DeepSeekV4HCPreExecutableCheckError):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


def test_checker_rejects_rehashed_manifest_type_alias_and_unknown_entrypoint(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    manifest = load_strict_json(output / "deployment_manifest.json")
    manifest["site"]["layer"] = False
    _rehash_manifest(output, manifest)
    with pytest.raises(DeepSeekV4HCPreExecutableCheckError):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])

    manifest = load_strict_json(output / "deployment_manifest.json")
    manifest["site"]["layer"] = 0
    manifest["entrypoint"]["activation"] = "activation.bin"
    _rehash_manifest(output, manifest)
    with pytest.raises(DeepSeekV4HCPreExecutableCheckError):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_checker_rejects_nonregular_program_without_blocking(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    kind: str,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    program = output / "program/hc_pre.bin"
    program.unlink()
    if kind == "symlink":
        program.symlink_to(output / "parameters/tensor_manifest.json")
    else:
        os.mkfifo(program)
    with pytest.raises(
        DeepSeekV4HCPreExecutableCheckError,
        match="without following symlinks|not a regular file",
    ):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


def test_checker_rejects_oversized_manifest_before_json_decode(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    (output / "deployment_manifest.json").write_bytes(
        b"{" + b" " * (2 * 1024 * 1024) + b"}"
    )
    with pytest.raises(
        DeepSeekV4HCPreExecutableCheckError,
        match="bound|exceed|size",
    ):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])


def test_checker_rejects_identical_artifact_replacement_during_read(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    program_path = output / "program/hc_pre.bin"
    payload = program_path.read_bytes()
    original_pread = executable_checker_module.os.pread
    replaced = False

    def replacing_pread(descriptor: int, count: int, offset: int) -> bytes:
        nonlocal replaced
        result = original_pread(descriptor, count, offset)
        metadata = os.fstat(descriptor)
        if not replaced and offset == 0 and metadata.st_size == 136:
            replacement = program_path.with_suffix(".replacement")
            replacement.write_bytes(payload)
            os.replace(replacement, program_path)
            replaced = True
        return result

    monkeypatch.setattr(executable_checker_module.os, "pread", replacing_pread)
    with pytest.raises(
        DeepSeekV4HCPreExecutableCheckError,
        match="replaced|changed",
    ):
        verify_deepseek_v4_hc_pre_executable_deployment(output, hc_pre_application[2])
    assert replaced


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_builder_never_replaces_existing_output(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    kind: str,
) -> None:
    output = tmp_path / "existing"
    if kind == "directory":
        output.mkdir()
        (output / "peer-owned").write_bytes(b"preserve")
    elif kind == "file":
        output.write_bytes(b"preserve")
    else:
        target = tmp_path / "peer-owned"
        target.write_bytes(b"preserve")
        output.symlink_to(target)
    with pytest.raises(DeepSeekV4HCPreExecutableBuildError, match="already exists"):
        _build(hc_pre_application, output)
    if kind == "directory":
        assert (output / "peer-owned").read_bytes() == b"preserve"
    elif kind == "file":
        assert output.read_bytes() == b"preserve"
    else:
        assert output.is_symlink()
        assert output.resolve().read_bytes() == b"preserve"


def test_builder_publication_race_preserves_peer_and_cleans_private_tree(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "deployment"
    original_publish = executable_builder_module._publish_create_once

    def racing_publish(**kwargs: Any) -> None:
        output.mkdir()
        (output / "peer-owned").write_bytes(b"preserve")
        original_publish(**kwargs)

    monkeypatch.setattr(
        executable_builder_module,
        "_publish_create_once",
        racing_publish,
    )
    with pytest.raises(DeepSeekV4HCPreExecutableBuildError, match="already exists"):
        _build(hc_pre_application, output)
    assert (output / "peer-owned").read_bytes() == b"preserve"
    assert not list(tmp_path.glob(".hc-pre-executable.tmp-*"))


def test_builder_verifies_before_publication_and_cleans_failure(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "deployment"

    def reject(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise DeepSeekV4HCPreExecutableCheckError("injected independent rejection")

    monkeypatch.setattr(
        executable_builder_module,
        "verify_deepseek_v4_hc_pre_executable_deployment",
        reject,
    )
    with pytest.raises(
        DeepSeekV4HCPreExecutableBuildError,
        match="independent executable-package verification failed",
    ):
        _build(hc_pre_application, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".hc-pre-executable.tmp-*"))


def test_builder_rejects_insufficient_free_space_before_staging(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "deployment"
    observed = executable_builder_module.shutil.disk_usage(tmp_path)
    disk_usage_type = type(observed)
    monkeypatch.setattr(
        executable_builder_module.shutil,
        "disk_usage",
        lambda path: disk_usage_type(observed.total, observed.used, 0),
    )
    with pytest.raises(
        DeepSeekV4HCPreExecutableBuildError,
        match="free-space reserve",
    ):
        _build(hc_pre_application, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".hc-pre-executable.tmp-*"))


def test_generated_artifact_fsync_failure_prevents_publication(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "deployment"
    original_fsync = executable_builder_module.os.fsync
    calls = 0

    def failing_fsync(descriptor: int) -> None:
        nonlocal calls
        descriptor_path = os.readlink(f"/proc/self/fd/{descriptor}")
        if descriptor_path.endswith("/execution_coverage.json"):
            calls += 1
            raise OSError("injected fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(executable_builder_module.os, "fsync", failing_fsync)
    with pytest.raises(
        DeepSeekV4HCPreExecutableBuildError,
        match="cannot write generated artifact",
    ):
        _build(hc_pre_application, output)
    assert calls == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".hc-pre-executable.tmp-*"))


def test_executable_package_has_no_execution_inputs_results_or_ppa_claims(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    manifest = _build(hc_pre_application, output)
    assert manifest["status"] == "program_packaged_execution_not_yet_evidenced"
    assert (
        "Program packaged, execution not yet evidenced." in manifest["claim_boundary"]
    )
    forbidden_roles = {
        "activation",
        "expected_result",
        "execution_result",
        "callback",
        "fallback_arithmetic",
        "cycle_report",
        "ppa_report",
    }
    assert not forbidden_roles & {record["role"] for record in manifest["artifacts"]}
    assert set(manifest["entrypoint"]) == {
        "execution_coverage",
        "execution_request_schema",
        "execution_result_schema",
        "logical_schedule",
        "logical_schedule_certificate",
        "parameter_deployment",
        "program",
        "program_contract",
        "program_disassembly",
    }
