from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import shutil
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import compiler.checking.deepseek_v4_query_a_executable as checker_module
import compiler.vertical_slice.deepseek_v4_query_a_executable as builder_module
from compiler.checking.deepseek_v4_query_a_executable import (
    DeepSeekV4QueryAExecutableCheckError,
    verify_deepseek_v4_query_a_executable_deployment,
)
from compiler.ir.model import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.microcode.deepseek_v4_query_a import (
    assemble,
    build_program_contract,
    disassemble,
    encode,
)
from compiler.vertical_slice.deepseek_v4_query_a_executable import (
    CLAIM_BOUNDARY,
    DEPLOYMENT_SCHEMA,
    DEPLOYMENT_STATUS,
    ENTRYPOINT,
    EXECUTION_REQUEST_SCHEMA,
    EXECUTION_RESULT_SCHEMA,
    DeepSeekV4QueryAExecutableBuildError,
    build_deepseek_v4_query_a_executable_deployment,
)
from runtime.service_engine.query_a_numeric import query_a_functional_counters


PROGRAM_SHA256 = "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
PROGRAM_CONTRACT_ID = "0aa1969479c527d33fa893557f40dd05e3efbc9a3e1af7d959d4cb8496806903"
SCHEDULE_ID = "2673d8ef4e62df0ec1441c1b14eeb6a207b246a70a987adadfe354a418711e13"
CERTIFICATE_ID = "d2a6e754abc7440dc341e00fac4bf7e48f9e53659f971fdfbb03c4782c47b546"
OFFICIAL_RESOURCE_HASHES = {
    "attention_norm_weight": (
        "2628db36b6aa28c06121bb01f2d8e0f6acf9d240393af7a91ae5073b0acb5772"
    ),
    "query_a_weight": (
        "d8646783efb3c0bda83bcd2c64b03cb25d1677d27b0c45ffe143a4175922932c"
    ),
    "query_a_scale": (
        "aea19c77d256ca30999de59a811b152a2dfc82673a43877d9cd67b80578bc5e2"
    ),
    "exhaustive_output_rows": (
        "c89db7222126863309183fc023c7091fb18392d16a397dac76a96a022cd62cef"
    ),
}


