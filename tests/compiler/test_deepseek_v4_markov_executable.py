from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

import pytest

from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_markov_executable import (
    DeepSeekV4MarkovExecutableCheckError,
    verify_deepseek_v4_markov_executable_roundtrip,
)
from compiler.checking.deepseek_v4_markov_execution import (
    DeepSeekV4MarkovExecutionCheckError,
    verify_deepseek_v4_markov_executable_execution,
)
from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.vertical_slice.deepseek_v4_markov_executable import (
    DeepSeekV4MarkovExecutableBuildError,
    build_deepseek_v4_markov_executable_deployment,
)
from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.markov_loop import markov_autoregressive_loop_bf16
import runtime.service_engine.deepseek_v4_markov_executable as executable_module
from runtime.service_engine.deepseek_v4_markov_executable import (
    DeepSeekV4MarkovExecutableServiceError,
    REQUEST_SCHEMA,
    execute_deepseek_v4_markov_executable_deployment,
    load_deepseek_v4_markov_executable_deployment,
)


FIXTURE_REVISION = "0123456789abcdef0123456789abcdef01234567"
W1_NAME = "mtp.2.markov_head.markov_w1.weight"
W2_NAME = "mtp.2.markov_head.markov_w2.weight"
SELECTED = (0, 3, 4, 7)


def _bf16(value: int | Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


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


def _output(name: str, rank: int) -> dict[str, Any]:
    return {
        "logical_dtype": "BF16",
        "name": name,
        "payload_bytes": 32,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": [4, 4],
        "source_slice": {"axis": 0, "start": rank * 4, "stop": rank * 4 + 4},
        "storage_dtype": "BF16",
        "transform": "identity",
    }


def _plan() -> list[dict[str, Any]]:
    return [
        {
            "action": "tensor_parallel_slice_axis_0",
            "logical_dtype": "BF16",
            "name": name,
            "outputs": [_output(name, rank) for rank in range(2)],
            "semantic_role": role,
            "shape": [8, 4],
            "size_bytes": 64,
            "storage_dtype": "BF16",
        }
        for name, role in (
            (W1_NAME, "model.dspark.markov_embedding.weight"),
            (W2_NAME, "model.dspark.markov_head.weight"),
        )
    ]


def _fixture_rows() -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    embedding = [[0] * 4 for _ in range(8)]
    head = [[0] * 4 for _ in range(8)]
    for local, global_id in enumerate(SELECTED):
        embedding[global_id][local] = _bf16(1)
        head[global_id][(local - 1) % 4] = _bf16(4)
    return (
        tuple(tuple(row) for row in embedding),
        tuple(tuple(row) for row in head),
    )


@pytest.fixture
def markov_application(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], Path, tuple, tuple]:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    w1, w2 = _fixture_rows()
    tensors = [
        (W1_NAME, "BF16", [8, 4], struct.pack("<32H", *(sum(w1, ())))),
        (W2_NAME, "BF16", [8, 4], struct.pack("<32H", *(sum(w2, ())))),
    ]
    shard = _safetensors(tensors)
    config = canonical_json_bytes({"architectures": ["MarkovFixture"]})
    index = canonical_json_bytes(
        {
            "metadata": {"total_size": 128},
            "weight_map": {name: "model.safetensors" for name, _, _, _ in tensors},
        }
    )
    payloads = {
        "config.json": config,
        "model.safetensors": shard,
        "model.safetensors.index.json": index,
    }
    for name, payload in payloads.items():
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
                for name, payload in sorted(payloads.items())
            ],
            "remote_code_policy": "disabled",
            "repository": "OpenTallas/deepseek-v4-markov-fixture",
            "required_files": ["config.json"],
            "revision": FIXTURE_REVISION,
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    plan = _plan()
    application = tmp_path / "canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_markov_fixture_plan.v1",
        plan_inputs=plan,
        output=application,
    )
    return snapshot, lock, application, w1, w2


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _zero_logits(batch: int) -> list[list[list[int]]]:
    return [[[0] * len(SELECTED) for _ in range(5)] for _ in range(batch)]


