from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import compiler.checking.deepseek_v4_hc_pre_input as input_checker_module
import compiler.vertical_slice.deepseek_v4_hc_pre_input as input_builder_module
from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_hc_pre_input import (
    DeepSeekV4HCPreInputCheckError,
    verify_deepseek_v4_hc_pre_input_composition,
)
from compiler.checking.deepseek_v4_lookup_execution import (
    verify_deepseek_v4_lookup_execution,
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
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    BASE_NAME,
    PROJECTION_NAME,
    SCALE_NAME,
)
from compiler.vertical_slice.deepseek_v4_hc_pre_executable import (
    build_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.vertical_slice.deepseek_v4_hc_pre_input import (
    DeepSeekV4HCPreInputBuildError,
    build_deepseek_v4_hc_pre_input_request,
)
from compiler.vertical_slice.deepseek_v4_lookup import (
    build_deepseek_v4_lookup_deployment,
)
from runtime.service_engine.deepseek_v4_lookup import DeepSeekV4LookupServiceEngine


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (
    ROOT / "schemas/compiler/deepseek_v4_hc_pre_input/composition_report_v1.schema.json"
)
FIXTURE_REVISION = "89abcdef0123456789abcdef0123456789abcdef"
OFFICIAL_SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_SNAPSHOT"
OFFICIAL_EVIDENCE_ENV = "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT"


class _StringSubclass(str):
    pass


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


def _identity_output(
    name: str,
    *,
    rank: int,
    shape: list[int],
    storage_dtype: str,
    logical_dtype: str,
    source_slice: dict[str, int] | None,
) -> dict[str, Any]:
    bits = {"BF16": 16, "F32": 32, "I64": 64}[storage_dtype]
    elements = 1
    for extent in shape:
        elements *= extent
    return {
        "logical_dtype": logical_dtype,
        "name": name,
        "payload_bytes": elements * bits // 8,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": shape,
        "source_slice": source_slice,
        "storage_dtype": storage_dtype,
        "transform": "identity",
    }


def _lookup_plan() -> list[dict[str, Any]]:
    hidden = 4096
    vocabulary = 8
    return [
        {
            "action": "tensor_parallel_slice_axis_0",
            "logical_dtype": "BF16",
            "name": "embed.weight",
            "outputs": [
                _identity_output(
                    "embed.weight",
                    rank=rank,
                    shape=[vocabulary // 2, hidden],
                    storage_dtype="BF16",
                    logical_dtype="BF16",
                    source_slice={
                        "axis": 0,
                        "start": rank * vocabulary // 2,
                        "stop": (rank + 1) * vocabulary // 2,
                    },
                )
                for rank in range(2)
            ],
            "semantic_role": "model.token_embedding.weight",
            "shape": [vocabulary, hidden],
            "size_bytes": vocabulary * hidden * 2,
            "storage_dtype": "BF16",
        },
        {
            "action": "replicate_identity",
            "logical_dtype": "INT64",
            "name": "layers.0.ffn.gate.tid2eid",
            "outputs": [
                _identity_output(
                    "layers.0.ffn.gate.tid2eid",
                    rank=rank,
                    shape=[vocabulary, 2],
                    storage_dtype="I64",
                    logical_dtype="INT64",
                    source_slice=None,
                )
                for rank in range(2)
            ],
            "semantic_role": "moe.hash_route.table",
            "shape": [vocabulary, 2],
            "size_bytes": vocabulary * 2 * 8,
            "storage_dtype": "I64",
        },
    ]


def _hc_pre_plan() -> list[dict[str, Any]]:
    shapes = {
        BASE_NAME: [24],
        PROJECTION_NAME: [24, 16384],
        SCALE_NAME: [3],
    }
    roles = {
        BASE_NAME: "hyper_connection.attn.base",
        PROJECTION_NAME: "hyper_connection.attn.projection",
        SCALE_NAME: "hyper_connection.attn.scale",
    }
    result: list[dict[str, Any]] = []
    for name in (BASE_NAME, PROJECTION_NAME, SCALE_NAME):
        shape = shapes[name]
        elements = 1
        for extent in shape:
            elements *= extent
        result.append(
            {
                "action": "replicate_identity",
                "logical_dtype": "FP32",
                "name": name,
                "outputs": [
                    _identity_output(
                        name,
                        rank=rank,
                        shape=shape,
                        storage_dtype="F32",
                        logical_dtype="FP32",
                        source_slice=None,
                    )
                    for rank in range(4)
                ],
                "semantic_role": roles[name],
                "shape": shape,
                "size_bytes": elements * 4,
                "storage_dtype": "F32",
            }
        )
    return result


def _finite_f32(element_count: int, seed: int) -> bytes:
    patterns = (
        (0x00000000, 0x80000000, 0x3F800000, 0xBF000000),
        (0x3EAAAAAB, 0x3DCCCCCD, 0x00800000, 0x007FFFFF),
        (0x40000000, 0xC0000000, 0x00000001, 0x3F000000),
    )
    block = struct.pack("<4I", *patterns[seed % len(patterns)])
    return (block * ((element_count + 3) // 4))[: element_count * 4]


@pytest.fixture(scope="module")
def composition_fixture(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("hc-pre-input-source")
    snapshot = root / "snapshot"
    snapshot.mkdir()
    hidden = 4096
    embedding_codes = tuple(
        0x3E00 + ((row * 17 + column) % 0x100)
        for row in range(8)
        for column in range(hidden)
    )
    route_values = tuple(
        value for row in range(8) for value in (row % 5, (row + 2) % 5)
    )
    hc_shapes = {
        BASE_NAME: [24],
        PROJECTION_NAME: [24, 16384],
        SCALE_NAME: [3],
    }
    tensors: list[tuple[str, str, list[int], bytes]] = [
        (
            "embed.weight",
            "BF16",
            [8, hidden],
            struct.pack(f"<{len(embedding_codes)}H", *embedding_codes),
        ),
        (
            "layers.0.ffn.gate.tid2eid",
            "I64",
            [8, 2],
            struct.pack("<16q", *route_values),
        ),
    ]
    for index, (name, shape) in enumerate(hc_shapes.items()):
        elements = 1
        for extent in shape:
            elements *= extent
        tensors.append((name, "F32", shape, _finite_f32(elements, index)))
    shard = _safetensors(tensors)
    checkpoint_files = {
        "config.json": canonical_json_bytes({"architectures": ["HCPreInputFixture"]}),
        "model.safetensors": shard,
        "model.safetensors.index.json": canonical_json_bytes(
            {
                "metadata": {"total_size": sum(len(record[3]) for record in tensors)},
                "weight_map": {name: "model.safetensors" for name, _, _, _ in tensors},
            }
        ),
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
            "repository": "OpenTallas/deepseek-v4-hc-pre-input-fixture",
            "required_files": ["config.json"],
            "revision": FIXTURE_REVISION,
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    lookup_plan = _lookup_plan()
    lookup_application = root / "lookup-canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(lookup_plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_hc_pre_input_lookup_fixture.v1",
        plan_inputs=lookup_plan,
        output=lookup_application,
    )
    hc_plan = _hc_pre_plan()
    executable_application = root / "hc-pre-canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(hc_plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_hc_pre_input_parameter_fixture.v1",
        plan_inputs=hc_plan,
        output=executable_application,
    )
    lookup_deployment = root / "lookup-deployment"
    build_deepseek_v4_lookup_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=lookup_application,
        output=lookup_deployment,
        hc_multiplier=4,
        expert_count=5,
    )
    executable_deployment = root / "hc-pre-executable"
    build_deepseek_v4_hc_pre_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=executable_application,
        output=executable_deployment,
    )
    request = root / "lookup-request.json"
    lookup_manifest = load_strict_json(lookup_deployment / "deployment_manifest.json")
    write_canonical_json(
        request,
        {
            "build_id": lookup_manifest["build_id"],
            "model_id": "deepseek-v4-flash-0731",
            "schema": "opentallas.deepseek_v4_lookup_request.v1",
            "token_ids": [[0, 3], [4, 7]],
        },
    )
    result = root / "lookup-result.json"
    write_canonical_json(
        result,
        DeepSeekV4LookupServiceEngine.load(lookup_deployment).execute(request),
    )
    differential = root / "lookup-differential.json"
    write_canonical_json(
        differential,
        verify_deepseek_v4_lookup_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=lookup_deployment,
            request_path=request,
            result_path=result,
        ),
    )
    return {
        "differential": differential,
        "executable_application": executable_application,
        "executable_deployment": executable_deployment,
        "lock": lock,
        "lookup_deployment": lookup_deployment,
        "request": request,
        "result": result,
        "snapshot": snapshot,
        "source_texts": ["development row zero", "development row one"],
    }


def _arguments(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot": source["snapshot"],
        "lock": source["lock"],
        "lookup_deployment_root": source["lookup_deployment"],
        "lookup_request_path": source["request"],
        "lookup_result_path": source["result"],
        "lookup_differential_path": source["differential"],
        "executable_deployment_root": source["executable_deployment"],
        "executable_application_root": source["executable_application"],
        "source_texts": source["source_texts"],
    }


def _build(source: dict[str, Any], output: Path, report: Path) -> dict[str, Any]:
    return build_deepseek_v4_hc_pre_input_request(
        **_arguments(source), output=output, report_output=report
    )


def _verify(source: dict[str, Any], output: Path, report: Path) -> dict[str, Any]:
    return verify_deepseek_v4_hc_pre_input_composition(
        **_arguments(source), request_root=output, report_path=report
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _copy_case(
    source: dict[str, Any], tmp_path: Path, *, copy_lookup: bool = False
) -> dict[str, Any]:
    case = dict(source)
    for key in ("request", "result", "differential"):
        destination = tmp_path / source[key].name
        shutil.copyfile(source[key], destination)
        case[key] = destination
    if copy_lookup:
        lookup = tmp_path / "lookup-deployment"
        shutil.copytree(source["lookup_deployment"], lookup)
        case["lookup_deployment"] = lookup
    return case


def test_composition_schema_is_strict_draft_2020_12() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def test_development_composition_is_deterministic_closed_and_independently_verified(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    first = tmp_path / "first-request"
    first_report = tmp_path / "first-report.json"
    second = tmp_path / "second-request"
    second_report = tmp_path / "second-report.json"
    report = _build(composition_fixture, first, first_report)
    replay = _build(composition_fixture, second, second_report)

    assert report == replay == load_strict_json(first_report)
    assert _tree(first) == _tree(second)
    assert first_report.read_bytes() == second_report.read_bytes()
    assert set(_tree(first)) == {"input/hc_hidden.bf16le", "request_manifest.json"}
    manifest = load_strict_json(first / "request_manifest.json")
    assert manifest["input"]["shape"] == [2, 2, 4, 4096]
    assert manifest["token_count"] == 4
    assert manifest["input"]["size_bytes"] == 131072
    assert (
        manifest["input"]["sha256"]
        == hashlib.sha256((first / "input/hc_hidden.bf16le").read_bytes()).hexdigest()
    )
    assert report["status"] == (
        "development_fixture_lookup_differential_composition_not_release_evidence"
    )
    assert report["tokenizer"]["encode_equivalence"] == (
        "not_available_development_fixture"
    )
    assert report["tokenizer"]["token_ids"] == [[0, 3], [4, 7]]
    assert report["tokenizer"]["tokenizer_validation_id"] is None
    serialized = first_report.read_text(encoding="utf-8")
    assert "development row zero" not in serialized
    assert "development row one" not in serialized
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        report
    )
    integrity = _verify(composition_fixture, first, first_report)
    assert integrity == {
        "composition_id": report["composition_id"],
        "input_sha256": manifest["input"]["sha256"],
        "request_sha256": report["request"]["request_sha256"],
        "status": report["status"],
        "token_count": 4,
    }


def test_composer_packs_exact_little_endian_lookup_codes(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    output = tmp_path / "request"
    _build(composition_fixture, output, tmp_path / "report.json")
    lookup_result = load_strict_json(composition_fixture["result"])
    hc = next(
        record
        for record in lookup_result["outputs"]
        if record["id"] == "hc_hidden_bf16_codes"
    )
    flattened = [
        code
        for batch in hc["values"]
        for position in batch
        for copies in position
        for code in copies
    ]
    assert (output / "input/hc_hidden.bf16le").read_bytes() == struct.pack(
        f"<{len(flattened)}H", *flattened
    )


@pytest.mark.parametrize("replacement", [True, 1.0, -1, 129280])
def test_token_type_aliases_and_range_violations_fail_closed(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    replacement: object,
) -> None:
    case = _copy_case(composition_fixture, tmp_path)
    request = load_strict_json(case["request"])
    request["token_ids"][0][0] = replacement
    write_canonical_json(case["request"], request)
    with pytest.raises(
        DeepSeekV4HCPreInputBuildError, match="token|request|differential"
    ):
        _build(case, tmp_path / "output", tmp_path / "report.json")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "mutation, match",
    [
        ("nonfinite", "non-finite BF16"),
        ("one_bit", "differential|locked checkpoint"),
        ("wrong_shape", "metadata differs"),
        ("wrong_build", "identity|build"),
        ("wrong_status", "identity|status"),
    ],
)
def test_lookup_result_mutations_fail_before_publication(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    case = _copy_case(composition_fixture, tmp_path)
    result = load_strict_json(case["result"])
    hc = next(
        record for record in result["outputs"] if record["id"] == "hc_hidden_bf16_codes"
    )
    if mutation == "nonfinite":
        hc["values"][0][0][0][0] = 0x7F80
    elif mutation == "one_bit":
        hc["values"][0][0][0][0] ^= 1
    elif mutation == "wrong_shape":
        hc["shape"] = [2, 2, 4, 4095]
    elif mutation == "wrong_build":
        result["build_id"] = "0" * 64
    else:
        result["deployment_status"] = "forged"
    write_canonical_json(case["result"], result)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match=match):
        _build(case, tmp_path / "output", tmp_path / "report.json")
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / "report.json").exists()


@pytest.mark.parametrize("invalid_code", [True, 1.0, -1, 65536])
def test_bf16_code_type_aliases_and_range_violations_fail_closed(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    invalid_code: object,
) -> None:
    case = _copy_case(composition_fixture, tmp_path)
    result = load_strict_json(case["result"])
    hc = next(
        record for record in result["outputs"] if record["id"] == "hc_hidden_bf16_codes"
    )
    hc["values"][0][0][0][0] = invalid_code
    write_canonical_json(case["result"], result)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="integer"):
        _build(case, tmp_path / "output", tmp_path / "report.json")
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / "report.json").exists()


