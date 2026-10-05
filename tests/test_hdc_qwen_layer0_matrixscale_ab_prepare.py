"""Pin the real layer inputs before claiming a matrix/scale HBM verdict."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_matrixscale_prepare_pins_same_real_images_and_oracle():
    record = json.loads((ROOT / "results/rtl/qwen_layer0_matrixscale_ab_prepare.json").read_text())
    post = json.loads((ROOT / "results/rtl/qwen_layer0_postscale_ab_prepare.json").read_text())
    assert record["status"] == "images_and_oracle_pinned"
    assert record["image_sha256"] == post["image_sha256"]
    assert record["oracle_sha256"] == post["oracle_sha256"]
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
