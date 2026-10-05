"""Bounded RTL interface gate; full-model Qwen execution is a separate gate."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "rtl/test/hostbinding"


def test_qwen_tp_host_binding(tmp_path):
    if not shutil.which("verilator"):
        pytest.skip("Verilator required")
    contract = json.loads((BINDING / "qwen_tp_host_binding.json").read_text())
    top = contract["top"]
    obj = tmp_path / "obj"
    command = [
        "verilator", "--cc", "--exe", "--build", "-j", "4", "-Wno-fatal",
        "--top-module", top, "--Mdir", str(obj),
        *[str(ROOT / source) for source in contract["sources"]],
        str(BINDING / "qwen_tp_host_binding_harness.cpp"),
    ]
    build = subprocess.run(command, capture_output=True, text=True, timeout=180)
    assert build.returncode == 0, build.stdout + build.stderr
    result = subprocess.run([str(obj / f"V{top}")], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS tie=0 cycles=55 token=131095 stalls=0" in result.stdout
    assert "PASS tie=1 cycles=55 token=70011 stalls=0" in result.stdout
