"""S81-VP-CFX overlay: exact counted edits on the tree form (XR / WRP fixture) and on the plain form; refusals."""
import gzip
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vp_cfx_overlay as CFX  # noqa: E402

FIX = HERE / "fixtures" / "s81_vp_xr" / "ot_s81sl_vp.sv.gz"


def _src():
    return gzip.open(FIX, "rt").read()


def test_overlay_applies_on_the_tree_form():
    s = _src()
    assert "CFX" not in s
    t = CFX.overlay(s)
    assert t.count("`define OT_S81SL_VP_CFX_DEFAULT") == 2 and t.count("parameter integer CFX =") == 1
    assert "+ (CFX != 0 ? 1 : 0))) u_wi (" in t and "lane_v <= ydv[YL];" in t and "yrow_d[YL][32 * i +: 32]" in t
    assert t.count("hqd_l[(4 *") == 4 and "if (cfw[0]) cf[16 + i] <= cfd[32 * i +: 32];" in t
    # the pin-time fault term and the write valid delay keep their cycle
    assert "(ydv[YA] && !hqv_c)" in t and re.search(r"D\(HPL \+ CS_HI_[ED] \+ CS_HO_D \+ SRO\), \.RESET\(1\)\) u_wv", t)
    # only additions and the listed line changes: every other line of the source is kept, in order
    kept = [ln for ln in s.splitlines() if ln in set(t.splitlines())]
    assert len(s.splitlines()) - len(kept) == 13


def test_cfx0_branch_is_plain_wires():
    t = CFX.overlay(_src())
    m = re.search(r"end else begin : g_ncfx\n(.*?)\n\s*end endgenerate", t, re.S)
    assert m and m.group(1).strip() == "assign cfw = cfs; assign cfd = q1r; assign hqd_l = hqd_c;"


def test_second_run_refused():
    t = CFX.overlay(_src())
    with pytest.raises(ValueError, match="already carries CFX"):
        CFX.overlay(t)


def test_miss_refused():
    s = _src().replace("else lane_v <= ydv[YA];", "else lane_v <= ydv[YA ];")
    with pytest.raises(ValueError, match="expected 1"):
        CFX.overlay(s)


def test_file_rewrite(tmp_path):
    f = tmp_path / "ot_s81sl_vp.sv"
    f.write_text(_src())
    assert CFX.main(["x", str(f)]) == 0
    assert "g_cfx" in f.read_text() and not list(tmp_path.glob("*.cfx_new"))
