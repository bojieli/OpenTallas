from __future__ import annotations

from contextlib import ExitStack
import copy
from dataclasses import FrozenInstanceError
import hashlib
import inspect
import json
import os
from pathlib import Path
import struct
from typing import Any

import pytest

from compiler.microcode.deepseek_v4_hc_pre import assemble, encode
from compiler.frontend.checkpoint import load_checkpoint_lock
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    build_deepseek_v4_hc_pre_deployment,
)
import runtime.service_engine.deepseek_v4_hc_pre as hc_service_module
from runtime.service_engine.deepseek_v4_hc_pre import (
    BASE_BYTES,
    BASE_NAME,
    BASE_SHAPE,
    COUNTER_CONTRACT_SCHEMA,
    DEPLOYMENT_SCHEMA,
    EXECUTABLE_INTEGRATION_REQUIREMENTS,
    MODEL_ID,
    NUMERIC_PROFILE_ID,
    NUMERIC_PROFILE_SCHEMA,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    PROJECTION_BYTES,
    PROJECTION_NAME,
    PROJECTION_SHAPE,
    ROUNDTRIP_SCHEMA,
    SCALE_BYTES,
    SCALE_NAME,
    SCALE_SHAPE,
    SEMANTIC_SCHEMA,
    TENSOR_SCHEMA,
    DeepSeekV4HCPreArtifactDeployment,
    DeepSeekV4HCPreServiceEngine,
    DeepSeekV4HCPreServiceError,
    execute_deepseek_v4_hc_pre_deployment,
    load_deepseek_v4_hc_pre_artifact_deployment,
)


APPLICATION_ID = "a" * 64
VERIFICATION_ID = "b" * 64
SITE = {"branch": "attention", "layer": 0, "scope": "main"}
COMPILER = {
    "name": "opentallas-deepseek-v4-hc-pre-artifact-compiler",
    "version": "0.1.0",
}
ENTRYPOINT = {
    "counter_contract": "counter_contract.json",
    "numeric_profile": "numeric_profile.json",
    "semantic_ir": "model.ir.json",
    "tensor_manifest": "tensor_manifest.json",
}
CLAIMS = [
    "Packages all learned parameters and the frozen numeric contract for one complete HC_PRE site.",
    "Contains no input activation or expected result and establishes no execution, transformer, model-completion, or CUDA-equivalence claim.",
    "Semantic counter coefficients are contract metadata only and establish no cycles, throughput, energy, area, or PPA result.",
    "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
]
SOURCE = {
    "application_id": APPLICATION_ID,
    "application_status": "partial_official_transform_application_not_release_evidence",
    "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
    "evidence_scope": "official_checkpoint",
    "repository": OFFICIAL_REPOSITORY,
    "revision": OFFICIAL_REVISION,
    "verification_id": VERIFICATION_ID,
}

OFFICIAL_BUILD_ID = "994815427eff455e780f8abf50a299896366dca0a5713778219ec43266aab3e2"
OFFICIAL_EVIDENCE_ROOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_EVIDENCE_ROOT"
OFFICIAL_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_HC_PRE_SNAPSHOT"


