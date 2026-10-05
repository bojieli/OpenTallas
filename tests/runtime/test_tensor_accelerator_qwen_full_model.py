"""The retained ABI 2.5 Qwen physical deployment.

This file belongs to the ABI 2.5 tensor-accelerator lane that ABI 3.0
superseded -- the lane inventoried in ``tests/compiler/README_RETIRED_LANE.md``
and tracked as OI-25.  It reads
``results/tensor_accelerator/qwen3_full_model_physical``, the ABI 2.5 physical
build, and nothing in ``runtime/abi3``, ``runtime/sim`` or ``compiler.ir.v3``
depends on any of it.  A green tick here is not evidence for ABI 3.0.

Three of its tests load the deployment through ``QwenFullModelSimulator``.
That needs the payload the manifest declares -- seventeen HBM shards and
``program/commands.bin`` -- which ``.gitignore`` excludes, in the same commit
that published the deployment, because it is tens of gigabytes.  They are
therefore preconditioned on the payload actually being present, and skip with
that stated when it is not.  The rest of the file needs only the committed
descriptors and runs everywhere.
"""

from __future__ import annotations

import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from jsonschema import Draft202012Validator, ValidationError

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from runtime.tensor_accelerator.attention import empty_kv_snapshot
from runtime.tensor_accelerator.bf16 import (
    accumulate_bf16_tile_fp32,
    dense_bf16_linear_bf16,
    finalize_bf16_accumulator,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (
    EXECUTION_SCHEMA,
    REQUEST_SCHEMA,
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
    _canonical,
    _untile_n_block,
    publish_qwen_full_model_execution_report,
)


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
EXECUTION_REPORT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_execution_v1.schema.json"
)


def _retained_deployment_is_complete(root: Path) -> bool:
    """Whether every artifact the deployment manifest declares is on disk.

    ``deployment_manifest.json`` is committed; the payload it declares -- the
    seventeen HBM shards under ``memory/hbm/`` and ``program/commands.bin`` --
    is excluded by ``.gitignore`` in the same commit that published the
    deployment, because it is tens of gigabytes.  So testing for the manifest
    alone answers "available" on every checkout, including the ones on which
    ``QwenFullModelSimulator.load`` cannot get past its own file-set check.
    The precondition these tests need is the artifact set, not the manifest.
    """

    manifest = root / "deployment_manifest.json"
    if not manifest.is_file():
        return False
    try:
        artifacts = json.loads(manifest.read_text(encoding="utf-8"))["artifacts"]
        return all((root / record["path"]).is_file() for record in artifacts)
    except (OSError, ValueError, KeyError, TypeError):
        return False


HAS_DEPLOYMENT = _retained_deployment_is_complete(DEPLOYMENT)
AUTHENTIC = pytest.mark.skipif(
    not HAS_DEPLOYMENT,
    reason=(
        "the retained ABI 2.5 Qwen physical deployment is incomplete: its "
        "HBM shards and program/commands.bin are excluded by .gitignore and "
        "cannot be reproduced from this repository. This is the retired ABI "
        "2.5 lane of tests/compiler/README_RETIRED_LANE.md (OI-25), not ABI "
        "3.0 coverage"
    ),
)

GRAPH_ID = "a" * 64
TRANSACTION_ID = 5_861_229_642_535_750_732


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _request() -> dict[str, Any]:
    body = {
        "expected_generations": [0] * 36,
        "graph_id": GRAPH_ID,
        "last_row_index": 0,
        "phase": "prefill",
        "position_end": 1,
        "position_start": 0,
        "schema": REQUEST_SCHEMA,
        "span_tokens": 1,
        "token_id": 0,
        "transaction_id": TRANSACTION_ID,
    }
    return _reidentify(body, "request_id")


def _request_simulator() -> QwenFullModelSimulator:
    simulator = object.__new__(QwenFullModelSimulator)
    simulator._model = SimpleNamespace(graph_id=GRAPH_ID)
    simulator._states = {
        f"kv.layer.{layer}": empty_kv_snapshot(f"kv.layer.{layer}", capacity=8000)
        for layer in range(36)
    }
    simulator._context_capacity = 8000
    simulator._request = _request()
    return simulator


