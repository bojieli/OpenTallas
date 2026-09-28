"""The INT8 PC-local window reconstructs synchronous core words exactly."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pc_window_gate_and_pins():
    subprocess.run([sys.executable, str(ROOT / "tools/rtl_hdc_qwen_int8_pc_window.py")],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    record = json.loads((ROOT / "results/rtl/qwen_o4_hbm_pc_window.json").read_text())
    assert record["status"] == "pass"
    assert record["observed"]["sector_reads"] == 6
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
