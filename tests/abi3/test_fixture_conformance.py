"""The Phase-B conformance gate for the ABI 3.0 fixture and its checker.

The fixture exists so the encoder, the digest binding and the admission proofs
can be exercised end to end without a model.  This module is the gate itself:

* the fixture builds through both storage classes, HBM and immutable ROM;
* two clean builds of the same storage class are byte-identical, so a rebuild
  proves nothing changed rather than merely that nothing crashed;
* both builds are admitted by the verifier and by the independent checker;
* the compiled instruction stream does not depend on the storage class, which is
  the property the ROM-versus-HBM comparison protocol rests on;
* a disk round-trip preserves every digest; and
* each of nine corruption classes is rejected.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import (
    NO_ID,
    PROGRAM_HEADER_BYTES,
    Permission,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment, DeploymentError
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.records import ProgramHeader, decode_body, split_program
from runtime.abi3.verifier import verify_deployment

from . import CHECKER, ROOT

STORAGE_CLASSES = [StorageClass.HBM, StorageClass.ROM]


@pytest.fixture(scope="module")
def capability() -> Any:
    return fixture_capability()


def publish(deployment: Deployment, root: Path, capability: Any) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    deployment.write(root)
    (root.parent / "capability.json").write_bytes(canonical_json(capability.to_dict()))
    return root


def run_checker(root: Path, capability_path: Path) -> tuple[int, dict[str, Any]]:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--deployment",
            str(root),
            "--capability",
            str(capability_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


# ---------------------------------------------------------------------------
# build, determinism, admission
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_the_fixture_builds_through_each_storage_class(
    storage_class: StorageClass, capability: Any
) -> None:
    deployment = build_fixture(storage_class=storage_class, capability=capability)
    header, body = split_program(deployment.program)
    assert header.instruction_count * 32 == len(body)
    assert len(deployment.table) > 0
    weights = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and d.payload["storage_class"] == int(storage_class)
    ]
    assert weights, f"no memory object uses {storage_class.name}"


@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_two_clean_builds_are_byte_identical(
    storage_class: StorageClass, capability: Any
) -> None:
    first = build_fixture(storage_class=storage_class, capability=capability)
    second = build_fixture(storage_class=storage_class, capability=capability)
    assert first.program == second.program
    assert first.table.encode() == second.table.encode()
    assert canonical_json(first.manifest()) == canonical_json(second.manifest())
    assert first.deployment_digest == second.deployment_digest


@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_both_storage_classes_are_admitted(
    storage_class: StorageClass, capability: Any
) -> None:
    deployment = build_fixture(storage_class=storage_class, capability=capability)
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    assert all(report.checks.values()), report.checks


def test_the_instruction_stream_does_not_depend_on_the_storage_class(
    capability: Any,
) -> None:
    """The ROM and HBM builds must compile to the same program.

    The full ``program.bin`` cannot be identical -- the header binds the
    deployment and descriptor-table digests, and those legitimately differ
    because the weight object names a different storage class -- so the check is
    that the *authenticated body* and every other header field agree.
    """
    hbm = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    rom = build_fixture(storage_class=StorageClass.ROM, capability=capability)
    assert hbm.program[PROGRAM_HEADER_BYTES:] == rom.program[PROGRAM_HEADER_BYTES:]
    assert decode_body(hbm.program[PROGRAM_HEADER_BYTES:]) == decode_body(
        rom.program[PROGRAM_HEADER_BYTES:]
    )
    left = ProgramHeader.decode(hbm.program[:PROGRAM_HEADER_BYTES])
    right = ProgramHeader.decode(rom.program[:PROGRAM_HEADER_BYTES])
    differing = {
        name
        for name in left.__slots__
        if getattr(left, name) != getattr(right, name)
    }
    assert differing == {"deployment_digest", "descriptor_table_digest"}, differing
    assert left.body_digest == right.body_digest
    assert left.max_retired_work == right.max_retired_work
    assert left.required_features == right.required_features


def test_the_two_builds_differ_only_where_the_storage_class_forces_it(
    capability: Any,
) -> None:
    hbm = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    rom = build_fixture(storage_class=StorageClass.ROM, capability=capability)
    assert len(hbm.table) == len(rom.table)
    differing = [
        index
        for index in range(len(hbm.table))
        if hbm.table[index].encode() != rom.table[index].encode()
    ]
    assert len(differing) == 1, differing
    changed = hbm.table[differing[0]]
    assert changed.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
    assert hbm.table[differing[0]].payload["storage_class"] == int(StorageClass.HBM)
    assert rom.table[differing[0]].payload["storage_class"] == int(StorageClass.ROM)


def test_the_rom_build_keeps_its_weights_immutable(capability: Any) -> None:
    rom = build_fixture(storage_class=StorageClass.ROM, capability=capability)
    for descriptor in rom.table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.MEMORY_OBJECT):
            continue
        if descriptor.payload["storage_class"] != int(StorageClass.ROM):
            continue
        assert descriptor.permissions & Permission.IMMUTABLE
        assert not descriptor.permissions & Permission.WRITE


# ---------------------------------------------------------------------------
# disk round trip
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_a_disk_round_trip_preserves_every_digest(
    storage_class: StorageClass, capability: Any, tmp_path: Path
) -> None:
    built = build_fixture(storage_class=storage_class, capability=capability)
    root = built.write(tmp_path / "bundle")
    read = Deployment.read(root)
    assert read.program == built.program
    assert read.table.encode() == built.table.encode()
    assert read.deployment_digest == built.deployment_digest
    assert canonical_json(read.manifest()) == canonical_json(built.manifest())
    manifest = json.loads((root / "deployment.json").read_text())
    assert manifest["deployment_sha256"] == built.deployment_digest.hex()
    assert manifest["program_sha256"] == built.manifest()["program_sha256"]
    report = verify_deployment(read, capability)
    assert report.admitted, report.errors


def test_writing_twice_produces_identical_files(
    capability: Any, tmp_path: Path
) -> None:
    for run in ("first", "second"):
        build_fixture(
            storage_class=StorageClass.HBM, capability=capability
        ).write(tmp_path / run)
    for name in ("deployment.json", "descriptors.bin", "program.bin"):
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes(), name


# ---------------------------------------------------------------------------
# corruption classes
# ---------------------------------------------------------------------------
def flip(path: Path, index: int) -> None:
    blob = bytearray(path.read_bytes())
    blob[index] ^= 0xFF
    path.write_bytes(bytes(blob))


def edit_manifest(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    manifest = json.loads(path.read_text())
    mutate(manifest)
    path.write_bytes(canonical_json(manifest))


def corrupt_program_header(root: Path) -> None:
    flip(root / "program.bin", 20)


def corrupt_program_magic(root: Path) -> None:
    flip(root / "program.bin", 1)


def corrupt_instruction(root: Path) -> None:
    flip(root / "program.bin", PROGRAM_HEADER_BYTES + 8)


def truncate_program(root: Path) -> None:
    blob = (root / "program.bin").read_bytes()
    (root / "program.bin").write_bytes(blob[:-32])


def corrupt_descriptor(root: Path) -> None:
    flip(root / "descriptors.bin", 70)


def truncate_descriptors(root: Path) -> None:
    blob = (root / "descriptors.bin").read_bytes()
    (root / "descriptors.bin").write_bytes(blob[:-64])


def unbind_table_digest(root: Path) -> None:
    edit_manifest(
        root / "deployment.json",
        lambda m: m.__setitem__("descriptor_table_sha256", "00" * 32),
    )


def unbind_program_digest(root: Path) -> None:
    edit_manifest(
        root / "deployment.json", lambda m: m.__setitem__("program_sha256", "00" * 32)
    )


def rewrite_object_source(root: Path) -> None:
    def mutate(manifest: dict[str, Any]) -> None:
        manifest["objects"][0]["source"]["size_bytes"] += 64

    edit_manifest(root / "deployment.json", mutate)


def rewrite_manifest_identity(root: Path) -> None:
    edit_manifest(
        root / "deployment.json", lambda m: m.__setitem__("model_id", "not-the-fixture")
    )


def drop_deployment_digest(root: Path) -> None:
    edit_manifest(
        root / "deployment.json", lambda m: m.__setitem__("deployment_sha256", "11" * 32)
    )


CORRUPTIONS: dict[str, Callable[[Path], None]] = {
    "program_header_byte": corrupt_program_header,
    "program_magic": corrupt_program_magic,
    "instruction_byte": corrupt_instruction,
    "program_truncated": truncate_program,
    "descriptor_byte": corrupt_descriptor,
    "descriptor_table_truncated": truncate_descriptors,
    "manifest_table_digest": unbind_table_digest,
    "manifest_program_digest": unbind_program_digest,
    "manifest_object_source": rewrite_object_source,
    "manifest_identity": rewrite_manifest_identity,
    "manifest_deployment_digest": drop_deployment_digest,
}


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory, capability: Any) -> Path:
    base = tmp_path_factory.mktemp("fixture-bundle")
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    publish(deployment, base / "deployment", capability)
    return base


def test_at_least_six_corruption_classes_are_covered() -> None:
    assert len(CORRUPTIONS) >= 6


@pytest.mark.parametrize("name", sorted(CORRUPTIONS))
def test_a_corrupted_bundle_is_rejected(
    name: str, published: Path, tmp_path: Path
) -> None:
    root = tmp_path / "deployment"
    shutil.copytree(published / "deployment", root)
    shutil.copy(published / "capability.json", tmp_path / "capability.json")
    assert Deployment.read(root) is not None  # the clean copy still reads
    CORRUPTIONS[name](root)
    with pytest.raises((DeploymentError, ValueError)):
        Deployment.read(root)
    status, report = run_checker(root, tmp_path / "capability.json")
    assert status == 1, report
    assert report["admitted"] is False
    assert report["errors"], report


def test_a_capability_that_does_not_match_is_rejected(capability: Any) -> None:
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    other = fixture_capability(TopologyClass.CLUSTER_32)
    report = verify_deployment(deployment, other)
    assert not report.admitted
    assert any("compiled against capability" in error for error in report.errors)


# ---------------------------------------------------------------------------
# the independent checker
# ---------------------------------------------------------------------------
def test_the_checker_does_not_import_the_builder_or_the_verifier() -> None:
    """The checker must be a second opinion, not the encoder read backwards."""
    source = CHECKER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules.add(node.module or "")
    assert "runtime.abi3.builder" not in modules
    assert "runtime.abi3.verifier" not in modules
    assert "runtime.abi3.fixture" not in modules
    assert not any(module.split(".")[0] == "compiler" for module in modules), modules
    assert "from .builder import" not in source
    assert "runtime.abi3.builder" not in source.replace(
        "runtime/abi3/builder.py", ""
    ).replace("``runtime.abi3.builder``", "")


def test_importing_the_checker_does_not_pull_in_the_builder() -> None:
    """Transitive imports count: a checker that loads the encoder indirectly is
    still exposed to the encoder's mistakes."""
    program = (
        "import importlib.util, sys;"
        f"spec = importlib.util.spec_from_file_location('checker', r'{CHECKER}');"
        "module = importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(module);"
        "print(int('runtime.abi3.builder' in sys.modules),"
        "      int('runtime.abi3.verifier' in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["0", "0"], result.stdout


@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_the_checker_admits_the_fixture(
    storage_class: StorageClass, capability: Any, tmp_path: Path
) -> None:
    deployment = build_fixture(storage_class=storage_class, capability=capability)
    root = publish(deployment, tmp_path / "deployment", capability)
    status, report = run_checker(root, tmp_path / "capability.json")
    assert status == 0, report
    assert report["admitted"] is True
    assert report["errors"] == []
    assert report["warnings"] == [], report["warnings"]
    assert all(report["checks"].values()), report["checks"]


@pytest.mark.parametrize("storage_class", STORAGE_CLASSES)
def test_the_checker_and_the_verifier_agree(
    storage_class: StorageClass, capability: Any, tmp_path: Path
) -> None:
    deployment = build_fixture(storage_class=storage_class, capability=capability)
    root = publish(deployment, tmp_path / "deployment", capability)
    _, report = run_checker(root, tmp_path / "capability.json")
    verified = verify_deployment(deployment, capability)
    assert report["admitted"] == verified.admitted
    assert report["program"]["proved_retired_work"] == verified.proved_retired_work
    assert report["program"]["declared_retired_work"] == verified.declared_retired_work
    assert report["program"]["loop_depth"] == verified.loop_depth
    assert report["program"]["event_count"] == verified.event_count
    assert report["program"]["state_resources"] == verified.state_resources
    assert report["program"]["descriptor_count"] == verified.descriptor_count
    assert report["program"]["instruction_count"] == verified.instruction_count


def test_the_checker_report_is_canonical_and_reproducible(
    capability: Any, tmp_path: Path
) -> None:
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    root = publish(deployment, tmp_path / "deployment", capability)
    outputs = []
    for run in range(2):
        target = tmp_path / f"report-{run}.json"
        subprocess.run(
            [
                sys.executable,
                str(CHECKER),
                "--deployment",
                str(root),
                "--capability",
                str(tmp_path / "capability.json"),
                "--output",
                str(target),
                "--quiet",
            ],
            check=True,
            cwd=str(ROOT),
        )
        outputs.append(target.read_bytes())
    assert outputs[0] == outputs[1]
    body = json.loads(outputs[0])
    assert canonical_json(body) == outputs[0]
    assert body["schema"] == "opentallas.abi3.legality_report.v1"
    assert body["digests"]["deployment_sha256"] == deployment.deployment_digest.hex()


def test_the_checker_rejects_a_deployment_it_cannot_find(tmp_path: Path) -> None:
    capability = fixture_capability()
    (tmp_path / "capability.json").write_bytes(canonical_json(capability.to_dict()))
    status, report = run_checker(tmp_path / "missing", tmp_path / "capability.json")
    assert status == 1
    assert report["admitted"] is False
    assert any("missing" in error for error in report["errors"])


def test_the_checker_rejects_an_unusable_capability(
    capability: Any, tmp_path: Path
) -> None:
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    root = publish(deployment, tmp_path / "deployment", capability)
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"schema": "not-a-capability"}))
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--deployment",
            str(root),
            "--capability",
            str(broken),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 2
    assert "capability is unusable" in result.stderr


