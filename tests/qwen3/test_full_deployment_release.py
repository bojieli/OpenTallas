from __future__ import annotations

import os
from pathlib import Path

import pytest

from compiler.frontend.checkpoint import load_checkpoint_lock
from compiler.ir.model import load_strict_json
from compiler.qwen3.checking import verify_deployment_artifacts, verify_physical_images
from compiler.qwen3.runtime import Qwen3ServiceEngine


DEPLOYMENT = os.environ.get("OPENTALLAS_QWEN3_DEPLOYMENT")
pytestmark = pytest.mark.skipif(
    DEPLOYMENT is None,
    reason="set OPENTALLAS_QWEN3_DEPLOYMENT for the 16.38-GB Qwen3 release gate",
)


def test_complete_real_deployment_inverse_reconstructs_and_executes() -> None:
    root = Path(DEPLOYMENT).resolve()
    manifest = load_strict_json(root / "deployment_manifest.json")
    lock = load_checkpoint_lock(root / "checkpoint.lock.json")
    physical = load_strict_json(root / "physical/physical_map.json")

    verify_deployment_artifacts(root, manifest)
    report = verify_physical_images(root, physical, lock)
    assert report["tensor_count_reconstructed"] == 399
    assert report["payload_bytes_reconstructed"] == 16_381_470_720

    engine = Qwen3ServiceEngine(root, device="cuda", attention_backend="sdpa")
    result = engine.run_span([151643], capture_layer_hashes=True)
    assert len(result.report["layer_boundaries"]) == 36
    assert result.report["counters"]["matrix_multiplications"] == 253
    assert result.report["logits"]["shape"] == [1, 1, 151936]
    assert result.report["logits"]["sha256"] == (
        "91421cfec308d469bf7313cbb1361f0f01fd5f54b778a39410cc94a279aef980"
    )
