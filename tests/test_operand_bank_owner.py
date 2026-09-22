"""Ownership must prevent stale writes and premature reuse across runtime tiles."""

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("memory", [False, True])
def test_operand_bank_ownership_protocol(tmp_path, memory):
    top = "tb_a3_runtime_weight_banks" if memory else "tb_a3_operand_bank_owner"
    sources = [ROOT / "rtl/abi3/ot_a3_operand_bank_owner.sv"]
    if memory:
        sources.append(ROOT / "rtl/abi3/ot_a3_runtime_weight_banks.sv")
    sources.append(ROOT / "rtl/test" / f"{top}.sv")
    sim = tmp_path / "owner.vvp"
    compiled = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            top,
            "-o",
            str(sim),
            *map(str, sources),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run(
        ["vvp", str(sim)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "PASS runtime weight banks" if memory else "PASS operand bank ownership"
    ) in result.stdout
