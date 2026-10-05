"""ot_hdc_mtp_accept_caller (protected DS MTP accept leaf behind the core's ot_hdc_accept ABI) against
ot_hdc_accept: 48 speculative steps, accepted lengths 0..5, plus a mutant (one TOKX dropped) that must fail."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ["rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv", "rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv",
       "rtl/hdc/ot_hdc_mtp_accept_caller.sv", "rtl/hdc/ot_hdc_accept.sv", "rtl/test/tb_hdc_mtp_accept_caller.sv"]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_caller_matches_ot_hdc_accept(tmp_path):
    vvp = tmp_path / "cal.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_mtp_accept_caller", "-o", str(vvp), *SRC], cwd=ROOT, check=True)
    out = subprocess.run(["vvp", "-n", str(vvp)], capture_output=True, text=True).stdout
    assert "PASS" in out and "accepted_hist=8,8,8,8,8,8" in out, out[-2000:]
    mut = subprocess.run(["vvp", "-n", str(vvp), "+MUTATE"], capture_output=True, text=True).stdout
    assert "FAIL" in mut and "fault=1" in mut, mut[-2000:]
