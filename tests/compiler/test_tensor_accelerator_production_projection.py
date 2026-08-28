from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.tensor_accelerator.bf16_qualification import (
    publish_qualification_report,
    qualify_bf16_projection_payloads,
)
from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.production_command import decode, encode
from compiler.tensor_accelerator.production_model import compute_graph_id
from compiler.tensor_accelerator.production_projection import (
    build_projection_deployment,
)
from compiler.tensor_accelerator.production_projection_checking import (
    ProductionProjectionCheckError,
    check_projection_candidate,
)
from runtime.tensor_accelerator.production_simulator import (
    ProductionProjectionSimulator,
    ProductionSimulationError,
    publish_execution_report,
)


ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v1.json"
SOURCE_HASH = "a" * 64
EMBEDDING = "model.embed_tokens.weight"
WEIGHT = "model.layers.0.self_attn.q_proj.weight"


def _safetensors(tensors: list[tuple[str, str, list[int], bytes]]) -> bytes:
    header: dict[str, Any] = {}
    body = bytearray()
    for name, dtype, shape, payload in tensors:
        start = len(body)
        body.extend(payload)
        header[name] = {
            "data_offsets": [start, len(body)],
            "dtype": dtype,
            "shape": shape,
        }
    encoded = json.dumps(
        header, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    encoded += b" " * (-len(encoded) % 8)
    return struct.pack("<Q", len(encoded)) + encoded + bytes(body)


def _binding(lock_id: str, name: str, shape: list[int], digest: str) -> dict[str, Any]:
    return {
        "checkpoint_lock_id": lock_id,
        "kind": "checkpoint",
        "payload_sha256": digest,
        "sources": [
            {
                "dtype": "bf16",
                "payload_sha256": digest,
                "shape": shape,
                "tensor_name": name,
            }
        ],
        "transform": {"kind": "identity"},
    }


def _model_graph(
    lock_id: str,
    embedding_payload: bytes,
    weight_payload: bytes,
    *,
    k: int,
    n: int,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "entrypoints": [
            {
                "inputs": ["input.token_ids"],
                "outputs": ["output.q"],
                "phase": phase,
                "predicate": {"kind": "always"},
                "states": [],
            }
            for phase in ("prefill", "decode")
        ],
        "model_id": "qwen3-projection-fixture",
        "numeric_profile": "qwen3_bf16_gqa_target_v1",
        "operations": [
            {
                "attributes": {"axis": -1},
                "effects": [],
                "id": "embedding.lookup",
                "inputs": ["input.token_ids", EMBEDDING],
                "kind": "EMBEDDING_LOOKUP",
                "numeric_contract": "bf16_payload_lookup_v1",
                "outputs": ["hidden.embedding"],
                "phases": ["prefill", "decode"],
                "predicate": {"kind": "always"},
                "source_anchor": {
                    "path": "modeling/qwen.py",
                    "source_sha256": SOURCE_HASH,
                    "symbol": "Qwen.embed_tokens",
                },
            },
            {
                "attributes": {"transpose_weight": True},
                "effects": [],
                "id": "layer0.q_projection",
                "inputs": ["hidden.embedding", WEIGHT],
                "kind": "MATMUL",
                "numeric_contract": "bf16_bf16_fp32_sequential_rne_v1",
                "outputs": ["output.q"],
                "phases": ["prefill", "decode"],
                "predicate": {"kind": "always"},
                "source_anchor": {
                    "path": "modeling/qwen.py",
                    "source_sha256": SOURCE_HASH,
                    "symbol": "QwenAttention.q_proj",
                },
            },
        ],
        "schema": "opentallas.model_graph.v2",
        "source": {
            "repository": "OpenTallas/qwen3-projection-fixture",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "source_lock_id": SOURCE_HASH,
        },
        "state_resources": [],
        "symbols": [
            {
                "binding": {"field": "span_tokens", "kind": "request"},
                "default": 1,
                "id": "span_tokens",
                "maximum": 1,
                "minimum": 1,
                "multiple_of": 1,
            }
        ],
        "tensors": [
            {
                "dtype": "i64",
                "id": "input.token_ids",
                "layout": "bs",
                "role": "input",
                "shape": [1, "span_tokens"],
            },
            {
                "binding": _binding(
                    lock_id,
                    EMBEDDING,
                    [2, k],
                    hashlib.sha256(embedding_payload).hexdigest(),
                ),
                "dtype": "bf16",
                "id": EMBEDDING,
                "layout": "row_major",
                "role": "weight",
                "shape": [2, k],
            },
            {
                "dtype": "bf16",
                "id": "hidden.embedding",
                "layout": "bsh",
                "role": "activation",
                "shape": [1, "span_tokens", k],
            },
            {
                "binding": _binding(
                    lock_id,
                    WEIGHT,
                    [n, k],
                    hashlib.sha256(weight_payload).hexdigest(),
                ),
                "dtype": "bf16",
                "id": WEIGHT,
                "layout": "row_major",
                "role": "weight",
                "shape": [n, k],
            },
            {
                "dtype": "bf16",
                "id": "output.q",
                "layout": "bsh",
                "role": "output",
                "shape": [1, "span_tokens", n],
            },
        ],
    }
    return {**body, "graph_id": compute_graph_id(body)}


@pytest.fixture
def projection_sources(tmp_path: Path) -> dict[str, Path]:
    k = 512
    n = 4
    input_codes = np.asarray(
        [
            [0x3F80, 0x3F00, 0xBF00, 0x0000] * (k // 8)
            + [0x4000, 0xBF80, 0x3E80, 0x3F00] * (k // 8),
            [0x4000, 0xBF80, 0x3E80, 0x0000] * (k // 8)
            + [0x3F00, 0x3F80, 0xBE80, 0xBF00] * (k // 8),
        ],
        dtype="<u2",
    )
    weight_codes = np.asarray(
        [
            [0x3F80] * (k // 2) + [0x3F00] * (k // 2),
            [0x3F00, 0xBF00] * (k // 4) + [0x3F80, 0x0000] * (k // 4),
            [0x3E80, 0x3F00, 0x3F80, 0xBF80] * (k // 8)
            + [0xBF00, 0x3F80, 0x3E80, 0x0000] * (k // 8),
            [0x0000, 0x3F80, 0x0000, 0xBF00] * (k // 8)
            + [0x3F00, 0x0000, 0xBF80, 0x3F80] * (k // 8),
        ],
        dtype="<u2",
    )
    embedding_payload = input_codes.tobytes(order="C")
    weight_payload = weight_codes.tobytes(order="C")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_bytes(canonical_json_bytes({"model_type": "qwen3"}))
    shard_name = "model-00001-of-00001.safetensors"
    (snapshot / shard_name).write_bytes(
        _safetensors(
            [
                (EMBEDDING, "BF16", [2, k], embedding_payload),
                (WEIGHT, "BF16", [n, k], weight_payload),
            ]
        )
    )
    write_canonical_json(
        snapshot / "model.safetensors.index.json",
        {
            "metadata": {"total_size": len(embedding_payload) + len(weight_payload)},
            "weight_map": {EMBEDDING: shard_name, WEIGHT: shard_name},
        },
    )
    expected_files = []
    for name in sorted(("config.json", shard_name, "model.safetensors.index.json")):
        payload = (snapshot / name).read_bytes()
        expected_files.append(
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    source = validate_checkpoint_source(
        {
            "checkpoint_index": "model.safetensors.index.json",
            "expected_files": expected_files,
            "remote_code_policy": "disabled",
            "repository": "OpenTallas/qwen3-projection-fixture",
            "required_files": ["config.json"],
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    lock_path = tmp_path / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)
    graph_path = tmp_path / "model_graph.v2.json"
    write_canonical_json(
        graph_path,
        _model_graph(lock["lock_id"], embedding_payload, weight_payload, k=k, n=n),
    )
    report = qualify_bf16_projection_payloads(
        checkpoint_lock_id=lock["lock_id"],
        input_record={
            "dtype": "BF16",
            "name": EMBEDDING,
            "payload_sha256": hashlib.sha256(embedding_payload).hexdigest(),
            "shape": [2, k],
            "size_bytes": len(embedding_payload),
        },
        input_row=0,
        input_row_payload=input_codes[0].tobytes(order="C"),
        weight_record={
            "dtype": "BF16",
            "name": WEIGHT,
            "payload_sha256": hashlib.sha256(weight_payload).hexdigest(),
            "shape": [n, k],
            "size_bytes": len(weight_payload),
        },
        weight_payload=weight_payload,
        selected_rows=[0, n - 1],
    )
    qualification_path = tmp_path / "qualification.json"
    publish_qualification_report(report, qualification_path)
    return {
        "capability": CAPABILITY,
        "graph": graph_path,
        "lock": lock_path,
        "qualification": qualification_path,
        "snapshot": snapshot,
    }


def _build(sources: dict[str, Path], output: Path) -> dict[str, Any]:
    return build_projection_deployment(
        snapshot=sources["snapshot"],
        checkpoint_lock_path=sources["lock"],
        model_graph_path=sources["graph"],
        capability_path=sources["capability"],
        qualification_path=sources["qualification"],
        output=output,
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _reidentify_plan(path: Path) -> None:
    plan = load_strict_json(path)
    body = {key: value for key, value in plan.items() if key != "physical_plan_id"}
    plan["physical_plan_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(path, plan)


def _refresh_manifest(root: Path) -> None:
    manifest_path = root / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    plan = load_strict_json(root / "physical/physical_plan.json")
    manifest["physical_plan_id"] = plan["physical_plan_id"]
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        payload = path.read_bytes()
        artifact["sha256"] = hashlib.sha256(payload).hexdigest()
        artifact["size_bytes"] = len(payload)
    body = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(manifest_path, manifest)


def _replace_program(root: Path, commands: tuple[Any, ...]) -> None:
    command_path = root / "program/commands.bin"
    payload = encode(commands)
    command_path.write_bytes(payload)
    plan_path = root / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["program"].update(
        {
            "command_count": len(commands),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    )
    write_canonical_json(plan_path, plan)
    _reidentify_plan(plan_path)
    _refresh_manifest(root)


def test_projection_build_is_deterministic_tiled_and_independently_checked(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = _build(projection_sources, first)
    second_manifest = _build(projection_sources, second)
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    plan = load_strict_json(first / "physical/physical_plan.json")
    check = load_strict_json(first / "checks/independent_check.json")
    commands = decode((first / "program/commands.bin").read_bytes())
    assert plan["problem"] == {
        "k": 512,
        "k_tile": 256,
        "k_tiles": 2,
        "m": 1,
        "n": 4,
        "n_tile": 4,
        "n_tiles": 1,
        "tile_count": 2,
    }
    assert [command.opcode.name for command in commands] == [
        "DMA_HBM_TO_SRAM",
        "MATMUL_BF16_TILE",
        "DMA_HBM_TO_SRAM",
        "MATMUL_BF16_TILE",
        "COMPLETE",
    ]
    assert commands[1].flags == 1
    assert commands[3].flags == 2
    assert check["status"] == "pass"
    assert check["reconstructed_weight"] == {
        "payload_sha256": load_strict_json(projection_sources["qualification"])[
            "weight"
        ]["payload_sha256"],
        "size_bytes": 4096,
        "source_tensor": WEIGHT,
        "tile_count": 2,
    }
    assert first_manifest["claim_boundary"][2] == (
        "uncharacterized functional evidence only"
    )


def test_independent_checker_rejects_rehashed_payload_and_sram_corruption(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "deployment"
    _build(projection_sources, output)
    image = output / "memory/hbm_weights_tiled.bin"
    payload = bytearray(image.read_bytes())
    payload[0] ^= 1
    image.write_bytes(payload)
    plan_path = output / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["hbm"]["image"]["sha256"] = hashlib.sha256(payload).hexdigest()
    tile_size = plan["hbm"]["tiles"][0]["size_bytes"]
    plan["hbm"]["tiles"][0]["payload_sha256"] = hashlib.sha256(
        payload[:tile_size]
    ).hexdigest()
    write_canonical_json(plan_path, plan)
    _reidentify_plan(plan_path)
    with pytest.raises(ProductionProjectionCheckError, match="inverse-reconstructed"):
        check_projection_candidate(
            snapshot=projection_sources["snapshot"],
            checkpoint_lock_path=projection_sources["lock"],
            model_graph_path=projection_sources["graph"],
            capability_path=projection_sources["capability"],
            qualification_path=projection_sources["qualification"],
            root=output,
        )

    clean = tmp_path / "clean"
    _build(projection_sources, clean)
    clean_plan_path = clean / "physical/physical_plan.json"
    clean_plan = load_strict_json(clean_plan_path)
    clean_plan["sram"]["regions"][1]["address"] += 16
    write_canonical_json(clean_plan_path, clean_plan)
    _reidentify_plan(clean_plan_path)
    with pytest.raises(ProductionProjectionCheckError, match="SRAM region"):
        check_projection_candidate(
            snapshot=projection_sources["snapshot"],
            checkpoint_lock_path=projection_sources["lock"],
            model_graph_path=projection_sources["graph"],
            capability_path=projection_sources["capability"],
            qualification_path=projection_sources["qualification"],
            root=clean,
        )


def test_independent_checker_rejects_missing_or_reordered_commands(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "deployment"
    _build(projection_sources, output)
    command_path = output / "program/commands.bin"
    commands = decode(command_path.read_bytes())
    missing = tuple(
        replace(command, index=index)
        for index, command in enumerate(commands[1:])
    )
    command_path.write_bytes(encode(missing))
    plan_path = output / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    command_payload = command_path.read_bytes()
    plan["program"].update(
        {
            "command_count": len(missing),
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        }
    )
    write_canonical_json(plan_path, plan)
    _reidentify_plan(plan_path)
    with pytest.raises(ProductionProjectionCheckError, match="command count"):
        check_projection_candidate(
            snapshot=projection_sources["snapshot"],
            checkpoint_lock_path=projection_sources["lock"],
            model_graph_path=projection_sources["graph"],
            capability_path=projection_sources["capability"],
            qualification_path=projection_sources["qualification"],
            root=output,
        )

    reordered = tmp_path / "reordered"
    _build(projection_sources, reordered)
    reordered_path = reordered / "program/commands.bin"
    original = decode(reordered_path.read_bytes())
    swapped_raw = (original[2], original[1], original[0], original[3], original[4])
    swapped = tuple(
        replace(command, index=index) for index, command in enumerate(swapped_raw)
    )
    reordered_path.write_bytes(encode(swapped))
    reordered_plan_path = reordered / "physical/physical_plan.json"
    reordered_plan = load_strict_json(reordered_plan_path)
    swapped_payload = reordered_path.read_bytes()
    reordered_plan["program"].update(
        {
            "sha256": hashlib.sha256(swapped_payload).hexdigest(),
            "size_bytes": len(swapped_payload),
        }
    )
    write_canonical_json(reordered_plan_path, reordered_plan)
    _reidentify_plan(reordered_plan_path)
    with pytest.raises(ProductionProjectionCheckError, match="DMA command"):
        check_projection_candidate(
            snapshot=projection_sources["snapshot"],
            checkpoint_lock_path=projection_sources["lock"],
            model_graph_path=projection_sources["graph"],
            capability_path=projection_sources["capability"],
            qualification_path=projection_sources["qualification"],
            root=reordered,
        )


def test_projection_build_never_overwrites_existing_output(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "owned"
    output.mkdir()
    marker = output / "owner"
    marker.write_text("user\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="already exists"):
        _build(projection_sources, output)
    assert marker.read_text(encoding="utf-8") == "user\n"
    assert not list(tmp_path.glob(".owned.tmp-*"))


def test_artifact_only_simulator_causally_matches_qualified_projection(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "deployment"
    _build(projection_sources, output)
    report = ProductionProjectionSimulator.load(output).execute()
    qualification = load_strict_json(projection_sources["qualification"])
    assert report["status"] == "pass"
    assert report["mode"] == "artifact_only_data_bearing_functional"
    assert report["output"]["payload_sha256"] == qualification["output"][
        "payload_sha256"
    ]
    assert report["output"]["saturated_element_count"] == qualification["output"][
        "saturated_element_count"
    ]
    selected_rows = qualification["selected_reference"]["output_rows"]
    assert [report["output"]["codes"][index] for index in selected_rows] == (
        qualification["selected_reference"]["output_codes"]
    )
    assert report["counter_reconciliation"] == "exact"
    assert report["timing"] == {
        "reason": "capability_uncharacterized",
        "status": "unavailable",
    }
    assert [record["opcode"] for record in report["trace"]] == [
        "DMA_HBM_TO_SRAM",
        "MATMUL_BF16_TILE",
        "DMA_HBM_TO_SRAM",
        "MATMUL_BF16_TILE",
        "COMPLETE",
    ]
    retained = tmp_path / "evidence/execution.json"
    publish_execution_report(report, retained)
    assert retained.read_bytes() == canonical_json_bytes(report)
    with pytest.raises(ProductionSimulationError, match="will not be overwritten"):
        publish_execution_report(report, retained)
    forged = dict(report)
    forged["status"] = "fail"
    with pytest.raises(ProductionSimulationError, match="identity or status"):
        publish_execution_report(forged, tmp_path / "forged.json")


def test_simulator_rejects_manifest_tamper_and_missing_dma(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    tampered = tmp_path / "tampered"
    _build(projection_sources, tampered)
    input_path = tampered / "request/input.bf16.bin"
    payload = bytearray(input_path.read_bytes())
    payload[0] ^= 1
    input_path.write_bytes(payload)
    with pytest.raises(ProductionSimulationError, match="SHA-256 or size differs"):
        ProductionProjectionSimulator.load(tampered)

    missing = tmp_path / "missing-dma"
    _build(projection_sources, missing)
    commands = decode((missing / "program/commands.bin").read_bytes())
    without_first_dma = tuple(
        replace(command, index=index)
        for index, command in enumerate(commands[1:])
    )
    _replace_program(missing, without_first_dma)
    with pytest.raises(ProductionSimulationError, match="fresh causally preceding DMA"):
        ProductionProjectionSimulator.load(missing).execute()


def test_simulator_rejects_rehashed_claim_and_tile_coverage_drift(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    claim = tmp_path / "claim-overreach"
    _build(projection_sources, claim)
    manifest_path = claim / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["claim_boundary"].append("production performance evidence")
    body = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(manifest_path, manifest)
    with pytest.raises(ProductionSimulationError, match="claim boundary"):
        ProductionProjectionSimulator.load(claim)

    coverage = tmp_path / "tile-coverage"
    _build(projection_sources, coverage)
    plan_path = coverage / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["hbm"]["tiles"][0]["k_start"] = plan["problem"]["k_tile"]
    write_canonical_json(plan_path, plan)
    _reidentify_plan(plan_path)
    _refresh_manifest(coverage)
    with pytest.raises(ProductionSimulationError, match="HBM tile 0 identity"):
        ProductionProjectionSimulator.load(coverage)


def test_reordered_dma_is_executed_causally_and_changes_result(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "reordered"
    _build(projection_sources, output)
    expected_hash = load_strict_json(projection_sources["qualification"])["output"][
        "payload_sha256"
    ]
    commands = decode((output / "program/commands.bin").read_bytes())
    reordered = list(commands)
    reordered[0] = replace(commands[0], source0=commands[2].source0)
    reordered[2] = replace(commands[2], source0=commands[0].source0)
    _replace_program(output, tuple(reordered))
    report = ProductionProjectionSimulator.load(output).execute()
    assert report["status"] == "pass"
    assert report["counter_reconciliation"] == "exact"
    assert report["output"]["payload_sha256"] != expected_hash


def test_simulator_rejects_forged_counter_expectations(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "forged-counters"
    _build(projection_sources, output)
    plan_path = output / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["expected_counters"]["scalar_multiplications"] += 1
    write_canonical_json(plan_path, plan)
    _reidentify_plan(plan_path)
    _refresh_manifest(output)
    with pytest.raises(ProductionSimulationError, match="observed execution counters"):
        ProductionProjectionSimulator.load(output).execute()


def test_production_simulator_has_no_graph_compiler_or_whole_matrix_shortcut() -> None:
    module = __import__(
        "runtime.tensor_accelerator.production_simulator", fromlist=["unused"]
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "production_projection import" not in source
    assert "production_projection_checking" not in source
    assert "production_model" not in source
    assert "dense_bf16_linear_bf16" not in source
    assert "transformers" not in source
    assert "torch" not in source


def test_production_projection_artifacts_validate_against_strict_schemas(
    projection_sources: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "schema-deployment"
    _build(projection_sources, output)
    report = ProductionProjectionSimulator.load(output).execute()
    schema_root = ROOT / "schemas/compiler/tensor_accelerator"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(schema_root.glob("*.schema.json"))
    }
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    instances = {
        "bf16_projection_deployment_v1.schema.json": load_strict_json(
            output / "deployment_manifest.json"
        ),
        "bf16_projection_execution_v1.schema.json": report,
        "bf16_projection_expectations_v1.schema.json": load_strict_json(
            output / "execution_expectations.json"
        ),
        "bf16_projection_independent_check_v1.schema.json": load_strict_json(
            output / "checks/independent_check.json"
        ),
        "bf16_projection_kernel_v1.schema.json": load_strict_json(
            output / "ir/tensor_kernel_ir.json"
        ),
        "bf16_projection_physical_plan_v1.schema.json": load_strict_json(
            output / "physical/physical_plan.json"
        ),
        "bf16_projection_request_v1.schema.json": load_strict_json(
            output / "request/execution_request.json"
        ),
        "bf16_projection_source_lock_v1.schema.json": load_strict_json(
            output / "source.lock.json"
        ),
        "production_capability_v1.schema.json": load_strict_json(
            output / "capability.json"
        ),
    }
    assert len(instances) == 9
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)
