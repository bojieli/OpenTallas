from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
from typing import Any

import pytest

from compiler.checking.deepseek_v4_grouped_output_executable import (
    DeepSeekV4GroupedOutputExecutableCheckError,
    verify_deepseek_v4_grouped_output_executable_deployment,
)
from compiler.vertical_slice.deepseek_v4_grouped_output_executable import (
    ENTRYPOINT,
    MANIFEST_FILENAME,
    DeepSeekV4GroupedOutputExecutableBuildError,
    build_deepseek_v4_grouped_output_executable_deployment,
)
from runtime.service_engine.secure_artifacts import canonical_json_bytes


EXPECTED_FILES = {MANIFEST_FILENAME, *ENTRYPOINT.values()}
EXPECTED_DIRECTORIES = {
    parent.as_posix()
    for path in EXPECTED_FILES
    for parent in Path(path).parents
    if parent != Path(".")
}
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
    required = (
        snapshot / "inference" / "model.py",
        lock,
        application / "canonical_application.json",
        application / "canonical_verification.json",
        application / "ranks/rank-000/layers.0.attn.wo_a.weight.bin",
        application / "ranks/rank-001/layers.0.attn.wo_a.weight.bin",
        application / "ranks/rank-002/layers.0.attn.wo_a.weight.bin",
        application / "ranks/rank-003/layers.0.attn.wo_a.weight.bin",
    )
    if not all(path.is_file() for path in required):
        return None
    return snapshot, lock, application


@pytest.fixture(scope="module")
def official_packages(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[tuple[int, int], Path], dict[tuple[int, int], dict[str, Any]]]:
    paths = _official_paths()
    if paths is None:
        pytest.skip("pinned official grouped-output evidence is unavailable")
    root = tmp_path_factory.mktemp("deepseek-v4-grouped-output-executable")
    packages: dict[tuple[int, int], Path] = {}
    reports: dict[tuple[int, int], dict[str, Any]] = {}
    for world_size, rank in ((8, 0), (1, 0)):
        package = root / f"ws{world_size}-rank{rank}"
        reports[(world_size, rank)] = (
            build_deepseek_v4_grouped_output_executable_deployment(
                *paths,
                package,
                world_size=world_size,
                rank=rank,
            )
        )
        packages[(world_size, rank)] = package
    return packages, reports


def _tree_identity(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _copy_package(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert type(value) is dict
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _reseal_artifact(package: Path, relative_path: str, payload: bytes) -> None:
    artifact_path = package / relative_path
    artifact_path.write_bytes(payload)
    manifest_path = package / MANIFEST_FILENAME
    manifest = _load_json(manifest_path)
    record = next(
        item for item in manifest["artifacts"] if item["path"] == relative_path
    )
    record["sha256"] = hashlib.sha256(payload).hexdigest()
    record["size_bytes"] = len(payload)
    core = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    _write_json(manifest_path, manifest)


def _reseal_json_mutation(
    package: Path,
    relative_path: str,
    mutation: tuple[str, ...],
    replacement: object,
) -> None:
    value = _load_json(package / relative_path)
    cursor: Any = value
    for component in mutation[:-1]:
        cursor = cursor[component]
    cursor[mutation[-1]] = replacement
    identity_fields = {
        ENTRYPOINT["logical_schedule"]: "schedule_id",
        ENTRYPOINT["logical_schedule_certificate"]: "certificate_id",
        ENTRYPOINT["resource_manifest"]: "resource_manifest_id",
    }
    identity = identity_fields.get(relative_path)
    if identity is not None:
        body = {key: child for key, child in value.items() if key != identity}
        value[identity] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    _reseal_artifact(package, relative_path, canonical_json_bytes(value))


def test_official_packages_have_exact_closure_and_repeatable_verification(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
) -> None:
    packages, reports = official_packages
    for topology, package in packages.items():
        observed_files = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file()
        }
        observed_directories = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_dir()
        }
        assert observed_files == EXPECTED_FILES
        assert observed_directories == EXPECTED_DIRECTORIES
        first = verify_deepseek_v4_grouped_output_executable_deployment(package)
        second = verify_deepseek_v4_grouped_output_executable_deployment(package)
        assert first == second == reports[topology]
        assert first["evidence_eligible"] is True
        assert first["official_evidence_certificate_id"] == (
            "57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838"
        )