def _canonical(value: Any) -> bytes:
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


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _numeric_profile() -> dict[str, Any]:
    return {
        "arithmetic_order": {
            "branch_reduction": "balanced_(p0_plus_p1)_plus_(p2_plus_p3)",
            "field_affine": "separate_binary32_multiply_then_add",
            "nonlinear": "correctly_rounded_binary32_sigmoid_and_exp",
            "projection": "increasing_k_exact_product_single_rne_product_add",
            "rms_reduction": "balanced_14_level_binary32_rne",
            "sinkhorn": "stable_softmax_column_then_19_row_column_pairs",
        },
        "constants": {
            "hc_epsilon_binary32": 0x358637BD,
            "norm_epsilon_binary32": 0x358637BD,
        },
        "dimensions": {
            "combination_destinations": 4,
            "combination_sources": 4,
            "flattened_width": 16384,
            "hc_multiplier": 4,
            "hidden_size": 4096,
            "mix_fields": 24,
            "post_fields": 4,
            "pre_fields": 4,
            "sinkhorn_iterations": 20,
        },
        "encodings": {
            "branch_and_residual": "BF16",
            "byte_order": "little",
            "coefficients_and_parameters": "F32",
            "input": "BF16",
        },
        "exception_policy": {
            "command_commit": "atomic_across_all_batch_times_sequence_tokens",
            "finite_branch_saturation": "final_bf16_conversion_only_and_counted",
            "nonfinite_or_boundary_overflow": "poison_without_partial_commit",
            "subnormals": "preserved_no_ftz_or_daz",
        },
        "profile_id": NUMERIC_PROFILE_ID,
        "runtime_axes": {
            "batch": "positive_dynamic",
            "sequence": "positive_dynamic",
            "token_count": "batch_times_sequence",
        },
        "schema": NUMERIC_PROFILE_SCHEMA,
        "source_boundary": {
            "backend_bit_equivalence": "not_claimed",
            "kernel_source_sha256": (
                "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
            ),
            "model_source_sha256": (
                "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
            ),
        },
        "specification": {
            "document": "SPEC-NUM",
            "requirement": "NUM-6.10",
            "version": "1.1",
        },
    }


def _counter_contract() -> dict[str, Any]:
    return {
        "command_scaling": {
            "fixed_counters": "per_token_coefficient_times_batch_times_sequence",
            "poisoned_command": "no_success_counter_commit",
            "saturation_counter": "exact_observed_final_bf16_clamp_count",
        },
        "data_dependent": {
            "hc_pre_branch_bf16_saturations": {
                "maximum_per_token": 4096,
                "minimum_per_token": 0,
            }
        },
        "evidence_boundary": (
            "Semantic reconciliation coefficients only; not instruction, traffic, "
            "cycle, throughput, energy, area, or PPA evidence."
        ),
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "per_successfully_committed_token": {
            "hc_pre_branch_bf16_conversions": 4096,
            "hc_pre_branch_coefficient_multiplies": 16384,
            "hc_pre_branch_reduction_adds": 12288,
            "hc_pre_coefficient_epsilon_adds": 4,
            "hc_pre_exp_evaluations": 16,
            "hc_pre_field_affine_adds": 24,
            "hc_pre_field_affine_multiplies": 24,
            "hc_pre_input_bf16_values": 16384,
            "hc_pre_post_factor_multiplies": 4,
            "hc_pre_projection_product_accumulates": 393216,
            "hc_pre_projection_rms_multiplies": 24,
            "hc_pre_residual_bf16_values_preserved": 16384,
            "hc_pre_rms_divides": 1,
            "hc_pre_rms_epsilon_adds": 1,
            "hc_pre_rms_reduction_adds": 16383,
            "hc_pre_rms_square_multiplies": 16384,
            "hc_pre_rsqrt_evaluations": 1,
            "hc_pre_sigmoid_evaluations": 8,
            "hc_pre_sinkhorn_column_reduction_adds": 240,
            "hc_pre_sinkhorn_column_stages": 20,
            "hc_pre_sinkhorn_divides": 640,
            "hc_pre_sinkhorn_epsilon_adds": 172,
            "hc_pre_sinkhorn_row_reduction_adds": 240,
            "hc_pre_sinkhorn_row_stages": 20,
            "hc_pre_softmax_max_comparisons": 12,
            "hc_pre_softmax_subtracts": 16,
        },
        "schema": COUNTER_CONTRACT_SCHEMA,
        "specification": "SPEC-NUM 1.1 NUM-6.10.6",
    }


