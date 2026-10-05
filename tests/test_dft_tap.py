"""The JTAG TAP (rtl/dft/ot_tap.sv) and the scan clock controller, in Verilator.

rtl/test/tb_ot_tap.sv drives the TAP pins only and checks IDCODE, BYPASS (also
for an unused opcode), Capture-IR, SCAN_CFG, a full load/capture/unload scan
test of a toy core through SCAN_ACCESS, a single-chain flush, MBIST_CTRL,
DFT_STATUS, the TMS reset, TRST_N and TDO enable.  The same bench also runs
under Icarus, so the result does not rest on one simulator.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "rtl/dft/ot_tap.sv", ROOT / "rtl/dft/ot_dft_scan_clock.sv", ROOT / "rtl/test/tb_ot_tap.sv"]
VERILATOR = Path(os.environ.get(
    "OPENTALLAS_VERILATOR", Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
))
EXPECTED_CHECKS = 25


def _checks(stdout: str) -> tuple[list[str], str | None]:
    checks = re.findall(r"^CHECK (\S+) (ok|FAIL.*)$", stdout, re.M)
    result = re.search(r"^RESULT (\w+) (\d+)$", stdout, re.M)
    failed = [f"{name}: {status}" for name, status in checks if status != "ok"]
    assert len(checks) == EXPECTED_CHECKS, stdout[-2000:]
    return failed, result.group(1) if result else None


@pytest.mark.skipif(not VERILATOR.is_file(), reason="needs the pinned Verilator 5")
def test_tap_under_verilator(tmp_path):
    subprocess.run(
        [str(VERILATOR), "--binary", "--timing", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL",
         "-Wno-UNUSEDPARAM", "--top-module", "tb_ot_tap", "-Mdir", str(tmp_path), *map(str, SOURCES)],
        check=True, capture_output=True, text=True,
    )
    run = subprocess.run([str(tmp_path / "Vtb_ot_tap")], check=True, capture_output=True, text=True)
    failed, result = _checks(run.stdout)
    assert not failed and result == "pass"


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_tap_under_icarus(tmp_path):
    subprocess.run(["iverilog", "-g2012", "-o", str(tmp_path / "tb.vvp"), *map(str, SOURCES)],
                   check=True, capture_output=True, text=True)
    run = subprocess.run(["vvp", "-n", str(tmp_path / "tb.vvp")], check=True, capture_output=True, text=True)
    failed, result = _checks(run.stdout)
    assert not failed and result == "pass"


@pytest.mark.skipif(not VERILATOR.is_file(), reason="needs the pinned Verilator 5")
def test_tap_lints_clean(tmp_path):
    lint = subprocess.run(
        [str(VERILATOR), "--lint-only", "-Wall", "-Wno-DECLFILENAME", "--top-module", "ot_tap",
         str(ROOT / "rtl/dft/ot_tap.sv")],
        capture_output=True, text=True,
    )
    assert lint.returncode == 0, lint.stderr