def _request(build_id: str) -> dict[str, Any]:
    return {
        "base_logits_binary32_codes": _zero_logits(2),
        "build_id": build_id,
        "entropy": None,
        "input_global_token_ids": [0, 4],
        "model_id": "deepseek-v4-flash-0731",
        "require_pytorch_cuda_equivalence": True,
        "schema": REQUEST_SCHEMA,
        "temperature_binary32": 0,
    }


def _selected_shards(rows: tuple[tuple[int, ...], ...]) -> tuple:
    return (
        (rows[0], rows[3]),
        (rows[4], rows[7]),
    )


def test_markov_deployment_is_deterministic_and_independently_roundtrips(
    markov_application: tuple,
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = markov_application
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest = build_deepseek_v4_markov_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=first,
        selected_global_token_ids=SELECTED,
    )
    build_deepseek_v4_markov_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
        selected_global_token_ids=SELECTED,
    )
    assert _tree(first) == _tree(second)
    assert manifest == load_strict_json(first / "deployment_manifest.json")
    assert manifest["selected_global_token_ids"] == list(SELECTED)
    assert manifest["microcode_abi"]["program_sha256"] == (
        "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
    )
    report = verify_deepseek_v4_markov_executable_roundtrip(first, application)
    assert report == load_strict_json(first / "roundtrip_report.json")
    assert report["checked_source_assignment_count"] == 4
    assert report["checked_source_assignment_bytes"] == 128
    assert report["checked_deployment_payload_count"] == 4
    assert report["checked_deployment_payload_bytes"] == 64


def test_artifact_execution_preserves_global_ids_and_matches_reference(
    markov_application: tuple,
    tmp_path: Path,
) -> None:
    snapshot, lock, application, w1, w2 = markov_application
    deployment = tmp_path / "deployment"
    manifest = build_deepseek_v4_markov_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=deployment,
        selected_global_token_ids=SELECTED,
    )
    loaded = load_deepseek_v4_markov_executable_deployment(deployment)
    assert loaded.selected_global_token_ids == SELECTED
    assert loaded.embedding_weight_shards_bf16_codes == _selected_shards(w1)
    assert loaded.head_weight_shards_bf16_codes == _selected_shards(w2)

    request = _request(manifest["build_id"])
    result = execute_deepseek_v4_markov_executable_deployment(deployment, request)
    differential = verify_deepseek_v4_markov_executable_execution(
        deployment_root=deployment,
        application_root=application,
        request=request,
        result=result,
    )
    expected = markov_autoregressive_loop_bf16(
        _zero_logits(2),
        (0, 2),
        _selected_shards(w1),
        _selected_shards(w2),
        temperature_binary32=0,
        tensor_parallel_world_size=2,
    )
    assert result["output_local_token_ids"] == [list(row) for row in expected.output_token_ids]
    assert result["output_global_token_ids"] == [
        [SELECTED[local] for local in row] for row in expected.output_token_ids
    ]
    assert result["output_global_token_ids"] == [
        [0, 3, 4, 7, 0, 3],
        [4, 7, 0, 3, 4, 7],
    ]
    assert result["markov_bias_binary32_codes"] == [
        [list(row) for row in batch]
        for batch in expected.markov_bias_binary32_codes
    ]
    assert result["adjusted_logits_binary32_codes"] == [
        [list(row) for row in batch]
        for batch in expected.adjusted_logits_binary32_codes
    ]
    assert result["logical_counters"]["micro_ops_executed"] == 21
    assert result["logical_counters"]["exact_product_accumulates"] == 160
    assert result["status"] == (
        "artifact_authenticated_selected_vocabulary_markov_execution"
    )
    assert differential["status"] == "exact_artifact_service_reference_match"
    assert differential["result_id"] == result["result_id"]

    changed_result = {
        **result,
        "output_global_token_ids": [
            *result["output_global_token_ids"][:-1],
            [0] * 6,
        ],
    }
    with pytest.raises(
        DeepSeekV4MarkovExecutionCheckError,
        match="output_global_token_ids differs",
    ):
        verify_deepseek_v4_markov_executable_execution(
            deployment_root=deployment,
            application_root=application,
            request=request,
            result=changed_result,
        )


