"""S81-VPW-WREG: s81_vpw_wreg_overlay.py on the fixture VP source (after the XR overlay, with and without SLR), and the
lock-step bench with iverilog: +1 clk on every vpw output with OT_S81SL_VP_WREG, same cycle (inert) without it.
    python3 -m pytest -q tools/die_plan/test_s81_vpw_wreg_overlay.py"""
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
import s81_vpw_wreg_overlay as W  # noqa: E402
import test_s81_vp_xr_overlay as TX  # noqa: E402

TB = HERE / "fixtures/s81_vp_xr/tb_vpw_wreg.sv"


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
    before = (tree / W.VP).read_text()
    assert W.main([str(tree)]) == 0
    after = (tree / W.VP).read_text()
    cut = before.index("module ot_s81sl_vpw")
    assert after[:cut] == before[:cut]                    # ot_s81sl_vp is untouched: no vp line moves, no vp latency changes
    assert "localparam integer CS_HI_E = CS_HI_D + XR;" in after   # lane HI stations unchanged (only the write port moves)
    vpw = after[after.index("module ot_s81sl_vpw"):]
    assert vpw.startswith("module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0, "
                          "parameter integer WREG = `OT_S81SL_VP_WREG_DEFAULT) (")
    assert "`ifdef OT_S81SL_VP_WREG\n`define OT_S81SL_VP_WREG_DEFAULT 1\n`else\n`define OT_S81SL_VP_WREG_DEFAULT 0" in after
    for a in ("wdo_q[k] <= w_wdo[k];", "wv_q <= w_wv; wcol_q <= w_wcol;", "xl_q[k] <= {REP{w_xl[k]}};", "& xwd_w[SL * gr +: SL]",
              "p_wdo[j] <= n_wdo[j];", "end else begin : g_nwreg"):
        assert a in vpw, a
    with pytest.raises(SystemExit, match="WREG_OVERLAY_TWICE"):
        W.main([str(tree)])


def test_overlay_on_slr_form(tree):
    assert S.main([str(tree)]) == 0
    assert W.main([str(tree)]) == 0
    vpw = (tree / W.VP).read_text().split("module ot_s81sl_vpw", 1)[1]
    assert "parameter integer SLR = XR, parameter integer WREG = `OT_S81SL_VP_WREG_DEFAULT) (" in vpw
    assert "p_wdo[j] <= n_wdo_s[j];" in vpw and "assign w_wdo[0] = n_wdo_s[0];" in vpw


def test_overlay_needs_the_xr_form(tmp_path):
    p = tmp_path / W.VP
    p.parent.mkdir(parents=True)
    p.write_bytes(gzip.decompress((TX.FX / "ot_s81sl_vp.sv.gz").read_bytes()))  # WRP only, no XR
    with pytest.raises(SystemExit, match="WREG_OVERLAY_MISS"):
        W.main([str(tmp_path)])


def bench(tree, tmp_path, defs, shift, slr=False, mutate=None):
    if slr:
        assert S.main([str(tree)]) == 0
    assert W.main([str(tree)]) == 0
    vp = (tree / W.VP).read_text()
    src = vp[vp.index("`ifdef OT_S81SL_VP_WREG"):]
    if mutate:
        assert src.count(mutate[0]) == 1
        src = src.replace(*mutate)
    mod = tmp_path / "vpw.sv"
    mod.write_text(src)
    out = tmp_path / "tb.vvp"
    cmd = ["iverilog", "-g2012", "-DNCYC=40000", f"-DSHIFT={shift}", *defs, "-o", str(out), str(TB), str(mod)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    res = subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True).stdout
    return [x for x in res.splitlines() if "VPW_WREG_RESULT" in x][-1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("defs,shift,slr,want", [
    (["-DOT_S81SL_VP_WREG"], 1, False, "PASS"),          # with the define: every output exactly one clk later
    (["-DOT_S81SL_VP_WREG"], 1, True, "PASS"),           # same on the SLR form
    ([], 0, False, "PASS"),                              # without the define: inert, same cycle
    ([], 0, True, "PASS"),
    (["-DOT_S81SL_VP_WREG"], 0, False, "FAIL"),          # controls: the bench sees the edge in both directions
    ([], 1, False, "FAIL"),
])
def test_lockstep(tree, tmp_path, defs, shift, slr, want):
    line = bench(tree, tmp_path, defs, shift, slr)
    assert f"VPW_WREG_RESULT {want}" in line, line
    assert f"wreg {1 if defs else 0}" in line, line
    if want == "PASS":
        assert "errors 0" in line
        n = {k: int(line.split(k + " ")[1].split(",")[0].split()[0]) for k in ("with data", "x-data", "collisions")}
        assert n["with data"] > 3000 and n["x-data"] > 1000 and n["collisions"] > 100, line   # every path was exercised


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
def test_mutant_xwd_not_delayed_fails(tree, tmp_path):
    line = bench(tree, tmp_path, ["-DOT_S81SL_VP_WREG"], 1, mutate=("assign xwd_w = p_xwd;", "assign xwd_w = xwd_i;"))
    assert "VPW_WREG_RESULT FAIL" in line, line