def _semantic() -> dict[str, Any]:
    return {
        "architectural_outputs": {
            "branch": {"dtype": "BF16", "shape": "[batch,sequence,4096]"},
            "comb": {"dtype": "F32", "shape": "[batch,sequence,4,4]"},
            "post": {"dtype": "F32", "shape": "[batch,sequence,4]"},
            "residual": {
                "dtype": "BF16",
                "shape": "[batch,sequence,4,4096]",
            },
        },
        "claim_boundary": (
            "Complete learned-parameter and numeric-contract package for one "
            "layer-0 attention HC_PRE site; contains no activation, result, or "
            "execution evidence."
        ),
        "model_id": MODEL_ID,
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "operation": {
            "base_resource": BASE_NAME,
            "input": "x_bf16[batch,sequence,4,4096]",
            "kind": "HC_PRE",
            "projection_resource": PROJECTION_NAME,
            "scale_resource": SCALE_NAME,
        },
        "schema": SEMANTIC_SCHEMA,
        "site": SITE,
        "source": SOURCE,
    }


def _coverage() -> dict[str, Any]:
    return {
        "execution_coverage": "none",
        "model_id": MODEL_ID,
        "numeric_contract_coverage": "SPEC-NUM 1.1 NUM-6.10",
        "packaged_operator_kind": "HC_PRE",
        "parameter_coverage": "all_three_learned_resources_for_one_site",
        "schema": "opentallas.deepseek_v4_hc_pre_coverage.v1",
        "site": SITE,
        "status": "complete_operator_artifact_contract_not_execution_evidence",
    }


def _resource(
    name: str,
    shape: tuple[int, ...],
    payload: bytes,
) -> dict[str, Any]:
    digest = _sha(payload)
    size = len(payload)
    return {
        "content_address": f"sha256:{digest}",
        "dtype": "F32",
        "encoding": "ieee754_binary32_little_endian",
        "layout": "c_contiguous_row_major",
        "memory_map": {"length_bytes": size, "offset_bytes": 0},
        "name": name,
        "path": f"payloads/sha256/{digest}.f32le",
        "replicated_ranks": [0, 1, 2, 3],
        "sha256": digest,
        "shape": list(shape),
        "size_bytes": size,
        "source_assignment_paths": [
            f"ranks/rank-{rank:03d}/{name}.bin" for rank in range(4)
        ],
    }


def _roundtrip(resources: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "application_id": APPLICATION_ID,
        "checked_artifact_count": 3,
        "checked_payload_bytes": BASE_BYTES + PROJECTION_BYTES + SCALE_BYTES,
        "checked_replica_count": 12,
        "checked_replica_payload_bytes": (BASE_BYTES + PROJECTION_BYTES + SCALE_BYTES)
        * 4,
        "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
        "model_id": MODEL_ID,
        "reconstructed": [
            {
                "deployment_path": record["path"],
                "dtype": "F32",
                "replicated_ranks": [0, 1, 2, 3],
                "sha256": record["sha256"],
                "shape": record["shape"],
                "size_bytes": record["size_bytes"],
                "source_assignment_paths": record["source_assignment_paths"],
                "tensor_name": record["name"],
            }
            for record in resources
        ],
        "schema": ROUNDTRIP_SCHEMA,
        "status": "byte_exact_full_parameter_roundtrip",
    }
    body["roundtrip_id"] = _sha(_canonical(body))
    return body


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical(value))


def _replace_nested_json_value(
    value: Any,
    path: tuple[str | int, ...],
    replacement: Any,
) -> None:
    target = value
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement


def _rehash_manifest(root: Path) -> None:
    manifest_path = root / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    for record in manifest["artifacts"]:
        payload = (root / record["path"]).read_bytes()
        record["sha256"] = _sha(payload)
        record["size_bytes"] = len(payload)
    identity = {
        "artifacts": manifest["artifacts"],
        "compiler": manifest["compiler"],
        "model_id": manifest["model_id"],
        "numeric_profile_id": manifest["numeric_profile_id"],
        "site": manifest["site"],
        "source": manifest["source"],
    }
    manifest["build_id"] = _sha(_canonical(identity))
    _write_json(manifest_path, manifest)


