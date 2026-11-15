"""KIT-OPS-5 11-14 (FABLE-METHOD lever 4): a post-CTS TT setup estimate below -150 ps stops the die-plan kit before route.
    python3 -m pytest -q tools/die_plan/test_postcts_setup_triage.py"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import gen_phys  # noqa: E402
import test_insertion_band_advisory as B  # noqa: E402


def _gate(tmp, verdict):
    return B._run(B._snippet(gen_phys.RUN_KIT, B.HBM_START, B.GP_END), tmp, verdict)


def test_setup_triage_stops_the_kit_even_under_the_advisory_band_policy(tmp_path):
    out, work = _gate(tmp_path, "SETUP_TRIAGE setup_est -443.00 < -150 ps (PLAN-TRIAGE) FAIL")
    assert "RC=6" in out
    txt = (work / "FAIL_POSTCTS").read_text()
    assert "SETUP_TRIAGE" in txt and "PLAN-TRIAGE" in txt
    assert not (work / "postcts_advisory.log").exists()


def test_plain_band_fail_is_still_advisory(tmp_path):
    out, work = _gate(tmp_path, "FAIL")
    assert "RC=0" in out and not (work / "FAIL_POSTCTS").exists()


def test_passing_gate_unchanged(tmp_path):
    out, work = _gate(tmp_path, "PASS")
    assert "RC=0" in out and not (work / "FAIL_POSTCTS").exists()


def test_kit_wave_classifies_the_stop_as_plan_triage():
    import kit_wave as KW
    rules = [r for r in KW.RULES if any(isinstance(x, str) and "SETUP_TRIAGE" in x for x in r)]
    assert len(rules) == 1 and rules[0][0] == "PLAN"


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
@pytest.mark.parametrize("ws,stop,expect", [(-443.0, "", 1), (-151.0, "", 1), (-149.0, "", 0), (-443.0, "0", 0), (-443.0, "off", 0)])
def test_gate_tcl_decision(ws, stop, expect):
    src = (HERE / "postcts_gate.tcl").read_text()
    i = src.index("set ot_pg_stop -150.0")
    j = src.index("set fh [open /work/postcts_gate_")
    block = src[i:j]
    script = (f"set n 5\nset ot_pg_C TT\nset ws {ws}\nset v PASS\n" + (f"set ::env(OT_POSTCTS_SETUP_STOP_PS) {stop}\n" if stop != "" else "")
              + block + "puts \"T=$ot_pg_triage V=$v\"\n")
    r = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert f"T={expect}" in r.stdout, r.stdout + r.stderr
