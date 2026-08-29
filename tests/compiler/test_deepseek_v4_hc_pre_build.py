from __future__ import annotations

import copy
from contextlib import ExitStack
import hashlib
import json
import mmap
import os
from pathlib import Path
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import compiler.checking.deepseek_v4_hc_pre_slice as hc_checker_module
import compiler.vertical_slice.deepseek_v4_hc_pre as hc_build_module
from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_hc_pre_slice import (
    DeepSeekV4HCPreCheckError,
    verify_deepseek_v4_hc_pre_deployment,
    verify_deepseek_v4_hc_pre_roundtrip,
)
from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    BASE_NAME,
    PROJECTION_NAME,
    SCALE_NAME,
    DeepSeekV4HCPreBuildError,
    build_deepseek_v4_hc_pre_deployment,
)


FIXTURE_REVISION = "abcdef0123456789abcdef0123456789abcdef01"
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/compiler/deepseek_v4_hc_pre"
SHAPES = {
    BASE_NAME: [24],
    PROJECTION_NAME: [24, 16384],
    SCALE_NAME: [3],
}
SCHEMA_TO_FILE = {
    "opentallas.deepseek_v4_hc_pre_counter_contract.v1": (
        "counter_contract.json",
        "counter_contract_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_deployment.v1": (
        "deployment_manifest.json",
        "deployment_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_numeric_profile.v1": (
        "numeric_profile.json",
        "numeric_profile_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_coverage.v1": (
        "operator_coverage.json",
        "operator_coverage_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_roundtrip.v1": (
        "roundtrip_report.json",
        "roundtrip_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_semantic.v1": (
        "model.ir.json",
        "semantic_v1.schema.json",
    ),
    "opentallas.deepseek_v4_hc_pre_tensors.v1": (
        "tensor_manifest.json",
        "tensor_manifest_v1.schema.json",
    ),
}


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
        header, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    raw_header += b" " * (-len(raw_header) % 8)
    return struct.pack("<Q", len(raw_header)) + raw_header + bytes(payload)


def _finite_payload(element_count: int, seed: int) -> bytes:
    patterns = (
        (0x00000000, 0x80000000, 0x00000001, 0x3F000000),
        (0x3F800000, 0xBF400000, 0x3EAAAAAB, 0x00800000),
        (0x40000000, 0x3DCCCCCD, 0xC0000000, 0x007FFFFF),
    )
    pattern = patterns[seed % len(patterns)]
    packed = struct.pack("<4I", *pattern)
    return (packed * ((element_count + 3) // 4))[: element_count * 4]


def _output(
    name: str,
    *,
    rank: int,
    shape: list[int],
    storage_dtype: str = "F32",
    logical_dtype: str = "FP32",
) -> dict[str, Any]:
    item_bytes = {"BF16": 2, "F32": 4}[storage_dtype]
    elements = 1
    for extent in shape:
        elements *= extent
    return {
        "logical_dtype": logical_dtype,
        "name": name,
        "payload_bytes": elements * item_bytes,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": shape,
        "source_slice": None,
        "storage_dtype": storage_dtype,
        "transform": "identity",
    }


def _plan(
    *,
    names: dict[str, str] | None = None,
    shapes: dict[str, list[int]] | None = None,
    dtypes: dict[str, tuple[str, str]] | None = None,
    rank_count: int = 4,
) -> list[dict[str, Any]]:
    names = names or {}
    shapes = shapes or {}
    dtypes = dtypes or {}
    records: list[dict[str, Any]] = []
    roles = {
        BASE_NAME: "hyper_connection.attn.base",
        PROJECTION_NAME: "hyper_connection.attn.projection",
        SCALE_NAME: "hyper_connection.attn.scale",
    }
    for original_name in (BASE_NAME, PROJECTION_NAME, SCALE_NAME):
        name = names.get(original_name, original_name)
        shape = shapes.get(original_name, SHAPES[original_name])
        storage_dtype, logical_dtype = dtypes.get(original_name, ("F32", "FP32"))
        item_bytes = {"BF16": 2, "F32": 4}[storage_dtype]
        elements = 1
        for extent in shape:
            elements *= extent
        records.append(
            {
                "action": "replicate_identity",
                "logical_dtype": logical_dtype,
                "name": name,
                "outputs": [
                    _output(
                        name,
                        rank=rank,
                        shape=shape,
                        storage_dtype=storage_dtype,
                        logical_dtype=logical_dtype,
                    )
                    for rank in range(rank_count)
                ],
                "semantic_role": roles[original_name],
                "shape": shape,
                "size_bytes": elements * item_bytes,
                "storage_dtype": storage_dtype,
            }
        )
    return records


def _materialize_application(
    root: Path,
    *,
    plan: list[dict[str, Any]] | None = None,
    payload_overrides: dict[str, bytes] | None = None,
) -> tuple[Path, dict[str, Any], Path, dict[str, bytes]]:
    plan = plan or _plan()
    payload_overrides = payload_overrides or {}
    root.mkdir(parents=True, exist_ok=True)
    snapshot = root / "snapshot"
    snapshot.mkdir()
    tensors: list[tuple[str, str, list[int], bytes]] = []
    payloads_by_name: dict[str, bytes] = {}
    for index, record in enumerate(plan):
        name = record["name"]
        shape = record["shape"]
        item_bytes = {"BF16": 2, "F32": 4}[record["storage_dtype"]]
        elements = record["size_bytes"] // item_bytes
        payload = payload_overrides.get(name)
        if payload is None:
            if record["storage_dtype"] == "F32":
                payload = _finite_payload(elements, index)
            else:
                payload = struct.pack("<H", 0x3F80) * elements
        if len(payload) != record["size_bytes"]:
            raise ValueError(f"payload override for {name!r} has the wrong size")
        payloads_by_name[name] = payload
        tensors.append((name, record["storage_dtype"], shape, payload))

    shard = _safetensors(tensors)
    config = canonical_json_bytes({"architectures": ["HCPreFixture"]})
    index = canonical_json_bytes(
        {
            "metadata": {"total_size": sum(len(item[3]) for item in tensors)},
            "weight_map": {name: "model.safetensors" for name, _, _, _ in tensors},
        }
    )
    checkpoint_files = {
        "config.json": config,
        "model.safetensors": shard,
        "model.safetensors.index.json": index,
    }
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


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _assert_recursive_object_schema_strict(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        raw_type = value.get("type")
        object_typed = raw_type == "object" or (
            isinstance(raw_type, list) and "object" in raw_type
        )
        if object_typed:
            assert value.get("additionalProperties") is False, (
                f"object schema at {path} is not closed"
            )
        for key, child in value.items():
            _assert_recursive_object_schema_strict(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_recursive_object_schema_strict(child, f"{path}[{index}]")


def _build(
    source: tuple[Path, dict[str, Any], Path, dict[str, bytes]], output: Path
) -> dict[str, Any]:
    snapshot, lock, application, _ = source
    return build_deepseek_v4_hc_pre_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
    )


def _rehash_canonical_evidence(
    application: dict[str, Any], verification: dict[str, Any]
) -> None:
    application_body = dict(application)
    application_body.pop("application_id")
    application["application_id"] = hashlib.sha256(
        canonical_json_bytes(application_body)
    ).hexdigest()
    verification["application_id"] = application["application_id"]
    verification_body = dict(verification)
    verification_body.pop("verification_id")
    verification["verification_id"] = hashlib.sha256(
        canonical_json_bytes(verification_body)
    ).hexdigest()


def _rehash_deployment_artifact(output: Path, artifact_name: str) -> None:
    artifact_path = output / artifact_name
    payload = artifact_path.read_bytes()
    manifest_path = output / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    for artifact in manifest["artifacts"]:
        if artifact["path"] == artifact_name:
            artifact["sha256"] = hashlib.sha256(payload).hexdigest()
            artifact["size_bytes"] = len(payload)
            break
    else:
        raise AssertionError(f"deployment does not list {artifact_name!r}")
    identity = {
        key: manifest[key]
        for key in (
            "artifacts",
            "compiler",
            "model_id",
            "numeric_profile_id",
            "site",
            "source",
        )
    }
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    manifest_path.write_bytes(canonical_json_bytes(manifest))


def test_hc_pre_build_is_deterministic_content_addressed_and_memory_mappable(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, payloads = hc_pre_application
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = _build(hc_pre_application, first)

    for path in application.rglob("*.bin"):
        os.utime(path, (1_700_000_000, 1_700_000_000))
    second_manifest = build_deepseek_v4_hc_pre_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
    )
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["status"] == (
        "development_fixture_complete_hc_pre_parameters_not_release_evidence"
    )
    canonical = load_strict_json(application / "canonical_application.json")
    retained = load_strict_json(application / "canonical_verification.json")
    assert first_manifest["source"] == {
        "application_id": canonical["application_id"],
        "application_status": canonical["status"],
        "checkpoint_lock_id": lock["lock_id"],
        "evidence_scope": "development_fixture",
        "repository": lock["source"]["repository"],
        "revision": lock["source"]["revision"],
        "verification_id": retained["verification_id"],
    }
    assert len(first_manifest["artifacts"]) == 9
    assert not any(
        str(tmp_path) in payload.decode("ascii", errors="ignore")
        for payload in _tree(first).values()
    )

    tensors = load_strict_json(first / "tensor_manifest.json")
    for resource, name in (
        ("base", BASE_NAME),
        ("projection", PROJECTION_NAME),
        ("scale", SCALE_NAME),
    ):
        record = tensors[resource]
        digest = hashlib.sha256(payloads[name]).hexdigest()
        assert record["path"] == f"payloads/sha256/{digest}.f32le"
        assert record["content_address"] == f"sha256:{digest}"
        assert record["replicated_ranks"] == [0, 1, 2, 3]
        path = first / record["path"]
        with (
            path.open("rb") as handle,
            mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped,
        ):
            assert mapped[:] == payloads[name]

    assert verify_deepseek_v4_hc_pre_roundtrip(first, application) == (
        load_strict_json(first / "roundtrip_report.json")
    )
    integrity = verify_deepseek_v4_hc_pre_deployment(first, application)
    assert integrity["build_id"] == first_manifest["build_id"]
    assert integrity["checked_artifact_count"] == 9


def test_hc_pre_package_freezes_numeric_profile_counters_and_claim_boundaries(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    manifest = _build(hc_pre_application, output)
    profile = load_strict_json(output / "numeric_profile.json")
    counters = load_strict_json(output / "counter_contract.json")
    coverage = load_strict_json(output / "operator_coverage.json")

    assert profile["specification"] == {
        "document": "SPEC-NUM",
        "requirement": "NUM-6.10",
        "version": "1.1",
    }
    assert profile["dimensions"] == {
        "combination_destinations": 4,
        "combination_sources": 4,
        "flattened_width": 16384,
        "hc_multiplier": 4,
        "hidden_size": 4096,
        "mix_fields": 24,
        "post_fields": 4,
        "pre_fields": 4,
        "sinkhorn_iterations": 20,
    }
    assert profile["constants"] == {
        "hc_epsilon_binary32": 0x358637BD,
        "norm_epsilon_binary32": 0x358637BD,
    }
    coefficients = counters["per_successfully_committed_token"]
    assert len(coefficients) == 26
    assert coefficients["hc_pre_projection_product_accumulates"] == 393216
    assert coefficients["hc_pre_sinkhorn_row_stages"] == 20
    assert coefficients["hc_pre_sinkhorn_column_stages"] == 20
    assert coefficients["hc_pre_sinkhorn_divides"] == 640
    assert coefficients["hc_pre_residual_bf16_values_preserved"] == 16384
    assert counters["data_dependent"]["hc_pre_branch_bf16_saturations"] == {
        "maximum_per_token": 4096,
        "minimum_per_token": 0,
    }
    assert coverage["execution_coverage"] == "none"
    assert "microcode" not in manifest["entrypoint"]
    assert all("Executes" not in claim for claim in manifest["claim_boundary"])
    assert any(
        "caller-trusted output parent" in claim for claim in manifest["claim_boundary"]
    )


def test_hc_pre_emitted_json_validates_and_every_object_schema_is_closed(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    for _, (artifact_name, schema_name) in SCHEMA_TO_FILE.items():
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        _assert_recursive_object_schema_strict(schema)
        artifact = load_strict_json(output / artifact_name)
        assert artifact["schema"] in SCHEMA_TO_FILE
        Draft202012Validator(schema).validate(artifact)


def test_hc_pre_source_schemas_bind_scope_status_and_frozen_source_hashes(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)

    for artifact_name, schema_name in (
        ("deployment_manifest.json", "deployment_v1.schema.json"),
        ("model.ir.json", "semantic_v1.schema.json"),
    ):
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        development = load_strict_json(output / artifact_name)

        wrong_development_status = copy.deepcopy(development)
        wrong_development_status["source"]["application_status"] = (
            "partial_official_transform_application_not_release_evidence"
        )
        assert list(validator.iter_errors(wrong_development_status))

        incomplete_official = copy.deepcopy(development)
        incomplete_official["source"]["evidence_scope"] = "official_checkpoint"
        assert list(validator.iter_errors(incomplete_official))

        official = copy.deepcopy(development)
        official["source"].update(
            {
                "application_status": (
                    "partial_official_transform_application_not_release_evidence"
                ),
                "evidence_scope": "official_checkpoint",
                "repository": "deepseek-ai/DeepSeek-V4-Flash-0731",
                "revision": "7872f01b1d1fe23eabc4c98b48bffcef5a386062",
            }
        )
        if artifact_name == "deployment_manifest.json":
            official["status"] = (
                "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
            )
        validator.validate(official)

    profile = load_strict_json(output / "numeric_profile.json")
    profile["source_boundary"]["model_source_sha256"] = "0" * 64
    profile_schema = json.loads(
        (SCHEMA_ROOT / "numeric_profile_v1.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(profile_schema).iter_errors(profile))


@pytest.mark.parametrize(
    ("artifact_name", "schema_name", "mutator"),
    [
        (
            "deployment_manifest.json",
            "deployment_v1.schema.json",
            lambda value: value["source"].update({"host_path": "/tmp/source"}),
        ),
        (
            "model.ir.json",
            "semantic_v1.schema.json",
            lambda value: value["architectural_outputs"]["branch"].update(
                {"values": []}
            ),
        ),
        (
            "tensor_manifest.json",
            "tensor_manifest_v1.schema.json",
            lambda value: value["projection"]["memory_map"].update({"host_pointer": 0}),
        ),
        (
            "numeric_profile.json",
            "numeric_profile_v1.schema.json",
            lambda value: value["dimensions"].update({"reserved": 1}),
        ),
        (
            "counter_contract.json",
            "counter_contract_v1.schema.json",
            lambda value: value["data_dependent"][
                "hc_pre_branch_bf16_saturations"
            ].update({"estimate": 0}),
        ),
        (
            "operator_coverage.json",
            "operator_coverage_v1.schema.json",
            lambda value: value["site"].update({"operator_index": 0}),
        ),
        (
            "roundtrip_report.json",
            "roundtrip_v1.schema.json",
            lambda value: value["reconstructed"][0].update({"host_path": "/tmp"}),
        ),
    ],
)
def test_hc_pre_schemas_reject_unknown_nested_fields(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    artifact_name: str,
    schema_name: str,
    mutator,
) -> None:
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    value = copy.deepcopy(load_strict_json(output / artifact_name))
    mutator(value)
    schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value))


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda application, verification: application["inputs"][0].update(
                {"action": "slice"}
            ),
            "canonical input",
        ),
        (
            lambda application, verification: application["assignments"][0].update(
                {"rank": False}
            ),
            "assignment differs",
        ),
        (
            lambda application, verification: application["coverage"].update(
                {"output_assignment_count": 11}
            ),
            "application coverage differs",
        ),
        (
            lambda application, verification: application["plan"].update(
                {"expected_input_count": 4}
            ),
            "status or completeness differs",
        ),
        (
            lambda application, verification: verification["checks"][0].update(
                {"method": "claimed_without_replay"}
            ),
            "verification check 0 differs",
        ),
        (
            lambda application, verification: verification["coverage"].update(
                {"checked_assignment_count": 11}
            ),
            "verification coverage differs",
        ),
    ],
)
def test_hc_pre_independent_checker_closes_rehashed_canonical_evidence(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    mutator,
    message: str,
) -> None:
    _, _, application_root, _ = hc_pre_application
    application = load_strict_json(application_root / "canonical_application.json")
    verification = load_strict_json(application_root / "canonical_verification.json")
    mutator(application, verification)
    _rehash_canonical_evidence(application, verification)
    with pytest.raises(DeepSeekV4HCPreCheckError, match=message):
        hc_checker_module._application_evidence(application, verification)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "attacker/spoofed-checkpoint"),
        ("revision", "0" * 40),
    ],
)
def test_hc_pre_builder_binds_application_provenance_to_checkpoint_lock(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    _, _, application_root, _ = hc_pre_application
    application_path = application_root / "canonical_application.json"
    verification_path = application_root / "canonical_verification.json"
    application = load_strict_json(application_path)
    verification = load_strict_json(verification_path)
    application["source"][field] = value
    _rehash_canonical_evidence(application, verification)
    application_path.write_bytes(canonical_json_bytes(application))
    verification_path.write_bytes(canonical_json_bytes(verification))

    output = tmp_path / "must-not-exist"
    with pytest.raises(
        DeepSeekV4HCPreBuildError,
        match="source release differs|source differs from its checkpoint lock",
    ):
        _build(hc_pre_application, output)
    assert not output.exists()


def test_hc_pre_build_rejects_wrong_name_shape_and_dtype(
    tmp_path: Path,
) -> None:
    variants = (
        _plan(names={PROJECTION_NAME: "layers.0.hc_attn_projection"}),
        _plan(shapes={PROJECTION_NAME: [24, 16383]}),
        _plan(dtypes={BASE_NAME: ("BF16", "BF16")}),
    )
    for index, plan in enumerate(variants):
        source = _materialize_application(tmp_path / f"variant-{index}", plan=plan)
        output = tmp_path / f"rejected-{index}"
        with pytest.raises(DeepSeekV4HCPreBuildError):
            _build(source, output)
        assert not output.exists()


def test_hc_pre_build_rejects_non_mp4_application_atomically(tmp_path: Path) -> None:
    source = _materialize_application(
        tmp_path / "three-rank-source", plan=_plan(rank_count=3)
    )
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4HCPreBuildError, match="ranks 0..3"):
        _build(source, output)
    assert not output.exists()


def test_hc_pre_build_rejects_replica_drift_atomically(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    replica = application / f"ranks/rank-003/{PROJECTION_NAME}.bin"
    with replica.open("r+b") as handle:
        handle.seek(4096)
        byte = handle.read(1)
        handle.seek(4096)
        handle.write(bytes((byte[0] ^ 1,)))
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4HCPreBuildError, match="replay failed.*differs"):
        _build(hc_pre_application, output)
    assert not output.exists()


def test_hc_pre_build_rejects_nonfinite_parameter_atomically(tmp_path: Path) -> None:
    bad_base = bytearray(_finite_payload(24, 0))
    bad_base[8:12] = struct.pack("<I", 0x7F800000)
    source = _materialize_application(
        tmp_path / "nonfinite-source",
        payload_overrides={BASE_NAME: bytes(bad_base)},
    )
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4HCPreBuildError, match="nonfinite"):
        _build(source, output)
    assert not output.exists()


def test_hc_pre_build_refuses_existing_output_without_touching_it(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "owned-by-user"
    sentinel.write_bytes(b"preserve")
    with pytest.raises(DeepSeekV4HCPreBuildError, match="already exists"):
        _build(hc_pre_application, output)
    assert sentinel.read_bytes() == b"preserve"
    assert list(output.iterdir()) == [sentinel]


def test_hc_pre_atomic_publish_does_not_replace_racing_peer(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "racing-peer"
    original_build_into = hc_build_module._build_into

    def build_then_race(**kwargs: Any) -> dict[str, Any]:
        deployment = original_build_into(**kwargs)
        output.mkdir()
        (output / "peer-owned").write_bytes(b"preserve")
        return deployment

    with monkeypatch.context() as context:
        context.setattr(hc_build_module, "_build_into", build_then_race)
        with pytest.raises(DeepSeekV4HCPreBuildError, match="already exists"):
            _build(hc_pre_application, output)
    assert (output / "peer-owned").read_bytes() == b"preserve"
    assert list(output.iterdir()) == [output / "peer-owned"]


def test_hc_pre_output_parent_replacement_fails_closed_and_cleans_by_descriptor(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publish_parent = tmp_path / "publish-parent"
    publish_parent.mkdir()
    displaced_parent = tmp_path / "displaced-parent"
    output = publish_parent / "deployment"
    original_build_into = hc_build_module._build_into

    def build_then_replace_parent(**kwargs: Any) -> dict[str, Any]:
        deployment = original_build_into(**kwargs)
        publish_parent.rename(displaced_parent)
        publish_parent.mkdir()
        return deployment

    with monkeypatch.context() as context:
        context.setattr(hc_build_module, "_build_into", build_then_replace_parent)
        with pytest.raises(
            DeepSeekV4HCPreBuildError,
            match="cannot reopen|was replaced",
        ):
            _build(hc_pre_application, output)

    assert not output.exists()
    assert list(publish_parent.iterdir()) == []
    assert list(displaced_parent.iterdir()) == []


def test_hc_pre_resolves_existing_output_parent_symlink_before_binding(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    resolved_parent = tmp_path / "resolved-parent"
    resolved_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(resolved_parent, target_is_directory=True)
    output = linked_parent / "deployment"

    manifest = _build(hc_pre_application, output)

    assert output.resolve() == resolved_parent / "deployment"
    assert load_strict_json(output / "deployment_manifest.json") == manifest
    assert (
        verify_deepseek_v4_hc_pre_deployment(
            output,
            hc_pre_application[2],
        )["build_id"]
        == manifest["build_id"]
    )


def test_hc_pre_cleanup_refuses_replaced_temporary_directory(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publish_parent = tmp_path / "publish-parent"
    publish_parent.mkdir()
    output = publish_parent / "deployment"
    original_build_into = hc_build_module._build_into
    moved_temporary: Path | None = None

    def build_then_replace_temporary(**kwargs: Any) -> dict[str, Any]:
        nonlocal moved_temporary
        deployment = original_build_into(**kwargs)
        temporary = kwargs["root"]
        moved_temporary = temporary.with_name(f"{temporary.name}.moved")
        temporary.rename(moved_temporary)
        temporary.mkdir()
        (temporary / "peer-owned").write_bytes(b"preserve")
        return deployment

    with monkeypatch.context() as context:
        context.setattr(hc_build_module, "_build_into", build_then_replace_temporary)
        with pytest.raises(
            DeepSeekV4HCPreBuildError,
            match="refusing to clean a replaced temporary HC_PRE deployment",
        ):
            _build(hc_pre_application, output)

    assert moved_temporary is not None
    replacement_directories = [
        path
        for path in publish_parent.iterdir()
        if path.name.startswith(".hc-pre-package.tmp-") and path != moved_temporary
    ]
    assert len(replacement_directories) == 1
    assert (replacement_directories[0] / "peer-owned").read_bytes() == b"preserve"
    assert moved_temporary.is_dir()
    assert not output.exists()


def test_hc_pre_checkers_reject_payload_and_metadata_mutation(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    tensors = load_strict_json(output / "tensor_manifest.json")
    projection = output / tensors["projection"]["path"]
    with projection.open("r+b") as handle:
        handle.seek(8192)
        byte = handle.read(1)
        handle.seek(8192)
        handle.write(bytes((byte[0] ^ 1,)))
    with pytest.raises(DeepSeekV4HCPreCheckError, match="differs"):
        verify_deepseek_v4_hc_pre_roundtrip(output, application)
    with pytest.raises(DeepSeekV4HCPreCheckError, match="differs"):
        verify_deepseek_v4_hc_pre_deployment(output, application)


def test_hc_pre_checker_rejects_rehashed_numeric_profile_drift(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    profile_path = output / "numeric_profile.json"
    profile = load_strict_json(profile_path)
    profile["dimensions"]["sinkhorn_iterations"] = 19
    profile_path.write_bytes(canonical_json_bytes(profile))
    _rehash_deployment_artifact(output, "numeric_profile.json")
    with pytest.raises(DeepSeekV4HCPreCheckError, match="frozen contract"):
        verify_deepseek_v4_hc_pre_deployment(output, application)


def test_hc_pre_checker_does_not_treat_json_boolean_as_frozen_integer(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    counters_path = output / "counter_contract.json"
    counters = load_strict_json(counters_path)
    counters["data_dependent"]["hc_pre_branch_bf16_saturations"][
        "minimum_per_token"
    ] = False
    counters_path.write_bytes(canonical_json_bytes(counters))
    _rehash_deployment_artifact(output, "counter_contract.json")
    with pytest.raises(DeepSeekV4HCPreCheckError, match="frozen contract"):
        verify_deepseek_v4_hc_pre_deployment(output, application)


def test_hc_pre_checker_rejects_unlisted_empty_directory(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    (output / "unlisted-empty-directory").mkdir()
    with pytest.raises(DeepSeekV4HCPreCheckError, match="unlisted or missing"):
        verify_deepseek_v4_hc_pre_deployment(output, application)


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_hc_pre_builder_rejects_nonregular_source_without_blocking(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    kind: str,
) -> None:
    _, _, application, _ = hc_pre_application
    source = application / f"ranks/rank-000/{BASE_NAME}.bin"
    source.unlink()
    if kind == "symlink":
        source.symlink_to(application / f"ranks/rank-001/{BASE_NAME}.bin")
    else:
        os.mkfifo(source)
    output = tmp_path / f"rejected-{kind}"
    with pytest.raises(
        DeepSeekV4HCPreBuildError,
        match="without following symlinks|not a regular file",
    ):
        _build(hc_pre_application, output)
    assert not output.exists()


def test_hc_pre_builder_rejects_oversize_source_before_replay(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    source = application / f"ranks/rank-000/{BASE_NAME}.bin"
    with source.open("ab") as handle:
        handle.write(b"\x00")
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4HCPreBuildError, match="bytes, expected 96"):
        _build(hc_pre_application, output)
    assert not output.exists()


@pytest.mark.parametrize("replacement", [False, True])
def test_hc_pre_builder_rejects_source_mutation_or_identical_replacement(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: bool,
) -> None:
    _, _, application, _ = hc_pre_application
    source = application / f"ranks/rank-000/{PROJECTION_NAME}.bin"
    payload = source.read_bytes()
    metadata = source.stat()
    identity = (metadata.st_dev, metadata.st_ino)
    original_pread = hc_build_module.os.pread
    changed = False

    def adversarial_pread(descriptor: int, length: int, offset: int) -> bytes:
        nonlocal changed
        chunk = original_pread(descriptor, length, offset)
        current = os.fstat(descriptor)
        if not changed and (current.st_dev, current.st_ino) == identity:
            if replacement:
                replacement_path = source.with_suffix(".replacement")
                replacement_path.write_bytes(payload)
                os.replace(replacement_path, source)
            else:
                with source.open("r+b") as handle:
                    handle.seek(16)
                    value = handle.read(1)
                    handle.seek(16)
                    handle.write(bytes((value[0] ^ 1,)))
            changed = True
        return chunk

    output = tmp_path / "must-not-exist"
    with monkeypatch.context() as context:
        context.setattr(hc_build_module.os, "pread", adversarial_pread)
        with pytest.raises(
            DeepSeekV4HCPreBuildError,
            match="changed while|was replaced while",
        ):
            _build(hc_pre_application, output)
    assert changed
    assert not output.exists()


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_hc_pre_checker_rejects_nonregular_deployment_entry_without_blocking(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    kind: str,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    tensors = load_strict_json(output / "tensor_manifest.json")
    payload = output / tensors["base"]["path"]
    payload.unlink()
    if kind == "symlink":
        payload.symlink_to(output / tensors["scale"]["path"])
    else:
        os.mkfifo(payload)
    with pytest.raises(
        DeepSeekV4HCPreCheckError,
        match="without following symlinks|not a regular file",
    ):
        verify_deepseek_v4_hc_pre_deployment(output, application)


def test_hc_pre_checker_rejects_oversize_manifest_before_decode(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    manifest = output / "deployment_manifest.json"
    manifest.write_bytes(b"{" + b" " * (1024 * 1024) + b"}")
    with pytest.raises(DeepSeekV4HCPreCheckError, match="exceeds"):
        verify_deepseek_v4_hc_pre_deployment(output, application)


@pytest.mark.parametrize("replacement", [False, True])
def test_hc_pre_checker_rejects_mutation_or_identical_replacement_during_read(
    hc_pre_application: tuple[Path, dict[str, Any], Path, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: bool,
) -> None:
    _, _, application, _ = hc_pre_application
    output = tmp_path / "deployment"
    _build(hc_pre_application, output)
    tensors = load_strict_json(output / "tensor_manifest.json")
    payload_path = output / tensors["projection"]["path"]
    payload = payload_path.read_bytes()
    metadata = payload_path.stat()
    identity = (metadata.st_dev, metadata.st_ino)
    original_pread = hc_checker_module.os.pread
    changed = False

    def adversarial_pread(descriptor: int, length: int, offset: int) -> bytes:
        nonlocal changed
        chunk = original_pread(descriptor, length, offset)
        current = os.fstat(descriptor)
        if not changed and (current.st_dev, current.st_ino) == identity:
            if replacement:
                replacement_path = payload_path.with_suffix(".replacement")
                replacement_path.write_bytes(payload)
                os.replace(replacement_path, payload_path)
            else:
                with payload_path.open("r+b") as handle:
                    handle.seek(32)
                    value = handle.read(1)
                    handle.seek(32)
                    handle.write(bytes((value[0] ^ 1,)))
            changed = True
        return chunk

    with monkeypatch.context() as context:
        context.setattr(hc_checker_module.os, "pread", adversarial_pread)
        with pytest.raises(
            DeepSeekV4HCPreCheckError,
            match="changed while|was replaced while",
        ):
            verify_deepseek_v4_hc_pre_deployment(output, application)
    assert changed


def test_hc_pre_secure_open_helpers_reject_character_device() -> None:
    with ExitStack() as builder_stack:
        root_descriptor, _ = hc_build_module._open_root(
            builder_stack, Path("/dev"), "device directory"
        )
        with pytest.raises(DeepSeekV4HCPreBuildError, match="not a regular file"):
            hc_build_module._safe_source(
                builder_stack,
                root_descriptor,
                "null",
                "character device",
                maximum_size=1,
            )
    with ExitStack() as checker_stack:
        root_descriptor, _ = hc_checker_module._open_root(
            checker_stack, Path("/dev"), "device directory"
        )
        with pytest.raises(DeepSeekV4HCPreCheckError, match="not a regular file"):
            hc_checker_module._safe_file(
                checker_stack,
                root_descriptor,
                "null",
                "character device",
                maximum_size=1,
            )
