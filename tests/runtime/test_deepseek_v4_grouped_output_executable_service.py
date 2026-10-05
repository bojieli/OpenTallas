from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

import pytest

from compiler.vertical_slice.deepseek_v4_grouped_output_executable import (
    ENTRYPOINT,
    MANIFEST_FILENAME,
    build_deepseek_v4_grouped_output_executable_deployment,
)
from runtime.service_engine.deepseek_v4_grouped_output_executable import (
    FLATTENED_OUTPUT_PATH,
    GROUPED_OUTPUT_PATH,
    REQUEST_INPUT_PATH,
    REQUEST_MANIFEST,
    RESULT_MANIFEST,
    DeepSeekV4GroupedOutputExecutableServiceEngine,
    DeepSeekV4GroupedOutputExecutableServiceError,
    build_deepseek_v4_grouped_output_execution_request,
    execute_deepseek_v4_grouped_output_executable_deployment,
    load_deepseek_v4_grouped_output_executable_deployment,
    load_deepseek_v4_grouped_output_executable_result,
)
from runtime.service_engine.grouped_output_numeric import (
    grouped_output_functional_counters,
)
from runtime.service_engine.secure_artifacts import canonical_json_bytes


CANONICAL_APPLICATION_ID = (
    "0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb"
)
RANK_ZERO_ASSIGNMENT_SHA256 = (
    "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b"
)


def _official_paths() -> tuple[Path, Path, Path] | None:
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
    lock = evidence / "checkpoint.lock.json"
    application = evidence / "canonical-mp4"
    assignment = (
        application / "ranks/rank-000/layers.0.attn.wo_a.weight.bin"
    )
    if not (
        (snapshot / "inference/model.py").is_file()
        and lock.is_file()
        and (application / "canonical_application.json").is_file()
        and (application / "canonical_verification.json").is_file()
        and assignment.is_file()
    ):
        return None
    return snapshot, lock, application


def _input_binding() -> dict[str, Any]:
    return {
        "kind": "external_content_hash_binding_only",
        "producer_id": CANONICAL_APPLICATION_ID,
        "producer_schema": "opentallas.canonical_application.v1",
        "source_byte_offset": 0,
        "source_content_sha256": RANK_ZERO_ASSIGNMENT_SHA256,
    }