def _official_source() -> tuple[Path, dict[str, Any], Path]:
    evidence = Path(
        os.environ.get(
            "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT",
            str(Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"),
        )
    )
    snapshot = Path(
        os.environ.get(
            "OPENTALLAS_DEEPSEEK_V4_SNAPSHOT",
            str(
                Path.home()
                / ".cache/huggingface/hub"
                / "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots"
                / "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
            ),
        )
    )
    lock_path = evidence / "checkpoint.lock.json"
    application = evidence / "query-a-canonical-v2"
    if not (
        snapshot.is_dir()
        and lock_path.is_file()
        and (application / "canonical_application.json").is_file()
        and (application / "canonical_verification.json").is_file()
    ):
        pytest.skip("pinned official Query-A canonical evidence is not available")
    lock = load_strict_json(lock_path)
    return snapshot, lock, application


@pytest.fixture(scope="module")
def official_source() -> tuple[Path, dict[str, Any], Path]:
    return _official_source()


@pytest.fixture(scope="module")
def official_package(
    tmp_path_factory: pytest.TempPathFactory,
    official_source: tuple[Path, dict[str, Any], Path],
) -> tuple[Path, dict[str, Any]]:
    snapshot, lock, application = official_source
    output = tmp_path_factory.mktemp("query-a-package") / "deployment"
    manifest = build_deepseek_v4_query_a_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
    )
    return output, manifest


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _copy_package(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def _rehash_outer_artifact(output: Path, relative: str) -> None:
    payload = (output / relative).read_bytes()
    manifest = load_strict_json(output / "deployment_manifest.json")
    for record in manifest["artifacts"]:
        if record["path"] == relative:
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["size_bytes"] = len(payload)
            break
    else:  # pragma: no cover - helper invariant
        raise AssertionError(f"artifact {relative!r} is absent")
    _rehash_manifest(output, manifest)


def _rehash_manifest(output: Path, manifest: dict[str, Any]) -> None:
    body = dict(manifest)
    body.pop("build_id", None)
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(output / "deployment_manifest.json", manifest)


def _verify(
    output: Path,
    source: tuple[Path, dict[str, Any], Path],
) -> dict[str, Any]:
    snapshot, lock, application = source
    return verify_deepseek_v4_query_a_executable_deployment(
        output, application, snapshot, lock
    )


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


def test_official_package_is_deterministic_closed_and_independently_verified(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    first, first_manifest = official_package
    snapshot, lock, application = official_source
    second = tmp_path / "second"
    second_manifest = build_deepseek_v4_query_a_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
    )
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["schema"] == DEPLOYMENT_SCHEMA
    assert first_manifest["status"] == DEPLOYMENT_STATUS
    assert first_manifest["claim_boundary"] == CLAIM_BOUNDARY
    assert first_manifest["entrypoint"] == ENTRYPOINT
    assert len(first_manifest["artifacts"]) == 14
    assert [record["path"] for record in first_manifest["artifacts"]] == sorted(
        record["path"] for record in first_manifest["artifacts"]
    )
    assert set(_tree(first)) == {
        "deployment_manifest.json",
        *(record["path"] for record in first_manifest["artifacts"]),
    }
    report = _verify(first, official_source)
    assert report["build_id"] == first_manifest["build_id"]
    assert report["checked_artifact_count"] == 14
    assert report["checked_rank_replica_count"] == 12
    assert report["status"] == "package_identity_verified_execution_not_evidenced"


def test_package_binds_exact_program_schedule_contract_and_disassembly(
    official_package: tuple[Path, dict[str, Any]],
) -> None:
    output, manifest = official_package
    program = (output / ENTRYPOINT["program"]).read_bytes()
    assert len(program) == 196
    assert hashlib.sha256(program).hexdigest() == PROGRAM_SHA256
    assert program == encode(assemble())
    assert (output / ENTRYPOINT["program_disassembly"]).read_text("ascii") == (
        disassemble(assemble())
    )
    assert load_strict_json(output / ENTRYPOINT["program_contract"]) == (
        build_program_contract()
    )
    assert manifest["program_contract_id"] == PROGRAM_CONTRACT_ID
    assert manifest["schedule_id"] == SCHEDULE_ID
    assert manifest["schedule_certificate_id"] == CERTIFICATE_ID


def test_package_binds_three_official_resources_four_replicas_and_generated_rows(
    official_package: tuple[Path, dict[str, Any]],
) -> None:
    output, manifest = official_package
    by_role = {record["role"]: record for record in manifest["artifacts"]}
    for role, digest in OFFICIAL_RESOURCE_HASHES.items():
        assert by_role[role]["sha256"] == digest
        payload = (output / by_role[role]["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest
    rows = (output / "resources/query_a_exhaustive_rows.u32le").read_bytes()
    assert struct.unpack("<1024I", rows) == tuple(range(1024))

    resources = load_strict_json(output / ENTRYPOINT["resource_manifest"])
    assert resources["source_application_id"] == manifest["source"]["application_id"]
    assert resources["source_verification_id"] == manifest["source"]["verification_id"]
    assert [record["resource_id"] for record in resources["resources"]] == [
        7,
        8,
        9,
        10,
    ]
    for record in resources["resources"][:3]:
        assert record["checkpoint_derived"] is True
        assert record["replicated_ranks"] == [0, 1, 2, 3]
        assert len(record["source_assignment_paths"]) == 4
    assert resources["resources"][3]["checkpoint_derived"] is False
    assert resources["resources"][3]["generator"] == {
        "kind": "contiguous_u32_range",
        "start_inclusive": 0,
        "stop_exclusive": 1024,
    }


def test_packaged_request_and_result_schemas_freeze_runtime_interfaces(
    official_package: tuple[Path, dict[str, Any]],
) -> None:
    output, manifest = official_package
    request = load_strict_json(output / ENTRYPOINT["execution_request_schema"])
    result = load_strict_json(output / ENTRYPOINT["execution_result_schema"])
    for schema in (request, result):
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        _assert_recursive_schema_closure(schema)

    assert request["properties"]["schema"] == {"const": EXECUTION_REQUEST_SCHEMA}
    assert set(request["required"]) == {
        "build_id",
        "input",
        "model_id",
        "program_sha256",
        "provenance",
        "schema",
        "token_count",
    }
    input_descriptor = request["$defs"]["inputDescriptor"]
    assert input_descriptor["properties"]["path"] == {
        "const": "input/attention_input.bf16le"
    }
    assert input_descriptor["properties"]["shape"]["prefixItems"] == [
        {"maximum": 4, "minimum": 1, "type": "integer"},
        {"const": 4096},
    ]
    provenance = request["$defs"]["provenance"]
    assert set(provenance["required"]) == {
        "kind",
        "source_batch_size",
        "source_build_id",
        "source_output_path",
        "source_output_sha256",
        "source_request_sha256",
        "source_result_manifest_sha256",
        "source_schema",
        "source_sequence_length",
    }
    assert provenance["properties"]["source_output_path"] == {
        "const": "outputs/attention_input.bf16le"
    }

    digest = "0" * 64
    example_request = {
        "build_id": manifest["build_id"],
        "input": {
            "dtype": "BF16",
            "encoding": "bfloat16_little_endian",
            "id": "attention_input",
            "path": "input/attention_input.bf16le",
            "register": "ATTENTION_INPUT",
            "sha256": digest,
            "shape": [1, 4096],
            "size_bytes": 8192,
        },
        "model_id": "deepseek-v4-flash-0731",
        "program_sha256": PROGRAM_SHA256,
        "provenance": {
            "kind": "verified_hc_pre_execution_result",
            "source_batch_size": 1,
            "source_build_id": digest,
            "source_output_path": "outputs/attention_input.bf16le",
            "source_output_sha256": digest,
            "source_request_sha256": digest,
            "source_result_manifest_sha256": digest,
            "source_schema": "opentallas.deepseek_v4_hc_pre_execution_result.v1",
            "source_sequence_length": 1,
        },
        "schema": EXECUTION_REQUEST_SCHEMA,
        "token_count": 1,
    }
    Draft202012Validator(request).validate(example_request)

    assert result["properties"]["schema"] == {"const": EXECUTION_RESULT_SCHEMA}
    assert len(result["properties"]["outputs"]["prefixItems"]) == 2
    assert result["$defs"]["meanSquare"]["properties"]["shape"] == {
        "items": False,
        "maxItems": 1,
        "minItems": 1,
        "prefixItems": [{"maximum": 4, "minimum": 1, "type": "integer"}],
        "type": "array",
    }
    assert (
        result["$defs"]["inverseRms"]["properties"]["shape"]
        == result["$defs"]["meanSquare"]["properties"]["shape"]
    )
    assert set(result["$defs"]["logicalCounters"]["required"]) == set(
        query_a_functional_counters(1)
    )
    assert result["$defs"]["numericStatus"]["properties"]["poison"] == {"const": False}


def test_functional_counter_contract_exactly_matches_service_function(
    official_package: tuple[Path, dict[str, Any]],
) -> None:
    output, manifest = official_package
    contract = load_strict_json(output / ENTRYPOINT["functional_counter_contract"])
    body = dict(contract)
    contract_id = body.pop("contract_id")
    assert contract_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert contract_id == manifest["functional_counter_contract_id"]
    fixed = contract["fixed_counters"]
    coefficients = contract["per_token_coefficients"]
    for token_count in range(1, 5):
        expected = {
            name: coefficient * token_count
            for name, coefficient in coefficients.items()
        }
        expected.update(fixed)
        assert query_a_functional_counters(token_count) == dict(
            sorted(expected.items())
        )


@pytest.mark.parametrize(
    ("relative", "mutator"),
    [
        ("program/query_a.bin", lambda value: value[:-1] + bytes([value[-1] ^ 1])),
        (
            "program/query_a.disassembly.txt",
            lambda value: value.replace(b"RMS_NORM", b"BAD_NORM", 1),
        ),
        (
            "resources/query_a_exhaustive_rows.u32le",
            lambda value: struct.pack("<I", 1) + value[4:],
        ),
        (
            "resources/query_a_scale.e8m0",
            lambda value: bytes([value[0] ^ 1]) + value[1:],
        ),
    ],
)
def test_checker_rejects_rehashed_byte_tampering(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    relative: str,
    mutator: Any,
) -> None:
    output = _copy_package(official_package[0], tmp_path / "tampered")
    path = output / relative
    path.write_bytes(mutator(path.read_bytes()))
    _rehash_outer_artifact(output, relative)
    with pytest.raises(DeepSeekV4QueryAExecutableCheckError):
        _verify(output, official_source)


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
            ("checks", "wire_program_decode"),
            1,
        ),
        (
            "resources/resource_manifest.json",
            ("resources", 0, "checkpoint_derived"),
            1,
        ),
        (
            "interfaces/execution_request_v1.schema.json",
            ("properties", "token_count", "maximum"),
            True,
        ),
        (
            "interfaces/execution_result_v1.schema.json",
            ("$defs", "logicalCounters", "properties", "complete_events", "minimum"),
            False,
        ),
        (
            "interfaces/functional_counter_contract.json",
            ("fixed_counters", "complete_events"),
            True,
        ),
        ("execution_coverage.json", ("site", "layer"), False),
    ],
)
def test_checker_rejects_nested_type_aliases_after_rehash(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    relative: str,
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    output = _copy_package(official_package[0], tmp_path / "type-alias")
    artifact = output / relative
    value = load_strict_json(artifact)
    target: Any = value
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement
    write_canonical_json(artifact, value)
    _rehash_outer_artifact(output, relative)
    with pytest.raises(DeepSeekV4QueryAExecutableCheckError):
        _verify(output, official_source)


def test_checker_rejects_rehashed_manifest_alias_unknown_path_and_extra_file(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    output = _copy_package(official_package[0], tmp_path / "manifest-alias")
    manifest = load_strict_json(output / "deployment_manifest.json")
    manifest["site"]["layer"] = False
    _rehash_manifest(output, manifest)
    with pytest.raises(DeepSeekV4QueryAExecutableCheckError):
        _verify(output, official_source)

    output = _copy_package(official_package[0], tmp_path / "manifest-entrypoint")
    manifest = load_strict_json(output / "deployment_manifest.json")
    manifest["entrypoint"]["activation"] = "activation.bin"
    _rehash_manifest(output, manifest)
    with pytest.raises(DeepSeekV4QueryAExecutableCheckError):
        _verify(output, official_source)

    output = _copy_package(official_package[0], tmp_path / "extra-file")
    (output / "unexpected.bin").write_bytes(b"x")
    with pytest.raises(DeepSeekV4QueryAExecutableCheckError, match="unlisted"):
        _verify(output, official_source)


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_checker_rejects_nonregular_program_without_blocking(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    kind: str,
) -> None:
    output = _copy_package(official_package[0], tmp_path / kind)
    program = output / "program/query_a.bin"
    program.unlink()
    if kind == "symlink":
        program.symlink_to(output / "resources/resource_manifest.json")
    else:
        os.mkfifo(program)
    with pytest.raises(
        DeepSeekV4QueryAExecutableCheckError,
        match="without following symlinks|not a regular file",
    ):
        _verify(output, official_source)


def test_checker_rejects_oversized_manifest_before_json_decode(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    output = _copy_package(official_package[0], tmp_path / "oversized")
    with (output / "deployment_manifest.json").open("wb") as handle:
        handle.write(b"{")
        handle.truncate(2 * 1024 * 1024)
    with pytest.raises(
        DeepSeekV4QueryAExecutableCheckError,
        match="bound|exceed|bytes",
    ):
        _verify(output, official_source)


def test_checker_rejects_identical_program_replacement_during_read(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _copy_package(official_package[0], tmp_path / "replacement-race")
    program = output / "program/query_a.bin"
    payload = program.read_bytes()
    original_pread = checker_module.os.pread
    replaced = False

    def replacing_pread(descriptor: int, count: int, offset: int) -> bytes:
        nonlocal replaced
        result = original_pread(descriptor, count, offset)
        metadata = os.fstat(descriptor)
        if not replaced and offset == 0 and metadata.st_size == 196:
            replacement = program.with_suffix(".replacement")
            replacement.write_bytes(payload)
            os.replace(replacement, program)
            replaced = True
        return result

    monkeypatch.setattr(checker_module.os, "pread", replacing_pread)
    with pytest.raises(
        DeepSeekV4QueryAExecutableCheckError,
        match="replaced|changed",
    ):
        _verify(output, official_source)
    assert replaced


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_builder_never_replaces_existing_output(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    kind: str,
) -> None:
    snapshot, lock, application = official_source
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
    with pytest.raises(DeepSeekV4QueryAExecutableBuildError, match="already exists"):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
        )
    if kind == "directory":
        assert (output / "peer-owned").read_bytes() == b"preserve"
    elif kind == "file":
        assert output.read_bytes() == b"preserve"
    else:
        assert output.is_symlink()
        assert output.resolve().read_bytes() == b"preserve"


def test_builder_publication_race_preserves_peer_and_cleans_private_tree(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, application = official_source
    output = tmp_path / "deployment"
    original_publish = builder_module._publish_create_once

    def racing_publish(**kwargs: Any) -> None:
        output.mkdir()
        (output / "peer-owned").write_bytes(b"preserve")
        original_publish(**kwargs)

    monkeypatch.setattr(builder_module, "_publish_create_once", racing_publish)
    with pytest.raises(DeepSeekV4QueryAExecutableBuildError, match="already exists"):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
        )
    assert (output / "peer-owned").read_bytes() == b"preserve"
    assert not list(tmp_path.glob(".query-a-executable.tmp-*"))


def test_builder_verifies_before_publication_and_cleans_failure(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, application = official_source
    output = tmp_path / "deployment"

    def reject(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise DeepSeekV4QueryAExecutableCheckError("injected rejection")

    monkeypatch.setattr(
        builder_module,
        "verify_deepseek_v4_query_a_executable_deployment",
        reject,
    )
    with pytest.raises(
        DeepSeekV4QueryAExecutableBuildError,
        match="independent Query-A package verification failed",
    ):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".query-a-executable.tmp-*"))


def test_builder_rejects_insufficient_free_space_before_staging(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, application = official_source
    output = tmp_path / "deployment"
    observed = builder_module.shutil.disk_usage(tmp_path)
    usage_type = type(observed)
    monkeypatch.setattr(
        builder_module.shutil,
        "disk_usage",
        lambda path: usage_type(observed.total, observed.used, 0),
    )
    with pytest.raises(DeepSeekV4QueryAExecutableBuildError, match="free-space"):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
        )
    assert not output.exists()


def test_builder_rejects_mutated_canonical_selection_and_cleans_failure(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    snapshot, lock, application = official_source
    copied_application = tmp_path / "canonical"
    shutil.copytree(application, copied_application)
    manifest_path = copied_application / "canonical_application.json"
    manifest = load_strict_json(manifest_path)
    manifest["selection"]["requested_input_names"].pop()
    body = dict(manifest)
    body.pop("application_id")
    manifest["application_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(manifest_path, manifest)
    output = tmp_path / "deployment"
    with pytest.raises(
        DeepSeekV4QueryAExecutableBuildError,
        match="replay|selection|three tensors",
    ):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=copied_application,
            output=output,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".query-a-executable.tmp-*"))


def test_checker_replays_every_canonical_replica_and_rejects_wrong_lock(
    official_package: tuple[Path, dict[str, Any]],
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    snapshot, lock, application = official_source
    copied_application = tmp_path / "canonical"
    shutil.copytree(application, copied_application)
    replica = copied_application / "ranks/rank-003/layers.0.attn.wq_a.scale.bin"
    payload = bytearray(replica.read_bytes())
    payload[0] ^= 1
    replica.write_bytes(payload)
    with pytest.raises(
        DeepSeekV4QueryAExecutableCheckError,
        match="replay|canonical resource|differs",
    ):
        verify_deepseek_v4_query_a_executable_deployment(
            official_package[0], copied_application, snapshot, lock
        )

    wrong_lock = copy.deepcopy(lock)
    wrong_lock["lock_id"] = "0" * 64
    with pytest.raises(
        DeepSeekV4QueryAExecutableCheckError,
        match="pinned official release",
    ):
        verify_deepseek_v4_query_a_executable_deployment(
            official_package[0], application, snapshot, wrong_lock
        )


def test_generated_artifact_fsync_failure_prevents_publication(
    official_source: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, application = official_source
    output = tmp_path / "deployment"
    original_fsync = builder_module.os.fsync
    calls = 0

    def failing_fsync(descriptor: int) -> None:
        nonlocal calls
        descriptor_path = os.readlink(f"/proc/self/fd/{descriptor}")
        if descriptor_path.endswith("/execution_coverage.json"):
            calls += 1
            raise OSError("injected fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(builder_module.os, "fsync", failing_fsync)
    with pytest.raises(
        DeepSeekV4QueryAExecutableBuildError,
        match="cannot write generated artifact",
    ):
        build_deepseek_v4_query_a_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
        )
    assert calls == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".query-a-executable.tmp-*"))


@pytest.mark.parametrize(
    ("dtype", "payload", "match"),
    [
        ("BF16", struct.pack("<H", 0x7F80), "non-finite BF16"),
        ("F8_E4M3", b"\x7f", "reserved FP8"),
        ("F8_E8M0", b"\xff", "reserved E8M0"),
    ],
)
def test_builder_and_checker_encoding_validators_fail_closed(
    tmp_path: Path,
    dtype: str,
    payload: bytes,
    match: str,
) -> None:
    path = tmp_path / "bad.bin"
    path.write_bytes(payload)
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        with pytest.raises(DeepSeekV4QueryAExecutableBuildError, match=match):
            builder_module._validate_encoding(
                descriptor, len(payload), dtype, "bad resource"
            )
        stable = checker_module._StableFile(
            descriptor=descriptor,
            fingerprint=checker_module._fingerprint(os.fstat(descriptor)),
            relative_path="bad.bin",
            root_descriptor=os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY),
            size_bytes=len(payload),
        )
        try:
            with pytest.raises(DeepSeekV4QueryAExecutableCheckError, match=match):
                checker_module._validate_encoding(stable, dtype, "bad resource")
        finally:
            os.close(stable.root_descriptor)
    finally:
        os.close(descriptor)


def test_package_contains_no_inputs_expected_outputs_or_physical_claims(
    official_package: tuple[Path, dict[str, Any]],
) -> None:
    output, manifest = official_package
    forbidden_roles = {
        "activation",
        "expected_output",
        "execution_result",
        "callback",
        "fallback_arithmetic",
        "cycle_report",
        "ppa_report",
    }
    assert not forbidden_roles & {record["role"] for record in manifest["artifacts"]}
    assert not (output / "request_manifest.json").exists()
    assert not (output / "result_manifest.json").exists()
    serialized = canonical_json_bytes(manifest).lower()
    assert b"execution not evidenced" in serialized
    assert b"not cycles" in serialized
    assert b"nvidia" in serialized
    assert b"expected output" in serialized