def test_interfaces_use_json_schema_2020_12_tuple_validation(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
) -> None:
    package = official_packages[0][(8, 0)]
    request = _load_json(package / ENTRYPOINT["execution_request_schema"])
    result = _load_json(package / ENTRYPOINT["execution_result_schema"])
    assert request["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert result["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    input_shape = request["properties"]["input"]["properties"]["shape"]
    assert len(input_shape["prefixItems"]) == 4
    assert input_shape["items"] is False
    for output in ("grouped", "flattened"):
        shape = result["properties"]["outputs"]["properties"][output][
            "properties"
        ]["shape"]
        assert shape["items"] is False
        assert len(shape["prefixItems"]) in {3, 4}


def test_world_size_one_uses_all_four_exact_official_assignment_segments(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
) -> None:
    package = official_packages[0][(1, 0)]
    resource = _load_json(package / ENTRYPOINT["resource_manifest"])["resources"][0]
    segments = resource["segments"]
    assert len(segments) == 4
    assert [segment["assignment_rank"] for segment in segments] == [0, 1, 2, 3]
    assert [segment["byte_offset"] for segment in segments] == [0, 0, 0, 0]
    assert [segment["global_row_range"] for segment in segments] == [
        [0, 2_048],
        [2_048, 4_096],
        [4_096, 6_144],
        [6_144, 8_192],
    ]
    assert [segment["content_sha256"] for segment in segments] == [
        "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b",
        "ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016",
        "d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc",
        "0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b",
    ]
    assert sum(segment["size_bytes"] for segment in segments) == (
        resource["size_bytes"]
    )


def test_publication_is_create_once_and_preserves_existing_package(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
) -> None:
    paths = _official_paths()
    assert paths is not None
    package = official_packages[0][(8, 0)]
    before = _tree_identity(package)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableBuildError):
        build_deepseek_v4_grouped_output_executable_deployment(
            *paths,
            package,
            world_size=8,
            rank=0,
        )
    assert _tree_identity(package) == before


@pytest.mark.parametrize(
    ("artifact_key", "mutation", "replacement"),
    [
        ("logical_schedule", ("topology", "rank"), 1),
        ("logical_schedule_certificate", ("status",), "fail"),
        ("resource_manifest", ("resources",), []),
    ],
)
def test_self_consistent_json_artifact_mutations_fail_independent_check(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
    tmp_path: Path,
    artifact_key: str,
    mutation: tuple[str, ...],
    replacement: object,
) -> None:
    package = _copy_package(official_packages[0][(8, 0)], tmp_path / "package")
    _reseal_json_mutation(package, ENTRYPOINT[artifact_key], mutation, replacement)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(package)


@pytest.mark.parametrize("artifact_key", ["program", "weight"])
def test_self_consistent_binary_mutations_fail_independent_check(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
    tmp_path: Path,
    artifact_key: str,
) -> None:
    package = _copy_package(official_packages[0][(8, 0)], tmp_path / "package")
    relative_path = ENTRYPOINT[artifact_key]
    payload = bytearray((package / relative_path).read_bytes())
    payload[0] ^= 1
    _reseal_artifact(package, relative_path, bytes(payload))
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(package)


def test_self_consistent_deployment_manifest_mutation_fails(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
    tmp_path: Path,
) -> None:
    package = _copy_package(official_packages[0][(8, 0)], tmp_path / "package")
    manifest_path = package / MANIFEST_FILENAME
    manifest = _load_json(manifest_path)
    manifest["status"] = "execution_evidenced"
    core = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(package)


@pytest.mark.parametrize(
    "bad_manifest",
    [
        b'{"schema":"a","schema":"b"}',
        b'{"value":NaN}',
    ],
)
def test_noncanonical_duplicate_and_nonfinite_json_fail_closed(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
    tmp_path: Path,
    bad_manifest: bytes,
) -> None:
    package = _copy_package(official_packages[0][(8, 0)], tmp_path / "package")
    (package / MANIFEST_FILENAME).write_bytes(bad_manifest)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(package)


def test_symlink_and_manifest_path_traversal_fail_closed(
    official_packages: tuple[
        dict[tuple[int, int], Path],
        dict[tuple[int, int], dict[str, Any]],
    ],
    tmp_path: Path,
) -> None:
    source = official_packages[0][(8, 0)]
    linked = _copy_package(source, tmp_path / "linked")
    program = linked / ENTRYPOINT["program"]
    program.unlink()
    program.symlink_to("program_contract.json")
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(linked)

    traversing = _copy_package(source, tmp_path / "traversing")
    manifest_path = traversing / MANIFEST_FILENAME
    manifest = _load_json(manifest_path)
    manifest["artifacts"][0]["path"] = "../outside"
    core = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    _write_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4GroupedOutputExecutableCheckError):
        verify_deepseek_v4_grouped_output_executable_deployment(traversing)


def test_builder_has_no_synthetic_positive_or_expected_output_input() -> None:
    parameters = inspect.signature(
        build_deepseek_v4_grouped_output_executable_deployment
    ).parameters
    assert set(parameters) == {
        "snapshot_root",
        "checkpoint_lock_path",
        "application_root",
        "output_dir",
        "world_size",
        "rank",
    }
    source = Path(
        "compiler/vertical_slice/deepseek_v4_grouped_output_executable.py"
    ).read_text(encoding="utf-8")
    checker = Path(
        "compiler/checking/deepseek_v4_grouped_output_executable.py"
    ).read_text(encoding="utf-8")
    assert "allow_synthetic" not in source
    assert "placeholder_positive" not in source
    assert "expected_output" not in inspect.signature(
        build_deepseek_v4_grouped_output_executable_deployment
    ).parameters
    assert "compiler.vertical_slice" not in checker
    assert "expected_output" not in checker
