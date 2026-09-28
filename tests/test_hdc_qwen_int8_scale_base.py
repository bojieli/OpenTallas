import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scale_base_gates_current():
    subprocess.run([sys.executable, "tools/rtl_hdc_qwen_int8_scale_base.py"],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    record = json.loads((ROOT / "results/rtl/qwen_int8_scale_base.json").read_text())
    assert record["status"] == "pass"
    assert len(record["gates"]) == 4