def _make_deployment(
    root: Path,
    *,
    base_payload: bytes | None = None,
) -> Path:
    root.mkdir()
    (root / "payloads/sha256").mkdir(parents=True)
    base_payload = base_payload or struct.pack(
        "<24I",
        *(
            0x80000000,
            0x00000001,
            0x3F000000,
            0x3F800000,
        )
        * 6,
    )
    projection_payload = b"\x00" * PROJECTION_BYTES
    scale_payload = struct.pack("<3I", 0x3F800000, 0x40000000, 0x3F000000)
    base = _resource(BASE_NAME, BASE_SHAPE, base_payload)
    projection = _resource(PROJECTION_NAME, PROJECTION_SHAPE, projection_payload)
    scale = _resource(SCALE_NAME, SCALE_SHAPE, scale_payload)
    tensor_manifest = {
        "base": base,
        "model_parallel": 4,
        "projection": projection,
        "scale": scale,
        "schema": TENSOR_SCHEMA,
        "total_unique_payload_bytes": BASE_BYTES + PROJECTION_BYTES + SCALE_BYTES,
    }
    json_artifacts = {
        "counter_contract.json": ("counter_contract", _counter_contract()),
        "model.ir.json": ("semantic_ir", _semantic()),
        "numeric_profile.json": ("numeric_profile", _numeric_profile()),
        "operator_coverage.json": ("operator_coverage", _coverage()),
        "roundtrip_report.json": (
            "roundtrip_report",
            _roundtrip((base, projection, scale)),
        ),
        "tensor_manifest.json": ("tensor_manifest", tensor_manifest),
    }
    roles = {
        base["path"]: "hc_base_parameter",
        projection["path"]: "hc_projection_parameter",
        scale["path"]: "hc_scale_parameter",
    }
    for relative, payload in (
        (base["path"], base_payload),
        (projection["path"], projection_payload),
        (scale["path"], scale_payload),
    ):
        destination = root / relative
        destination.write_bytes(payload)
    for relative, (role, value) in json_artifacts.items():
        _write_json(root / relative, value)
        roles[relative] = role
    artifacts = []
    for relative in sorted(roles):
        payload = (root / relative).read_bytes()
        artifacts.append(
            {
                "path": relative,
                "role": roles[relative],
                "sha256": _sha(payload),
                "size_bytes": len(payload),
            }
        )
    identity = {
        "artifacts": artifacts,
        "compiler": COMPILER,
        "model_id": MODEL_ID,
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "site": SITE,
        "source": SOURCE,
    }
    manifest = {
        **identity,
        "build_id": _sha(_canonical(identity)),
        "claim_boundary": CLAIMS,
        "entrypoint": ENTRYPOINT,
        "schema": DEPLOYMENT_SCHEMA,
        "status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
        ),
    }
    _write_json(root / "deployment_manifest.json", manifest)
    return root


@pytest.fixture
def deployment_root(tmp_path: Path) -> Path:
    return _make_deployment(tmp_path / "deployment")


def _official_builder_inputs() -> tuple[Path, Path, Path]:
    default_evidence_root = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731"
    default_snapshot = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / OFFICIAL_REVISION
    )
    evidence_root = Path(
        os.environ.get(OFFICIAL_EVIDENCE_ROOT_ENV, default_evidence_root)
    )
    snapshot = Path(os.environ.get(OFFICIAL_SNAPSHOT_ENV, default_snapshot))
    lock_path = evidence_root / "checkpoint.lock.json"
    application_root = evidence_root / "hc-pre-canonical"
    missing = [
        str(path)
        for path in (lock_path, application_root, snapshot)
        if not path.exists()
    ]
    if missing:
        pytest.skip(
            f"set {OFFICIAL_EVIDENCE_ROOT_ENV} and {OFFICIAL_SNAPSHOT_ENV} "
            f"for the real official HC_PRE builder integration; missing {missing}"
        )
    return snapshot, lock_path, application_root


def test_hc_pre_service_is_independent_and_v1_boundary_is_explicit() -> None:
    source = inspect.getsource(hc_service_module)
    assert "runtime.reference" not in source
    assert "compiler.checking" not in source
    assert "compiler.vertical_slice" not in source
    assert "execute_hc_pre(" not in source
    assert "execution_coverage=none" in source
    assert any(
        "packaged microcode" in item for item in EXECUTABLE_INTEGRATION_REQUIREMENTS
    )