def test_fused_matrix_block_is_exactly_segmented_k_execution() -> None:
    rng = np.random.default_rng(0x5157454E)
    vocabulary = np.array(
        [
            0x0000,
            0x3D00,
            0x3E00,
            0x3F00,
            0x3F80,
            0x4000,
            0xBD00,
            0xBE00,
            0xBF00,
            0xBF80,
            0xC000,
        ],
        dtype=np.uint16,
    )
    inputs = rng.choice(vocabulary, size=(1, 512))
    weights = rng.choice(vocabulary, size=(64, 512))
    tiled = np.ascontiguousarray(
        weights.reshape(64, 2, 256).transpose(1, 0, 2), dtype="<u2"
    ).tobytes()
    details = {
        "k": 512,
        "k_tile": 256,
        "k_tiles": 2,
        "n_tile": 64,
    }
    reconstructed = _untile_n_block(tiled, details)
    np.testing.assert_array_equal(reconstructed, weights)

    fused = dense_bf16_linear_bf16(
        inputs,
        reconstructed,
        input_tile_rows=1,
        output_tile_rows=64,
    )
    accumulator = None
    for start in range(0, 512, 256):
        segment = accumulate_bf16_tile_fp32(
            inputs[:, start : start + 256],
            reconstructed[:, start : start + 256],
            None if accumulator is None else accumulator.values,
        )
        accumulator = segment
    assert accumulator is not None
    segmented = finalize_bf16_accumulator(accumulator.values)
    np.testing.assert_array_equal(fused.values, segmented.values)
    assert (
        fused.output_saturated_element_count == segmented.output_saturated_element_count
    )


def test_request_v1_is_fixed_and_fails_closed() -> None:
    simulator = _request_simulator()
    retained = _request()
    assert simulator._validate_request(retained) == retained

    wrong_identity = copy.deepcopy(retained)
    wrong_identity["token_id"] = 1
    with pytest.raises(QwenFullModelSimulationError, match="identity differs"):
        simulator._validate_request(wrong_identity)

    stale = copy.deepcopy(retained)
    stale["expected_generations"][0] = 1
    stale = _reidentify(stale, "request_id")
    with pytest.raises(QwenFullModelSimulationError, match="fixed request"):
        simulator._validate_request(stale)

    wrong_position = copy.deepcopy(retained)
    wrong_position.update(
        {"last_row_index": 0, "phase": "decode", "position_end": 2, "position_start": 1}
    )
    wrong_position = _reidentify(wrong_position, "request_id")
    with pytest.raises(QwenFullModelSimulationError, match="fixed request"):
        simulator._validate_request(wrong_position)

    out_of_range = copy.deepcopy(retained)
    out_of_range["token_id"] = 151_936
    out_of_range = _reidentify(out_of_range, "request_id")
    with pytest.raises(QwenFullModelSimulationError, match="bounds differ"):
        simulator._validate_request(out_of_range)


def test_noncanonical_request_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(_request(), indent=2), encoding="utf-8")
    with pytest.raises(QwenFullModelSimulationError, match="not canonical JSON"):
        _canonical(path, "execution request")


def test_execution_report_publication_is_canonical_and_no_overwrite(
    tmp_path: Path,
) -> None:
    report = _schema_report()
    output = tmp_path / "nested/execution.json"
    publish_qwen_full_model_execution_report(report, output)
    assert output.read_bytes() == canonical_json_bytes(report)
    with pytest.raises(QwenFullModelSimulationError, match="already exists"):
        publish_qwen_full_model_execution_report(report, output)

    forged = dict(report)
    forged["status"] = "fail"
    with pytest.raises(QwenFullModelSimulationError, match="boundary differs"):
        publish_qwen_full_model_execution_report(forged, tmp_path / "forged.json")


