from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import numpy as np
import pytest

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from runtime.tensor_accelerator.attention import make_kv_snapshot
from runtime.tensor_accelerator.qwen_full_model_checkpoint import (
    QwenFullModelCheckpointError,
    load_dynamic_runtime_checkpoint,
    publish_dynamic_runtime_checkpoint,
    validate_checkpoint_manifest,
    validate_dynamic_checkpoint_manifest,
    validate_dynamic_checkpoint_predecessor,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/compiler/tensor_accelerator"
RETAINED_V1 = (
    ROOT
    / "results/tensor_accelerator/qwen3_long_acceptance_restart_v1/"
    "checkpoint.0001/checkpoint_manifest.json"
)


def _reidentify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _bindings() -> dict[str, str]:
    return {
        "build_id": "a" * 64,
        "capability_id": "b" * 64,
        "checkpoint_lock_id": "c" * 64,
        "command_program_sha256": "d" * 64,
        "graph_id": "e" * 64,
        "hbm_logical_sha256": "f" * 64,
        "kernel_ir_id": "0" * 64,
        "physical_plan_id": "1" * 64,
        "session_id": "2" * 64,
    }


def _states(length: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for layer in range(36):
        keys = np.full((length, 8, 128), layer + 1, dtype=np.uint16)
        values = np.full((length, 8, 128), layer + 101, dtype=np.uint16)
        result[f"kv.layer.{layer}"] = make_kv_snapshot(
            resource_id=f"kv.layer.{layer}",
            generation=length,
            capacity=8000,
            key_values=keys,
            value_values=values,
        )
    return result


def _predecessor(
    bindings: dict[str, str], states: dict[str, Any], length: int, token: int
) -> dict[str, Any]:
    body = {
        "outputs": {"committed_logits": {"greedy_token_id": token}},
        "session_id": bindings["session_id"],
        "state": [
            {
                "generation": length,
                "key_payload_sha256": hashlib.sha256(
                    np.ascontiguousarray(
                        states[f"kv.layer.{layer}"].key_values, dtype="<u2"
                    ).tobytes()
                ).hexdigest(),
                "layer": layer,
                "length": length,
                "resource_id": f"kv.layer.{layer}",
                "value_payload_sha256": hashlib.sha256(
                    np.ascontiguousarray(
                        states[f"kv.layer.{layer}"].value_values, dtype="<u2"
                    ).tobytes()
                ).hexdigest(),
            }
            for layer in range(36)
        ],
        "step_index": length - 1,
    }
    return _reidentify(body, "report_id")


def test_dynamic_checkpoint_v2_round_trips_all_state_and_preserves_v1(
    tmp_path: Path,
) -> None:
    bindings = _bindings()
    states = _states(2)
    predecessor = _predecessor(bindings, states, 2, 33975)
    output = tmp_path / "checkpoint"
    manifest = publish_dynamic_runtime_checkpoint(
        output=output,
        bindings=bindings,
        context_capacity=8000,
        next_step_index=2,
        previous_report_id=predecessor["report_id"],
        previous_greedy_token_id=33975,
        states=states,
    )
    assert validate_dynamic_checkpoint_predecessor(manifest, predecessor) == manifest
    assert validate_dynamic_checkpoint_manifest(
        manifest,
        expected_bindings=bindings,
        expected_context_capacity=8000,
    ) == manifest
    schema = load_strict_json(
        SCHEMA_ROOT / "qwen_full_model_runtime_checkpoint_v2.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)

    rebuilt_manifest, rebuilt_states = load_dynamic_runtime_checkpoint(
        output,
        expected_bindings=bindings,
        expected_context_capacity=8000,
    )
    assert rebuilt_manifest == manifest
    for resource, expected in states.items():
        observed = rebuilt_states[resource]
        assert observed.capacity == 8000
        assert observed.generation == expected.generation
        assert np.array_equal(observed.key_values, expected.key_values)
        assert np.array_equal(observed.value_values, expected.value_values)
        assert not observed.key_values.flags.writeable
        assert not observed.value_values.flags.writeable

    with pytest.raises(ArtifactError, match="unknown.*execution_mode"):
        validate_checkpoint_manifest(manifest)
    retained = load_strict_json(RETAINED_V1)
    assert validate_checkpoint_manifest(retained) == retained
    assert retained["checkpoint_id"] == (
        "20cfc61600b1b86b58e9aa677f17f195df4fdecba4e20a4d5db660dc4bb5e4b2"
    )


def test_dynamic_checkpoint_v2_rejects_mode_binding_predecessor_and_corruption(
    tmp_path: Path,
) -> None:
    bindings = _bindings()
    states = _states(2)
    predecessor = _predecessor(bindings, states, 2, 33975)
    output = tmp_path / "checkpoint"
    manifest = publish_dynamic_runtime_checkpoint(
        output=output,
        bindings=bindings,
        context_capacity=8000,
        next_step_index=2,
        previous_report_id=predecessor["report_id"],
        previous_greedy_token_id=33975,
        states=states,
    )

    wrong_mode = copy.deepcopy(manifest)
    wrong_mode["execution_mode"] = "long_acceptance_v1"
    wrong_mode = _reidentify(wrong_mode, "checkpoint_id")
    with pytest.raises(QwenFullModelCheckpointError, match="boundary differs"):
        validate_dynamic_checkpoint_manifest(wrong_mode)

    wrong_bindings = dict(bindings)
    wrong_bindings["session_id"] = "3" * 64
    with pytest.raises(QwenFullModelCheckpointError, match="binding differs"):
        load_dynamic_runtime_checkpoint(
            output,
            expected_bindings=wrong_bindings,
            expected_context_capacity=8000,
        )

    forged_predecessor = copy.deepcopy(predecessor)
    forged_predecessor["state"][0]["key_payload_sha256"] = "4" * 64
    forged_predecessor = _reidentify(forged_predecessor, "report_id")
    forged_manifest = copy.deepcopy(manifest)
    forged_manifest["previous_report_id"] = forged_predecessor["report_id"]
    forged_manifest = _reidentify(forged_manifest, "checkpoint_id")
    with pytest.raises(QwenFullModelCheckpointError, match="state differs"):
        validate_dynamic_checkpoint_predecessor(
            forged_manifest, forged_predecessor
        )

    shard = output / manifest["state_image"]["shards"][0]["path"]
    with shard.open("r+b") as handle:
        first = handle.read(1)
        handle.seek(0)
        handle.write(bytes([first[0] ^ 1]))
    with pytest.raises(QwenFullModelCheckpointError, match="hash differs"):
        load_dynamic_runtime_checkpoint(
            output,
            expected_bindings=bindings,
            expected_context_capacity=8000,
        )


def test_dynamic_checkpoint_v2_failure_never_publishes_partial_root(
    tmp_path: Path,
) -> None:
    states = _states(2)
    states.pop("kv.layer.35")
    output = tmp_path / "checkpoint"
    with pytest.raises(QwenFullModelCheckpointError, match="resources differ"):
        publish_dynamic_runtime_checkpoint(
            output=output,
            bindings=_bindings(),
            context_capacity=8000,
            next_step_index=2,
            previous_report_id="5" * 64,
            previous_greedy_token_id=1,
            states=states,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".checkpoint.tmp-*"))