def test_real_official_parameter_builder_output_loads_as_nonexecutable_v1(
    tmp_path: Path,
) -> None:
    snapshot, lock_path, application_root = _official_builder_inputs()
    output = tmp_path / "official-hc-pre-deployment"
    manifest = build_deepseek_v4_hc_pre_deployment(
        snapshot=snapshot,
        lock=load_checkpoint_lock(lock_path),
        application_root=application_root,
        output=output,
    )

    assert manifest["build_id"] == OFFICIAL_BUILD_ID
    assert manifest["claim_boundary"] == CLAIMS
    assert "microcode" not in manifest["entrypoint"]
    deployment = load_deepseek_v4_hc_pre_artifact_deployment(output)
    assert deployment.build_id == OFFICIAL_BUILD_ID
    assert deployment.executable is False


def test_hc_pre_artifact_loader_snapshots_exact_official_f32_resources(
    deployment_root: Path,
) -> None:
    deployment = load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)

    assert isinstance(deployment, DeepSeekV4HCPreArtifactDeployment)
    assert deployment.executable is False
    assert len(deployment.artifacts) == 9
    assert deployment.application_id == APPLICATION_ID
    assert deployment.verification_id == VERIFICATION_ID
    assert deployment.base.name == BASE_NAME
    assert deployment.base.shape == BASE_SHAPE
    assert deployment.base.codes[:4] == (
        0x80000000,
        0x00000001,
        0x3F000000,
        0x3F800000,
    )
    assert len(deployment.projection.codes) == 24
    assert all(len(row) == 16384 for row in deployment.projection.codes)
    assert deployment.scale.codes == (0x3F800000, 0x40000000, 0x3F000000)
    assert len(deployment.counter_coefficients) == 26
    assert (
        dict(deployment.counter_coefficients)["hc_pre_projection_product_accumulates"]
        == 393216
    )
    program = encode(assemble())
    assert deployment.required_microcode_sha256 == _sha(program)
    assert deployment.required_microcode_size_bytes == len(program)

    with pytest.raises(FrozenInstanceError):
        deployment.build_id = "0" * 64  # type: ignore[misc]
    with pytest.raises(TypeError):
        deployment.projection.codes[0][0] = 1  # type: ignore[index]


def test_hc_pre_service_loads_verified_snapshot_but_execution_fails_closed(
    deployment_root: Path,
    tmp_path: Path,
) -> None:
    engine = DeepSeekV4HCPreServiceEngine.load(deployment_root)
    request_fifo = tmp_path / "must-not-be-read"
    os.mkfifo(request_fifo)

    with pytest.raises(
        DeepSeekV4HCPreServiceError,
        match=r"parameter-only.*execution_coverage=none.*canonical versioned",
    ):
        engine.execute(request_fifo)
    with pytest.raises(DeepSeekV4HCPreServiceError, match="packaged microcode"):
        execute_deepseek_v4_hc_pre_deployment(deployment_root, request_fifo)


