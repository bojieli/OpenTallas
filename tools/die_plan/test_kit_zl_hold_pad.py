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
    assert 'zlp_env OT_ZLP 0] eq "1"' in t and "HB4xp67_ASAP7_75t_R" in t and "setDoNotTouch 1" in t
