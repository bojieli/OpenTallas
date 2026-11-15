"""KV-PVGEN 11-15: qkd_pv16_vport_b with -DOT_PV_VPORT_SELREP32 (32 kept sel copies) is edge for edge the old module:
the existing lock-step bench (vs the closed r6 module) PASSes with and without the define, and its negative controls
(MUT 1: sel flipped, MUT 5: epoch select flipped) FAIL with it, so the replicated form is not blind to a select error."""
import shutil
import subprocess
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
SRC = [R / "rtl/test/kv_bootage_1019/tb_kvba_vport.sv", R / "rtl/qwen_sys/static_kv_20261014/qkd_pv16_vport.sv",
       R / "rtl/qwen_sys/kv_bootage_20261019/qkd_pv16_vport_b.sv"]
NCYC = 800        # random-phase cycles (bench default 4000): the fault / landing / flag / invalid-age phases do not depend on it
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None or not all(f.is_file() for f in SRC),
                                reason="iverilog or the bench sources missing (sparse tree)")


def run(tmp_path, defines, mut=0):
    out = tmp_path / "t.vvp"
    cmd = ["iverilog", "-g2012", *defines, f"-Ptb_kvba_vport.MUT={mut}", f"-Ptb_kvba_vport.NCYC={NCYC}", "-o", str(out), *map(str, SRC)]
    subprocess.run(cmd, check=True, capture_output=True)
    return subprocess.run(["vvp", str(out)], check=True, capture_output=True, text=True, cwd=tmp_path, timeout=300).stdout


@pytest.mark.parametrize("defines", [[], ["-DOT_PV_VPORT_SELREP32"]])
def test_lockstep_pass(tmp_path, defines):
    assert "KVBA_VPORT PASS" in run(tmp_path, defines)


@pytest.mark.parametrize("mut", [1, 5])
def test_mutants_fail_with_selrep(tmp_path, mut):
    assert "KVBA_VPORT FAIL" in run(tmp_path, ["-DOT_PV_VPORT_SELREP32"], mut)
