"""HEAD-92 11-10 form ZLP: kit_zl_hold_pad.py wiring (pre_cts source line, config exports, resume) is idempotent."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_zl_hold_pad as Z  # noqa: E402


def _kit(tmp_path):
    k = tmp_path / "k"
    k.mkdir()
    (k / "pre_cts.tcl").write_text("source /work/clock_taps.tcl\n")
    (k / "config.mk").write_text("export PLATFORM = asap7\n")
    return k


def test_apply_wires_kit_once(tmp_path):
    k = _kit(tmp_path)
    Z.apply(k)
    Z.apply(k)
    pre = (k / "pre_cts.tcl").read_text()
    assert pre.count(Z.SRC) == 1 and pre.index(Z.SRC) < pre.index("clock_taps.tcl")
    cfg = (k / "config.mk").read_text()
    assert cfg.count("export OT_ZLP = 1") == 1 and "export SLEW_MARGIN = 20" in cfg
    assert json.loads((k / "resume.json").read_text()) == {"start": "cts"}
    assert (k / "zl_hold_pad.tcl").read_text() == Z.TCL.read_text()
    assert (k / "pre_cts.tcl.pre_zlp").read_text() == "source /work/clock_taps.tcl\n"


def test_existing_resume_kept(tmp_path):
    k = _kit(tmp_path)
    (k / "resume.json").write_text('{"start": "place"}\n')
    Z.apply(k, report_only=True)
    assert json.loads((k / "resume.json").read_text()) == {"start": "place"}
    assert "OT_ZLP_REPORT_ONLY = 1" in (k / "config.mk").read_text()


def test_tcl_is_off_by_default():
    t = Z.TCL.read_text()
    assert 'zlp_env OT_ZLP 0] eq "1"' in t and "HB4xp67_ASAP7_75t_R" in t and "setDoNotTouch" not in t and "regexp {^D$} $pn" in t


def test_qc_seam_class_recipe(tmp_path):
    import re
    k = _kit(tmp_path)
    cre = Z.class_regex()
    Z.apply(k, class_re=cre)
    Z.apply(k, class_re=cre)
    cfg = (k / "config.mk").read_text()
    assert cfg.count("export OT_ZLP_CLASS = ") == 1 and "$" not in cfg.split("OT_ZLP_CLASS = ")[1]
    assert "#" not in cre  # a make comment char would cut the value
    for hit in ("u_bound.u_pd12_b_hw_i_3.r[4]$_DFF_P_", "u_bound.u_u_xl1_5.wo_d[174]$_DFF_P_",
                "u_bound.u_u_xl1_2.wctl[26]$_DFF_P_", "u_bound.u_rrl_7/q$_DFF_P_", "u_bound.u_ist_x_su_c_i__u_lane0_1_2/q$_DFF_P_",
                "u_bound.u_u_r3.u_hi_pad_d.g_line.r[2][5]$_DFF_P_", "u_bound.u_lpad_x_ctl_i.r[1]$_DFF_P_"):
        assert re.search(cre, hit), hit
    for miss in ("u_bound.u_core.u_dec.u_out.acc[3]$_DFF_P_", "u_bound.u_core.fsm.state[1]$_DFF_P_"):
        assert not re.search(cre, miss), miss


def test_unknown_class_refused():
    import pytest
    with pytest.raises(SystemExit):
        Z.class_regex(names=["nope"])
    assert Z.class_regex(names=["pad_line"]).startswith("(")


def test_tcl_class_filter_present():
    t = Z.TCL.read_text()
    assert "OT_ZLP_CLASS" in t and "class_skipped" in t
    assert "regexp -- $zlp_class [$inst getName]" in t
