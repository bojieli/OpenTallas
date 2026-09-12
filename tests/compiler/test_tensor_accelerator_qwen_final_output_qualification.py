from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.qwen_final_output_qualification import (
    QwenFinalOutputQualificationError,
    load_qwen_final_output_qualification,
    publish_qwen_final_output_qualification,
    qualify_locked_qwen_final_output,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
CHECKPOINT_LOCK = ROOT / "build/qwen3-8b/checkpoint.lock.json"
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CONNECTED = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_connected_layer_execution.json"
)
RETAINED = ROOT / "results/tensor_accelerator/qwen3_final_output_qualification.json"
SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_final_output_qualification_v1.schema.json"
)
HAS_REAL_SOURCES = (
    all(path.is_file() for path in (CHECKPOINT_LOCK, GRAPH, CONNECTED, RETAINED))
    and SNAPSHOT.is_dir()
)
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES,
    reason="authentic Qwen final-output sources unavailable",
)

REPORT_ID = "bbd7abf87cdb0bd1450efe3da688b2f0ba8b2353e14f44e4a698f57cf3d2339d"
FINAL_NORM_SHA256 = "f7d59069dc6d3671f93fbe96b0f2f607b3b9b4962adedece208125b973c8ccc3"
LOGITS_SHA256 = "f367621a1bbc2e90410e00c67a9ff48ad93d5f683bdad8b86644bfeab123cff6"
ARGMAX_TOKEN_ID = 118195


def _reidentify(value: dict[str, Any], field: str) -> None:
    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()


@pytest.fixture(scope="module")
def qualification() -> dict[str, Any]:
    if not HAS_REAL_SOURCES:
        pytest.skip("authentic Qwen final-output sources unavailable")
    return qualify_locked_qwen_final_output(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        connected_execution_path=CONNECTED,
    )


@REAL
def test_final_output_qualification_is_authentic_exact_and_retained(
    qualification: dict[str, Any],
) -> None:
    retained = load_qwen_final_output_qualification(RETAINED)
    assert qualification == retained
    assert qualification["report_id"] == REPORT_ID
    assert qualification["outputs"]["final_norm"]["payload_sha256"] == (
        FINAL_NORM_SHA256
    )
    assert qualification["outputs"]["last_token"]["payload_sha256"] == (
        FINAL_NORM_SHA256
    )
    assert qualification["outputs"]["logits"] == {
        "argmax_tie_count": 1,
        "argmax_token_id": ARGMAX_TOKEN_ID,
        "payload_sha256": LOGITS_SHA256,
        "shape": [1, 151936],
    }
    assert qualification["projection_saturated_element_count"] == 0
    assert qualification["selected_reference"]["status"] == "exact_match"
    assert qualification["target_adaptation"] == {
        "classification": "qualified_operator_family_fixture",
        "framework_fallback": False,
        "full_model_claim": False,
        "input_boundary": "connected_layer_hidden_1_not_hidden_36",
        "matrix_reduction": "strictly_increasing_k_binary32_rne",
    }


@REAL
def test_final_output_qualification_validates_strict_schema(
    qualification: dict[str, Any],
) -> None:
    validator = Draft202012Validator(load_strict_json(SCHEMA))
    validator.validate(qualification)
    forged = copy.deepcopy(qualification)
    forged["target_adaptation"]["full_model_claim"] = True
    with pytest.raises(ValidationError):
        validator.validate(forged)


@REAL
def test_final_output_qualification_publishes_atomically_without_overwrite(
    qualification: dict[str, Any], tmp_path: Path
) -> None:
    output = tmp_path / "qualification.json"
    publish_qwen_final_output_qualification(qualification, output)
    assert load_qwen_final_output_qualification(output) == qualification
    with pytest.raises(QwenFinalOutputQualificationError, match="not be overwritten"):
        publish_qwen_final_output_qualification(qualification, output)


@REAL
def test_final_output_qualification_rejects_reidentified_boundary_overclaim(
    qualification: dict[str, Any], tmp_path: Path
) -> None:
    forged = copy.deepcopy(qualification)
    forged["target_adaptation"]["full_model_claim"] = True
    _reidentify(forged, "report_id")
    path = tmp_path / "forged.json"
    write_canonical_json(path, forged)
    with pytest.raises(QwenFinalOutputQualificationError, match="contract differs"):
        load_qwen_final_output_qualification(path)


@REAL
def test_final_output_qualification_rejects_reidentified_connected_corruption(
    tmp_path: Path,
) -> None:
    connected = load_strict_json(CONNECTED)
    connected["output"]["hidden_1"]["codes"][0] ^= 1
    _reidentify(connected, "report_id")
    path = tmp_path / "connected-corrupt.json"
    write_canonical_json(path, connected)
    with pytest.raises(
        QwenFinalOutputQualificationError,
        match="hidden payload identity differs",
    ):
        qualify_locked_qwen_final_output(
            snapshot=SNAPSHOT,
            checkpoint_lock_path=CHECKPOINT_LOCK,
            model_graph_path=GRAPH,
            connected_execution_path=path,
        )