def _schema_report() -> dict[str, Any]:
    digest = "b" * 64
    body = {
        "artifact_admission": {
            "all_hbm_shards_sha256_verified": True,
            "non_hbm_manifest_artifacts_sha256_verified": True,
        },
        "build_id": digest,
        "capability_id": digest,
        "claim_boundary": {
            "complete_model_one_token_execution": True,
            "decode_steps": 0,
            "exact_8000_token_acceptance": False,
            "timing_or_performance": False,
        },
        "command_abi": {"major": 2, "minor": 5},
        "command_count": 924_386,
        "command_program_sha256": digest,
        "counter_reconciliation": "complete_observed_command_and_numeric_counts",
        "counters": {
            **{f"arithmetic.synthetic_{index}": index for index in range(18)},
            "commands.total": 924_386,
            "hbm.useful_bytes_read": 1,
        },
        "events": [
            {
                "command_count": 1,
                "command_start": index,
                "kernel_index": index,
                "kind": "MATMUL",
                "operation_id": f"node.{index:04d}",
                "outputs": {
                    f"tensor.{index}": {
                        "payload_sha256": digest,
                        "size_bytes": 2,
                    }
                },
            }
            for index in range(617)
        ],
        "graph_id": digest,
        "hbm_logical_sha256": digest,
        "independent_check_id": digest,
        "kernel_ir_id": digest,
        "layer_outputs": [
            {
                "layer": layer,
                "payload_sha256": digest,
                "size_bytes": 8192,
                "tensor_id": f"hidden.{layer}",
            }
            for layer in range(1, 37)
        ],
        "mode": "artifact_only_data_bearing_functional",
        "operation_count": 617,
        "outputs": {
            "committed_logits": {
                "greedy_maximum_count": 1,
                "greedy_token_id": 0,
                "payload_sha256": digest,
                "size_bytes": 303_872,
            },
            "final_normalization": {
                "payload_sha256": digest,
                "size_bytes": 8192,
            },
            "hidden_36": {"payload_sha256": digest, "size_bytes": 8192},
            "last_token": {"payload_sha256": digest, "size_bytes": 8192},
        },
        "physical_plan_id": digest,
        "request_id": digest,
        "saturation": {
            "by_kernel": {str(index): 0 for index in range(578)},
            "total": 0,
        },
        "schema": EXECUTION_SCHEMA,
        "simulator_version": "tensor-accelerator-qwen-full-model-simulator-0.1.0",
        "source_lock_id": digest,
        "state": [
            {
                "generation": 1,
                "key_payload_sha256": digest,
                "layer": layer,
                "length": 1,
                "resource_id": f"kv.layer.{layer}",
                "value_payload_sha256": digest,
            }
            for layer in range(36)
        ],
        "status": "pass",
        "timing": {
            "reason": "capability_uncharacterized",
            "status": "unavailable",
        },
    }
    return _reidentify(body, "report_id")


def test_execution_report_schema_is_strict_and_preserves_claim_boundary() -> None:
    schema = load_strict_json(EXECUTION_REPORT_SCHEMA)
    Draft202012Validator.check_schema(schema)
    report = _schema_report()
    Draft202012Validator(schema).validate(report)

    overclaim = copy.deepcopy(report)
    overclaim["claim_boundary"]["exact_8000_token_acceptance"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(overclaim)

    fallback = copy.deepcopy(report)
    fallback["host_framework_fallback"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(fallback)


def test_simulator_has_no_compiler_checker_or_framework_fallback_import() -> None:
    source = (
        ROOT / "runtime/tensor_accelerator/qwen_full_model_simulator.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "qwen_full_model_physical import",
        "qwen_full_model_physical_checking import",
        "import torch",
        "import transformers",
        "from transformers",
    )
    assert not any(fragment in source for fragment in forbidden)


@AUTHENTIC
def test_retained_deployment_loads_at_the_exact_physical_identity() -> None:
    with QwenFullModelSimulator.load(DEPLOYMENT, verify_hbm_hashes=False) as simulator:
        assert simulator.build_id == (
            "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
        )
        assert simulator.state_generations == (0,) * 36
        assert simulator.state_lengths == (0,) * 36
        with pytest.raises(
            QwenFullModelSimulationError,
            match="verification of every HBM shard",
        ):
            simulator.execute()


@AUTHENTIC
def test_loader_rejects_extra_deployment_file(tmp_path: Path) -> None:
    candidate = shutil.copytree(
        DEPLOYMENT,
        tmp_path / "extra-file",
        copy_function=os.link,
    )
    (candidate / "unexpected.bin").write_bytes(b"unexpected")
    with pytest.raises(QwenFullModelSimulationError, match="file set differs"):
        QwenFullModelSimulator.load(candidate, verify_hbm_hashes=False)


@AUTHENTIC
def test_command_failure_preserves_all_committed_state() -> None:
    with QwenFullModelSimulator.load(DEPLOYMENT, verify_hbm_hashes=False) as simulator:
        original_generations = simulator.state_generations
        original_lengths = simulator.state_lengths
        simulator._hbm_hashes_verified = True
        simulator._commands = (
            replace(
                simulator._commands[0], source0=simulator._commands[0].source0 + 64
            ),
            *simulator._commands[1:],
        )
        with pytest.raises(QwenFullModelSimulationError, match="command 0 differs"):
            simulator.execute()
        assert simulator.state_generations == original_generations
        assert simulator.state_lengths == original_lengths
