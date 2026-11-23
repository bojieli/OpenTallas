"""S81-VPW-SPR: s81_vpw_spr_overlay.py on the fixture VP source (after the XR and SLR overlays, with or without XRB), and the
SPR 0 / SPR 1 lock-step bench with iverilog (plus a mutant the bench must catch).
    python3 -m pytest -q tools/die_plan/test_s81_vpw_spr_overlay.py"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vpw_slr_overlay as S  # noqa: E402
import s81_vpw_spr_overlay as P  # noqa: E402
import s81_vpw_xrb_overlay as B  # noqa: E402
from test_s81_vpw_slr_overlay import tree  # noqa: E402,F401  (fixture: XR overlay applied)


def test_overlay_edits_only_vpw_and_refuses_twice(tree):  # noqa: F811
    assert S.main([str(tree)]) == 0
    before = (tree / P.REL).read_text()
    assert P.main([str(tree)]) == 0
    after = (tree / P.REL).read_text()
    vp_end = before.rfind("\nendmodule", 0, before.index("module ot_s81sl_vpw"))
    assert after[:vp_end] == before[:vp_end]                              # nothing of ot_s81sl_vp moves
    assert "parameter integer SPR = `OT_S81SL_VP_SPR_DEFAULT) (" in after and "begin : g_spr" in after
    assert "(SPR != 0) ? spr_wd :" in after and "& hs_d_i[128 + SL * sr +: SL]" in after
    with pytest.raises(SystemExit, match="SPR_OVERLAY_TWICE"):
        P.main([str(tree)])


def test_overlay_needs_the_slr_form_and_composes_after_xrb(tree):  # noqa: F811
    with pytest.raises(SystemExit, match="SPR_OVERLAY_MISS"):
        P.main([str(tree)])
    assert S.main([str(tree)]) == 0 and B.main([str(tree)]) == 0 and P.main([str(tree)]) == 0
    after = (tree / P.REL).read_text()
    assert "& hs_d_b[sb][128 + SL * sr +: SL]" in after and "& sw_d_b[sb][SL * sr +: SL]" in after


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("xrb,mutant,want", [(0, False, "SPR_EQ PASS"), (1, False, "SPR_EQ PASS"), (0, True, "SPR_EQ FAIL")])
def test_lockstep_spr_equals_mux(tree, tmp_path, xrb, mutant, want):  # noqa: F811
    assert S.main([str(tree)]) == 0 and (not xrb or B.main([str(tree)]) == 0) and P.main([str(tree)]) == 0
    vp = (tree / P.REL).read_text()
    mod = vp[min(vp.find("// " + t + " (tools") % (len(vp) + 1) for t in (B.TAG, P.TAG)):]
    if mutant:   # c1 data under the c0 select
        old = "({SL{sel_q[3]}} & c1_w"
        assert mod.count(old) == 1
        mod = mod.replace(old, "({SL{sel_q[2]}} & c1_w")
    (tmp_path / "vpw.sv").write_text(mod)
    tb = (HERE / "fixtures/s81_vp_xr/tb_vpw_spr.sv").read_text()
    if xrb:
        tb = tb.replace(".SPR(1)) u1", ".SPR(1), .XRB(1)) u1")
    (tmp_path / "tb.sv").write_text(tb)
    out = tmp_path / "tb.vvp"
    r = subprocess.run(["iverilog", "-g2012", "-s", "tb_vpw_spr", "-o", str(out), str(tmp_path / "tb.sv"), str(tmp_path / "vpw.sv")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    r = subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True, timeout=600)
    assert want in r.stdout, r.stdout[-800:]