@pytest.fixture(scope="module")
def official_runtime(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    paths = _official_paths()
    if paths is None:
        pytest.skip("pinned official grouped-output evidence is unavailable")
    root = tmp_path_factory.mktemp("deepseek-v4-grouped-output-runtime")
    package = root / "package"
    build = build_deepseek_v4_grouped_output_executable_deployment(
        *paths,
        package,
        world_size=8,
        rank=0,
    )
    assignment = (
        paths[2] / "ranks/rank-000/layers.0.attn.wo_a.weight.bin"
    )
    with assignment.open("rb") as source:
        activation = source.read(8_192)
    assert len(activation) == 8_192
    assert hashlib.sha256(assignment.read_bytes()).hexdigest() == (
        RANK_ZERO_ASSIGNMENT_SHA256
    )
    package_before = _tree_identity(package)
    request = root / "request"
    request_manifest = build_deepseek_v4_grouped_output_execution_request(
        package,
        request,
        activation,
        batch_count=1,
        sequence_length=1,
        selected_output_ranks=[0, 7],
        input_binding=_input_binding(),
    )
    request_before = _tree_identity(request)
    first_result = root / "result-first"
    second_result = root / "result-second"
    with DeepSeekV4GroupedOutputExecutableServiceEngine.load(package) as engine:
        first = engine.execute(request / REQUEST_MANIFEST, first_result)
        replay = engine.replay(
            first_result,
            expected_request_id=request_manifest["request_id"],
        )
        second = engine.execute(request / REQUEST_MANIFEST, second_result)
    assert _tree_identity(package) == package_before
    assert _tree_identity(request) == request_before
    return {
        "activation": activation,
        "build": build,
        "first": first,
        "first_result": first_result,
        "package": package,
        "package_before": package_before,
        "replay": replay,
        "request": request,
        "request_before": request_before,
        "request_manifest": request_manifest,
        "root": root,
        "second": second,
        "second_result": second_result,
    }


def _tree_identity(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _copy_tree(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert type(value) is dict
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _rehash_identity(value: dict[str, Any], identity_field: str) -> None:
    body = {key: child for key, child in value.items() if key != identity_field}
    value[identity_field] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _reseal_package_artifact(
    package: Path,
    relative_path: str,
    payload: bytes,
) -> None:
    (package / relative_path).write_bytes(payload)
    manifest_path = package / MANIFEST_FILENAME
    manifest = _load_json(manifest_path)
    record = next(
        item for item in manifest["artifacts"] if item["path"] == relative_path
    )
    record["sha256"] = hashlib.sha256(payload).hexdigest()
    record["size_bytes"] = len(payload)
    _rehash_identity(manifest, "build_id")
    _write_json(manifest_path, manifest)


def test_runtime_has_no_compiler_checkpoint_reference_or_expected_output_import() -> (
    None
):
    source = Path(
        "runtime/service_engine/deepseek_v4_grouped_output_executable.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    absolute_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    absolute_imports.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    forbidden_roots = {
        "compiler",
        "safetensors",
        "torch",
        "transformers",
        "runtime.reference",
    }
    assert not any(
        module == root or module.startswith(f"{root}.")
        for module in absolute_imports
        for root in forbidden_roots
    )
    assert not any(
        isinstance(node, ast.Name) and node.id == "expected_output"
        for node in ast.walk(tree)
    )


def test_official_content_audit_executes_deterministically_and_replays(
    official_runtime: dict[str, Any],
) -> None:
    first = official_runtime["first"]
    second = official_runtime["second"]
    replay = official_runtime["replay"]
    request = official_runtime["request_manifest"]
    assert first.manifest["result_id"] == second.manifest["result_id"]
    assert replay.manifest["result_id"] == first.manifest["result_id"]
    assert first.manifest["request_id"] == request["request_id"]
    assert first.manifest["execution_scope"] == "selected_output_rank_audit"
    assert first.manifest["complete_output"] is False
    assert first.manifest["selected_output_ranks"] == (0, 7)
    assert _tree_identity(official_runtime["first_result"]) == _tree_identity(
        official_runtime["second_result"]
    )
    assert _tree_identity(official_runtime["package"]) == official_runtime[
        "package_before"
    ]
    assert _tree_identity(official_runtime["request"]) == official_runtime[
        "request_before"
    ]


def test_grouped_and_flattened_views_alias_exact_bytes_with_distinct_shapes(
    official_runtime: dict[str, Any],
) -> None:
    result_dir = official_runtime["first_result"]
    manifest = official_runtime["first"].manifest
    grouped = (result_dir / GROUPED_OUTPUT_PATH).read_bytes()
    flattened = (result_dir / FLATTENED_OUTPUT_PATH).read_bytes()
    assert grouped == flattened
    assert hashlib.sha256(grouped).hexdigest() == manifest["outputs"]["grouped"][
        "sha256"
    ]
    assert manifest["outputs"]["grouped"]["shape"] == (1, 1, 1, 2)
    assert manifest["outputs"]["flattened"]["shape"] == (1, 1, 2)
    assert len(grouped) == 4


def test_result_counters_reconcile_exact_semantic_work(
    official_runtime: dict[str, Any],
) -> None:
    expected = dict(grouped_output_functional_counters(1, 8, 2))
    assert dict(official_runtime["first"].logical_counters) == expected
    assert expected["grouped_output_exact_product_accumulates"] == 8_192
    assert expected["grouped_output_grouped_output_bf16_values"] == 2
    assert expected["grouped_output_flattened_output_bf16_values"] == 2
    assert expected["semantic_operators_executed"] == 1
    assert expected["complete_events"] == 1


def test_request_and_result_publication_are_create_once_without_overwrite(
    official_runtime: dict[str, Any],
) -> None:
    package = official_runtime["package"]
    request = official_runtime["request"]
    result = official_runtime["first_result"]
    request_before = _tree_identity(request)
    result_before = _tree_identity(result)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        build_deepseek_v4_grouped_output_execution_request(
            package,
            request,
            official_runtime["activation"],
            batch_count=1,
            sequence_length=1,
            selected_output_ranks=[0, 7],
            input_binding=_input_binding(),
        )
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        execute_deepseek_v4_grouped_output_executable_deployment(
            package,
            request / REQUEST_MANIFEST,
            result,
        )
    assert _tree_identity(request) == request_before
    assert _tree_identity(result) == result_before


def test_forged_self_consistent_resource_segment_is_rejected(
    official_runtime: dict[str, Any],
    tmp_path: Path,
) -> None:
    package = _copy_tree(official_runtime["package"], tmp_path / "package")
    relative_path = ENTRYPOINT["resource_manifest"]
    resource_manifest = _load_json(package / relative_path)
    resource_manifest["resources"][0]["segments"][0]["content_sha256"] = "0" * 64
    _rehash_identity(resource_manifest, "resource_manifest_id")
    _reseal_package_artifact(
        package,
        relative_path,
        canonical_json_bytes(resource_manifest),
    )
    with pytest.raises(
        DeepSeekV4GroupedOutputExecutableServiceError,
        match="segments differ from frozen official assignments",
    ):
        load_deepseek_v4_grouped_output_executable_deployment(package)


@pytest.mark.parametrize("artifact_key", ["program", "execution_request_schema"])
def test_forged_self_consistent_static_artifact_is_rejected(
    official_runtime: dict[str, Any],
    tmp_path: Path,
    artifact_key: str,
) -> None:
    package = _copy_tree(official_runtime["package"], tmp_path / "package")
    relative_path = ENTRYPOINT[artifact_key]
    payload = bytearray((package / relative_path).read_bytes())
    payload[-1] ^= 1
    _reseal_package_artifact(package, relative_path, bytes(payload))
    with pytest.raises(
        DeepSeekV4GroupedOutputExecutableServiceError,
        match="content identity differs",
    ):
        load_deepseek_v4_grouped_output_executable_deployment(package)


def test_in_memory_deployment_substitution_is_rejected(
    official_runtime: dict[str, Any],
) -> None:
    deployment = load_deepseek_v4_grouped_output_executable_deployment(
        official_runtime["package"]
    )
    try:
        deployment.local_group_count = True
        with pytest.raises(
            DeepSeekV4GroupedOutputExecutableServiceError,
            match="in-memory snapshot differs",
        ):
            deployment.verify()
    finally:
        deployment.close()


@pytest.mark.parametrize(
    ("batch_count", "selected"),
    [
        (True, [0]),
        (1, [False]),
    ],
)
def test_bool_integer_aliases_fail_before_request_publication(
    official_runtime: dict[str, Any],
    tmp_path: Path,
    batch_count: object,
    selected: list[object],
) -> None:
    output = tmp_path / "request"
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        build_deepseek_v4_grouped_output_execution_request(
            official_runtime["package"],
            output,
            official_runtime["activation"],
            batch_count=batch_count,  # type: ignore[arg-type]
            sequence_length=1,
            selected_output_ranks=selected,
            input_binding=_input_binding(),
        )
    assert not output.exists()


def test_nonfinite_bf16_input_fails_before_request_publication(
    official_runtime: dict[str, Any],
    tmp_path: Path,
) -> None:
    payload = bytearray(official_runtime["activation"])
    payload[:2] = b"\x80\x7f"
    output = tmp_path / "request"
    with pytest.raises(
        DeepSeekV4GroupedOutputExecutableServiceError,
        match="nonfinite BF16",
    ):
        build_deepseek_v4_grouped_output_execution_request(
            official_runtime["package"],
            output,
            bytes(payload),
            batch_count=1,
            sequence_length=1,
            selected_output_ranks=[0, 7],
            input_binding=_input_binding(),
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("selected_output_ranks", [7, 0]),
        ("input.shape.local_heads", True),
    ],
)
def test_self_consistent_request_manifest_mutations_poison_without_output(
    official_runtime: dict[str, Any],
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    request = _copy_tree(official_runtime["request"], tmp_path / "request")
    manifest_path = request / REQUEST_MANIFEST
    manifest = _load_json(manifest_path)
    if field == "selected_output_ranks":
        manifest[field] = replacement
    else:
        manifest["input"]["shape"][2] = replacement
    _rehash_identity(manifest, "request_id")
    _write_json(manifest_path, manifest)
    request_before = _tree_identity(request)
    output = tmp_path / "result"
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        execute_deepseek_v4_grouped_output_executable_deployment(
            official_runtime["package"],
            manifest_path,
            output,
        )
    assert not output.exists()
    assert _tree_identity(request) == request_before


def test_self_consistent_nonfinite_request_payload_poisons_without_output(
    official_runtime: dict[str, Any],
    tmp_path: Path,
) -> None:
    request = _copy_tree(official_runtime["request"], tmp_path / "request")
    input_path = request / REQUEST_INPUT_PATH
    payload = bytearray(input_path.read_bytes())
    payload[:2] = b"\x80\x7f"
    input_path.write_bytes(payload)
    manifest_path = request / REQUEST_MANIFEST
    manifest = _load_json(manifest_path)
    manifest["input"]["sha256"] = hashlib.sha256(payload).hexdigest()
    _rehash_identity(manifest, "request_id")
    _write_json(manifest_path, manifest)
    output = tmp_path / "result"
    with pytest.raises(
        DeepSeekV4GroupedOutputExecutableServiceError,
        match="nonfinite BF16",
    ):
        execute_deepseek_v4_grouped_output_executable_deployment(
            official_runtime["package"],
            manifest_path,
            output,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("mutation", "replacement"),
    [
        (("request_sha256",), True),
        (("outputs", "grouped", "shape", 2), True),
    ],
)
def test_self_consistent_result_manifest_bool_aliases_fail_replay(
    official_runtime: dict[str, Any],
    tmp_path: Path,
    mutation: tuple[str | int, ...],
    replacement: object,
) -> None:
    result = _copy_tree(official_runtime["first_result"], tmp_path / "result")
    manifest_path = result / RESULT_MANIFEST
    manifest = _load_json(manifest_path)
    cursor: Any = manifest
    for component in mutation[:-1]:
        cursor = cursor[component]
    cursor[mutation[-1]] = replacement
    _rehash_identity(manifest, "result_id")
    _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        load_deepseek_v4_grouped_output_executable_result(result)


def test_self_consistent_output_mutation_cannot_change_one_alias_view(
    official_runtime: dict[str, Any],
    tmp_path: Path,
) -> None:
    result = _copy_tree(official_runtime["first_result"], tmp_path / "result")
    grouped_path = result / GROUPED_OUTPUT_PATH
    payload = bytearray(grouped_path.read_bytes())
    payload[0] ^= 1
    grouped_path.write_bytes(payload)
    manifest_path = result / RESULT_MANIFEST
    manifest = _load_json(manifest_path)
    manifest["outputs"]["grouped"]["sha256"] = hashlib.sha256(payload).hexdigest()
    _rehash_identity(manifest, "result_id")
    _write_json(manifest_path, manifest)
    with pytest.raises(
        DeepSeekV4GroupedOutputExecutableServiceError,
        match="grouped and flattened byte views differ",
    ):
        load_deepseek_v4_grouped_output_executable_result(result)


def test_symlinked_request_input_is_rejected_without_result(
    official_runtime: dict[str, Any],
    tmp_path: Path,
) -> None:
    request = _copy_tree(official_runtime["request"], tmp_path / "request")
    input_path = request / REQUEST_INPUT_PATH
    input_path.unlink()
    input_path.symlink_to("../request_manifest.json")
    output = tmp_path / "result"
    with pytest.raises(DeepSeekV4GroupedOutputExecutableServiceError):
        execute_deepseek_v4_grouped_output_executable_deployment(
            official_runtime["package"],
            request / REQUEST_MANIFEST,
            output,
        )
    assert not output.exists()

