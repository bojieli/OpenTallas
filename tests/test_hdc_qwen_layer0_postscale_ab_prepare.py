"""Bind the staged full-shape CROM source A/B to its exact RTL inputs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_postscale_ab_prepare_is_source_pinned():
    record = json.loads((ROOT / "results/rtl/qwen_layer0_postscale_ab_prepare.json").read_text())
    assert record["status"] == "images_and_oracle_pinned"
    assert len(record["image_sha256"]) == 11
    assert len(record["oracle_sha256"]) == 64
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
