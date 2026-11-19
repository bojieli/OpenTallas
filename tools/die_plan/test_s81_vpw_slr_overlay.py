"""S81-VPW-SLR: s81_vpw_slr_overlay.py on the fixture VP source (after the XR overlay), and the lock-step bench with iverilog.
    python3 -m pytest -q tools/die_plan/test_s81_vpw_slr_overlay.py"""
import gzip
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vp_xr_overlay as X  # noqa: E402
import s81_vpw_slr_overlay as S  # noqa: E402
import test_s81_vp_xr_overlay as TX  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    for src, dst in TX.FILES.items():
        p = tmp_path / dst
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(gzip.decompress((TX.FX / src).read_bytes()))
    (tmp_path / "physical/die_plan/s81/bind/source_modules").mkdir(parents=True, exist_ok=True)
    assert X.main([str(tmp_path), "--die", "3S=01000"]) == 0
    return tmp_path


def test_overlay_edits_only_vpw_and_refuses_twice(tree):
    before = (tree / S.VP).read_text()
    assert S.main([str(tree)]) == 0
    after = (tree / S.VP).read_text()
    cut = before.index("module ot_s81sl_vpw")
    assert after[:cut] == before[:cut]                                    # nothing of ot_s81sl_vp moves (bind names keep their lines)
    assert "parameter integer SLR = XR) (" in after and "wdo_q[k] <= n_wdo_s[k];" in after
    assert after.count("(* keep *) reg [4:0] sv_q;") == 1 and "end else begin : g_nslr" in after
    assert "n_wa[b] = hi_sw ?" in after                                   # address / mask / collision decode untouched
    with pytest.raises(SystemExit, match="SLR_OVERLAY_TWICE"):
        S.main([str(tree)])


def test_overlay_needs_the_xr_form(tmp_path):
    p = tmp_path / S.VP
    p.parent.mkdir(parents=True)
    p.write_bytes(gzip.decompress((TX.FX / "ot_s81sl_vp.sv.gz").read_bytes()))  # WRP only, no XR
    with pytest.raises(SystemExit, match="SLR_OVERLAY_MISS"):
        S.main([str(tmp_path)])


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("ctl,want", [("", "PASS"), ("-DCTL_XR0", "FAIL")])
def test_lockstep_same_cycle(tree, tmp_path, ctl, want):
    assert S.main([str(tree)]) == 0
    vp = (tree / S.VP).read_text()
    mod = tmp_path / "vpw.sv"
    mod.write_text(vp[vp.index("module ot_s81sl_vpw"):])
    out = tmp_path / "tb.vvp"
    cmd = ["iverilog", "-g2012", "-DNCYC=40000", "-o", str(out), str(HERE / "fixtures/s81_vp_xr/tb_vpw_slr.sv"), str(mod)] + ([ctl] if ctl else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    res = subprocess.run(["vvp", str(out)], capture_output=True, text=True).stdout
    line = [x for x in res.splitlines() if "VPW_SLR_RESULT" in x][-1]
    assert f"VPW_SLR_RESULT {want}" in line, line
    if want == "PASS":
        assert "errors 0" in line and int(line.split("with data ")[1].split(",")[0]) > 3000   # the data path was exercised
