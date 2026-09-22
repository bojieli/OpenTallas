"""Keep G2's view capture and weight dimensions aligned with the real ABI."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_g2_issue_contract(tmp_path):
    image = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_g2_issue_contract",
            "-o",
            str(image),
            str(ROOT / "rtl/abi3/ot_a3_pkg.sv"),
            str(ROOT / "rtl/abi3/ot_a3_g2_array_issue_adapter.sv"),
            str(ROOT / "rtl/test/tb_a3_g2_issue_contract.sv"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["vvp", str(image)], check=True, capture_output=True, text=True, timeout=30
    )
    assert "PASS G2 issue contract checks=30" in result.stdout