def test_hc_pre_loader_rejects_payload_mutation(deployment_root: Path) -> None:
    manifest = json.loads(
        (deployment_root / "deployment_manifest.json").read_text(encoding="ascii")
    )
    projection = next(
        item
        for item in manifest["artifacts"]
        if item["role"] == "hc_projection_parameter"
    )
    path = deployment_root / projection["path"]
    with path.open("r+b") as handle:
        handle.seek(8192)
        value = handle.read(1)
        handle.seek(8192)
        handle.write(bytes((value[0] ^ 1,)))
    with pytest.raises(DeepSeekV4HCPreServiceError, match="deployment hash"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


def test_hc_pre_loader_rejects_rehashed_contract_mutation(
    deployment_root: Path,
) -> None:
    profile_path = deployment_root / "numeric_profile.json"
    profile = json.loads(profile_path.read_text(encoding="ascii"))
    profile["dimensions"]["sinkhorn_iterations"] = 19
    _write_json(profile_path, profile)
    _rehash_manifest(deployment_root)

    with pytest.raises(DeepSeekV4HCPreServiceError, match="numeric profile differs"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


@pytest.mark.parametrize(
    ("relative", "path", "replacement", "message"),
    [
        (
            "deployment_manifest.json",
            ("site", "layer"),
            False,
            "metadata or non-execution claim boundary differs",
        ),
        ("model.ir.json", ("site", "layer"), False, "semantic IR differs"),
        (
            "numeric_profile.json",
            ("dimensions", "sinkhorn_iterations"),
            20.0,
            "numeric profile differs",
        ),
        (
            "counter_contract.json",
            (
                "data_dependent",
                "hc_pre_branch_bf16_saturations",
                "minimum_per_token",
            ),
            False,
            "counter contract differs",
        ),
        (
            "operator_coverage.json",
            ("site", "layer"),
            False,
            "explicit non-execution boundary",
        ),
        (
            "roundtrip_report.json",
            ("reconstructed", 0, "replicated_ranks", 0),
            False,
            "roundtrip report differs",
        ),
        (
            "tensor_manifest.json",
            ("base", "memory_map", "offset_bytes"),
            False,
            "official F32 identity",
        ),
    ],
)
def test_hc_pre_loader_uses_type_sensitive_frozen_json_comparisons(
    deployment_root: Path,
    relative: str,
    path: tuple[str | int, ...],
    replacement: Any,
    message: str,
) -> None:
    document_path = deployment_root / relative
    document = json.loads(document_path.read_text(encoding="ascii"))
    _replace_nested_json_value(document, path, replacement)
    _write_json(document_path, document)
    if relative != "deployment_manifest.json":
        _rehash_manifest(deployment_root)

    with pytest.raises(DeepSeekV4HCPreServiceError, match=message):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("checkpoint_lock_id", "0" * 64),
        ("evidence_scope", "development_checkpoint"),
        ("repository", "local/development-checkpoint"),
        ("revision", "0" * 40),
        ("application_status", "development_transform_application"),
    ],
)
def test_hc_pre_loader_rejects_development_source_identity(
    deployment_root: Path,
    field: str,
    replacement: str,
) -> None:
    manifest_path = deployment_root / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    manifest["source"][field] = replacement
    _write_json(manifest_path, manifest)
    _rehash_manifest(deployment_root)

    with pytest.raises(DeepSeekV4HCPreServiceError, match="pinned official"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


def test_hc_pre_loader_rejects_official_identity_and_f32_metadata_drift(
    deployment_root: Path,
) -> None:
    manifest_path = deployment_root / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    manifest["source"]["repository"] = "attacker/rehashed"
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
    manifest["build_id"] = _sha(_canonical(identity))
    _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4HCPreServiceError, match="pinned official"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)

    manifest["source"] = copy.deepcopy(SOURCE)
    identity["source"] = manifest["source"]
    manifest["build_id"] = _sha(_canonical(identity))
    _write_json(manifest_path, manifest)
    tensor_path = deployment_root / "tensor_manifest.json"
    tensors = json.loads(tensor_path.read_text(encoding="ascii"))
    tensors["base"]["dtype"] = "BF16"
    _write_json(tensor_path, tensors)
    _rehash_manifest(deployment_root)
    with pytest.raises(DeepSeekV4HCPreServiceError, match="official F32 identity"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


@pytest.mark.parametrize("replacement", [False, True])
def test_hc_pre_loader_rejects_mutation_or_identical_replacement_during_read(
    deployment_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: bool,
) -> None:
    manifest = json.loads(
        (deployment_root / "deployment_manifest.json").read_text(encoding="ascii")
    )
    record = next(
        item
        for item in manifest["artifacts"]
        if item["role"] == "hc_projection_parameter"
    )
    target = deployment_root / record["path"]
    payload = target.read_bytes()
    metadata = target.stat()
    identity = (metadata.st_dev, metadata.st_ino)
    original_pread = hc_service_module.os.pread
    changed = False

    def adversarial_pread(descriptor: int, length: int, offset: int) -> bytes:
        nonlocal changed
        chunk = original_pread(descriptor, length, offset)
        current = os.fstat(descriptor)
        if not changed and (current.st_dev, current.st_ino) == identity:
            if replacement:
                replacement_path = target.with_suffix(".replacement")
                replacement_path.write_bytes(payload)
                os.replace(replacement_path, target)
            else:
                with target.open("r+b") as handle:
                    handle.seek(16)
                    value = handle.read(1)
                    handle.seek(16)
                    handle.write(bytes((value[0] ^ 1,)))
            changed = True
        return chunk

    monkeypatch.setattr(hc_service_module.os, "pread", adversarial_pread)
    with pytest.raises(
        DeepSeekV4HCPreServiceError,
        match="changed while|was replaced while",
    ):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)
    assert changed


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_hc_pre_loader_rejects_nonregular_artifact_without_blocking(
    deployment_root: Path,
    kind: str,
) -> None:
    manifest = json.loads(
        (deployment_root / "deployment_manifest.json").read_text(encoding="ascii")
    )
    base = next(
        item for item in manifest["artifacts"] if item["role"] == "hc_base_parameter"
    )
    scale = next(
        item for item in manifest["artifacts"] if item["role"] == "hc_scale_parameter"
    )
    target = deployment_root / base["path"]
    target.unlink()
    if kind == "symlink":
        target.symlink_to(deployment_root / scale["path"])
    else:
        os.mkfifo(target)
    with pytest.raises(
        DeepSeekV4HCPreServiceError,
        match="without following symlinks|not a regular file",
    ):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


