from __future__ import annotations

from pathlib import Path

import pytest

from compiler.tensor_accelerator.layer_qualification import (
    OFFICIAL_REPLAY_DIFFERING_ELEMENTS,
    OFFICIAL_REPLAY_SHA256,
    TARGET_KNOWN_ANSWER_SHA256,
    LayerQualificationError,
    load_layer_qualification,
    publish_layer_qualification,
    qualify_locked_layer,
)
from compiler.tensor_accelerator.common import canonical_json_bytes, sha256_bytes


SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = Path("/home/ubuntu/OpenTallas/build/qwen3-8b/checkpoint.lock.json")
ATTENTION = Path(
    "results/tensor_accelerator/qwen3_hbm_sram_attention_execution.json"
)
RETAINED = Path("results/tensor_accelerator/qwen3_layer_qualification.json")
HAS_REAL_SOURCES = SNAPSHOT.is_dir() and LOCK.is_file() and ATTENTION.is_file()
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES,
    reason="pinned Qwen layer sources unavailable",
)
PROJECTION_ROWS = {
    "attention_output": [0, 1, 127, 128, 1023, 2047, 3071, 4095],
    "down": [0, 1, 127, 128, 1023, 2047, 3071, 4095],
    "gate": [0, 1, 127, 128, 1023, 4095, 8191, 12287],
    "up": [0, 1, 127, 128, 1023, 4095, 8191, 12287],
}
OUTPUT_WIDTHS = {
    "attention_projected": 4096,
    "down": 4096,
    "gate": 12288,
    "gated_mlp": 12288,
    "hidden_0": 4096,
    "hidden_1": 4096,
    "mlp_norm": 4096,
    "post_attention": 4096,
    "silu_activation": 12288,
    "up": 12288,
}
OUTPUT_ELEMENTS = {
    role: (
        [0, 1, 127, 128, 1023, 2047, 3071, width - 1]
        if width == 4096
        else [0, 1, 127, 128, 1023, 4095, 8191, width - 1]
    )
    for role, width in OUTPUT_WIDTHS.items()
}


def _qualify() -> dict[str, object]:
    return qualify_locked_layer(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        attention_execution_path=ATTENTION,
        token_id=0,
        selected_projection_rows=PROJECTION_ROWS,
        selected_output_elements=OUTPUT_ELEMENTS,
    )


@REAL
def test_authentic_layer_qualification_is_deterministic_and_independent(
    tmp_path: Path,
) -> None:
    first = _qualify()
    second = _qualify()
    assert first == second
    assert load_layer_qualification(RETAINED) == first
    assert first["report_id"] == (
        "94cc82dd113e16f05795c0de36930800701014e37e08267ce355ecfba3cfeea9"
    )
    assert first["output"] == {
        "hidden_1": {
            "payload_sha256": TARGET_KNOWN_ANSWER_SHA256["hidden_1"],
            "shape": [1, 4096],
        }
    }
    assert first["official_source_replay"] == {
        "differing_element_count": OFFICIAL_REPLAY_DIFFERING_ELEMENTS,
        "implementation": "pinned_transformers_qwen3_cpu_bf16",
        "known_answer_payload_sha256": OFFICIAL_REPLAY_SHA256,
        "source_sha256": (
            "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
        ),
        "status": "qualified_deterministic_target_adaptation",
    }
    assert first["accounting"] == {
        "epsilon_additions": 1,
        "final_weight_multiplications": 4096,
        "input_square_multiplications": 4096,
        "mean_divisions": 1,
        "normalization_multiplications": 4096,
        "projection_accumulation_additions": 167_772_160,
        "projection_multiplications": 167_772_160,
        "reciprocal_square_roots": 1,
        "reduction_additions": 4095,
        "residual_additions": 8192,
        "sigmoid_denominator_additions": 12288,
        "sigmoid_divisions": 12288,
        "sigmoid_exponentials": 12288,
        "silu_multiplications": 12288,
        "up_gate_multiplications": 12288,
    }
    assert first["projection_saturated_element_count"] == {
        "attention_output": 0,
        "down": 0,
        "gate": 0,
        "up": 0,
    }
    assert first["rmsnorm_saturated_element_count"] == {
        "normalized": 0,
        "output": 0,
    }
    assert first["vector_saturated_element_count"] == {
        "attention_residual": 0,
        "final_residual": 0,
        "silu_activation": 0,
        "silu_output": 0,
    }
    output = tmp_path / "qualification.json"
    publish_layer_qualification(first, output)
    assert load_layer_qualification(output) == first
    with pytest.raises(LayerQualificationError, match="will not be overwritten"):
        publish_layer_qualification(first, output)


def test_loader_rejects_noncanonical_or_forged_layer_qualification(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"status": "pass"}\n', encoding="utf-8")
    with pytest.raises(LayerQualificationError, match="not canonical"):
        load_layer_qualification(malformed)

    forged = load_layer_qualification(RETAINED)
    forged["undeclared_evidence"] = {"status": "pass"}
    body = {key: value for key, value in forged.items() if key != "report_id"}
    forged["report_id"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(LayerQualificationError, match="key set differs"):
        publish_layer_qualification(forged, tmp_path / "forged-published.json")
    forged_path = tmp_path / "forged.json"
    forged_path.write_bytes(canonical_json_bytes(forged))
    with pytest.raises(LayerQualificationError, match="key set differs"):
        load_layer_qualification(forged_path)


def test_layer_qualification_has_no_framework_or_production_lowering_dependency() -> None:
    module = __import__(
        "compiler.tensor_accelerator.layer_qualification",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "import torch" not in source.lower()
    assert "import transformers" not in source.lower()
    assert "production_" not in source.lower()
