from __future__ import annotations

from pathlib import Path

import pytest

from compiler.tensor_accelerator.qkv_qualification import (
    COEFFICIENT_TABLE_SHA256,
    OFFICIAL_KNOWN_ANSWER_SHA256,
    QKVQualificationError,
    load_qkv_qualification,
    publish_qkv_qualification,
    qualify_locked_qkv,
)


SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = Path("/home/ubuntu/OpenTallas/build/qwen3-8b/checkpoint.lock.json")
HAS_REAL_SOURCES = SNAPSHOT.is_dir() and LOCK.is_file()
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES, reason="pinned Qwen sources unavailable"
)
PROJECTION_ROWS = {
    "q": [0, 1, 127, 128, 1023, 2047, 3071, 4095],
    "k": [0, 1, 127, 128, 255, 511, 767, 1023],
    "v": [0, 1, 127, 128, 255, 511, 767, 1023],
}
OUTPUT_ELEMENTS = PROJECTION_ROWS


def _qualify() -> dict[str, object]:
    return qualify_locked_qkv(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        token_id=0,
        position_id=7999,
        selected_projection_rows=PROJECTION_ROWS,
        selected_output_elements=OUTPUT_ELEMENTS,
    )


@REAL
def test_real_qkv_qualification_is_deterministic_independent_and_official_exact(
    tmp_path: Path,
) -> None:
    first = _qualify()
    second = _qualify()
    assert first == second
    assert first["report_id"] == (
        "42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae"
    )
    assert first["official_reference"] == {
        "implementation": "pinned_transformers_qwen3_cpu_bf16",
        "known_answer_payload_sha256": OFFICIAL_KNOWN_ANSWER_SHA256,
        "source_sha256": (
            "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
        ),
        "status": "exact_match",
    }
    assert first["rope"]["coefficient_table_payload_sha256"] == (
        COEFFICIENT_TABLE_SHA256
    )
    assert first["accounting"] == {
        "coefficient_table_bytes": 4_096_000,
        "epsilon_additions": 41,
        "final_weight_multiplications": 9_216,
        "input_square_multiplications": 9_216,
        "mean_divisions": 41,
        "normalization_multiplications": 9_216,
        "projection_accumulation_additions": 25_165_824,
        "projection_multiplications": 25_165_824,
        "reciprocal_square_roots": 41,
        "reduction_additions": 9_175,
        "rope_additions": 5_120,
        "rope_multiplications": 10_240,
    }
    output = tmp_path / "qualification.json"
    publish_qkv_qualification(first, output)
    assert load_qkv_qualification(output) == first
    with pytest.raises(QKVQualificationError, match="will not be overwritten"):
        publish_qkv_qualification(first, output)


def test_loader_rejects_noncanonical_or_forged_qualification(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"status": "pass"}\n', encoding="utf-8")
    with pytest.raises(QKVQualificationError, match="not canonical"):
        load_qkv_qualification(malformed)


def test_qualification_has_no_framework_or_model_execution_dependency() -> None:
    module = __import__(
        "compiler.tensor_accelerator.qkv_qualification",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "import torch" not in source.lower()
    assert "import transformers" not in source.lower()
