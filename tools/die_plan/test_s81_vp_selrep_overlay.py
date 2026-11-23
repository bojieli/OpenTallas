"""S81-VP-SELREP: s81_vp_selrep_overlay.py on the fixture VP source, raw and after the XR / SLR / XRB / SPR overlays.
Every edit is counted, no source line moves, a second run and a foreign source are refused, and SELREP 0 keeps the source
expressions.  The SELREP 0 / 1 lock-step equivalence ran as a Verilator bench on the full vp with its deps (OPUS-FIX-S81-
LEAF-R10 11-22, epyc8: 8/8 PASS, 59,959 compares; the per-group mutant FAILs, 33,611 mismatches).
    python3 -m pytest -q tools/die_plan/test_s81_vp_selrep_overlay.py"""
import gzip
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vp_selrep_overlay as R  # noqa: E402
import s81_vpw_slr_overlay as S  # noqa: E402
import s81_vpw_spr_overlay as P  # noqa: E402
import s81_vpw_xrb_overlay as B  # noqa: E402
from test_s81_vpw_slr_overlay import tree  # noqa: E402,F401  (fixture: XR overlay applied)

RAW = HERE / "fixtures/s81_vp_xr/ot_s81sl_vp.sv.gz"


def test_raw_fixture_patch_counts_and_keeps_lines():
    s = gzip.decompress(RAW.read_bytes()).decode()
    out = R.patch(s)
    assert out.count("\n") == s.count("\n")
    assert out.count(R.TAG) == 3                                              # xsr / npre_d decl / nmr blocks
    assert "parameter integer SELREP = `ifdef OT_S81SL_VP_SELREP 1 `else 0 `endif" in out
    assert "x_qd <= (SELREP != 0) ? xq_sel : xsw2 ? {q0, q1} : {q1, q0};" in out
    assert "if (SRP != 0) n_pre <= npre_d; if (e_nm) begin if (SRP == 0) n_pre <= e_cd[159:32];" in out
    assert "if (SRP == 0) n_pre <= q1r;" in out
    # every changed line keeps its position: the diff is line-for-line
    a, b = s.split("\n"), out.split("\n")
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    assert len(changed) == len(R.EDITS)


def test_refuses_twice_and_foreign_source(tmp_path):
    s = gzip.decompress(RAW.read_bytes()).decode()
    with pytest.raises(SystemExit, match="SELREP_OVERLAY_TWICE"):
        R.patch(R.patch(s))
    with pytest.raises(SystemExit, match="SELREP_OVERLAY_MISS"):
        R.patch(s.replace("            n_pre <= q1r;\n", "            n_pre <= q1r ^ 1;\n"))


def test_composes_with_vpw_overlays(tree):  # noqa: F811
    assert S.main([str(tree)]) == 0 and B.main([str(tree)]) == 0 and P.main([str(tree)]) == 0
    assert R.main([str(tree)]) == 0
    vp = (tree / R.REL).read_text()
    assert "begin : g_xsr" in vp and "begin : g_nmr" in vp and "begin : g_spr" in vp