def test_more_than_four_tokens_and_nonrectangular_batches_fail_closed(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    for index, token_ids in enumerate(([[0, 1, 2], [3, 4, 5]], [[0], [1, 2]])):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        case = _copy_case(composition_fixture, case_root)
        request = load_strict_json(case["request"])
        request["token_ids"] = token_ids
        write_canonical_json(case["request"], request)
        with pytest.raises(DeepSeekV4HCPreInputBuildError, match="token|rectangular"):
            _build(case, case_root / "output", case_root / "report.json")


def test_retained_differential_and_lookup_artifact_mutations_fail_closed(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    differential_case_root = tmp_path / "differential-case"
    differential_case_root.mkdir()
    differential_case = _copy_case(composition_fixture, differential_case_root)
    differential = load_strict_json(differential_case["differential"])
    differential["token_ids_sha256"] = "0" * 64
    write_canonical_json(differential_case["differential"], differential)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="differential"):
        _build(
            differential_case,
            differential_case_root / "output",
            differential_case_root / "report.json",
        )

    artifact_case_root = tmp_path / "artifact-case"
    artifact_case_root.mkdir()
    artifact_case = _copy_case(
        composition_fixture, artifact_case_root, copy_lookup=True
    )
    microcode = artifact_case["lookup_deployment"] / "microcode.bin"
    payload = bytearray(microcode.read_bytes())
    payload[-1] ^= 1
    microcode.write_bytes(payload)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="artifact"):
        _build(
            artifact_case,
            artifact_case_root / "output",
            artifact_case_root / "report.json",
        )


