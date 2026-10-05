"""Source-pinned bounded full-shape packed attention adapter gate."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_packed_bypass_record_is_current():
    rec = json.loads((ROOT / "results/rtl/v41x_attn_packed_bypass.json").read_text())
    assert rec["status"] == "pass"
    assert rec["full_shape_stub_lint"]["status"] == "pass"
    assert rec["bounded_handshake"]["qk_beats"] == 2
    assert rec["bounded_handshake"]["pv_beats"] == 2
    assert rec["bounded_handshake"]["scalar_kv_reads"] == 0
    for path, digest in rec["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_packed_bypass_qk_pv_handshake(tmp_path):
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        pytest.skip("Icarus Verilog unavailable")
    out = tmp_path / "bypass.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_v41x_attn_packed_bypass",
                    "-DV41X_ATTN_SERVICE_LINT_STUB", "-o", str(out),
                    "rtl/test/tb_v41x_attn_packed_bypass.sv",
                    "rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv",
                    "rtl/test/ot_hdc_v41x_attn_service_lint_stub.sv"], cwd=ROOT,
                   check=True, capture_output=True, text=True)
    run = subprocess.run(["vvp", str(out)], cwd=ROOT, check=True,
                         capture_output=True, text=True)
    assert "PASS packed adapter QK/PV bypass" in run.stdout
