"""Bounded request reservations, independent responses, identity and flush."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("depth", [1, 2, 3, 8])
def test_auxiliary_prefetch(tmp_path, depth):
    sim = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_lq8_auxiliary_prefetch",
            f"-Ptb_a3_lq8_auxiliary_prefetch.DEPTH={depth}",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_lq8_auxiliary_prefetch.sv"),
            str(ROOT / "rtl/test/tb_a3_lq8_auxiliary_prefetch.sv"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"PASS auxiliary prefetch depth={depth} words=200 peak={depth}" in run.stdout