def test_the_checker_rejects_a_capability_that_is_too_small(
    capability: Any, tmp_path: Path
) -> None:
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    root = publish(deployment, tmp_path / "deployment", capability)
    body = capability.to_dict()
    body["limits"]["max_instructions"] = 2
    (tmp_path / "small.json").write_bytes(canonical_json(body))
    status, report = run_checker(root, tmp_path / "small.json")
    assert status == 1
    assert any("capability admits 2" in error for error in report["errors"])
    assert report["checks"]["instruction_bound"] is False


def test_the_checker_proves_the_write_path_the_verifier_leaves_open(
    capability: Any, tmp_path: Path
) -> None:
    """A cross-check with teeth.

    ``runtime/abi3/verifier.py`` claims 'no engine output into a read-only
    object' but never inspects an OPERATOR's output views, so a deployment that
    writes its matmul result into the immutable weight object is admitted.  The
    independent checker makes that proof, which is exactly the kind of
    disagreement an independent checker exists to surface.
    """
    deployment = build_fixture(storage_class=StorageClass.ROM, capability=capability)
    table = deployment.table
    weight_view = next(
        d.descriptor_id
        for d in table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.TENSOR_VIEW)
        and table[d.primary_object_id].payload["storage_class"] == int(StorageClass.ROM)
    )
    matmul = next(
        d
        for d in table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.OPERATOR)
        and d.payload["output_view_0"] != NO_ID
    )
    from . import patched_payload, restamp
    from runtime.abi3.descriptors import OPERATOR_PAYLOAD

    deployment.table = patched_payload(
        table, matmul.descriptor_id, OPERATOR_PAYLOAD, "output_view_0", weight_view
    )
    restamp(deployment)
    # The verifier's verdict is recorded rather than asserted: whether the gap
    # is still open is tracked by the strict xfail in test_verifier.py, and this
    # test must keep passing either way.
    verifier_admits = verify_deployment(deployment, capability).admitted
    root = publish(deployment, tmp_path / "deployment", capability)
    status, report = run_checker(root, tmp_path / "capability.json")
    assert status == 1
    assert report["checks"]["engine_write_paths"] is False
    assert any("ROM object" in error for error in report["errors"]), report["errors"]
    if verifier_admits:
        # the disagreement this checker exists to surface
        assert verify_deployment(deployment, capability).errors == []