def test_hc_pre_loader_rejects_oversize_before_json_decode(
    deployment_root: Path,
) -> None:
    (deployment_root / "deployment_manifest.json").write_bytes(
        b"{" + b" " * (1024 * 1024) + b"}"
    )
    with pytest.raises(DeepSeekV4HCPreServiceError, match="exceeds"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


def test_hc_pre_loader_rejects_noncanonical_json_and_unlisted_microcode(
    deployment_root: Path,
) -> None:
    manifest_path = deployment_root / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="ascii")
    with pytest.raises(DeepSeekV4HCPreServiceError, match="not canonical JSON"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)

    _write_json(manifest_path, manifest)
    (deployment_root / "microcode.bin").write_bytes(encode(assemble()))
    with pytest.raises(DeepSeekV4HCPreServiceError, match="unlisted"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)


def test_hc_pre_loader_rejects_nonfinite_f32_payload_atomically(tmp_path: Path) -> None:
    codes = [0] * 24
    codes[7] = 0x7F800000
    root = _make_deployment(
        tmp_path / "nonfinite",
        base_payload=struct.pack("<24I", *codes),
    )
    with pytest.raises(DeepSeekV4HCPreServiceError, match="nonfinite binary32"):
        load_deepseek_v4_hc_pre_artifact_deployment(root)


def test_hc_pre_descriptor_helpers_reject_character_device() -> None:
    with ExitStack() as stack:
        descriptor, _ = hc_service_module._open_root(stack, Path("/dev"), "device root")
        with pytest.raises(DeepSeekV4HCPreServiceError, match="not a regular file"):
            hc_service_module._safe_file(
                stack,
                descriptor,
                "null",
                "character device",
                maximum_size=1,
            )


def test_hc_pre_loader_rejects_symlink_deployment_root(
    deployment_root: Path,
    tmp_path: Path,
) -> None:
    link = tmp_path / "deployment-link"
    link.symlink_to(deployment_root, target_is_directory=True)
    with pytest.raises(DeepSeekV4HCPreServiceError, match="without following symlinks"):
        load_deepseek_v4_hc_pre_artifact_deployment(link)


def test_hc_pre_loader_bounds_deployment_tree_depth(deployment_root: Path) -> None:
    nested = deployment_root / "extra"
    for depth in range(9):
        nested /= f"level-{depth}"
    nested.mkdir(parents=True)

    with pytest.raises(DeepSeekV4HCPreServiceError, match="directory depth exceeds"):
        load_deepseek_v4_hc_pre_artifact_deployment(deployment_root)
