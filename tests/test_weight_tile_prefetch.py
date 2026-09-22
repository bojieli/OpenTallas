"""Prefetch reserves finite storage for responses and preserves tile identity."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/abi3/ot_a3_operand_bank_owner.sv",
    "rtl/abi3/ot_a3_runtime_weight_banks.sv",
    "rtl/abi3/ot_a3_weight_tile_prefetch.sv",
    "rtl/test/tb_a3_runtime_weight_banks.sv",
    "rtl/test/tb_a3_weight_tile_prefetch.sv",
]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("depth", [3, 4, 8])
def test_tile_prefetch_overlap_and_order(tmp_path, depth):
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_weight_tile_prefetch",
            f"-Ptb_a3_weight_tile_prefetch.FIFO_DEPTH={depth}",
            "-o",
            str(sim),
            *[str(ROOT / p) for p in SOURCES],
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS tile prefetch words=76 max_contiguous=32" in run.stdout