def test_wrong_executable_build_and_noncanonical_request_fail_closed(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    executable_root = tmp_path / "executable-case"
    executable_root.mkdir()
    executable_case = _copy_case(composition_fixture, executable_root)
    executable = executable_root / "hc-pre-executable"
    shutil.copytree(composition_fixture["executable_deployment"], executable)
    executable_case["executable_deployment"] = executable
    manifest_path = executable / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["build_id"] = "0" * 64
    write_canonical_json(manifest_path, manifest)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="executable|build"):
        _build(
            executable_case,
            executable_root / "output",
            executable_root / "report.json",
        )

    canonical_root = tmp_path / "canonical-case"
    canonical_root.mkdir()
    canonical_case = _copy_case(composition_fixture, canonical_root)
    canonical_case["request"].write_bytes(
        canonical_case["request"].read_bytes().rstrip(b"\n") + b" \n"
    )
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="canonical JSON"):
        _build(
            canonical_case,
            canonical_root / "output",
            canonical_root / "report.json",
        )


def test_request_payload_manifest_report_and_tree_mutations_are_detected(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    for case_name in ("payload", "manifest", "report", "extra"):
        case_root = tmp_path / case_name
        case_root.mkdir()
        output = case_root / "request"
        report = case_root / "report.json"
        _build(composition_fixture, output, report)
        if case_name == "payload":
            path = output / "input/hc_hidden.bf16le"
            payload = bytearray(path.read_bytes())
            payload[0] ^= 1
            path.write_bytes(payload)
        elif case_name == "manifest":
            manifest = load_strict_json(output / "request_manifest.json")
            manifest["token_count"] = 3
            write_canonical_json(output / "request_manifest.json", manifest)
        elif case_name == "report":
            provenance = load_strict_json(report)
            provenance["lookup"]["result_sha256"] = "0" * 64
            write_canonical_json(report, provenance)
        else:
            (output / "unexpected.bin").write_bytes(b"unexpected")
        with pytest.raises(DeepSeekV4HCPreInputCheckError):
            _verify(composition_fixture, output, report)


def test_request_special_files_are_rejected_without_blocking(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    for kind in ("symlink", "fifo"):
        case_root = tmp_path / kind
        case_root.mkdir()
        output = case_root / "request"
        report = case_root / "report.json"
        _build(composition_fixture, output, report)
        input_path = output / "input/hc_hidden.bf16le"
        input_path.unlink()
        if kind == "symlink":
            input_path.symlink_to(composition_fixture["request"])
            match = "following symlinks"
        else:
            os.mkfifo(input_path)
            match = "regular file"
        with pytest.raises(DeepSeekV4HCPreInputCheckError, match=match):
            _verify(composition_fixture, output, report)


def test_source_text_rows_are_type_sensitive_and_hash_bound(
    composition_fixture: dict[str, Any], tmp_path: Path
) -> None:
    output = tmp_path / "request"
    report = tmp_path / "report.json"
    _build(composition_fixture, output, report)
    wrong = dict(composition_fixture)
    wrong["source_texts"] = ["development row zero!", "development row one"]
    with pytest.raises(DeepSeekV4HCPreInputCheckError, match="report differs"):
        _verify(wrong, output, report)
    for invalid in (
        "scalar string",
        ["one row only"],
        ["first", 1],
        ["first", _StringSubclass("second")],
    ):
        case = dict(composition_fixture)
        case["source_texts"] = invalid
        with pytest.raises(DeepSeekV4HCPreInputBuildError, match="source_texts"):
            _build(
                case,
                tmp_path / f"bad-{len(str(invalid))}",
                tmp_path / f"bad-{len(str(invalid))}.json",
            )


def test_symlink_fifo_device_oversize_and_replacement_evidence_are_rejected(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symlink_case_root = tmp_path / "symlink"
    symlink_case_root.mkdir()
    symlink_case = _copy_case(composition_fixture, symlink_case_root)
    symlink_case["request"].unlink()
    symlink_case["request"].symlink_to(composition_fixture["request"])
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="following symlinks"):
        _build(symlink_case, symlink_case_root / "out", symlink_case_root / "report")

    fifo_case_root = tmp_path / "fifo"
    fifo_case_root.mkdir()
    fifo_case = _copy_case(composition_fixture, fifo_case_root)
    fifo_case["result"].unlink()
    os.mkfifo(fifo_case["result"])
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="regular file"):
        _build(fifo_case, fifo_case_root / "out", fifo_case_root / "report")

    device_case = dict(composition_fixture)
    device_case["differential"] = Path("/dev/null")
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="regular file"):
        _build(device_case, tmp_path / "device-out", tmp_path / "device-report")

    oversize = tmp_path / "oversize.json"
    oversize.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    oversize_case = dict(composition_fixture)
    oversize_case["request"] = oversize
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="exceeds"):
        _build(oversize_case, tmp_path / "oversize-out", tmp_path / "oversize-report")

    replacement_root = tmp_path / "replacement"
    replacement_root.mkdir()
    replacement_case = _copy_case(composition_fixture, replacement_root)
    original_read = input_checker_module._read_file
    replaced = False

    def replacing_read(source, label: str, maximum: int) -> bytes:
        nonlocal replaced
        payload = original_read(source, label, maximum)
        if label == "lookup request" and not replaced:
            replacement = replacement_root / "replacement.json"
            replacement.write_bytes(payload)
            os.replace(replacement, replacement_case["request"])
            replaced = True
        return payload

    monkeypatch.setattr(input_checker_module, "_read_file", replacing_read)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="changed|replaced"):
        _build(
            replacement_case,
            replacement_root / "out",
            replacement_root / "report",
        )


