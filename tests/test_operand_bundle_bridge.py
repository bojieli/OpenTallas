"""Bundle reservation must preserve the lane's registered-memory timing."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_operand_bundle_timing(tmp_path):
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_operand_bundle_bridge",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_operand_bundle_bridge.sv"),
            str(ROOT / "rtl/test/tb_a3_operand_bundle_bridge.sv"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS bundle bridge" in run.stdout
