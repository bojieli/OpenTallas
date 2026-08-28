from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.attention_qualification import (
    AttentionQualificationError,
    load_attention_qualification,
    publish_attention_qualification,
    qualify_qkv_attention,
)
from compiler.tensor_accelerator.common import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[2]
QKV_EXECUTION = ROOT / "results/tensor_accelerator/qwen3_hbm_sram_qkv_execution.json"
PINNED_SOURCE = Path(
    "/home/ubuntu/OpenTallas/build/qwen3-8b/reference-venv/lib/python3.10/"
    "site-packages/transformers/models/qwen3/modeling_qwen3.py"
)
SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/attention_qualification_v1.schema.json"
)
HAS_SOURCES = QKV_EXECUTION.is_file() and PINNED_SOURCE.is_file()
REAL = pytest.mark.skipif(
    not HAS_SOURCES,
    reason="retained Q/K/V execution or pinned Qwen source unavailable",
)


def _qualify() -> dict[str, object]:
    return qualify_qkv_attention(
        qkv_execution_path=QKV_EXECUTION,
        modeling_source_path=PINNED_SOURCE,
    )


@REAL
def test_real_qkv_attention_qualification_is_deterministic_strict_and_exact(
    tmp_path: Path,
) -> None:
    first = _qualify()
    second = _qualify()
    assert first == second
    assert first["report_id"] == (
        "82bd8f8b687e6674d72220b6a749e43da5224a22ba3bbeba562284a449d5a5bd"
    )
    fixtures = {item["fixture_id"]: item for item in first["fixtures"]}
    assert set(fixtures) == {
        "authentic_empty_history",
        "checkpoint_derived_causal_prefill",
        "checkpoint_derived_nonempty_history",
    }
    assert fixtures["authentic_empty_history"]["outputs"] == {
        "attention": {
            "payload_sha256": (
                "1290713a7a352e6cd41670e31fe3462cd4d6fd714859deca4022d320eab8d819"
            ),
            "shape": [1, 32, 128],
        },
        "probabilities": {
            "payload_sha256": (
                "26ab507cf4bbb401acc7bebf555f8cd2130512b6c6ba2eb38e94aafcaeae114a"
            ),
            "shape": [1, 32, 1],
        },
        "scaled_scores": {
            "payload_sha256": (
                "8d329919350507b7e0b24604598f6af732c7a8a82810218c4e3f3e845dc71ee5"
            ),
            "shape": [1, 32, 1],
        },
    }
    assert fixtures["checkpoint_derived_nonempty_history"]["outputs"] == {
        "attention": {
            "payload_sha256": (
                "d53e8a3890eb01357fb60ec2607a716179cec0eb556e28629963af655cd3e1fb"
            ),
            "shape": [1, 32, 128],
        },
        "probabilities": {
            "payload_sha256": (
                "eb557e71a0d0110f467343eac7be5edd832c2ff79617b96c9bde777ad7a73685"
            ),
            "shape": [1, 32, 4],
        },
        "scaled_scores": {
            "payload_sha256": (
                "65c111d6a5026a86aaa86264d1cad5b97b10e8c871ba96e56e19f4b3f206fac3"
            ),
            "shape": [1, 32, 4],
        },
    }
    prefill = fixtures["checkpoint_derived_causal_prefill"]
    assert prefill["selected_probability_codes"][0]["codes"][1] == 0
    assert first["transaction_qualification"] == {
        "abort_preserved_all_resources": True,
        "committed_state_sha256": [
            "214b9ff612200f6926365c083e32e29cf1130ab496c6f5cfeb8237e033f58e16",
            "cdac1f9b58ae8ea1c4fd8a2f6f9a7d6d687bc7d22490c8833745a56bb647c0c8",
        ],
        "generation_checked": True,
        "mixed_transaction_rejected": True,
        "resource_count": 2,
        "status": "pass",
    }

    schema = __import__("json").loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first)
    output = tmp_path / "attention_qualification.json"
    publish_attention_qualification(first, output)
    assert load_attention_qualification(output) == first
    with pytest.raises(AttentionQualificationError, match="will not be overwritten"):
        publish_attention_qualification(first, output)


def test_attention_qualification_loader_rejects_noncanonical_and_forged(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"status": "pass"}\n', encoding="utf-8")
    with pytest.raises(AttentionQualificationError, match="not canonical"):
        load_attention_qualification(malformed)

    if HAS_SOURCES:
        forged_value = _qualify()
        forged_value["status"] = "fail"
        forged = tmp_path / "forged.json"
        forged.write_bytes(canonical_json_bytes(forged_value))
        with pytest.raises(AttentionQualificationError, match="contract differs"):
            load_attention_qualification(forged)


def test_attention_qualification_has_no_framework_execution_dependency() -> None:
    module = __import__(
        "compiler.tensor_accelerator.attention_qualification",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8").lower()
    assert "import torch" not in source
    assert "import transformers" not in source