def test_deployment_and_request_tampering_fail_closed(
    markov_application: tuple,
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = markov_application
    deployment = tmp_path / "deployment"
    manifest = build_deepseek_v4_markov_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=deployment,
        selected_global_token_ids=SELECTED,
    )
    request = _request(manifest["build_id"])
    bad_request = {**request, "input_global_token_ids": [0, 1]}
    with pytest.raises(
        DeepSeekV4MarkovExecutableServiceError,
        match="outside selected vocabulary",
    ):
        execute_deepseek_v4_markov_executable_deployment(deployment, bad_request)
    with pytest.raises(DeepSeekV4MarkovExecutableServiceError, match="request identity"):
        execute_deepseek_v4_markov_executable_deployment(
            deployment, {**request, "build_id": "0" * 64}
        )

    payload = deployment / "rom/markov_w1/rank-000.bf16"
    original = payload.read_bytes()
    payload.write_bytes(original[:-1] + bytes((original[-1] ^ 1,)))
    with pytest.raises(
        DeepSeekV4MarkovExecutableServiceError,
        match="differs from deployment manifest",
    ):
        load_deepseek_v4_markov_executable_deployment(deployment)


def test_inverse_checker_rejects_deployment_and_canonical_source_drift(
    markov_application: tuple,
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = markov_application
    deployment = tmp_path / "deployment"
    build_deepseek_v4_markov_executable_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=deployment,
        selected_global_token_ids=SELECTED,
    )
    deployed = deployment / "rom/markov_w2/rank-001.bf16"
    original_deployed = deployed.read_bytes()
    deployed.write_bytes(bytes((original_deployed[0] ^ 1,)) + original_deployed[1:])
    with pytest.raises(
        DeepSeekV4MarkovExecutableCheckError,
        match="differs from selected canonical rows",
    ):
        verify_deepseek_v4_markov_executable_roundtrip(deployment, application)
    deployed.write_bytes(original_deployed)

    source = application / f"ranks/rank-000/{W1_NAME}.bin"
    original_source = source.read_bytes()
    source.write_bytes(bytes((original_source[0] ^ 1,)) + original_source[1:])
    with pytest.raises(
        DeepSeekV4MarkovExecutableCheckError,
        match="changed during inverse checking",
    ):
        verify_deepseek_v4_markov_executable_roundtrip(deployment, application)


@pytest.mark.parametrize(
    ("selected", "match"),
    [
        ((0, 0, 4, 7), "strictly increasing"),
        ((0, 4, 7), "same nonzero row count"),
        ((0, 3, 4, 8), "exceeds the canonical vocabulary"),
        ((0, 1, 2, 3), "same nonzero row count"),
    ],
)
def test_builder_rejects_invalid_selected_vocabularies_atomically(
    markov_application: tuple,
    tmp_path: Path,
    selected: tuple[int, ...],
    match: str,
) -> None:
    snapshot, lock, application, _, _ = markov_application
    output = tmp_path / f"bad-{hash(selected)}"
    with pytest.raises(DeepSeekV4MarkovExecutableBuildError, match=match):
        build_deepseek_v4_markov_executable_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
            selected_global_token_ids=selected,
        )
    assert not output.exists()


def test_artifact_service_has_no_compiler_reference_rng_or_framework_dependency() -> None:
    source = Path(executable_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    absolute_import_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    absolute_import_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert absolute_import_roots.isdisjoint(
        {"compiler", "random", "runtime.reference", "torch"}
    )
