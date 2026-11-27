"""PC11 B1 kind11 commit-record path (default-off): native Verilator sim of the K/HOST sender, the C safe7 receiver and the
default-off identity against the pre-existing commit-record modules. Single context only (mctx faults).  The static-service B1
landing is applied from a patch to a temp copy: the live service is not changed and nothing here is wired into any kit."""
import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "rtl/qwen_split"
PC = SRC / "pc11_b1"
VERILATOR = shutil.which("verilator") or str(Path.home() / ".local/opentallas-tools/bin/verilator")
pytestmark = pytest.mark.skipif(not Path(VERILATOR).exists() and not shutil.which("verilator"), reason="verilator required")


def _build(tmp_path, top, files):
    mdir = tmp_path / ("obj_" + top)
    r = subprocess.run([VERILATOR, "--binary", "--timing", "-j", "4", "-Wno-fatal", "--top-module", top, "--Mdir", str(mdir)] + [str(f) for f in files],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return mdir / ("V" + top)


@pytest.fixture(scope="module")
def tb_k11(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("k11")
    svc = tmp / "qfd_native59_static_service_obs1.sv"
    shutil.copy(SRC / "qfd_native59_static_service_obs1.sv", svc)
    p = subprocess.run(["patch", "-s", "-p1", str(svc), "-i", str(PC / "fixtures/static_service_pcc_b1.patch")], cwd=tmp, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return tmp, _build(tmp, "tb_k11", [PC / "tb/tb_k11.sv", PC / "qkd_pc11_b1_kind11.sv", svc, SRC / "mu/qfd_status_obs_hold_chunk.sv"])


@pytest.mark.parametrize("arm", range(10))
def test_kind11_arms(tb_k11, arm):
    tmp, exe = tb_k11
    r = subprocess.run([str(exe), f"+ARM={arm}"], cwd=tmp, capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert r.returncode == 0 and "K11_RESULT" in out and "%Error" not in out and "Fatal" not in out, out[-1500:]
    m = re.search(r"completed=(\d+) fault=(\d+)", out)
    assert m
    completed, fault = m.group(1), m.group(2)
    # copy order printed msb first: [2]=plain legacy copy, [1:0]=protected copies
    assert completed[0] == "1" and fault[0] == "0", out
    assert (completed[1:] == "11" and fault[1:] == "00") if arm == 0 else (completed[1:] == "00" and fault[1:] in ("11", "00")), out


def test_default_off_identical_to_stock_records(tmp_path):
    exe = _build(tmp_path, "tb_off", [PC / "tb/tb_off.sv", PC / "qkd_pc11_b1_kind11.sv", PC / "fixtures/qwen_pc11_commit_record.sv"])
    r = subprocess.run([str(exe)], cwd=tmp_path, capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert r.returncode == 0 and "mismatches=0" in out, out[-1500:]