def test_existing_outputs_late_failure_and_publication_race_do_not_overwrite(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="already exists"):
        _build(composition_fixture, existing, tmp_path / "unused-report")
    nested_output = tmp_path / "nested-output"
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="outside"):
        _build(
            composition_fixture,
            nested_output,
            nested_output / "composition.json",
        )
    assert not nested_output.exists()

    late_root = tmp_path / "late"
    late_root.mkdir()

    def fail_verification(**_: Any) -> dict[str, Any]:
        raise DeepSeekV4HCPreInputCheckError("injected late verification failure")

    monkeypatch.setattr(
        input_builder_module,
        "verify_deepseek_v4_hc_pre_input_composition",
        fail_verification,
    )
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="late verification"):
        _build(
            composition_fixture,
            late_root / "output",
            late_root / "report.json",
        )
    assert not (late_root / "output").exists()
    assert not (late_root / "report.json").exists()
    assert not list(late_root.glob(".*.tmp-*"))
    monkeypatch.undo()

    race_root = tmp_path / "race"
    race_root.mkdir()
    race_output = race_root / "output"
    race_report = race_root / "report.json"
    original_publish = input_builder_module._publish_create_once
    calls = 0

    def racing_publish(**kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            race_output.mkdir()
        original_publish(**kwargs)

    monkeypatch.setattr(input_builder_module, "_publish_create_once", racing_publish)
    with pytest.raises(DeepSeekV4HCPreInputBuildError, match="already exists"):
        _build(composition_fixture, race_output, race_report)
    assert race_output.is_dir()
    assert not any(race_output.iterdir())
    assert not race_report.exists()
    assert not list(race_root.glob(".*.tmp-*"))


def test_unrelated_sibling_publication_does_not_invalidate_held_evidence(
    composition_fixture: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read = input_checker_module._read_file
    sibling = (
        composition_fixture["request"].parent / "concurrent-unrelated-evidence.tmp"
    )

    def publishing_read(source, label: str, maximum: int) -> bytes:
        payload = original_read(source, label, maximum)
        if label == "lookup request":
            sibling.write_bytes(b"unrelated")
        return payload

    monkeypatch.setattr(input_checker_module, "_read_file", publishing_read)
    try:
        report = _build(
            composition_fixture, tmp_path / "output", tmp_path / "report.json"
        )
        assert report["request"]["shape"] == [2, 2, 4, 4096]
    finally:
        sibling.unlink(missing_ok=True)


def test_official_hello_composition_revalidates_tokenizer_and_locked_lookup(
    tmp_path: Path,
) -> None:
    raw_snapshot = os.environ.get(OFFICIAL_SNAPSHOT_ENV)
    raw_evidence = os.environ.get(OFFICIAL_EVIDENCE_ENV)
    if not raw_snapshot or not raw_evidence:
        pytest.skip(
            f"set {OFFICIAL_SNAPSHOT_ENV} and {OFFICIAL_EVIDENCE_ENV} for official integration"
        )
    snapshot = Path(raw_snapshot)
    evidence = Path(raw_evidence)
    lock = load_strict_json(evidence / "checkpoint.lock.json")
    arguments = {
        "snapshot": snapshot,
        "lock": lock,
        "lookup_deployment_root": evidence / "lookup-deployment",
        "lookup_request_path": evidence / "hc-pre-lookup-request.json",
        "lookup_result_path": evidence / "hc-pre-lookup-result.json",
        "lookup_differential_path": evidence / "hc-pre-lookup-differential.json",
        "executable_deployment_root": evidence / "hc-pre-executable",
        "executable_application_root": evidence / "hc-pre-canonical",
        "source_texts": ["Hello"],
    }
    report = build_deepseek_v4_hc_pre_input_request(
        **arguments,
        output=tmp_path / "request",
        report_output=tmp_path / "composition.json",
    )
    assert report["status"] == (
        "official_tokenizer_lookup_differential_composition_verified"
    )
    assert report["tokenizer"]["token_ids"] == [[19923]]
    assert report["tokenizer"]["tokenizer_validation_id"] == (
        "176e504a2a500bfccd88d6ef10b72c1d08853a90ff62d97d173faaa808dd5c23"
    )
    assert report["tokenizer"]["source_text_rows"] == [
        {
            "batch_index": 0,
            "encoded_token_ids_sha256": hashlib.sha256(b"[19923]\n").hexdigest(),
            "encode_status": "exact_official_tokenizer_encode_equivalence",
            "utf8_sha256": hashlib.sha256(b"Hello").hexdigest(),
            "utf8_size_bytes": 5,
        }
    ]
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(
        report
    )
    assert (
        verify_deepseek_v4_hc_pre_input_composition(
            **arguments,
            request_root=tmp_path / "request",
            report_path=tmp_path / "composition.json",
        )["status"]
        == report["status"]
    )
    wrong_text = dict(arguments)
    wrong_text["source_texts"] = ["hello"]
    with pytest.raises(
        DeepSeekV4HCPreInputCheckError, match="tokenizer output differs"
    ):
        verify_deepseek_v4_hc_pre_input_composition(
            **wrong_text,
            request_root=tmp_path / "request",
            report_path=tmp_path / "composition.json",
        )
