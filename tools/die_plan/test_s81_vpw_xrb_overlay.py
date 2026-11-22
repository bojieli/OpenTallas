"""S81-VPW-XRB: s81_vpw_xrb_overlay.py on the fixture VP source (after the XR and SLR overlays), and the XRB 0 / XRB 1
lock-step bench with iverilog (plus a mutant the bench must catch).
    python3 -m pytest -q tools/die_plan/test_s81_vpw_xrb_overlay.py"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vpw_slr_overlay as S  # noqa: E402
import s81_vpw_xrb_overlay as B  # noqa: E402
from test_s81_vpw_slr_overlay import tree  # noqa: E402,F401  (fixture: XR overlay applied)


def test_overlay_edits_only_vpw_and_refuses_twice(tree):  # noqa: F811
    assert S.main([str(tree)]) == 0
    before = (tree / B.REL).read_text()
    assert B.main([str(tree)]) == 0
    after = (tree / B.REL).read_text()
    vp_end = before.index("module ot_s81sl_vpw")
    vp_end = before.rfind("\nendmodule", 0, vp_end)
    assert after[:vp_end] == before[:vp_end]                              # nothing of ot_s81sl_vp moves
    assert "parameter integer XRB = `OT_S81SL_VP_XRB_DEFAULT) (" in after and "begin : g_xrb" in after
    assert after.count("sw_d_b[sb][") == 2 and after.count("xwd_b[gb][") == 2 and "cw_d_b[sb][31:0]" in after
    assert "n_wdo[b] = hi_sw ? sw_d_i[255:128]" in after                  # b_dec untouched
    with pytest.raises(SystemExit, match="XRB_OVERLAY_TWICE"):
        B.main([str(tree)])


def test_overlay_needs_the_slr_form(tree):  # noqa: F811
    with pytest.raises(SystemExit, match="XRB_OVERLAY_MISS"):
        B.main([str(tree)])


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("mutant,want", [(False, "XRB_EQ PASS"), (True, "XRB_EQ FAIL")])
def test_lockstep_xrb_equals_shared(tree, tmp_path, mutant, want):  # noqa: F811
    assert S.main([str(tree)]) == 0 and B.main([str(tree)]) == 0
    vp = (tree / B.REL).read_text()
    mod = vp[vp.index("// " + B.TAG + " (tools"):]
    if mutant:
        line = "always @(posedge clk) begin sw_d_q <= sw_d; hs_d_q <= hs_d;"
        assert mod.count(line) == 1
        mod = mod.replace(line, "always @(posedge clk) begin sw_d_q <= sw_d; hs_d_q <= hs_d ^ 256'd1;")
    (tmp_path / "vpw.sv").write_text(mod)
    out = tmp_path / "tb.vvp"
    r = subprocess.run(["iverilog", "-g2012", "-o", str(out), str(HERE / "fixtures/s81_vp_xr/tb_vpw_xrb.sv"),
                        str(tmp_path / "vpw.sv")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    r = subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True, timeout=600)
    assert want in r.stdout, r.stdout[-800:]
