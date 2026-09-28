import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_embed_row_hbm_record_current():
    subprocess.run([sys.executable, "tools/rtl_hdc_qwen_embed_row_hbm.py"],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    record = json.loads((ROOT / "results/rtl/qwen_embed_row_hbm.json").read_text())
    assert record["status"] == "pass"
    assert record["observed"]["sectors"] == 5
    for name, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
