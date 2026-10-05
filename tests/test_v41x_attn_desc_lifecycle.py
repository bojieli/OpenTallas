"""Source-pinned L0 packed attention descriptor lifecycle gate."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_descriptor_lifecycle_record_is_current():
    rec = json.loads((ROOT / "results/rtl/v41x_attn_desc_lifecycle.json").read_text())
    assert rec["status"] == "pass"
    assert rec["tests"]["qk_accepted_beats"] == 32
    assert rec["tests"]["pv_accepted_beats"] == 32
    for path, digest in rec["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_descriptor_lifecycle_replay_and_faults(tmp_path):
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        pytest.skip("Icarus Verilog unavailable")
    out = tmp_path / "lifecycle.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_v41x_attn_desc_lifecycle",
                    "-o", str(out), "rtl/test/tb_v41x_attn_desc_lifecycle.sv",
                    "rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv"], cwd=ROOT,
                   check=True, capture_output=True, text=True)
    run = subprocess.run(["vvp", str(out)], cwd=ROOT, check=True,
                         capture_output=True, text=True)
    assert "PASS lifecycle:" in run.stdout
