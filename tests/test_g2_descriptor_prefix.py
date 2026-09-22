"""Bounded descriptor prefixes preserve arbitration, bounds and full reads."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("words", [1, 3, 6])
def test_descriptor_prefix(tmp_path, words):
    sim = tmp_path / "sim"
    subprocess.run([
        "iverilog", "-g2012", "-DOT_A3_FAKERAM_BEHAVIOURAL",
        "-s", "tb_a3_g2_descriptor_prefix",
        f"-Ptb_a3_g2_descriptor_prefix.WORDS={words}", "-o", str(sim),
        str(ROOT / "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv"),
        str(ROOT / "rtl/abi3/ot_a3_g2_descriptor_store.sv"),
        str(ROOT / "rtl/test/tb_a3_g2_descriptor_prefix.sv"),
    ], check=True, capture_output=True, text=True, timeout=30)
    result = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"PASS descriptor prefix words={words} checks=9 saved_cycles={6-words}" in result.stdout
