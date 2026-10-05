"""Complete-bundle admission must reject mixed identities and align all planes."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_lq8_operand_join(tmp_path):
    sim = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_lq8_operand_join",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_lq8_operand_join.sv"),
            str(ROOT / "rtl/test/tb_a3_lq8_operand_join.sv"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS LQ8 operand join" in run.stdout
