"""Keep the real layer-0 post-TP scale HBM supply gate source-pinned."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_post_tp_scale_hbm_real_image_gate():
    record = json.loads((ROOT / "results/rtl/qwen_post_tp_scale_hbm.json").read_text())
    assert record["status"] == "pass"
    assert record["observed"] == {"dies": 2, "words_per_die": 8192,
                                  "sectors_per_die": 2048}
    assert all(run["status"] == "pass" for run in record["runs"].values())
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    for die in (0, 1):
        image = Path(f"/tmp/qwen-real-layer0-d{die}")
        if image.exists():
            assert hashlib.sha256((image / "crom.hex").read_bytes()).hexdigest() == \
                record["image_sha256"][f"die{die}"]["crom"]


def test_head_final_norm_hbm_binding_gate():
    record = json.loads((ROOT / "results/rtl/qwen_head_norm_hbm.json").read_text())
    assert record["status"] == "pass"
    assert record["observed"] == {"dies": 1, "words_per_die": 4096,
                                  "sectors_per_die": 1024}
    assert record["runs"]["head"]["status"] == "pass"
    assert len(record["image_sha256"]["head"]["source"]) == 64
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
