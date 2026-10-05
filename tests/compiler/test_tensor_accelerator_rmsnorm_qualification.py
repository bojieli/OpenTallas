from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator.common import write_canonical_json
from compiler.tensor_accelerator.rmsnorm_qualification import (
    RMSNormQualificationError,
    load_rmsnorm_qualification,
    qualify_locked_rmsnorm,
    qualify_rmsnorm_payloads,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = ROOT / "build/qwen3-8b/checkpoint.lock.json"


@pytest.mark.skipif(not SNAPSHOT.is_dir() or not LOCK.is_file(), reason="Qwen fixture unavailable")
def test_real_qwen_embedding_rmsnorm_qualification_is_exact_and_reproducible(
    tmp_path: Path,
) -> None:
    first = qualify_locked_rmsnorm(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        embedding_tensor="model.embed_tokens.weight",
        token_id=0,
        weight_tensor="model.layers.0.input_layernorm.weight",
        selected_elements=(0, 1, 2, 3, 511, 1023, 2047, 4095),
    )
    second = qualify_locked_rmsnorm(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        embedding_tensor="model.embed_tokens.weight",
        token_id=0,
        weight_tensor="model.layers.0.input_layernorm.weight",
        selected_elements=(0, 1, 2, 3, 511, 1023, 2047, 4095),
    )
    assert first == second
    assert first["input"]["row_payload_sha256"] == (
        "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
    )
    assert first["weight"]["payload_sha256"] == (
        "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
    )
    assert first["output"]["mean_square_binary32_code"] == 0x3A5BF2CA
    assert first["output"]["inverse_rms_binary32_code"] == 0x420A0297
    assert first["output"]["normalized_payload_sha256"] == (
        "bf4b81b7e711157b4e8c91bde7294d3be647844dbd7336d462201a246a1da28d"
    )
    assert first["output"]["payload_sha256"] == (
        "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
    )
    assert first["selected_reference"]["output_codes"] == [
        15516,
        15458,
        15440,
        48103,
        15148,
        15433,
        47867,
        15172,
    ]
    report_path = tmp_path / "qualification.json"
    write_canonical_json(report_path, first)
    assert load_rmsnorm_qualification(report_path) == first


def test_payload_qualification_rejects_bad_hash_shape_and_selection() -> None:
    embedding = {
        "dtype": "BF16",
        "name": "embedding",
        "payload_sha256": hashlib.sha256(b"all embedding bytes").hexdigest(),
        "shape": [2, 2],
        "size_bytes": 8,
    }
    weight_payload = bytes.fromhex("803f803f")
    weight = {
        "dtype": "BF16",
        "name": "weight",
        "payload_sha256": hashlib.sha256(weight_payload).hexdigest(),
        "shape": [2],
        "size_bytes": 4,
    }
    with pytest.raises(RMSNormQualificationError, match="weight payload differs"):
        qualify_rmsnorm_payloads(
            checkpoint_lock_id="0" * 64,
            embedding_record=embedding,
            token_id=0,
            embedding_payload=weight_payload,
            weight_record=weight,
            weight_payload=weight_payload[::-1],
            selected_elements=(0,),
        )
    with pytest.raises(RMSNormQualificationError, match="weight width differs"):
        qualify_rmsnorm_payloads(
            checkpoint_lock_id="0" * 64,
            embedding_record=embedding,
            token_id=0,
            embedding_payload=weight_payload,
            weight_record={**weight, "shape": [1], "size_bytes": 2},
            weight_payload=weight_payload,
            selected_elements=(0,),
        )
    with pytest.raises(RMSNormQualificationError, match="strictly increasing"):
        qualify_rmsnorm_payloads(
            checkpoint_lock_id="0" * 64,
            embedding_record=embedding,
            token_id=0,
            embedding_payload=weight_payload,
            weight_record=weight,
            weight_payload=weight_payload,
            selected_elements=(1, 0),
        )
