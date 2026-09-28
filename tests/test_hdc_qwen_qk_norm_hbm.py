"""Keep the real-image Q/K norm HBM verdict bound to its source."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qk_norm_hbm_source_and_exact_gate():
    record = json.loads((ROOT / "results/rtl/qwen_qk_norm_hbm.json").read_text())
    assert record["status"] == "pass"
    assert record["observed"] == {"dies": 2, "words_per_die": 2560,
                                  "sectors_per_die": 640}
    assert {x["status"] for x in record["runs"].values()} == {"pass"}
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
